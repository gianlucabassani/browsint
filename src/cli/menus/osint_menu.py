"""
OSINT menu module for the Browsint CLI application.
"""
from colorama import Fore, Style
from typing import TYPE_CHECKING
from ..utils import clear_screen, prompt_for_input, export_menu, json_serial
import json
import validators
from datetime import datetime
from tabulate import tabulate
import logging
from scraper.utils.formatters import (
    generate_html_report, format_domain_osint_report, create_pdf_domain_report, text_report_to_html, formal_html_report_domain
)

if TYPE_CHECKING:
    from ..scraper_cli import ScraperCLI

logger = logging.getLogger("browsint.cli")

async def display_osint_menu() -> str:
    '''Visualizza il menu OSINT e restituisce la scelta dell'utente.'''
    #clear_screen()
    print(f"\n{Fore.BLUE}{'═' * 40}")
    print(f"█ {Fore.WHITE}{'INVESTIGAZIONE OSINT':^36}{Fore.BLUE} █")
    print(f"{'═' * 40}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}1.{Style.RESET_ALL} Analisi OSINT Dominio/IP (whois, dns, shodan,...)")
    print(f"{Fore.YELLOW}2.{Style.RESET_ALL} Profila indirizzo email (Breaches, Verifiche, ecc.)")
    print(f"{Fore.YELLOW}3.{Style.RESET_ALL} Ricerca username sui social media")
    print(f"{Fore.YELLOW}4.{Style.RESET_ALL} Mostra profili OSINT salvati")
    print(f"{Fore.YELLOW}5.{Style.RESET_ALL} Analizza un profilo esistente")
    print(f"{Fore.YELLOW}6.{Style.RESET_ALL} Esporta profilo\n")
    print(f"{Fore.YELLOW}0.{Style.RESET_ALL} Torna al menu principale")

    return await prompt_for_input("Scelta: ")

async def handle_osint_choice(cli_instance: 'ScraperCLI', choice: str) -> None:
    '''
    Gestisce la scelta dell'utente nel menu OSINT.
    
    Args:
        cli_instance: L'istanza di ScraperCLI per accedere ai metodi
        choice: La scelta dell'utente
    '''
    match choice:
        case "1": await profile_domain_cli(cli_instance)
        case "2": await profile_email_cli(cli_instance)
        case "3": await profile_username_cli(cli_instance)
        case "4": await show_osint_profiles_cli(cli_instance)
        case "5": await anlyze_existing_profile_cli(cli_instance)
        case "6": await export_osint_profile_cli(cli_instance)
        case "0": return
        case _:
            print(f"{Fore.RED}✗ Scelta non valida")
            await prompt_for_input("Premi INVIO per continuare...") 

async def show_osint_tables(cli_instance: 'ScraperCLI', profile_data: dict):
    print(f"{Fore.CYAN}Recupero sommario profili OSINT salvati...{Style.RESET_ALL}")
    profiles_summary = cli_instance.osint_extractor.get_all_osint_profiles_summary()

    if not profiles_summary:
        print(f"{Fore.YELLOW}⚠ Nessun profilo OSINT trovato nel database.{Style.RESET_ALL}")
        return

    print(f"\n{Fore.BLUE}{'═' * 70}")
    print(f"█ {Fore.WHITE}{'SOMMARIO PROFILI OSINT SALVATI':^66}{Fore.BLUE} █")
    print(f"{'═' * 70}{Style.RESET_ALL}")

    headers = ["ID", "Nome/Identificativo", "Tipo", "Dominio Assoc.", "Fonti Profilo", "Data Creazione DB"]
    table_data = []
    for summary in profiles_summary:
        sources_str = ", ".join(summary.get("profile_sources", [])) or "Nessuna"
        created_at_display = summary.get("created_at", "N/A")
        if isinstance(created_at_display, datetime):
            created_at_display = created_at_display.strftime("%Y-%m-%d %H:%M:%S")

        table_data.append([
            summary.get("id"),
            summary.get("name"),
            summary.get("type", "N/D").capitalize(),
            summary.get("domain", "N/A"),
            sources_str,
            created_at_display
        ])

    if table_data:
        print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))
    else:
        print(f"{Fore.YELLOW}Nessun dato da visualizzare.{Style.RESET_ALL}")
        return

