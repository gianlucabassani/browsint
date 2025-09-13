#  Contiene funzioni per validare input (es. dominio)

import re
from colorama import Fore, Style

# Chiamato da ScraperCLI per validare domini
def validate_domain(domain: str) -> tuple[bool, str | None]:
        '''
        Funzione: _validate_domain
        Valida e pulisce un input che dovrebbe essere un nome di dominio.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            str domain -> La stringa da validare come dominio
        Valore di ritorno:
            tuple[bool, str | None] -> Una tupla con un booleano (valido/non valido) e il dominio pulito (o None se non valido)
        '''
        domain = str(domain).strip().lower()

        if not domain:
            print(f"{Fore.RED}✗ Nessun dominio inserito")
            return False, None

        if domain.startswith(("http://", "https://")):
            domain = domain.split("://", 1)[1]

        domain = domain.split("/", 1)[0]
        domain = domain.split("?", 1)[0]
        domain = domain.split(":", 1)[0]

        if domain.startswith("www."):
            domain = domain[4:]

        domain_pattern = r"^((?!-)[a-z0-9-]{1,63}(?<!-)\.)+[a-z]{2,63}$"

        '''
        Il pattern regex verifica che il dominio:
        ^((?!-) - Non inizi con un trattino
        [a-z0-9-]{1,63} - Contenga solo lettere minuscole, numeri e trattini, con una lunghezza da 1 a 63 caratteri
        (?<!-) - Non finisca con un trattino
        \.) - Seguito da un punto
        [a-z]{2,63}$ - Termini con un TLD di 2 a 63 caratteri (es. .com, .org, .it)
        Questo pattern è conforme agli standard dei nomi di dominio 
        '''

        if not re.match(domain_pattern, domain):
            print(f"{Fore.RED}✗ Formato dominio non valido: '{domain}'. Usare: example.com")
            return False, None

        return True, domain

