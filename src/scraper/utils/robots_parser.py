import logging
import re
from dataclasses import dataclass, field
from typing import List, Set, Dict
from urllib.parse import urljoin, urlparse
from colorama import Fore, Style

logger = logging.getLogger("scraper.robots_parser")

@dataclass
class RobotsRule:
    path: str
    allow: bool = False
    is_sensitive: bool = False

@dataclass

# Chiamato da Crawler per analizzare robots.txt
class RobotsData:
    '''
    Funzione: RobotsData
    Classe che rappresenta i dati estratti da un file robots.txt.
    Parametri formali:
        self -> Riferimento all'istanza della classe
        rules: List[RobotsRule] -> Lista di oggetti RobotsRule che rappresentano le regole di accesso
        sitemaps: List[str] -> Lista di URL di sitemap
        sensitive_paths: Set[str] -> Set di percorsi che sono considerati sensibili
    '''
    rules: List[RobotsRule] = field(default_factory=list)
    sitemaps: List[str] = field(default_factory=list)
    sensitive_paths: Set[str] = field(default_factory=set)
    crawl_delay: float = 0.0

    def to_dict(self) -> Dict:
        '''
        Funzione: to_dict
        Converte i dati in un dizionario JSON.
        Parametri formali:
            self -> Riferimento all'istanza della classe
        Valore di ritorno:
            Dict -> Dizionario JSON contenente i dati estratti
        '''
        return {
            "rules": [{"path": r.path, "allow": r.allow, "is_sensitive": r.is_sensitive} for r in self.rules],
            "sitemaps": list(self.sitemaps),
            "sensitive_paths": list(self.sensitive_paths),
            "crawl_delay": self.crawl_delay
        }

class RobotsParser:
    '''
    Funzione: RobotsParser
    Classe che analizza e gestisce i dati di un file robots.txt.
    Parametri formali:
        self -> Riferimento all'istanza della classe
        SENSITIVE_PATTERNS -> Lista di pattern di percorsi sensibili
    '''
    SENSITIVE_PATTERNS = [
        r'admin', r'backup', r'staging', r'dev', r'test', r'beta',
        r'wp-admin', r'administrator', r'login', r'user', r'console',
        r'dashboard', r'private', r'secret', r'internal', r'config',
        r'setup', r'install', r'phpmy', r'sql', r'database', r'db',
        r'temp', r'tmp', r'old', r'bak', r'.git', r'.svn', r'.env',
        r'api/internal', r'api/private', r'api/v\d+/admin'
    ]

    def __init__(self):
        self.sensitive_patterns = [re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_PATTERNS]

    def _is_sensitive_path(self, path: str) -> bool:
        '''
        Funzione: _is_sensitive_path
        Verifica se un percorso è sensibile in base ai pattern definiti.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            path -> Percorso da verificare
        Valore di ritorno: 
            bool -> True se il percorso è sensibile, False altrimenti
        '''
        return any(pattern.search(path) for pattern in self.sensitive_patterns) 

    def parse(self, robots_content: str, base_url: str) -> RobotsData:
        '''
        Funzione: parse
        Analizza il contenuto di un file robots.txt e restituisce i dati estratti.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            robots_content -> Contenuto del file robots.txt
            base_url -> URL base del sito
        Valore di ritorno:
            RobotsData -> Oggetto RobotsData contenente i dati estratti
        '''
        data = RobotsData()
        current_agent = "*"
        in_relevant_agent = False

        for line in robots_content.splitlines():
            line = line.strip().lower()
            if not line or line.startswith('#'):
                continue

            if line.startswith('user-agent:'):
                agent = line.split(':', 1)[1].strip()
                in_relevant_agent = agent == '*'
                current_agent = agent
                continue

            if current_agent != '*' and not in_relevant_agent:
                continue

            if line.startswith('allow:'):
                path = line.split(':', 1)[1].strip()
                full_path = urljoin(base_url, path)
                rule = RobotsRule(path=path, allow=True, is_sensitive=self._is_sensitive_path(path)) 
                data.rules.append(rule)
                if rule.is_sensitive:
                    data.sensitive_paths.add(path) 

            elif line.startswith('disallow:'):
                path = line.split(':', 1)[1].strip()
                full_path = urljoin(base_url, path)
                rule = RobotsRule(path=path, allow=False, is_sensitive=self._is_sensitive_path(path))
                data.rules.append(rule)
                if rule.is_sensitive:
                    data.sensitive_paths.add(path)

            elif line.startswith('sitemap:'):
                sitemap = line.split(':', 1)[1].strip()
                data.sitemaps.append(sitemap)

            elif line.startswith('crawl-delay:'):
                try:
                    data.crawl_delay = float(line.split(':', 1)[1].strip())
                except ValueError:
                    pass

        return data

    def is_allowed(self, url: str, rules: List[RobotsRule]) -> bool:
        """Check if a URL is allowed based on robots rules"""
        path = urlparse(url).path
        if not path:
            path = "/"

        # Sort rules by length (most specific first)
        sorted_rules = sorted(rules, key=lambda x: len(x.path), reverse=True)
        
        for rule in sorted_rules:
            if path.startswith(rule.path):
                return rule.allow
        
        return True  # Default allow if no matching rules

    def print_analysis(self, data: RobotsData, base_url: str):
        """Print a colored analysis of robots.txt data"""
        print(f"\n{Fore.CYAN}=== Robots.txt Analysis for {base_url} ==={Style.RESET_ALL}")
        
        if data.sensitive_paths:
            print(f"\n{Fore.RED}🔍 Sensitive Paths Found:{Style.RESET_ALL}")
            for path in sorted(data.sensitive_paths):
                print(f"  • {path}")
        
        print(f"\n{Fore.YELLOW}📋 Access Rules:{Style.RESET_ALL}")
        for rule in data.rules:
            allow_text = 'Allow' if rule.allow else 'Disallow'
            sensitive_mark = f" {Fore.RED}(!){Style.RESET_ALL}" if rule.is_sensitive else ""
            print(f"  • {allow_text}: {rule.path}{sensitive_mark}")
        
        if data.sitemaps:
            print(f"\n{Fore.BLUE}🗺 Sitemaps:{Style.RESET_ALL}")
            for sitemap in data.sitemaps:
                print(f"  • {sitemap}")
        
        if data.crawl_delay:
            print(f"\n{Fore.MAGENTA}⏱ Crawl-delay: {data.crawl_delay} seconds{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}\n")