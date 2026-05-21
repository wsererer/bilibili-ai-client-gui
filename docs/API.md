# API Documentation

## Table of Contents
- [Bilibili APIs](#bilibili-apis)
- [MCP Server Tools](#mcp-server-tools)
- [Webhook Receiver](#webhook-receiver)
- [OpenClaw Integration](#openclaw-integration)
- [Internal APIs](#internal-apis)

---

## Bilibili APIs

### QR Code Login

**Generate QR Code**
```
GET https://passport.bilibili.com/x/passport-login/web/qrcode/generate
```

**Poll Login Status**
```
GET https://passport.bilibili.com/x/passport-login/web/qrcode/poll
Parameters:
  - qrcode_key: string (from generate response)
  - source: main-web
  - gourl: https://www.bilibili.com
```

### Video Information

**Get Video Metadata**
```
GET https://api.bilibili.com/x/web-interface/view
Parameters:
  - bvid: string (e.g., BV1xx411c7mD)
```

**Get Subtitles**
```
GET https://api.bilibili.com/x/player/v2
Parameters:
  - cid: number (from view API)
  - bvid: string
Headers:
  - Cookie: SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx
```

Response:
```json
{
  "data": {
    "subtitle": {
      "subtitles": [
        {
          "subtitle_url": "//xxxxx",
          "lan": "zh",
          "type": 0
        }
      ]
    }
  }
}
```

Subtitle type: 0 = user subtitle, 1 = AI subtitle

### Messages

**Get @ Mentions**
```
GET https://api.bilibili.com/x/msgfeed/at
Headers:
  - Cookie: SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx
```

---

## MCP Server Tools

The MCP server provides tools for AI Agent integration. Run with:
```bash
python main.py --mode mcp
```

### Tools

#### get_pending_messages
Get pending messages for processing.

```json
{
  "name": "get_pending_messages",
  "arguments": {}
}
```

#### get_subtitle
Get subtitle for a specific BV video.

```json
{
  "name": "get_subtitle",
  "arguments": {
    "bv_id": "BV1xx411c7mD"
  }
}
```

#### ack_message
Acknowledge message processing.

```json
{
  "name": "ack_message",
  "arguments": {
    "msg_id": "xxx",
    "status": "processed|failed"
  }
}
```

#### get_summary_history
Get video summary history.

```json
{
  "name": "get_summary_history",
  "arguments": {
    "limit": 50
  }
}
```

#### add_summary
Add a new video summary.

```json
{
  "name": "add_summary",
  "arguments": {
    "bv_id": "BV1xx411c7mD",
    "sender_uid": "123456",
    "sender_name": "username",
    "subtitle_text": "original subtitle",
    "summary_text": "AI summary"
  }
}
```

#### get_stats
Get processing statistics.

```json
{
  "name": "get_stats",
  "arguments": {}
}
```

---

## Webhook Receiver

The webhook receiver allows external services to push messages to the app. Run with:
```bash
python main.py --mode webhook
```

### POST /webhook
Receive external webhook calls.

Request:
```json
{
  "type": "dynamic|live_dm",
  "id": "message_id",
  "bv_id": "BV1xx411c7mD",
  "uid": "123456",
  "uname": "username",
  "content": "message content"
}
```

Response:
```json
{
  "status": "ok"
}
```

### GET /health
Health check endpoint.

Response:
```json
{
  "status": "healthy"
}
```

---

## OpenClaw Integration

OpenClaw is triggered via CLI command:

```bash
openclaw agent --message "处理视频任务..."
```

### Configuration

| Config Key | Description | Default |
|-----------|-------------|---------|
| `openclaw_path` | Path to openclaw executable | `openclaw` |

### Message Format

```
处理视频任务
==========
BV号: BV1xx411c7mD
发送者UID: 123456 (username)

字幕内容:
{subtitle text}
==========

请生成视频摘要并保存到 ~/.openclaw/workspace/bilibili-summaries/ 目录。
格式: {日期}/{BV号}.md
```

---

## Internal APIs

### Subtitle Extraction Priority Chain

```
1. B站 API (/x/web-interface/view) — 获取视频标题和信息
2. B站 API (/x/player/v2) — 获取字幕 (user > AI)
3. yt-dlp download — 下载字幕
4. Whisper transcription — 音频转写
```

### Configuration

- `data/login_cookie.txt` - Primary cookie source
- `data/config.json` - App config (auto-loaded from login_cookie.txt on startup)
- Cookie must be >50 chars and contain SESSDATA

### Database Schema

```sql
-- Messages table
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  sender_uid TEXT NOT NULL,
  sender_name TEXT,
  bv_id TEXT NOT NULL,
  content TEXT,
  received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  status TEXT DEFAULT 'pending'
);

-- Whitelist table
CREATE TABLE whitelist (
  uid TEXT PRIMARY KEY,
  username TEXT,
  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Summaries table
CREATE TABLE summaries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bv_id TEXT NOT NULL,
  sender_uid TEXT,
  sender_name TEXT,
  subtitle_text TEXT,
  summary_text TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Message statuses: `pending`, `not_whitelisted`, `triggered`, `trigger_failed`, `no_subtitle`
