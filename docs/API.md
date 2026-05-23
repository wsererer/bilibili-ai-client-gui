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

#### get_stats
Get processing statistics.

```json
{
  "name": "get_stats",
  "arguments": {}
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
openclaw agent --message "..." --agent main --json
```

### Configuration

| Config Key | Description | Default |
|-----------|-------------|---------|
| `openclaw_path` | Path to openclaw executable | `openclaw` |
| `auto_send` | Enable auto-send after summary | `false` |
| `send_channel` | Send channel (wechat/feishu/both) | `wechat` |
| `wechat_target` | WeChat target account ID | `""` |
| `feishu_target` | Feishu target account ID | `""` |

### Message Format (File-Based Approach)

**v2.0 变更**: 字幕文本不再嵌入 `--message` 参数，改为写入临时文件，`--message` 中仅携带文件路径和 read 指令。

```
处理视频任务 | BV号: BV1xx411c7mD | 发送者UID: 123456 (username) | 请使用 read 工具读取字幕文件，然后生成视频摘要并保存 | 字幕文件路径: C:\Users\xxx\AppData\Local\Temp\BV1xxx_sub_abc123.txt | 请生成视频摘要并保存到 ~/.openclaw/workspace/bilibili-summaries/ 目录 | 格式: 日期/BV号.md | 【重要】处理完成后，通过微信发送摘要给用户，目标账号: o9cq...@im.wechat
```

当 `auto_send=true` 且目标账号已配置时，末尾会追加发送指令及目标账号。
目标账号为空时不附加 `，目标账号:` 部分。

关键设计决策：
- `--message` 为**单行**（无换行符），避免 Windows `cmd.exe` 解析 `.cmd` 批处理文件时损坏参数
- 长字幕文本通过 `tempfile.mkstemp()` 写入临时文件，trigger 完成后自动清理
- Agent 被指示使用 `read` 工具读取临时文件内容
- `--deliver` 已移除（无 MCP 投递目标时返回 RC=1，但处理结果已保存）

### Fix History

| Bug | Root Cause | Solution |
|-----|-----------|----------|
| B-22 | Windows `cmd.exe` 在通过 `.cmd` 批处理包装器传递含换行符的长参数时静默损坏参数边界，导致 `--agent main` 参数丢失，触发 "Pass --to <E.164>, --session-id, or --agent" 错误 | 字幕写入临时文件，`--message` 使用单行管道格式（无换行符），Agent 通过 `read` 工具读取文件 |

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

Message statuses: `pending`, `not_whitelisted`, `triggered`, `trigger_failed`, `no_subtitle`, `processed`, `failed`, `openclaw_failed`
