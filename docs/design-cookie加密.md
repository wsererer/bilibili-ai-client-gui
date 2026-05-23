# Cookie 加密设计文档

## 1. 概述

### 1.1 目标

将扫码登录获取的 Cookie 加密存放，避免明文存储。

### 1.2 背景

当前 Cookie 明文存储在两个位置：

| 文件 | 字段 | 格式 |
|------|------|------|
| `data/config.json` | `bili_auth` | 明文 |
| `data/login_cookie.txt` | 整个文件 | 明文 |

### 1.3 需求

- 不需要特别隐秘
- 简单加密即可
- 轻量级方案，无额外依赖

---

## 2. 加密方案选择

### 2.1 方案对比

| 方案 | 安全性 | 复杂度 | 依赖 | 推荐 |
|------|--------|--------|------|------|
| Base64 编码 | 低（可逆） | 极低 | 无 | ❌ |
| XOR + Base64 | 低-中 | 低 | 无 | ✅ |
| Fernet 对称加密 | 中-高 | 中 | cryptography | ❌ |
| AES-CBC | 高 | 高 | cryptography | ❌ |

### 2.2 选择：XOR + Base64

**理由**：
- 无额外依赖，纯 Python 实现
- 满足"不需要特别隐秘"的需求
- 实现简单，易于维护

---

## 3. 加密工具实现

### 3.1 新增文件

**`utils/crypto.py`**

```python
import base64
import secrets
from pathlib import Path
from utils.app_data import APP_DATA_DIR

KEY_FILE = APP_DATA_DIR / ".key"


def _get_key() -> str:
    """获取或创建加密密钥"""
    if KEY_FILE.exists():
        return KEY_FILE.read_text(encoding='utf-8').strip()
    else:
        key = secrets.token_hex(32)  # 64 字符的十六进制密钥
        KEY_FILE.write_text(key, encoding='utf-8')
        return key


def _xor_encrypt(text: str, key: str) -> bytes:
    """XOR 加密"""
    key_bytes = key.encode('utf-8')
    text_bytes = text.encode('utf-8')
    encrypted = bytearray()
    for i, byte in enumerate(text_bytes):
        encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
    return bytes(encrypted)


def encrypt(text: str) -> str:
    """加密并返回 base64 编码的密文"""
    key = _get_key()
    encrypted = _xor_encrypt(text, key)
    return base64.urlsafe_b64encode(encrypted).decode('utf-8')


def decrypt(encrypted_text: str) -> str:
    """解密 base64 编码的密文"""
    key = _get_key()
    encrypted = base64.urlsafe_b64decode(encrypted_text)
    decrypted = bytearray()
    key_bytes = key.encode('utf-8')
    for i, byte in enumerate(encrypted):
        decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
    return bytes(decrypted).decode('utf-8')


def is_encrypted(text: str) -> bool:
    """判断文本是否已加密"""
    return text.startswith("ENC:")


def encrypt_if_needed(text: str) -> str:
    """如果未加密则加密"""
    if is_encrypted(text):
        return text
    return f"ENC:{encrypt(text)}"


def decrypt_if_needed(text: str) -> str:
    """如果已加密则解密"""
    if is_encrypted(text):
        return decrypt(text[4:])  # 去掉 "ENC:" 前缀
    return text
```

---

## 4. 配置修改

### 4.1 config.py 修改

**修改 `_load_cookie_from_file` 方法**：

```python
def _load_cookie_from_file(self):
    from utils.crypto import decrypt_if_needed
    
    cookie_file = APP_DATA_DIR / "login_cookie.txt"
    if cookie_file.exists():
        try:
            cookie = cookie_file.read_text(encoding='utf-8').strip()
            if cookie:
                # 尝试解密
                cookie = decrypt_if_needed(cookie)
                if len(cookie) > 50 and "SESSDATA" in cookie:
                    if not self._config.get("bili_auth") or "SESSDATA" not in self._config.get("bili_auth", ""):
                        self._config["bili_auth"] = cookie
        except Exception:
            pass
```

**修改 `save` 方法**：

```python
def save(self):
    from utils.crypto import encrypt_if_needed
    
    # 保存到 JSON 时加密 cookie
    save_config = self._config.copy()
    if save_config.get("bili_auth"):
        save_config["bili_auth"] = encrypt_if_needed(save_config["bili_auth"])
    
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(save_config, f, ensure_ascii=False, indent=2)
```

**修改 `_load` 方法**：

```python
def _load(self):
    from utils.crypto import decrypt_if_needed
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self._config = json.load(f)
            # 解密 cookie
            if self._config.get("bili_auth"):
                self._config["bili_auth"] = decrypt_if_needed(self._config["bili_auth"])
        except Exception:
            self._config = DEFAULT_CONFIG.copy()
    else:
        self._config = DEFAULT_CONFIG.copy()
    for key, value in DEFAULT_CONFIG.items():
        if key not in self._config:
            self._config[key] = value
    self._load_cookie_from_file()
```

---

## 5. 登录保存修改

### 5.1 bilibili_login.py 修改

**修改 `save_cookie` 方法**：

```python
def save_cookie():
    from utils.crypto import encrypt
    
    cookie = LOGIN_DATA.get("cookie")
    logger.info(f"save_cookie called, cookie present: {bool(cookie)}")
    if cookie:
        try:
            config.set("bili_auth", cookie)
            config.set("bili_login_time", str(int(time.time())))

            cookie_file = get_config_path()
            logger.info(f"Saving cookie to: {cookie_file}")
            # 加密存储
            encrypted_cookie = f"ENC:{encrypt(cookie)}"
            cookie_file.write_text(encrypted_cookie, encoding='utf-8')
            logger.info(f"Cookie saved successfully, file exists: {cookie_file.exists()}")

            return True
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
    return False
```

