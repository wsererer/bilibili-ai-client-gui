---
name: bilibili-ai-client
description: Navigate Bilibili AI Client GUI project — architecture, commands, testing, OpenClaw integration, bundling. Use when working on this B站 auto-reply / summary generation project, or when user mentions bilibili, OpenClaw, subtitle extraction, MCP tools, webhook, or PyInstaller for this codebase.
---

# Bilibili AI Client GUI

## Project Overview

B站 AI 客户端 — 自动轮询@消息和动态，提取视频字幕，通过 OpenClaw 生成摘要。

**Language**: Python 3.10+  
**GUI**: tkinter  
**Build**: PyInstaller  
**Test**: pytest + ruff  

## Architecture

```
B站@消息/动态 → message_poller → main.process_new_message
                                        ↓
                            subtitle_extractor → B站 API / yt-dlp / Whisper
                                        ↓
                            openclaw_trigger → OpenClaw agent → 摘要存库

webhook_server ← 外部系统 (n8n等)
mcp_server    ← AI Agent (6 tools)
bilibili_login ← QR码登录
```

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point, `--mode gui/mcp/webhook/all` |
| `message_poller.py` | Polls B站 @消息 + 动态，LRU 去重 |
| `openclaw_trigger.py` | Triggers OpenClaw with `--agent main --json`, auto_send with target account |
| `mcp_server.py` | 6 MCP tools (get_pending_messages, get_stats, ack_message, add_summary, get_summary_history, unknown→error) |
| `webhook_server.py` | Flask webhook receiver on port 18792 |
| `config.py` | Singleton config, XOR+Base64 encrypted cookie |
| `database.py` | SQLite (whitelist, messages, summaries, stats, login_state) |
| `gui/main_window.py` | tkinter main window |
| `bilibili_login.py` | QR code login → encrypt cookie |
| `utils/subtitle_extractor.py` | Subtitle chain: B站 API > yt-dlp > Whisper |
| `utils/crypto.py` | XOR + Base64 encryption/decryption |
| `utils/logger.py` | loguru logger, file rotation 10MB |

## Essential Commands

```bash
# Run
python main.py --mode gui          # GUI mode (default)
python main.py --mode mcp           # MCP server (stdin/stdout)
python main.py --mode webhook       # Webhook receiver
python main.py --mode all           # GUI + webhook + poller

# Test (network tests skipped by default)
python -m pytest tests/ -m "not network" -v
python -m pytest tests/test_database.py -v   # single module

# Lint
ruff check .
ruff check --fix .                  # auto-fix

# Build
pyinstaller bilibili_ai_client_gui.spec --clean --noconfirm
# Output: dist/BilibiliAIClient.exe
```

## Setup Guide

### 1. 依赖安装
```bash
pip install -r requirements.txt
```
Whisper 模型：复制或运行 `python download_model.py`

### 2. 白名单设置
GUI 设置 → 白名单 → 添加 B站 UID。只有白名单用户的 @消息会被处理。

### 3. B站 Cookie 登录
- **QR 码登录**：点击"网页登录" → 浏览器扫码
- **手动输入**：F12 → Application → Cookies → 复制 `SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx`

### 4. OpenClaw 路径
设置 → "OpenClaw 路径" → 填入可执行文件路径（默认 `openclaw`）

### 5. 自动推送（可选）
勾选"启用摘要自动推送" → 选择渠道 → 填写微信/飞书目标账号 → 保存

## OpenClaw Integration

### File-Based Approach (B-22 修复)

`openclaw_trigger.py` 使用**文件传参法**避免 Windows `cmd.exe` 的已知 bug：

```
字幕文本 → tempfile.mkstemp() → 临时 .txt 文件
→ --message 中仅传文件路径 + read 工具指令
→ Agent 用 read 工具读取文件内容
```

命令格式 (`openclaw_trigger.py:72`):
```
openclaw agent --message "处理视频任务 | BV号: {bv_id} | 发送者UID: {uid} | 请使用 read 工具读取字幕文件... | 字幕文件路径: {tmp_path} | ... | 【重要】处理完成后，通过微信发送摘要给用户，目标账号: {target}" --agent main --json
```

关键点：
- `--agent main` **必须**（不能用 `--local`）
- `--message` 为**单行管道格式**（不含换行符）
- `--deliver` 已移除（无 MCP 目标时返回 RC=1）
- 长字幕文本写入临时文件，不嵌入命令行
- Agent 回执解析失败时 fallback: `try_read_summary_file()`

### Auto-Send 推送

当 `auto_send=true` 时，`_build_message()` 从 config 读取 `wechat_target`/`feishu_target` 拼入提示词：

| send_channel | 示例指令 |
|-------------|---------|
| `wechat` | `【重要】处理完成后，通过微信发送摘要给用户，目标账号: {wechat_target}` |
| `feishu` | `【重要】处理完成后，通过飞书发送摘要给用户，目标账号: {feishu_target}` |
| `both` | `【重要】处理完成后，通过微信和飞书发送摘要给用户，微信目标账号: {w}，飞书目标账号: {f}` |

目标账号为空时不附加 `，目标账号:`，避免 OpenClaw 报 Unknown target 错误。

## Testing Conventions

- 170 non-network tests pass, 13 `@pytest.mark.network` (skipped by default)
- Database tests use `tmp_path` + `db_with_temp` fixture
- Network-dependent tests marked `@pytest.mark.network`
- GUI tests mock tkinter, only test data logic
- Config in `pyproject.toml`: asyncio_mode=auto, ruff line-length=120

## Sensitive Data (DO NOT COMMIT)

- `data/config.json` — 加密 cookie 配置
- `data/login_cookie.txt` — Cookie 明文
- `data/.key` — 加密密钥
- `data/bilibili_client.db` — SQLite 数据库（含消息记录）
- 以上均在 `.gitignore` 中

## Security Rules

- Cookie 不得写入日志（已修复 B-08, B-09）
- GUI 中 Cookie 显示为 `********`（已修复 B-10）
- Cookie 使用 XOR+Base64 加密存储
- Whisper model (~3.7GB) 不提交 git

## Bug Fix History

全部 26 个已知 Bug 已修复（B-01 ~ B-26），详见 `docs/bug-list.md`。

### 近期修复

| Bug | 描述 | 文件 |
|-----|------|------|
| B-23 | 推送指令缺少目标账号，OpenClaw 报 Unknown target | `openclaw_trigger.py:55-64` |
| B-24 | check_login() 轮询文件不可靠，QR 登录后 cookie 未保存 | `gui/main_window.py:526-544` |
| B-25 | _clear_cookie() 不清除 login_cookie.txt | `gui/main_window.py:599-605` |
| B-26 | ext 提取逻辑取域名后半段作扩展名，生成非法文件路径导致字幕下载失败 | `utils/subtitle_extractor.py:325` |
