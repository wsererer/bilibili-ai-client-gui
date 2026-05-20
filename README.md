# Bilibili AI Client GUI

B站 AI 客户端 - 自动获取字幕并 AI 回复 Bilibili 动态/评论

[English](README_EN.md) | 中文

## 功能特性

- 🤖 **AI 自动回复**: 自动回复 B站 动态和评论
- 📝 **智能字幕提取**: 支持 B站字幕 > AI字幕 > yt-dlp > Whisper 多优先级链
- 💬 **MCP 协议支持**: 通过 Model Context Protocol 与 AI Agent 通信
- 🖥️ **图形界面**: PyQt6 现代化 GUI
- 🔐 **安全登录**: QR码登录，支持 Cookie 认证

## 系统要求

- Python 3.10+
- Windows/Linux/macOS

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/your-repo/bilibili-ai-client-gui.git
cd bilibili-ai-client-gui
```

### 2. 创建虚拟环境

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 下载 Whisper 模型

```bash
python download_model.py
```

### 5. 配置

创建 `data/` 目录，并添加以下文件：

**`data/login_cookie.txt`** - B站登录Cookie:
```
SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx
```

获取方式:
1. 登录 [bilibili.com](https://bilibili.com)
2. F12 打开开发者工具 → Application → Cookies
3. 复制 SESSDATA, bili_jct, DedeUserID 值

### 6. 运行

```bash
# GUI 模式
python main.py --mode gui

# MCP 模式 (供 AI Agent 调用)
python main.py --mode mcp

# Webhook 模式
python main.py --mode webhook

# 所有模式
python main.py --mode all
```

## 项目结构

```
bilibili-ai-client-gui/
├── main.py              # 程序入口
├── config.py            # 配置管理
├── database.py          # 数据库模块
├── bilibili_login.py    # QR码登录
├── message_poller.py    # 消息轮询
├── webhook_server.py    # Webhook服务器
├── mcp_server.py       # MCP协议服务器
├── openclaw_trigger.py  # OpenClaw触发器
├── gui/                 # GUI模块
├── utils/               # 工具模块
│   ├── logger.py
│   └── subtitle_extractor.py
├── tests/               # 测试套件
├── docs/                # 文档
└── data/                # 运行时数据 (不提交)
```

## API 接口

详见 [docs/API.md](docs/API.md)

## 测试

```bash
python -m pytest tests/ -v
```

## 构建发布包

```bash
pyinstaller bilibili_ai_client.spec
```

## 依赖

- PyQt6 >= 6.6.0
- bilibili-api >= 6.4.0
- requests >= 2.31.0
- httpx >= 0.27.0
- mcp >= 0.1.0
- loguru >= 0.7.0
- yt-dlp >= 2024.0.0
- faster-whisper >= 1.0.0

## 下载 exe (免安装)

直接从 GitHub Releases 下载打包好的 Windows 可执行文件：

📦 **下载链接**: [BilibiliAIClient-win.zip](https://github.com/wsererer/bilibili-ai-client-gui/releases/latest)

解压后直接运行 `BilibiliAIClient.exe` 即可，无需安装 Python 环境。

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 免责声明

本项目仅供学习研究使用，请勿用于任何商业用途。使用本项目时，请遵守 B站 的服务条款。