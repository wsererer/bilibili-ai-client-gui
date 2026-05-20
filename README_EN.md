# Bilibili AI Client GUI

Bilibili AI Client - Automatically extract subtitles and AI-reply to Bilibili dynamics/comments

[中文](README.md) | English

## Features

- 🤖 **AI Auto-Reply**: Automatically reply to Bilibili dynamics and comments
- 📝 **Smart Subtitle Extraction**: Multi-priority chain: B站 subtitles > AI subtitles > yt-dlp > Whisper
- 💬 **MCP Protocol Support**: Communicate with AI Agent via Model Context Protocol
- 🖥️ **Graphical Interface**: Modern PyQt6 GUI
- 🔐 **Secure Login**: QR code login with Cookie authentication

## Requirements

- Python 3.10+
- Windows/Linux/macOS

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-repo/bilibili-ai-client-gui.git
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

### 4. Download Whisper model

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

# Webhook mode
python main.py --mode webhook

# All modes
python main.py --mode all
```

## Project Structure

```
bilibili-ai-client-gui/
├── main.py              # Entry point
├── config.py            # Configuration
├── database.py          # Database module
├── bilibili_login.py    # QR code login
├── message_poller.py    # Message polling
├── webhook_server.py   # Webhook server
├── mcp_server.py       # MCP protocol server
├── openclaw_trigger.py # OpenClaw trigger
├── gui/                # GUI module
├── utils/              # Utilities
│   ├── logger.py
│   └── subtitle_extractor.py
├── tests/              # Test suite
├── docs/               # Documentation
└── data/               # Runtime data (not committed)
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

## Dependencies

- PyQt6 >= 6.6.0
- bilibili-api >= 6.4.0
- requests >= 2.31.0
- httpx >= 0.27.0
- mcp >= 0.1.0
- loguru >= 0.7.0
- yt-dlp >= 2024.0.0
- faster-whisper >= 1.0.0

## License

MIT License - See [LICENSE](LICENSE)

## Disclaimer

This project is for educational and research purposes only. Please do not use it for commercial purposes. When using this project, please comply with Bilibili's Terms of Service.