import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

from app.utils.logging import structlog

logger = structlog.get_logger()

_PLAINTEXT_PREFIX = "pt:"
_CIPHERTEXT_PREFIX = "fr:"


def _load_fernet() -> Fernet | None:
    raw = os.getenv("TOKEN_ENCRYPTION_KEY", "").strip()
    if not raw:
        return None
    try:
        return Fernet(raw.encode("utf-8"))
    except (ValueError, TypeError):
        derived = base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())
        logger.warning("token_encryption_key_derived_from_passphrase")
        return Fernet(derived)


_FERNET = _load_fernet()


def encrypt_token(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    if _FERNET is None:
        logger.warning("token_encryption_disabled_storing_plaintext")
        return _PLAINTEXT_PREFIX + plaintext
    return _CIPHERTEXT_PREFIX + _FERNET.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(stored: str | None) -> str | None:
    if stored is None:
        return None
    if stored.startswith(_CIPHERTEXT_PREFIX):
        if _FERNET is None:
            logger.error("token_encryption_key_missing_cannot_decrypt")
            return None
        try:
            return _FERNET.decrypt(stored[len(_CIPHERTEXT_PREFIX):].encode("utf-8")).decode("utf-8")
        except InvalidToken:
            logger.error("token_decryption_failed_invalid_token_or_wrong_key")
            return None
    if stored.startswith(_PLAINTEXT_PREFIX):
        return stored[len(_PLAINTEXT_PREFIX):]
    return stored


def encryption_enabled() -> bool:
    return _FERNET is not None
