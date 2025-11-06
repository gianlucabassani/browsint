"""
Database menu module for the Browsint CLI application.
"""
from colorama import Fore, Style
from typing import TYPE_CHECKING
from ..utils import clear_screen, prompt_for_input
import logging
from pathlib import Path
from datetime import datetime
import shutil

if TYPE_CHECKING:
    from ..scraper_cli import ScraperCLI

logger = logging.getLogger("browsint.cli")

def display_db_menu() -> str:
    '''Visualizza il menu del database e restituisce la scelta dell'utente.'''
    #clear_screen()
    print(f"\n{Fore.BLUE}{'═' * 40}")
    print(f"█ {Fore.WHITE}{'GESTIONE DATABASE E API':^36}{Fore.BLUE} █")
    print(f"{'═' * 40}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}=== Database ==={Style.RESET_ALL}")
    print(f"{Fore.YELLOW}1.{Style.RESET_ALL} Informazioni Generali Database")
    print(f"{Fore.YELLOW}2.{Style.RESET_ALL} Gestione Backup Database")
    print(f"{Fore.YELLOW}3.{Style.RESET_ALL} Svuota Cache delle Query")
    print(f"{Fore.YELLOW}4.{Style.RESET_ALL} Gestione Tabelle Database")
    print(f"\n{Fore.CYAN}=== API Keys ==={Style.RESET_ALL}")
    print(f"{Fore.YELLOW}5.{Style.RESET_ALL} Visualizza API Keys configurate")
    print(f"{Fore.YELLOW}6.{Style.RESET_ALL} Aggiungi/Aggiorna API Key")
    print(f"{Fore.YELLOW}7.{Style.RESET_ALL} Rimuovi API Key")
    print(f"\n{Fore.YELLOW}0.{Style.RESET_ALL} Torna al menu Opzioni Generali")

    return prompt_for_input("Scelta: ")

def handle_db_choice(cli_instance: 'ScraperCLI', choice: str) -> None:
    '''
    Gestisce la scelta dell'utente nel menu del database.
    
    Args:
        cli_instance: L'istanza di ScraperCLI per accedere ai metodi
        choice: La scelta dell'utente
    '''
    match choice:
        case "1": _display_db_info(cli_instance)
        case "2": display_backup_menu(cli_instance)
        case "3": _clear_query_cache(cli_instance)
        case "4": _clear_specific_table(cli_instance)
        case "5": show_api_keys(cli_instance)
        case "6": add_api_key(cli_instance)
        case "7": remove_api_key(cli_instance)
        case "0": return
        case _:
            print(f"{Fore.RED}✗ Scelta non valida")
            input(f"{Fore.CYAN}\nPremi INVIO per continuare...{Style.RESET_ALL}")

