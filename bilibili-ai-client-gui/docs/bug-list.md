# Bug 清单

## 已修复 Bug

| ID | 描述 | 位置 | 严重性 | 状态 |
|----|------|------|--------|------|
| B-01 | `database.py` 缺少 `get_failed_messages()` 和 `reset_message_status()`，GUI 和测试调用时抛 `AttributeError` | `database.py` | 严重 | ✅ 已修复 |
| B-02 | `test_integration.py` 用 `await` 调用同步函数 `process_new_message` | `tests/test_integration.py:27,44` | 严重 | ✅ 已修复 |
| B-03 | `test_openclaw_trigger.py` 断言命令行含 `--session-id` 和 `bilibili-BV1xxx`，实际代码没有该参数 | `tests/test_openclaw_trigger.py:36,102` | 严重 | ✅ 已修复 |
| B-04 | `test_message_poller.py` 调用 `_notify_callbacks`、`_calculate_delay`、`getdynamic`、`get_mentions`、`max_delay` 等不存在的方法/属性 | `tests/test_message_poller.py:48,59,63,75,81,89` | 严重 | ✅ 已修复 |
| B-05 | `test_mcp_server.py` 断言 17 个工具、断言不存在的工具名 (add_whitelist 等) | `tests/test_mcp_server.py:15-37` | 严重 | ✅ 已修复 |
| B-06 | `_fetch_subtitles_from_bilibili_api()` 中 `best_sub` 变量在特定分支可能未定义 | `utils/subtitle_extractor.py:312-329` | 中 | ✅ 已修复 |
| B-07 | `requirements.txt` 列出 `PyQt6>=6.6.0`，实际 GUI 用 tkinter，PyQt6 完全未使用 | `requirements.txt:5` | 低 | ✅ 已修复 |
| B-08 | Cookie 前 30 字符写入日志 (`auto_start is True, config.bili_auth: ...`) | `main.py:153` | 严重 | ✅ 已修复 |
| B-09 | Cookie 前 50 字符写入日志 (`Extracted cookie: ...`) | `bilibili_login.py:228` | 严重 | ✅ 已修复 |
| B-10 | Cookie 明文显示在 GUI 手动输入框 (`_show_cookie_input`) | `gui/main_window.py:589-591` | 高 | ✅ 已修复 |
| B-11 | `processed_ids` 集合无限增长，截断策略 O(n) 拷贝 | `message_poller.py:47,154-155` | 中 | ✅ 已修复（改为 OrderedDict LRU） |
| B-12 | `auth_entry` 创建时 `state="disabled"`，未改成 normal 就直接 `insert()` 抛 TclError | `gui/main_window.py:230,233-234` | 严重 | ✅ 已修复 |
| B-13 | `_process_message` 中 `loop.call_soon_threadsafe()` 回调永不执行（asyncio 循环未启动就 `close()`） | `gui/main_window.py:394-422` | 严重 | ✅ 已修复（改用 `root.after`） |
| B-14 | `_reprocess_blocked` 用 `loop.run_until_complete()` 包装同步函数 `reprocess_blocked_messages`，抛 `TypeError` | `gui/main_window.py:374` | 严重 | ✅ 已修复 |
| B-15 | `_show_cookie_input` 中用户不修改直接点保存，"********" 占位符被当真写入配置 | `gui/main_window.py:593` | 中 | ✅ 已修复 |
| B-16 | `test_webhook_server.py` 中 `TestWebhookMessageNormalization` 三个测试调用 `receiver._normalize_message()`，但 `WebhookReceiver` 类不存在该方法 | `tests/test_webhook_server.py:10-42` | 严重 | ✅ 已修复 |
| B-17 | `conftest.py` 中 `reset_singleton` autouse fixture 引用 `database.conn` 和 `database._db_path`，但 `Database` 类没有这两个属性 | `tests/conftest.py:76-81` | 低 | ✅ 已修复 |
| B-18 | 项目无 `pyproject.toml` / `mypy.ini` / `.ruff.toml` | 项目根目录 | 中 | ✅ 已修复 |
| B-19 | 无 `tests/__init__.py`，测试目录不是 Python 包 | `tests/` | 低 | ✅ 已修复 |
| B-20 | `test_server_start_stop` 的 `assert server.server is None` 与实现不符 | `tests/test_webhook_server.py:56,58` | 中 | ✅ 已修复 |
| B-21 | `conftest.py` 中 `temp_db` fixture 使用硬编码路径而非导入 `DB_FILE` | `tests/conftest.py:15` | 低 | ✅ 已修复 |
| B-22 | Windows `cmd.exe` 通过 `.cmd` 批处理文件传递含换行符的长参数时静默损坏参数，导致 OpenClaw "Gateway agent failed" 错误 | `openclaw_trigger.py` | 严重 | ✅ 已修复（文件传参法） |

## 统计

| 状态 | 数量 |
|------|------|
| 已修复 | 22 |
| 未修复 | 0 |
| 合计 | 22 |
