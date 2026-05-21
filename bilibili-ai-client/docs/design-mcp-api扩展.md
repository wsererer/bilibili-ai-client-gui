# MCP API 扩展设计文档

## 1. 概述

### 1.1 目标

扩展 MCP Server 的工具接口，让 OpenClaw 能够完全自主运行，包括管理白名单、Cookie、配置等。

### 1.2 背景

当前 MCP Server 只提供 6 个基础工具，无法满足 OpenClaw 自主运行的需求：

| 需求 | 现状 | 缺失 |
|------|------|------|
| 白名单管理 | GUI 操作 | 无 API |
| Cookie 管理 | GUI 操作 | 无 API |
| 配置管理 | GUI 操作 | 无 API |
| 消息查询 | 只有 pending | 缺少筛选 |

---

## 2. 现有 API 分析

### 2.1 已有 MCP 工具（6 个）

| 工具 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `get_pending_messages` | 获取待处理消息 | 无 | 消息列表 |
| `get_subtitle` | 获取字幕 | `bv_id` | 字幕文本 |
| `ack_message` | 确认处理 | `msg_id`, `status` | 成功状态 |
| `get_summary_history` | 获取摘要历史 | `limit` | 摘要列表 |
| `add_summary` | 添加摘要 | `bv_id`, `summary_text` 等 | 成功状态 |
| `get_stats` | 获取统计 | 无 | 统计数据 |

### 2.2 已有数据库方法

| 方法 | 功能 |
|------|------|
| `database.add_whitelist()` | 添加白名单 |
| `database.remove_whitelist()` | 删除白名单 |
| `database.get_whitelist()` | 获取白名单 |
| `database.is_whitelist()` | 检查是否白名单 |
| `database.get_messages()` | 获取消息列表 |
| `database.get_message()` | 获取单条消息 |
| `database.update_message_status()` | 更新消息状态 |

---

## 3. 新增 API 设计

### 3.1 白名单管理（3 个）

#### add_whitelist

**描述**：添加用户到白名单

**输入**：
```json
{
  "uid": "123456",
  "username": "test_user"  // 可选
}
```

**输出**：
```json
{
  "success": true,
  "uid": "123456"
}
```

**实现**：
```python
elif name == "add_whitelist":
    uid = arguments.get("uid")
    username = arguments.get("username")
    if not uid:
        return [TextContent(type="text", text=json.dumps({"error": "uid is required"}))]
    success = database.add_whitelist(uid, username)
    return [TextContent(type="text", text=json.dumps({"success": success, "uid": uid}))]
```

---

#### remove_whitelist

**描述**：从白名单移除用户

**输入**：
```json
{
  "uid": "123456"
}
```

**输出**：
```json
{
  "success": true,
  "uid": "123456"
}
```

**实现**：
```python
elif name == "remove_whitelist":
    uid = arguments.get("uid")
    if not uid:
        return [TextContent(type="text", text=json.dumps({"error": "uid is required"}))]
    success = database.remove_whitelist(uid)
    return [TextContent(type="text", text=json.dumps({"success": success, "uid": uid}))]
```

---

#### get_whitelist

**描述**：获取白名单列表

**输入**：
```json
{}
```

**输出**：
```json
[
  {
    "uid": "123456",
    "username": "test_user",
    "added_at": "2024-01-01 12:00:00"
  }
]
```

**实现**：
```python
elif name == "get_whitelist":
    whitelist = database.get_whitelist()
    return [TextContent(type="text", text=json.dumps(whitelist, ensure_ascii=False))]
```

---

### 3.2 Cookie 管理（3 个）

#### set_cookie

**描述**：设置 B站登录 Cookie

**输入**：
```json
{
  "cookie": "SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx"
}
```

**输出**：
```json
{
  "success": true,
  "length": 120
}
```

**实现**：
```python
elif name == "set_cookie":
    cookie = arguments.get("cookie", "")
    if not cookie:
        return [TextContent(type="text", text=json.dumps({"error": "cookie is required"}))]
    config.set("bili_auth", cookie)
    # 同时保存到文件
    from utils.app_data import APP_DATA_DIR
    cookie_file = APP_DATA_DIR / "login_cookie.txt"
    cookie_file.write_text(cookie, encoding='utf-8')
    return [TextContent(type="text", text=json.dumps({"success": True, "length": len(cookie)}))]
```

---

#### get_cookie_status

**描述**：获取 Cookie 状态

**输入**：
```json
{}
```

**输出**：
```json
{
  "has_cookie": true,
  "length": 120,
  "has_sessdata": true
}
```

**实现**：
```python
elif name == "get_cookie_status":
    cookie = config.get("bili_auth", "")
    return [TextContent(type="text", text=json.dumps({
        "has_cookie": bool(cookie),
        "length": len(cookie),
        "has_sessdata": "SESSDATA" in cookie
    }))]
```

---

#### clear_cookie

**描述**：清除 Cookie

**输入**：
```json
{}
```

**输出**：
```json
{
  "success": true
}
```

**实现**：
```python
elif name == "clear_cookie":
    config.set("bili_auth", "")
    from utils.app_data import APP_DATA_DIR
    cookie_file = APP_DATA_DIR / "login_cookie.txt"
    if cookie_file.exists():
        cookie_file.write_text("", encoding='utf-8')
    return [TextContent(type="text", text=json.dumps({"success": True}))]
```

