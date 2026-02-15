import logging
import time
import asyncio
from collections import deque
from urllib.parse import urlparse, urljoin, unquote
from colorama import Fore, Style
from bs4 import BeautifulSoup
from typing import Optional, Any
from scraper.fetcher import WebFetcher
from scraper.parser import WebParser
from scraper.utils.robots_parser import RobotsParser, RobotsData
from db.manager import DatabaseManager
from pathlib import Path
from scraper.utils.extractors import extract_emails, extract_phone_numbers, filter_phone_numbers, filter_emails
from scraper.utils.web_analysis import detect_framework, detect_js_libraries, detect_analytics
import json


logger = logging.getLogger("scraper.crawler")

class Crawler:
    '''
    Funzione: Crawler
    Classe responsabile per la navigazione e il download ricorsivo di pagine web (crawling).
    Versione Asincrona per compatibilità con httpx WebFetcher.
    '''
    def __init__(self, fetcher: WebFetcher, parser: WebParser, db_manager: DatabaseManager, osint_extractor=None, base_dirs: dict[str, Path] = None):
        self.fetcher = fetcher
        self.parser = parser
        self.db_manager = db_manager
        self.osint_extractor = osint_extractor
        self.visited_urls = set()
        self.base_domain = ""
        self.base_dirs = base_dirs or {}
        self.current_site_dir = None
        self.already_profiled_in_session = set()
        self.robots_parser = RobotsParser()
        self.robots_data: Optional[RobotsData] = None
        self.respect_robots = True

    def set_osint_extractor(self, extractor):
        self.osint_extractor = extractor
        if extractor:
            self.already_profiled_in_session = set()

    def _normalize_url(self, url: str, base_url: str) -> str | None:
        try:
            absolute_url = urljoin(base_url, url.strip())
            parsed_url = urlparse(absolute_url)
            clean_url = parsed_url._replace(fragment="").geturl()
            clean_url = unquote(clean_url)
            if clean_url.endswith("/") and parsed_url.path != "/":
                clean_url = clean_url.rstrip("/")
            return clean_url
        except Exception as e:
            logger.warning(f"Errore normalizzazione URL '{url}': {e}")
            return None

    def _is_internal_url(self, url: str) -> bool:
        if not self.base_domain:
            return False
        try:
            parsed_url = urlparse(url)
            return parsed_url.netloc == self.base_domain
        except Exception:
            return False

    def _save_page_info(self, url: str, title: str, status_code: int, content_length: int, content_type: str) -> Optional[int]:
        domain = urlparse(url).netloc
        website_id = self._get_or_create_website(domain)
        if not website_id:
            logger.error(f"Impossibile ottenere o creare website_id per il dominio {domain}")
            return None

        try:
            with self.db_manager.transaction("websites") as cursor:
                cursor.execute(
                    "SELECT id FROM pages WHERE url = ? AND website_id = ?",
                    (url, website_id)
                )
                existing_page = cursor.fetchone()

                if existing_page:
                    page_id = existing_page['id']
                    cursor.execute(
                        "UPDATE pages SET status_code = ?, content_length = ?, content_type = ?, last_checked = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (status_code, content_length, content_type, page_id)
                    )
                    logger.info(f"Pagina '{url}' aggiornata (ID: {page_id}).")
                    return page_id
                else:
                    cursor.execute(
                        "INSERT INTO pages (website_id, url, title, status_code, content_length, content_type) VALUES (?, ?, ?, ?, ?, ?)",
                        (website_id, url, title, status_code, content_length, content_type)
                    )
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Errore durante il salvataggio della pagina '{url}': {e}")
            return None

    def _get_or_create_website(self, domain: str) -> Optional[int]:
        try:
            with self.db_manager.transaction("websites") as cursor:
                cursor.execute("SELECT id FROM websites WHERE domain = ?", (domain,))
                existing_website = cursor.fetchone()
                
                if existing_website:
                    return existing_website['id']
                
                cursor.execute(
                    "INSERT INTO websites (domain) VALUES (?)",
                    (domain,)
                )
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Errore durante la creazione del website per il dominio '{domain}': {e}")
            return None

    def _save_link_info(self, page_id: int, href: str, anchor_text: str, is_internal: bool) -> None:
        try:
            with self.db_manager.transaction("websites") as cursor:
                cursor.execute(
                    "SELECT id FROM links WHERE page_id = ? AND href = ?",
                    (page_id, href)
                )
                existing_link = cursor.fetchone()
                
                if not existing_link:
                    cursor.execute(
                        "INSERT INTO links (page_id, href, anchor_text, is_internal, is_followed) VALUES (?, ?, ?, ?, ?)",
                        (page_id, href, anchor_text, is_internal, 1)
                    )
        except Exception as e:
            logger.error(f"Errore durante il salvataggio del link '{href}' da pagina ID {page_id}: {e}")

    def _save_metadata_info(self, page_id: int, metadata: dict[str, Any]) -> None:
        if not metadata:
            return
        try:
            with self.db_manager.transaction("websites") as cursor:
                for name, content in metadata.items():
                    if isinstance(content, (list, dict)):
                        content = json.dumps(content)
                    cursor.execute(
                        "INSERT OR IGNORE INTO meta_data (page_id, meta_name, meta_content) VALUES (?, ?, ?)",
                        (page_id, name, str(content))
                    )
        except Exception as e:
            logger.error(f"Errore durante il salvataggio dei metadati per pagina ID {page_id}: {e}")

    def _setup_site_directories(self, domain: str) -> None:
        if not self.base_dirs.get("downloaded_tree"):
            logger.error("Downloaded tree directory not configured")
            return

        clean_domain = domain.replace('www.', '')
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        site_dir_name = f"{clean_domain}_{timestamp}"

        self.current_site_dir = self.base_dirs["downloaded_tree"] / site_dir_name

        try:
            self.current_site_dir.mkdir(exist_ok=True)
            subdirs = ["html", "images", "documents", "other"]
            for subdir in subdirs:
                (self.current_site_dir / subdir).mkdir(exist_ok=True)

            logger.info(f"Created site directory structure at {self.current_site_dir}")

            latest_link = self.base_dirs["downloaded_tree"] / f"{clean_domain}_latest"
            if latest_link.exists() or latest_link.is_symlink():
                 try:
                    latest_link.unlink()
                 except Exception:
                    pass
            
            try:
                latest_link.symlink_to(self.current_site_dir, target_is_directory=True)
            except OSError as e_symlink:
                logger.error(f"Errore creazione symlink '{latest_link}': {e_symlink}")

        except Exception as e:
            logger.error(f"Error creating site directories: {e}")
            self.current_site_dir = None

    def _get_file_path_for_url(self, url: str, content_type_header: str) -> tuple[Path, str]:
        if not self.current_site_dir:
            return Path("."), "error.html"

        parsed_url = urlparse(url)
        path_components = parsed_url.path.strip("/").split("/")
        
        if 'html' in content_type_header or not content_type_header:
            base_dir = self.current_site_dir / "html"
        elif any(ext in content_type_header for ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'ico']):
            base_dir = self.current_site_dir / "images"
        elif any(ext in content_type_header for ext in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf', 'csv', 'xml', 'json']):
            base_dir = self.current_site_dir / "documents"
        else:
            base_dir = self.current_site_dir / "other"
            
        if path_components and path_components[0]:
            current_dir = base_dir
            for component in path_components[:-1]:
                current_dir = current_dir / component
                try:
                    current_dir.mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
            
            if path_components[-1]:
                file_name = path_components[-1]
                if not '.' in file_name:
                    if 'html' in content_type_header: file_name += '.html'
                    elif 'xml' in content_type_header: file_name += '.xml'
                    elif 'json' in content_type_header: file_name += '.json'
                    else: file_name += '.html'
            else:
                file_name = 'index.html'
        else:
            current_dir = base_dir
            file_name = 'index.html'

        file_name = "".join(c if c.isalnum() or c in ['.', '-', '_'] else '_' for c in file_name)[:100]
        return current_dir, file_name

    def _save_robots_data(self, website_id: int, robots_data: RobotsData, robots_content: str) -> Optional[int]:
        try:
            with self.db_manager.transaction("websites") as cursor:
                cursor.execute(
                    "INSERT OR REPLACE INTO robots_txt (website_id, content, crawl_delay) VALUES (?, ?, ?)",
                    (website_id, robots_content, robots_data.crawl_delay)
                )
                robots_txt_id = cursor.lastrowid

                for rule in robots_data.rules:
                    cursor.execute(
                        "INSERT INTO robots_rules (robots_txt_id, path, allow, is_sensitive) VALUES (?, ?, ?, ?)",
                        (robots_txt_id, rule.path, rule.allow, rule.is_sensitive)
                    )

                for sitemap in robots_data.sitemaps:
                    cursor.execute(
                        "INSERT OR REPLACE INTO robots_sitemaps (robots_txt_id, url) VALUES (?, ?)",
                        (robots_txt_id, sitemap)
                    )
                return robots_txt_id
        except Exception as e:
            logger.error(f"Error saving robots.txt data: {e}")
            return None

    async def _fetch_and_parse_robots(self, base_url: str, queue: deque) -> Optional[RobotsData]:
        robots_url = urljoin(base_url, "/robots.txt")
        logger.info(f"Fetching robots.txt from {robots_url}")
        
        # Await the fetch call
        robots_content = await self.fetcher.fetch(robots_url)
        if not robots_content:
            logger.warning(f"No robots.txt found at {robots_url}")
            return None
            
        robots_data = self.robots_parser.parse(robots_content, base_url)
        self.robots_parser.print_analysis(robots_data, base_url)
        
        # Interactive choice must be done carefully to not break async flow 
        # (input is blocking, but acceptable here as it's once at startup)
        while True:
            print(f"\n{Fore.YELLOW}Do you want to respect robots.txt rules?{Style.RESET_ALL}")
            print(f"  {Fore.YELLOW}y{Style.RESET_ALL} - Yes, follow robots.txt rules (ethical)")
            print(f"  {Fore.RED}n{Style.RESET_ALL} - No, ignore robots.txt rules and crawl restricted paths")
            # Running input in thread to avoid blocking loop if possible, 
            # but simple input() is usually fine for CLI tools before massive concurrency starts
            choice = input(f"\nYour choice (y/n): ").strip().lower()
            
            if choice in ['y', 'n']:
                self.respect_robots = (choice == 'y')
                if not self.respect_robots:
                    print(f"\n{Fore.RED}Warning: robots.txt rules will be ignored.{Style.RESET_ALL}")
                    
                    disallowed_paths = [rule.path for rule in robots_data.rules 
                                      if not rule.allow and '*' not in rule.path and '?' not in rule.path]
                    
                    if disallowed_paths:
                        print(f"\n{Fore.YELLOW}Adding {len(disallowed_paths)} restricted paths to crawl queue:{Style.RESET_ALL}")
                        for path in disallowed_paths:
                            target_url = urljoin(base_url, path)
                            if path.endswith('/'):
                                print(f"  {Fore.BLUE}[DIR]{Style.RESET_ALL} {target_url}")
                            else:
                                print(f"  {Fore.MAGENTA}[FILE]{Style.RESET_ALL} {target_url}")
                            queue.append((target_url, 0))
                        
                        sensitive_paths = [path for path in disallowed_paths 
                                         if any(rule.path == path and rule.is_sensitive for rule in robots_data.rules)]
                        if sensitive_paths:
                            print(f"\n{Fore.RED}🔒 Found {len(sensitive_paths)} sensitive paths to explore:{Style.RESET_ALL}")
                            for path in sensitive_paths:
                                target_url = urljoin(base_url, path)
                                print(f"  {Fore.RED}[SENSITIVE]{Style.RESET_ALL} {target_url}")
                break
            else:
                print(f"\n{Fore.RED}Invalid choice. Please enter 'y' or 'n'.{Style.RESET_ALL}")
        
        website_id = self._get_or_create_website(self.base_domain)
        if website_id:
            self._save_robots_data(website_id, robots_data, robots_content)
        
        return robots_data

    def _should_crawl_url(self, url: str) -> bool:
        if not self.respect_robots or not self.robots_data:
            return True
        return self.robots_parser.is_allowed(url, self.robots_data.rules)

    async def start_crawl(self, start_url: str, depth_limit: int = 2, politeness_delay: float = 1.0, perform_osint_on_pages: bool = False, save_to_disk: bool = True) -> dict:
        """
        Avvia il crawling in modo asincrono.
        Gestisce KeyboardInterrupt per uscire in modo pulito e salvare i risultati.
        """
        stats = {
            'urls_visited': 0,
            'pages_saved': 0,
            'download_path': None,
            'errors': 0,
            'robots_txt': None,
            'restricted_paths_crawled': 0,
            'total_requests': 0  # Added tracking
        }
        osint_findings_summary = {
            "entities_profiled": [],
            "page_technologies": {}
        }
        
        # Settings per robustezza
        MAX_QUEUE_SIZE = 50000 # Increased limit
        MAX_CONSECUTIVE_ERRORS = 5
        consecutive_errors = 0

        self.base_domain = urlparse(start_url).netloc
        if not self.base_domain:
            logger.error(f"URL di partenza non valido: {start_url}")
            stats['errors'] +=1
            return stats

        if save_to_disk:
            self._setup_site_directories(self.base_domain)
            if not self.current_site_dir:
                stats['errors'] +=1
                return stats
            stats['download_path'] = str(self.current_site_dir)
            print(f"Content will be saved to: {self.current_site_dir}{Style.RESET_ALL}\n")

        print(f"\n{Fore.CYAN}Starting crawl of {start_url} (Mode: {'OSINT' if perform_osint_on_pages else 'Download'})")

        queue = deque([(start_url, 0)])
        self.visited_urls.clear()

        # Fetch initial robots.txt
        self.robots_data = await self._fetch_and_parse_robots(start_url, queue)
        if self.robots_data:
            stats['robots_txt'] = self.robots_data.to_dict()
            if self.robots_data.crawl_delay > politeness_delay:
                logger.info(f"Adjusting politeness delay to {self.robots_data.crawl_delay}s")
                politeness_delay = self.robots_data.crawl_delay

        if perform_osint_on_pages:
            self.db_manager.init_schema("osint")
        else:
            self.db_manager.init_schema("websites")

        # Main Crawl Loop Wrapped in Try/Except for Graceful Exit
        try:
            while queue:
                current_url, current_depth = queue.popleft()

                if current_url in self.visited_urls:
                    continue

                if current_depth > depth_limit:
                    continue

                if not self._should_crawl_url(current_url):
                    continue

                print(f"{Fore.YELLOW}Crawling{Style.RESET_ALL}: {current_url} (Profondità: {current_depth})")
                self.visited_urls.add(current_url)
                stats['urls_visited'] += 1
                stats['total_requests'] += 1

                await asyncio.sleep(politeness_delay)
                
                # Async fetch
                page_response = await self.fetcher.fetch_full_response(current_url)

                # Gestione errori consecutivi / Anti-Flooding
                if page_response:
                    if page_response.status_code in [429, 503, 504]:
                        consecutive_errors += 1
                        logger.warning(f"Server instabile/busy ({page_response.status_code}). Errore {consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}")
                        if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                            print(f"\n{Fore.RED}Troppi errori consecutivi dal server. Interruzione di sicurezza.{Style.RESET_ALL}")
                            break
                        await asyncio.sleep(politeness_delay * consecutive_errors) # Backoff
                        continue
                    else:
                        consecutive_errors = 0 # Reset se successo

                if not page_response or not page_response.content:
                    stats['errors'] += 1
                    continue

                page_content_bytes = page_response.content
                page_content_text = None
                content_type_header = page_response.headers.get('Content-Type', '').lower()

                # Save to disk
                if save_to_disk and not perform_osint_on_pages:
                    try:
                        save_dir, file_name = self._get_file_path_for_url(current_url, content_type_header)
                        save_path = save_dir / file_name
                        save_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Definiamo funzione sincrona per scrittura file
                        def write_file():
                            with open(save_path, 'wb') as f:
                                f.write(page_content_bytes)
                        
                        await asyncio.to_thread(write_file)
                        stats['pages_saved'] += 1

                    except Exception as e:
                        logger.error(f"Errore salvataggio {current_url}: {e}")
                        stats['errors'] += 1

                parsed_data = {}
                page_id = None

                if any(ct in content_type_header for ct in ['html', 'xml', 'text', 'json']):
                    try:
                        encoding_to_try = page_response.encoding or 'utf-8'
                        page_content_text = page_content_bytes.decode(encoding_to_try, errors='replace')
                        parsed_data = self.parser.parse(page_content_text, current_url)

                        if not perform_osint_on_pages:
                            page_id = self._save_page_info(
                                url=current_url,
                                title=parsed_data.get("title", ""),
                                status_code=page_response.status_code,
                                content_length=len(page_content_bytes),
                                content_type=content_type_header
                            )

                            if page_id and parsed_data.get("metadata"):
                                self._save_metadata_info(page_id, parsed_data["metadata"])

                    except Exception as e:
                        logger.warning(f"Errore parsing {current_url}: {e}")

                # Gestione Link
                if parsed_data and "links" in parsed_data and current_depth < depth_limit:
                    for link_info in parsed_data["links"]:
                        if not (link_url := link_info.get("url")): continue
                        if not (normalized_link := self._normalize_url(link_url, current_url)): continue

                        is_internal = self._is_internal_url(normalized_link)
                        
                        if not perform_osint_on_pages and page_id:
                            self._save_link_info(page_id, normalized_link, link_info.get("text", ""), is_internal)

                        if is_internal and normalized_link not in self.visited_urls:
                            # FIX Coda Piena: limite aumentato
                            if len(queue) < MAX_QUEUE_SIZE:
                                queue.append((normalized_link, current_depth + 1))
                            else:
                                logger.debug(f"Coda crawler piena ({MAX_QUEUE_SIZE}), link ignorato: {normalized_link}")

                # OSINT Logic
                if perform_osint_on_pages and page_content_text and self.osint_extractor:
                    print(f"    {Fore.MAGENTA}Avvio OSINT per pagina: {current_url}{Style.RESET_ALL}")
                    try:
                        # Nota: Se extract_emails ecc sono molto lenti, considerare asyncio.to_thread
                        # Per ora manteniamo sincrono per semplicità di migrazione logica
                        page_emails = extract_emails(page_content_text)
                        page_phones = extract_phone_numbers(page_content_text)
                        filtered_emails = filter_emails(page_emails, self.base_domain, logger)
                        filtered_phones = filter_phone_numbers(page_phones)

                        for email in filtered_emails:
                            if email not in self.already_profiled_in_session:
                                print(f"      {Fore.BLUE}Profilazione email trovata: {email}{Style.RESET_ALL}")
                                # Se profile_email fa chiamate di rete (sincrone), bloccherà qui.
                                # Idealmente anche osint_extractor andrebbe migrato, ma per ora va bene così.
                                email_profile_result = self.osint_extractor.profile_email(email)
                                osint_findings_summary["entities_profiled"].append({
                                    "page_url": current_url,
                                    "entity_type": "email",
                                    "entity": email,
                                    "profile_details": email_profile_result
                                })
                                self.already_profiled_in_session.add(email)

                        if filtered_phones:
                            osint_findings_summary["entities_profiled"].append({
                                "page_url": current_url,
                                "entity_type": "phone_numbers_found",
                                "entity": list(filtered_phones),
                                "profile_details": {"message": "Numeri estratti"}
                            })

                        # Tech detection
                        soup_from_parser = BeautifulSoup(page_content_text, 'html.parser')
                        page_tech = {}
                        tf = detect_framework(soup_from_parser, page_response.headers, page_content_text, current_url)
                        if tf and tf != "Unknown": page_tech["framework_cms"] = tf
                        
                        tjs = detect_js_libraries(soup_from_parser, page_content_text)
                        if tjs: page_tech["js_libraries"] = tjs
                        
                        ta = detect_analytics(page_content_text)
                        if ta: page_tech["analytics"] = ta

                        if page_tech:
                            osint_findings_summary["page_technologies"][current_url] = page_tech

                    except Exception as e_osint:
                        logger.error(f"Errore OSINT per {current_url}: {e_osint}")

        except (KeyboardInterrupt, asyncio.CancelledError):
            print(f"\n\n{Fore.RED}!!! INTERRUZIONE RILEVATA (CTRL+C) !!!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Il crawling è stato interrotto manualmente.{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Salvataggio dei dati raccolti finora...{Style.RESET_ALL}")
            # Non rilanciamo l'errore, permettiamo al codice di procedere al return stats

        except Exception as e:
            logger.error(f"Errore critico nel loop di crawling: {e}", exc_info=True)
            stats['errors'] += 1

        # Finalizzazione (eseguita anche se CTRL+C)
        if perform_osint_on_pages:
            try:
                from scraper.utils.osint_sources import find_brand_social_profiles
                clean_brand = self.base_domain.lower().replace('www.', '').split('.')[0]
                
                print(f"\n{Fore.CYAN}Ricerca profili social per '{clean_brand}'...{Style.RESET_ALL}")
                # Eseguiamo in thread separato se è bloccante
                social_results = await asyncio.to_thread(find_brand_social_profiles, clean_brand, logger, self.base_dirs)
                
                if social_results and not social_results.get("error"):
                    profiles = social_results.get("profiles", {})
                    if profiles:
                        print(f"{Fore.YELLOW}✓ Trovati {len(profiles)} profili social{Style.RESET_ALL}")
                        for platform, data in profiles.items():
                            osint_findings_summary["entities_profiled"].append({
                                "page_url": start_url,
                                "entity_type": "social_profile",
                                "entity": data.get("username", clean_brand),
                                "profile_details": {"platform": platform, "url": data.get("url")}
                            })
            except Exception as e:
                logger.error(f"Errore social search: {e}")
            
            stats['osint_summary'] = osint_findings_summary

        return stats