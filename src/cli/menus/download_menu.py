"""
Download menu module for the Browsint CLI application.
"""
from colorama import Fore, Style
from typing import TYPE_CHECKING
from pathlib import Path
from urllib.parse import urlparse
import time
import logging
import asyncio
import validators
from ..utils import clear_screen, prompt_for_input
import json

if TYPE_CHECKING: # Serve a evitare errori di importazione circolare
    from ..scraper_cli import ScraperCLI

# Initialize loggers
logger = logging.getLogger("browsint.cli")
crawler_logger = logging.getLogger("scraper.crawler")
fetcher_logger = logging.getLogger("scraper.fetcher")
db_logger = logging.getLogger("DatabaseManager")

def display_download_menu() -> str:
    '''Visualizza il menu di download e restituisce la scelta dell'utente.'''
    #clear_screen()
    print(f"\n{Fore.BLUE}{'═' * 40}")
    print(f"█ {Fore.WHITE}{'CRAWL & DOWNLOAD':^36}{Fore.BLUE} █")
    print(f"{'═' * 40}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}1.{Style.RESET_ALL} Downlod singola pagina web (HTML + Struttura)")
    print(f"{Fore.YELLOW}2.{Style.RESET_ALL} Download multiplo da file (HTML + Struttura)")
    print(f"{Fore.YELLOW}3.{Style.RESET_ALL} Crawl e download struttura sito web\n")
    print(f"{Fore.YELLOW}0.{Style.RESET_ALL} Torna al menu principale")

    return prompt_for_input("Scelta: ")

async def handle_download_choice(cli_instance: 'ScraperCLI', choice: str) -> None:
    '''
    Gestisce la scelta dell'utente nel menu di download.
    
    Args:
        cli_instance: L'istanza di ScraperCLI per accedere ai metodi
        choice: La scelta dell'utente
    '''
    match choice:
        case "1": await download_single_url(cli_instance)
        case "2": await download_multiple_urls(cli_instance)
        case "3": await start_website_crawl_base(cli_instance)
        case "0": return
        case _:
            print(f"{Fore.RED}✗ Scelta non valida")
            input(f"{Fore.CYAN}\nPremi INVIO per continuare...{Style.RESET_ALL}")

async def download_single_url(cli_instance: 'ScraperCLI') -> None:
    '''Scarica il contenuto di un singolo URL e offre l'opzione di salvarlo.'''
    url = prompt_for_input("Inserisci URL: ")
    if not url:
        print(f"{Fore.RED}URL non può essere vuoto.")
        return

    # Normalizza l'URL: aggiungi https:// se manca lo schema
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url

    print(f"{Fore.YELLOW}⏳ Scaricamento in corso per {url}...")
    try:
        async with cli_instance.web_fetcher:
            content = await cli_instance.web_fetcher.fetch(url)
        if content:
            print(f"\n{Fore.YELLOW}✓ Contenuto scaricato ({len(content)} bytes)")
            save_option = prompt_for_input("\nSalvare il contenuto? (s/n): ").lower()
            if save_option == "s":
                url_parsed = urlparse(url)
                domain = url_parsed.netloc or "local_file"
                timestamp = time.strftime("%Y%m%d_%H%M%S") # formato esempio: 20231001_123456
                default_filename = f"{domain.replace('.', '_')}_{timestamp}.html" # + nome file

                filename_input = prompt_for_input(f"Nome file (default: {default_filename}): ")
                if filename_input:
                    filename = filename_input if filename_input.lower().endswith('.html') else filename_input + '.html'
                else:
                    filename = default_filename
                filepath = cli_instance.dirs["sites"] / filename
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"{Fore.YELLOW}✓ Contenuto salvato in: {filepath}")
                except Exception as e_save:
                    logger.error(f"Error saving file {filepath}: {e_save}", exc_info=True)
                    print(f"{Fore.RED}✗ Errore nel salvataggio del file: {e_save}")
        else:
            print(f"{Fore.RED}✗ Download fallito o contenuto vuoto per {url}.")
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operazione annullata dall'utente.{Style.RESET_ALL}")
        return
    except Exception as e:
        logger.error(f"Error during single URL download {url}: {e}", exc_info=True)
        print(f"{Fore.RED}✗ Errore durante il download: {e}")

