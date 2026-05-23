# Bilibili AI Client — 测试计划

## 1. 测试目标

- 所有模块通过 **pytest** 单元测试
- 全部通过 **ruff** 默认规则 lint
- GUI（tkinter）、Flask 登录等难以完全自动化测试的模块，至少覆盖可独立测试的数据处理逻辑
- 消除全部损坏测试（B-01 ~ B-21）

## 2. 测试层级

### 2.1 单元测试（Unit Tests）

| 模块 | 文件 | 测试重点 | 实际测试数 | 状态 |
|------|------|---------|-----------|------|
| config | `config.py` | 单例、get/set 持久化、load/save、cookie 文件加载、属性访问 | 16 | ✅ |
| database | `database.py` | 所有 CRUD、状态查询、失败消息、login_state、边界条件 | 21 | ✅ |
| crypto | `utils/crypto.py` | 加密解密往返、标记判断、智能加/解密、空值 | 6 | ✅ |
| message_poller | `message_poller.py` | 生命周期、回调管理、指数退避、httpx mock | 15 | ✅ |
| mcp_server | `mcp_server.py` | 6 个工具调用、参数校验、错误处理 | 6 | ✅ |
| openclaw_trigger | `openclaw_trigger.py` | 命令构建、输出解析、文件回退、回调通知、超时 | 12 | ✅ |
| webhook_server | `webhook_server.py` | 消息规范化、服务启停、端点响应、回调分发 | 17 | ✅ |
| subtitle_extractor | `utils/subtitle_extractor.py` | URL 校验、SRT/VTT/JSON 解析、clean_transcript、文件选择 | 25 | ✅ |
| gui | `gui/main_window.py` | 白名单操作、消息刷新、设置保存、Cookie 操作 *（数据方法，不测 tkinter 渲染）* | 10 | ✅ |
| bilibili_login | `bilibili_login.py` | 二维码 URL 生成、poll_login 状态机、cookie 提取保存（mock httpx） | 12 | ✅ |
| main | `main.py` | `process_new_message` 状态机、`reprocess_blocked`、`on_openclaw_complete` | 9 | ✅ |
| app_data | `utils/app_data.py` | 目录发现、目录创建、PyInstaller 路径 | 6 | ✅ |
| logger | `utils/logger.py` | 初始化、幂等性 | 5 | ✅ |

### 2.2 集成测试（Integration Tests）

| 测试场景 | 涉及模块 | 方法 |
|----------|---------|------|
| 轮询→数据库写入全流程 | `message_poller` + `database` | mock httpx 响应 |
| 触发→回调→摘要入库 | `openclaw_trigger` + `main` + `database` | mock subprocess |
| Webhook 接收→消息处理 | `webhook_server` + `main` | mock aiohttp 请求 |
| MCP 工具→数据库读写 | `mcp_server` + `database` | 直接调用 call_tool |

### 2.3 端到端测试（E2E Tests）

| 测试场景 | 条件 |
|----------|------|
| 视频字幕提取（已知 BV 号） | 需要网络 + B站可达（标记 `@pytest.mark.network`） |
| 进程启动模式（--mode all/gui/webhook/mcp） | 超时控制 3s，子进程启停 |
| 端到端消息处理 | 需要网络 |

### 2.4 安全测试

- Cookie 不写入日志 ✅
- Cookie 在 GUI 中以掩码显示（`********`）✅
- 加密密钥存储隔离 ✅

## 3. 测试环境

### 3.1 Python 依赖

```txt
pytest>=7.0.0
pytest-asyncio>=0.21.0
httpx>=0.27.0
aiohttp>=3.9.0
```

### 3.2 测试配置（pyproject.toml）

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "network: tests that require network access",
]

[tool.mypy]
python_version = "3.10"
ignore_missing_imports = true
strict_optional = true
warn_unused_ignores = true

[tool.ruff]
line-length = 120
target-version = "py310"
```

### 3.3 测试数据库策略

- 使用 `pytest` 的 `tmp_path` fixture 创建临时 SQLite 数据库
- 每个测试函数独立数据库文件，互不污染
- `conftest.py` 提供 `db_with_temp` fixture

## 4. 质量门禁

```bash
# 运行全部测试（跳过网络）
pytest tests/ -m "not network" -v

# Lint
ruff check .

