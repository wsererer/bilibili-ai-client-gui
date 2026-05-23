# 失败任务重试设计文档

## 1. 概述

### 1.1 目标

让 OpenClaw 能够重新处理失败的任务，避免每次测试都要重新发送评论。

### 1.2 背景

当前消息处理失败后，状态会变成 `trigger_failed` 或 `openclaw_failed`，但：
- 没有重新处理的 API
- 没有重置状态的机制
- 测试不便，需要重新发评论

---

## 2. 失败状态分析

### 2.1 当前失败状态

| 状态 | 说明 | 可重试 |
|------|------|--------|
| `trigger_failed` | 触发 OpenClaw 失败 | ✅ |
| `openclaw_failed` | OpenClaw 处理失败 | ✅ |
| `no_subtitle` | 无法获取字幕 | ✅ |
| `not_whitelisted` | 不在白名单 | ✅ |
| `no_sender_uid` | 无发送者 UID | ❌ |

### 2.2 失败原因

| 原因 | 解决方案 |
|------|----------|
| OpenClaw 超时 | 重试 |
| 字幕提取失败 | 重试（可能临时网络问题） |
| 网络错误 | 重试 |
| 白名单问题 | 先添加白名单，再重试 |

---

## 3. 新增 API 设计

### 3.1 get_failed_messages

**描述**：获取处理失败的消息列表

**输入**：
```json
{
  "limit": 20,
  "status": "all"
}
```

**参数说明**：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `limit` | integer | 否 | 20 | 返回数量 |
| `status` | string | 否 | "all" | 筛选状态 |

**可选状态值**：
- `all` - 所有失败状态
- `trigger_failed` - 触发失败
- `openclaw_failed` - 处理失败
- `no_subtitle` - 无字幕
- `not_whitelisted` - 不在白名单

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
Tool(
    name="get_failed_messages",
    description="获取处理失败的消息列表，用于重试",
    inputSchema={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "返回数量，默认20",
                "default": 20
            },
            "status": {
                "type": "string",
                "description": "筛选状态：trigger_failed / openclaw_failed / no_subtitle / not_whitelisted / all",
                "default": "all"
            }
        },
        "required": []
    }
)
```

---

### 3.2 retry_message

**描述**：重新处理指定消息（重置状态为 pending）

**输入**：
```json
{
  "msg_id": "msg_xxx"
}
```

**输出**：
```json
{
  "success": true,
  "msg_id": "msg_xxx",
  "old_status": "trigger_failed",
  "new_status": "pending"
}
```

**实现**：
```python
Tool(
    name="retry_message",
    description="重新处理指定消息（重置状态为pending）",
    inputSchema={
        "type": "object",
        "properties": {
            "msg_id": {
                "type": "string",
                "description": "消息ID"
            }
        },
        "required": ["msg_id"]
    }
)
```

---

## 4. 数据库新增方法

### 4.1 get_failed_messages

```python
@staticmethod
def get_failed_messages(limit: int = 20, status: str = "all") -> List[Dict[str, Any]]:
    """获取失败的消息"""
    with get_db() as conn:
        cursor = conn.cursor()
        if status == "all":
            cursor.execute("""
                SELECT * FROM messages 
                WHERE status IN ('trigger_failed', 'openclaw_failed', 'no_subtitle', 'not_whitelisted')
                ORDER BY received_at DESC LIMIT ?
            """, (limit,))
        else:
            cursor.execute("""
                SELECT * FROM messages 
                WHERE status = ?
                ORDER BY received_at DESC LIMIT ?
            """, (status, limit))
        return [dict(row) for row in cursor.fetchall()]
```

### 4.2 reset_message_status

```python
@staticmethod
def reset_message_status(msg_id: str) -> Optional[str]:
    """重置消息状态为 pending，返回原状态"""
    with get_db() as conn:
        cursor = conn.cursor()
        # 先获取原状态
        cursor.execute("SELECT status FROM messages WHERE id = ?", (msg_id,))
        row = cursor.fetchone()
        if not row:
            return None
        old_status = row["status"]
        # 重置状态
        cursor.execute("UPDATE messages SET status = 'pending' WHERE id = ?", (msg_id,))
        return old_status
```

---

## 5. MCP 工具实现

### 5.1 工具定义

```python
Tool(
    name="get_failed_messages",
    description="获取处理失败的消息列表，用于重试",
    inputSchema={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "返回数量，默认20",
                "default": 20
            },
            "status": {
                "type": "string",
                "description": "筛选状态：trigger_failed / openclaw_failed / no_subtitle / not_whitelisted / all",
                "default": "all"
            }
        },
        "required": []
    }
),
Tool(
    name="retry_message",
    description="重新处理指定消息（重置状态为pending）",
    inputSchema={
        "type": "object",
        "properties": {
            "msg_id": {
                "type": "string",
                "description": "消息ID"
            }
        },
        "required": ["msg_id"]
    }
),
```

### 5.2 处理逻辑

```python
elif name == "get_failed_messages":
    limit = arguments.get("limit", 20)
    status = arguments.get("status", "all")
    messages = database.get_failed_messages(limit, status)
    return [TextContent(type="text", text=json.dumps(messages, ensure_ascii=False))]

