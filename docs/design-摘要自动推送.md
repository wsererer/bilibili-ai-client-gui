# 摘要自动推送设计文档

## 1. 概述

### 1.1 目标

实现摘要自动推送功能，当 OpenClaw 处理完视频摘要后，自动通过微信或飞书发送给用户。

### 1.2 实现状态

**已实现** ✅

---

## 2. 功能设计

### 2.1 核心功能

| 功能 | 说明 |
|------|------|
| 自动推送 | OpenClaw 处理完成后自动发送摘要 |
| 渠道选择 | 支持微信、飞书、或两者同时 |
| 配置开关 | 可启用/禁用自动推送 |
| 目标配置 | 可配置推送目标账号 |

### 2.2 工作流程

```
用户@AI → 提取字幕 → OpenClaw 处理 → 生成摘要 → 发送指令 → 推送给用户
```

---

## 3. 配置项设计

### 3.1 配置项列表

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `auto_send` | bool | `False` | 是否自动发送摘要 |
| `send_channel` | string | `"wechat"` | 发送渠道 |
| `wechat_target` | string | `""` | 微信目标账号 |
| `feishu_target` | string | `""` | 飞书目标账号 |

### 3.2 渠道选项

| 值 | 说明 |
|------|------|
| `"wechat"` | 仅微信 |
| `"feishu"` | 仅飞书 |
| `"both"` | 微信和飞书同时发送 |

### 3.3 配置文件示例

**config.json**：
```json
{
  "auto_send": true,
  "send_channel": "wechat",
  "wechat_target": "wx_801q...",
  "feishu_target": ""
}
```

---

## 4. 消息格式修改

### 4.1 修改文件

**`openclaw_trigger.py`**

### 4.2 修改内容

**`_build_message` 方法**：

```python
def _build_message(self, bv_id: str, subtitle_path: str, sender_uid: str, sender_name: str) -> str:
    sender_info = f"发送者UID: {sender_uid}"
    if sender_name:
        sender_info += f" ({sender_name})"

    send_instruction = ""
    auto_send = config.get("auto_send", False)
    if auto_send:
        send_channel = config.get("send_channel", "wechat")
        wechat_target = config.get("wechat_target", "")
        feishu_target = config.get("feishu_target", "")
        if send_channel == "wechat":
            target = f"，目标账号: {wechat_target}" if wechat_target else ""
            send_instruction = f" | 【重要】处理完成后，通过微信发送摘要给用户{target}"
        elif send_channel == "feishu":
            target = f"，目标账号: {feishu_target}" if feishu_target else ""
            send_instruction = f" | 【重要】处理完成后，通过飞书发送摘要给用户{target}"
        elif send_channel == "both":
            target_w = f"，微信目标账号: {wechat_target}" if wechat_target else ""
            target_f = f"，飞书目标账号: {feishu_target}" if feishu_target else ""
            send_instruction = f" | 【重要】处理完成后，通过微信和飞书发送摘要给用户{target_w}{target_f}"

    return (f"处理视频任务 | BV号: {bv_id} | {sender_info} | "
            f"请使用 read 工具读取字幕文件，然后生成视频摘要并保存 | "
            f"字幕文件路径: {subtitle_path} | "
            f"请生成视频摘要并保存到 ~/.openclaw/workspace/bilibili-summaries/ 目录 | "
            f"格式: 日期/BV号.md{send_instruction}")
```

---

## 5. GUI 设置界面

### 5.1 界面设计

```
┌─────────────────────────────────────────────────────────┐
│ 摘要推送设置                                              │
├─────────────────────────────────────────────────────────┤
│ ☑ 启用摘要自动推送                                        │
│                                                          │
│ 推送渠道:                                                 │
│   (•)微信  ( )飞书  ( )两者                               │
│                                                          │
│ 微信目标: [wx_801q...]                                  │
│                                                          │
│ 飞书目标: [                                              ] │
└─────────────────────────────────────────────────────────┘
```

### 5.2 实现代码

```python
def _setup_settings_tab(self, parent):
    # ... 现有代码 ...

    # 摘要推送设置
    ttk.Separator(settings_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
    ttk.Label(settings_frame, text="摘要推送设置", font=("", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))

    self.auto_send_var = tk.BooleanVar(value=config.get("auto_send", False))
    ttk.Checkbutton(settings_frame, text="启用摘要自动推送", variable=self.auto_send_var).pack(anchor=tk.W, pady=(0, 10))

    channel_frame = ttk.Frame(settings_frame)
    channel_frame.pack(fill=tk.X, pady=(0, 10))
    ttk.Label(channel_frame, text="推送渠道:").pack(side=tk.LEFT)

    self.send_channel_var = tk.StringVar(value=config.get("send_channel", "wechat"))
    ttk.Radiobutton(channel_frame, text="微信", variable=self.send_channel_var, value="wechat").pack(side=tk.LEFT, padx=10)
    ttk.Radiobutton(channel_frame, text="飞书", variable=self.send_channel_var, value="feishu").pack(side=tk.LEFT, padx=10)
    ttk.Radiobutton(channel_frame, text="两者", variable=self.send_channel_var, value="both").pack(side=tk.LEFT, padx=10)

    ttk.Label(settings_frame, text="微信目标账号:").pack(anchor=tk.W, pady=(0, 5))
    wechat_frame = ttk.Frame(settings_frame)
    wechat_frame.pack(fill=tk.X, pady=(0, 10))
    self.wechat_target_entry = ttk.Entry(wechat_frame, width=50)
    self.wechat_target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    self.wechat_target_entry.insert(0, config.get("wechat_target", ""))

    ttk.Label(settings_frame, text="飞书目标账号:").pack(anchor=tk.W, pady=(0, 5))
    feishu_frame = ttk.Frame(settings_frame)
    feishu_frame.pack(fill=tk.X, pady=(0, 20))
    self.feishu_target_entry = ttk.Entry(feishu_frame, width=50)
    self.feishu_target_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    self.feishu_target_entry.insert(0, config.get("feishu_target", ""))
```

