import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from openclaw_trigger import OpenClawTrigger


class TestOpenClawCommand:
    def test_command_trigger_builds_correct_command(self, monkeypatch):
        triggered = []

        def mock_run(cmd, shell=True, capture_output=True, text=True):
            triggered.append(cmd)
            class Result:
                returncode = 0
                stdout = "OK"
                stderr = ""
            return Result()

        monkeypatch.setattr("subprocess.run", mock_run)

        trigger = OpenClawTrigger(mode="command")
        result = trigger.trigger(
            bv_id="BV1xxx",
            subtitle_text="测试字幕内容",
            sender_uid="123456",
            sender_name="测试用户"
        )

        assert result == True
        assert len(triggered) == 1
        cmd = triggered[0]
        assert "openclaw" in cmd.lower()
        assert "BV1xxx" in cmd

    def test_command_trigger_failure(self, monkeypatch):
        def mock_run(*args, **kwargs):
            class Result:
                returncode = 1
                stdout = ""
                stderr = "Error"
            return Result()

        monkeypatch.setattr("subprocess.run", mock_run)

        trigger = OpenClawTrigger(mode="command")
        result = trigger.trigger(
            bv_id="BV1xxx",
            subtitle_text="测试",
            sender_uid="123",
            sender_name="用户"
        )

        assert result == False


class TestOpenClawWebhook:
    @pytest.mark.asyncio
    async def test_webhook_trigger_builds_payload(self, monkeypatch):
        triggered = []

        class FakeResponse:
            status_code = 200

        async def mock_post(url, json=None, timeout=None):
            triggered.append({"url": url, "json": json})
            return FakeResponse()

        import httpx
        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

        trigger = OpenClawTrigger(mode="webhook", webhook_url="http://test.local/hooks")
        result = await trigger.trigger(
            bv_id="BV1xxx",
            subtitle_text="测试字幕",
            sender_uid="123456",
            sender_name="测试用户"
        )

        assert result == True
        assert len(triggered) == 1
        assert triggered[0]["url"] == "http://test.local/hooks"
        assert "BV1xxx" in str(triggered[0]["json"])


class TestOpenClawConnection:
    def test_check_connection_timeout(self, monkeypatch):
        import httpx

        async def mock_get(*args, **kwargs):
            raise httpx.ConnectError("Connection failed")

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        trigger = OpenClawTrigger()
        result = trigger.check_connection("http://invalid.local/health", timeout=1)
        assert result == False