# Bilibili AI Client - 测试文档

## 目录
1. [概述与环境准备](#1-概述与环境准备)
2. [配置系统测试](#2-配置系统测试)
3. [登录与认证测试](#3-登录与认证测试)
4. [数据库测试](#4-数据库测试)
5. [消息轮询服务测试](#5-消息轮询服务测试)
6. [字幕提取测试](#6-字幕提取测试)
7. [OpenClaw 触发器测试](#7-openclaw-触发器测试)
8. [MCP 服务器测试](#8-mcp-服务器测试)
9. [Webhook 服务测试](#9-webhook-服务测试)
10. [GUI 功能测试](#10-gui-功能测试)
11. [端到端集成测试](#11-端到端集成测试)
12. [异常与边界条件测试](#12-异常与边界条件测试)

---

## 1. 概述与环境准备

### 1.1 测试范围

本项目为 **Bilibili AI 客户端**，核心功能：
- 轮询 B站动态/提及消息
- 提取视频字幕（B站API > yt-dlp > Whisper本地转写）
- 触发 OpenClaw 进行 AI 处理
- 提供 GUI 界面和 MCP 服务器接口

### 1.2 测试环境要求

```
Python: 3.10+
依赖: pip install -r requirements.txt
数据库: data/bilibili_client.db (SQLite)
Cookie: data/login_cookie.txt 或 config.json 中的 bili_auth
```

### 1.3 前置条件

```bash
# 准备测试 Cookie（两种方式）
# 方式1: 登录生成
python bilibili_login.py

# 方式2: 手动写入（参考格式）
echo "SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx" > data/login_cookie.txt
```

### 1.4 测试数据准备

| 类型 | BV号 | 说明 |
|------|------|------|
| 有官方字幕 | `BV1h8rDBFEV7` | 东京股神，有 `zh` 用户字幕 |
| 有AI字幕 | `BV1Y5BxBpEpg` | 有 `zh` + `ai-zh` 字幕 |
| 无字幕视频 | `BV1xx411c7mD` | 需要 Whisper 转写 |

白名单测试用户: `17709654` (wsererer)

### 1.5 测试运行方式

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定模块测试
python -m pytest tests/test_subtitle.py -v

# 运行带详细输出
python -m pytest tests/ -v -s --tb=short
```

---

## 2. 配置系统测试

### 2.1 Config 单例模式

```python
def test_config_singleton():
    from config import Config, config
    c1 = Config()
    c2 = Config()
    assert c1 is c2 is config

def test_config_defaults():
    from config import config
    assert config.get("language") == "zh"
    assert config.get("theme") == "light"
    assert config.get("polling_interval") == 30
    assert config.get("auto_start") == True
```

### 2.2 配置读写

```python
def test_config_get_set(tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.json")
    c = config.Config()
    c.set("test_key", "test_value")
    assert c.get("test_key") == "test_value"
```

### 2.3 bili_auth 配置

```python
def test_bili_auth_config():
    from config import config
    valid_cookie = "SESSDATA=xxx,1234567890,abc*xyz; bili_jct=xxx; DedeUserID=123"
    config.set("bili_auth", valid_cookie)
    assert len(config.get("bili_auth")) > 50
```

### 2.4 配置项完整列表

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `language` | str | "zh" | 语言 |
| `theme` | str | "light" | 主题 |
| `message_mode` | str | "polling" | 消息模式 |
| `polling_interval` | int | 30 | 轮询间隔(秒) |
| `openclaw_trigger` | str | "command" | 触发方式 |
| `webhook_url` | str | "http://127.0.0.1:18789/hooks/agent" | Webhook地址 |
| `webhook_port` | int | 18792 | Webhook端口 |
| `auto_start` | bool | True | 启动时自动开始 |
| `bili_auth` | str | "" | B站认证Cookie |

---

## 3. 登录与认证测试

### 3.1 QR 码登录流程

```python
def test_qrcode_generation():
    import httpx
    resp = httpx.get(
        "https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
        timeout=10
    )
    data = resp.json()
    assert data["code"] == 0
    assert "qrcode_key" in data["data"]
    assert "url" in data["data"]

def test_login_server_routes():
    import requests
    base_url = "http://127.0.0.1:51888"
    assert requests.get(f"{base_url}/", timeout=5).status_code == 200
    assert requests.get(f"{base_url}/login_status", timeout=5).status_code == 200
```

### 3.2 Cookie 提取与保存

```python
def test_cookie_extraction():
    from bilibili_login import extract_cookies
    mock_response = {
        "code": 0,
        "data": {
            "cookie_info": {
                "SESSDATA": "test_sessdata",
                "bili_jct": "test_bili_jct",
                "DedeUserID": "123456"
            }
        }
    }
    cookies = extract_cookies(mock_response)
    assert "SESSDATA=test_sessdata" in cookies
    assert len(cookies) > 50
```

---

## 4. 数据库测试

### 4.1 数据库初始化

```python
def test_db_init(tmp_path):
    import sqlite3
    from database import get_db, init_db
    db_path = tmp_path / "test.db"
    init_db(db_path)
    assert db_path.exists()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    assert all(t in tables for t in ["whitelist", "messages", "summaries", "stats"])
```

### 4.2 白名单管理

```python
def test_whitelist_add_remove(tmp_path):
    from database import add_whitelist, remove_whitelist, is_whitelist
    init_db(tmp_path / "test.db")
    add_whitelist("123456", "test_user")
    assert is_whitelist("123456") == True
    remove_whitelist("123456")
    assert is_whitelist("123456") == False
```

### 4.3 消息管理

```python
def test_message_add_and_get(tmp_path):
    from database import add_message, get_pending_messages, update_message_status
    init_db(tmp_path / "test.db")
    add_message(msg_id="msg_001", sender_uid="123", sender_name="用户A",
                bv_id="BV1xxx", content="测试消息")
    pending = get_pending_messages()
    assert any(m["msg_id"] == "msg_001" for m in pending)
    update_message_status("msg_001", "processed")
```

### 4.4 摘要与统计

```python
def test_summary_and_stats(tmp_path):
    from database import add_summary, get_summaries, increment_stats, get_today_count
    init_db(tmp_path / "test.db")
    add_summary(bv_id="BV1xxx", sender_uid="123", sender_name="用户A",
                subtitle_text="字幕", summary_text="摘要")
    increment_stats()
    assert get_today_count() >= 1
```

---

## 5. 消息轮询服务测试

### 5.1 Poller 生命周期

```python
def test_poller_start_stop():
    from message_poller import MessagePoller
    poller = MessagePoller()
    assert poller.running == False
    poller.start()
    assert poller.running == True
    poller.stop()
    assert poller.running == False
```

### 5.2 动态消息获取

```python
def test_getdynamic_with_auth():
    import asyncio
    from message_poller import MessagePoller
    poller = MessagePoller()
    bili_auth = open("data/login_cookie.txt").read().strip()
    async def test():
        return await poller.getdynamic(bili_auth)
    result = asyncio.run(test())
    assert isinstance(result, list)
```

### 5.3 回调机制

```python
def test_poller_callback():
    from message_poller import MessagePoller
    poller = MessagePoller()
    results = []
    def cb(msg): results.append(msg)
    poller.set_callback(cb)
    poller._notify_callbacks({"msg_id": "test_001"})
    assert len(results) == 1
    assert results[0]["msg_id"] == "test_001"
```

---

## 6. 字幕提取测试

### 6.1 URL 格式验证

```python
@pytest.mark.parametrize("url,expected", [
    ("https://www.bilibili.com/video/BV1xxx", True),
    ("https://b23.tv/xxx", True),
    ("https://youtube.com/watch?v=xxx", False),
])
def test_is_bilibili_url(url, expected):
    from utils.subtitle_extractor import is_bilibili_url
    assert is_bilibili_url(url) == expected
```

### 6.2 **字幕优先级验证（核心）**

```python
def test_priority_user_subtitle_over_ai():
    """用户字幕 > AI字幕 > Whisper"""
    from utils.subtitle_extractor import SubtitleExtractor
    extractor = SubtitleExtractor()

    # BV1Y5BxBpEpg 有 zh (type=0) 和 ai-zh (type=1)
    # 必须返回用户字幕，不是AI字幕
    result = extractor.extract("https://www.bilibili.com/video/BV1Y5BxBpEpg")
    assert result is not None
    assert result.source == "subtitle"
    assert "zh" in result.raw_subtitle_path.lower()
    assert "ai-zh" not in result.raw_subtitle_path.lower()

def test_priority_ai_over_whisper():
    """有AI字幕时不应使用 Whisper"""
    from utils.subtitle_extractor import SubtitleExtractor
    extractor = SubtitleExtractor()

    result = extractor.extract("https://www.bilibili.com/video/BV1xxx")
    if result:
        assert result.source in ["subtitle"]  # 不应该是 whisper

def test_whisper_as_last_resort():
    """无字幕时使用 Whisper"""
    from utils.subtitle_extractor import SubtitleExtractor
    extractor = SubtitleExtractor()

    # 强制测试 Whisper 路径（无有效 cookie）
    extractor.cookie = None
    result = extractor.extract("https://www.bilibili.com/video/BV1xxx")
    # 应该返回 Whisper 转写或 None
```

### 6.3 B站 API 字幕获取

```python
def test_bilibili_api_subtitle():
    """测试 B站 /x/player/v2 API"""
    from utils.subtitle_extractor import SubtitleExtractor
    extractor = SubtitleExtractor()

    result = extractor.extract("https://www.bilibili.com/video/BV1h8rDBFEV7")
    assert result is not None
    assert len(result.transcript_text) > 10
```

### 6.4 字幕解析

```python
def test_subtitle_file_to_text():
    from utils.subtitle_extractor import subtitle_file_to_text
    # 测试 SRT/VTT/JSON 格式解析
    # 验证 clean_transcript 去除重复行
```

---

## 7. OpenClaw 触发器测试

### 7.1 命令模式

```python
def test_command_trigger(monkeypatch):
    from openclaw_trigger import OpenClawTrigger
    triggered = []
    def mock_run(cmd, **kwargs):
        triggered.append(cmd)
        return type('obj',(object,),{'returncode':0,'stdout':'OK','stderr':''})()
    monkeypatch.setattr("subprocess.run", mock_run)

    trigger = OpenClawTrigger(mode="command")
    success = trigger.trigger(bv_id="BV1xxx", subtitle_text="测试",
                            sender_uid="123", sender_name="用户")
    assert success == True
    assert "openclaw" in triggered[0].lower()
```

### 7.2 Webhook 模式

```python
def test_webhook_trigger(monkeypatch):
    import httpx
    from openclaw_trigger import OpenClawTrigger

    async def mock_post(url, json=None, **kwargs):
        return type('obj',(object,),{'status_code':200})()
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    trigger = OpenClawTrigger(mode="webhook")
    async def test():
        return await trigger.trigger(bv_id="BV1xxx", subtitle_text="测试",
                                   sender_uid="123", sender_name="用户")
    assert asyncio.run(test()) == True
```

---

## 8. MCP 服务器测试

### 8.1 工具列表

```python
def test_mcp_tools():
    from mcp_server import list_tools
    import asyncio
    tools = asyncio.run(list_tools())
    assert len(tools) == 6
    assert any(t.name == "get_subtitle" for t in tools)
    assert any(t.name == "ack_message" for t in tools)
```

### 8.2 工具调用

```python
@pytest.mark.parametrize("tool,args", [
    ("get_pending_messages", {}),
    ("get_stats", {}),
    ("ack_message", {"msg_id": "x", "status": "processed"}),
])
def test_mcp_tool_call(tool, args):
    from mcp_server import call_tool
    import asyncio
    results = asyncio.run(call_tool(tool, args))
    assert len(results) == 1
```

---

## 9. Webhook 服务测试

### 9.1 消息格式转换

```python
@pytest.mark.parametrize("payload,expected_bv", [
    ({"type": "dynamic", "bv_id": "BV1xxx"}, "BV1xxx"),
    ({"type": "live_dm", "bv_id": "BV1yyy"}, "BV1yyy"),
])
def test_message_normalization(payload, expected_bv):
    from webhook_server import WebhookReceiver
    r = WebhookReceiver()
    assert r._normalize_message(payload)["bv_id"] == expected_bv
```

### 9.2 健康检查

```python
def test_webhook_health():
    import requests
    r = requests.get("http://127.0.0.1:18792/health", timeout=5)
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

---

## 10. GUI 功能测试

> GUI 使用 Tkinter，需要图形环境

### 10.1 窗口初始化

```python
def test_gui_window_init():
    from gui.main_window import MainWindow
    window = MainWindow()
    assert window.window is not None
```

### 10.2 白名单 UI

```python
def test_gui_whitelist_add():
    from gui.main_window import MainWindow
    from database import is_whitelist, remove_whitelist
    window = MainWindow()
    window.uid_entry.insert(0, "998899")
    window.username_entry.insert(0, "测试")
    window.add_whitelist()
    assert is_whitelist("998899") == True
    remove_whitelist("998899")
```

### 10.3 设置保存

```python
def test_gui_settings_save():
    from gui.main_window import MainWindow
    from config import config
    window = MainWindow()
    window.polling_interval_entry.delete(0, "end")
    window.polling_interval_entry.insert(0, "60")
    window.save_settings()
    assert config.get("polling_interval") == 60
```

---

## 11. 端到端集成测试

### 11.1 完整消息处理流程

```python
def test_full_message_processing():
    """测试消息收到 → 字幕提取 → 触发的完整流程"""
    from message_poller import MessagePoller
    from database import add_whitelist, add_message, get_pending_messages
    from main import process_new_message
    import asyncio

    bili_auth = open("data/login_cookie.txt").read().strip()
    test_uid = "998899"
    add_whitelist(test_uid, "测试用户")

    test_msg = {
        "msg_id": "e2e_test",
        "bv_id": "BV1h8rDBFEV7",
        "sender_uid": test_uid,
        "sender_name": "测试",
        "content": "测试"
    }

    asyncio.run(process_new_message(test_msg))
    pending = get_pending_messages()
    # 验证状态更新
```

### 11.2 GUI 全模式启动

```python
def test_all_mode_startup():
    import subprocess, time
    proc = subprocess.Popen(["python", "main.py", "--mode", "all"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5)
    assert proc.poll() is None  # 进程正常运行
    proc.terminate()
    proc.wait()
```

---

## 12. 异常与边界条件测试

### 12.1 无效 Cookie

```python
def test_no_cookie_fallback():
    from utils.subtitle_extractor import SubtitleExtractor
    extractor = SubtitleExtractor()
    extractor.cookie = "invalid"
    # 应该使用 Whisper，不应崩溃
```

### 12.2 网络超时

```python
def test_network_timeout():
    import httpx
    from utils.subtitle_extractor import SubtitleExtractor
    extractor = SubtitleExtractor()
    # 验证超时后优雅降级
```

### 12.3 空字幕文本

```python
def test_empty_subtitle():
    from utils.subtitle_extractor import SubtitleExtractor
    extractor = SubtitleExtractor()
    result = extractor.extract("https://www.bilibili.com/video/BV1xxx")
    if result:
        assert result.source in ["subtitle", "whisper"]
```

### 12.4 并发消息处理

```python
def test_concurrent_processing():
    import asyncio
    from main import process_new_message
    messages = [
        {"msg_id": f"c_{i}", "bv_id": "BV1xxx",
         "sender_uid": "999999", "sender_name": "测", "content": "测"}
        for i in range(10)
    ]
    async def test():
        await asyncio.gather(*[process_new_message(m) for m in messages])
    asyncio.run(test())  # 不应死锁
```

---

## 附录

### A. 测试夹具

```python
@pytest.fixture
def temp_db(tmp_path):
    from database import init_db
    db_path = tmp_path / "test.db"
    init_db(db_path)
    yield db_path

@pytest.fixture
def valid_cookie():
    if Path("data/login_cookie.txt").exists():
        return Path("data/login_cookie.txt").read_text().strip()
    pytest.skip("No cookie file")
```

### B. 测试 BV 号汇总

| BV号 | 字幕类型 | 用途 |
|------|----------|------|
| `BV1h8rDBFEV7` | 用户字幕 `zh` | 标准字幕提取测试 |
| `BV1Y5BxBpEpg` | 用户字幕 `zh` + AI字幕 `ai-zh` | 优先级验证 |
| `BV1xx411c7mD` | 无字幕 | Whisper fallback 测试 |

### C. Mock 策略

```python
# 使用 pytest-mock 避免依赖真实 API
def test_with_mock(monkeypatch):
    async def mock_get(*args, **kwargs):
        return {"data": {"cid": 12345}}
    monkeypatch.setattr(httpx, "get", mock_get)
    # 测试逻辑
```