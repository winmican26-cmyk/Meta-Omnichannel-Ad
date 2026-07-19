"""Encrypted API key storage for AI providers.

Keys are stored in the ``api_keys`` database table and encrypted at rest
using the same Fernet-based encryption used for OAuth tokens (see
:mod:`app.utils.encryption`).

If no ``TOKEN_ENCRYPTION_KEY`` environment variable is set, a warning is
logged but keys are still stored (plaintext-prefixed) so the system remains
functional for development.
"""

from __future__ import annotations

import sqlite3

from app.database import DB_PATH, get_db
from app.utils.encryption import encrypt_token, decrypt_token
from app.utils.logging import structlog

logger = structlog.get_logger()


def _ensure_table() -> None:
    """Create the ``api_keys`` table if it doesn't exist."""
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                provider TEXT PRIMARY KEY,
                encrypted_key TEXT NOT NULL,
                label TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def save_key(provider: str, key: str, label: str | None = None) -> None:
    """Encrypt and store a provider API key.

    Args:
        provider: Provider identifier (e.g. ``"claude"``, ``"openai"``).
        key: The raw API key string.
        label: Optional human-readable label (e.g. ``"Production"``).
    """
    _ensure_table()
    encrypted = encrypt_token(key)
    if encrypted is None:
        logger.error("key_encryption_failed", provider=provider)
        raise ValueError("Failed to encrypt API key")

    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO api_keys (provider, encrypted_key, label, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (provider, encrypted, label),
        )
        conn.commit()
    logger.info("key_saved", provider=provider)


def get_key(provider: str) -> str | None:
    """Retrieve and decrypt a provider API key.

    Returns ``None`` if no key is stored for *provider*.
    """
    _ensure_table()
    with get_db() as conn:
        row = conn.execute(
            "SELECT encrypted_key FROM api_keys WHERE provider = ?",
            (provider,),
        ).fetchone()
    if row is None:
        return None
    return decrypt_token(row["encrypted_key"])


def has_key(provider: str) -> bool:
    """Check whether a key exists for *provider* (without decrypting)."""
    _ensure_table()
    with get_db() as conn:
        row = conn.execute(
            "SELECT 1 FROM api_keys WHERE provider = ?", (provider,)
        ).fetchone()
    return row is not None


def delete_key(provider: str) -> bool:
    """Remove a stored API key.

    Returns ``True`` if a key was actually deleted.
    """
    _ensure_table()
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM api_keys WHERE provider = ?", (provider,))
        conn.commit()
    return cursor.rowcount > 0


def list_keys() -> list[dict]:
    """Return all stored provider keys (metadata only — no plaintext)."""
    _ensure_table()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT provider, label, created_at, updated_at FROM api_keys ORDER BY provider"
        ).fetchall()
    return [dict(row) for row in rows]


def validate_and_save_key(provider: str, key: str) -> tuple[bool, str]:
    """Validate an API key with the provider, then save if valid.

    Uses the provider's ``validate_key`` method. If validation succeeds,
    the key is encrypted and persisted.

    Returns ``(success, message)``.
    """
    from app.ai_providers import get_provider

    provider_instance = get_provider(provider)
    if provider_instance is None:
        return False, f"Unknown provider: {provider}"

    if not provider_instance.validate_key(key):
        return False, f"Invalid API key for {provider_instance.display_name()}"

    save_key(provider, key)
    return True, f"{provider_instance.display_name()} key saved and verified"