async def profile_domain_cli(cli_instance: 'ScraperCLI'):
    import asyncio
    '''Gestisce l'interazione CLI per profilare un dominio web utilizzando strumenti OSINT.'''
    if not cli_instance.osint_extractor:
        print(f"{Fore.RED}✗ OSINT functionality not available. Check configuration and API keys.{Style.RESET_ALL}")
        return

    domain = (await prompt_for_input("Inserisci il dominio da profilare (es. example.com): ")).strip()
    if not domain:
        print(f"{Fore.RED}✗ Il dominio / url non può essere vuoto{Style.RESET_ALL}")
        return

    print(f"{Fore.YELLOW}⏳ Raccolta dati OSINT per {domain}...{Style.RESET_ALL}")

    try:
        try:
            profile = await asyncio.to_thread(cli_instance.osint_extractor.profile_domain, domain)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operazione annullata dall'utente.{Style.RESET_ALL}")
            return

        if profile and not profile.get("error"):
            cli_instance.osint_extractor._display_osint_profile(profile, domain)

            print(f"\n{Fore.CYAN}Azioni disponibili per '{domain}':{Style.RESET_ALL}")
            print("1. Esporta scansione")
            print("2. Torna al menu OSINT")

            choice = (await prompt_for_input("Scelta: ")).strip()
            if choice == "1":
                await export_osint_profile_cli(cli_instance, profile_data=profile)
        else:
            error_msg = profile.get("error", "Unknown error")
            print(f"{Fore.RED}✗ Errore nella creazione del profilo OSINT: {error_msg}{Style.RESET_ALL}")

    except Exception as e:
        logger.error(f"Error during domain profiling: {e}", exc_info=True)
        print(f"{Fore.RED}✗ Errore durante la profilazione: {e}{Style.RESET_ALL}")
    finally:
        await prompt_for_input("Premi INVIO per continuare...")

async def profile_email_cli(cli_instance: 'ScraperCLI'):
    import asyncio
    '''Gestisce l'interazione CLI per profilare un indirizzo email utilizzando strumenti OSINT.'''
    email_input = (await prompt_for_input("Inserisci l'indirizzo email da analizzare: ")).strip()
    if not validators.email(email_input):
        print(f"{Fore.RED}✗ Email non valida")
        return

    print(f"{Fore.YELLOW}⏳ Profilazione email: {email_input}...{Style.RESET_ALL}")

    try:
        try:
            profile_result = await asyncio.to_thread(cli_instance.osint_extractor.profile_email, email_input)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operazione annullata dall'utente.{Style.RESET_ALL}")
            return

        if profile_result and not profile_result.get("error"):
            cli_instance.osint_extractor._display_osint_profile(profile_result, email_input)
            cli_instance.osint_extractor._offer_additional_actions(profile_result, email_input)

            action_choice = (await prompt_for_input("Seleziona un'opzione (1-2): ")).strip()
            if action_choice == '1':
                await export_osint_profile_cli(cli_instance, profile_data=profile_result)
            elif action_choice == '2':
                pass
            else:
                print(f"{Fore.RED}✗ Scelta azione non valida.{Style.RESET_ALL}")

        elif profile_result and profile_result.get("error"):
                print(f"{Fore.RED}✗ Errore Profilazione Email: {profile_result.get('error')}")
        else:
                print(f"{Fore.YELLOW}⚠ Nessun risultato significativo per '{email_input}'. Controlla l'input o le API keys.{Style.RESET_ALL}")
    except Exception as e:
        logger.error(f"Error during email profiling: {e}", exc_info=True)
        print(f"{Fore.RED}✗ Errore durante la profilazione: {e}{Style.RESET_ALL}")

