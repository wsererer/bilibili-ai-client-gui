import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from pathlib import Path


@pytest.fixture
def temp_db(tmp_path):
    import shutil
    from database import database

    db_path = Path("data/bilibili_client.db")
    backup_path = Path("data/bilibili_client.db.bak")

    if db_path.exists():
        shutil.copy(db_path, backup_path)

    yield db_path

    if backup_path.exists():
        shutil.move(backup_path, db_path)


@pytest.fixture
def valid_cookie():
    cookie_path = Path("data/login_cookie.txt")
    if cookie_path.exists():
        return cookie_path.read_text().strip()
    pytest.skip("No cookie file at data/login_cookie.txt")


@pytest.fixture
def config_backup(tmp_path, monkeypatch):
    import config as config_module
    import json

    backup = {}
    for key in ["language", "theme", "polling_interval", "auto_start", "bili_auth"]:
        backup[key] = config_module.config.get(key)

    yield config_module.config

    for key, value in backup.items():
        config_module.config.set(key, value)


@pytest.fixture
def clean_subtitles():
    import shutil
    subtitle_dir = Path("data/subtitles")
    if subtitle_dir.exists():
        for f in subtitle_dir.glob("test_*"):
            f.unlink()
    yield subtitle_dir


@pytest.fixture
def mock_bili_auth(monkeypatch):
    import config
    monkeypatch.setattr(config.config, "_config", {
        "bili_auth": "SESSDATA=test; bili_jct=test; DedeUserID=123456",
        "polling_interval": 30,
        "auto_start": True,
    })


@pytest.fixture
def whitelisted_uid():
    return "17709654"


@pytest.fixture(autouse=True)
def reset_singleton():
    from database import database
    database.conn = None
    database._db_path = None
    yield
    database.conn = None
    database._db_path = None