# src/scraper/utils/clients.py
#  Contiene funzioni per interagire con API esterne o librerie specifiche per ottenere dati (WHOIS, DNS, Shodan, Hunter.io, HIBP)
import requests
import json
import logging
import shodan # Per Shodan
from dns import resolver as dns_resolver # Per DNS
from typing import List, Dict, Any, Optional
from datetime import datetime # Per la gestione delle date in WHOIS
import sys
import time
from waybackpy import WaybackMachineCDXServerAPI
from colorama import Fore, Style

# È una buona pratica avere un logger per modulo
logger = logging.getLogger(__name__)


# === Wayback Machine Client ===
def fetch_wayback_snapshots(url: str, limit: int = 5) -> Dict [str, Any]:
    '''
    Funzione: fetch_wayback_snapshots
    Recupera una lista degli ultimi snapshot da Wayback Machine per un dato URL.
    Parametri formali:
        url: L'URL per cui cercare gli snapshot
        limit: Il numero massimo di snapshot da recuperare (default 5)
    Valore di ritorno:
        dict[str, Any] -> Un dizionario contenente i dati degli snapshot o un messaggio di errore
    '''

    try:
        logger.debug(f"Fetching Wayback Machine snapshots for URL: {url} with limit {limit}")
        print(f"Cercando snapshot per {url} con limite {limit}...")  # Per debug
        cdx_api = WaybackMachineCDXServerAPI(url, user_agent= "Browsint Research Bot")
        cdx_api.limit = limit  # Imposta il limite di snapshot da recuperare
        snapshots = cdx_api.snapshots() 

        if not snapshots:
            logger.info(f"No snapshots found for {url}.")
            return {"info": f"No snapshots found for {url}."}

        # Converti i risultati in un formato più leggibile
        results = []
        for s in snapshots:
            results.append({
                "timestamp": s.timestamp,
                "url": s.archive_url, # URL dell'archivio effettivo
                "original_url": s.original,
                "status_code": s.statuscode,
                "mime_type": s.mimetype,
                "diges": s.digest  # Hash del contenuto
            })

            print(f"Trovato snapshot numero {len(results)}:{s.archive_url}")
            if len(results) > 5: break

        logger.debug(f"Found {len(results)} snapshots for {url}.")
        return {"snapshots": results}

    except requests.exceptions.RequestException as e:
        logger.warning(f"Network error fetching Wayback Machine data for {url}: {e}")
        return {"error": f"Si è verificato un errore di rete durante il lookup su Wayback Machine: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error during Wayback Machine lookup for {url}: {e}", exc_info=True)
        return {"error": f"Si è verificato il seguente errore durante l'esecuzione del Wayback Machine lookup: {e}"}
    

# === Hunter.io Client ===
def fetch_hunterio(email: str, api_key: Optional[str]) -> Dict[str, Any]:
    '''
    Funzione: _fetch_hunterio
    Recupera informazioni su un indirizzo email dall'API di Hunter.io.
    Parametri formali:
        self -> Riferimento all'istanza della classe
        str email -> L'indirizzo email da cercare su Hunter.io
    Valore di ritorno:
        dict[str, Any] -> Un dizionario contenente i dati di Hunter.io o un errore
    '''
    if not api_key:
        logger.info("Hunter.io API key not provided. Skipping Hunter.io lookup.")
        return {"error": "API key for Hunter.io not provided"}

    try:
        logger.debug(f"Fetching Hunter.io data for {email}")
        url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={api_key}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Solleva un'eccezione per status codes 4xx/5xx
        
        if response.text:
            hunter_data = response.json()
            logger.debug(f"Hunter.io response for {email}: {hunter_data}")
            return hunter_data
        logger.debug(f"Hunter.io returned empty response for {email}.")
        return {"error": "Empty response from Hunter.io"}
        
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"Hunter.io API HTTP error for {email}: {http_err} - Response: {response.text if 'response' in locals() else 'N/A'}")
        return {"error": f"HTTP error {http_err.response.status_code} from Hunter.io: {response.text if 'response' in locals() else str(http_err)}"}
    except requests.exceptions.ReadTimeout as e:
        logger.error(f"Hunter.io API request timed out for {email}: {e}")
        return {"error": f"Timeout error durning Hunter.io request: {str(e)}"}
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Hunter.io API request error for {email}: {req_err}", exc_info=True)
        return {"error": f"Request error during Hunter.io fetch: {str(req_err)}"}
    except json.JSONDecodeError as json_err:
        response_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'N/A'
        logger.error(
            f"Hunter.io API JSON decode error for {email}: {json_err} - Response was: {response_text}",
            exc_info=True
        )
        return {"error": f"JSON decode error from Hunter.io: {str(json_err)}"}
    except Exception as e:
        logger.error(f"Hunter.io API unexpected error for {email}: {e}", exc_info=True)
        return {"error": f"Unexpected API error during Hunter.io fetch: {str(e)}"}