async def profile_username_cli(cli_instance: 'ScraperCLI'):
    '''
    Funzione: profile_username_cli
    Gestisce l'interazione CLI per ricercare username sui social media utilizzando Sherlock.
    '''
    target_input = prompt_for_input("Inserisci l'username da ricercare: ").strip()
    
    if not target_input:
        print(f"{Fore.RED}✗ L'input non può essere vuoto")
        return

    print(f"{Fore.YELLOW}⏳ Ricerca profili social per: {target_input}...{Style.RESET_ALL}")

    try:
        try:
            profile_result = cli_instance.osint_extractor.profile_username(target_input)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operazione annullata dall'utente.{Style.RESET_ALL}")
            return
        
        if profile_result and not profile_result.get("error"):
            # Mostra i profili trovati man mano che vengono scoperti
            if "profiles" in profile_result:
                profiles_data = profile_result["profiles"]
                
                if isinstance(profiles_data, dict):
                    print(f"\n{Fore.BLUE}=== Profili Trovati ==={Style.RESET_ALL}")
                    
                    for platform, data in profiles_data.items():
                        if isinstance(data, dict) and data.get("exists", False): 
                            print(f"\n{Fore.CYAN}{platform}:{Style.RESET_ALL}")
                            print(f"  • URL: {data.get('url', 'N/A')}")
                            if "confidence" in data:
                                confidence = data["confidence"] * 100
                                print(f"  • Confidenza: {confidence:.1f}%")

            # Mostra il riepilogo finale
            if "summary" in profile_result:
                print(f"\n{Fore.BLUE}=== Riepilogo Finale ==={Style.RESET_ALL}")
                summary = profile_result["summary"]
                if "profiles_found" in summary:
                    print(f"Profili trovati: {summary['profiles_found']}")
                if "report_file" in summary:
                    print(f"Report completo salvato in: {summary['report_file']}")

            # Offri opzioni aggiuntive
            print(f"\n{Fore.CYAN}Azioni disponibili:{Style.RESET_ALL}")
            print("1. Esporta risultati")
            print("2. Torna al menu OSINT")

            choice = prompt_for_input("Scelta: ").strip()
            if choice == "1":
                export_osint_profile_cli(cli_instance, profile_data=profile_result)
        else:
            error_msg = profile_result.get("error", "Unknown error")
            print(f"{Fore.RED}✗ Errore nella ricerca: {error_msg}{Style.RESET_ALL}")

    except Exception as e:
        logger.error(f"Error during username search: {e}", exc_info=True)
        print(f"{Fore.RED}✗ Errore durante la ricerca: {e}{Style.RESET_ALL}")
    finally:
        input(f"\n{Fore.CYAN}Premi INVIO per continuare...{Style.RESET_ALL}")

async def show_osint_profiles_cli(cli_instance: 'ScraperCLI'):
    '''Mostra un sommario dei profili OSINT salvati nel database tramite CLI. Permette anche di visualizzare l'analisi di un profilo selezionato.'''
    await show_osint_tables(cli_instance, profile_data=None)  # Mostra i profili OSINT salvati


    # Prompt to view a profile's analysis
    id_input = (await prompt_for_input("\nInserisci l'ID del profilo da visualizzare (INVIO per tornare): ")).strip()
    if not id_input or id_input == '0':
        return
    try:
        profile_id = int(id_input)
    except ValueError:
        print(f"{Fore.RED}✗ Valore errato, inserire un numero intero.{Style.RESET_ALL}")
        return
    profile = cli_instance.osint_extractor.get_osint_profile_by_id(profile_id)
    if not profile:
        print(f"{Fore.YELLOW}⚠ Profilo con ID {profile_id} non trovato.{Style.RESET_ALL}")
        return
    print(f"\n{Fore.CYAN}--- ANALISI PROFILO OSINT ID {profile_id} ---{Style.RESET_ALL}")
    cli_instance.osint_extractor._display_osint_profile(profile, profile.get('entity', {}).get('name', str(profile_id)))
    await prompt_for_input("Premi INVIO per continuare...")


    
