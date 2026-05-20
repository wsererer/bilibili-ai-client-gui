# API Documentation

## Table of Contents
- [Bilibili APIs](#bilibili-apis)
- [MCP Server Tools](#mcp-server-tools)
- [Webhook Endpoints](#webhook-endpoints)
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
          "type": 0  // 0=user subtitle, 1=AI subtitle
        }
      ]
    }
  }
}
```

### Dynamic Feed

**Get Dynamic Tabs**
```
GET https://api.bilibili.com/x/dynamic/app/tabs/v2
```

**Get Dynamic Feed**
```
GET https://api.bilibili.com/x/dynamic/app/feed/topic
Parameters:
  - topic: string (e.g., DYNAMIC_TOPIC_ALL)
```

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

Response:
```json
{
  "messages": [
    {
      "msg_id": "xxx",
      "bv_id": "BV1xx411c7mD",
      "sender_uid": "123456",
      "sender_name": "username",
      "content": "message content",
      "status": "pending"
    }
  ]
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

Response:
```json
{
  "title": "Video Title",
  "video_id": "BV1xx411c7mD",
  "source": "subtitle|whisper",
  "transcript_text": "Transcript content..."
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

Response:
```json
{
  "summaries": [
    {
      "id": 1,
      "bv_id": "BV1xx411c7mD",
      "sender_uid": "123456",
      "sender_name": "username",
      "subtitle_text": "original subtitle",
      "summary_text": "summary by AI",
      "created_at": "2024-01-01 12:00:00"
    }
  ]
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

Response:
```json
{
  "today": 10,
  "total": 100
}
```

---

## Webhook Endpoints

Start webhook server with:
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

## Internal APIs

### Subtitle Extraction Priority Chain

```
1. B站 API (user subtitles, type=0)
   └─> Retry up to 5 times if only AI subtitles returned

2. B站 API (AI subtitles, type=1)
   └─> Fallback if no user subtitles

3. yt-dlp download
   └─> Download subtitles via yt-dlp

4. Whisper transcription
   └─> Download audio and transcribe with faster-whisper
```

### Configuration

- `data/login_cookie.txt` - Primary cookie source
- `data/config.json` - Alternative cookie via `bili_auth` key
- Cookie must be >50 chars for API authentication

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

### OpenClaw Integration

**Webhook Mode:**
```
POST http://127.0.0.1:18789/hooks/agent
```

**Command Mode:**
```
openclaw agent --message "message content"
```