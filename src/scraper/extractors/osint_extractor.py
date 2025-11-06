from datetime import datetime
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, cast
import phonenumbers
import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style
from dns import resolver as dns_resolver
from db.manager import DatabaseManager
from scraper.fetcher import WebFetcher
from scraper.parser import WebParser

from ..utils.data_processing import standardize_for_json, extract_structured_fields
from ..utils.validators import validate_domain
from ..utils.extractors import extract_emails, filter_emails,  extract_phone_numbers, filter_phone_numbers
from ..utils.clients import fetch_dns_records, fetch_hunterio, fetch_whois, fetch_shodan, check_email_breaches
from ..utils.osint_sources import (
    fetch_domain_osint,
    fetch_email_osint,
    fetch_social_osint,
    find_brand_social_profiles,
    fetch_website_contacts
)
from ..utils.formatters import format_domain_osint_report, format_page_analysis_report, generate_html_report
from urllib.parse import urlparse

logger = logging.getLogger("osint.extractor")


class OSINTExtractor:
    '''
    Funzione: OSINTExtractor
    Orchestratore responsabile per l'estrazione e l'elaborazione dei dati OSINT da varie fonti.
    Parametri formali:
        self -> Riferimento all'istanza della classe
        dict[str, str] | None api_keys -> Dizionario contenente le API keys per i vari servizi OSINT
        Path | str | None data_dir -> Percorso della directory per i file di output
        dict[str, Path] | None dirs -> Dizionario contenente i percorsi delle directory del progetto
    Valore di ritorno:
        None -> Il costruttore non restituisce un valore esplicito
    '''
    def __init__(self, api_keys: dict[str, str] | None = None, data_dir: Path | str | None = None, dirs: dict[str, Path] | None = None):
        self.db = DatabaseManager.get_instance()
        self.db.init_schema("osint")
        self.fetcher = WebFetcher(cache_dir=".osint_cache")
        self.parser = WebParser()
        self.api_keys = api_keys or {}
        self.logger = logging.getLogger("osint.extractor")
        self.data_dir = Path(data_dir) if data_dir else Path.cwd() / "data"
        self.dirs = dirs or {}

# GESTIONE DI OGNI OGGETTO ANALIZZATO
    def entity(self, target: str, entity_type: str) -> dict[str, Any]:
       '''
       Funzione: entity
       Coordina l'estrazione dei dati OSINT per una specifica entità (dominio, email, username) da tutte le fonti configurate.
       Parametri formali:
           self -> Riferimento all'istanza della classe
           str target -> L'identificativo dell'entità da analizzare
           str entity_type -> Il tipo di entità (dominio, email, username)
       Valore di ritorno:
           dict[str, Any] -> I risultati dell'analisi OSINT per l'entità specificata
       '''
       self.logger.info(f"Profiling {entity_type}: {target}")
       entity_id = self._get_or_create_entity(target, entity_type) # recupera o crea l'entità nel database 
       self.logger.debug(f"Entity ID for {target} ({entity_type}): {entity_id}")

       data_to_save = {}
       source_type_for_saving = entity_type 

       if entity_type == "domain":
           self.logger.debug(f"Processing domain data for {target}")
           data_to_save = fetch_domain_osint(target, api_keys=self.api_keys, logger=self.logger) # scansione dominio
           source_type_for_saving = "domain"
       elif entity_type == "email":
           self.logger.debug(f"Processing email data for {target}")
           data_to_save = fetch_email_osint(target, api_keys=self.api_keys, logger=self.logger) # scansione email
           source_type_for_saving = "email"
       elif entity_type == "username":
           self.logger.debug(f"Processing username social scan for {target}")
           data_to_save = fetch_social_osint(target, logger=self.logger) # scansione username sui social
           source_type_for_saving = "social"
       else:
           self.logger.error(f"Unknown entity type for entity: {entity_type}")
           return {"error": f"Unknown entity type: {entity_type}"}

       self.logger.debug(f"Data collected for {target} ({entity_type}): {data_to_save}")

       if data_to_save:
            try:
               self._save_osint_profile(entity_id, source_type_for_saving, data_to_save) # salvataggio su db

            except Exception as e:
                 self.logger.error(f"Error during data saving or contact extraction for entity {entity_id}: {e}", exc_info=True)


       profile_result = self._build_full_profile(entity_id) # costruzione profilo completo 
       self.logger.debug(f"Result of _build_full_profile for entity {entity_id}: {profile_result}")
       return profile_result
    
