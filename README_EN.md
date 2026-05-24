# Bilibili AI Client GUI

Bilibili AI Client - Automatically extract video subtitles and generate summaries via OpenClaw

[中文](README.md) | English

## Features

- 📝 **Subtitle Extraction**: B站 API > yt-dlp > Whisper local model (built-in)
- 🔐 **QR Code Login**: B站 QR code login, Cookie encrypted storage (XOR + Base64)
- 📋 **Whitelist Filtering**: Only process @messages from whitelisted users
- 🖥️ **GUI**: PySide6 Qt modern interface (dark/light theme toggle, collapsible log panel, window state persistence)
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
# Method 1: Copy whisper_model folder (~3.7GB)
# Method 2: Download model
python download_model.py
```

### 5. First-time configuration

Start the GUI:

```bash
python main.py --mode gui
```

Open the **Settings** panel and follow these steps:

#### 5.1 Add whitelist
Only @messages from whitelisted users will be processed. In the "Whitelist" section:
- Enter your Bilibili UID (numeric)
- Click "Add"
- (For testing, add `12345678` first)

#### 5.2 Login to Bilibili
- **Method 1 (recommended)**: Click "Web Login" → Browser opens QR code → Scan with Bilibili App → Cookie saved automatically
- **Method 2**: Click "Manual Cookie Input" → F12 in browser → Application → Cookies → Copy `SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx` → Paste into input

Message polling starts automatically after successful login.

#### 5.3 Configure OpenClaw
OpenClaw is the AI summary generation engine. It must be installed locally.

- **Install OpenClaw**: Visit [OpenClaw website](https://openclaw.ai) to download and install
- **Set OpenClaw path**:
  - Enter the executable path in the "OpenClaw Path" field in Settings
  - Default: `openclaw` (when added to system PATH)
  - Windows: `C:\Users\YourUsername\AppData\Roaming\npm\openclaw.cmd`
  - Linux/macOS: `/usr/local/bin/openclaw` or `npx openclaw`
- Click "Browse" button to use the file picker

#### 5.4 Configure auto-push (optional)
Auto-push sends summaries to WeChat or Feishu after generation:

1. Check "Enable Auto Push"
2. Select push channel: WeChat / Feishu / Both
3. Enter target account:
   - **WeChat target**: Get your chat_id from OpenClaw. After starting the WeChat account in OpenClaw, use `openclaw wx message --target xxx` to list available targets. Format: `wx_xxxx@im.wechat`
   - **Feishu target**: Your Feishu user ID or group chat ID
4. Click "Save Settings"

> **Note**: If the target account is empty, OpenClaw will not append target parameters and the push may fail. Make sure to log in to WeChat/Feishu in OpenClaw first.

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
├── gui/                 # PySide6 Qt GUI
│   ├── app.py           # qasync entry + QApplication init
│   ├── main_window.py   # Main window (menu bar, status bar, tray, window persistence)
│   ├── signal_bus.py    # Global signal bus
│   ├── theme.py         # Theme manager (light/dark toggle, inline QSS)
│   ├── pages/           # Page components
│   │   ├── messages_page.py
│   │   ├── history_page.py
│   │   ├── stats_page.py
│   │   ├── logs_page.py
│   │   └── settings_page.py
│   ├── widgets/         # Reusable widgets
│   │   ├── sidebar.py
│   │   ├── log_panel.py
│   │   ├── stat_card.py
│   │   └── summary_dialog.py
│   └── models/          # Qt data models
│       ├── message_model.py
│       ├── summary_model.py
│       └── whitelist_model.py
├── utils/
│   ├── logger.py
│   ├── crypto.py        # Encryption utility
│   └── subtitle_extractor.py
├── whisper_model/       # Whisper model (copy or download)
├── tests/               # Full test suite (250 passing)
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

**Results**: 250 passed (248 common + 2 signal isolation skipped), ruff 0 errors.

## Build Executable

```bash
pyinstaller pyinstaller.spec --clean --noconfirm
```

> Output: `dist/BilibiliAIClient.exe` (~2GB, includes Whisper model)

## Version

Current version: **v1.1.0**
- Full PySide6 Qt GUI migration (replaced tkinter)
- Dark/light theme toggle, system tray, window state persistence
- 8 operational logic bug fixes (signal routing, poller callback, stats update, etc.)
- Single instance protection, proper exit cleanup
- Note: `v1.0.0` was the tkinter version, `v1.1.0` is the PySide6 version

## License

MIT License - See [LICENSE](LICENSE)

## Disclaimer

This project is for educational and research purposes only. Please do not use it for commercial purposes. When using this project, please comply with Bilibili's Terms of Service.
