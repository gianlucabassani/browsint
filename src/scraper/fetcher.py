import hashlib
import logging
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, NamedTuple,  Union

import requests
from .utils.clients import _safe_get

logger = logging.getLogger("scraper.fetcher")

class FetchResponse(NamedTuple): 
    '''
    Funzione: FetchResponse
    Rappresenta una risposta completa da una richiesta HTTP.
    Attributi:
        NamedTuple -> Classe per rappresentare una tupla con nomi di attributi
    
    Parametri formali:
        status_code: int -> Codice di stato HTTP della risposta
        content: bytes | None -> Contenuto della risposta in formato byte, None se non disponibile
        headers: requests.structures.CaseInsensitiveDict -> Intestazioni della risposta
        url: str -> URL della richiesta
        encoding: str | None -> Codifica del contenuto, None se non specificata

    Valore di ritorno:
        None -> Il costruttore non restituisce un valore esplicito
    '''
    status_code: int
    content: bytes | None
    headers: requests.structures.CaseInsensitiveDict
    url: str
    encoding: str | None

class WebFetcher:
    '''
    Funzione: WebFetcher
    Recupera contenuti web con gestione di errori, retry e politeness.
    Parametri formali:
        self -> Riferimento all'istanza della classe
        str | None cache_dir -> Directory per la cache delle pagine (None per disabilitare)
        str | None user_agent -> User-Agent personalizzato che identifica il crawler
        tuple[float, float] delay_range -> Range (min, max) di attesa tra le richieste in secondi
    Valore di ritorno:
        None -> Il costruttore non restituisce un valore esplicito
    '''

    def __init__(
        self,
        cache_dir: str | None = None, # param opzionale che può essere stringa o none
        user_agent: str | None = None,
        delay_range: tuple[float, float] = (1.0, 3.0),
    ):
        self.headers = {
            "User-Agent": user_agent or "Browsint/1.0 Research Bot",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        self.delay_range = delay_range
        self.last_request_time: float = 0.0

        self.cache_enabled = cache_dir is not None
        if self.cache_enabled:
            self.cache_dir = Path(cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"Cache attivata in {self.cache_dir}")

    def _get_cache_path(self, url: str) -> Path:
        '''
        Funzione: _get_cache_path
        Genera un percorso file univoco per l'URL nella cache.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            str url -> L'URL per cui generare il percorso cache
        Valore di ritorno:
            Path -> Percorso completo del file di cache
        '''
        url_hash = hashlib.md5(url.encode()).hexdigest() # formatta l'url in un hash md5
        return self.cache_dir / f"{url_hash}.html"

    def _check_cache(self, url: str) -> str | None:
        '''
        Funzione: _check_cache
        Verifica se l'URL è in cache e restituisce il contenuto testuale.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            str url -> L'URL da cercare in cache
        Valore di ritorno:
            Optional[str] -> Il contenuto della pagina se presente in cache, altrimenti None
        '''
        if not self.cache_enabled:
            return None

        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            logger.debug(f"Cache hit per {url}")
            try:
                with open(cache_path, encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Errore lettura cache per {url}: {e}")

        return None

    def _save_to_cache(self, url: str, content: str) -> bool:
        '''
        Funzione: _save_to_cache
        Salva il contenuto testuale nella cache.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            str url -> L'URL associato al contenuto
            str content -> Il contenuto HTML da salvare
        Valore di ritorno:
            bool -> True se il salvataggio è avvenuto con successo, False altrimenti
        '''
        if not self.cache_enabled:
            return False

        try:
            cache_path = self._get_cache_path(url)
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.warning(f"Impossibile salvare in cache {url}: {e}")
            return False

    def _respect_politeness(self) -> None:
        '''
        Funzione: _respect_politeness
        Attende per rispettare le politiche di politeness (ritardo tra richieste).
        Parametri formali:
            self -> Riferimento all'istanza della classe
        Valore di ritorno:
            None -> La funzione non restituisce un valore
        '''
        current_time = time.time()
        elapsed = current_time - self.last_request_time

        min_delay = self.delay_range[0]
        if elapsed < min_delay:
            sleep_time = min_delay - elapsed
            logger.debug(f"Attesa di {sleep_time:.2f}s per politeness")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def fetch(self, url: str, force_download: bool = False, timeout: int = 30, retries: int = 3) -> str | None:
        '''
        Funzione: fetch
        Recupera il contenuto testuale di un URL, con opzioni di cache, timeout e retry.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            str url -> L'URL da scaricare
            bool force_download -> Forzare il download anche se presente in cache
            int timeout -> Timeout della richiesta in secondi
            int retries -> Numero di tentativi in caso di errore
        Valore di ritorno:
            str | None -> Il contenuto testuale della pagina o None in caso di fallimento
        '''
        response_obj = self.fetch_full_response(url, force_download, timeout, retries)
        # Se la risposta è in cache e non forziamo il download, restituiamo il contenuto dalla cache
        if response_obj and response_obj.content:
            try:
                # Prova a decodificare il contenuto in base alla codifica apparente
                return response_obj.content.decode(response_obj.encoding if response_obj.encoding else 'utf-8', errors='replace')
            except Exception as e:
                logger.warning(f"Errore decodifica contenuto testuale per {url}: {e}")
                return None
        return None

    def fetch_full_response(self, url: str, force_download: bool = False, timeout: int = 30, retries: int = 3) -> FetchResponse | None:
        '''
        Funzione: fetch_full_response
        Recupera il contenuto completo (status, content, headers, etc.) di un URL.
        Parametri formali:
            self -> Riferimento all'istanza della classe
            str url -> L'URL da scaricare
            bool force_download -> Forzare il download (ignora cache)
            int timeout -> Timeout della richiesta in secondi
            int retries -> Numero di tentativi in caso di errore
        Valore di ritorno:
            FetchResponse | None -> Un oggetto FetchResponse contenente i dati della risposta, o None in caso di fallimento
        '''
        self._respect_politeness()
        attempt = 0
        while attempt < retries:
            try:
                logger.info(f"Download completo {url} (tentativo {attempt+1}/{retries})")
                response = _safe_get(url, headers=self.headers, timeout=timeout, allow_redirects=True)

                content_bytes = response.content

                return FetchResponse(
                    status_code=response.status_code,
                    content=content_bytes,
                    headers=response.headers,
                    url=response.url,
                    encoding=response.apparent_encoding
                )

            except requests.RequestException as e:
                logger.warning(f"Errore durante il download completo di {url}: {e}")

            attempt += 1
            if attempt < retries:
                sleep_time = random.uniform(2, 5) * attempt
                logger.debug(f"Attendo {sleep_time:.2f} secondi prima di riprovare")
                time.sleep(sleep_time)

        logger.error(f"Impossibile scaricare (completo) {url} dopo {retries} tentativi")
        return None