# === Have I Been Pwned (HIBP) Client ===
def check_email_breaches(email: str, api_key: Optional[str]) -> List[Dict[str, Any]]:
    '''
    Funzione: _check_email_breaches
    Controlla se un indirizzo email è apparso in data breach noti utilizzando l'API di Have I Been Pwned (HIBP).
    Parametri formali:
        self -> Riferimento all'istanza della classe
        str email -> L'indirizzo email da controllare su HIBP
    Valore di ritorno:
        list[dict[str, Any]] -> Una lista di dizionari rappresentanti i breach trovati, o una lista vuota in caso di nessun breach o errore
    '''
    if not api_key:
        logger.info("HIBP API key not configured. Skipping breach check.")
        return [] # Restituisce lista vuota se la chiave non c'è

    try:
        logger.debug(f"Checking HIBP for breaches for email: {email}")
        response = requests.get(
            f"https://haveibeenpwned.com/api/v3/breachedaccount/{email.strip()}",
            headers={"hibp-api-key": api_key, "User-Agent": "BrowsintOSINTTool/1.0"}, # È buona norma specificare un User-Agent
            timeout=15,
        )
        if response.status_code == 200:
            logger.debug(f"HIBP data found for {email}")
            return response.json()
        elif response.status_code == 404:
            logger.debug(f"No breaches found for {email} on HIBP (404).")
            return []
        else:
            logger.warning(
                f"HIBP API returned status {response.status_code} for {email}: {response.text[:200]}"
            )
            return [] # Restituisce lista vuota in caso di altri errori API
    except requests.exceptions.RequestException as e:
        logger.error(f"HIBP check network/request error for {email}: {e}", exc_info=True)
        return []
    except json.JSONDecodeError as e:
        response_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'N/A'
        logger.error(
            f"HIBP check JSON decode error for {email}: {e} - Response: {response_text}",
            exc_info=True
        )
        return []
    except Exception as e:
        logger.error(f"HIBP check unexpected error for {email}: {e}", exc_info=True)
        return []