### 5.3 保存逻辑

```python
def _save_settings(self):
    # ... 现有代码 ...
    
    auto_send = self.auto_send_var.get()
    send_channel = self.send_channel_var.get()
    wechat_target = self.wechat_target_entry.get().strip()
    feishu_target = self.feishu_target_entry.get().strip()

    config.set("auto_send", auto_send)
    config.set("send_channel", send_channel)
    config.set("wechat_target", wechat_target)
    config.set("feishu_target", feishu_target)

    self._set_status("设置已保存")
```

---

## 6. 发送指令示例

### 6.1 微信推送

**配置**：
```json
{
  "auto_send": true,
  "send_channel": "wechat",
  "wechat_target": "wx_...@im.wechat"
}
```

**生成的指令**：
```
处理视频任务 | BV号: BV1xxx | 发送者UID: 123456 (test_user) | 请使用 read 工具读取字幕文件，然后生成视频摘要并保存 | 字幕文件路径: C:\Users\...\Temp\BV1xxx_sub_xxx.txt | 请生成视频摘要并保存到 ~/.openclaw/workspace/bilibili-summaries/ 目录 | 格式: 日期/BV号.md | 【重要】处理完成后，通过微信发送摘要给用户，目标账号: wx_...@im.wechat
```

> 目标账号为空时不会附加 `，目标账号:` 部分，OpenClaw 默认使用 `self`。

### 6.2 飞书推送

**配置**：
```json
{
  "auto_send": true,
  "send_channel": "feishu",
  "feishu_target": "user@feishu"
}
```

**生成的指令**：
```
... | 【重要】处理完成后，通过飞书发送摘要给用户，目标账号: user@feishu
```

### 6.3 双渠道推送

**配置**：
```json
{
  "auto_send": true,
  "send_channel": "both",
  "wechat_target": "wx_...@im.wechat",
  "feishu_target": "user@feishu"
}
```

**生成的指令**：
```
... | 【重要】处理完成后，通过微信和飞书发送摘要给用户，微信目标账号: wx_...@im.wechat，飞书目标账号: user@feishu
```

---

## 7. 前置条件

### 7.1 OpenClaw 配置

| 条件 | 说明 |
|------|------|
| 微信插件 | OpenClaw 需要加载微信插件 |
| 飞书插件 | OpenClaw 需要加载飞书插件 |
| 账号配置 | 微信/飞书账号需要在 OpenClaw 中配置 |

### 7.2 验证方式

```bash
# 检查 OpenClaw 插件
openclaw plugin list

# 测试发送
openclaw agent --message "测试发送" --session-id test --json
```

---

## 8. 注意事项

### 8.1 发送失败处理

- 如果 OpenClaw 发送失败，会在日志中显示错误
- 不影响主流程，摘要仍会保存到数据库
- 用户可以手动重试

### 8.2 隐私考虑

- 推送目标账号存储在本地配置文件
- 建议使用加密存储（参见 Cookie 加密设计）

---

## 9. 测试用例

### 9.1 配置测试

```python
def test_auto_send_config():
    config.set("auto_send", True)
    config.set("send_channel", "wechat")
    
    assert config.get("auto_send") == True
    assert config.get("send_channel") == "wechat"
```

### 9.2 消息生成测试

```python
def test_build_message_with_send():
    config.set("auto_send", True)
    config.set("send_channel", "wechat")
    
    trigger = OpenClawTrigger()
    message = trigger._build_message("BV1xxx", "字幕内容", "123", "test_user")
    
    assert "通过微信发送摘要给用户" in message
```

---

## 10. 工作量

| 任务 | 时间 | 状态 |
|------|------|------|
| 配置项设计 | 10 分钟 | ✅ 完成 |
| 消息格式修改 | 20 分钟 | ✅ 完成 |
| GUI 设置界面 | 30 分钟 | ✅ 完成 |
| 测试 | 20 分钟 | ✅ 完成 |
| **总计** | **1.5 小时** | ✅ 已实现 |
