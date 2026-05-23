# Vibe Coding Prompt — Bilibili AI Client 全面测试

## 项目概述

**项目名称**：Bilibili AI Client — 测试驱动重构

**仓库路径**：`M:\bilibili第三方ai客户端+自动回复ai\bilibili-ai-client-gui`

**当前状态**：
- 基础功能已实现（消息轮询、字幕提取、OpenClaw 摘要、Webhook、MCP 协议）
- **21 个 Bug 已全部修复**（详见 `docs/bug-list.md`）
- 现有测试 **174 个**，其中 **162 个通过**，13 个网络测试默认跳过
- 已配置完整的 `pyproject.toml`（pytest / mypy / ruff）
- ruff：**0 errors** ✅

**最终目标**：已完成 — 所有代码通过 pytest 测试和 ruff lint。

---

## 开发规范

### 代码质量门禁（必须全部通过）

```bash
# 1. 运行所有非网络测试
pytest tests/ -m "not network" -v

# 2. Lint
ruff check .

# 3. 类型检查（不阻塞）
mypy . --ignore-missing-imports
```

### 测试编写规范

1. **测试文件**：`tests/test_<模块名>.py`
2. **测试类**：`Test<模块名>`（大驼峰）
3. **测试函数**：`test_<功能>_<场景>`（小写 + 下划线）
4. **数据库测试**：使用 `tmp_path` fixture 创建临时数据库，不污染开发数据
5. **网络依赖测试**：标记 `@pytest.mark.network`，默认跳过
6. **GUI 测试**：不创建真实 `tk.Tk` 实例，只测数据处理逻辑
7. **Mock 策略**：`monkeypatch` / `pytest-mock` 模拟 httpx/subprocess，不调用真实外部服务
8. **fixture**：测试专用的 fixture 放在 `tests/conftest.py` 中

### 代码修改规范

1. **不改变已有功能的逻辑**（除非修复 Bug）
2. **所有新代码必须包含类型注解**
3. **异常处理使用具体异常类型，不裸用 `except Exception`**
4. **无调试打印语句、无 `# type: ignore`（除非绝对必要）**

---

## 模块划分与子 Agent 分配

根据源代码实际依赖关系，按以下顺序分 **13 个子 Agent** 执行。

### Phase 1：基础设施（Agent-01）✅

**负责文件**：
- `pyproject.toml`（新创建）
- `tests/__init__.py`（新创建）
- `tests/conftest.py`（修改）

**任务清单**：
- [x] 创建 `pyproject.toml`，配置 pytest（asyncio_mode=auto）、mypy（中等严格）、ruff（默认规则）
- [x] 创建 `tests/__init__.py`
- [x] 修改 `conftest.py`：修复 B-17, B-21

**验证**：`pytest tests/ -v` 正常发现测试

---

### Phase 2：修复损坏测试（Agent-02）✅

**负责文件**：
- `tests/test_webhook_server.py`

**任务清单**：
- [x] 修复 B-16：调用真实的 `_on_webhook` 方法
- [x] 修复 B-20：验证 `server.runner` 和 `server.site`

**验证**：`pytest tests/test_webhook_server.py -v` 全部通过

---

### Phase 3：config 模块测试（Agent-03）✅

**负责文件**：
- `tests/test_config.py`

**任务清单**：
- [x] `test_set_persists_to_file`
- [x] `test_cookie_load_from_file`
- [x] `test_language_property`
- [x] `test_openclaw_path_property`
- [x] `test_window_geometry_property`
- [x] `test_save_creates_file`
- [x] `test_corrupted_file_fallback`

**验证**：`pytest tests/test_config.py -v` 全部通过

---

### Phase 4：database 模块测试（Agent-04）✅

**负责文件**：
- `tests/test_database.py`

**任务清单**：
- [x] `test_get_whitelist`
- [x] `test_is_whitelist_false`
- [x] `test_get_not_whitelisted_messages`
- [x] `test_add_message_duplicate`
- [x] `test_get_message`
- [x] `test_get_messages`
- [x] `test_get_messages_by_bv_id` + 状态筛选
- [x] `test_save_get_login_state`
- [x] `test_clear_login_state`

**验证**：`pytest tests/test_database.py -v` 全部通过

---

### Phase 5：app_data + logger 模块测试（Agent-05）✅

**负责文件**：
- `tests/test_app_data.py`（新创建）
- `tests/test_logger.py`（新创建）

**任务清单**：
- [x] `test_app_data.py`：路径正确性、目录创建、一致性
- [x] `test_logger.py`：初始化幂等性、handler、级别

**验证**：`pytest tests/test_app_data.py tests/test_logger.py -v` 通过

---

### Phase 6：message_poller 模块测试（Agent-06）✅

**负责文件**：
- `tests/test_message_poller.py`

**任务清单**：
- [x] `test_double_start`
- [x] `test_empty_callback`
- [x] `test_run_sync_poll_calls_api`
- [x] `test_run_sync_poll_parses_at_response`
- [x] `test_run_sync_poll_parses_dynamic_response`
- [x] `test_run_sync_poll_dedup`
- [x] `test_run_sync_poll_invalid_cookie`
- [x] `test_run_sync_poll_callback_invoked`

**验证**：`pytest tests/test_message_poller.py -v` 全部通过

---

### Phase 7：mcp_server 模块测试（Agent-07）✅

