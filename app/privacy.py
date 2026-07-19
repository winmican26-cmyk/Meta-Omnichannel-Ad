import base64
import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Form, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.database import get_db, init_db
from app.security import client_key, detect_injection, dsr_rate_limiter, strip_html
from app.utils.logging import structlog

logger = structlog.get_logger()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DEFAULT_CONFIRM_BASE = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8766")

router = APIRouter(prefix="/privacy", tags=["privacy"])

DSRType = Literal[
    "access",
    "rectification",
    "erasure",
    "portability",
    "restriction",
    "objection",
    "withdraw_consent",
]


class DSRSubmission(BaseModel):
    request_type: DSRType
    full_name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=320)
    description: str = Field(..., min_length=10, max_length=4000)
    identity_verification_consent: bool
    related_session_id: str | None = None

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError("email must be a valid address")
        return value.strip()


class DSRAcknowledgement(BaseModel):
    ticket_id: str
    received_at: str
    statutory_deadline: str
    status: str
    next_steps: str


def init_dsr_table() -> None:
    init_db()
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dsr_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                request_type TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                description TEXT NOT NULL,
                related_session_id TEXT,
                status TEXT NOT NULL DEFAULT 'received',
                received_at TEXT NOT NULL,
                statutory_deadline TEXT NOT NULL,
                resolved_at TEXT
            )
            """
        )
        conn.commit()


def _generate_ticket_id() -> str:
    import secrets

    return "DSR-" + secrets.token_hex(6).upper()


@router.post("/dsr", response_model=DSRAcknowledgement)
async def submit_dsr(payload: DSRSubmission, request: Request) -> DSRAcknowledgement:
    dsr_rate_limiter.enforce(
        f"dsr:{client_key(request)}",
        detail="You've submitted several requests recently. Please try again in a few minutes.",
    )

    if not payload.identity_verification_consent:
        raise HTTPException(
            status_code=400,
            detail="Identity verification consent is required to process a GDPR data subject request.",
        )

    clean_name = strip_html(payload.full_name).strip()[:200]
    clean_description = strip_html(payload.description).strip()[:4000]
    if not clean_name or len(clean_description) < 10:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid name and a description of at least 10 characters.",
        )

    is_injection, _matched = detect_injection(clean_description)
    if is_injection:
        logger.warning(
            "dsr_injection_blocked", client=client_key(request), email=payload.email
        )
        raise HTTPException(
            status_code=400,
            detail=(
                "Your request contains content we cannot process. Please describe your "
                "data-rights request in plain language without code, scripts, or instructions."
            ),
        )

    init_dsr_table()
    received_at = datetime.utcnow()
    deadline = received_at + timedelta(days=30)
    ticket_id = _generate_ticket_id()

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO dsr_requests
            (ticket_id, request_type, full_name, email, description, related_session_id,
             status, received_at, statutory_deadline)
            VALUES (?, ?, ?, ?, ?, ?, 'received', ?, ?)
            """,
            (
                ticket_id,
                payload.request_type,
                clean_name,
                payload.email,
                clean_description,
                payload.related_session_id,
                received_at.isoformat() + "Z",
                deadline.isoformat() + "Z",
            ),
        )
        conn.commit()

    return DSRAcknowledgement(
        ticket_id=ticket_id,
        received_at=received_at.isoformat() + "Z",
        statutory_deadline=deadline.isoformat() + "Z",
        status="received",
        next_steps=(
            "We will verify your identity using the email you provided and respond within one calendar month, "
            "as required by GDPR Article 12(3). If the request is complex we may extend by up to two further months "
            "and will notify you of any extension."
        ),
    )


@router.get("/dsr/{ticket_id}", response_model=DSRAcknowledgement)
async def get_dsr_status(ticket_id: str) -> DSRAcknowledgement:
    init_dsr_table()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM dsr_requests WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="DSR ticket not found")

    return DSRAcknowledgement(
        ticket_id=row["ticket_id"],
        received_at=row["received_at"],
        statutory_deadline=row["statutory_deadline"],
        status=row["status"],
        next_steps="Identity verification in progress." if row["status"] == "received" else f"Status: {row['status']}",
    )