elif name == "retry_message":
    msg_id = arguments.get("msg_id")
    if not msg_id:
        return [TextContent(type="text", text=json.dumps({"error": "msg_id is required"}))]
    old_status = database.reset_message_status(msg_id)
    if old_status is None:
        return [TextContent(type="text", text=json.dumps({"error": "Message not found"}))]
    return [TextContent(type="text", text=json.dumps({
        "success": True,
        "msg_id": msg_id,
        "old_status": old_status,
        "new_status": "pending"
    }))]
```

---

## 6. GUI 重试按钮（可选）

### 6.1 界面设计

在消息列表下方添加"重试"按钮：

```python
def _setup_messages_tab(self, parent):
    # ... 现有代码 ...
    
    btn_frame = ttk.Frame(parent)
    btn_frame.pack(fill=tk.X, padx=5, pady=5)
    ttk.Button(btn_frame, text="刷新", command=self._refresh_messages).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="处理选中", command=self._process_message).pack(side=tk.LEFT, padx=2)
    ttk.Button(btn_frame, text="重试失败", command=self._retry_failed).pack(side=tk.LEFT, padx=2)  # 新增
```

### 6.2 重试逻辑

```python
def _retry_failed(self):
    """重试失败的消息"""
    selection = self.message_list.curselection()
    if not selection:
        return
    
    content = self.message_list.get(selection[0])
    # 解析消息 ID
    try:
        msg_id = content.split("]")[0].split("[")[1]
    except Exception:
        self._set_status("无法解析消息ID")
        return
    
    old_status = database.reset_message_status(msg_id)
    if old_status:
        self._set_status(f"已重置消息 {msg_id} 状态: {old_status} -> pending")
        self._refresh_messages()
    else:
        self._set_status("重置失败")
```

---

## 7. OpenClaw 重试流程

### 7.1 完整流程

```python
# 1. 获取失败消息
failed = call_tool("get_failed_messages", {"status": "all"})

# 2. 重试每条失败消息
for msg in failed:
    msg_id = msg["id"]
    bv_id = msg["bv_id"]
    
    # 3. 重置状态为 pending
    result = call_tool("retry_message", {"msg_id": msg_id})
    if not result["success"]:
        continue
    
    # 4. 获取字幕
    subtitle_result = call_tool("get_subtitle", {"bv_id": bv_id})
    subtitle = subtitle_result.get("subtitle", "")
    
    if not subtitle:
        # 仍然无法获取字幕
        call_tool("ack_message", {"msg_id": msg_id, "status": "failed"})
        continue
    
    # 5. 生成摘要（调用 OpenClaw）
    # ... OpenClaw 处理逻辑 ...
    
    # 6. 保存摘要
    call_tool("add_summary", {
        "bv_id": bv_id,
        "sender_uid": msg["sender_uid"],
        "sender_name": msg["sender_name"],
        "subtitle_text": subtitle,
        "summary_text": summary
    })
    
    # 7. 确认处理完成
    call_tool("ack_message", {"msg_id": msg_id, "status": "processed"})
```

### 7.2 批量重试

```python
# 批量重试所有失败消息
def retry_all_failed():
    failed = call_tool("get_failed_messages", {"status": "all", "limit": 100})
    success_count = 0
    fail_count = 0
    
    for msg in failed:
        result = call_tool("retry_message", {"msg_id": msg["id"]})
        if result["success"]:
            success_count += 1
        else:
            fail_count += 1
    
    return {"success": success_count, "fail": fail_count}
```

---

## 8. 测试用例

### 8.1 单元测试

```python
def test_get_failed_messages():
    # 创建测试消息
    database.add_message("test_msg_1", "123", "user", "BV1xxx", "content")
    database.update_message_status("test_msg_1", "trigger_failed")
    
    # 获取失败消息
    failed = database.get_failed_messages()
    assert any(m["id"] == "test_msg_1" for m in failed)

def test_reset_message_status():
    # 创建测试消息
    database.add_message("test_msg_2", "123", "user", "BV1xxx", "content")
    database.update_message_status("test_msg_2", "trigger_failed")
    
    # 重置状态
    old_status = database.reset_message_status("test_msg_2")
    assert old_status == "trigger_failed"
    
    # 验证新状态
    msg = database.get_message("test_msg_2")
    assert msg["status"] == "pending"
```

### 8.2 集成测试

```python
def test_retry_workflow():
    # 模拟失败消息
    call_tool("add_whitelist", {"uid": "123"})
    call_tool("ack_message", {"msg_id": "test_msg", "status": "trigger_failed"})
    
    # 获取失败消息
    failed = call_tool("get_failed_messages", {})
    assert len(failed) > 0
    
    # 重试
    result = call_tool("retry_message", {"msg_id": "test_msg"})
    assert result["success"] == True
    
    # 验证状态
    msg = database.get_message("test_msg")
    assert msg["status"] == "pending"
```

---

## 9. 工作量估算

| 任务 | 时间 |
|------|------|
| 数据库新增方法 | 15 分钟 |
| MCP 工具定义 | 15 分钟 |
| MCP 处理逻辑 | 30 分钟 |
| GUI 重试按钮 | 15 分钟 |
| 测试 | 30 分钟 |
| **总计** | **1.5 小时** |