---

## 6. GUI 显示修改

### 6.1 gui/main_window.py 修改

**修改设置界面显示**：

```python
def _setup_settings_tab(self, parent):
    # ... 现有代码 ...
    
    # 显示 Cookie 状态（不显示明文）
    cookie = config.get("bili_auth", "")
    if cookie:
        display_text = f"已登录 (Cookie 长度: {len(cookie)})"
    else:
        display_text = "未登录"
    
    self.auth_entry = tk.Text(auth_frame, height=4, width=50, font=("Consolas", 9), state="disabled")
    self.auth_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
    self.auth_entry.insert("1.0", display_text)
```

---

## 7. 数据迁移

### 7.1 自动迁移逻辑

在 `_load` 方法中添加迁移逻辑：

```python
def _migrate_plaintext_cookie(self):
    """迁移明文 Cookie 为加密格式"""
    from utils.crypto import encrypt, is_encrypted
    
    cookie = self._config.get("bili_auth", "")
    if cookie and not is_encrypted(cookie):
        # 标记为已加密
        encrypted = f"ENC:{encrypt(cookie)}"
        self._config["bili_auth"] = encrypted
        self.save()
        
        # 同时更新 cookie 文件
        cookie_file = APP_DATA_DIR / "login_cookie.txt"
        if cookie_file.exists():
            file_content = cookie_file.read_text(encoding='utf-8').strip()
            if file_content and not is_encrypted(file_content):
                cookie_file.write_text(encrypted, encoding='utf-8')
```

在 `_load` 方法末尾调用：

```python
def _load(self):
    # ... 现有代码 ...
    self._load_cookie_from_file()
    self._migrate_plaintext_cookie()  # 添加这行
```

---

## 8. 存储格式

### 8.1 加密前

**config.json**：
```json
{
  "bili_auth": "SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx"
}
```

**login_cookie.txt**：
```
SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx
```

### 8.2 加密后

**config.json**：
```json
{
  "bili_auth": "ENC:Z0FBQUFBQm..."
}
```

**login_cookie.txt**：
```
ENC:Z0FBQUFBQm...
```

### 8.3 标记说明

- `ENC:` 前缀表示已加密
- 方便区分明文和密文
- 支持向后兼容（无前缀视为明文）

---

## 9. 安全性分析

### 9.1 XOR 加密特点

| 特点 | 说明 |
|------|------|
| 密钥长度 | 64 字符（256 位） |
| 加密方式 | 逐字节 XOR |
| 编码方式 | Base64 URL-safe |
| 密钥存储 | `data/.key` 文件 |

### 9.2 安全性评估

| 攻击方式 | 防护能力 |
|----------|----------|
| 明文泄露 | ✅ 有效防止 |
| 简单逆向 | ⚠️ 有限防护 |
| 专业破解 | ❌ 无法防护 |

### 9.3 适用场景

- ✅ 防止意外泄露
- ✅ 防止简单窥探
- ❌ 不适用于高安全需求

---

## 10. 文件修改清单

### 10.1 新增文件

| 文件 | 说明 |
|------|------|
| `utils/crypto.py` | 加密工具模块 |

### 10.2 修改文件

| 文件 | 修改内容 |
|------|----------|
| `config.py` | 加载解密、保存加密、迁移逻辑 |
| `bilibili_login.py` | 保存时加密 |
| `gui/main_window.py` | 显示时隐藏明文 |

---

## 11. 测试用例

### 11.1 加密解密测试

```python
def test_encrypt_decrypt():
    from utils.crypto import encrypt, decrypt
    
    original = "SESSDATA=xxx; bili_jct=xxx; DedeUserID=xxx"
    encrypted = encrypt(original)
    decrypted = decrypt(encrypted)
    
    assert encrypted != original
    assert decrypted == original

def test_encryption_marker():
    from utils.crypto import is_encrypted, encrypt_if_needed, decrypt_if_needed
    
    text = "SESSDATA=xxx"
    encrypted = encrypt_if_needed(text)
    
    assert is_encrypted(encrypted)
    assert not is_encrypted(text)
    assert decrypt_if_needed(encrypted) == text

def test_double_encryption():
    from utils.crypto import encrypt_if_needed
    
    text = "SESSDATA=xxx"
    encrypted1 = encrypt_if_needed(text)
    encrypted2 = encrypt_if_needed(encrypted1)
    
    # 不会重复加密
    assert encrypted1 == encrypted2
```

### 11.2 配置迁移测试

```python
def test_config_migration():
    # 模拟明文配置
    config = Config()
    config._config["bili_auth"] = "SESSDATA=xxx; bili_jct=xxx"
    config._migrate_plaintext_cookie()
    
    # 验证已加密
    assert config._config["bili_auth"].startswith("ENC:")
```

---

## 12. 工作量估算

| 任务 | 时间 |
|------|------|
| 创建加密工具 | 20 分钟 |
| 修改 config.py | 20 分钟 |
| 修改 bilibili_login.py | 10 分钟 |
| 修改 gui/main_window.py | 10 分钟 |
| 测试 | 30 分钟 |
| **总计** | **1.5 小时** |
