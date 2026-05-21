# Bilibili AI Client GUI

B站 AI 客户端 - 自动获取字幕并 AI 回复 Bilibili 动态/评论

[English](README_EN.md) | 中文

## 功能特性

- 🤖 **AI 自动回复**: 自动回复 B站 动态和评论
- 📝 **智能字幕提取**: B站 API > yt-dlp > Whisper 多优先级链
- 🔐 **QR码登录**: 支持 Cookie 认证，自动持久化
- 📋 **白名单管理**: 仅处理白名单用户的评论，添加白名单后自动重新识别被拦截消息
- 🖥️ **图形界面**: PyQt6 现代化 GUI
- 💬 **MCP 协议**: 通过 Model Context Protocol 与 AI Agent 通信
- 🔗 **OpenClaw 集成**: 通过 CLI 命令触发 OpenClaw 处理视频

## 系统要求

- Python 3.10+
- Windows/Linux/macOS
- [OpenClaw](https://openclaw.ai)（可选，用于 AI 处理视频）

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/wsererer/bilibili-ai-client-gui.git
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

### 4. 下载 Whisper 模型（可选）

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

# Webhook 接收模式 (接收外部消息)
python main.py --mode webhook

# 所有模式
python main.py --mode all
```

## OpenClaw 集成

软件通过 CLI 命令调用 OpenClaw 处理视频：

```bash
openclaw agent --message "处理视频任务..."
```

### 配置 OpenClaw 路径

在 GUI 设置中可以自定义 OpenClaw 可执行文件路径（默认: `openclaw`）。

如果 `openclaw` 不在系统 PATH 中，可以指定完整路径：
```
C:\Users\你的用户名\AppData\Roaming\npm\openclaw.cmd
```

## 白名单机制

- 只有白名单用户的评论会被处理
- 未白名单用户的评论会被记录为 `not_whitelisted` 状态
- 添加新用户到白名单后，会自动重新处理该用户之前被拦截的评论

## 项目结构

```
bilibili-ai-client-gui/
├── main.py              # 程序入口
├── config.py            # 配置管理
├── database.py          # 数据库模块
├── bilibili_login.py    # QR码登录
├── message_poller.py    # 消息轮询
├── webhook_server.py    # Webhook接收服务器
├── mcp_server.py        # MCP协议服务器
├── openclaw_trigger.py  # OpenClaw CLI触发器
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

## 下载 exe (免安装)

直接从 GitHub Releases 下载打包好的 Windows 可执行文件：

📦 **下载链接**: [BilibiliAIClient-win.zip](https://github.com/wsererer/bilibili-ai-client-gui/releases/latest)

解压后直接运行 `BilibiliAIClient.exe` 即可，无需安装 Python 环境。

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 免责声明

本项目仅供学习研究使用，请勿用于任何商业用途。使用本项目时，请遵守 B站 的服务条款。