# === WHOIS Client ===
def fetch_whois(target: str) -> Dict[str, Any]:
    '''
    Funzione: _fetch_whois
    Recupera i dati WHOIS di un dominio o indirizzo IP utilizzando la libreria python-whois o ipwhois.
    Parametri formali:
        str target -> Il dominio o indirizzo IP per cui recuperare i dati WHOIS
    Valore di ritorno:
        dict[str, Any] -> Un dizionario contenente i dati WHOIS o un errore
    '''
    try:
        # Verifica se l'input è un IP
        import ipaddress
        try:
            ip = ipaddress.ip_address(target)
            is_ip = True
        except ValueError:
            is_ip = False

        if is_ip:
            from ipwhois import IPWhois
            logger.debug(f"Fetching IP WHOIS data for: {target}")
            
            obj = IPWhois(target)
            whois_info = obj.lookup_rdap(depth=1)
            
            if not whois_info:
                logger.warning(f"IP WHOIS lookup for {target} returned no data.")
                return {"error": "IP WHOIS lookup returned no data."}

            # Standardizza i campi per IP WHOIS
            processed_info = {
                "ip": target,
                "asn": whois_info.get("asn"),
                "asn_description": whois_info.get("asn_description"),
                "network": whois_info.get("network", {}).get("cidr"),
                "name": whois_info.get("network", {}).get("name"),
                "country": whois_info.get("network", {}).get("country"),
                "abuse_emails": whois_info.get("network", {}).get("abuse_emails", []),
                "tech_emails": whois_info.get("network", {}).get("tech_emails", []),
                "admin_emails": whois_info.get("network", {}).get("admin_emails", []),
                "registration_date": whois_info.get("network", {}).get("start_address"),
                "last_updated": whois_info.get("network", {}).get("last_changed"),
                "registrar": whois_info.get("network", {}).get("registrar"),
                "raw": whois_info  # Mantieni anche i dati raw per riferimento
            }

            # Standardizza le date
            for key in ["registration_date", "last_updated"]:
                if isinstance(processed_info.get(key), datetime):
                    processed_info[key] = processed_info[key].isoformat()

            logger.debug(f"Successfully processed IP WHOIS data for {target}")
            return processed_info

        else:
            import whois  # Importa qui per rendere la dipendenza da python-whois opzionale per il modulo
            logger.debug(f"Fetching domain WHOIS data for: {target}")
            whois_info = whois.whois(target)

            if not whois_info:
                logger.warning(f"WHOIS lookup for {target} returned no data.")
                return {"error": "WHOIS lookup returned no data."}

            # Converti l'oggetto in dizionario se non lo è già
            if not isinstance(whois_info, dict):
                processed_info = {}
                # Estrai solo gli attributi non nulli
                for key, value in vars(whois_info).items():
                    if value is not None and key != "status":  # Escludiamo lo status che gestiamo separatamente
                        processed_info[key] = value
            else:
                processed_info = {k: v for k, v in whois_info.items() if v is not None and k != "status"}

            # Gestisci lo status separatamente perché potrebbe essere una lista o una stringa
            status = whois_info.status
            if status:
                if isinstance(status, (list, tuple)):
                    processed_info["status"] = [str(s) for s in status if s]
                else:
                    processed_info["status"] = [str(status)]

            # Standardizza i campi delle date
            date_fields = ["creation_date", "expiration_date", "updated_date"]
            for field in date_fields:
                value = processed_info.get(field)
                if value:
                    if isinstance(value, (list, tuple)):
                        # Se è una lista di date, prendi la più recente
                        dates = [d for d in value if isinstance(d, datetime)]
                        if dates:
                            processed_info[field] = max(dates).isoformat()
                    elif isinstance(value, datetime):
                        processed_info[field] = value.isoformat()

            # Standardizza i name servers
            name_servers = processed_info.get("name_servers", [])
            if name_servers:
                if isinstance(name_servers, (list, tuple)):
                    processed_info["name_servers"] = [str(ns).lower() for ns in name_servers if ns]
                else:
                    processed_info["name_servers"] = [str(name_servers).lower()]

            # Standardizza gli indirizzi email
            emails = processed_info.get("emails", [])
            if emails:
                if isinstance(emails, (list, tuple)):
                    processed_info["emails"] = [str(e).lower() for e in emails if e]
                else:
                    processed_info["emails"] = [str(emails).lower()]

            if not any(processed_info.get(k) for k in ["domain_name", "registrar", "creation_date", "name_servers"]):
                logger.warning(f"WHOIS lookup for {target} returned incomplete data.")
                return {"error": "WHOIS lookup returned incomplete data."}

            logger.debug(f"Successfully processed domain WHOIS data for {target}")
            return processed_info

    except Exception as e:
        logger.error(f"Error during WHOIS lookup for {target}: {e}", exc_info=True)
        return {"error": f"WHOIS lookup failed: {str(e)}"}

