"""Load developer configuration without third-party dependencies."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_environment(env_path=None):
    """Read an optional local .env; never override already-exported variables."""
    path = Path(env_path) if env_path else ROOT / '.env'
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key, value = key.strip(), value.strip().strip('"\'')
        if key:
            os.environ.setdefault(key, value)


load_environment()
PORT = int(os.environ.get('PORT', '8000'))
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')
DEMO_MODE = os.environ.get('REVIEWLENS_DEMO_MODE', '0') == '1'
DB_PATH = Path(os.environ.get('REVIEWLENS_DB_PATH', str(ROOT / '.data' / 'reviewlens.db')))


def api_key():
    return os.environ.get('GEMINI_API_KEY', '').strip()


def is_configured():
    return bool(api_key() and api_key() != 'replace_with_your_key')