# INTERAZIONI CON DB (estrazione o creazione)
    def _get_or_create_entity(self, identifier: str, entity_type: str) -> int:
        '''
        Funzione: _get_or_create_entity
        Registra una nuova entità nel database o recupera l'ID di un'entità esistente.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            str identifier -> L'identificativo univoco dell'entità (es. dominio, email, username)
            str entity_type -> Il tipo di entità ("domain", "email", "username")
        Valore di ritorno:
            int -> L'ID univoco dell'entità nel database
        '''
        db_entity_type = "company" if entity_type == "domain" else "person" # Associa "domain" a "company" e gli altri tipi a "person"
        domain_value = identifier if entity_type == "domain" else None # Se l'entità è un dominio, salva il dominio, altrimenti None

        with self.db.transaction("osint") as cursor: # Inizia una transazione per garantire l'atomicità (ovvero tutte le operazioni devono riuscire o fallire insieme)
            cursor.execute(
                """
                INSERT OR IGNORE INTO entities (type, name, domain)
                VALUES (?, ?, ?)
            """,
                (db_entity_type, identifier, domain_value), # Inserisce il tipo, il nome e il dominio (se applicabile) dell'entità
            )

            entity_id: Optional[int] = None # Inizializza entity_id come None per gestire il caso in cui l'inserimento fallisca
            if cursor.rowcount > 0: # controlla se l'inserimento è riuscito
                entity_id = cursor.lastrowid # associa l'ID dell'ultima riga inserita a entity_id
                if entity_id is None:
                    self.logger.error(f"CRITICAL: rowcount > 0 but lastrowid is None for entity '{identifier}'.")
                    raise ValueError(f"Failed to get lastrowid for new entity '{identifier}'")
                self.logger.debug(f"Created new entity: ID {entity_id}, Name '{identifier}', Type '{db_entity_type}'")
                return cast(int, entity_id) # Restituisce l'ID dell'entità appena creata (cast serve a specificare che entity_id è di tipo int)
            else:
                self.logger.debug(f"Entity '{identifier}' (type: {db_entity_type}) likely already exists. Fetching its ID.")
                if db_entity_type == "company" and domain_value:
                    cursor.execute("SELECT id FROM entities WHERE name=? AND type=? AND domain=?", (identifier, db_entity_type, domain_value)) # Se l'entità è una company, cerca per nome e dominio

                elif db_entity_type == "person" and domain_value is None:
                     cursor.execute("SELECT id FROM entities WHERE name=? AND type=? AND domain IS NULL", (identifier, db_entity_type)) # Se l'entità è una person, cerca per nome e tipo, ignorando il dominio

                else:
                    self.logger.warning(f"Attempting generic SELECT for entity: Name '{identifier}', Type '{db_entity_type}', Domain '{domain_value}'") 
                    cursor.execute("SELECT id FROM entities WHERE name=? AND type=?", (identifier, db_entity_type)) # se l'entità non è né company né person, esegue una ricerca generica

                result = cursor.fetchone() # recupera prima riga del risultato della query (che corrisponde all'entità cercata)
                if not result:
                    self.logger.error(f"CRITICAL: Entity '{identifier}' (type: {db_entity_type}) was IGNORED on insert but NOT FOUND on select. Check UNIQUE constraints and SELECT query logic.")
                    raise ValueError(f"Entity '{identifier}' exists (was ignored) but its ID could not be retrieved.")

                entity_id = result['id'] # Estra l'ID dell'entità
                self.logger.debug(f"Found existing entity: ID {entity_id}, Name '{identifier}', Type '{db_entity_type}')")
                return cast(int, entity_id) # Restituisce ID 

    def _process_domain_data(self, target: str) -> dict[str, Any]:
        '''
        Funzione: _process_domain_data
        Raccoglie dati OSINT per un dominio o IP da WHOIS, DNS e Shodan.
        Parametri formali:
            self -> Riferimento all'istanza della classe (presumendo contenga api_keys e logger)
            str target -> Il dominio o IP da processare
        Valore di ritorno:
            dict[str, Any] -> Un dizionario contenente i dati raccolti dalle varie fonti
        '''
        result: dict[str, Any] = {}

        # Verifica se l'input è un IP
        try:
            import ipaddress
            is_ip = bool(ipaddress.ip_address(target))
        except ValueError:
            is_ip = False

        # WHOIS lookup (fetch_whois in clients.py does NOT take an API key)
        self.logger.info(f"Running WHOIS lookup for {target}...")
        whois_data = fetch_whois(target)
        if whois_data and not whois_data.get("error"):
            result["whois"] = whois_data
        elif whois_data and whois_data.get("error"):
            self.logger.warning(f"WHOIS lookup failed for {target}: {whois_data['error']}")
        else:
            self.logger.warning(f"WHOIS lookup for {target} returned no data.")

        # Se non è un IP, procedi con DNS lookup
        if not is_ip:
            # DNS lookup (fetch_dns_records in clients.py does NOT take an API key)
            self.logger.info(f"Running DNS lookup for {target}...")
            dns_data = fetch_dns_records(target)
            # Check if dns_data is valid data (not just an error dict)
            if dns_data and not dns_data.get("error"):
                result["dns"] = dns_data

                # Shodan lookup (requires API key and resolved IPs)
                shodan_api_key = self.api_keys.get("shodan")
                if shodan_api_key:
                    # Extract IPv4 addresses
                    # Note: The DNS function returns a list of strings, which is what fetch_shodan expects for IPs
                    resolved_ips: List[str] = dns_data.get("A", [])

                    if resolved_ips:
                        # Ask user if Shodan scan is desired (optional user interaction)
                        user_choice = input(f"\n{Fore.YELLOW}Vuoi eseguire la scansione Shodan per {target}? (s/N): {Style.RESET_ALL}").lower()
                        if user_choice == 's':
                            self.logger.info(f"Running Shodan lookup for IPs: {resolved_ips} associated with {target}...")
                            # Corrected: Pass the list of IPs as the first argument and the API key as the second
                            shodan_data = fetch_shodan(resolved_ips, shodan_api_key)
                            # Check if shodan_data is valid data (not just an error dict)
                            if shodan_data and not shodan_data.get("error"):
                                result["shodan"] = shodan_data
                            elif shodan_data and shodan_data.get("error"):
                                self.logger.warning(f"Shodan lookup failed: {shodan_data['error']}")
                            else:
                                self.logger.warning("Shodan lookup returned no data.")
                        else:
                            self.logger.info("Shodan lookup skipped by user.")
                    else:
                        self.logger.debug(f"No A records found for Shodan lookup of {target}. Shodan lookup skipped.")
                else:
                    self.logger.info("Shodan API key not provided. Skipping Shodan lookup.")

            elif dns_data and dns_data.get("error"):
                self.logger.warning(f"DNS lookup failed for {target}: {dns_data['error']}")
            else:
                self.logger.warning(f"DNS lookup for {target} returned no data or encountered an unhandled issue.")
        else:
            # Se è un IP, esegui direttamente Shodan
            shodan_api_key = self.api_keys.get("shodan")
            if shodan_api_key:
                user_choice = input(f"\n{Fore.YELLOW}Vuoi eseguire la scansione Shodan per l'IP {target}? (s/N): {Style.RESET_ALL}").lower()
                if user_choice == 's':
                    self.logger.info(f"Running Shodan lookup for IP: {target}...")
                    shodan_data = fetch_shodan([target], shodan_api_key)
                    if shodan_data and not shodan_data.get("error"):
                        result["shodan"] = shodan_data
                    elif shodan_data and shodan_data.get("error"):
                        self.logger.warning(f"Shodan lookup failed: {shodan_data['error']}")
                    else:
                        self.logger.warning("Shodan lookup returned no data.")
                else:
                    self.logger.info("Shodan lookup skipped by user.")
            else:
                self.logger.info("Shodan API key not provided. Skipping Shodan lookup.")

        return result

