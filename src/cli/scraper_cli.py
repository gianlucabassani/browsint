"""
Main CLI class for the Browsint application.
"""
import sys
from pathlib import Path
from textwrap import indent
from urllib.parse import urlparse
import json
import logging
import re
import time
from datetime import datetime
from colorama import Fore, Style
from tabulate import tabulate
import validators
import os
from config import get_api_keys, load_env, set_env_key, unset_env_key
from typing import Optional

# Import the database manager
from db.manager import DatabaseManager

# Import scraper components
from scraper.extractors.osint_extractor import OSINTExtractor
from scraper.fetcher import WebFetcher
from scraper.parser import WebParser
from scraper.crawler import Crawler

# Import menu modules
from .menus import osint_menu, download_menu, db_menu, scraping_menu
# Import utilities
from .utils import json_serial, clear_screen, prompt_for_input, confirm_action

# Initialize loggers
logger = logging.getLogger("browsint.cli")
crawler_logger = logging.getLogger("scraper.crawler")
fetcher_logger = logging.getLogger("scraper.fetcher")
db_logger = logging.getLogger("DatabaseManager")

class ScraperCLI:
    '''Gestisce l'interfaccia a riga di comando per lo strumento OSINT (ORCHESTRATORE).'''

    def __init__(self):
        '''Inizializza l'interfaccia a riga di comando per lo strumento OSINT.'''
        # Prima chiamiamo setup per inizializzare i percorsi
        self.setup()
        
        # Carichiamo le API keys dalle variabili d'ambiente e dal file .env
        self.api_keys = self._load_api_keys_from_env()
        
        # Prefer singleton getter for DB when available, otherwise fallback
        try:
            self.db_manager = DatabaseManager.get_instance()
        except Exception:
            # If manager has no get_instance, fallback to direct instantiation
            self.db_manager = DatabaseManager()

        # Delay heavy components until needed (lazy init via properties)
        self._osint_extractor = None
        self._web_fetcher = None
        self._web_parser = None
        self._crawler = None

        self.running = True

    def setup(self) -> None:
        '''Inizializza la configurazione di base delle directory e dei file.'''
        # use resolve() to make base_dir robust when packaged or symlinked
        self.base_dir = Path(__file__).parent.parent.parent.resolve()
        self.env_file = self.base_dir / ".env"
        self.data_dir = self.base_dir / "data"

        # Crea il file .env se non esiste
        if not self.env_file.exists():
            self.env_file.touch()

        self.dirs = {
            "sites": self.data_dir / "url_downloaded",
            "analysis": self.data_dir / "site_analysis",
            "reports": self.data_dir / "downloaded_reports",
            "osint_exports": self.data_dir / "osint_exports",
            "downloaded_tree": self.data_dir / "downloaded_tree",
            "osint_usernames": self.data_dir / "osint_usernames",
            "pdf_reports": self.data_dir / "pdf_reports"
        }

        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {dir_path}")

    def _load_api_keys_from_env(self) -> dict:
        '''Carica le API keys dalle variabili d'ambiente e dal file .env.'''
        # delegate to centralized config helper
        try:
            return get_api_keys(self.env_file)
        except Exception:
            # Fallback: attempt to load env and use helper again; return empty dict if still failing
            try:
                load_env(self.env_file)
                return get_api_keys(self.env_file)
            except Exception:
                return {}

    def show_banner(self) -> None:
        '''Mostra un banner ASCII art all'avvio dell'applicazione.'''

        banner = fr"""{Fore.CYAN}
██████╗ ██████╗  ██████╗ ██╗    ██╗███████╗██╗███╗   ██╗████████╗
██╔══██╗██╔══██╗██╔═══██╗██║    ██║██╔════╝██║████╗  ██║╚══██╔══╝
██████╔╝██████╔╝██║   ██║██║ █╗ ██║███████╗██║██╔██╗ ██║   ██║   
██╔══██╗██╔══██╗██║   ██║██║███╗██║╚════██║██║██║╚██╗██║   ██║   
██████╔╝██║  ██║╚██████╔╝╚███╔███╔╝███████║██║██║ ╚████║   ██║   
╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚══╝╚══╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝   
            {Fore.YELLOW}Web Intelligence & OSINT Collection Tool{Style.RESET_ALL}
            {Fore.BLUE}Version BETA{Style.RESET_ALL}

{Fore.LIGHTBLUE_EX}{'='*60}{Style.RESET_ALL}

            """
        print(banner)
        time.sleep(0.5)

    def run(self) -> None:
        '''Avvia il loop principale dell'applicazione CLI.'''
        try:
            self.show_banner()

            required_keys = ["shodan", "whoisxml", "hunterio", "hibp"]
            if self.api_keys:
                missing_keys = [key for key in required_keys if key not in self.api_keys or not self.api_keys.get(key)]
                if missing_keys:
                    print(f"{Fore.YELLOW}⚠ API keys mancanti o non valorizzate per: {', '.join(missing_keys)}")
                    print(f"{Fore.YELLOW}⚠ Alcune funzionalità OSINT potrebbero non funzionare correttamente.{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠ File di configurazione API non caricato o vuoto. Molte funzionalità OSINT saranno limitate.{Style.RESET_ALL}")

            while self.running:
                try:
                    choice = self.display_main_menu()
                    self._handle_main_menu_choice(choice)
                except KeyboardInterrupt:
                    print(f"\n{Fore.YELLOW}Grazie per aver usato Browsint! Arrivederci!{Style.RESET_ALL}")
                    return

        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}Grazie per aver usato Browsint! Arrivederci!{Style.RESET_ALL}")
        except Exception as e:
            logger.error(f"Errore generale nell'applicazione: {e}", exc_info=True)
            print(f"\n{Fore.RED}✗ Si è verificato un errore imprevisto: {e}{Style.RESET_ALL}")

    def display_main_menu(self) -> str:
        '''Visualizza il menu principale e restituisce la scelta dell'utente.'''
        print(f"{Fore.BLUE}{'═' * 40}")
        print(f"█ {Fore.WHITE}{'BROWSINT - MENU PRINCIPALE':^36}{Fore.BLUE} █")
        print(f"{'═' * 40}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}1.{Style.RESET_ALL} Web Crawl & Download")
        print(f"{Fore.YELLOW}2.{Style.RESET_ALL} OSINT Web Scraping")
        print(f"{Fore.YELLOW}3.{Style.RESET_ALL} Profilazione OSINT")
        print(f"{Fore.YELLOW}4.{Style.RESET_ALL} Opzioni di sistema\n")
        print(f"{Fore.YELLOW}0.{Style.RESET_ALL} Esci")
        return prompt_for_input(f"{Fore.CYAN}Scelta: {Style.RESET_ALL}")
    
    def _handle_main_menu_choice(self, choice: str):
        '''Gestisce la scelta dell'utente nel menu principale.'''
        match choice:
            case "1": self._download_websites_menu()
            case "2": self._scrape_crawl_websites_menu()
            case "3": self._osint_menu()
            case "4": self._options_menu()
            case "0":
                print(f"\n{Fore.YELLOW}Grazie per aver usato Browsint! Arrivederci!{Style.RESET_ALL}")
                self.running = False
            case _:
                print(f"{Fore.RED}✗ Scelta non valida")
                input(f"{Fore.CYAN}\nPremi INVIO per continuare...{Style.RESET_ALL}")

    def _download_websites_menu(self):
        '''Menu per il download di siti web.'''
        while True:
            choice = download_menu.display_download_menu()
            if choice == "0":
                break
            download_menu.handle_download_choice(self, choice)

    def _scrape_crawl_websites_menu(self):
        '''Menu per lo scraping e crawling di siti web.'''
        while True:
            choice = scraping_menu.display_scraping_menu()
            if choice == "0":
                break
            scraping_menu.handle_scraping_choice(self, choice)

    def _osint_menu(self):
        '''Menu per le funzionalità OSINT.'''
        while True:
            choice = osint_menu.display_osint_menu()
            if choice == "0":
                break
            osint_menu.handle_osint_choice(self, choice)

    def _options_menu(self):
        '''Menu per le opzioni di sistema.'''
        while True:
            choice = db_menu.display_db_menu()
            if choice == "0":
                break
            db_menu.handle_db_choice(self, choice)
    
    # Lazy-loaded components to avoid eager heavy instantiation
    @property
    def osint_extractor(self) -> OSINTExtractor:
        if self._osint_extractor is None:
            self._osint_extractor = OSINTExtractor(
                api_keys=self.api_keys,
                data_dir=self.data_dir,
                dirs=self.dirs
            )
        return self._osint_extractor

    @osint_extractor.setter
    def osint_extractor(self, value):
        self._osint_extractor = value

    @property
    def web_fetcher(self) -> WebFetcher:
        if self._web_fetcher is None:
            self._web_fetcher = WebFetcher()
        return self._web_fetcher

    @web_fetcher.setter
    def web_fetcher(self, value):
        self._web_fetcher = value

    @property
    def web_parser(self) -> WebParser:
        if self._web_parser is None:
            self._web_parser = WebParser()
        return self._web_parser

    @web_parser.setter
    def web_parser(self, value):
        self._web_parser = value

    @property
    def crawler(self) -> Crawler:
        if self._crawler is None:
            self._crawler = Crawler(
                fetcher=self.web_fetcher,
                parser=self.web_parser,
                db_manager=self.db_manager,
                osint_extractor=self.osint_extractor,
                base_dirs=self.dirs
            )
        return self._crawler

    @crawler.setter
    def crawler(self, value):
        self._crawler = value
    
            
    def _get_validated_url_input(self, prompt_message: str) -> Optional[str]:
        '''
        Ottiene e valida un input URL.
        '''
        url = prompt_for_input(prompt_message)
        if not url:
            print(f"{Fore.RED}✗ L'URL non può essere vuoto.{Style.RESET_ALL}")
            return None
        if not validators.url(url):
            print(f"{Fore.RED}✗ URL non valido.{Style.RESET_ALL}")
            return None
        return url

    def _get_depth_input(self, default: int = 2, message: str = None) -> int:
        '''
        Ottiene e valida un input di profondità di crawl.
        '''
        if message is None:
            message = f"Inserisci il limite di profondità (default: {default}): "
        depth_str = prompt_for_input(message)
        return int(depth_str) if depth_str.isdigit() else default