async def download_multiple_urls(cli_instance: 'ScraperCLI') -> None:
    '''Scarica contenuti da una lista di URL specificati in un file.'''
    file_path_input = prompt_for_input("Inserisci il percorso del file contenente gli URL (uno per riga): ")
    url_file_path = Path(file_path_input)

    if not url_file_path.is_file():
        print(f"{Fore.RED}✗ File non trovato: {url_file_path}")
        return

    try:
        with open(url_file_path, encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        if not urls:
            print(f"{Fore.YELLOW}⚠ Nessun URL valido trovato nel file.")
            return

        print(f"{Fore.YELLOW}⏳ Trovati {len(urls)} URL. Inizio download...")

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        batch_download_dir = cli_instance.dirs["sites"] / f"batch_{timestamp}"
        batch_download_dir.mkdir(parents=True, exist_ok=True)

        report_lines = [f"Report di Download Batch - {timestamp}\nTotal URLs: {len(urls)}\n"]
        success_count = 0

        for i, url in enumerate(urls, 1): # enumerate inizia da 1 e conta gli URL
            parsed = urlparse(url)
            if not parsed.scheme:
                url = "https://" + url
            print(f"{Fore.CYAN}[{i}/{len(urls)}] Scaricando: {url}...{Style.RESET_ALL}")
            try:
                async with cli_instance.web_fetcher:
                    content = await cli_instance.web_fetcher.fetch(url)
                if content:
                    domain = urlparse(url).netloc or f"url_{i}" # netloc riesce a ottenere il dominio eseguendo un parse dell'URL 
                    file_name = f"{domain.replace('.', '_')}_{i}.html"
                    file_save_path = batch_download_dir / file_name
                    with open(file_save_path, "w", encoding="utf-8") as cf:
                        cf.write(content)
                    report_lines.append(f"[SUCCESS] {url} -> Salvato in {file_save_path} ({len(content)} bytes)")
                    success_count += 1
                    print(f"{Fore.YELLOW}✓ Successo.{Style.RESET_ALL}")
                else:
                    report_lines.append(f"[FAILED] {url} -> Nessun contenuto o errore download.")
                    print(f"{Fore.RED}✗ Fallito (nessun contenuto).{Style.RESET_ALL}")
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Operazione annullata dall'utente durante il download multiplo.{Style.RESET_ALL}")
                break
            except Exception as e_multi:
                logger.error(f"Error downloading {url} in batch: {e_multi}", exc_info=True)
                report_lines.append(f"[ERROR] {url} -> {e_multi}")
                print(f"{Fore.RED}✗ Errore: {e_multi}{Style.RESET_ALL}")
            time.sleep(0.5) # evito scovraccarico

        report_lines.insert(2, f"Completati con successo: {success_count}")
        report_lines.insert(3, f"Falliti/Errori: {len(urls) - success_count}\n")

        report_file_path = cli_instance.dirs["reports"] / f"report_batch_{timestamp}.txt"
        with open(report_file_path, "w", encoding="utf-8") as rf:
            rf.write("\n".join(report_lines))

        print(f"\n{Fore.YELLOW}✓ Download batch completato. Report salvato in: {report_file_path}")
        print(f"{Fore.CYAN}File salvati in: {batch_download_dir}{Style.RESET_ALL}")

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operazione annullata dall'utente durante il download multiplo.{Style.RESET_ALL}")
        return
    except Exception as e_main:
        logger.error(f"General error during multiple URL download: {e_main}", exc_info=True)
        print(f"{Fore.RED}✗ Errore generale durante il download multiplo: {e_main}")

async def start_website_crawl_base(cli_instance: 'ScraperCLI') -> None:
    '''
    Esegue il crawling di un sito web in modalità download, salvando HTML e struttura su disco e nel database websites.
    '''
    #clear_screen()
    print(f"\n{Fore.BLUE}{'═' * 40}")
    print(f"█ {Fore.WHITE}{'CRAWL E DOWNLOAD STRUTTURA SITO WEB':^36}{Fore.BLUE} █")
    print(f"{'═' * 40}{Style.RESET_ALL}\n")

    url = cli_instance._get_validated_url_input("Inserisci l'URL di partenza per il crawling (es. https://example.com): ")
    if not url:
        return
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
    

    depth = cli_instance._get_depth_input(default=2, message="Inserisci il limite di profondità per il crawling (default: 2): ")
    if depth is None:
        return

    # Imposta i livelli di logging per vedere solo le informazioni importanti durante il crawling
    original_crawler_level = crawler_logger.level
    original_fetcher_level = fetcher_logger.level
    original_db_level = db_logger.level

    crawler_logger.setLevel(logging.INFO)
    fetcher_logger.setLevel(logging.INFO)
    db_logger.setLevel(logging.WARNING)

    print(f"\n{Fore.YELLOW}Avvio crawling per {url} con profondità {depth}...{Style.RESET_ALL}")
    time.sleep(1)

    try:
        # Ottieni l'istanza del crawler dalla ScraperCLI
        crawler_instance = cli_instance.crawler
        
        # Verifica se l'istanza del crawler è valida
        if not crawler_instance:
            logger.error("L'istanza del crawler non è stata inizializzata in ScraperCLI.")
            print(f"{Fore.RED}✗ Errore interno: il crawler non è disponibile.")
            return

        # Salva l'originale osint_extractor se presente e imposta a None per questa operazione
        original_crawler_osint_extractor = crawler_instance.osint_extractor 
        crawler_instance.osint_extractor = None # Disabilita l'OSINT extractor per questa operazione

        try:
            async with cli_instance.web_fetcher:
                crawl_stats = await cli_instance.crawler.start_crawl(
                start_url=url,
                depth_limit=depth,
                politeness_delay=1.0,
                perform_osint_on_pages=False,
                save_to_disk=True  # Modalità download
            )
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Crawling annullato dall'utente.{Style.RESET_ALL}")
            return
        
        # Ripristina l'osint_extractor originale del crawler per operazioni future
        crawler_instance.osint_extractor = original_crawler_osint_extractor

        print(f"\n{Fore.YELLOW}✓ Crawling per {url} completato.{Style.RESET_ALL}")
        _display_base_crawl_stats(crawl_stats)

    except Exception as e:
        logger.error(f"Errore durante il crawling: {e}", exc_info=True)
        print(f"{Fore.RED}✗ Errore durante il crawling: {e}")
    finally:
        # Ripristina i livelli di logging originali
        crawler_logger.setLevel(original_crawler_level)
        fetcher_logger.setLevel(original_fetcher_level)
        db_logger.setLevel(original_db_level)


def _display_base_crawl_stats(stats: dict) -> None:
    '''Visualizza statistiche di base del crawling completato.'''
    print(f"\n{Fore.YELLOW}✓ Crawling completato{Style.RESET_ALL}")
    print(f"\nStatistiche di base:")
    print(f"  • URLs visitati: {stats.get('urls_visited', 0)}")
    print(f"  • Pagine salvate (HTML): {stats.get('pages_saved', 0)}") 
    print(f"  • Errori download: {stats.get('errors', 0)}")
    
    print(f"\nPercorsi di salvataggio:")
    # Il percorso di download è generato all'interno del Crawler e dovrebbe essere una Path
    # Qui viene gestito l'errore per 'download_path' che può essere non presente se ci sono stati errori
    download_path_str = stats.get('download_path', 'N/A')
    if isinstance(download_path_str, Path):
        download_path_str = str(download_path_str)
    print(f"  • Contenuto HTML: {download_path_str}")

    print(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
    input()