# === Shodan Client ===
def fetch_shodan(ip_addresses: List[str], api_key: Optional[str]) -> Dict[str, Any]:
    '''
    Funzione: _fetch_shodan
    Recupera dati da Shodan per un dominio e i suoi indirizzi IP associati.        Parametri formali:
        self -> Riferimento all'istanza della classe            
        str domain -> Il dominio associato (per logging/contesto)
        List[str] ip_addresses -> Lista degli indirizzi IP per cui eseguire la lookup Shodan
    Valore di ritorno:
       Dict[str, Any] -> Un dizionario contenente i dati Shodan o un errore
    '''
    if not api_key:
        logger.warning("Shodan API key not configured. Skipping Shodan lookup.")
        return {"error": "API key for Shodan not provided"}
    if not ip_addresses:
        logger.debug("No IP addresses provided for Shodan lookup.")
        return {"info": "No IP addresses provided", "data_by_ip": {}, "summary": {}}

    results: Dict[str, Any] = {
        "ips_queried": ip_addresses,
        "data_by_ip": {}, # Dati grezzi per ogni IP
        "summary": {      # Riepilogo aggregato
            "ports": set(),
            "hostnames": set(),
            "organizations": set(),
            "isps": set(),
            "vulnerabilities": set() # Per i CVE o 'vulns'
        }
    }

    try:
        logger.debug(f"Initializing Shodan API for IPs: {ip_addresses}")
        api = shodan.Shodan(api_key)

        for ip in ip_addresses:
            try:
                logger.debug(f"Querying Shodan for IP: {ip}")
                host_info = api.host(ip)
                results["data_by_ip"][ip] = host_info # Salva tutti i dati per quell'IP

                # Aggiorna il riepilogo
                if host_info.get("ports"):
                    results["summary"]["ports"].update(host_info["ports"])
                if host_info.get("hostnames"):
                    results["summary"]["hostnames"].update(host_info["hostnames"])
                if host_info.get("org"):
                    results["summary"]["organizations"].add(host_info["org"])
                if host_info.get("isp"):
                    results["summary"]["isps"].add(host_info["isp"])
                if host_info.get("vulns"): # 'vulns' è la chiave usata da Shodan per i CVE
                    results["summary"]["vulnerabilities"].update(host_info["vulns"])
            
            except shodan.APIError as e_ip: # Errore specifico per un IP (es. IP non trovato, rate limit)
                logger.warning(f"Shodan API Error for IP {ip}: {e_ip}")
                results["data_by_ip"][ip] = {"error": str(e_ip), "status_code": e_ip.value if hasattr(e_ip, 'value') else None}
            except Exception as e_host: # Errore generico per un singolo IP
                logger.error(f"Unexpected error fetching Shodan data for IP {ip}: {e_host}", exc_info=True)
                results["data_by_ip"][ip] = {"error": f"Unexpected error: {str(e_host)}"}
        
        # Converti i set in liste ordinate per la serializzazione JSON e una migliore leggibilità
        results["summary"]["ports"] = sorted(list(results["summary"]["ports"]))
        results["summary"]["hostnames"] = sorted(list(results["summary"]["hostnames"]))
        results["summary"]["organizations"] = sorted(list(results["summary"]["organizations"]))
        results["summary"]["isps"] = sorted(list(results["summary"]["isps"]))
        results["summary"]["vulnerabilities"] = sorted(list(results["summary"]["vulnerabilities"]))

        logger.debug(f"Shodan lookup successful for IPs: {ip_addresses}")
        return results

    except shodan.APIError as e: # Errore API Shodan generale (es. chiave API non valida all'init)
        logger.error(f"General Shodan API error (e.g., invalid API key): {e}", exc_info=True)
        return {"error": f"Shodan API error: {str(e)}"}
    except Exception as e_main: # Catch-all per errori imprevisti durante l'inizializzazione o l'elaborazione
        logger.error(f"Failed to fetch Shodan data due to an unexpected error: {e_main}", exc_info=True)
        return {"error": f"Unexpected Shodan client error: {str(e_main)}"}

