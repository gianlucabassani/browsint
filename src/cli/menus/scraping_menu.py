"""
Scraping menu module for the Browsint CLI application.
"""
from colorama import Fore, Style
from typing import TYPE_CHECKING
from ..utils import clear_screen, prompt_for_input, json_serial, export_menu
import json
import asyncio
import validators
import time
from datetime import datetime
from urllib.parse import urlparse
import logging
from pathlib import Path
from tabulate import tabulate
from scraper.utils.formatters import format_page_analysis_report, generate_html_report, create_pdf_page_report, text_report_to_html, formal_html_report_page
from scraper.utils.extractors import extract_emails, extract_phone_numbers
from scraper.utils.web_analysis import detect_technologies

if TYPE_CHECKING:
    from ..scraper_cli import ScraperCLI

logger = logging.getLogger("browsint.cli")
crawler_logger = logging.getLogger("scraper.crawler")
fetcher_logger = logging.getLogger("scraper.fetcher")

async def display_scraping_menu() -> str:
    '''Visualizza il menu di scraping e restituisce la scelta dell'utente.'''
    #clear_screen()
    print(f"\n{Fore.BLUE}{'═' * 40}")
    print(f"█ {Fore.WHITE}{'OSINT SCRAPING':^36}{Fore.BLUE} █")
    print(f"{'═' * 40}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}1.{Style.RESET_ALL} Analizza una pagina web (Estrazione dati base)")
    print(f"{Fore.YELLOW}2.{Style.RESET_ALL} Crawl struttura web con estrazione OSINT \n")
    print(f"{Fore.YELLOW}0.{Style.RESET_ALL} Torna al menu principale")

    return await prompt_for_input("Scelta: ")

async def handle_scraping_choice(cli_instance: 'ScraperCLI', choice: str) -> None:
    '''
    Gestisce la scelta dell'utente nel menu di scraping.
    
    Args:
        cli_instance: L'istanza di ScraperCLI per accedere ai metodi
        choice: La scelta dell'utente
    '''
    match choice:
        case "1": await analyze_page_structure(cli_instance)
        case "2": await start_website_crawl_with_osint(cli_instance)
        case "0": return
        case _:
            print(f"{Fore.RED}✗ Scelta non valida")
            await prompt_for_input("Premi INVIO per continuare...") 

async def analyze_page_structure(cli_instance: 'ScraperCLI') -> None:
    '''
    Analizza la struttura di una singola pagina web e estrae informazioni OSINT di base.
    '''
    url = await prompt_for_input("Inserisci l'URL della pagina da analizzare: ")
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
    if not validators.url(url):
        print(f"{Fore.RED}✗ URL non valido.")
        return

    print(f"{Fore.YELLOW}⏳ Analisi struttura pagina per {url}...{Style.RESET_ALL}")
    try:
        try:
            async with cli_instance.web_fetcher:
                response = await cli_instance.web_fetcher.fetch_full_response(url) # ottengo anche gli headers e lo stato della risposta
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operazione annullata dall'utente.{Style.RESET_ALL}")
            return
        if not response or not response.content:
            print(f"{Fore.RED}✗ Impossibile scaricare il contenuto per l'analisi.")
            return

        try:
            content = response.content.decode(response.encoding if response.encoding else 'utf-8', errors='replace') 
        except Exception as e_decode:
            logger.warning(f"Errore decodifica contenuto testuale per {url}: {e_decode}")
            print(f"{Fore.RED}✗ Errore decodifica contenuto per {url}: {e_decode}")
            return

        parsed_data = cli_instance.web_parser.parse(content, url) # parsing del contenuto HTML

        # Prepare OSINT data
        osint_data = {}
        if hasattr(cli_instance, 'osint_extractor') and cli_instance.osint_extractor: # hasattr per verificare se l'OSINT Extractor è disponibile
            try:
                page_emails = extract_emails(content) 
                page_phones = extract_phone_numbers(content)
                osint_data["emails"] = page_emails
                osint_data["phone_numbers"] = page_phones

                domain_for_tech = urlparse(url).netloc
                if domain_for_tech:
                    tech_data = detect_technologies(domain_for_tech, logger)
                    if tech_data and not tech_data.get("error"):
                        osint_data["page_technologies"] = tech_data

            except Exception as e_osint_page:
                logger.error(f"Errore durante estrazione OSINT base per {url}: {e_osint_page}", exc_info=True)
                print(f"{Fore.RED}✗ Errore durante estrazione OSINT base per pagina: {e_osint_page}{Style.RESET_ALL}")

        # Remove the save_raw prompt and logic from here
        save_paths = {}
        # Display formatted report (with empty save_paths)
        print(format_page_analysis_report(url, parsed_data, osint_data, save_paths))

        export_choice = await export_menu()
        if export_choice != "0":
            await _export_analysis_results(cli_instance, url, parsed_data, osint_data, export_choice)

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operazione annullata dall'utente.{Style.RESET_ALL}")
        return
    except Exception as e:
        logger.error(f"Error during page structure analysis for {url}: {e}", exc_info=True)
        print(f"{Fore.RED}✗ Errore durante l'analisi della pagina: {e}")

    await prompt_for_input("Premi INVIO per continuare...")

