import json
from typing import Any, List
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server
import asyncio

from database import database
from utils.subtitle_extractor import subtitle_extractor
from utils.logger import logger

SERVER_NAME = "bilibili-ai-client"
SERVER_VERSION = "1.0.0"

server = Server(SERVER_NAME)

@server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="get_pending_messages",
            description="获取待处理的消息列表，包含BV号和发送者信息",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_subtitle",
            description="获取指定BV号的字幕内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "bv_id": {
                        "type": "string",
                        "description": "B站视频BV号，如 BV1xx411c7mD"
                    }
                },
                "required": ["bv_id"]
            }
        ),
        Tool(
            name="ack_message",
            description="确认消息已处理",
            inputSchema={
                "type": "object",
                "properties": {
                    "msg_id": {
                        "type": "string",
                        "description": "消息ID"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["processed", "failed"],
                        "description": "处理状态"
                    }
                },
                "required": ["msg_id", "status"]
            }
        ),
        Tool(
            name="get_summary_history",
            description="获取视频摘要历史记录",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回记录数量，默认50",
                        "default": 50
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="add_summary",
            description="添加新的视频摘要记录",
            inputSchema={
                "type": "object",
                "properties": {
                    "bv_id": {
                        "type": "string",
                        "description": "B站视频BV号"
                    },
                    "sender_uid": {
                        "type": "string",
                        "description": "发送者UID"
                    },
                    "sender_name": {
                        "type": "string",
                        "description": "发送者用户名"
                    },
                    "subtitle_text": {
                        "type": "string",
                        "description": "字幕文本"
                    },
                    "summary_text": {
                        "type": "string",
                        "description": "摘要内容"
                    }
                },
                "required": ["bv_id", "summary_text"]
            }
        ),
        Tool(
            name="get_stats",
            description="获取统计数据",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    try:
        if name == "get_pending_messages":
            messages = database.get_pending_messages()
            return [TextContent(type="text", text=json.dumps(messages, ensure_ascii=False))]

        elif name == "get_subtitle":
            bv_id = arguments.get("bv_id")
            if not bv_id:
                return [TextContent(type="text", text=json.dumps({"error": "bv_id is required"}))]
            url = f"https://www.bilibili.com/video/{bv_id}"
            text = subtitle_extractor.extract_text(url)
            return [TextContent(type="text", text=json.dumps({"bv_id": bv_id, "subtitle": text}, ensure_ascii=False))]

        elif name == "ack_message":
            msg_id = arguments.get("msg_id")
            status = arguments.get("status", "processed")
            if msg_id:
                database.update_message_status(msg_id, status)
            return [TextContent(type="text", text=json.dumps({"success": True}))]

        elif name == "get_summary_history":
            limit = arguments.get("limit", 50)
            summaries = database.get_summaries(limit)
            return [TextContent(type="text", text=json.dumps(summaries, ensure_ascii=False))]

        elif name == "add_summary":
            bv_id = arguments.get("bv_id", "")
            sender_uid = arguments.get("sender_uid", "")
            sender_name = arguments.get("sender_name", "")
            subtitle_text = arguments.get("subtitle_text", "")
            summary_text = arguments.get("summary_text", "")

            summary_id = database.add_summary(bv_id, sender_uid, sender_name, subtitle_text, summary_text)
            return [TextContent(type="text", text=json.dumps({"success": True, "id": summary_id}))]

        elif name == "get_stats":
            today_count = database.get_today_count()
            total_count = database.get_total_count()
            return [TextContent(type="text", text=json.dumps({
                "today": today_count,
                "total": total_count
            }))]

        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    except Exception as e:
        logger.error(f"MCP tool error: {name} - {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    logger.info("Starting Bilibili AI Client MCP Server")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())