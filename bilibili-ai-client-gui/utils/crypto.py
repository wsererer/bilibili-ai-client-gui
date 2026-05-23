import base64
import secrets
from utils.app_data import APP_DATA_DIR

KEY_FILE = APP_DATA_DIR / ".key"

def _get_key() -> str:
    """Get or create encryption key"""
    if KEY_FILE.exists():
        return KEY_FILE.read_text(encoding='utf-8').strip()
    key = secrets.token_hex(32)
    KEY_FILE.write_text(key, encoding='utf-8')
    return key

def _xor_encrypt(text: str, key: str) -> bytes:
    """XOR encryption"""
    key_bytes = key.encode('utf-8')
    text_bytes = text.encode('utf-8')
    encrypted = bytearray()
    for i, byte in enumerate(text_bytes):
        encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
    return bytes(encrypted)

def encrypt(text: str) -> str:
    """Encrypt and return base64 encoded ciphertext"""
    if not text:
        return ""
    key = _get_key()
    encrypted = _xor_encrypt(text, key)
    return base64.urlsafe_b64encode(encrypted).decode('utf-8')

def decrypt(encrypted_text: str) -> str:
    """Decrypt base64 encoded ciphertext"""
    if not encrypted_text:
        return ""
    key = _get_key()
    encrypted = base64.urlsafe_b64decode(encrypted_text)
    decrypted = bytearray()
    key_bytes = key.encode('utf-8')
    for i, byte in enumerate(encrypted):
        decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
    return bytes(decrypted).decode('utf-8')

def is_encrypted(text: str) -> bool:
    """Check if text is encrypted"""
    return bool(text) and text.startswith("ENC:")

def encrypt_if_needed(text: str) -> str:
    """Encrypt if not already encrypted"""
    if is_encrypted(text):
        return text
    if not text:
        return ""
    return f"ENC:{encrypt(text)}"

def decrypt_if_needed(text: str) -> str:
    """Decrypt if encrypted"""
    if is_encrypted(text):
        return decrypt(text[4:])
    return text