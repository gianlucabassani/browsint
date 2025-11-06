# scraper/utils/osint_sources.py

import logging
import re
import time
import random
from typing import Any, Dict, List, Set, Optional
import requests
from bs4 import BeautifulSoup
import phonenumbers
from colorama import Fore, Style
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Importa le utility già esistenti per le chiamate API e l'estrazione/filtraggio
from .clients import fetch_whois, fetch_dns_records, fetch_shodan, fetch_hunterio, check_email_breaches, fetch_wayback_snapshots, _safe_get
from .extractors import extract_emails, filter_emails, extract_phone_numbers, filter_phone_numbers

logger = logging.getLogger("osint.sources")


def _parse_sherlock_stdout(stdout: str, username: str, include_username: bool = False) -> dict:
    """Parse sherlock stdout lines into a profiles dict.

    Returns a dict mapping site -> info dict (url, exists, confidence, optionally username).
    """
    results: dict = {}
    try:
        for line in stdout.splitlines():
            if "[+]" in line:
                try:
                    # Example: [+] Reddit: https://www.reddit.com/user/username
                    site = line.split("[+]", 1)[1].strip().split(":")[0].strip()
                    url = line.split(":", 1)[1].strip()
                    info = {
                        "url": url,
                        "status": "Claimed",
                        "exists": True,
                        "confidence": 1.0,
                    }
                    if include_username:
                        info["username"] = username
                    results[site] = info
                except Exception:
                    logger.debug(f"Failed to parse sherlock line: {line}")
                    continue
    except Exception:
        logger.debug("Error parsing sherlock stdout")
    return results

# === Funzioni per Fetching Dati Dominio ===

# Usato dal OSINTExtractor per raccogliere dati dominio/IP
def fetch_domain_osint(target: str, api_keys: Dict[str, str], logger) -> dict[str, Any]:
    '''
    Funzione: fetch_domain_osint
    Raccoglie dati OSINT per un dominio o IP da varie fonti (WHOIS, DNS, Shodan).

    Args:
        target: Il dominio o IP da processare
        api_keys: Dizionario contenente le API keys necessarie
        logger: L'istanza del logger

    Ritorno:
        dict[str, Any]        → Dizionario con i dati raccolti da WHOIS, DNS e Shodan (se possibile)
    '''
    result: dict[str, Any] = {}
    logger.info(f"OSINT scan avviata per: {target}")

    # Verifica se l'input è un IP
    try:
        import ipaddress
        is_ip = bool(ipaddress.ip_address(target))
    except ValueError:
        is_ip = False

    # WHOIS
    logger.debug(f"Eseguo WHOIS lookup per {target}...")
    whois_data = fetch_whois(target)
    if whois_data and not whois_data.get("error"):
        result["whois"] = whois_data
        logger.debug("WHOIS completato con successo.")
    elif whois_data and whois_data.get("error"):
        logger.warning(f"WHOIS fallito per {target}: {whois_data['error']}")
    else:
        logger.warning(f"Nessun dato WHOIS trovato per {target}.")

    # Se non è un IP, procedi con DNS lookup
    if not is_ip:
        # DNS
        logger.debug(f"Eseguo DNS lookup per {target}...")
        dns_data = fetch_dns_records(target)
        if dns_data and not dns_data.get("error"):
            result["dns"] = dns_data
            logger.debug("DNS completato con successo.")

            # SHODAN (se presenti A records e API key)
            shodan_api_key = api_keys.get("shodan")
            if shodan_api_key:
                resolved_ips: list[str] = dns_data.get("A", [])
                if resolved_ips:
                    try:
                        user_choice = input(f"\n{Fore.YELLOW}Vuoi eseguire la scansione Shodan per {target}? (s/N): {Style.RESET_ALL}").lower()
                    except Exception:
                        user_choice = 'n'  # fallback in ambienti non interattivi

                    if user_choice == 's':
                        logger.info(f"Eseguo Shodan lookup sugli IP: {resolved_ips}")
                        shodan_data = fetch_shodan(resolved_ips, shodan_api_key)
                        if shodan_data and not shodan_data.get("error"):
                            result["shodan"] = shodan_data
                            logger.debug("Shodan completato con successo.")
                        elif shodan_data and shodan_data.get("error"):
                            logger.warning(f"Shodan fallito: {shodan_data['error']}")
                        else:
                            logger.warning("Shodan non ha restituito dati.")
                    else:
                        logger.info("Scansione Shodan saltata dall'utente.")
                else:
                    logger.debug("Nessun record A trovato. Skipping Shodan.")
            else:
                logger.info("Chiave API Shodan mancante. Skipping Shodan.")

        elif dns_data and dns_data.get("error"):
            logger.warning(f"DNS lookup fallito per {target}: {dns_data['error']}")
        else:
            logger.warning("DNS lookup non ha restituito dati o ha incontrato un errore imprevisto.")
    else:
        # Se è un IP, esegui direttamente Shodan
        shodan_api_key = api_keys.get("shodan")
        if shodan_api_key:
            try:
                user_choice = input(f"\n{Fore.YELLOW}Vuoi eseguire la scansione Shodan per l'IP {target}? (s/N): {Style.RESET_ALL}").lower()
            except Exception:
                user_choice = 'n'  # fallback in ambienti non interattivi

            if user_choice == 's':
                logger.info(f"Eseguo Shodan lookup per l'IP: {target}")
                shodan_data = fetch_shodan([target], shodan_api_key)
                if shodan_data and not shodan_data.get("error"):
                    result["shodan"] = shodan_data
                    logger.debug("Shodan completato con successo.")
                elif shodan_data and shodan_data.get("error"):
                    logger.warning(f"Shodan fallito: {shodan_data['error']}")
                else:
                    logger.warning("Shodan non ha restituito dati.")
            else:
                logger.info("Scansione Shodan saltata dall'utente.")
        else:
            logger.info("Chiave API Shodan mancante. Skipping Shodan.")

     # === Wayback Machine ===
    if not is_ip:
        wayback_data = fetch_wayback_snapshots(target)
        if wayback_data and not wayback_data.get("error"):
            result["wayback_machine"] = wayback_data
            logger.debug("Wayback Machine completato con successo.")
        else:
            logger.warning(f"Wayback Machine lookup fallito per {target}: {wayback_data.get('error', 'Nessun dato trovato')}")
            result["wayback_machine"] = {"error": "Nessun dato trovato o errore durante il fetch"}
    else:
        logger.info("Wayback Machine non applicabile per gli IP. Skipping Wayback Machine.")
        result["wayback_machine"] = {"error": "Not applicable for IP addresses"}
    
        
    logger.debug(f"Raccolta OSINT per {target} completata. Risultati: {result}")
    return result


