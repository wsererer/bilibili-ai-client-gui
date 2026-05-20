import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

from utils.app_data import APP_DATA_DIR

CONFIG_FILE = APP_DATA_DIR / "config.json"

DEFAULT_CONFIG = {
    "language": "zh",
    "theme": "light",
    "message_mode": "polling",
    "polling_interval": 30,
    "openclaw_trigger": "command",
    "webhook_url": "http://127.0.0.1:18789/hooks/agent",
    "webhook_port": 18792,
    "auto_start": True,
    "window_geometry": None,
    "last_login_uid": None,
    "bili_auth": "",
}


class Config:
    _instance: Optional['Config'] = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except Exception:
                self._config = DEFAULT_CONFIG.copy()
        else:
            self._config = DEFAULT_CONFIG.copy()
        for key, value in DEFAULT_CONFIG.items():
            if key not in self._config:
                self._config[key] = value
        self._load_cookie_from_file()

    def _load_cookie_from_file(self):
        cookie_file = APP_DATA_DIR / "login_cookie.txt"
        if cookie_file.exists():
            try:
                cookie = cookie_file.read_text(encoding='utf-8').strip()
                if cookie and len(cookie) > 50 and "SESSDATA" in cookie:
                    if not self._config.get("bili_auth") or "SESSDATA" not in self._config.get("bili_auth", ""):
                        self._config["bili_auth"] = cookie
            except Exception:
                pass

    def save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default=None):
        return self._config.get(key, default)

    def set(self, key: str, value):
        self._config[key] = value
        self.save()

    @property
    def language(self) -> str:
        return self._config.get("language", "zh")

    @language.setter
    def language(self, value: str):
        self._config["language"] = value
        self.save()

    @property
    def theme(self) -> str:
        return self._config.get("theme", "light")

    @theme.setter
    def theme(self, value: str):
        self._config["theme"] = value
        self.save()

    @property
    def message_mode(self) -> str:
        return self._config.get("message_mode", "polling")

    @message_mode.setter
    def message_mode(self, value: str):
        self._config["message_mode"] = value
        self.save()

    @property
    def polling_interval(self) -> int:
        return self._config.get("polling_interval", 30)

    @polling_interval.setter
    def polling_interval(self, value: int):
        self._config["polling_interval"] = value
        self.save()

    @property
    def openclaw_trigger(self) -> str:
        return self._config.get("openclaw_trigger", "command")

    @openclaw_trigger.setter
    def openclaw_trigger(self, value: str):
        self._config["openclaw_trigger"] = value
        self.save()

    @property
    def webhook_url(self) -> str:
        return self._config.get("webhook_url", "http://127.0.0.1:18789/hooks/agent")

    @webhook_url.setter
    def webhook_url(self, value: str):
        self._config["webhook_url"] = value
        self.save()

    @property
    def auto_start(self) -> bool:
        return self._config.get("auto_start", True)

    @property
    def window_geometry(self) -> Optional[dict]:
        return self._config.get("window_geometry")

    @window_geometry.setter
    def window_geometry(self, value):
        self._config["window_geometry"] = value
        self.save()


config = Config()