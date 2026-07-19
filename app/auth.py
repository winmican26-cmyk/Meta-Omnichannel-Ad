import hashlib
import hmac
import os
import re
import secrets
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, field_validator

from app.database import (
    create_email_user,
    get_email_user,
    get_session_record,
    init_db,
    save_session,
    update_session_ad_account,
)
from app.security import auth_rate_limiter, client_key
from app.utils.logging import structlog

logger = structlog.get_logger()

router = APIRouter(tags=["auth"])

META_API_VERSION = os.getenv("META_API_VERSION", "v25.0")
META_APP_ID = os.getenv("META_APP_ID", "YOUR_META_APP_ID")
META_APP_SECRET = os.getenv("META_APP_SECRET", "YOUR_META_APP_SECRET")
REDIRECT_URI = os.getenv("META_REDIRECT_URI", "http://localhost:8765/auth/callback")
# Legacy scope-based OAuth (used when no Login-for-Business config_id is set)
META_SCOPES = os.getenv(
    "META_SCOPES",
    "ads_management,ads_read,business_management,pages_show_list,pages_read_engagement,read_insights",
)
# Facebook Login for Business — preferred for SaaS. Create the configuration at
# https://developers.facebook.com/apps/<APP_ID>/fb-login-business/ and paste the
# resulting configuration ID here. When set, the engine uses config_id instead
# of scope so consent is business-context aware and granted assets are listed
# in Business Manager.
META_LOGIN_CONFIG_ID = os.getenv("META_LOGIN_CONFIG_ID", "").strip()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_KEYLEN = 32

active_sessions: dict[str, dict[str, Any]] = {}
oauth_states: set[str] = set()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_KEYLEN,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(bytes.fromhex(digest_hex)),
        )
        return hmac.compare_digest(candidate, bytes.fromhex(digest_hex))
    except (ValueError, AttributeError):
        return False


class AuthCallbackResponse(BaseModel):
    session_id: str
    ad_accounts: list[dict[str, Any]]


class AuthSessionResponse(BaseModel):
    ad_account_id: str | None = None
    ad_accounts: list[dict[str, Any]]
    user_id: str | None = None


class SwitchAccountResponse(BaseModel):
    status: str
    ad_account_id: str


def get_session(session_id: str | None) -> dict[str, Any]:
    if not session_id:
        raise HTTPException(status_code=401, detail="No active session")
    if session_id in active_sessions:
        return active_sessions[session_id]

    session = get_session_record(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="No active session")

    active_sessions[session_id] = session
    return session


def get_session_from_request(request: Request) -> dict[str, Any]:
    return get_session(request.headers.get("X-Session-ID"))


@router.get("/auth/login")
async def login() -> RedirectResponse:
    if META_APP_ID == "YOUR_META_APP_ID":
        raise HTTPException(status_code=500, detail="META_APP_ID is not configured")

    state = secrets.token_urlsafe(32)
    oauth_states.add(state)

    params = [
        f"client_id={META_APP_ID}",
        f"redirect_uri={REDIRECT_URI}",
        f"state={state}",
        "response_type=code",
    ]
    if META_LOGIN_CONFIG_ID:
        # Facebook Login for Business — preferred path. The configuration
        # itself names the permissions, so we do not send `scope`.
        params.append(f"config_id={META_LOGIN_CONFIG_ID}")
        logger.info("meta_oauth_login_for_business", config_id=META_LOGIN_CONFIG_ID)
    else:
        # Legacy scope-based fallback. Works for development before the
        # Login-for-Business configuration is created in the App Dashboard.
        params.append(f"scope={META_SCOPES}")
        logger.info("meta_oauth_legacy_scope_flow", scopes=META_SCOPES)

    url = f"https://www.facebook.com/{META_API_VERSION}/dialog/oauth?" + "&".join(params)
    return RedirectResponse(url)


class SetupStatus(BaseModel):
    ready_for_oauth: bool
    using_login_for_business: bool
    items: list[dict[str, Any]]