---

### 3.3 配置管理（2 个）

#### get_config

**描述**：获取配置项

**输入**：
```json
{
  "key": "polling_interval"  // 可选，不传返回全部
}
```

**输出**：
```json
// 指定 key
{
  "key": "polling_interval",
  "value": 30
}

// 全部配置
{
  "polling_interval": 30,
  "openclaw_path": "openclaw",
  "auto_start": true,
  ...
}
```

**实现**：
```python
elif name == "get_config":
    key = arguments.get("key")
    if key:
        value = config.get(key)
        return [TextContent(type="text", text=json.dumps({"key": key, "value": value}, ensure_ascii=False))]
    else:
        # 返回全部配置（隐藏敏感信息）
        all_config = config._config.copy()
        if "bili_auth" in all_config and all_config["bili_auth"]:
            all_config["bili_auth"] = f"***({len(all_config['bili_auth'])} chars)"
        return [TextContent(type="text", text=json.dumps(all_config, ensure_ascii=False))]
```

---

#### set_config

**描述**：设置配置项

**输入**：
```json
{
  "key": "polling_interval",
  "value": "60"
}
```

**输出**：
```json
{
  "success": true,
  "key": "polling_interval",
  "value": "60"
}
```

**实现**：
```python
elif name == "set_config":
    key = arguments.get("key")
    value = arguments.get("value")
    if not key:
        return [TextContent(type="text", text=json.dumps({"error": "key is required"}))]
    config.set(key, value)
    return [TextContent(type="text", text=json.dumps({"success": True, "key": key, "value": value}))]
```

---

### 3.4 消息管理（1 个）

#### get_messages

**描述**：获取消息列表（支持筛选）

**输入**：
```json
{
  "limit": 50,
  "status": "trigger_failed"  // 可选
}
```

**输出**：
```json
[
  {
    "id": "msg_xxx",
    "bv_id": "BV1xxx",
    "sender_uid": "123456",
    "sender_name": "test_user",
    "content": "...",
    "status": "trigger_failed",
    "received_at": "2024-01-01 12:00:00"
  }
]
```

**实现**：
```python
elif name == "get_messages":
    limit = arguments.get("limit", 50)
    status = arguments.get("status")
    if status:
        messages = [m for m in database.get_messages(limit * 2) if m.get("status") == status][:limit]
    else:
        messages = database.get_messages(limit)
    return [TextContent(type="text", text=json.dumps(messages, ensure_ascii=False))]
```

---

## 4. 完整工具列表

### 4.1 工具总览（15 个）

| 类别 | 工具 | 状态 |
|------|------|------|
| 消息 | `get_pending_messages` | 已有 |
| 消息 | `get_messages` | **新增** |
| 消息 | `ack_message` | 已有 |
| 字幕 | `get_subtitle` | 已有 |
| 摘要 | `get_summary_history` | 已有 |
| 摘要 | `add_summary` | 已有 |
| 统计 | `get_stats` | 已有 |
| 白名单 | `add_whitelist` | **新增** |
| 白名单 | `remove_whitelist` | **新增** |
| 白名单 | `get_whitelist` | **新增** |
| Cookie | `set_cookie` | **新增** |
| Cookie | `get_cookie_status` | **新增** |
| Cookie | `clear_cookie` | **新增** |
| 配置 | `get_config` | **新增** |
| 配置 | `set_config` | **新增** |

---

## 5. 实现步骤

### 5.1 修改文件

| 文件 | 修改内容 |
|------|----------|
| `mcp_server.py` | 新增 9 个工具定义和处理逻辑 |

### 5.2 实现顺序

1. 添加工具定义（`list_tools` 函数）
2. 添加处理逻辑（`call_tool` 函数）
3. 测试每个工具

---

## 6. 测试用例

### 6.1 白名单测试

```python
# 添加白名单
result = call_tool("add_whitelist", {"uid": "123456", "username": "test"})
assert result["success"] == True

# 获取白名单
whitelist = call_tool("get_whitelist", {})
assert any(item["uid"] == "123456" for item in whitelist)

# 删除白名单
result = call_tool("remove_whitelist", {"uid": "123456"})
assert result["success"] == True
```

### 6.2 Cookie 测试

```python
# 设置 Cookie
result = call_tool("set_cookie", {"cookie": "SESSDATA=xxx; bili_jct=xxx"})
assert result["success"] == True

# 获取状态
status = call_tool("get_cookie_status", {})
assert status["has_cookie"] == True

# 清除 Cookie
result = call_tool("clear_cookie", {})
assert result["success"] == True
```

### 6.3 配置测试

```python
# 设置配置
result = call_tool("set_config", {"key": "polling_interval", "value": "60"})
assert result["success"] == True

# 获取配置
config = call_tool("get_config", {"key": "polling_interval"})
assert config["value"] == "60"
```

---

## 7. 工作量估算

| 任务 | 时间 |
|------|------|
| 添加工具定义 | 30 分钟 |
| 添加处理逻辑 | 1 小时 |
| 测试和调试 | 30 分钟 |
| **总计** | **2 小时** |