**负责文件**：
- `tests/test_mcp_server.py`

**任务清单**：
- [x] `test_get_stats`
- [x] `test_ack_message`
- [x] `test_get_pending_messages`
- [x] `test_add_summary`
- [x] `test_get_summary_history`
- [x] `test_unknown_tool`

**验证**：`pytest tests/test_mcp_server.py -v` 全部通过

---

### Phase 8：openclaw_trigger 模块测试（Agent-08）✅

**负责文件**：
- `tests/test_openclaw_trigger.py`

**任务清单**：
- [x] `test_extract_summary_from_json`
- [x] `test_extract_summary_from_plaintext`
- [x] `test_extract_summary_empty_output`
- [x] `test_try_read_summary_file_exists`
- [x] `test_try_read_summary_file_not_found`
- [x] `test_trigger_timeout`
- [x] `test_notify_callback`

**验证**：`pytest tests/test_openclaw_trigger.py -v` 全部通过

---

### Phase 9：webhook_server 模块测试（Agent-09）✅

**负责文件**：
- `tests/test_webhook_server.py`

**任务清单**：
- [x] `test_on_webhook_callback_invoked`
- [x] `test_on_webhook_missing_fields`
- [x] `test_set_callback`
- [x] `test_double_start` / `test_double_stop`
- [x] `test_run_callback_sync` / `test_run_callback_async`

**验证**：`pytest tests/test_webhook_server.py -v` 全部通过

---

### Phase 10：subtitle_extractor 模块测试（Agent-10）✅

**负责文件**：
- `tests/test_subtitle_extractor.py`

**任务清单**：
- [x] `test_clean_transcript_removes_html`
- [x] `test_clean_transcript_empty`
- [x] `test_subtitle_file_to_text_srt/vtt/json`
- [x] `test_choose_best_file_empty`
- [x] `test_parse_json_subtitle_invalid`
- [x] `test_subtitle_file_to_text_unsupported`
- [x] `test_clean_transcript_consecutive_empty_lines`

**验证**：`pytest tests/test_subtitle_extractor.py -v` 全部通过

---

### Phase 11：GUI 模块测试（Agent-11）✅

**负责文件**：
- `tests/test_gui.py`（新创建）

**策略**：不创建真实 tkinter 窗口，只测试数据处理逻辑。

**任务清单**：
- [x] `test_add_whitelist_integration`
- [x] `test_remove_whitelist_empty_selection`
- [x] `test_refresh_messages`
- [x] `test_refresh_whitelist`
- [x] `test_save_settings`
- [x] `test_clear_cookie`
- [x] `test_set_status`
- [x] `test_on_close_saves_geometry`
- [x] `test_show_cookie_input_save_placeholder`
- [x] `test_show_cookie_input_save_valid`

**验证**：`pytest tests/test_gui.py -v` 全部通过

---

### Phase 12：bilibili_login 模块测试（Agent-12）✅

**负责文件**：
- `tests/test_bilibili_login.py`（新创建）

**策略**：mock httpx，不启动真实 Flask 服务器。

**任务清单**：
- [x] `test_generate_qrcode_success`
- [x] `test_generate_qrcode_api_failure`
- [x] `test_generate_qrcode_exception`
- [x] `test_poll_login_waiting`
- [x] `test_poll_login_confirmed`
- [x] `test_poll_login_expired`
- [x] `test_poll_login_extract_cookie_from_url`
- [x] `test_save_cookie`
- [x] `test_save_cookie_no_cookie`
- [x] `test_run_login_server`

**验证**：`pytest tests/test_bilibili_login.py -v` 全部通过

---

### Phase 13：main 模块测试 + 集成测试（Agent-13）✅

**负责文件**：
- `tests/test_main.py`（新创建）

**任务清单**：
- [x] `test_process_new_message_no_bv_id`
- [x] `test_process_new_message_no_sender`
- [x] `test_process_new_message_duplicate`
- [x] `test_process_new_message_subtitle_fail`
- [x] `test_on_openclaw_complete_success`
- [x] `test_on_openclaw_complete_failure`
- [x] `test_reprocess_blocked_messages`
- [x] `test_parse_args_defaults`

**验证**：`pytest tests/test_main.py -v` 全部通过

---

## 执行流程

所有 13 个 Phase 已完成。

---

## 质量门禁命令（汇总）

```bash
# ========== 测试 ==========
pytest tests/ -m "not network" -v
# 预期：162 passed, 13 deselected

# ========== Lint ==========
ruff check .
# 预期：All checks passed!

# ========== 类型检查（不阻塞）==========
mypy . --ignore-missing-imports
```

---

## 已知破测试（已修复）

| 文件 | 问题 | 状态 |
|------|------|------|
| `tests/test_webhook_server.py` | `_normalize_message()` 不存在 | ✅ 已修复 |
| `tests/test_webhook_server.py` | `server.server` 断言不对 | ✅ 已修复 |
| `tests/conftest.py` | `database.conn` 不存在 | ✅ 已修复 |

完整列表见 `docs/bug-list.md`（B-01 ~ B-21，全部已修复 ✅）。

---

## 注意事项

1. ✅ **所有 Bug 已修复**
2. ✅ **162 个测试全部通过**
3. ✅ **ruff 0 errors**
4. ✅ **pyproject.toml 已配置**