@router.get("/auth/setup-status", response_model=SetupStatus)
async def setup_status() -> SetupStatus:
    """Reports which Meta App Dashboard configuration items are still missing.

    Helps you complete steps 2, 3, 4, 5 from the setup checklist without
    digging through .env or guessing whether the OAuth URL will work.
    """
    items: list[dict[str, Any]] = []

    app_id_ok = META_APP_ID and META_APP_ID != "YOUR_META_APP_ID"
    items.append({
        "step": 2,
        "name": "META_APP_ID configured",
        "ok": app_id_ok,
        "dashboard_url": f"https://developers.facebook.com/apps/{META_APP_ID}/settings/basic/" if app_id_ok else "https://developers.facebook.com/apps/",
        "hint": "Set META_APP_ID in .env from App Dashboard → Settings → Basic.",
    })

    secret_ok = META_APP_SECRET and META_APP_SECRET != "YOUR_META_APP_SECRET"
    items.append({
        "step": 2,
        "name": "META_APP_SECRET configured",
        "ok": secret_ok,
        "dashboard_url": f"https://developers.facebook.com/apps/{META_APP_ID}/settings/basic/" if app_id_ok else "https://developers.facebook.com/apps/",
        "hint": "Click 'Show' on App Secret in App Dashboard → Settings → Basic and paste it into META_APP_SECRET.",
    })

    items.append({
        "step": 3,
        "name": "Marketing API product enabled (assumed when App ID is set)",
        "ok": app_id_ok,
        "dashboard_url": f"https://developers.facebook.com/apps/{META_APP_ID}/add/" if app_id_ok else "https://developers.facebook.com/apps/",
        "hint": "Add the Marketing API product to your app from App Dashboard → Add Products.",
    })

    config_id_ok = bool(META_LOGIN_CONFIG_ID)
    items.append({
        "step": 4,
        "name": "Facebook Login for Business config_id configured",
        "ok": config_id_ok,
        "dashboard_url": f"https://developers.facebook.com/apps/{META_APP_ID}/fb-login-business/" if app_id_ok else "https://developers.facebook.com/apps/",
        "hint": "Create a Login Configuration with the required permissions, copy its ID into META_LOGIN_CONFIG_ID. If empty the engine falls back to scope-based OAuth.",
    })

    redirect_ok = REDIRECT_URI.startswith("http")
    items.append({
        "step": 5,
        "name": f"OAuth redirect URI ({REDIRECT_URI})",
        "ok": redirect_ok,
        "dashboard_url": f"https://developers.facebook.com/apps/{META_APP_ID}/fb-login-business/settings/" if app_id_ok else "https://developers.facebook.com/apps/",
        "hint": "Add this redirect_uri to 'Valid OAuth Redirect URIs' in Facebook Login for Business → Settings.",
    })

    return SetupStatus(
        ready_for_oauth=app_id_ok and secret_ok and redirect_ok,
        using_login_for_business=config_id_ok,
        items=items,
    )


@router.get("/auth/callback", response_model=AuthCallbackResponse)
async def callback(code: str, state: str) -> AuthCallbackResponse:
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    oauth_states.remove(state)

    async with httpx.AsyncClient(timeout=30) as client:
        token_resp = await client.get(
            f"https://graph.facebook.com/{META_API_VERSION}/oauth/access_token",
            params={
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "redirect_uri": REDIRECT_URI,
                "code": code,
            },
        )
        data = token_resp.json()
        if "access_token" not in data:
            logger.warning("meta_oauth_token_exchange_failed", response=data)
            raise HTTPException(status_code=400, detail=f"Token error: {data}")

        short_lived = data["access_token"]
        long_resp = await client.get(
            f"https://graph.facebook.com/{META_API_VERSION}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "fb_exchange_token": short_lived,
            },
        )
        long_data = long_resp.json()
        access_token = long_data.get("access_token")
        if not access_token:
            logger.warning("meta_oauth_long_lived_exchange_failed", response=long_data)
            raise HTTPException(status_code=400, detail="Failed to get long-lived token")

        accounts_resp = await client.get(
            f"https://graph.facebook.com/{META_API_VERSION}/me/adaccounts",
            params={"access_token": access_token, "fields": "id,name,account_id,account_status"},
        )
        accounts = accounts_resp.json().get("data", [])

        me_resp = await client.get(
            f"https://graph.facebook.com/{META_API_VERSION}/me",
            params={"access_token": access_token, "fields": "id,name"},
        )
        me = me_resp.json()

    session_id = secrets.token_urlsafe(32)
    session = {
        "access_token": access_token,
        "ad_account_id": accounts[0]["id"] if accounts else None,
        "ad_accounts": accounts,
        "user_id": me.get("id"),
        "user_name": me.get("name"),
    }
    active_sessions[session_id] = session
    save_session(session_id=session_id, **session)

    logger.info("user_logged_in_via_oauth", session_id=session_id, ad_accounts_count=len(accounts))
    return AuthCallbackResponse(session_id=session_id, ad_accounts=accounts)