# 全部通过才能视为完成 ✅
```

## 5. 模块测试详细规格

### 5.1 config.py — 16 个测试 ✅

| 测试函数 | 状态 |
|---------|------|
| `test_singleton_identity` | ✅ |
| `test_defaults` | ✅ |
| `test_set_and_get` | ✅ |
| `test_nested_dict` | ✅ |
| `test_set_persists_to_file` | ✅ |
| `test_save_creates_file` | ✅ |
| `test_valid_cookie` | ✅ |
| `test_empty_cookie` | ✅ |
| `test_cookie_load_from_file` | ✅ |
| `test_polling_interval` | ✅ |
| `test_auto_start` | ✅ |
| `test_language_property` | ✅ |
| `test_openclaw_path_property` | ✅ |
| `test_window_geometry_property` | ✅ |
| `test_window_geometry_none` | ✅ |
| `test_corrupted_file_fallback` | ✅ |

### 5.2 database.py — 21 个测试 ✅

| 测试函数 | 状态 |
|---------|------|
| `test_get_whitelist` | ✅ |
| `test_is_whitelist_false` | ✅ |
| `test_add_whitelist` | ✅ |
| `test_remove_whitelist` | ✅ |
| `test_duplicate_add` | ✅ |
| `test_get_not_whitelisted_messages` | ✅ |
| `test_add_message_duplicate` | ✅ |
| `test_get_message` | ✅ |
| `test_get_messages` | ✅ |
| `test_get_messages_by_bv_id` | ✅ |
| `test_get_messages_by_bv_id_with_status` | ✅ |
| `test_add_message` | ✅ |
| `test_update_status` | ✅ |
| `test_add_summary` | ✅ |
| `test_get_summaries` | ✅ |
| `test_increment_stats` | ✅ |
| `test_get_today_total` | ✅ |
| `test_get_failed_messages` | ✅ |
| `test_reset_message_status` | ✅ |
| `test_save_get_login_state` | ✅ |
| `test_clear_login_state` | ✅ |

### 5.3 crypto.py — 6 个测试 ✅

| 测试函数 | 状态 |
|---------|------|
| `test_encrypt_decrypt_roundtrip` | ✅ |
| `test_is_encrypted` | ✅ |
| `test_encrypt_if_needed` | ✅ |
| `test_decrypt_if_needed` | ✅ |
| `test_empty_string` | ✅ |
| `test_different_inputs` | ✅ |

### 5.4 message_poller.py — 15 个测试 ✅

| 测试函数 | 状态 |
|---------|------|
| `test_initial_state` | ✅ |
| `test_start_sets_running` | ✅ |
| `test_stop_clears_running` | ✅ |
| `test_set_callback` | ✅ |
| `test_retry_config` | ✅ |
| `test_exponential_backoff` | ✅ |
| `test_double_start` | ✅ |
| `test_empty_callback` | ✅ |
| `test_run_sync_poll_calls_api` | ✅ |
| `test_run_sync_poll_parses_at_response` | ✅ |
| `test_run_sync_poll_parses_dynamic_response` | ✅ |
| `test_run_sync_poll_dedup` | ✅ |
| `test_run_sync_poll_callback_invoked` | ✅ |
| `test_run_sync_poll_invalid_cookie_empty` | ✅ |
| `test_run_sync_poll_invalid_cookie_no_sessdata` | ✅ |

### 5.5 mcp_server.py — 6 个测试 ✅

| 测试函数 | 状态 |
|---------|------|
| `test_get_stats_returns_today_and_total` | ✅ |
| `test_ack_message_success` | ✅ |
| `test_get_pending_messages_returns_list` | ✅ |
| `test_add_summary_success` | ✅ |
| `test_get_summary_history` | ✅ |
| `test_unknown_tool_returns_error` | ✅ |

### 5.6 openclaw_trigger.py — 12 个测试 ✅

| 测试函数 | 状态 |
|---------|------|
| `test_command_trigger_builds_correct_command` | ✅ |
| `test_command_trigger_failure` | ✅ |
| `test_custom_openclaw_path` | ✅ |
| `test_build_message_format` | ✅ |
| `test_extract_summary_from_json` | ✅ |
| `test_extract_summary_from_plaintext` | ✅ |
| `test_extract_summary_empty_output` | ✅ |
| `test_try_read_summary_file_exists` | ✅ |
| `test_try_read_summary_file_not_found` | ✅ |
| `test_trigger_timeout` | ✅ |
| `test_notify_callback` | ✅ |
| `test_callback_not_set` | ✅ |

### 5.7 webhook_server.py — 17 个测试 ✅

| 测试函数 | 状态 |
|---------|------|
| `test_on_webhook_dynamic` | ✅ |
| `test_on_webhook_live_dm` | ✅ |
| `test_on_webhook_passthrough` | ✅ |
| `test_on_webhook_no_callback` | ✅ |
| `test_set_callback` | ✅ |
| `test_server_initial_state` | ✅ |
| `test_server_start_stop` | ✅ |
| `test_double_start` | ✅ |
| `test_double_stop` | ✅ |
| `test_webhook_endpoint_exists` | ✅ |
| `test_health_endpoint` | ✅ |
| `test_webhook_callback_invoked` | ✅ |
| `test_on_webhook_dynamic_via_server` | ✅ |
| `test_on_webhook_dynamic_missing_fields` | ✅ |
| `test_on_webhook_live_dm_missing_fields` | ✅ |
| `test_run_callback_sync` | ✅ |
| `test_run_callback_async` | ✅ |

### 5.8 subtitle_extractor.py — 25 个测试 ✅

| 测试函数 | 状态 |
|---------|------|
| `test_url_validation` (params:6) | ✅ |
| `test_parse_json_subtitle` | ✅ |
| `test_parse_srt` | ✅ |
| `test_parse_vtt` | ✅ |
| `test_clean_transcript_removes_duplicates` | ✅ |
| `test_clean_transcript_removes_html` | ✅ |
| `test_clean_transcript_empty` | ✅ |
| `test_clean_transcript_consecutive_empty_lines` | ✅ |
| `test_subtitle_file_to_text_srt` | ✅ |
| `test_subtitle_file_to_text_vtt` | ✅ |
| `test_subtitle_file_to_text_json` | ✅ |
| `test_subtitle_file_to_text_unsupported` | ✅ |
| `test_choose_best_file_empty` | ✅ |
| `test_parse_json_subtitle_invalid` | ✅ |
| `test_parse_json_subtitle_valid` | ✅ |
| `test_sanitize` (params:4) | ✅ |
| `test_parse_langs` | ✅ |
| `test_extractor_uses_cookie_from_file` | ✅ |
| `test_extractor_output_dir_exists` | ✅ |

### 5.9 gui/main_window.py — 10 个测试 ✅

> 策略：不测 tkinter 渲染/事件循环，只测数据处理逻辑。

| 测试函数 | 状态 |
|---------|------|
| `test_add_whitelist_integration` | ✅ |
| `test_remove_whitelist_empty_selection` | ✅ |
| `test_refresh_messages` | ✅ |
| `test_refresh_whitelist` | ✅ |
| `test_save_settings` | ✅ |
| `test_clear_cookie` | ✅ |
| `test_set_status` | ✅ |
| `test_on_close_saves_geometry` | ✅ |
| `test_show_cookie_input_save_placeholder` | ✅ |
| `test_show_cookie_input_save_valid` | ✅ |

### 5.10 bilibili_login.py — 12 个测试 ✅

> 策略：mock httpx 请求，不启动真实 HTTP 服务器。

| 测试函数 | 状态 |
|---------|------|
| `test_generate_qrcode_success` | ✅ |
| `test_generate_qrcode_api_failure` | ✅ |
| `test_generate_qrcode_exception` | ✅ |
| `test_poll_login_waiting` | ✅ |
| `test_poll_login_confirmed` | ✅ |
| `test_poll_login_expired` | ✅ |
| `test_poll_login_extract_cookie_from_url` | ✅ |
| `test_poll_login_no_oauth_key` | ✅ |
| `test_save_cookie` | ✅ |
| `test_save_cookie_no_cookie` | ✅ |
| `test_run_login_server` | ✅ |
| `test_run_login_server_default_port` | ✅ |

### 5.11 main.py — 9 个测试 ✅

| 测试函数 | 状态 |
|---------|------|
| `test_process_new_message_no_bv_id` | ✅ |
| `test_process_new_message_no_sender` | ✅ |
| `test_process_new_message_duplicate` | ✅ |
| `test_process_new_message_subtitle_fail` | ✅ |
| `test_on_openclaw_complete_success` | ✅ |
| `test_on_openclaw_complete_failure` | ✅ |
| `test_reprocess_blocked_messages` | ✅ |
| `test_parse_args_defaults` | ✅ |
| `test_parse_args_custom_values` | ✅ |

### 5.12 utils/app_data.py — 6 个测试 ✅

| 测试函数 | 状态 |
|---------|------|
| `test_get_app_data_dir_returns_path` | ✅ |
| `test_app_data_dir_ends_with_data` | ✅ |
| `test_app_data_dir_exists` | ✅ |
| `test_app_data_dir_is_directory` | ✅ |
| `test_creates_data_subdirectory` | ✅ |
| `test_app_data_dir_consistent` | ✅ |

### 5.13 utils/logger.py — 5 个测试 ✅

| 测试函数 | 状态 |
|---------|------|
| `test_init_logging_idempotent` | ✅ |
| `test_logger_returns_loguru_logger` | ✅ |
| `test_logger_not_none` | ✅ |
| `test_init_logging_creates_handlers` | ✅ |
| `test_logger_level_configured` | ✅ |

## 6. 测试数据管理

- **数据库**：每个测试使用 `pytest` 的 `tmp_path` fixture 创建临时 SQLite 数据库
- **配置文件**：使用 `tmp_path` 创建临时 config.json
- **B站 API**：使用 `httpx.Client` 的 mock 模拟 HTTP 响应
- **子进程**：使用 `monkeypatch` 模拟 `subprocess.run`
- **网络请求**：所有可能联网的测试标记 `@pytest.mark.network`，默认跳过
- **GUI**：不创建真实 `tk.Tk` 实例，mock `MainWindow` 方法

## 7. 测试文件组织

```
tests/
├── __init__.py               # 包标识
├── conftest.py               # 全局 fixtures
├── test_app_data.py          # 6 个测试 ✅
├── test_bilibili_login.py    # 12 个测试 ✅
├── test_config.py            # 16 个测试 ✅
├── test_crypto.py            # 6 个测试 ✅
├── test_database.py          # 21 个测试 ✅
├── test_gui.py               # 10 个测试 ✅
├── test_integration.py       # E2E 测试
├── test_logger.py            # 5 个测试 ✅
├── test_main.py              # 9 个测试 ✅
├── test_mcp_server.py        # 6 个测试 ✅
├── test_message_poller.py    # 15 个测试 ✅
├── test_openclaw_trigger.py  # 12 个测试 ✅
├── test_subtitle_extractor.py # 25 个测试 ✅
└── test_webhook_server.py    # 17 个测试 ✅
```

## 8. 执行计划

1. ✅ **Phase 1：基础设施** - pyproject.toml / tests/__init__.py / conftest.py
2. ✅ **Phase 2：修复损坏测试** - B-16, B-20
3. ✅ **Phase 3：config 模块测试** - 16 个
4. ✅ **Phase 4：database 模块测试** - 21 个
5. ✅ **Phase 5：app_data + logger** - 11 个
6. ✅ **Phase 6：message_poller** - 15 个
7. ✅ **Phase 7：mcp_server** - 6 个
8. ✅ **Phase 8：openclaw_trigger** - 12 个
9. ✅ **Phase 9：webhook_server** - 17 个
10. ✅ **Phase 10：subtitle_extractor** - 25 个
11. ✅ **Phase 11：GUI** - 10 个
12. ✅ **Phase 12：bilibili_login** - 12 个
13. ✅ **Phase 13：main + 集成** - 9 个

所有 Phase 已完成 ✅

## 9. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| GUI tkinter 需要显示器 | 无法 CI 运行 | 分离数据处理与渲染，只测数据方法 |
| 字幕提取依赖 B站 API | 测试不稳定 | Mock httpx，只测解析逻辑；标记 `@network` |
| 异步代码测试复杂度 | 事件循环冲突 | `pytest-asyncio` + `asyncio_mode = "auto"` |
| Webhook 服务器需端口 | 端口冲突 | 使用临时端口，mock 请求 |
| subprocess 调用 openclaw | 无可执行文件 | `monkeypatch` 替换 `subprocess.run` |
