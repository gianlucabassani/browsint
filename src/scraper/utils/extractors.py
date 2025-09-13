# Contiene funzioni per estrarre pattern specifici (email, numeri di telefono) da testo grezzo e per filtrare questi risultati

import re
import phonenumbers
import logging
from typing import Set

logger = logging.getLogger("osint.extractors")

# Chiamato da OSINTExtractor per estrarre email
def extract_emails(text: str) -> set:
    '''
    Funzione: _extract_emails
    Estrae indirizzi email da una stringa di testo con logica di validazione e filtro per i falsi positivi.
    Parametri formali:
        self -> Riferimento all'istanza della classe
        str text -> La stringa di testo da cui estrarre le email
    Valore di ritorno:
        set -> Un set contenente gli indirizzi email unici e validi trovati
    '''
    email_pattern = r'\b[A-Za-z0-9][A-Za-z0-9._%+-]{1,64}@(?:[A-Za-z0-9-]{1,63}\.){1,8}[A-Za-z]{2,63}\b' 
    
    '''
    Pattern regex per identificare indirizzi email:
    - \b[A-Za-z0-9][A-Za-z0-9._%+-]{1,64} - Inizia con un carattere alfanumerico seguito da uno o più caratteri alfanumerici, punti, trattini o underscore
    - @ - Segue il simbolo @
    - (?:[A-Za-z0-9-]{1,63}\.){1,8} - Segue uno o più domini, ciascuno composto da 1 a 63 caratteri alfanumerici o trattini, seguito da un punto
    - [A-Za-z]{2,63} - Termina con un dominio di primo livello di 2 a 63 caratteri alfanumerici
    - \b - Assicura che l'email sia delimitata da spazi o altri caratteri non alfanumerici
    - Il pattern è progettato per essere flessibile e catturare la maggior parte degli indirizzi email validi, POTREBBE INCLUDERE FALSI POSITIVI!
    '''
    excluded_domains = [
        'example.com', 'domain.com', 'yoursite.com', 'yourdomain.com',
        'example.org', 'email.com', 'test.com', 'sample.com' 
    ] # Domini comuni di esempio o generici da escludere

    excluded_patterns = [
        r'^[0-9a-f]{32}@', # MD5 hash pattern
        r'^[0-9a-f]{8}[0-9a-f]{4}[0-9a-f]{4}[0-9a-f]{4}[0-9a-f]{12}@', # UUID pattern
    ]

    excluded_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.css', '.js', '.pdf', '.doc', '.mp3', '.mp4']

    emails = set()
    for e in re.findall(email_pattern, text): # trova tutte le regex nel text 
        e_lower = e.lower()

        if any(ext in e_lower for ext in excluded_extensions): 
            continue

        should_skip = False
        for pattern in excluded_patterns:
            if re.match(pattern, e_lower):
                should_skip = True
                break

        if should_skip:
            continue

        domain_part = e_lower.split('@')[1] # Ottieni la parte del dominio dell'email
        if any(domain_part == excl_domain for excl_domain in excluded_domains): 
            continue

        local_part = e_lower.split('@')[0] # Ottieni la parte locale dell'email
        if len(set(local_part)) <= 2 and len(local_part) > 4:
            continue

        emails.add(e_lower) # aggiunge l'email al set se supera i controlli

    return emails

