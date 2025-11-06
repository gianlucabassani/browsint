#  Contiene funzioni per analizzare il contenuto web per rilevare tecnologie, header, ecc
# src/scraper/utils/web_analysis.py

from bs4 import BeautifulSoup
import re
import logging
import requests # Aggiunto: necessario per fare la richiesta HTTP
from .clients import _safe_get
from typing import Dict, Any, List # Aggiunto: per type hinting

# Chiamato da Crawler per rilevare tecnologie usate dal sito
def detect_framework(soup:BeautifulSoup, headers:dict, html_content:str, url:str) -> list | str:
    '''
    Funzione: detect_framework
    Rileva il framework web o il CMS utilizzato da un sito web.
    Parametri formali:
        soup -> Oggetto BeautifulSoup del contenuto HTML
        headers -> Dizionario degli header della risposta HTTP
        html_content -> Contenuto HTML come stringa
        url -> L'URL della pagina
    Valore di ritorno:
        list | str -> Una lista di framework/CMS rilevati o la stringa "Unknown"
    '''
    detected = []

    generator_meta = soup.find("meta", attrs={"name": lambda x: x and x.lower() == "generator"})
    if generator_meta and generator_meta.get("content"):
        detected.append(generator_meta.get("content").strip())

    if "X-Powered-By" in headers:
        detected.append(headers["X-Powered-By"].strip())
    if "X-Generator" in headers:
        detected.append(headers["X-Generator"].strip())

    if "wp-content" in html_content or "wp-includes" in html_content:
        detected.append("WordPress")
    if soup.find(id="drupal-css"):
        detected.append("Drupal")
    if any(tag.get("href") and "joomla" in tag.get("href") for tag in soup.find_all("link")):
        detected.append("Joomla")
    if "Powered by Shopify" in html_content:
        detected.append("Shopify")
    if "squarespace.com" in html_content:
        detected.append("Squarespace")
    if "wix.com" in html_content:
        detected.append("Wix")

    for script in soup.find_all("script", src=True):
        src = script["src"]
        if "wp-content" in src or "wp-includes" in src:
            detected.append("WordPress")

    if "/wp-admin" in url or "/wp-login" in url:
        detected.append("WordPress")

    if detected:
        # Preferisci il valore del meta tag generator se presente e rilevato
        if generator_meta and generator_meta.get("content") in detected:
            return generator_meta.get("content").strip()
        return list(set(detected)) # Rimuovi duplicati
    return "Unknown"

# Chiamato da Crawler per rilevare librerie JS usate dal sito
def detect_js_libraries(soup: BeautifulSoup, html_content: str) -> list:
    '''
    Funzione: detect_js_libraries
    Rileva le librerie JavaScript comuni utilizzate in una pagina web.
    Parametri formali:
        soup -> Oggetto BeautifulSoup del contenuto HTML
        html_content -> Contenuto HTML come stringa
    Valore di ritorno:
        list -> Una lista delle librerie JavaScript rilevate
    '''
    libraries = set()

    script_patterns = {
        "jQuery": r"jquery(-[0-9\.]*(\.min)?\.js|\.js)",
        "React": r"react(-dom)?(-[0-9\.]*(\.min)?\.js|\.js)",
        "AngularJS": r"angular(-[0-9\.]*(\.min)?\.js|\.js)",
        "Angular": r"main\.(?:[a-f0-9]+\.)?js",
        "Vue.js": r"vue(-[0-9\.]*(\.min)?\.js|\.js)",
        "Bootstrap JS": r"bootstrap(-[0-9\.]*(\.bundle|\.min)?\.js|\.js)",
        "Lodash": r"lodash(-[0-9\.]*(\.min)?\.js|\.js)",
        "Moment.js": r"moment(-[0-9\.]*(\.min)?\.js|\.js)",
        "GSAP": r"gsap(-[0-9\.]*(\.min)?\.js|\.js)|TweenMax",
        "D3.js": r"d3(-[0-9\.]*(\.min)?\.js|\.js)",
    }

    for script_tag in soup.find_all("script", src=True):
        src = script_tag["src"]
        for lib_name, pattern in script_patterns.items():
            if re.search(pattern, src, re.IGNORECASE):
                libraries.add(lib_name)

    # Controlli basati sul contenuto HTML per maggiore robustezza
    if re.search(r"window\.jQuery|\$\(|jQuery\(", html_content):
        libraries.add("jQuery (likely)")

    if "React.createElement" in html_content or "ReactDOM.render" in html_content:
        libraries.add("React (likely)")
    if "ng-app" in html_content or "angular.module" in html_content:
        libraries.add("AngularJS (likely)")
    if "new Vue(" in html_content:
        libraries.add("Vue.js (likely)")


    return list(libraries) if libraries else []