# SALVATAGGIO DATI PROFILO
    def _save_osint_profile(self, entity_id: int, source: str, data: dict[str, Any]) -> None:
        '''
        Funzione: _save_osint_profile
        Salva i dati OSINT grezzi e i campi estratti strutturati nel database.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            int entity_id -> L'ID dell'entità a cui associare il profilo
            str source -> La fonte da cui provengono i dati (es. "domain", "email", "social")
            dict[str, Any] data -> Il dizionario contenente i dati raccolti
        Valore di ritorno:
            None -> La funzione non restituisce un valore
        '''
        if not data:
            self.logger.info(f"No data to save for entity_id {entity_id}, source {source}.")
            return

        data_standardized = standardize_for_json(data)
        structured_fields = extract_structured_fields(data, source)

        with self.db.transaction("osint") as cursor:
            cursor.execute(
                """
                INSERT INTO osint_profiles (entity_id, source, raw_data, extracted_fields)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(entity_id, source) DO UPDATE SET
                    raw_data=excluded.raw_data,
                    extracted_fields=excluded.extracted_fields,
                    updated_at=CURRENT_TIMESTAMP
            """,
                (
                    entity_id,
                    source,
                    json.dumps(data_standardized),
                    json.dumps(structured_fields),
                ),
            )
        self.logger.debug(f"OSINT profile saved for entity ID {entity_id}, source {source}.")