def filter_emails(emails: Set[str], domain: str, logger: logging.Logger, keep_service_emails: bool = False) -> Set[str]:
    '''
    Funzione: filter_emails
    Applica un filtro agli indirizzi email per rimuovere falsi positivi basati su pattern specifici
    o domini di servizio e dare priorità alle email interne o con termini significativi.

    Parametri formali:
        set emails -> Un set contenente gli indirizzi email da filtrare
        str domain -> Il dominio del sito associato (per dare priorità alle email interne)
        logging.Logger logger -> L'istanza del logger da utilizzare per i messaggi
        bool keep_service_emails -> Flag per indicare se mantenere le email con domini di servizio noti

    Valore di ritorno:
        set -> Un set contenente gli indirizzi email filtrati
    '''

    filtered_emails: Set[str] = set() # Inizializza un set per le email filtrate
    original_count = len(emails) # conta le email originali
    removed_count = 0

    # Domini di servizio noti che spesso non sono contatti utili
    service_domains = {
        'sentry.io',
        'sentry.wixpress.com',
        'sentry-next.wixpress.com',
        'contactprivacy.com',
        'whois.tucows.com',
        'domainsbyproxy.com',
        'secureserver.net',
        'hostmaster.sk',
        'nic.it',
        # Aggiungere altri domini di servizio o proxy noti qui
    }

    # Pattern regex per identificare local part che sembrano ID univoci o hash
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$', re.IGNORECASE)
    long_hex_pattern = re.compile(r'^[0-9a-f]{12,64}$', re.IGNORECASE)

    '''
    Pattern regex per identificare local part che sembrano UUID o lunghe stringhe esadecimali:
    - ^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$:
        - Inizia con 8 caratteri esadecimali, seguiti da un trattino opzionale
        - Poi 4 caratteri esadecimali, un altro trattino opzionale
        - Poi 4 caratteri esadecimali, un altro trattino opzionale
        - Poi 4 caratteri esadecimali, un altro trattino opzionale
        - Infine 12 caratteri esadecimali
    - ^[0-9a-f]{12,64}$:
        - Inizia con 12 a 64 caratteri esadecimali, senza trattini
    Questi pattern sono progettati per catturare local part che sembrano UUID o hash
    '''
    
    # Termini comuni nella local part che indicano un contatto legittimo
    meaningful_terms = {'info', 'contact', 'support', 'hello', 'sales', 'admin', 'contatti', 'assistenza', 'ufficio', 'office', 'segreteria', 'privacy', 'legal', 'team', 'staff', 'help', 'customer', 'clienti', 'richieste', 'richiesta', 'richieste generali', 'partnerships', 'marketing'}

    # Normalizza il dominio per confronto
    normalized_domain = domain.lower()
    # Considera anche sottodomini comuni come mail.dominio.com
    normalized_mail_domain = f"mail.{normalized_domain}"
    # Potresti voler considerare anche il dominio senza www se presente
    normalized_domain_no_www = normalized_domain.replace("www.", "")


    for email in emails:
        try:
            # Assicurati che l'email abbia il formato atteso prima di splittare
            if '@' not in email:
                logger.debug(f"Skipping invalid email format during filtering: {email}")
                removed_count += 1
                continue

            local_part, email_domain = email.split('@', 1)
            local_part = local_part.lower()
            email_domain = email_domain.lower()

            # --- Regole di ESCLUSIONE ---

            # Escludi domini di servizio, a meno che non sia specificato di mantenerli
            if email_domain in service_domains:
                if not keep_service_emails: # Usa il parametro passato
                    logger.debug(f"Filtering out service domain email: {email}")
                    removed_count += 1
                    continue

            # Escludi local part che sembrano UUID o lunghe stringhe esadecimali
            if uuid_pattern.match(local_part) or long_hex_pattern.match(local_part):
                 logger.debug(f"Filtering out email with pattern-like local part: {email}")
                 removed_count += 1
                 continue

            # Aggiungi altre regole di esclusione se necessario (es. local part molto corte e generiche)
            # if len(local_part) < 3 and local_part in {'a', 'test', 'user'}:
            #    logger.debug(f"Filtering out short/generic local part email: {email}")
            #    removed_count += 1
            #    continue


            # --- Regole di INCLUSIONE ---
            # Se l'email non è stata esclusa, valutiamo se includerla

            # Includi email che appartengono al dominio target o sottodomini comuni di mail
            # Confronta anche con il dominio senza www
            if email_domain == normalized_domain or \
               email_domain == normalized_mail_domain or \
               email_domain == normalized_domain_no_www:
                logger.debug(f"Including email matching target domain: {email}")
                filtered_emails.add(email)
                continue

            # Includi email la cui local part contiene termini significativi
            if any(term in local_part for term in meaningful_terms):
                logger.debug(f"Including email with meaningful term in local part: {email}")
                filtered_emails.add(email)
                continue

            # Se l'email non è stata esclusa e non rientra nelle regole di inclusione esplicita,
            # per default NON la aggiungiamo al set filtrato.
            logger.debug(f"Filtering out email that did not match inclusion criteria: {email}")
            removed_count += 1


        except Exception as e:
            # Gestisci eventuali errori durante l'elaborazione di una singola email
            logger.error(f"Error processing email {email} during filtering: {e}", exc_info=True)
            removed_count += 1
            continue # Salta questa email

    logger.info(f"Email filtering completed. Original: {original_count}, Removed: {removed_count}, Filtered: {len(filtered_emails)}")

    return filtered_emails