# === DNS Client ===
def fetch_dns_records(domain: str) -> Dict[str, List[str]]:
    '''
    Funzione: _fetch_dns_records
    Recupera i record DNS per un dominio utilizzando la libreria dnspython.
    Parametri formali:
        self -> Riferimento all'istanza della classe
        str domain -> Il dominio per cui recuperare i record DNS
    Valore di ritorno:
        dict[str, list[str]] -> Un dizionario contenente i record DNS per vari tipi (A, MX, TXT, ecc.)
    '''
    records: Dict[str, List[str]] = {}
    resolver = dns_resolver.Resolver()
    resolver.nameservers = ['8.8.8.8', '1.1.1.1', '9.9.9.9'] # Google, Cloudflare, Quad9
    resolver.timeout = 3.0 # Timeout per singola query
    resolver.lifetime = 7.0 # Timeout totale per la risoluzione

    # Tipi di record comuni da interrogare
    record_types = ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME", "SRV", "CAA", "PTR"] # PTR è più per IP ma lo includo
    logger.debug(f"Fetching DNS records for domain: {domain} (Types: {', '.join(record_types)})")

    for rtype in record_types:
        try:
            logger.debug(f"Querying {rtype} records for {domain}")
            answers = resolver.resolve(domain, rtype)
            current_rtype_records = []
            if rtype == "MX":
                current_rtype_records = sorted([f"{r.preference} {str(r.exchange).rstrip('.')}" for r in answers])
            elif rtype == "SOA":
                # Di solito c'è un solo record SOA
                if answers:
                    r = answers[0]
                    current_rtype_records = [
                        f"mname={str(r.mname).rstrip('.')} rname={str(r.rname).rstrip('.')} serial={r.serial} refresh={r.refresh} retry={r.retry} expire={r.expire} minimum={r.minimum}"
                    ]
            elif rtype == "TXT":
                # Concatena le stringhe TXT se sono spezzate (come da RFC)
                current_rtype_records = ["".join(s.decode("utf-8", "ignore") for s in r.strings) for r in answers]
            elif rtype == "SRV":
                current_rtype_records = sorted([f"priority={r.priority} weight={r.weight} port={r.port} target={str(r.target).rstrip('.')}" for r in answers])
            elif rtype == "CAA":
                current_rtype_records = [f"flags={r.flags} tag={r.tag.decode()} value=\"{r.value.decode()}\"" for r in answers]
            elif rtype == "PTR" and domain.endswith(".in-addr.arpa"): # Solo per reverse DNS
                 current_rtype_records = sorted([str(r).rstrip(".") for r in answers])
            elif rtype != "PTR": # A, AAAA, NS, CNAME
                current_rtype_records = sorted([str(r).rstrip(".") for r in answers])
            
            if current_rtype_records:
                records[rtype] = current_rtype_records
            # Non aggiungere una chiave vuota se non ci sono record di quel tipo (tranne errore)
            
            logger.debug(f"Found {len(current_rtype_records)} {rtype} records for {domain}")

        except dns_resolver.NoAnswer:
            logger.debug(f"No {rtype} records found for {domain} (NoAnswer).")
            # Non è un errore, semplicemente non ci sono record di quel tipo
            records[rtype] = [] # Indica esplicitamente che non ci sono record di questo tipo
        except dns_resolver.NXDOMAIN:
            logger.warning(f"Domain {domain} does not exist (NXDOMAIN) when querying for {rtype}.")
            # Se il dominio non esiste, non ha senso continuare
            return {"error": f"NXDOMAIN - Domain {domain} does not exist", "details": records}
        except dns_resolver.Timeout:
            logger.warning(f"DNS query timeout for {domain} [{rtype}]")
            records[rtype] = [f"Error: DNS query timed out for {rtype}"]
        except dns_resolver.NoNameservers:
            logger.error(f"No nameservers available or configured for DNS resolution of {domain} [{rtype}].")
            return {"error": f"No nameservers available for {domain}", "details": records}
        except Exception as e: # Altre eccezioni di dnspython o generiche
            logger.error(f"DNS query for {domain} [{rtype}] failed: {e}", exc_info=True)
            records[rtype] = [f"Error fetching {rtype}: {str(e)}"]

    if not records and not any(isinstance(v, list) and any("Error:" in e_str for e_str in v) for v in records.values()):
        logger.warning(f"No DNS records of any queried type found for {domain} and no specific errors reported during DNS resolution.")
    elif not records and any(isinstance(v, list) and any("Error:" in e_str for e_str in v) for v in records.values()):
         logger.warning(f"DNS resolution for {domain} resulted in errors but no data: {records}")
    
    if not records: # Se dopo tutti i tentativi non abbiamo nessun record (neanche liste vuote per NoAnswer)
        return {"info": f"No DNS records found for domain {domain} across all queried types."}
        
    return records