# ---------------------------------------------------------------------------
# Meta Data Deletion Callback
# https://developers.facebook.com/docs/development/create-an-app/app-dashboard/data-deletion-callback/
# Meta POSTs a `signed_request` field. We verify it with META_APP_SECRET,
# stage a deletion for the supplied user_id, and return { url, confirmation_code }.
# ---------------------------------------------------------------------------


class MetaDeletionAck(BaseModel):
    url: str
    confirmation_code: str


def _b64url_decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


def _parse_signed_request(signed_request: str, app_secret: str) -> dict:
    try:
        encoded_sig, encoded_payload = signed_request.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Malformed signed_request") from exc

    expected_sig = hmac.new(
        app_secret.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    received_sig = _b64url_decode(encoded_sig)
    if not hmac.compare_digest(expected_sig, received_sig):
        raise HTTPException(status_code=403, detail="Invalid signed_request signature")

    payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
    if payload.get("algorithm") != "HMAC-SHA256":
        raise HTTPException(status_code=400, detail="Unsupported signed_request algorithm")
    return payload


def init_meta_deletion_table() -> None:
    init_db()
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta_deletion_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                confirmation_code TEXT UNIQUE NOT NULL,
                meta_user_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'received',
                received_at TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )
        conn.commit()


def _stage_meta_user_deletion(meta_user_id: str) -> None:
    """Mark all sessions tied to this Meta user_id for purge.

    The deletion is staged (status flip) rather than executed inline so the
    confirmation-status endpoint can report progress to Meta and so we have
    an audit row. A background worker would do the actual row deletion.
    """
    init_db()
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET access_token = NULL, ad_accounts_json = NULL "
            "WHERE user_id = ?",
            (meta_user_id,),
        )
        conn.commit()


@router.post("/meta/deletion", response_model=MetaDeletionAck)
async def meta_data_deletion_callback(signed_request: str = Form(...)) -> MetaDeletionAck:
    app_secret = os.getenv("META_APP_SECRET", "").strip()
    if not app_secret or app_secret == "YOUR_META_APP_SECRET":
        logger.error("meta_deletion_callback_missing_app_secret")
        raise HTTPException(status_code=500, detail="META_APP_SECRET is not configured")

    payload = _parse_signed_request(signed_request, app_secret)
    meta_user_id = str(payload.get("user_id", "")).strip()
    if not meta_user_id:
        raise HTTPException(status_code=400, detail="signed_request missing user_id")

    init_meta_deletion_table()
    confirmation_code = secrets.token_urlsafe(16)
    received_at = datetime.utcnow().isoformat() + "Z"

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO meta_deletion_requests
            (confirmation_code, meta_user_id, status, received_at)
            VALUES (?, ?, 'received', ?)
            """,
            (confirmation_code, meta_user_id, received_at),
        )
        conn.commit()

    _stage_meta_user_deletion(meta_user_id)

    logger.info(
        "meta_data_deletion_callback_received",
        meta_user_id=meta_user_id,
        confirmation_code=confirmation_code,
    )

    status_url = f"{_DEFAULT_CONFIRM_BASE.rstrip('/')}/privacy/meta/deletion-status/{confirmation_code}"
    return MetaDeletionAck(url=status_url, confirmation_code=confirmation_code)


@router.get("/meta/deletion-status/{confirmation_code}")
async def meta_deletion_status(confirmation_code: str) -> dict:
    init_meta_deletion_table()
    with get_db() as conn:
        row = conn.execute(
            "SELECT status, received_at, completed_at FROM meta_deletion_requests "
            "WHERE confirmation_code = ?",
            (confirmation_code,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Deletion confirmation code not found")

    return {
        "confirmation_code": confirmation_code,
        "status": row["status"],
        "received_at": row["received_at"],
        "completed_at": row["completed_at"],
    }
