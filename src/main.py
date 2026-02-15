"""
Main entry point for the Browsint application.
"""
import sys
from pathlib import Path
import argparse
import logging
import asyncio
import colorama

# Add src directory to Python path
src_path = str(Path(__file__).parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import the main CLI class
from cli.scraper_cli import ScraperCLI
from cli.utils import clear_screen

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("browsint.main")

def main():
    '''
    Funzione: main
    Punto di ingresso principale dell'applicazione CLI.
    Parametri formali:
        Nessuno
    Valore di ritorno:
        None -> La funzione esegue il punto di ingresso principale dell'applicazione
    '''
    clear_screen()
    colorama.init(autoreset=True)

    parser = argparse.ArgumentParser(description="Strumento OSINT CLI.")
    args = parser.parse_args()

    cli = ScraperCLI()
    try:
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        print("\n[!] Interruzione da tastiera ricevuta. Uscita in corso...")

if __name__ == "__main__":
    main() 