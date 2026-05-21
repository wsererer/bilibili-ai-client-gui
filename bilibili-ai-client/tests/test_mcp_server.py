import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from mcp_server import list_tools, call_tool
import json


class TestMCPServerTools:
    @pytest.mark.asyncio
    async def test_list_tools_returns_six_tools(self):
        tools = await list_tools()
        assert len(tools) == 6

    @pytest.mark.asyncio
    async def test_tools_have_correct_names(self):
        tools = await list_tools()
        tool_names = [t.name for t in tools]
        assert "get_pending_messages" in tool_names
        assert "get_subtitle" in tool_names
        assert "ack_message" in tool_names
        assert "get_summary_history" in tool_names
        assert "add_summary" in tool_names
        assert "get_stats" in tool_names

    @pytest.mark.asyncio
    async def test_get_stats_returns_today_and_total(self):
        results = await call_tool("get_stats", {})
        assert len(results) == 1
        data = json.loads(results[0].text)
        assert "today" in data
        assert "total" in data
        assert isinstance(data["today"], int)
        assert isinstance(data["total"], int)

    @pytest.mark.asyncio
    async def test_ack_message_success(self):
        results = await call_tool("ack_message", {"msg_id": "test_msg", "status": "processed"})
        assert len(results) == 1
        data = json.loads(results[0].text)
        assert data.get("success") == True

    @pytest.mark.asyncio
    async def test_get_pending_messages_returns_list(self):
        results = await call_tool("get_pending_messages", {})
        assert len(results) == 1
        data = json.loads(results[0].text)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_add_summary_success(self):
        results = await call_tool("add_summary", {
            "bv_id": "BV1test",
            "sender_uid": "123",
            "sender_name": "测试",
            "subtitle_text": "字幕",
            "summary_text": "摘要"
        })
        assert len(results) == 1
        data = json.loads(results[0].text)
        assert data.get("success") == True

    @pytest.mark.asyncio
    async def test_get_summary_history(self):
        results = await call_tool("get_summary_history", {"limit": 10})
        assert len(results) == 1
        data = json.loads(results[0].text)
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        results = await call_tool("nonexistent_tool", {})
        assert len(results) == 1
        data = json.loads(results[0].text)
        assert "error" in data