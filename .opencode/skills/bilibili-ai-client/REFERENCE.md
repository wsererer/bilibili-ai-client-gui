# Bilibili AI Client — 参考文档

## 首次设置流程

1. **安装依赖**：`pip install -r requirements.txt` + whisper model
2. **启动 GUI**：`python main.py --mode gui`
3. **白名单**：设置 → 白名单 → 添加 B站 UID（否则 @消息被忽略）
4. **B站 Cookie**：网页登录扫码 或 手动粘贴 Cookie
5. **OpenClaw 路径**：填写 openclaw 可执行文件路径
6. **自动推送**（可选）：启用 → 选渠道 → 填目标账号 → 保存
7. **等待消息**：轮询自动开始，收到 @消息后依次：字幕提取 → OpenClaw → 推送

## MCP 工具接口

`mcp_server.py` 当前 6 个工具，通过 `server.list_tools()` 注册：

| Tool | Function | Input |
|------|----------|-------|
| get_pending_messages | `call_tool("get_pending_messages", {})` | {} |
| get_stats | `call_tool("get_stats", {})` | {} |
| ack_message | `call_tool("ack_message", {"msg_id","status"})` | status: processed/failed |
| add_summary | `call_tool("add_summary", {"bv_id","sender_uid","sender_name","subtitle_text","summary_text"})` | — |
| get_summary_history | `call_tool("get_summary_history", {"limit"})` | limit: int (default 50) |
| (未知) | 自动返回 `{"error":"未知工具"}` | — |

返回值格式：`List[TextContent]`，text 为 JSON 字符串。

添加新工具步骤：
1. 在 `list_tools()` 返回值中添加 `Tool(...)` 描述
2. 在 `call_tool()` 中添加 `if name == "new_tool":` 分支
3. 测试：`tests/test_mcp_server.py` 添加 `@pytest.mark.asyncio async def test_...`

## 消息状态机

```
pending → triggered → processed
    ↓          ↓
    ├→ no_subtitle      └→ openclaw_failed
    ├→ no_sender_uid            ↓
    └→ not_whitelisted    reprocess_blocked → pending
```

`main.py:process_new_message()` 实现状态流转。

## Webhook 消息格式

```json
{
  "type": "dynamic|live_dm|(passthrough)",
  "id": "msg_id",
  "bv_id": "BV1xxx",
  "uid": "sender_uid",
  "uname": "sender_name",
  "content": "text"
}
```

POST `http://localhost:18792/webhook`

## OpenClaw Trigger 工作流

```
main.py:process_new_message(bv_id 存在)
  → subtitle_extractor.extract(url) → ExtractResult
  → openclaw_trigger.trigger(bv_id, subtitle_text, sender_uid, sender_name)
    → _save_subtitle_to_temp() → tempfile.mkstemp() → .txt 文件
    → _build_message() → 单行管道格式 @--message + 文件路径 @--message
      → auto_send=true 时追加发送指令及目标账号（wechat_target/feishu_target）
    → subprocess.run(["openclaw", "agent", "--message", "...", "--agent", "main", "--json"])
      （注意：--deliver 已移除；字幕不在 --message 中，在临时文件中）
    → _cleanup_temp_files() → 删除临时 .txt 文件
    → 解析 stdout JSON 获取 summary
      → 失败时 fallback: try_read_summary_file()
    → success → callback(bv_id, summary) → database.add_summary()
    → failure → callback(bv_id, None) → status=openclaw_failed
```

**B-22 根因**: Windows `cmd.exe` 在通过 `.cmd` 批处理包装器传递含换行符的长参数时静默损坏。
**修复**: 字幕文本写入临时文件，`--message` 中只传文件路径，Agent 用 `read` 工具读取文件内容。

### Auto-Send 推送（B-23）

当 `auto_send=true` 时，`_build_message()` 从 config 读取 `wechat_target`/`feishu_target` 拼入提示词：
- 微信：`...通过微信发送摘要给用户，目标账号: {wechat_target}`
- 飞书：`...通过飞书发送摘要给用户，目标账号: {feishu_target}`
- 双渠道：`...通过微信和飞书发送摘要给用户，微信目标账号: {w}，飞书目标账号: {f}`
- 目标为空时不附加 `，目标账号:` 部分

### Cookie 登录改进（B-24, B-25）

- `check_login()` 改为直接检查 `config.get("bili_auth")` 单例（不再轮询文件）
- `_clear_cookie()` 同时删除 `login_cookie.txt`

## 完整文件清单

```
bilibili-ai-client-gui/
├── main.py              # 入口
├── config.py            # 配置单例
├── database.py          # SQLite 操作
├── bilibili_login.py    # QR 扫码登录
├── message_poller.py    # 消息轮询 + LRU 去重
├── webhook_server.py    # Flask webhook
├── mcp_server.py        # MCP 协议（6工具）
├── openclaw_trigger.py  # OpenClaw 触发
├── gui/
│   └── main_window.py   # tkinter 主窗口
├── utils/
│   ├── app_data.py      # PyInstaller 兼容路径
│   ├── crypto.py        # XOR+Base64 加密
│   ├── logger.py        # loguru 日志
│   └── subtitle_extractor.py  # 字幕链
├── tests/               # 170个测试
│   ├── conftest.py
│   ├── test_*.py        # 14个测试文件
│   └── __init__.py
├── docs/                # 文档
├── whisper_model/       # Whisper 模型文件
├── data/                # 运行时数据（gitignored）
│   ├── config.json
│   ├── login_cookie.txt
│   ├── .key
│   └── bilibili_client.db
├── pyproject.toml       # pytest/mypy/ruff 配置
└── bilibili_ai_client_gui.spec  # PyInstaller spec
```
