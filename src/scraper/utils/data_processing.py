# Contiene funzioni per manipolare o standardizzare i dati raccolti.

from datetime import datetime
from typing import Any

# Chiamato da json_serial in cli/scraper_cli.py per serializzare datetime
def standardize_for_json(item: Any) -> Any:
    """Standardizza i dati per la serializzazione JSON."""
    if isinstance(item, datetime):
        return item.isoformat()
    if isinstance(item, dict):
        return {k: standardize_for_json(v) for k, v in item.items()}
    if isinstance(item, list):
        return [standardize_for_json(v) for v in item]
    return item

# Chiamato da OSINTExtractor per strutturare i dati grezzi
def extract_structured_fields(data: dict[str, Any], source_type: str) -> dict[str, Any]:
        '''
        Funzione: _extract_structured_fields
        Estrae e struttura i campi chiave dai dati grezzi raccolti da una specifica fonte OSINT.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            dict[str, Any] data -> Il dizionario contenente i dati grezzi dalla fonte
            str source_type -> Il tipo di fonte ("domain", "email", "social")
        Valore di ritorno:
            dict[str, Any] -> Un dizionario contenente i campi strutturati estratti
        '''
        structured: dict[str, Any] = {}
        if source_type == "domain":
            if whois_data := data.get("whois"):
                structured.update(
                    {
                        "registrar": str(whois_data.get("registrar", "")),
                        "creation_date": str(whois_data.get("creation_date", "")),
                        "expiration_date": str(whois_data.get("expiration_date", "")),
                        "domain_name": str(whois_data.get("domain_name", whois_data.get("domain", ""))),
                        "org": str(whois_data.get("org", "")),
                        "name_servers": whois_data.get("name_servers", [])
                    }
                )
            if shodan_data := data.get("shodan"):
                structured.update(
                    {
                        "ip": shodan_data.get("ip_str", ""),
                        "ports": shodan_data.get("ports", []),
                        "hostnames": shodan_data.get("hostnames", []),
                        "isp": shodan_data.get("isp", ""),
                        "org": shodan_data.get("org", "")
                    }
                )
            if dns_data := data.get("dns"):
                structured["dns_records"] = dns_data
            
            if wayback_data := data.get("wayback_machine"):
                if not wayback_data.get("error") and not wayback_data.get("info"): # Controllo che non sia un errore o skip
                    snapshots = wayback_data.get("snapshots", [])
                    if snapshots:
                        structured["wayback_snapshot_count"] = len(snapshots)
                        # Prendi i 5 snapshot più recenti per un'anteprima
                        structured["wayback_latest_snapshots"] = [
                            {"timestamp": s["timestamp"], "url": s["url"]}
                            for s in snapshots[:5]
                        ]
                    else:
                        structured["wayback_snapshot_count"] = 0
                        
        elif source_type == "email":
            if hunter_info := data.get("hunterio"):
                hunter_data_content = hunter_info.get("data", hunter_info)
                structured["hunterio_status"] = hunter_data_content.get("status", hunter_data_content.get("result"))
                structured["hunterio_score"] = hunter_data_content.get("score", 0)
                structured["hunterio_disposable"] = hunter_data_content.get("disposable", False)
                structured["hunterio_webmail"] = hunter_data_content.get("webmail", False)

            if breaches_info := data.get("breaches"):
                if isinstance(breaches_info, list):
                    structured["breach_count"] = len(breaches_info)
                    structured["breached_sites"] = [str(b.get("Name", "")) for b in breaches_info[:5]]
                else:
                    structured["breach_count"] = 0
                    structured["breached_sites"] = []

        elif source_type == "social":
            if profiles_data := data.get("profiles"):
                found_profiles = {
                    platform: details.get("url")
                    for platform, details in profiles_data.items()
                    if details.get("exists")
                }
                structured["social_media_presence"] = found_profiles
                structured["platform_count"] = len(found_profiles)


        return structured