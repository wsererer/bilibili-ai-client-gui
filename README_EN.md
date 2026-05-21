# Bilibili AI Client GUI

Bilibili AI Client - Automatically extract subtitles and AI-reply to Bilibili dynamics/comments

[中文](README.md) | English

## Features

- 🤖 **AI Auto-Reply**: Automatically reply to Bilibili dynamics and comments
- 📝 **Smart Subtitle Extraction**: B站 API > yt-dlp > Whisper multi-priority chain
- 🔐 **QR Code Login**: Cookie authentication with auto-persistence
- 📋 **Whitelist Management**: Only process comments from whitelisted users, auto-reprocess blocked messages when whitelist is updated
- 🖥️ **Graphical Interface**: Modern PyQt6 GUI
- 💬 **MCP Protocol**: Communicate with AI Agent via Model Context Protocol
- 🔗 **OpenClaw Integration**: Trigger OpenClaw via CLI command to process videos

## Requirements

- Python 3.10+
- Windows/Linux/macOS
- [OpenClaw](https://openclaw.ai) (optional, for AI video processing)

## Installation

### 1. Clone the repository

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

### 4. Download Whisper model (optional)

```bash
python download_model.py
```

### 5. Configuration

Create `data/` directory and add the following file:

**`data/login_cookie.txt`** - Bilibili login cookie:
```
SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx
```

How to obtain:
1. Login to [bilibili.com](https://bilibili.com)
2. F12 to open Developer Tools → Application → Cookies
3. Copy SESSDATA, bili_jct, DedeUserID values

### 6. Run

```bash
# GUI mode
python main.py --mode gui

# MCP mode (for AI Agent)
python main.py --mode mcp

# Webhook receiver mode (receive external messages)
python main.py --mode webhook

# All modes
python main.py --mode all
```

## OpenClaw Integration

The software calls OpenClaw via CLI command to process videos:

```bash
openclaw agent --message "Process video task..."
```

### Configure OpenClaw Path

You can customize the OpenClaw executable path in GUI settings (default: `openclaw`).

If `openclaw` is not in your system PATH, specify the full path:
```
C:\Users\YourName\AppData\Roaming\npm\openclaw.cmd
```

## Whitelist Mechanism

- Only comments from whitelisted users are processed
- Comments from non-whitelisted users are recorded with `not_whitelisted` status
- When a new user is added to the whitelist, their previously blocked comments are automatically reprocessed

## Project Structure

```
bilibili-ai-client-gui/
├── main.py              # Entry point
├── config.py            # Configuration
├── database.py          # Database module
├── bilibili_login.py    # QR code login
├── message_poller.py    # Message polling
├── webhook_server.py    # Webhook receiver server
├── mcp_server.py        # MCP protocol server
├── openclaw_trigger.py  # OpenClaw CLI trigger
├── gui/                 # GUI module
├── utils/               # Utilities
│   ├── logger.py
│   └── subtitle_extractor.py
├── tests/               # Test suite
├── docs/                # Documentation
└── data/                # Runtime data (not committed)
```

## API Documentation

See [docs/API.md](docs/API.md)

## Testing

```bash
python -m pytest tests/ -v
```

## Build Executable

```bash
pyinstaller bilibili_ai_client.spec
```

## Download exe (no install required)

Download the packaged Windows executable directly from GitHub Releases:

📦 **Download**: [BilibiliAIClient-win.zip](https://github.com/wsererer/bilibili-ai-client-gui/releases/latest)

Extract and run `BilibiliAIClient.exe` directly, no Python environment required.

## License

MIT License - See [LICENSE](LICENSE)

## Disclaimer

This project is for educational and research purposes only. Please do not use it for commercial purposes. When using this project, please comply with Bilibili's Terms of Service.