async def anlyze_existing_profile_cli(cli_instance: 'ScraperCLI'):
    import asyncio
    '''Gestisce l'interazione CLI per rieseguire analisi su un profilo OSINT esistente.'''
    
    await show_osint_tables(cli_instance, profile_data=None)  # Mostra i profili OSINT salvati
    try:
        id_input = await prompt_for_input("Inserisci l'ID del target da analizzare: ")
        profile_id = int(id_input)
    except ValueError:
        print(f"{Fore.RED}✗ Valore errato, inserire un numero intero.{Style.RESET_ALL}")
        return

    profile = cli_instance.osint_extractor.get_osint_profile_by_id(profile_id)
    if not profile:
        print(f"{Fore.YELLOW}⚠ Profilo con ID {profile_id} non trovato.{Style.RESET_ALL}")
        return

    entity = profile.get('entity', {})
    contacts = profile.get('contacts', [])
    entity_type = entity.get('type')
    # Email: presente se almeno un contatto di tipo email
    has_email = any(c.get('contact_type') == 'email' for c in contacts)
    # Username: solo per person, è il name
    has_username = entity_type == 'person' and entity.get('name')
    # Dominio: solo per company, è il domain
    has_domain = entity_type == 'company' and entity.get('domain')

    print(f"\n{Fore.CYAN}Vuoi rieseguire un check tra:{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}1.{Style.RESET_ALL} Email (solo se il profilo ha un'email associata)")
    print(f"{Fore.YELLOW}2.{Style.RESET_ALL} Social-scan (solo se il profilo ha un username o nome associato)")
    print(f"{Fore.YELLOW}3.{Style.RESET_ALL} Sottodomini (solo se il profilo ha un dominio associato)")
    print(f"{Fore.YELLOW}0.{Style.RESET_ALL} Annulla")
    choice_input = (await prompt_for_input("Scelta: ")).strip()

    if choice_input == '1':
        if has_email:
            # Prendo il primo contatto di tipo email
            email = next(c['value'] for c in contacts if c.get('contact_type') == 'email')
            print(f"{Fore.YELLOW}Rieseguendo scansione email per {email}...{Style.RESET_ALL}")
            # Effettuo di nuovo il check email
            await asyncio.to_thread(cli_instance.osint_extractor.profile_email, email, force_recheck=True)
            print(f"{Fore.YELLOW}Check email completato. Visualizza il profilo aggiornato per vedere i cambiamenti.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠ Il profilo non ha un'email associata per rieseguire il check.{Style.RESET_ALL}")
    elif choice_input == '2':
        if has_username:
            # Prendo il nome associato al profilo
            username = entity.get('name')
            print(f"{Fore.YELLOW}Rieseguendo scansione social per {username}...{Style.RESET_ALL}")
            await asyncio.to_thread(cli_instance.osint_extractor.profile_username, username, force_recheck=True)
            print(f"{Fore.YELLOW}Check social completato. Visualizza il profilo aggiornato per vedere i cambiamenti.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠ Il profilo non ha un nome/username associato per rieseguire il check social.{Style.RESET_ALL}")
    elif choice_input == '3':
        if has_domain:
            # Prendo il dominio associato al profilo
            domain = entity.get('domain')
            print(f"{Fore.YELLOW}Rieseguendo scansione sottodomini per {domain}...{Style.RESET_ALL}")
            await asyncio.to_thread(cli_instance.osint_extractor.profile_domain, domain, force_recheck=True)
            print(f"{Fore.YELLOW}Check sottodomini completato. Visualizza il profilo aggiornato per vedere i cambiamenti.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠ Il profilo non ha un dominio associato per rieseguire il check sottodomini.{Style.RESET_ALL}")
    elif choice_input == '0':
        print(f"{Fore.BLUE}Operazione annullata.{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}✗ Scelta non valida.{Style.RESET_ALL}")