# === Funzioni per Fetching Dati Email ===

# Usato dal OSINTExtractor per raccogliere dati email
def fetch_email_osint(email: str, api_keys: Dict[str, str], logger) -> Dict[str, Any]:
    '''
    Funzione: fetch_email_osint
    Processa l'estrazione di dati per un indirizzo email da varie fonti (Hunter.io, HIBP).

    Args:
        email: L'indirizzo email da processare
        api_keys: Dizionario contenente le API keys necessarie
        logger: L'instance del logger

    Returns:
        Un dizionario contenente i dati raccolti dalle varie fonti
    '''
    result: Dict[str, Any] = {}
    logger.info(f"Running email OSINT fetch for {email}...")

    # Hunter.io lookup
    hunter_api_key = api_keys.get("hunterio")
    if hunter_api_key:
        hunter_data = fetch_hunterio(email, hunter_api_key)
        if hunter_data and not hunter_data.get("error"):
            result["hunterio"] = hunter_data
            logger.debug(f"Hunter.io data fetched for {email}")
        elif hunter_data and hunter_data.get("error"):
            logger.warning(f"Hunter.io lookup failed for {email}: {hunter_data['error']}")
        else:
            logger.warning(f"Hunter.io lookup for {email} returned no data.")
    else:
        logger.info(f"Hunter.io API key not provided, skipping Hunter.io lookup for {email}")
        result["hunterio"] = {"error": "API key not provided"}

    # HIBP lookup
    hibp_api_key = api_keys.get("hibp")
    if hibp_api_key:
        breaches_data = check_email_breaches(email, hibp_api_key)
        if breaches_data:
            result["breaches"] = breaches_data
            if not breaches_data:
                logger.debug(f"No breaches found for {email} on HIBP.")
            else:
                logger.debug(f"Found {len(breaches_data)} breaches for {email} on HIBP.")
        else:
            logger.debug(f"HIBP check for {email} returned no data or encountered an issue.")
    else:
        logger.info(f"HIBP API key not provided, skipping breach check for {email}")
        result["breaches"] = {"error": "HIBP API key not provided"}
        
        # Add basic email analysis when HIBP is not available
        domain = email.split('@')[1] if '@' in email else 'Unknown'
        result["basic_analysis"] = {
            "domain": domain,
            "provider_type": "public" if domain.lower() in [
                'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 
                'protonmail.com', 'icloud.com', 'aol.com', 'live.com'
            ] else "custom",
            "note": "Limited analysis without HIBP API key"
        }

    logger.info(f"Finished email OSINT fetch for {email}. Result keys: {list(result.keys())}")
    return result

