"""Password encryption for IMAP/SMTP credentials using Fernet."""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import get_settings


def _get_fernet() -> Fernet:
    """Derive a Fernet key from SECRET_KEY."""
    settings = get_settings()
    # Derive 32-byte key from SECRET_KEY using SHA-256
    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)


def encrypt_password(plain: str) -> str:
    """Encrypt a plaintext password. Returns base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plain.encode()).decode()


def decrypt_password(cipher: str) -> str:
    """Decrypt an encrypted password. Returns plaintext."""
    f = _get_fernet()
    return f.decrypt(cipher.encode()).decode()