# ESTRAI DATI

    def _extract_and_save_contacts(self, entity_id: int, data: dict[str, Any], source: str) -> None:
        '''
        Funzione: _extract_and_save_contacts
        Estrae indirizzi email e numeri di telefono dai dati OSINT raccolti e li salva nella tabella contatti.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            int entity_id -> L'ID dell'entità a cui associare i contatti
            dict[str, Any] data -> Il dizionario contenente i dati OSINT raccolti da cui estrarre i contatti
            str source -> La fonte da cui i contatti sono stati estratti (per tracciare l'origine)
        Valore di ritorno:
            None -> La funzione non restituisce un valore
        '''
        self.logger.debug(f"Starting contact extraction for entity {entity_id} from source {source}")
        if not data:
            self.logger.debug(f"No data provided for contact extraction for entity {entity_id} from source {source}.")
            return

        emails_found = set()
        phones_found = set()

        def find_contacts_recursive(item: Any):
            """Ricorsivamente cerca stringhe dentro dict/list e usa helper centralizzati per
            estrarre email e numeri di telefono (evitando regex duplicati)."""
            if isinstance(item, dict):
                for k, v in item.items():
                    if isinstance(v, str):
                        # prefer explicit email-looking fields
                        if 'email' in k.lower() and "@" in v:
                            emails_found.add(v.lower())

                        # use centralized extractors for robustness
                        try:
                            emails_found.update(extract_emails(v))
                        except Exception:
                            # fallback to central extractor again (best-effort)
                            try:
                                emails_found.update(extract_emails(v))
                            except Exception:
                                pass

                        try:
                            phones_found.update(extract_phone_numbers(v))
                        except Exception:
                            try:
                                phones_found.update(extract_phone_numbers(v))
                            except Exception:
                                pass
                    else:
                        find_contacts_recursive(v)
            elif isinstance(item, list):
                for i in item:
                    find_contacts_recursive(i)
            elif isinstance(item, str):
                try:
                    emails_found.update(extract_emails(item))
                except Exception:
                    try:
                        emails_found.update(extract_emails(item))
                    except Exception:
                        pass
                try:
                    phones_found.update(extract_phone_numbers(item))
                except Exception:
                    try:
                        phones_found.update(extract_phone_numbers(item))
                    except Exception:
                        pass


        find_contacts_recursive(data)

        # Use centralized phone filter to clean and validate phone numbers
        try:
            cleaned_phones = filter_phone_numbers(phones_found)
        except Exception:
            # Fallback: simple cleanup
            cleaned_phones = set()
            for phone in phones_found:
                cleaned_phone_value = re.sub(r'[^\d+]', '', str(phone))
                if 7 < len(cleaned_phone_value.replace('+', '')) < 16:
                    cleaned_phones.add(cleaned_phone_value)


        contacts_to_save: list[tuple[str, str, str]] = []
        email_exclude_extensions = ['.png', '.jpg', '.gif', '.jpeg', '.webp', '.svg', '.css', '.js']
        for email in emails_found:
             if not any(email.lower().endswith(ext) for ext in email_exclude_extensions):
                 contacts_to_save.append(("email", email.lower(), source))

        for phone in cleaned_phones:
             contacts_to_save.append(("phone", phone, source))


        if not contacts_to_save:
            self.logger.debug(f"No valid emails or phones found during extraction for entity {entity_id} from source {source}")
            return


        self.logger.debug(f"Saving {len(contacts_to_save)} contacts for entity {entity_id} from source {source}")
        with self.db.transaction("osint") as cursor:
            for contact_type, value, src in contacts_to_save:
                 if not value: continue

                 if contact_type == "email":
                     cursor.execute("SELECT id FROM contacts WHERE entity_id=? AND email IS NOT NULL AND email=?", (entity_id, value))
                     if not cursor.fetchone():
                        cursor.execute(
                             """
                             INSERT INTO contacts (entity_id, email, phone, source)
                             VALUES (?, ?, ?, ?)
                         """,
                             (entity_id, value, None, src),
                        )
                     else:
                         self.logger.debug(f"Email '{value}' already exists for entity {entity_id}. Skipping insert.")

                 elif contact_type == "phone":
                     cursor.execute("SELECT id FROM contacts WHERE entity_id=? AND phone IS NOT NULL AND phone=?", (entity_id, value))
                     if not cursor.fetchone():
                         cursor.execute(
                             """
                             INSERT INTO contacts (entity_id, email, phone, source)
                             VALUES (?, ?, ?, ?)
                         """,
                             (entity_id, None, value, src),
                         )
                     else:
                         self.logger.debug(f"Phone '{value}' already exists for entity {entity_id}. Skipping insert.")
                 else:
                     self.logger.warning(f"Unknown contact type '{contact_type}' during save for entity {entity_id}. Skipping insertion.")
        self.logger.debug(f"Finished saving contacts for entity {entity_id}.")

    def _build_full_profile(self, entity_id: int) -> dict[str, Any]:
        '''
        Funzione: _build_full_profile
        Compila un profilo OSINT completo per un'entità recuperando tutti i dati associati dal database.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            int entity_id -> L'ID dell'entità per cui costruire il profilo
        Valore di ritorno:
            dict[str, Any] -> Un dizionario rappresentante il profilo completo dell'entità
        '''
        self.logger.debug(f"Starting _build_full_profile for entity ID: {entity_id}")
        try:
            entity_row = self.db.fetch_one("SELECT * FROM entities WHERE id=?", (entity_id,), "osint") # recupera riga dell'entità dal database
            self.logger.debug(f"Fetched entity row for ID {entity_id}: {entity_row}")

            if not entity_row:
                self.logger.warning(f"Entity with ID {entity_id} not found for profile building.")
                return {"error": "Entity not found"}

            entity = dict(entity_row) # converte la riga in un dizionario
            self.logger.debug(f"Entity data extracted from row: {entity}")

            profiles_rows = self.db.fetch_all(
                    "SELECT source, extracted_fields, raw_data, updated_at FROM osint_profiles WHERE entity_id=?", (entity_id,), "osint"
                ) # estrae i profili associati all'entità
            profiles_data = {}
            for p_row in profiles_rows:
                source = p_row["source"]
                try:
                    extracted = json.loads(p_row["extracted_fields"]) if p_row.get("extracted_fields") else {} # struttura i campi estratti
                    raw = json.loads(p_row.get("raw_data")) if p_row.get("raw_data") else {} # struttura i dati grezzi
                    profiles_data[source] = {
                        "extracted": extracted,
                        "raw": raw,
                        "updated_at": p_row["updated_at"]
                    } # concatena i dati estratti e grezzi in un dizionario
                except json.JSONDecodeError:
                     self.logger.error(f"Failed to decode JSON for profile source {source}, entity {entity_id}.", exc_info=True)
                     profiles_data[source] = {"error": "Failed to decode profile data", "updated_at": p_row["updated_at"], "raw": p_row.get("raw_data", "N/A")}


            contacts_rows = self.db.fetch_all(
                "SELECT email, phone, source, created_at FROM contacts WHERE entity_id=?", (entity_id,), "osint"
            ) # estrae i contatti associati all'entità
            contacts_list = []
            for row in contacts_rows:
                if row.get("email"):
                    contacts_list.append({
                        "contact_type": "email", "value": row["email"], "source": row["source"], "created_at": row["created_at"]
                    }) # aggiunge l'email alla lista dei contatti
                if row.get("phone"):
                     contacts_list.append({
                        "contact_type": "phone", "value": row["phone"], "source": row["source"], "created_at": row["created_at"]
                     }) # aggiunge il telefono alla lista dei contatti

            domain_info_row = None
            if entity.get("type") == "company":
                 domain_info_row = self.db.fetch_one("SELECT * FROM domain_info WHERE entity_id=?", (entity_id,), "osint") # estrae le informazioni di dominio se l'entità è una company


            final_profile = {
                "entity": entity,
                "domain_info": dict(domain_info_row) if domain_info_row else None,
                "profiles": profiles_data,
                "contacts": contacts_list,
            } # costruisce il profilo finale con i dati dell'entità, le informazioni di dominio, i profili e i contatti
            self.logger.debug(f"Final profile structure for ID {entity_id} includes entity data: {final_profile.get('entity', 'N/A entity data')}")


            return final_profile

        except Exception as e:
            self.logger.error(f"Unexpected error building full profile for entity ID {entity_id}: {e}", exc_info=True)
            return {"error": f"Error building profile: {str(e)}"}
 
    def get_all_osint_profiles_summary(self) -> list[dict[str, Any]]:
       '''
       Funzione: get_all_osint_profiles_summary
       Recupera un sommario di tutte le entità OSINT salvate e le loro fonti di profilo disponibili.
       Parametri formali:
           self -> Riferimento all'istanza della classe
       Valore di ritorno:
           list[dict[str, Any]] -> Una lista di dizionari, ognuno rappresentante un sommario di un profilo OSINT
       '''
       self.logger.debug("Fetching all OSINT profiles summary.")
       with self.db.transaction("osint") as cursor:
           cursor.execute("SELECT id, name, type, domain, created_at FROM entities ORDER BY created_at DESC") # recupera tutte le entità dal database
           entities_rows = cursor.fetchall() # query per il recupero

            # per ogni entità, viene creato un dizionario che contiene l'ID, il nome, il tipo e il dominio (se applicabile)
           summaries = []
           for entity_row in entities_rows: 
               entity_dict = dict(entity_row) 
               cursor.execute("""
                   SELECT DISTINCT source
                   FROM osint_profiles
                   WHERE entity_id = ?
               """, (entity_dict["id"],)) # recupera le fonti di profilo associate all'entità
               sources_rows = cursor.fetchall() 
               entity_dict["profile_sources"] = [row["source"] for row in sources_rows] # aggiunge le fonti di profilo al dizionario dell'entità
               summaries.append(entity_dict) # aggiunge il sommario dell'entità alla lista dei sommari
           self.logger.debug(f"Fetched {len(summaries)} profile summaries.")
           return summaries

    def get_osint_profile_by_identifier(self, identifier: str) -> Optional[dict[str, Any]]:
        '''
        Funzione: get_osint_profile_by_identifier
        Recupera un profilo OSINT completo dal database utilizzando un identificativo (dominio, email o username).
        Parametri formali:
            self -> Riferimento all'istanza della classe
            str identifier -> L'identificativo dell'entità da cercare nel database
        Valore di ritorno:
            Optional[dict[str, Any]] -> Il profilo OSINT completo o None se l'entità non viene trovata
        '''
        self.logger.debug(f"Attempting to retrieve full profile for identifier: '{identifier}'")
        entity_type_guess = "unknown"
        if '.' in identifier and '@' not in identifier: # se contiene un punto ma non una chiocciola, probabilmente è un dominio
            entity_type_guess = "domain"
        elif '@' in identifier:
            entity_type_guess = "email" # se contiene una chiocciola, probabilmente è un'email
        else:
            entity_type_guess = "username" # altrimenti, è un username o un identificativo generico

        db_entity_type = "company" if entity_type_guess == "domain" else "person" # Associa "domain" a "company" e gli altri tipi a "person"
 
        entity_id_row = None
        with self.db.transaction("osint") as cursor: # Inizia una transazione per garantire l'atomicità
            if db_entity_type == "company":
                cursor.execute("SELECT id FROM entities WHERE name = ? AND type = 'company'", (identifier,)) # cerca per nome e tipo "company"
            else:
                cursor.execute("SELECT id FROM entities WHERE name = ? AND type = 'person'", (identifier,)) # cerca per nome e tipo "person"
            entity_id_row = cursor.fetchone()

        if entity_id_row:
            self.logger.debug(f"Entity found for identifier '{identifier}', ID: {entity_id_row['id']}. Building full profile.") 
            return self._build_full_profile(entity_id_row["id"]) # se l'entità esiste, costruisce il profilo completo
        else:
            self.logger.warning(f"No entity found in DB for identifier: '{identifier}' (guessed type: {entity_type_guess}).")
            return None

    def get_osint_profile_by_id(self, entity_id: int) -> Optional[dict[str, Any]]:
        '''
        Funzione: get_osint_profile_by_id
        Recupera un profilo OSINT completo dal database utilizzando l'ID univoco dell'entità.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            int entity_id -> L'ID dell'entità da cercare nel database
        Valore di ritorno:
            Optional[dict[str, Any]] -> Il profilo OSINT completo o None se l'entità non viene trovata
        '''
        self.logger.debug(f"Attempting to retrieve full profile for entity ID: '{entity_id}'")
        return self._build_full_profile(entity_id) # chiama il metodo per costruire il profilo completo

    def profile_domain(self, domain: str, force_recheck: bool = False) -> dict[str, Any]:
        '''
        Avvia il processo di profilazione OSINT per un dominio web.
        Valida l'input e delega al metodo entity.
        Args:
            domain: Il dominio da profilare
        Returns:
            Il profilo OSINT completo per il dominio, o un dizionario di errore.
        '''
        self.logger.info(f"Starting domain profiling for input: {domain}")
        if domain is None:
            self.logger.error("Input domain is None.")
            return {"error": "Input domain cannot be None"}

        is_valid, clean_domain = validate_domain(domain)
        if not is_valid:
             self.logger.warning(f"Invalid domain input: {domain}. Error: {clean_domain}")
             return {"error": f"Invalid domain format: {clean_domain}", "original_input": domain}

        self.logger.info(f"Profiling clean domain: {clean_domain}")
        # Chiama il metodo entity per gestire il flusso di lavoro 
        return self.entity(clean_domain, "domain")

    # Metodo pubblico chiamato dalla CLI per profilare un indirizzo email
    def profile_email(self, email: str) -> dict[str, Any]:
        '''
        Avvia il processo di profilazione OSINT per un indirizzo email.
        Delega al metodo entity.
        Args:
            email: L'indirizzo email da profilare
        Returns:
            Il profilo OSINT completo per l'email, o un dizionario di errore.
        '''
        self.logger.info(f"Starting email profiling for input: {email}")
        
        # Enhanced validation
        if not email or not isinstance(email, str):
            self.logger.warning(f"Invalid email input type: {type(email)}")
            return {"error": "Invalid email input provided.", "original_input": email}
        
        # Trim whitespace
        email = email.strip()
        
        # Basic email validation with regex
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            self.logger.warning(f"Email format validation failed for: {email}")
            return {"error": "Invalid email format provided.", "original_input": email}

        return self.entity(email, "email")

    # Metodo pubblico chiamato dalla CLI per profilare un username
    def profile_username(self, username: str) -> dict[str, Any]:
        '''
        Funzione: profile_username
        Esegue una scansione della presenza di un username su piattaforme social.
        
        Args:
            username: L'username da ricercare
            
        Returns:
            Un dizionario contenente i risultati della scansione social
        '''
        self.logger.info(f"Starting username social scan for: {username}")
        return fetch_social_osint(username, self.logger, self.dirs)

    def _display_osint_profile(self, profile_data: dict, target_identifier: str) -> None:
        '''
        Funzione: _display_osint_profile
        Visualizza i dati del profilo OSINT in un formato leggibile.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            dict profile_data -> I dati del profilo da visualizzare
            str target_identifier -> L'identificatore del target (dominio, email, username)
        Valore di ritorno:
            None -> La funzione non restituisce un valore
        '''
        if not profile_data:
            print(f"\n{Fore.RED}✗ No OSINT data found for {target_identifier}{Style.RESET_ALL}")
            return

        # Determine the type of profile and use appropriate formatter
        entity_type = profile_data.get("entity", {}).get("type")
        
        if entity_type == "company":  # Domain profile
            profiles = profile_data.get("profiles", {})
            domain_data = profiles.get("domain", {}).get("raw", {})
            shodan_skipped = "shodan" not in domain_data
            print(format_domain_osint_report(domain_data, target_identifier, target_identifier, shodan_skipped))
        
        elif entity_type == "person":  # Email or username profile
            if "@" in target_identifier:  # Email profile
                email_data = profile_data.get("profiles", {}).get("email", {}).get("raw", {})
                self._display_email_profile(email_data, target_identifier, profile_data) # mostra i dati associati all'email
            else:  # Username profile
                social_data = profile_data.get("profiles", {}).get("social", {}).get("raw", {})
                self._display_social_profile(social_data, target_identifier, profile_data) # mostra i dati associati allo username
        else:
            print(f"\n{Fore.RED}Unknown profile type for {target_identifier}{Style.RESET_ALL}")

    def _display_email_profile(self, email_data: dict, email: str, full_profile: dict) -> None:
        '''
        Funzione: _display_email_profile
        Visualizza il profilo OSINT di un indirizzo email in formato leggibile.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            dict email_data -> I dati OSINT dell'email
            str email -> L'indirizzo email target
            dict full_profile -> Il profilo completo dell'entità
        Valore di ritorno:
            None -> La funzione stampa i risultati
        '''
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"EMAIL OSINT PROFILE: {email}")
        print(f"{'='*80}{Style.RESET_ALL}")
        
        # Hunter.io data
        hunter_data = email_data.get("hunter", {})
        if hunter_data and not hunter_data.get("error"):
            print(f"\n{Fore.YELLOW}[HUNTER.IO RESULTS]{Style.RESET_ALL}")
            
            # Email verification
            verification = hunter_data.get("verification", {})
            if verification:
                print(f"  Status: {verification.get('status', 'Unknown')}")
                print(f"  Result: {verification.get('result', 'Unknown')}")
                print(f"  Score: {verification.get('score', 'N/A')}")
                
                # Email pattern analysis
                if verification.get('smtp_server'):
                    print(f"  SMTP Server: {verification['smtp_server']}")
                if verification.get('regexp'):
                    print(f"  Pattern Valid: {'Yes' if verification['regexp'] else 'No'}")
            
            # Domain information from Hunter
            domain_info = hunter_data.get("domain_info", {})
            if domain_info:
                print(f"\n  {Fore.YELLOW}Domain Analysis:{Style.RESET_ALL}")
                print(f"    Domain: {domain_info.get('domain', 'N/A')}")
                print(f"    Organization: {domain_info.get('organization', 'N/A')}")
                print(f"    Pattern: {domain_info.get('pattern', 'N/A')}")
        
        # Have I Been Pwned data
        hibp_data = email_data.get("hibp", {})
        if hibp_data and not hibp_data.get("error"):
            print(f"\n{Fore.RED}[HAVE I BEEN PWNED - BREACH DATA]{Style.RESET_ALL}")
            
            breaches = hibp_data.get("breaches", [])
            if breaches:
                print(f"  Found in {len(breaches)} data breach(es):")
                for breach in breaches[:5]:  # Show first 5 breaches
                    print(f"    • {breach.get('Name', 'Unknown')}")
                    print(f"      Date: {breach.get('BreachDate', 'Unknown')}")
                    print(f"      Accounts: {breach.get('PwnCount', 'Unknown'):,}")
                    print(f"      Data: {', '.join(breach.get('DataClasses', []))}")
                    print()
                
                if len(breaches) > 5:
                    print(f"    ... and {len(breaches) - 5} more breaches")
            else:
                print(f"  {Fore.YELLOW}✓ No breaches found{Style.RESET_ALL}")
            
            # Paste data
            pastes = hibp_data.get("pastes", [])
            if pastes:
                print(f"\n  {Fore.YELLOW}Found in {len(pastes)} paste(s):{Style.RESET_ALL}")
                for paste in pastes[:3]:  # Show first 3 pastes
                    print(f"    • Source: {paste.get('Source', 'Unknown')}")
                    print(f"      Date: {paste.get('Date', 'Unknown')}")
                    print(f"      Title: {paste.get('Title', 'No title')}")
        
        # Basic email analysis when no HIBP key is available
        elif not self.api_keys.get("hibp"):
            print(f"\n{Fore.YELLOW}[BASIC EMAIL ANALYSIS - NO HIBP KEY]{Style.RESET_ALL}")
            
            # Domain analysis
            domain = email.split('@')[1] if '@' in email else 'Unknown'
            print(f"  Domain: {domain}")
            
            # Check if it's a common provider
            common_providers = [
                'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 
                'protonmail.com', 'icloud.com', 'aol.com', 'live.com'
            ]
            
            if domain.lower() in common_providers:
                print(f"  Provider Type: {Fore.CYAN}Public Email Provider{Style.RESET_ALL}")
            else:
                print(f"  Provider Type: {Fore.YELLOW}Custom/Corporate Domain{Style.RESET_ALL}")
            
            # Basic format validation
            import re
            if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                print(f"  Format: {Fore.GREEN}Valid{Style.RESET_ALL}")
            else:
                print(f"  Format: {Fore.RED}Invalid{Style.RESET_ALL}")
            
            print(f"  {Fore.YELLOW}ℹ  Add HIBP API key for breach data{Style.RESET_ALL}")
        
        # Contact information from full profile
        contacts = full_profile.get("contacts", [])
        if contacts:
            print(f"\n{Fore.CYAN}[EXTRACTED CONTACTS]{Style.RESET_ALL}")
            emails = [c for c in contacts if c.get("contact_type") == "email"]
            phones = [c for c in contacts if c.get("contact_type") == "phone"]
            
            if emails:
                print(f"  Emails found: {len(emails)}")
                for contact in emails[:5]:
                    print(f"    • {contact.get('value', 'N/A')} (from: {contact.get('source', 'Unknown')})")
            
            if phones:
                print(f"  Phone numbers: {len(phones)}")
                for contact in phones[:5]:
                    print(f"    • {contact.get('value', 'N/A')} (from: {contact.get('source', 'Unknown')})")
        
        # Enhanced Summary
        print(f"\n{Fore.CYAN}[SUMMARY]{Style.RESET_ALL}")
        breach_count = len(hibp_data.get("breaches", [])) if hibp_data and not hibp_data.get("error") else 0
        paste_count = len(hibp_data.get("pastes", [])) if hibp_data and not hibp_data.get("error") else 0
        
        print(f"  Email: {email}")
        
        # Enhanced verification status
        hunter_verification = hunter_data.get('verification', {}).get('result', 'Not verified') if hunter_data else 'Not verified'
        print(f"  Verification Status: {hunter_verification}")
        
        if self.api_keys.get("hibp"):
            print(f"  Data Breaches: {breach_count}")
            print(f"  Paste Appearances: {paste_count}")
            print(f"  Risk Level: {self._assess_email_risk_level(breach_count, paste_count)}")
        else:
            print(f"  Data Breaches: {Fore.YELLOW}HIBP API key required{Style.RESET_ALL}")
            print(f"  Risk Level: {Fore.YELLOW}UNKNOWN (add HIBP key for assessment){Style.RESET_ALL}")

    def _display_social_profile(self, social_data: dict, username: str, full_profile: dict) -> None:
        '''
        Funzione: _display_social_profile
        Visualizza il profilo social OSINT di un username in formato leggibile.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            dict social_data -> I dati OSINT del profilo social
            str username -> L'username target
            dict full_profile -> Il profilo completo dell'entità
        Valore di ritorno:
            None -> La funzione stampa i risultati
        '''
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"SOCIAL OSINT PROFILE: {username}")
        print(f"{'='*80}{Style.RESET_ALL}")
        
        # Social platform results
        platforms = social_data.get("platforms", {})
        if platforms:
            found_platforms = []
            not_found_platforms = []
            error_platforms = []
            
            for platform, data in platforms.items():
                if isinstance(data, dict):
                    if data.get("found"):
                        found_platforms.append((platform, data))
                    elif data.get("error"):
                        error_platforms.append((platform, data))
                    else:
                        not_found_platforms.append(platform)
            
            # Found profiles
            if found_platforms:
                print(f"\n{Fore.YELLOW}[FOUND PROFILES] ({len(found_platforms)} platforms){Style.RESET_ALL}")
                for platform, data in found_platforms:
                    print(f"  ✓ {platform.upper()}")
                    print(f"    URL: {data.get('url', 'N/A')}")
                    if data.get('response_time'):
                        print(f"    Response Time: {data['response_time']:.2f}s")
                    if data.get('additional_info'):
                        for key, value in data['additional_info'].items():
                            print(f"    {key.replace('_', ' ').title()}: {value}")
                    print()
            
            # Statistics
            print(f"\n{Fore.CYAN}[STATISTICS]{Style.RESET_ALL}")
            print(f"  Total Platforms Checked: {len(platforms)}")
            print(f"  ✓ Found: {Fore.YELLOW}{len(found_platforms)}{Style.RESET_ALL}")
            print(f"  ✗ Not Found: {Fore.YELLOW}{len(not_found_platforms)}{Style.RESET_ALL}")
            print(f"  ⚠ Errors: {Fore.RED}{len(error_platforms)}{Style.RESET_ALL}")
            
            # Coverage percentage
            if len(platforms) > 0:
                coverage = (len(found_platforms) / len(platforms)) * 100
                print(f"  Coverage: {coverage:.1f}%")
            
            # Platform breakdown by category
            social_platforms = []
            professional_platforms = []
            gaming_platforms = []
            other_platforms = []
            
            for platform, data in found_platforms:
                platform_lower = platform.lower()
                if platform_lower in ['twitter', 'facebook', 'instagram', 'tiktok', 'snapchat', 'reddit']:
                    social_platforms.append(platform)
                elif platform_lower in ['linkedin', 'github', 'stackoverflow', 'behance']:
                    professional_platforms.append(platform)
                elif platform_lower in ['steam', 'twitch', 'xbox', 'playstation']:
                    gaming_platforms.append(platform)
                else:
                    other_platforms.append(platform)
            
            if any([social_platforms, professional_platforms, gaming_platforms, other_platforms]):
                print(f"\n{Fore.CYAN}[PLATFORM CATEGORIES]{Style.RESET_ALL}")
                if social_platforms:
                    print(f"  Social Media: {', '.join(social_platforms)}")
                if professional_platforms:
                    print(f"  Professional: {', '.join(professional_platforms)}")
                if gaming_platforms:
                    print(f"  Gaming: {', '.join(gaming_platforms)}")
                if other_platforms:
                    print(f"  Other: {', '.join(other_platforms)}")
            
            # Errors summary
            if error_platforms:
                print(f"\n{Fore.RED}[ERRORS ENCOUNTERED]{Style.RESET_ALL}")
                for platform, data in error_platforms[:5]:  # Show first 5 errors
                    print(f"  ⚠ {platform}: {data.get('error', 'Unknown error')}")
        
        # Additional analysis
        analysis = social_data.get("analysis", {})
        if analysis:
            print(f"\n{Fore.CYAN}[ANALYSIS]{Style.RESET_ALL}")
            if analysis.get("common_patterns"):
                print(f"  Common Patterns: {', '.join(analysis['common_patterns'])}")
            if analysis.get("risk_indicators"):
                print(f"  Risk Indicators: {', '.join(analysis['risk_indicators'])}")
            if analysis.get("activity_score"):
                print(f"  Activity Score: {analysis['activity_score']}/100")
        
        # Summary
        print(f"\n{Fore.CYAN}[SUMMARY]{Style.RESET_ALL}")
        print(f"  Username: {username}")
        print(f"  Active Profiles: {len(found_platforms) if found_platforms else 0}")
        print(f"  Digital Footprint: {self._assess_social_footprint(len(found_platforms) if found_platforms else 0)}")
        
        # Recommendations
        if found_platforms:
            print(f"\n{Fore.YELLOW}[RECOMMENDATIONS]{Style.RESET_ALL}")
            print(f"  • Review privacy settings on found profiles")
            print(f"  • Consider username variations for broader coverage")
            print(f"  • Monitor these profiles for changes over time")

    def _assess_email_risk_level(self, breach_count: int, paste_count: int) -> str:
        '''
        Funzione: _assess_email_risk_level
        Valuta il livello di rischio di un indirizzo email basandosi sui breach e paste trovati.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            int breach_count -> Numero di breach in cui è stato trovato l'email
            int paste_count -> Numero di paste in cui è stato trovato l'email
        Valore di ritorno:
            str -> Livello di rischio colorato per la visualizzazione
        '''
        total_exposures = breach_count + paste_count
        
        if total_exposures == 0:
            return f"{Fore.YELLOW}LOW{Style.RESET_ALL}"
        elif total_exposures <= 2:
            return f"{Fore.YELLOW}MEDIUM{Style.RESET_ALL}"
        elif total_exposures <= 5:
            return f"{Fore.RED}HIGH{Style.RESET_ALL}"
        else:
            return f"{Fore.RED}CRITICAL{Style.RESET_ALL}"

    def _assess_social_footprint(self, profile_count: int) -> str:
        '''
        Funzione: _assess_social_footprint
        Valuta l'impronta digitale social basandosi sul numero di profili trovati.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            int profile_count -> Numero di profili social trovati
        Valore di ritorno:
            str -> Descrizione dell'impronta digitale colorata per la visualizzazione
        '''
        if profile_count == 0:
            return f"{Fore.YELLOW}Minimal{Style.RESET_ALL}"
        elif profile_count <= 3:
            return f"{Fore.YELLOW}Low{Style.RESET_ALL}"
        elif profile_count <= 7:
            return f"{Fore.YELLOW}Moderate{Style.RESET_ALL}"
        elif profile_count <= 12:
            return f"{Fore.RED}High{Style.RESET_ALL}"
        else:
            return f"{Fore.RED}Extensive{Style.RESET_ALL}"

    def _offer_additional_actions(self, profile_data: dict, target_identifier: str) -> None:
        '''
        Funzione: _offer_additional_actions
        Presenta all'utente le opzioni di azioni aggiuntive disponibili dopo la visualizzazione di un profilo OSINT.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            dict profile_data -> Dizionario contenente i dati del profilo OSINT
            str target_identifier -> L'identificativo primario del target
        Valore di ritorno:
            None -> La funzione visualizza le opzioni
        '''
        if not profile_data or profile_data.get("error"):
            print(
                f"\n{Fore.YELLOW}Nessuna azione aggiuntiva disponibile a causa di un errore nel profilo.{Style.RESET_ALL}"
            )
        else:
            print(f"\n{Fore.CYAN}Azioni disponibili per '{target_identifier}':{Style.RESET_ALL}")
            print(f"1. Esporta l'analisi")
            print(f"2. Torna al menu OSINT")

        pass

    # Funzioni menu main.py

    def get_all_table_names(self, db_name: str) -> list[str]:
        """Recupera i nomi di tutte le tabelle nel database."""
        query = """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """
        results = self.execute_query(query, db_name=db_name)
        return [row['name'] for row in results] if results else []

    def backup_database(self, db_name: str) -> tuple[bool, str]:
        """
        Crea un backup del database.
        Returns:
            tuple[bool, str]: (successo, percorso_backup o messaggio_errore)
        """
        if db_name not in self.databases:
            return False, f"Database {db_name} non trovato"

        try:
            source_path = Path(self.databases[db_name])
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = source_path.parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            backup_path = backup_dir / f"{source_path.stem}_{timestamp}.db"
            
            # Assicurati che tutte le modifiche siano salvate
            if db_name in self.connections and self.connections[db_name]:
                self.connections[db_name].commit()
            
            import shutil
            shutil.copy2(source_path, backup_path)
            
            return True, str(backup_path)
        except Exception as e:
            logger.error(f"Errore backup database {db_name}: {e}")
            return False, str(e)

    def clear_table(self, table_name: str, db_name: str) -> bool:
        """Svuota una tabella specifica."""
        try:
            with self.transaction(db_name) as cursor:
                cursor.execute(f"DELETE FROM {table_name}")
            return True
        except Exception as e:
            logger.error(f"Errore svuotamento tabella {table_name}: {e}")
            return False

    def clear_all_tables(self, db_name: str) -> tuple[bool, list[str]]:
        """
        Svuota tutte le tabelle utente nel database.
        Returns:
            tuple[bool, list[str]]: (successo, lista_tabelle_svuotate)
        """
        cleared_tables = []
        try:
            tables = self.get_all_table_names(db_name)
            with self.transaction(db_name) as cursor:
                for table in tables:
                    cursor.execute(f"DELETE FROM {table}")
                    cleared_tables.append(table)
            return True, cleared_tables
        except Exception as e:
            logger.error(f"Errore svuotamento tabelle in {db_name}: {e}")
            return False, cleared_tables

    def get_database_size(self, db_name: str) -> float:
        """Restituisce la dimensione del database in MB."""
        try:
            size = Path(self.databases[db_name]).stat().st_size
            return size / (1024 * 1024)  # Converti in MB
        except Exception as e:
            logger.error(f"Errore lettura dimensione database {db_name}: {e}")
            return 0.0

    def clear_cache(self) -> None:
        '''Pulisce la cache delle richieste HTTP.'''
        self.fetcher.clear_cache()

    def find_brand_social_profiles(self, domain_or_brand_name: str) -> Dict[str, Any]:
        '''
        Funzione: find_brand_social_profiles
        Ricerca profili social associati a un dominio o nome di brand.
        
        Args:
            domain_or_brand_name: Il dominio o nome di brand da cercare
            
        Returns:
            Un dizionario contenente i profili social trovati e eventuali errori
        '''
        self.logger.info(f"Starting brand social profile search for: {domain_or_brand_name}")
        return find_brand_social_profiles(domain_or_brand_name, self.logger, self.dirs)