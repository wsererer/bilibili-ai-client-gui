import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from openclaw_trigger import OpenClawTrigger


class TestOpenClawCommand:
    def test_command_trigger_builds_correct_command(self, monkeypatch):
        triggered = []

        def mock_run(cmd, capture_output=True, text=True, timeout=120, encoding='utf-8', errors='replace'):
            triggered.append(cmd)
            class Result:
                returncode = 0
                stdout = "OK"
                stderr = ""
            return Result()

        monkeypatch.setattr("subprocess.run", mock_run)

        trigger = OpenClawTrigger()
        result = trigger.trigger(
            bv_id="BV1xxx",
            subtitle_text="测试字幕内容",
            sender_uid="123456",
            sender_name="测试用户"
        )

        assert result == True
        assert len(triggered) == 1
        cmd = triggered[0]
        assert "openclaw" in cmd[0].lower()
        assert "--session-id" in cmd
        assert "bilibili-BV1xxx" in cmd
        assert "--message" in cmd

    def test_command_trigger_failure(self, monkeypatch):
        def mock_run(*args, **kwargs):
            class Result:
                returncode = 1
                stdout = ""
                stderr = "Error"
            return Result()

        monkeypatch.setattr("subprocess.run", mock_run)

        trigger = OpenClawTrigger()
        result = trigger.trigger(
            bv_id="BV1xxx",
            subtitle_text="测试",
            sender_uid="123",
            sender_name="用户"
        )

        assert result == False

    def test_custom_openclaw_path(self, monkeypatch):
        triggered = []

        def mock_run(cmd, capture_output=True, text=True, timeout=120, encoding='utf-8', errors='replace'):
            triggered.append(cmd)
            class Result:
                returncode = 0
                stdout = "OK"
                stderr = ""
            return Result()

        monkeypatch.setattr("subprocess.run", mock_run)

        trigger = OpenClawTrigger()
        trigger.set_openclaw_path("/custom/path/openclaw")
        result = trigger.trigger(
            bv_id="BV1xxx",
            subtitle_text="测试",
            sender_uid="123",
            sender_name="用户"
        )

        assert result == True
        assert triggered[0][0] == "/custom/path/openclaw"

    def test_session_id_format(self, monkeypatch):
        triggered = []

        def mock_run(cmd, capture_output=True, text=True, timeout=120, encoding='utf-8', errors='replace'):
            triggered.append(cmd)
            class Result:
                returncode = 0
                stdout = ""
                stderr = ""
            return Result()

        monkeypatch.setattr("subprocess.run", mock_run)

        trigger = OpenClawTrigger()
        trigger.trigger("BV1Y5BxBpEpg", "字幕", "123", "用户")

        cmd = triggered[0]
        session_idx = cmd.index("--session-id")
        assert cmd[session_idx + 1] == "bilibili-BV1Y5BxBpEpg"

    def test_build_message_format(self):
        trigger = OpenClawTrigger()
        msg = trigger._build_message("BV1xxx", "测试字幕", "123456", "用户")
        assert "BV1xxx" in msg
        assert "123456" in msg
        assert "用户" in msg
        assert "测试字幕" in msg
