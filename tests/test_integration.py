import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import asyncio


class TestEndToEndMessageProcessing:
    @pytest.mark.asyncio
    async def test_process_new_message_whitelisted(self, whitelisted_uid):
        from main import process_new_message
        from database import database

        database.add_whitelist(whitelisted_uid, "白名单用户")

        test_msg = {
            "msg_id": f"e2e_{int(time.time()*1000)}",
            "bv_id": "BV1h8rDBFEV7",
            "sender_uid": whitelisted_uid,
            "sender_name": "白名单用户",
            "content": "测试"
        }

        await process_new_message(test_msg)

    @pytest.mark.asyncio
    async def test_process_new_message_not_whitelisted(self):
        from main import process_new_message
        from database import database

        before_count = len(database.get_pending_messages())

        test_msg = {
            "msg_id": "e2e_not_whitelisted",
            "bv_id": "BV1h8rDBFEV7",
            "sender_uid": "999999999",
            "sender_name": "非白名单",
            "content": "测试"
        }

        await process_new_message(test_msg)

        after_count = len(database.get_pending_messages())
        assert after_count == before_count


class TestSubtitleExtractionPipeline:
    def test_subtitle_priority_bv1y5(self):
        from utils.subtitle_extractor import SubtitleExtractor
        extractor = SubtitleExtractor()
        result = extractor.extract("https://www.bilibili.com/video/BV1Y5BxBpEpg")

        assert result is not None
        assert result.source == "subtitle"
        raw_path_lower = result.raw_subtitle_path.lower()
        assert "zh" in raw_path_lower and "ai-zh" not in raw_path_lower

    def test_subtitle_priority_bv1h8(self):
        from utils.subtitle_extractor import SubtitleExtractor
        extractor = SubtitleExtractor()
        result = extractor.extract("https://www.bilibili.com/video/BV1h8rDBFEV7")

        assert result is not None
        assert result.source == "subtitle"


class TestStartupModes:
    def test_mode_all_starts(self):
        import subprocess

        proc = subprocess.Popen(
            ["python", "main.py", "--mode", "all"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(3)
        poll = proc.poll()
        assert poll is None, f"进程应该运行，实际退出码: {poll}"
        proc.terminate()
        proc.wait(timeout=5)

    def test_mode_gui_starts(self):
        import subprocess

        proc = subprocess.Popen(
            ["python", "main.py", "--mode", "gui"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(3)
        poll = proc.poll()
        assert poll is None, f"GUI模式应该运行，实际退出码: {poll}"
        proc.terminate()
        proc.wait(timeout=5)


class TestExceptionHandling:
    def test_invalid_url_returns_none(self):
        from utils.subtitle_extractor import SubtitleExtractor
        extractor = SubtitleExtractor()
        result = extractor.extract("https://youtube.com/watch?v=invalid")
        assert result is None

    def test_empty_cookie_uses_whisper_fallback(self):
        from utils.subtitle_extractor import SubtitleExtractor
        extractor = SubtitleExtractor()
        original = extractor.cookie
        extractor.cookie = ""
        result = extractor.extract("https://www.bilibili.com/video/BV1h8rDBFEV7")
        extractor.cookie = original
        if result:
            assert result.source in ["subtitle", "whisper"]