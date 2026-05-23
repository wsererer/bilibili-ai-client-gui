# Bilibili AI Client GUI

B站 AI 客户端 - 自动获取视频字幕并通过 OpenClaw 生成摘要

[English](README_EN.md) | 中文

## 功能特性

- 📝 **字幕提取**: B站 API > yt-dlp > Whisper 本地模型（内置）
- 🔐 **QR码登录**: 支持 B站 QR码登录，Cookie 加密存储（XOR + Base64）
- 📋 **白名单过滤**: 仅处理白名单用户的@消息
- 🖥️ **图形界面**: tkinter 现代化 GUI（含滚动设置页面）
- 💬 **MCP 协议**: 6 个工具接口，支持 AI Agent 调用
- 🔗 **OpenClaw 集成**: 触发 OpenClaw 生成视频摘要（文件传参法，避免 cmd.exe 参数损坏）
- 📊 **消息轮询**: 自动监听@消息和动态
- 🔄 **失败重试**: GUI 和 API 双通道支持重试失败任务
- 📡 **Webhook**: 支持外部系统（如 n8n）回调触发
- 📤 **自动推送**: 摘要生成后自动通过微信/飞书推送，支持目标账号配置

## 核心流程

```
B站@消息/动态 ──轮询──▶ 字幕提取 ──触发──▶ OpenClaw ──▶ 摘要存库
                                                    │
Webhook ◀──外部系统（n8n等）────────────────────────┘
```

## 系统要求

- Python 3.10+
- Windows/Linux/macOS
- [OpenClaw](https://openclaw.ai)（可选，用于 AI 生成摘要）

## 安装与设置

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

### 4. 获取 Whisper 模型

```bash
# 方式一：从 bilibili-ai-client 复制 whisper_model 文件夹
# 方式二：下载模型
python download_model.py
```

### 5. 首次运行配置

启动 GUI：

```bash
python main.py --mode gui
```

打开 **设置** 面板，按以下步骤配置：

#### 5.1 添加白名单
只有白名单用户的 @消息才会被处理。在设置页面的"白名单"区域：
- 输入你的 B站 UID（数字）
- 点击"添加"
- （测试时可先添加 `17709654`）

#### 5.2 登录 B站
- **方式一（推荐）**：点击"网页登录" → 浏览器打开二维码 → 用 B站 App 扫码 → 自动保存 Cookie
- **方式二**：点击"手动输入 Cookie" → 在浏览器 F12 → Application → Cookies → 复制 `SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx` → 粘贴到输入框

登录成功后消息轮询自动开始。

#### 5.3 配置 OpenClaw 路径
如果安装了 OpenClaw：
- 在设置页面的"OpenClaw 路径"输入框填写路径
- 默认：`openclaw`（已加入 PATH 时）
- Windows 常见路径：`C:\Users\xxx\AppData\Roaming\npm\openclaw.cmd`
- 远程部署：确保 OpenClaw 在本机可执行

#### 5.4 配置自动推送（可选）
摘要生成后自动推送到微信或飞书：

1. 勾选"启用摘要自动推送"
2. 选择推送渠道：微信 / 飞书 / 两者
3. 填写目标账号：
   - **微信目标账号**：从 OpenClaw 获取你的 chat_id（格式如 `wx_xxxx@im.wechat`）
   - **飞书目标账号**：你的飞书用户 ID
4. 点击"保存设置"

> 目标账号为空时，OpenClaw 不会附加目标参数，推送可能失败。

### 6. 运行

```bash
# GUI 模式（推荐）
python main.py --mode gui

# MCP 模式（供 AI Agent 调用）
python main.py --mode mcp

# Webhook 接收模式
python main.py --mode webhook

# 所有模式
python main.py --mode all
```

## Cookie 加密

Cookie 使用 XOR + Base64 加密存储在 `data/config.json`，密钥在 `data/.key`。GUI 中仅显示"已登录（加密存储）"，不暴露明文。

## 消息状态

| 状态 | 说明 |
|------|------|
| `pending` | 等待处理 |
| `not_whitelisted` | 用户不在白名单 |
| `no_sender_uid` | 无发送者 UID |
| `triggered` | 已触发 OpenClaw |
| `processed` | 处理完成 |
| `failed` | 处理失败（可重试） |
| `openclaw_failed` | OpenClaw 执行失败（可重试） |
| `no_subtitle` | 无法获取字幕 |

## MCP API（6 个工具）

| 工具 | 说明 |
|------|------|
| get_pending_messages | 获取待处理消息 |
| get_stats | 获取统计信息 |
| ack_message | 确认消息状态 |
| add_summary | 添加摘要记录 |
| get_summary_history | 获取摘要历史 |
| (未知工具) | 返回 error 信息 |

## 项目结构

```
bilibili-ai-client-gui/
├── main.py              # 程序入口
├── config.py            # 配置管理（含加密）
├── database.py          # SQLite 数据库
├── bilibili_login.py    # QR码登录服务
├── message_poller.py    # B站消息轮询
├── webhook_server.py    # Webhook 接收服务
├── mcp_server.py        # MCP 协议服务（6个工具）
├── openclaw_trigger.py  # OpenClaw 触发器（文件传参法）
├── gui/                 # tkinter GUI
│   └── main_window.py   # 主窗口（含重试按钮）
├── utils/
│   ├── logger.py
│   ├── crypto.py        # 加密工具
│   └── subtitle_extractor.py
├── whisper_model/      # Whisper 模型（需复制或下载）
├── tests/               # 完整测试套件（170个通过）
├── docs/                # 文档
│   ├── PROGRESS.md      # 进度跟踪
│   └── API.md           # API 文档
└── pyproject.toml       # 项目配置（pytest/mypy/ruff）
```

## 测试

```bash
# 运行全部非网络测试
python -m pytest tests/ -m "not network" -v

# 运行指定模块测试
python -m pytest tests/test_database.py -v

# Lint 检查
ruff check .

# 全部测试（含网络）
python -m pytest tests/ -v
```

**测试结果**：170 passed，13 个网络测试默认跳过，ruff 0 errors。

## 构建发布包

```bash
pyinstaller bilibili_ai_client_gui.spec --clean --noconfirm
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 免责声明

本项目仅供学习研究使用，请勿用于任何商业用途。使用本项目时，请遵守 B站 的服务条款。