# Chiamato da OSINTExtractor per estrarre numeri di telefono
def extract_phone_numbers(text: str) -> set[str]:
    '''
    Estrae potenziali numeri di telefono da una stringa di testo.
    Args:
        text: La stringa di testo da cui estrarre i numeri
    Returns:
        set[str]: Set di numeri di telefono formattati
    '''
    logger.debug("Starting phone number extraction using phonenumbers.")
    found_phones = set()

    try:
        matcher = phonenumbers.PhoneNumberMatcher(text, None)

        for match in matcher:
            try:
                phone_number = match.number

                if phonenumbers.is_possible_number(phone_number):
                    if phone_number.country_code and phone_number.national_number:
                        try:
                            # Prova prima formato E164
                            formatted = phonenumbers.format_number(
                                phone_number, 
                                phonenumbers.PhoneNumberFormat.E164
                            )
                        except phonenumbers.NumberParseException:
                            # Fallback su formato internazionale
                            formatted = phonenumbers.format_number(
                                phone_number,
                                phonenumbers.PhoneNumberFormat.INTERNATIONAL
                            )

                        found_phones.add(formatted)
                        logger.debug(
                            f"Phone extracted: {formatted} "
                            f"(Valid: {phonenumbers.is_valid_number(phone_number)})"
                        )
                    else:
                        # Gestione numeri senza prefisso internazionale
                        cleaned_str = ''.join(filter(str.isdigit, str(match.raw_string)))
                        if len(cleaned_str) >= 7:
                            found_phones.add(cleaned_str)
                            logger.debug(
                                f"Added phone without country code: {cleaned_str}"
                            )
                else:
                    logger.debug(f"Invalid phone match: {match.raw_string}")

            except Exception as e:
                logger.warning(f"Error processing phone match: {e}")
                continue

    except Exception as e:
        logger.error(f"Phone extraction failed: {e}")
        return set()

    logger.debug(f"Phone extraction completed. Found: {len(found_phones)}")
    return found_phones

def filter_phone_numbers(phone_numbers: set) -> set:
    '''
    Funzione: _filter_phone_numbers
    Applica un filtro aggiuntivo ai numeri di telefono per rimuovere falsi positivi basati su pattern specifici o formati non validi.
    Parametri formali:
        set phone_numbers -> Un set contenente i numeri di telefono da filtrare
    Valore di ritorno:
        set -> Un set contenente i numeri di telefono filtrati
    '''
    filtered_phones = set()

    date_patterns = [
        r'^20\d{6}$',
        r'^\d{8}$',
        r'^\d{6}$',
        r'^20\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$',
        r'^(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])20\d{2}$',
        r'^(19|20)\d{2}\d{4}$'
    ]

    ''' 
    Pattern regex per identificare date in formato:
    - ^20\d{6}$: Anno 20xx seguito da 6 cif
    - ^\d{8}$: 8 cifre consecutive (potrebbe essere una data)
    - ^\d{6}$: 6 cifre consecutive (potrebbe essere una data)
    - ^20\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])$:
        - Anno 20xx seguito da mese (01-12) e giorno (01-31)
    - ^(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])20\d{2}$:
        - Mese (01-12) e giorno (01-31) seguito da anno 20xx
    - ^(19|20)\d{2}\d{4}$:
        - Anno 19xx o 20xx seguito da 4 cifre (potrebbe essere un numero di telefono o un codice)
    Questi pattern sono progettati per catturare date in vari formati comuni, ma potrebbero includere falsi positivi.
    '''
    ip_pattern = r'^\d{1,3}(\.\d{1,3}){3}$'

    '''
    Pattern regex per identificare indirizzi IP:
    - ^\d{1,3}(\.\d{1,3}){3}$:
        - Inizia con 1-3 cifre, seguite da un punto e altre 1-3 cifre, ripetuto 3 volte
        - Cattura indirizzi IP in formato IPv4, ma potrebbe includere falsi positivi
    '''
    sequential_pattern = r'^(?:0(?=1)|1(?=2)|2(?=3)|3(?=4)|4(?=5)|5(?=6)|6(?=7)|7(?=8)|8(?=9)){5,}\d$'
    
    '''
    Pattern regex per identificare sequenze numeriche:
    - ^(?:0(?=1)|1(?=2)|2(?=3)|3(?=4)|4(?=5)|5(?=6)|6(?=7)|7(?=8)|8(?=9)){5,}\d$:
        - Cattura sequenze numeriche in cui ogni cifra è seguita dalla successiva
        - Ad esempio, "0123456789" o "1234567890"
        - Il pattern è progettto per identificare sequenze numeriche lunghe, ma potrebbe includere falsi positivi
    '''

    for phone in phone_numbers:
        # Gestione del doppio + all'inizio
        if phone.startswith('++'):
            cleaned = '+' + ''.join(filter(str.isdigit, phone[2:]))
        elif phone.startswith('+'):
            cleaned = '+' + ''.join(filter(str.isdigit, phone[1:]))
        else:
            cleaned = ''.join(filter(str.isdigit, phone))

        should_exclude = False
        for pattern in date_patterns:
            if re.match(pattern, cleaned):
                should_exclude = True
                break

        if should_exclude:
            continue

        if re.match(ip_pattern, phone):
            continue

        if re.match(sequential_pattern, cleaned):
            continue

        if len(cleaned) == 10 and cleaned.startswith(('1', '2')):
            try:
                timestamp = int(cleaned)
                if 1000000000 <= timestamp <= 9999999999:
                    continue
            except ValueError:
                pass

        digits = cleaned.replace('+', '')
        if 8 <= len(digits) <= 15:
            filtered_phones.add(cleaned)  

    return filtered_phones