async def export_osint_profile_cli(cli_instance: 'ScraperCLI', profile_data: dict = None) -> None:
    '''Esporta i dati di un profilo OSINT in formato scelto (JSON, HTML, PDF, Tutti).'''
    try:
        if profile_data is None:
            # Se non viene fornito un profilo, chiedi l'ID
            id_input = await prompt_for_input("Inserisci l'ID del profilo da esportare: ")
            try:
                profile_id = int(id_input)
                profile_data = cli_instance.osint_extractor.get_osint_profile_by_id(profile_id)
                if not profile_data:
                    print(f"{Fore.RED}✗ Profilo non trovato.{Style.RESET_ALL}")
                    return
            except ValueError:
                print(f"{Fore.RED}✗ ID non valido.{Style.RESET_ALL}")
                return

        target_id = profile_data.get("entity", {}).get("name", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        osint_dir = cli_instance.dirs["osint_exports"]
        pdf_dir = cli_instance.dirs["pdf_reports"]

        export_choice = await export_menu()
        if export_choice == "0":
            print("Esportazione annullata.")
            return

        exported = False # Variabile per tenere traccia di cosa è stato esportato
        if export_choice in {"1", "4"}: # Se la scelta è JSON o Tutti
            json_path = osint_dir / f"osint_profile_{target_id}_{timestamp}.json" 
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=4, ensure_ascii=False, default=json_serial) # Effettua una conversione JSON
            print(f"\n{Fore.YELLOW}✓ Profilo esportato in JSON: {json_path}{Style.RESET_ALL}")
            exported = True # Segna come esportato
        
        if export_choice in {"2", "4"}: # Se la scelta è HTML o Tutti
            html_path = osint_dir / f"osint_profile_{target_id}_{timestamp}.html"
            profiles = profile_data.get('profiles', {}) # Estraggo i profili dal profilo (entita principale)
            data = profiles.get('domain', {}).get('raw', {}) # Estraggo i dati del dominio (esempio. whois, dns, ecc..)
            domain_analyzed = profile_data.get('entity', {}).get('name', target_id) # Prendo il nome del dom analizzato
            target_input = profile_data.get('target_input', domain_analyzed) # Se non presente, uso in nome inserito in input
            shodan_skipped = 'shodan' not in data
            html_report = formal_html_report_domain(data, target_input, domain_analyzed, shodan_skipped, ) # se shodan non presente, lo gestisco
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_report) # scrivo report
            print(f"{Fore.YELLOW}✓ Profilo esportato in HTML: {html_path}{Style.RESET_ALL}")
            exported = True
        
        if export_choice in {"3", "4"}:
            pdf_path = pdf_dir / f"osint_profile_{target_id}_{timestamp}.pdf"
            profiles = profile_data.get('profiles', {})
            data = profiles.get('domain', {}).get('raw', {})
            domain_analyzed = profile_data.get('entity', {}).get('name', target_id)
            target_input = profile_data.get('target_input', domain_analyzed)
            shodan_skipped = 'shodan' not in data
            create_pdf_domain_report(data, target_input, domain_analyzed, shodan_skipped, str(pdf_path))
            print(f"{Fore.YELLOW}✓ Profilo esportato in PDF: {pdf_path}{Style.RESET_ALL}")
            exported = True
        
        if not exported:
            print(f"{Fore.YELLOW}Nessun formato selezionato per l'esportazione.{Style.RESET_ALL}")

    except Exception as e:
        logger.error(f"Error exporting profile: {e}", exc_info=True)
        print(f"{Fore.RED}✗ Errore durante l'esportazione del profilo: {e}{Style.RESET_ALL}")