def _display_db_info(cli_instance: 'ScraperCLI') -> None:
    """Mostra informazioni sui database."""
    while True:
        print(f"\n{Fore.BLUE}{'═' * 40}")
        print(f"█ {Fore.WHITE}{'INFORMAZIONI DATABASE':^36}{Fore.BLUE} █")
        print(f"{'═' * 40}{Style.RESET_ALL}")
        
        # Mostra le opzioni disponibili
        print(f"{Fore.YELLOW}1.{Style.RESET_ALL} Mostra info di tutti i database")
        print(f"{Fore.YELLOW}2.{Style.RESET_ALL} Seleziona database specifico\n")
        print(f"\n{Fore.YELLOW}0.{Style.RESET_ALL} Torna al menu precedente")
        
        choice = prompt_for_input("Scelta: ").strip()
        
        if choice == "1":
            for db_name in ["websites", "osint"]:
                try:
                    size = cli_instance.db_manager.get_database_size(db_name) 
                    tables = cli_instance.db_manager.get_all_table_names(db_name)
                    
                    print(f"\n{Fore.CYAN}Database {db_name.upper()}:{Style.RESET_ALL}")
                    print(f"  Dimensione: {size:.2f} MB")
                    print(f"  Tabelle ({len(tables)}):")
                    for table in tables:
                        row_count = cli_instance.db_manager.fetch_one(f"SELECT COUNT(*) as count FROM {table}", db_name=db_name)
                        count = row_count['count'] if row_count else 0
                        print(f"    - {table} ({count} righe)")
                except Exception as e:
                    print(f"{Fore.RED}Errore lettura info {db_name}: {e}{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
            
        elif choice == "2":
            print(f"\n{Fore.CYAN}Database disponibili:{Style.RESET_ALL}")
            print("1. websites")
            print("2. osint")
            db_choice = prompt_for_input("\nSeleziona database (0 per annullare): ").strip()
            
            if db_choice == "1":
                db_name = "websites"
            elif db_choice == "2":
                db_name = "osint"
            else:
                continue
                
            try:
                size = cli_instance.db_manager.get_database_size(db_name)
                tables = cli_instance.db_manager.get_all_table_names(db_name)
                
                print(f"\n{Fore.CYAN}Database {db_name.upper()}:{Style.RESET_ALL}")
                print(f"  Dimensione: {size:.2f} MB")
                print(f"  Tabelle ({len(tables)}):")
                for table in tables:
                    row_count = cli_instance.db_manager.fetch_one(f"SELECT COUNT(*) as count FROM {table}", db_name=db_name)
                    count = row_count['count'] if row_count else 0
                    print(f"    - {table} ({count} righe)")
            except Exception as e:
                print(f"{Fore.RED}Errore lettura info {db_name}: {e}{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
            
        elif choice == "0":
            break

def _clear_query_cache(cli_instance: 'ScraperCLI') -> None:
    """Svuota la cache delle query."""
    while True:
        print(f"\n{Fore.BLUE}{'═' * 40}")
        print(f"█ {Fore.WHITE}{'GESTIONE CACHE':^36}{Fore.BLUE} █")
        print(f"{'═' * 40}{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}1.{Style.RESET_ALL} Svuota tutta la cache")
        print(f"{Fore.YELLOW}2.{Style.RESET_ALL} Svuota cache per database specifico")
        print(f"\n{Fore.YELLOW}0.{Style.RESET_ALL} Torna al menu precedente")
        
        choice = prompt_for_input("Scelta: ").strip()
        
        if choice == "1":
            try:
                cli_instance.db_manager.clear_cache()
                print(f"{Fore.YELLOW}✓ Cache delle query svuotata con successo{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}✗ Errore pulizia cache: {e}{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
            
        elif choice == "2":
            print(f"\n{Fore.CYAN}Database disponibili:{Style.RESET_ALL}")
            print("1. websites")
            print("2. osint")
            db_choice = prompt_for_input("Scelta (0 per annullare): ").strip()
            
            if db_choice == "1":
                db_name = "websites"
            elif db_choice == "2":
                db_name = "osint"
            else:
                continue
                
            try:
                # Chiamiamo clear_cache senza il parametro del database
                cli_instance.db_manager.clear_cache()
                print(f"{Fore.YELLOW}✓ Cache delle query svuotata con successo{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}✗ Errore pulizia cache: {e}{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
            
        elif choice == "0":
            break

def _clear_specific_table(cli_instance: 'ScraperCLI') -> None:
    """Svuota le tabelle del database."""
    while True:
        print(f"\n{Fore.BLUE}{'═' * 40}")
        print(f"█ {Fore.WHITE}{'GESTIONE TABELLE':^36}{Fore.BLUE} █")
        print(f"{'═' * 40}{Style.RESET_ALL}")
        
        print(f"{Fore.YELLOW}1.{Style.RESET_ALL} Svuota tutte le tabelle di tutti i database")
        print(f"{Fore.YELLOW}2.{Style.RESET_ALL} Svuota tutte le tabelle di un database")
        print(f"{Fore.YELLOW}3.{Style.RESET_ALL} Svuota una tabella specifica")
        print(f"\n{Fore.YELLOW}0.{Style.RESET_ALL} Torna al menu precedente")
        
        choice = prompt_for_input("Scelta: ").strip()
        
        if choice == "1":
            print(f"{Fore.RED}⚠️ ATTENZIONE: Stai per eliminare TUTTI i dati da TUTTI i database!{Style.RESET_ALL}")
            
            # Mostra riepilogo dei dati che verranno eliminati
            for db_name in ["websites", "osint"]:
                try:
                    tables = cli_instance.db_manager.get_all_table_names(db_name)
                    if tables:
                        print(f"\n{Fore.CYAN}Database {db_name.upper()}:{Style.RESET_ALL}")
                        for table in tables:
                            row_count = cli_instance.db_manager.fetch_one(f"SELECT COUNT(*) as count FROM {table}", db_name=db_name)
                            count = row_count['count'] if row_count else 0
                            print(f"  - {table} ({count} righe)")
                except Exception as e:
                    print(f"{Fore.RED}Errore lettura tabelle {db_name}: {e}{Style.RESET_ALL}")

            confirm = prompt_for_input(f"\n{Fore.RED}⚠️ Confermi di voler eliminare TUTTI i dati? (s/N): ").strip().lower()
            
            if confirm == 's':
                double_confirm = prompt_for_input(f"{Fore.RED}⚠️ Questa azione non può essere annullata! Conferma nuovamente: (s/N) ").strip().lower()
                if double_confirm == 's':
                    for db_name in ["websites", "osint"]:
                        try:
                            success, cleared = cli_instance.db_manager.clear_all_tables(db_name)
                            if success:
                                print(f"{Fore.YELLOW}✓ Tabelle di {db_name} svuotate con successo:{Style.RESET_ALL}")
                                for table in cleared:
                                    print(f"  - {table}")
                            else:
                                print(f"{Fore.RED}✗ Errore durante lo svuotamento di {db_name}{Style.RESET_ALL}")
                        except Exception as e:
                            print(f"{Fore.RED}✗ Errore durante lo svuotamento di {db_name}: {e}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}Operazione annullata{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}Operazione annullata{Style.RESET_ALL}")
            
            input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
            
        elif choice == "2":
            print(f"\n{Fore.CYAN}Database disponibili:{Style.RESET_ALL}")
            print("1. websites")
            print("2. osint")
            db_choice = prompt_for_input("Scelta (0 per annullare): ").strip()
            
            if db_choice == "1":
                db_name = "websites"
            elif db_choice == "2":
                db_name = "osint"
            else:
                continue
            
            try:
                tables = cli_instance.db_manager.get_all_table_names(db_name)
                if not tables:
                    print(f"{Fore.YELLOW}⚠ Nessuna tabella trovata nel database {db_name}{Style.RESET_ALL}")
                    input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
                    continue
                
                print(f"\n{Fore.RED}⚠️ ATTENZIONE: Stai per eliminare tutti i dati da {db_name}!{Style.RESET_ALL}")
                print(f"\n{Fore.CYAN}Tabelle che verranno svuotate:{Style.RESET_ALL}")
                for table in tables:
                    row_count = cli_instance.db_manager.fetch_one(f"SELECT COUNT(*) as count FROM {table}", db_name=db_name)
                    count = row_count['count'] if row_count else 0
                    print(f"  - {table} ({count} righe)")
                
                confirm = prompt_for_input(f"\n{Fore.RED}⚠️ Confermi di voler eliminare TUTTI i dati da {db_name}? (s/N): ").strip().lower()
                
                if confirm == 's':
                    double_confirm = prompt_for_input(f"{Fore.RED}⚠️ Questa azione non può essere annullata! Conferma nuovamente: (s/N) ").strip().lower()
                    if double_confirm == 's':
                        success, cleared = cli_instance.db_manager.clear_all_tables(db_name)
                        if success:
                            print(f"{Fore.YELLOW}✓ Tabelle di {db_name} svuotate con successo:{Style.RESET_ALL}")
                            for table in cleared:
                                print(f"  - {table}")
                        else:
                            print(f"{Fore.RED}✗ Errore durante lo svuotamento{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}Operazione annullata{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}Operazione annullata{Style.RESET_ALL}")
                
            except Exception as e:
                print(f"{Fore.RED}✗ Errore: {e}{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
            
        elif choice == "3":
            print(f"\n{Fore.CYAN}Database disponibili:{Style.RESET_ALL}")
            print("1. websites")
            print("2. osint")
            db_choice = prompt_for_input("Scelta (0 per annullare): ").strip()
            
            if db_choice == "1":
                db_name = "websites"
            elif db_choice == "2":
                db_name = "osint"
            else:
                continue
            
            try:
                tables = cli_instance.db_manager.get_all_table_names(db_name)
                if not tables:
                    print(f"{Fore.YELLOW}⚠ Nessuna tabella trovata nel database {db_name}{Style.RESET_ALL}")
                    input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
                    continue
                    
                print(f"\n{Fore.CYAN}Tabelle disponibili in {db_name}:{Style.RESET_ALL}")
                for i, table in enumerate(tables, 1):
                    row_count = cli_instance.db_manager.fetch_one(f"SELECT COUNT(*) as count FROM {table}", db_name=db_name)
                    count = row_count['count'] if row_count else 0
                    print(f"{i}. {table} ({count} righe)")
                
                table_choice = prompt_for_input("\nSeleziona numero tabella (0 per annullare): ").strip()
                
                if table_choice.isdigit() and 0 < int(table_choice) <= len(tables):
                    table_name = tables[int(table_choice)-1]
                    confirm = prompt_for_input(f"{Fore.RED}⚠️ Confermi di voler svuotare {table_name}? (s/N): ").strip().lower()
                    
                    if confirm == 's':
                        if cli_instance.db_manager.clear_table(table_name, db_name):
                            print(f"{Fore.YELLOW}✓ Tabella {table_name} svuotata con successo{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.RED}✗ Errore durante lo svuotamento della tabella{Style.RESET_ALL}")
                
            except Exception as e:
                print(f"{Fore.RED}✗ Errore: {e}{Style.RESET_ALL}")
            input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
            
        elif choice == "0":
            break

def show_api_keys(cli_instance: 'ScraperCLI') -> None:
    '''Visualizza le API keys configurate, mascherandone parzialmente il valore per sicurezza.'''
    if not cli_instance.api_keys:
        print(f"{Fore.YELLOW}⚠ Nessuna API key configurata.")
        return
    print(f"\n{Fore.CYAN}API Keys Configurate:{Style.RESET_ALL}")
    table = []
    for service, key_value in cli_instance.api_keys.items():
        masked_key = key_value[:4] + "****" + key_value[-4:] if len(key_value) > 8 else "****"
        table.append([service, masked_key])
    if table:
        from tabulate import tabulate
        print(tabulate(table, headers=["Servizio", "API Key (Mascherata)"], tablefmt="pretty"))

        
    else:
        print(f"{Fore.YELLOW}Nessuna API key trovata.{Style.RESET_ALL}")

    input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")

def add_api_key(cli_instance: 'ScraperCLI') -> None:
    import maskpass
    '''Permette all'utente di aggiungere o modificare una API key.'''
    print(f"\n{Fore.CYAN}Aggiungi/Modifica API Key{Style.RESET_ALL}")
    supported_services = {
        "hunterio": "HUNTER_IO_API_KEY",
        "hibp": "HIBP_API_KEY",
        "shodan": "SHODAN_API_KEY",
        "whoisxml": "WHOISXML_API_KEY",
        "virustotal": "VIRUSTOTAL_API_KEY",
        "securitytrails": "SECURITYTRAILS_API_KEY"
    }
    
    print("\nServizi supportati:")
    for i, (service, env_var) in enumerate(supported_services.items(), 1):
        print(f"{i}. {service} ({env_var})")
    
    try:
        choice = int(prompt_for_input("\nSeleziona il numero del servizio (0 per annullare): "))
        if choice == 0:
            return
        if 1 <= choice <= len(supported_services):
            service_name = list(supported_services.keys())[choice - 1]
            env_var = supported_services[service_name]
            print(f"{Fore.CYAN}Inserisci la API key per {service_name}: {Style.RESET_ALL}", end='', flush=True)
            api_key = maskpass.askpass('', mask='*').strip()
            if not api_key:
                print(f"{Fore.RED}✗ API key non può essere vuota.")
                return
            
            # Salva nel file .env (usa wrapper centralizzato)
            try:
                from ...config import set_env_key
            except Exception:
                # fallback to dotenv directly if relative import fails
                from dotenv import set_key as _dot_set_key
                _dot_set_key(cli_instance.env_file, env_var, api_key)
            else:
                set_env_key(cli_instance.env_file, env_var, api_key)
            # Aggiorna le variabili d'ambiente
            import os
            os.environ[env_var] = api_key
            # Aggiorna il dizionario delle API keys
            cli_instance.api_keys[service_name] = api_key
            # Aggiorna l'estrattore OSINT
            cli_instance.osint_extractor.api_keys = cli_instance.api_keys
            
            print(f"{Fore.YELLOW}✓ API key per '{service_name}' salvata con successo.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}✗ Scelta non valida.")
    except ValueError:
        print(f"{Fore.RED}✗ Inserire un numero valido.")

def remove_api_key(cli_instance: 'ScraperCLI') -> None:
    '''Permette all'utente di rimuovere una API key.'''
    if not cli_instance.api_keys:
        print(f"{Fore.YELLOW}⚠ Nessuna API key configurata da rimuovere.")
        return

    service_mapping = {
        "hunterio": "HUNTER_IO_API_KEY",
        "hibp": "HIBP_API_KEY",
        "shodan": "SHODAN_API_KEY",
        "whoisxml": "WHOISXML_API_KEY",
        "virustotal": "VIRUSTOTAL_API_KEY",
        "securitytrails": "SECURITYTRAILS_API_KEY"
    }

    try:
        services = list(cli_instance.api_keys.keys())
        for i, service in enumerate(services, 1):
            print(f"{i}. {service}")
        
        choice = int(prompt_for_input("\nSeleziona il numero del servizio da rimuovere (0 per annullare): "))
        if choice == 0:
            return
        if 1 <= choice <= len(services):
            service_name = services[choice - 1]
            env_var = service_mapping[service_name]
            
            confirm = prompt_for_input(f"{Fore.YELLOW}Confermi la rimozione della API key per {service_name}? (s/N): {Style.RESET_ALL}").lower()
            if confirm == 's':
                # Rimuovi dal file .env (usa wrapper centralizzato)
                try:
                    from ...config import unset_env_key
                except Exception:
                    from dotenv import unset_key as _dot_unset_key
                    _dot_unset_key(cli_instance.env_file, env_var)
                else:
                    unset_env_key(cli_instance.env_file, env_var)
                # Rimuovi dalla variabile d'ambiente
                import os
                os.environ.pop(env_var, None) 
                # Rimuovi dal dizionario delle API keys
                cli_instance.api_keys.pop(service_name, None)
                # Aggiorna l'estrattore OSINT
                cli_instance.osint_extractor.api_keys = cli_instance.api_keys
                
                print(f"{Fore.YELLOW}✓ API key per '{service_name}' rimossa con successo.{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}Operazione annullata.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}✗ Scelta non valida.")
    except ValueError:
        print(f"{Fore.RED}✗ Inserire un numero valido.")

def display_backup_menu(cli_instance: 'ScraperCLI'):
    while True:
        print(f"\n{Fore.BLUE}{'═' * 40}")
        print(f"█ {Fore.WHITE}{'GESTIONE BACKUP':^36}{Fore.BLUE} █")
        print(f"{'═' * 40}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}1.{Style.RESET_ALL} Elenca backup disponibili")
        print(f"{Fore.YELLOW}2.{Style.RESET_ALL} Crea nuovo backup")
        print(f"{Fore.YELLOW}3.{Style.RESET_ALL} Ripristina da backup")
        print(f"{Fore.YELLOW}4.{Style.RESET_ALL} Elimina backup")
        print(f"\n{Fore.YELLOW}0.{Style.RESET_ALL} Torna al menu precedente")
        choice = prompt_for_input("Scelta: ").strip()
        if choice == "1":
            list_available_backups()
        elif choice == "2":
            perform_db_backup(cli_instance)
        elif choice == "3":
            restore_from_backup(cli_instance)
        elif choice == "4":
            delete_backup()
        elif choice == "0":
            break

def list_available_backups() -> None:
    """Mostra i backup disponibili in modo semplice."""
    clear_screen()
    print(f"\n{Fore.CYAN}--- BACKUP DISPONIBILI ---{Style.RESET_ALL}")
    backup_dir = Path("data/databases/backups")
    if not backup_dir.exists():
        print(f"{Fore.YELLOW}Cartella backup non trovata.{Style.RESET_ALL}")
        prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
        return
    backup_files = list(backup_dir.glob("*.db"))
    if not backup_files:
        print(f"{Fore.YELLOW}Nessun backup trovato.{Style.RESET_ALL}")
        prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
        return
    backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    print(f"\n{Fore.BLUE}Backup trovati:{Style.RESET_ALL}")
    for i, backup_file in enumerate(backup_files, 1):
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        creation_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
        date_str = creation_time.strftime('%d/%m/%Y alle %H:%M')
        print(f"{i}. {backup_file.name}")
        print(f"   Dimensione: {size_mb:.1f} MB")
        print(f"   Creato: {date_str}")
        print()
    prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")

def perform_db_backup(cli_instance: 'ScraperCLI') -> None:
    """Crea un nuovo backup del database websites e osint."""
    clear_screen()
    print(f"\n{Fore.CYAN}--- CREA BACKUP ---{Style.RESET_ALL}")
    try:
        print(f"{Fore.CYAN}Creazione backup in corso...{Style.RESET_ALL}")
        for db_name in ["websites", "osint"]:
            success, backup_path = cli_instance.db_manager.backup_database(db_name)
            if success:
                print(f"{Fore.GREEN}✓ Backup {db_name} creato con successo!{Style.RESET_ALL}")
                print(f"  Percorso: {backup_path}")
                logger.info(f"Database backup created: {backup_path}")
            else:
                print(f"{Fore.RED}✗ Errore durante la creazione del backup di {db_name}.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Errore imprevisto: {e}{Style.RESET_ALL}")
        logger.error(f"Unexpected error in backup: {e}", exc_info=True)
    prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")

def restore_from_backup(cli_instance: 'ScraperCLI') -> None:
    """Ripristina il database da un backup selezionato."""
    clear_screen()
    print(f"\n{Fore.CYAN}--- RIPRISTINA DATABASE ---{Style.RESET_ALL}")
    backup_dir = Path("data/databases/backups")
    if not backup_dir.exists():
        print(f"{Fore.YELLOW}Cartella backup non trovata.{Style.RESET_ALL}")
        prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
        return
    backup_files = list(backup_dir.glob("*.db"))
    if not backup_files:
        print(f"{Fore.YELLOW}Nessun backup disponibile.{Style.RESET_ALL}")
        prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
        return
    backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    print(f"\n{Fore.BLUE}Scegli quale backup ripristinare:{Style.RESET_ALL}")
    for i, backup_file in enumerate(backup_files, 1):
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        creation_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
        date_str = creation_time.strftime('%d/%m/%Y alle %H:%M')
        print(f"{i}. {backup_file.name} ({size_mb:.1f} MB) - {date_str}")
    try:
        choice = prompt_for_input(f"\n{Fore.CYAN}Numero del backup da ripristinare (0 per annullare): {Style.RESET_ALL}")
        if choice == "0":
            print(f"{Fore.YELLOW}Operazione annullata.{Style.RESET_ALL}")
            prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
            return
        backup_number = int(choice)
        if backup_number < 1 or backup_number > len(backup_files):
            print(f"{Fore.RED}Numero non valido.{Style.RESET_ALL}")
            prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
            return
        selected_backup = backup_files[backup_number - 1]
        print(f"\n{Fore.YELLOW}ATTENZIONE:{Style.RESET_ALL}")
        print(f"Il database attuale verrà sostituito con il backup '{selected_backup.name}'")
        print(f"Tutti i dati non salvati andranno persi!")
        confirm = prompt_for_input(f"\n{Fore.CYAN}Sei sicuro di voler procedere? (s/N): {Style.RESET_ALL}")
        if confirm != 's':
            print(f"{Fore.YELLOW}Operazione annullata.{Style.RESET_ALL}")
            prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
            return
        print(f"\n{Fore.CYAN}Ripristino in corso...{Style.RESET_ALL}")
        cli_instance.db_manager.disconnect()  # Chiude tutte le connessioni
        # Determina quale database ripristinare (websites/osint) in base al nome file
        if "websites" in selected_backup.name:
            main_db_path = cli_instance.db_manager.databases['websites']
        elif "osint" in selected_backup.name:
            main_db_path = cli_instance.db_manager.databases['osint']
        else:
            print(f"{Fore.RED}Impossibile determinare il database dal nome del backup.{Style.RESET_ALL}")
            prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
            return
        shutil.copy2(selected_backup, main_db_path)
        cli_instance.db_manager.init_schema()  # Riconnette e re-inizializza
        print(f"{Fore.GREEN}✓ Database ripristinato con successo!{Style.RESET_ALL}")
        logger.info(f"Database restored from backup: {selected_backup.name}")
    except ValueError:
        print(f"{Fore.RED}Devi inserire un numero.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Errore durante il ripristino: {e}{Style.RESET_ALL}")
        logger.error(f"Error during restore: {e}", exc_info=True)
        try:
            cli_instance.db_manager.init_schema()
        except:
            pass
    prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")

def delete_backup() -> None:
    """Elimina un backup selezionato."""
    clear_screen()
    print(f"\n{Fore.CYAN}--- ELIMINA BACKUP ---{Style.RESET_ALL}")
    backup_dir = Path("data/databases/backups")
    if not backup_dir.exists():
        print(f"{Fore.YELLOW}Cartella backup non trovata.{Style.RESET_ALL}")
        prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
        return
    backup_files = list(backup_dir.glob("*.db"))
    if not backup_files:
        print(f"{Fore.YELLOW}Nessun backup da eliminare.{Style.RESET_ALL}")
        prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
        return
    backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    print(f"\n{Fore.BLUE}Scegli quale backup eliminare:{Style.RESET_ALL}")
    for i, backup_file in enumerate(backup_files, 1):
        size_mb = backup_file.stat().st_size / (1024 * 1024)
        creation_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
        date_str = creation_time.strftime('%d/%m/%Y alle %H:%M')
        print(f"{i}. {backup_file.name} ({size_mb:.1f} MB) - {date_str}")
    try:
        choice = prompt_for_input(f"\n{Fore.CYAN}Numero del backup da eliminare (0 per annullare): {Style.RESET_ALL}")
        if choice == "0":
            print(f"{Fore.YELLOW}Operazione annullata.{Style.RESET_ALL}")
            prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
            return
        backup_number = int(choice)
        if backup_number < 1 or backup_number > len(backup_files):
            print(f"{Fore.RED}Numero non valido.{Style.RESET_ALL}")
            prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
            return
        backup_to_delete = backup_files[backup_number - 1]
        print(f"\n{Fore.YELLOW}Stai per eliminare: {backup_to_delete.name}{Style.RESET_ALL}")
        confirm = prompt_for_input(f"{Fore.CYAN}Sei sicuro? (s/N): {Style.RESET_ALL}")
        if confirm != 's':
            print(f"{Fore.YELLOW}Operazione annullata.{Style.RESET_ALL}")
            prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")
            return
        backup_to_delete.unlink()
        print(f"{Fore.GREEN}✓ Backup eliminato con successo.{Style.RESET_ALL}")
        logger.info(f"Backup deleted: {backup_to_delete.name}")
    except ValueError:
        print(f"{Fore.RED}Devi inserire un numero.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Errore durante l'eliminazione: {e}{Style.RESET_ALL}")
        logger.error(f"Error deleting backup: {e}", exc_info=True)
    prompt_for_input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")