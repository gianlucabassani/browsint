"""
Utility functions for the Browsint CLI application.
"""
import os
from datetime import datetime
import json
import asyncio
from colorama import Fore, Style

def json_serial(obj):
    '''
    Serializza oggetti non serializzabili di default in JSON.
    Parametri formali:
        object obj -> Oggetto da serializzare
    Valore di ritorno:
        any -> Rappresentazione serializzabile dell'oggetto o eccezione TypeError
    '''
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, set):
        return list(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

def clear_screen():
    '''Cancella la console per una migliore visualizzazione.'''
    # for windows
    if os.name == 'nt':
        _ = os.system('cls')
    # for mac and linux(here, os.name is 'posix')
    else:
        _ = os.system('clear')

async def prompt_for_input(prompt: str) -> str:
    '''Chiede un input all'utente con un prompt formattato in modo asincrono.'''
    # Use to_thread to avoid blocking the asyncio event loop while waiting for user input
    result = await asyncio.to_thread(input, f"\n{Fore.CYAN}{prompt}{Style.RESET_ALL}")
    return result.strip()

async def confirm_action(message: str, default_yes: bool = True) -> bool:
    '''Chiede conferma all'utente per un'azione in modo asincrono.'''
    options = "(S/n)" if default_yes else "(s/N)"
    choice = await prompt_for_input(f"{Fore.YELLOW}{message} {options}: {Style.RESET_ALL}")

    if default_yes:
        return choice.lower() in ('s', '')
    else:
        return choice.lower() == 's' 


async def export_menu() -> str:
    print(f"{Fore.BLUE}\nScegli il formato di esportazione:{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}1.{Style.RESET_ALL} JSON")
    print(f"{Fore.YELLOW}2.{Style.RESET_ALL} HTML")
    print(f"{Fore.YELLOW}3.{Style.RESET_ALL} PDF")
    print(f"{Fore.YELLOW}4.{Style.RESET_ALL} Tutti")
    print(f"{Fore.YELLOW}0.{Style.RESET_ALL} Annulla")
    return (await prompt_for_input("Scelta: ")).strip()
