import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import sqlite3


class TestDatabaseInit:
    def test_db_exists(self):
        from database import database
        db_path = Path("data/bilibili_client.db")
        assert db_path.exists()

    def test_table_creation(self):
        conn = sqlite3.connect("data/bilibili_client.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert "whitelist" in tables
        assert "messages" in tables
        assert "summaries" in tables
        assert "stats" in tables


class TestWhitelist:
    def test_add_whitelist(self):
        from database import database
        test_uid = "test_999988"
        result = database.add_whitelist(test_uid, "测试用户")
        assert result == True
        assert database.is_whitelist(test_uid) == True
        database.remove_whitelist(test_uid)

    def test_remove_whitelist(self):
        from database import database
        test_uid = "test_999987"
        database.add_whitelist(test_uid, "测试用户")
        database.remove_whitelist(test_uid)
        assert database.is_whitelist(test_uid) == False

    def test_duplicate_add(self):
        from database import database
        test_uid = "test_999986"
        database.add_whitelist(test_uid, "用户1")
        database.add_whitelist(test_uid, "用户2")
        assert database.is_whitelist(test_uid) == True
        database.remove_whitelist(test_uid)


class TestMessages:
    def test_add_message(self):
        from database import database
        import time
        msg_id = f"test_msg_{int(time.time()*1000)}"
        result = database.add_message(msg_id=msg_id, sender_uid="123", sender_name="用户A",
                                      bv_id="BV1xxx", content="测试消息")
        assert result == True
        pending = database.get_pending_messages()
        assert any(m["id"] == msg_id for m in pending)

    def test_update_status(self):
        from database import database
        import time
        msg_id = f"test_msg_{int(time.time()*1000)}"
        database.add_message(msg_id=msg_id, sender_uid="123", sender_name="用户",
                           bv_id="BV1xxx", content="测试")
        database.update_message_status(msg_id, "processed")
        pending = database.get_pending_messages()
        assert not any(m["id"] == msg_id for m in pending)


class TestSummaries:
    def test_add_summary(self):
        from database import database
        import time
        summary_id = database.add_summary(
            bv_id=f"BV1test_{int(time.time())}",
            sender_uid="123",
            sender_name="用户",
            subtitle_text="字幕内容",
            summary_text="摘要内容"
        )
        assert summary_id is not None and summary_id > 0

    def test_get_summaries(self):
        from database import database
        summaries = database.get_summaries(limit=10)
        assert isinstance(summaries, list)


class TestStats:
    def test_increment_stats(self):
        from database import database
        before_today = database.get_today_count()
        before_total = database.get_total_count()

        database.add_summary(
            bv_id=f"BV1test_{int(time.time())}",
            sender_uid="123",
            sender_name="用户",
            subtitle_text="字幕",
            summary_text="摘要"
        )

        assert database.get_today_count() == before_today + 1
        assert database.get_total_count() == before_total + 1

    def test_get_today_total(self):
        from database import database
        assert isinstance(database.get_today_count(), int)
        assert isinstance(database.get_total_count(), int)
        assert database.get_total_count() >= database.get_today_count()