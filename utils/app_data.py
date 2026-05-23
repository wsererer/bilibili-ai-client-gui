import sys
from pathlib import Path

def get_app_data_dir():
    """Get the user-writable data directory for the app."""
    if getattr(sys, 'frozen', False):
        base_dir = Path(sys.executable).parent
    else:
        base_dir = Path(__file__).parent.parent
    return base_dir / "data"

APP_DATA_DIR = get_app_data_dir()
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)