@router.get("/auth/me", response_model=AuthSessionResponse)
async def get_current_user(request: Request) -> AuthSessionResponse:
    session = get_session_from_request(request)
    return AuthSessionResponse(
        ad_account_id=session.get("ad_account_id"),
        ad_accounts=session.get("ad_accounts", []),
        user_id=session.get("user_id"),
    )


@router.post("/auth/switch-account/{ad_account_id}", response_model=SwitchAccountResponse)
async def switch_account(ad_account_id: str, request: Request) -> SwitchAccountResponse:
    session = get_session_from_request(request)
    ad_accounts = session.get("ad_accounts", [])
    valid_ids = {account.get("id") for account in ad_accounts}
    if valid_ids and ad_account_id not in valid_ids:
        raise HTTPException(status_code=404, detail="Ad account is not available in this session")

    session["ad_account_id"] = ad_account_id
    update_session_ad_account(request.headers.get("X-Session-ID"), ad_account_id)
    logger.info("active_ad_account_switched", ad_account_id=ad_account_id)
    return SwitchAccountResponse(status="switched", ad_account_id=ad_account_id)


# ---------------------------------------------------------------------------
# Email signup / login (sits alongside Meta OAuth)
# Email-only users still need to connect Meta from the dashboard before they
# can create campaigns — but they get an account and session immediately so
# they can browse pricing, configure billing, etc.
# ---------------------------------------------------------------------------


class EmailSignupRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=200)
    full_name: str | None = Field(default=None, max_length=200)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        v = value.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("email must be a valid address")
        return v


class EmailLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=200)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        v = value.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("email must be a valid address")
        return v


class EmailAuthResponse(BaseModel):
    session_id: str
    message: str
    redirect: str
    user_id: int
    email: str
    needs_meta_connection: bool = True


def _issue_email_session(*, user_id: int, email: str, full_name: str | None) -> str:
    session_id = secrets.token_urlsafe(32)
    session = {
        "access_token": "",
        "ad_account_id": None,
        "ad_accounts": [],
        "user_id": str(user_id),
        "user_name": full_name,
        "user_email": email,
    }
    active_sessions[session_id] = session
    save_session(session_id=session_id, **session)
    return session_id


@router.post("/auth/email/signup", response_model=EmailAuthResponse)
async def email_signup(payload: EmailSignupRequest, request: Request) -> EmailAuthResponse:
    auth_rate_limiter.enforce(
        f"signup:{client_key(request)}",
        detail="Too many signup attempts from this address. Please wait a minute.",
    )

    init_db()
    existing = get_email_user(payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user_id = create_email_user(
        email=payload.email,
        password_hash=_hash_password(payload.password),
        full_name=payload.full_name,
    )
    session_id = _issue_email_session(
        user_id=user_id, email=payload.email, full_name=payload.full_name
    )
    logger.info("email_signup", user_id=user_id, email=payload.email)
    return EmailAuthResponse(
        session_id=session_id,
        message="Account created. Connect Meta to start running campaigns.",
        redirect="/auth/login",
        user_id=user_id,
        email=payload.email,
    )


@router.post("/auth/email/login", response_model=EmailAuthResponse)
async def email_login(payload: EmailLoginRequest, request: Request) -> EmailAuthResponse:
    auth_rate_limiter.enforce(
        f"login:{client_key(request)}",
        detail="Too many sign-in attempts from this address. Please wait a minute.",
    )

    user = get_email_user(payload.email)
    if not user or not _verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    session_id = _issue_email_session(
        user_id=user["id"], email=user["email"], full_name=user.get("full_name")
    )
    logger.info("email_login", user_id=user["id"], email=user["email"])
    return EmailAuthResponse(
        session_id=session_id,
        message="Signed in.",
        redirect="/auth/login",
        user_id=user["id"],
        email=user["email"],
    )
