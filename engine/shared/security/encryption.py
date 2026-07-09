import base64
import hashlib
import logging
from cryptography.fernet import Fernet
from engine.shared.config.settings import get_settings

logger = logging.getLogger(__name__)

def _get_fernet_key() -> str:
    settings = get_settings()
    raw_key = getattr(settings, "secrets_encryption_key", "") or ""
    raw_key = raw_key.strip()
    
    if not raw_key:
        logger.warning(
            "[Security] SECRETS_ENCRYPTION_KEY is not configured in settings. "
            "Values will be processed in PLAINTEXT. This is insecure for production!"
        )
        return ""
    
    # Derive a valid 32-byte Fernet key from the user-provided string using SHA-256
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(key_hash).decode("utf-8")

def encrypt_value(plain_text: str) -> str:
    if not plain_text:
        return ""
    
    fernet_key = _get_fernet_key()
    if not fernet_key:
        return plain_text
        
    try:
        cipher_suite = Fernet(fernet_key.encode("utf-8"))
        encrypted_bytes = cipher_suite.encrypt(plain_text.encode("utf-8"))
        return encrypted_bytes.decode("utf-8")
    except Exception as e:
        logger.error(f"[Security] Encryption failed: {e}")
        raise ValueError(f"Encryption failed: {e}")

def decrypt_value(cipher_text: str) -> str:
    if not cipher_text:
        return ""
        
    fernet_key = _get_fernet_key()
    if not fernet_key:
        return cipher_text
        
    if not cipher_text.startswith("gAAAA"):
        logger.debug("[Security] Value is not encrypted (does not start with gAAAA), returning as-is.")
        return cipher_text
        
    try:
        cipher_suite = Fernet(fernet_key.encode("utf-8"))
        decrypted_bytes = cipher_suite.decrypt(cipher_text.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        logger.warning(f"[Security] Decryption failed (treating as plaintext): {e}")
        return cipher_text