# === Funzioni per Social Scan Username ===

# Usato dal OSINTExtractor per raccogliere dati social
def fetch_social_osint(username: str, logger, dirs: Dict[str, Path]) -> Dict[str, Any]:
    '''
    Funzione: fetch_social_osint
    Esegue una scansione della presenza di un username su piattaforme social usando Sherlock.
    
    Args:
        username: L'username da ricercare
        logger: L'istanza del logger
        dirs: Dizionario contenente i percorsi delle directory del progetto
        
    Returns:
        Dizionario contenente i risultati della scansione social
    '''
    try:
        # Sanitizzazione dell'input
        username = username.strip()
        if not username:
            logger.warning("Empty username provided for social scan.")
            return {"error": "Username cannot be empty", "profiles": {}}

        # Esegui sherlock e cattura l'output direttamente
        logger.info(f"Starting Sherlock scan for username: {username}")
        
        # Assicurati che la directory esista
        output_dir = dirs["osint_usernames"]
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Genera il nome del file di output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"sherlock_{username}_{timestamp}.txt"
        
        cmd = [
            "sherlock",
            username,
            "--print-found",
            "--timeout", "10",
            "--output", str(output_file)
        ]
        
        try:
            # Esegui sherlock e cattura l'output
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.debug(f"Sherlock stdout: {process.stdout}")
            if process.stderr:
                logger.debug(f"Sherlock stderr: {process.stderr}")
            
            # Parse Sherlock stdout using helper
            results = _parse_sherlock_stdout(process.stdout, username, include_username=False)

            formatted_results = {
                "profiles": results,
                "summary": {
                    "username": username,
                    "platforms_checked": len(process.stdout.splitlines()),
                    "profiles_found": len(results),
                    "report_file": str(output_file),
                },
            }

            return formatted_results
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Sherlock execution failed: {e.stderr if e.stderr else e.stdout}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "profiles": {},
                "raw_output": e.stdout if e.stdout else "No output available"
            }
            
    except Exception as e:
        error_msg = f"Error in social scan: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg, "profiles": {}}

# === Funzioni per Ricerca Profili Social di Brand/Dominio ===

# Usato dal OSINTExtractor per raccogliere dati social di brand
def find_brand_social_profiles(domain_or_brand_name: str, logger, dirs: Dict[str, Path]) -> Dict[str, Any]:
    '''
    Funzione: find_brand_social_profiles
    Ricerca profili social associati a un dominio o nome di brand usando Sherlock.

    Args:
        domain_or_brand_name: Il dominio o nome di brand da cercare
        logger: L'istanza del logger
        dirs: Dizionario contenente i percorsi delle directory del progetto

    Returns:
        Un dizionario contenente i profili social trovati e eventuali errori
    '''
    try:
        # Sanitizza l'input
        if not domain_or_brand_name or not domain_or_brand_name.strip():
            return {"error": "Domain or brand name cannot be empty", "profiles": {}}

        # Estrai il nome del brand dal dominio se necessario
        brand_name = domain_or_brand_name.split(".")[0] if "." in domain_or_brand_name else domain_or_brand_name
        logger.info(f"Starting brand social profile search for: {brand_name}")
        
        # Assicurati che la directory esista
        output_dir = dirs["osint_usernames"]
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Genera il nome del file di output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"sherlock_{brand_name}_{timestamp}.txt"
        
        cmd = [
            "sherlock",
            brand_name,
            "--print-found",
            "--timeout", "10",
            "--output", str(output_file)
        ]
        
        try:
            # Esegui sherlock e cattura l'output
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.debug(f"Sherlock stdout: {process.stdout}")
            if process.stderr:
                logger.debug(f"Sherlock stderr: {process.stderr}")
            
            # Parse Sherlock stdout using helper
            results = _parse_sherlock_stdout(process.stdout, brand_name, include_username=True)

            formatted_results = {
                "profiles": results,
                "summary": {
                    "username": brand_name,
                    "platforms_checked": len(process.stdout.splitlines()),
                    "profiles_found": len(results),
                    "report_file": str(output_file),
                },
            }

            return formatted_results
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Sherlock execution failed: {e.stderr if e.stderr else e.stdout}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "profiles": {},
                "raw_output": e.stdout if e.stdout else "No output available"
            }
            
    except Exception as e:
        error_msg = f"Error in social scan: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg, "profiles": {}}


