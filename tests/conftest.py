import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from pathlib import Path
import sqlite3
from typing import Generator



@pytest.fixture
def temp_db(tmp_path: Path) -> Generator[Path, None, None]:
    db_file = tmp_path / "test_bilibili_client.db"
    yield db_file
    if db_file.exists():
        db_file.unlink()


@pytest.fixture
def test_db(temp_db: Path) -> Generator[None, None, None]:
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            uid TEXT PRIMARY KEY,
            username TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            sender_uid TEXT NOT NULL,
            sender_name TEXT,
            bv_id TEXT NOT NULL,
            content TEXT,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bv_id TEXT NOT NULL,
            sender_uid TEXT,
            sender_name TEXT,
            subtitle_text TEXT,
            summary_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            date TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()
    yield


@pytest.fixture
def valid_cookie():
    cookie_path = Path("data/login_cookie.txt")
    if cookie_path.exists():
        return cookie_path.read_text().strip()
    pytest.skip("No cookie file at data/login_cookie.txt")


@pytest.fixture
def config_backup(tmp_path: Path, monkeypatch):
    import config as config_module

    backup = {}
    for key in ["language", "theme", "polling_interval", "auto_start", "bili_auth"]:
        backup[key] = config_module.config.get(key)

    yield config_module.config

    for key, value in backup.items():
        config_module.config.set(key, value)


@pytest.fixture
def clean_subtitles():
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


@pytest.fixture
def mock_httpx(monkeypatch):
    import httpx

    class MockResponse:
        def __init__(self, json_data: dict, status_code: int = 200):
            self._json = json_data
            self.status_code = status_code

        def json(self):
            return self._json

    class MockAsyncClient:
        def __init__(self, **kwargs):
            self.base_url = kwargs.get("base_url", "")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url: str, **kwargs) -> MockResponse:
            return MockResponse({"code": 0, "data": []})

        async def post(self, url: str, **kwargs) -> MockResponse:
            return MockResponse({"code": 0})

        async def aclose(self):
            pass

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)


@pytest.fixture
def mock_subprocess(monkeypatch):
    import subprocess

    class MockCompletedProcess:
        def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    class MockPopen:
        def __init__(self, args, **kwargs):
            self.args = args
            self.returncode = 0

        def communicate(self, timeout=None):
            return ('{"summary": "测试摘要"}', b"")

        def wait(self, timeout=None):
            return 0

    def mock_run(*args, **kwargs):
        return MockCompletedProcess(stdout='{"summary": "测试摘要"}', returncode=0)

    def mock_popen(*args, **kwargs):
        return MockPopen(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(subprocess, "Popen", mock_popen)