async def start_website_crawl_with_osint(cli_instance: 'ScraperCLI') -> None:
    '''
    Avvia il crawling di un sito web in modalità OSINT, estraendo informazioni e salvandole nel database osint.
    Non scarica i file su disco ma analizza ogni pagina per estrarre informazioni utili.
    '''
    if not cli_instance.osint_extractor:
        print(f"{Fore.RED}✗ OSINT Extractor non disponibile. Impossibile procedere.{Style.RESET_ALL}")
        return

    url = await prompt_for_input("Inserisci l'URL di partenza per il crawling OSINT: ")
    if not url:
        print(f"{Fore.RED}✗ URL non può essere vuoto.")
        return
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
    

    depth_str = await prompt_for_input("Inserisci il limite di profondità (default: 1): ")
    depth = int(depth_str) if depth_str.isdigit() else 1

    print(f"{Fore.YELLOW}⏳ Inizializzazione crawler OSINT per {url} con profondità {depth}...")

    original_crawler_level = crawler_logger.level
    original_fetcher_level = fetcher_logger.level
    crawler_logger.setLevel(logging.WARNING)
    fetcher_logger.setLevel(logging.WARNING)

    try:
        try:
            async with cli_instance.web_fetcher:
                crawl_stats = await cli_instance.crawler.start_crawl(
                start_url=url,
                depth_limit=depth,
                perform_osint_on_pages=True,
                save_to_disk=False  # Non salvare su disco in modalità OSINT
            )
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Crawling OSINT annullato dall'utente.{Style.RESET_ALL}")
            return

        _display_base_crawl_stats(crawl_stats)

        if "osint_summary" in crawl_stats:
            print("\n")
            display_crawl_osint_report(crawl_stats["osint_summary"], url)
    except Exception as e:
        logger.error(f"Errore durante il crawling OSINT: {e}", exc_info=True)
        print(f"{Fore.RED}✗ Errore durante il crawling OSINT: {e}")
    finally:
        crawler_logger.setLevel(original_crawler_level)
        fetcher_logger.setLevel(original_fetcher_level)

def display_crawl_osint_report(osint_summary: dict, target_url: str) -> None:
    '''Mostra un report aggregato dei risultati OSINT raccolti durante il crawling.'''
    print(f"\n{Fore.BLUE}{'=' * 70}")
    print(f"█ {Fore.WHITE}{f'REPORT OSINT CRAWL per {target_url}':^66}{Fore.BLUE} █")
    print(f"{'=' * 70}{Style.RESET_ALL}\n")

    entities_profiled = osint_summary.get("entities_profiled", [])
    if entities_profiled:
        # Organizziamo i dati per tipo
        emails_data = []
        phones_data = []
        social_data = []
        
        for finding in entities_profiled:
            page = finding.get('page_url')
            etype = finding.get('entity_type')
            entity_identifier = finding.get('entity')
            profile_details = finding.get('profile_details', {})

            if etype == "email":
                if profile_details and not profile_details.get("error"):
                    email_db_profiles = profile_details.get("profiles", {}).get("email", {})
                    extracted_info = email_db_profiles.get("extracted", {})
                    
                    emails_data.append([
                        entity_identifier,
                        page,
                        extracted_info.get("hunterio_status", "N/A"),
                        extracted_info.get("breach_count", 0)
                    ])
            elif etype == "phone_numbers_found":
                if isinstance(entity_identifier, list):
                    for phone in entity_identifier:
                        phones_data.append([phone, page])
                else:
                    phones_data.append([entity_identifier, page])
            elif etype == "social_profile":
                # Aggiungiamo i dati social con più informazioni
                platform = profile_details.get("platform", "N/A")
                url = profile_details.get("url", "N/A")
                confidence = profile_details.get("confidence", "N/A")
                social_data.append([
                    platform,
                    entity_identifier,
                    url,
                    confidence
                ])

        # Mostra tabella email
        if emails_data:
            print(f"\n{Fore.YELLOW}--- 📧 Email Trovate e Profilate ---{Style.RESET_ALL}")
            print(tabulate(
                emails_data,
                headers=["Email", "Pagina", "Stato HunterIO", "N° Breaches"],
                tablefmt="grid"
            ))
        
        # Mostra tabella telefoni
        if phones_data:
            print(f"\n{Fore.YELLOW}--- 📱 Numeri di Telefono Trovati ---{Style.RESET_ALL}")
            print(tabulate(
                phones_data,
                headers=["Numero", "Pagina"],
                tablefmt="grid"
            ))
            
        # Mostra tabella social media
        if social_data:
            print(f"\n{Fore.YELLOW}--- 🌐 Profili Social Media ---{Style.RESET_ALL}")
            print(tabulate(
                social_data,
                headers=["Piattaforma", "Username", "URL", "Confidenza"],
                tablefmt="grid"
            ))

        # Mostra tecnologie rilevate
        page_technologies = osint_summary.get("page_technologies", {})
        if page_technologies:
            print(f"\n{Fore.YELLOW}--- 💻 Tecnologie Rilevate per Pagina ---{Style.RESET_ALL}")
            tech_data = []
            for page, techs in page_technologies.items():
                tech_data.append([
                    page,
                    techs.get("framework_cms", "N/A"),
                    ", ".join(techs.get("js_libraries", [])) if techs.get("js_libraries") else "N/A",
                    ", ".join(techs.get("analytics", [])) if techs.get("analytics") else "N/A"
                ])
            
            if tech_data:
                print(tabulate(
                    tech_data,
                    headers=["URL", "Framework/CMS", "JS Libraries", "Analytics"],
                    tablefmt="grid"
                ))
            else:
                print(f"{Fore.YELLOW}Nessuna tecnologia specifica rilevata.{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}Nessuna entità OSINT (email/telefoni/social) rilevata e profilata dalle pagine.{Style.RESET_ALL}")

    print(f"\n{Fore.BLUE}{'=' * 70}{Style.RESET_ALL}\n")