# === Funzioni per Estrazione Contatti da Sito Web ===

# Usato dal OSINTExtractor per raccogliere contatti da sito web
def fetch_website_contacts(domain: str, ) -> Dict[str, List[str]]:
    '''
    Funzione: fetch_website_contacts
    Estrae informazioni di contatto (email, telefoni) dalle pagine comuni di un sito web.

    Args:
        domain: Il dominio del sito da cui estrarre i contatti
        logger: L'istanza del logger

    Returns:
        Un dizionario contenente le liste di email e numeri di telefono trovati e filtrati
    '''
    logger.info(f"Extracting contacts from website: {domain}")
    contacts = {"emails": set(), "phone_numbers": set()}

    pages_to_check_paths = [
        "", # Homepage
        "/contact",
        "/contact-us",
        "/contatti",
        "/contacto",
        "/about",
        "/about-us",
        "/chi-siamo",
        "/sobre-nos",
        "/privacy-policy",
        "/terms-of-service",
         "/impressum", 
         "/direttiva-cookies"
         "/terms-and-conditions",
        "/legal-notice",
        "/faq",
        "/help",
        "/support",
        "/customer-service",
        "/customer-support",
        "/team",
        "/staff",
        "/our-team",
        "/our-staff",
        "/team-members",
        "/team-staff",
        "/team-membership",
        "/team-staff-members",
        "/team-contacts",
        "/team-contact",
        "/team-contact-us",
        "/team-contacto",
        "/team-chi-siamo",
        "/team-about",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    for path in pages_to_check_paths:
        # Try both HTTPS and HTTP, but prefer HTTPS
        urls_to_try = [f"https://{domain}{path}"]
        if not path.startswith("http"): # Avoid adding http scheme if path is already a full URL
             urls_to_try.append(f"http://{domain}{path}")


        for url in urls_to_try:
            try:
                # Use a timeout and handle redirects
                response = _safe_get(url, headers=headers, timeout=10, verify=False, allow_redirects=True)

                # Only process if the request was successful (2xx status code)
                if response.status_code >= 200 and response.status_code < 300:
                    logger.debug(f"Successfully fetched {response.url} (original: {url}) with status {response.status_code}")
                    page_content = response.text

                    # Extract emails and phones using the utility functions
                    found_emails = extract_emails(page_content)
                    for email in found_emails:
                        contacts["emails"].add(email)

                    found_phones = extract_phone_numbers(page_content)
                    for phone in found_phones:
                        contacts["phone_numbers"].add(phone)

                    # If we successfully fetched the homepage, we might not need to try the http version immediately
                    # But for other paths, it's safer to try both if the first fails.
                    if path == "" and url.startswith("https"):
                         break # If homepage HTTPS worked, no need for HTTP homepage immediately

                elif response.status_code == 404:
                    logger.debug(f"Page not found for {url} (status 404).")
                else:
                    logger.debug(f"Failed to fetch {url} with status code {response.status_code}")

            except requests.exceptions.RequestException as e:
                logger.debug(f"Request error fetching {url} for contact extraction: {e}")
                continue # Try next URL for this path/scheme
            except Exception as e:
                logger.debug(f"Unexpected error processing {url} for contacts: {e}")
                continue # Try next URL for this path/scheme

        # After trying both http/https for a path, if we found contacts, maybe move to the next path faster?
        # Or if a page (like homepage) was fetched successfully, we might stop trying http for it.
        # This logic is already handled by the inner loop and break for homepage.


    # Filter the collected contacts using the utility functions
    # Note: filter_emails requires the domain for internal/external check
    filtered_emails_set = filter_emails(contacts["emails"], domain, logger) # Pass logger
    filtered_phones_set = filter_phone_numbers(contacts["phone_numbers"]) # Pass logger if needed inside

    logger.info(f"Finished contact extraction for {domain}. Emails found (filtered): {len(filtered_emails_set)}, Phones found (filtered): {len(filtered_phones_set)}")

    return {"emails": list(filtered_emails_set), "phone_numbers": list(filtered_phones_set)}


