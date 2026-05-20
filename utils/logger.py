import sys
from pathlib import Path
from loguru import logger as _logger

def get_log_file():
    if getattr(sys, '_MEIPASS', False):
        base_dir = Path(sys._MEIPASS).parent
    else:
        base_dir = Path(__file__).parent.parent
    log_dir = base_dir / "data"
    log_dir.mkdir(exist_ok=True)
    return log_dir / "app.log"

LOG_FILE = get_log_file()

_initialized = False

def init_logging():
    global _initialized
    if _initialized:
        return _logger

    _initialized = True
    _logger.remove()

    try:
        _logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO"
        )
    except Exception:
        pass

    try:
        _logger.add(
            str(LOG_FILE),
            rotation="10 MB",
            retention="7 days",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            encoding="utf-8"
        )
    except Exception:
        pass

    return _logger

logger = init_logging()