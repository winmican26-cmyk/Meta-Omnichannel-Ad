import os
import sqlite3
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from app.utils.encryption import decrypt_token, encrypt_token

DB_PATH = os.getenv("CCCO_DB_PATH", "campaigns.db")


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ccco_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adset_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                event TEXT NOT NULL,
                pixel_id TEXT NOT NULL,
                application_id TEXT NOT NULL,
                web_url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'PAUSED'
            )
            """
        )
        _ensure_column(conn, "ccco_campaigns", "session_id", "TEXT")
        _ensure_column(conn, "ccco_campaigns", "ad_account_id", "TEXT")
        _ensure_column(conn, "ccco_campaigns", "android_deeplink", "TEXT")
        _ensure_column(conn, "ccco_campaigns", "ios_deeplink", "TEXT")
        _ensure_column(conn, "ccco_campaigns", "daily_budget", "INTEGER")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ccco_campaigns_owner ON ccco_campaigns(session_id, ad_account_id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                access_token TEXT NOT NULL,
                ad_account_id TEXT,
                ad_accounts_json TEXT,
                user_id TEXT,
                user_name TEXT,
                user_email TEXT,
                subscription_tier TEXT DEFAULT 'free',
                credits_balance INTEGER DEFAULT 150,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        _ensure_column(conn, "sessions", "user_email", "TEXT")
        _ensure_column(conn, "sessions", "subscription_tier", "TEXT DEFAULT 'free'")
        _ensure_column(conn, "sessions", "credits_balance", "INTEGER DEFAULT 150")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS campaign_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adset_id TEXT NOT NULL,
                date TEXT NOT NULL,
                conversions_web INTEGER DEFAULT 0,
                conversions_app INTEGER DEFAULT 0,
                spend REAL DEFAULT 0,
                cpa REAL DEFAULT 0,
                channel_split_web REAL DEFAULT 0,
                channel_split_app REAL DEFAULT 0,
                UNIQUE(adset_id, date),
                FOREIGN KEY (adset_id) REFERENCES ccco_campaigns(adset_id)
            )
            """
        )
        _ensure_column(conn, "campaign_insights", "session_id", "TEXT")
        _ensure_column(conn, "campaign_insights", "ad_account_id", "TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_campaign_insights_owner ON campaign_insights(session_id, ad_account_id, date)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS campaign_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                session_id TEXT NOT NULL,
                original_adset_id TEXT,
                config TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS optimizer_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                ad_account_id TEXT,
                campaign_name TEXT,
                event TEXT,
                optimizer TEXT NOT NULL,
                request_json TEXT NOT NULL,
                suggestion_json TEXT NOT NULL,
                used_fallback INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_optimizer_runs_owner ON optimizer_runs(session_id, ad_account_id, created_at)"
        )
        conn.commit()


def _ensure_column(
    conn: sqlite3.Connection, table: str, column: str, definition: str
) -> None:
    existing = {
        row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def save_ccco_campaign(
    *,
    adset_id: str,
    name: str,
    event: str,
    pixel_id: str,
    application_id: str,
    web_url: str,
    status: str = "PAUSED",
    session_id: str | None = None,
    ad_account_id: str | None = None,
    android_deeplink: str | None = None,
    ios_deeplink: str | None = None,
    daily_budget: int | None = None,
) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO ccco_campaigns
            (adset_id, name, event, pixel_id, application_id, web_url, status,
             session_id, ad_account_id, android_deeplink, ios_deeplink, daily_budget)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                adset_id,
                name,
                event,
                pixel_id,
                application_id,
                web_url,
                status,
                session_id,
                ad_account_id,
                android_deeplink,
                ios_deeplink,
                daily_budget,
            ),
        )
        conn.commit()


def save_session(
    *,
    session_id: str,
    access_token: str,
    ad_account_id: str | None,
    ad_accounts: list[dict],
    user_id: str | None = None,
    user_name: str | None = None,
    user_email: str | None = None,
    subscription_tier: str = "free",
    credits_balance: int = 150,
) -> None:
    init_db()
    ad_accounts_json = json.dumps(ad_accounts) if ad_accounts else None
    encrypted_token = encrypt_token(access_token)
    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO sessions
            (session_id, access_token, ad_account_id, ad_accounts_json, user_id, user_name, user_email, subscription_tier, credits_balance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                encrypted_token,
                ad_account_id,
                ad_accounts_json,
                user_id,
                user_name,
                user_email,
                subscription_tier,
                credits_balance,
            ),
        )
        conn.commit()


def get_session_record(session_id: str) -> dict | None:
    init_db()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not row:
            return None

    session = dict(row)
    session["access_token"] = decrypt_token(session.get("access_token"))
    session["ad_accounts"] = (
        json.loads(session["ad_accounts_json"]) if session["ad_accounts_json"] else []
    )
    session.pop("ad_accounts_json", None)
    return session


def update_session_ad_account(session_id: str, ad_account_id: str) -> None:
    init_db()
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET ad_account_id = ? WHERE session_id = ?",
            (ad_account_id, session_id),
        )
        conn.commit()


def update_session_subscription(session_id: str, subscription_tier: str) -> None:
    init_db()
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET subscription_tier = ? WHERE session_id = ?",
            (subscription_tier, session_id),
        )
        conn.commit()


def update_session_credits(session_id: str, credits_balance: int) -> None:
    init_db()
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET credits_balance = ? WHERE session_id = ?",
            (credits_balance, session_id),
        )
        conn.commit()


def create_email_user(*, email: str, password_hash: str, full_name: str | None) -> int:
    init_db()
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?)",
            (email.lower(), password_hash, full_name),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_email_user(email: str) -> dict | None:
    init_db()
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, full_name, created_at FROM users WHERE email = ?",
            (email.lower(),),
        ).fetchone()
    return dict(row) if row else None


def list_owned_ccco_campaigns(
    *,
    session_id: str | None,
    ad_account_id: str | None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    init_db()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM ccco_campaigns
            WHERE session_id = ? AND ad_account_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (session_id, ad_account_id, limit, offset),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_ccco_campaign(
    *,
    adset_id: str,
    session_id: str,
    ad_account_id: str,
) -> bool:
    """Delete a CCCO campaign and its associated insights (cascade).

    Returns ``True`` if a campaign was actually deleted, ``False`` if nothing
    matched (prevents silent no-ops).
    """
    init_db()
    with get_db() as conn:
        # Delete insights first (child rows) to respect the FK relationship
        conn.execute(
            "DELETE FROM campaign_insights WHERE adset_id = ? AND session_id = ? AND ad_account_id = ?",
            (adset_id, session_id, ad_account_id),
        )
        cursor = conn.execute(
            "DELETE FROM ccco_campaigns WHERE adset_id = ? AND session_id = ? AND ad_account_id = ?",
            (adset_id, session_id, ad_account_id),
        )
        conn.commit()
    return cursor.rowcount > 0


def record_optimizer_run(
    *,
    session_id: str | None,
    ad_account_id: str | None,
    campaign_name: str,
    event: str,
    optimizer: str,
    request_json: str,
    suggestion_json: str,
    used_fallback: bool = False,
) -> None:
    init_db()
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO optimizer_runs
            (session_id, ad_account_id, campaign_name, event, optimizer,
             request_json, suggestion_json, used_fallback)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                ad_account_id,
                campaign_name,
                event,
                optimizer,
                request_json,
                suggestion_json,
                1 if used_fallback else 0,
            ),
        )
        conn.commit()
