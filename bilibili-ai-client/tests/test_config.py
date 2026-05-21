import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from config import Config, config


class TestConfigSingleton:
    def test_singleton_identity(self):
        c1 = Config()
        c2 = Config()
        assert c1 is c2 is config

    def test_defaults(self):
        assert config.get("language") == "zh"
        assert config.get("theme") == "light"
        assert config.get("polling_interval") == 30
        assert config.get("auto_start") == True
        assert config.get("webhook_port") == 18792


class TestConfigGetSet:
    def test_set_and_get(self, tmp_path, monkeypatch):
        import json
        test_file = tmp_path / "config.json"

        monkeypatch.setattr("config.CONFIG_FILE", test_file)
        c = Config()
        c.set("test_key", "test_value")
        assert c.get("test_key") == "test_value"

    def test_nested_dict(self, tmp_path, monkeypatch):
        import json
        test_file = tmp_path / "config.json"

        monkeypatch.setattr("config.CONFIG_FILE", test_file)
        c = Config()
        c.set("nested", {"a": 1, "b": 2})
        assert c.get("nested") == {"a": 1, "b": 2}


class TestConfigBiliAuth:
    def test_valid_cookie(self, tmp_path, monkeypatch):
        test_file = tmp_path / "config.json"
        monkeypatch.setattr("config.CONFIG_FILE", test_file)
        c = Config()
        valid_cookie = "SESSDATA=abc123,456789,abc*def; bili_jct=xyz; DedeUserID=123456"
        c.set("bili_auth", valid_cookie)
        assert len(c.get("bili_auth")) > 50
        assert "SESSDATA" in c.get("bili_auth")

    def test_empty_cookie(self, tmp_path, monkeypatch):
        test_file = tmp_path / "config.json"
        monkeypatch.setattr("config.CONFIG_FILE", test_file)
        c = Config()
        c.set("bili_auth", "")
        assert c.get("bili_auth") == ""


class TestConfigProperties:
    def test_polling_interval(self, tmp_path, monkeypatch):
        test_file = tmp_path / "config.json"
        monkeypatch.setattr("config.CONFIG_FILE", test_file)
        c = Config()
        c.set("polling_interval", 60)
        assert c.polling_interval == 60

    def test_auto_start(self, tmp_path, monkeypatch):
        test_file = tmp_path / "config.json"
        monkeypatch.setattr("config.CONFIG_FILE", test_file)
        c = Config()
        c.set("auto_start", False)
        assert c.auto_start == False