# Chiamato da Crawler per controllare header di sicurezza
def check_security_headers(headers: dict) -> dict:
    '''
    Funzione: check_security_headers
    Controlla la presenza e la validità di base degli header di sicurezza importanti nella risposta HTTP.
    Parametri formali:
        dict headers -> Dizionario degli header della risposta HTTP
    Valore di ritorno:
        dict -> Un dizionario contenente gli header di sicurezza trovati e i loro valori
    '''
    security_headers_found = {}
    lower_headers = {k.lower(): v for k, v in headers.items()}

    common_sec_headers = {
        "Strict-Transport-Security": "HSTS",
        "Content-Security-Policy": "CSP",
        "X-Frame-Options": "X-Frame-Options", # Mantieni il nome completo per chiarezza
        "X-Content-Type-Options": "X-Content-Type-Options", # Mantieni il nome completo
        "Referrer-Policy": "Referrer-Policy",
        "Permissions-Policy": "Permissions-Policy",
        "X-XSS-Protection": "X-XSS-Protection", # Mantieni il nome completo
    }

    for header_name, display_name in common_sec_headers.items():
        if header_name.lower() in lower_headers:
            security_headers_found[display_name] = lower_headers[header_name.lower()]

    return security_headers_found

# Chiamato da Crawler per rilevare servizi di analytics usati dal sito
def detect_analytics(html_content: str) -> list:
    '''
    Funzione: detect_analytics
    Rileva la presenza di script o pattern associati a servizi di analytics comuni nel contenuto HTML.
    Parametri formali:
        str html_content -> Contenuto HTML della pagina come stringa
    Valore di ritorno:
        list -> Una lista dei servizi di analytics rilevati
    '''
    analytics_services = set()

    if re.search(
        r"www\.google-analytics\.com/analytics\.js|gtag\('config', 'UA-|gtag\('config', 'G-", html_content
    ):
        analytics_services.add("Google Analytics (Universal or GA4)")

    if "googletagmanager.com/gtm.js" in html_content:
        analytics_services.add("Google Tag Manager")

    if "connect.facebook.net/en_US/fbevents.js" in html_content or "fbq('init'" in html_content:
        analytics_services.add("Facebook Pixel")

    if "matomo.js" in html_content or "piwik.js" in html_content or "_paq.push" in html_content:
        analytics_services.add("Matomo (Piwik)")

    if "static.hotjar.com/c/hotjar-" in html_content or "hj('event'" in html_content:
        analytics_services.add("Hotjar")

    if "js.hs-scripts.com/" in html_content or "track HubSpot analytics" in html_content:
        analytics_services.add("HubSpot Analytics")

    return list(analytics_services)


# === FUNZIONE CONSOLIDATA PER IL RILEVAMENTO TECNOLOGIE ===

