from pathlib import Path
import os
from typing import Dict, Optional
from dotenv import load_dotenv, set_key, unset_key


def load_env(env_file: Optional[Path | str] = None) -> None:
    """Load environment variables from a .env file if provided.

    This wraps python-dotenv's load_dotenv so callers don't import dotenv directly.
    """
    if env_file:
        try:
            load_dotenv(Path(env_file))
        except Exception:
            # Best-effort: ignore errors, rely on existing env
            return
    else:
        load_dotenv()


def get_api_keys(env_file: Optional[Path | str] = None) -> Dict[str, str]:
    """Return a dict with known API keys read from environment or .env file.

    Keys returned follow the project's convention used in the codebase.
    """
    load_env(env_file)

    api_keys = {
        "hunterio": os.getenv("HUNTER_IO_API_KEY"),
        "hibp": os.getenv("HIBP_API_KEY"),
        "shodan": os.getenv("SHODAN_API_KEY"),
        "whoisxml": os.getenv("WHOISXML_API_KEY"),
        "virustotal": os.getenv("VIRUSTOTAL_API_KEY"),
        "securitytrails": os.getenv("SECURITYTRAILS_API_KEY"),
    }

    return {k: v for k, v in api_keys.items() if v}


def set_env_key(env_file: Path | str, key: str, value: str) -> bool:
    """Set a key in the .env file (wraps dotenv.set_key)."""
    try:
        set_key(env_file, key, value)
        return True
    except Exception:
        return False


def unset_env_key(env_file: Path | str, key: str) -> bool:
    """Unset a key in the .env file (wraps dotenv.unset_key)."""
    try:
        unset_key(env_file, key)
        return True
    except Exception:
        return False
