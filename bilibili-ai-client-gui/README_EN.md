# Bilibili AI Client GUI

Bilibili AI Client - Automatically extract video subtitles and generate summaries via OpenClaw

[中文](README.md) | English

## Features

- 📝 **Subtitle Extraction**: B站 API > yt-dlp > Whisper local model (built-in)
- 🔐 **QR Code Login**: B站 QR code login, Cookie encrypted storage (XOR + Base64)
- 📋 **Whitelist Filtering**: Only process @messages from whitelisted users
- 🖥️ **GUI**: tkinter modern interface (with scrollable settings)
- 💬 **MCP Protocol**: 6 tool interfaces for AI Agent integration
- 🔗 **OpenClaw Integration**: Trigger OpenClaw to generate video summaries (file-based approach, avoids cmd.exe argument corruption)
- 📊 **Message Polling**: Auto-monitor @messages and dynamics
- 🔄 **Failed Retry**: GUI and API dual-channel support for retrying failed tasks
- 📡 **Webhook**: Support external systems (e.g. n8n) callback triggers

## Core Flow

```
B站 @message/dynamic ──poll──▶ Subtitle Extract ──trigger──▶ OpenClaw ──▶ Summary to DB
                                                         │
Webhook ◀──External System (n8n etc)────────────────────┘
```

## Requirements

- Python 3.10+
- Windows/Linux/macOS
- [OpenClaw](https://openclaw.ai) (optional, for AI summary generation)

## Installation

### 1. Clone repository

```bash
git clone https://github.com/wsererer/bilibili-ai-client-gui.git
cd bilibili-ai-client-gui
```

### 2. Create virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Get Whisper model

```bash
# Method 1: Copy whisper_model folder from bilibili-ai-client (~3.7GB)
# Method 2: Download model
python download_model.py
```

### 5. Login

```bash
python main.py --mode gui
```
Login with QR code. Cookie is automatically encrypted.

### 6. Run

```bash
# GUI mode (recommended)
python main.py --mode gui

# MCP mode (for AI Agent)
python main.py --mode mcp

# Webhook receiver mode
python main.py --mode webhook

# All modes
python main.py --mode all
```

## Cookie Encryption

Cookie is encrypted with XOR + Base64 in `data/config.json`, key in `data/.key`. GUI shows "已登录（加密存储）" only, no plaintext exposed.

## Message Status

| Status | Description |
|--------|-------------|
| `pending` | Waiting for processing |
| `not_whitelisted` | User not in whitelist |
| `no_sender_uid` | No sender UID |
| `triggered` | OpenClaw triggered |
| `processed` | Processing complete |
| `failed` | Processing failed (retryable) |
| `openclaw_failed` | OpenClaw execution failed (retryable) |
| `no_subtitle` | Unable to extract subtitle |

## MCP API (6 tools)

| Tool | Description |
|------|-------------|
| get_pending_messages | Get pending messages |
| get_stats | Get statistics |
| ack_message | Confirm message status |
| add_summary | Add summary record |
| get_summary_history | Get summary history |
| (unknown tool) | Returns error |

## Project Structure

```
bilibili-ai-client-gui/
├── main.py              # Entry point
├── config.py            # Configuration (with encryption)
├── database.py          # SQLite database
├── bilibili_login.py    # QR code login service
├── message_poller.py    # B站 message polling
├── webhook_server.py    # Webhook receiver service
├── mcp_server.py        # MCP protocol service (6 tools)
├── openclaw_trigger.py  # OpenClaw trigger (file-based approach)
├── gui/                 # tkinter GUI
│   └── main_window.py   # Main window (with retry buttons)
├── utils/
│   ├── logger.py
│   ├── crypto.py        # Encryption utility
│   └── subtitle_extractor.py
├── whisper_model/       # Whisper model (copy or download)
├── tests/               # Full test suite (170 passing)
├── docs/                # Documentation
│   ├── PROGRESS.md      # Progress tracking
│   └── API.md           # API documentation
└── pyproject.toml       # Project configuration (pytest/mypy/ruff)
```

## Testing

```bash
# Run all non-network tests
python -m pytest tests/ -m "not network" -v

# Run specific module tests
python -m pytest tests/test_database.py -v

# Lint check
ruff check .

# Full tests (including network)
python -m pytest tests/ -v
```

**Results**: 170 passed, 13 network tests skipped by default, ruff 0 errors.

## Build Executable

```bash
pyinstaller bilibili_ai_client_gui.spec --clean --noconfirm
```

## License

MIT License - See [LICENSE](LICENSE)

## Disclaimer

This project is for educational and research purposes only. Please do not use it for commercial purposes. When using this project, please comply with Bilibili's Terms of Service.