# Chiamato da Crawler per rilevare tecnologie usate dal sito
def detect_technologies(domain: str, logger: logging.Logger) -> Dict[str, Any]:
    '''
    Funzione: detect_technologies
    Rileva le tecnologie utilizzate da un sito web (framework, JS libs, server, headers, analytics).

    Questa funzione effettua la richiesta HTTP, analizza la risposta (headers, contenuto)
    e chiama le funzioni di rilevamento specifiche (framework, js, analytics, security headers).

    Parametri formali:
        str domain -> Il dominio del sito per cui rilevare le tecnologie
        logging.Logger logger -> L'istanza del logger da utilizzare per i messaggi

    Valore di ritorno:
        dict -> Un dizionario contenente le tecnologie rilevate o un errore
    '''
    #logger.info(f"Detecting technologies for https://{domain}")
    tech_data: Dict[str, Any] = {} # Specifica il tipo per chiarezza

    try:
        url = f"https://{domain}"
        # Utilizza requests.get direttamente qui per fare la richiesta
        response = _safe_get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            },
            timeout=10,
            verify=True,
            allow_redirects=True,
        )
        response.raise_for_status() # Solleva un'eccezione per status codes 4xx/5xx

        final_url = response.url
        content = response.text # Ottieni il contenuto testuale

        soup = BeautifulSoup(content, "html.parser")

        # Estrazione Meta Tags
        meta_tags = {}
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            content_meta = meta.get("content") # Rinominato per evitare conflitto
            if name and content_meta:
                meta_tags[name.lower()] = content_meta
        if meta_tags:
            tech_data["meta_tags"] = meta_tags

        # Server Header
        if "Server" in response.headers:
            tech_data["web_server"] = response.headers["Server"]

        # Rilevamento Framework/CMS (chiama la funzione locale)
        frameworks = detect_framework(soup, response.headers, content, final_url)
        if frameworks and frameworks != "Unknown": # Controlla sia per lista non vuota che per "Unknown"
             tech_data["framework_cms"] = frameworks

        # Rilevamento JS Libraries (chiama la funzione locale)
        js_libs = detect_js_libraries(soup, content)
        if js_libs:
            tech_data["js_libraries"] = js_libs

        # Controllo Security Headers (chiama la funzione locale)
        security_headers = check_security_headers(response.headers)
        if security_headers:
            tech_data["security_headers"] = security_headers

        # Rilevamento Analytics (chiama la funzione locale)
        analytics = detect_analytics(content)
        if analytics:
            tech_data["analytics"] = analytics

        #logger.info(f"Technology detection successful for {domain}.")

    except requests.exceptions.SSLError as e:
        logger.warning(f"SSL Error for {domain}: {str(e)}. Retrying with http...")
        try:
            url_http = f"http://{domain}"
            # Riprova con HTTP se HTTPS fallisce per errore SSL
            response_http = _safe_get(
                url_http, headers=response.headers if 'response' in locals() else {}, # Usa header originali se disponibili
                timeout=10, allow_redirects=True, verify=False # verify=False per ignorare errori SSL nel fallback
            )
            response_http.raise_for_status()

            # Ripeti l'analisi con la risposta HTTP
            final_url = response_http.url
            content = response_http.text
            soup = BeautifulSoup(content, "html.parser")

            meta_tags = {}
            for meta in soup.find_all("meta"):
                name = meta.get("name") or meta.get("property")
                content_meta = meta.get("content") # Rinominato per evitare conflitto
                if name and content_meta:
                    meta_tags[name.lower()] = content_meta
            if meta_tags:
                tech_data["meta_tags"] = meta_tags

            if "Server" in response_http.headers:
                tech_data["web_server"] = response_http.headers["Server"]

            frameworks = detect_framework(soup, response_http.headers, content, final_url)
            if frameworks and frameworks != "Unknown":
                 tech_data["framework_cms"] = frameworks

            js_libs = detect_js_libraries(soup, content)
            if js_libs:
                tech_data["js_libraries"] = js_libs

            security_headers = check_security_headers(response_http.headers)
            if security_headers:
                tech_data["security_headers"] = security_headers

            analytics = detect_analytics(content)
            if analytics:
                tech_data["analytics"] = analytics

            tech_data["note"] = "Analysis performed via HTTP fallback due to SSL error on HTTPS."
            logger.info(f"Technology detection successful via HTTP fallback for {domain}.")

        except Exception as http_e:
            logger.error(f"Error detecting technologies via HTTP fallback for {domain}: {str(http_e)}")
            tech_data["error"] = f"HTTPS SSL Error ({e}), HTTP fallback failed ({http_e})"

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error detecting technologies for {domain}: {str(e)}")
        tech_data["error"] = f"Request failed: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error detecting technologies for {domain}: {str(e)}", exc_info=True)
        tech_data["error"] = f"Unexpected error: {str(e)}"

    return tech_data