def _display_base_crawl_stats(stats: dict) -> None:
    '''Visualizza statistiche di base del crawling completato.'''
    print(f"\n{Fore.YELLOW}✓ Crawling OSINT completato")
    print(f"\nStatistiche di base:")
    print(f"  • URLs visitati: {stats.get('urls_visited', 0)}")
    print(f"  • Pagine salvate: {stats.get('pages_saved', 0)}")
    print(f"  • Errori download: {stats.get('errors', 0)}")
    print(f"\nPercorso di salvataggio:")
    print(f"  • Contenuto: {stats.get('download_path', 'N/A')}")

async def _export_analysis_results(cli_instance: 'ScraperCLI', url: str, parsed_data: dict, osint_data: dict, export_choice: str, save_paths: dict = None) -> None:
    '''
    Esporta i risultati dell'analisi web in formato scelto (JSON, HTML, PDF, Tutti).
    '''
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        domain = urlparse(url).netloc
        analysis_dir = cli_instance.dirs["analysis"]
        pdf_dir = cli_instance.dirs["pdf_reports"]
        export_data = {
            "url": url,
            "timestamp": timestamp,
            "analysis_type": "web_page",
            "parsed_data": parsed_data,
            "osint_data": osint_data,
            "meta": {
                "generated_by": "Browsint Web Analyzer"
            }
        }
        exported = False
        save_paths = save_paths or {}
        # Only ask to save raw HTML/JSON if exporting JSON or HTML (or all)
        if export_choice in {"1", "2", "4"}:
            save_raw = (await prompt_for_input("Vuoi salvare anche HTML originale e struttura JSON? (s/N): ")).lower() == 's'
            if save_raw:
                analysis_output_dir = analysis_dir / f"{domain.replace('.', '_')}_{timestamp}"
                analysis_output_dir.mkdir(parents=True, exist_ok=True)
                # Save original HTML
                raw_html_path = analysis_output_dir / "original.html"
                async with cli_instance.web_fetcher:
                    response = await cli_instance.web_fetcher.fetch_full_response(url)
                content = response.content.decode(response.encoding if response.encoding else 'utf-8', errors='replace')
                with open(raw_html_path, "w", encoding="utf-8") as f_html:
                    f_html.write(content)
                save_paths["original_html"] = raw_html_path
                # Save parsed JSON
                parsed_json_path = analysis_output_dir / "parsed_structure.json"
                with open(parsed_json_path, "w", encoding="utf-8") as f_json:
                    json.dump(parsed_data, f_json, indent=2, ensure_ascii=False, default=json_serial)
                save_paths["parsed_json"] = parsed_json_path
        if export_choice in {"1", "4"}:
            json_path = analysis_dir / f"analysis_{domain}_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False, default=json_serial)
            print(f"\n{Fore.YELLOW}✓ Esportato JSON: {json_path}{Style.RESET_ALL}")
            exported = True
        if export_choice in {"2", "4"}:
            html_path = analysis_dir / f"analysis_{domain}_{timestamp}.html"
            html_report = formal_html_report_page(url, parsed_data, osint_data, save_paths)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_report)
            print(f"{Fore.YELLOW}✓ Esportato HTML: {html_path}{Style.RESET_ALL}")
            exported = True
        if export_choice in {"3", "4"}:
            pdf_path = pdf_dir / f"analysis_{domain}_{timestamp}.pdf"
            create_pdf_page_report(url, parsed_data, osint_data, save_paths, str(pdf_path))
            print(f"{Fore.YELLOW}✓ Esportato PDF: {pdf_path}{Style.RESET_ALL}")
            exported = True
        if not exported:
            print(f"{Fore.YELLOW}Nessun formato selezionato per l'esportazione.{Style.RESET_ALL}")
        else:
            logger.info(f"Analysis results exported for {url} [{export_choice}]")
    except Exception as e:
        logger.error(f"Error exporting analysis results: {e}", exc_info=True)
        print(f"{Fore.RED}✗ Errore durante l'esportazione: {e}{Style.RESET_ALL}")