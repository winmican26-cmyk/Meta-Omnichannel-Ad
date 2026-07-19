"""Security defenses: prompt injection detection, output scrubbing, rate
limiting, log sanitization, and security headers.

Threat model covered:
- Prompt injection / jailbreak attempts via free-text inputs (chat, DSR).
- Tool poisoning via crafted user content that tries to spoof assistant
  actions or redirect navigation — mitigated via a strict allowlist on
  the action names the assistant may return.
- Sensitive data leakage via responses or logs — secrets matching known
  patterns (AWS, Slack, GitHub, OpenAI, Meta, generic Bearer, PEM keys,
  long secret-adjacent strings) are scrubbed before egress.
- Abuse via brute-force or chat flooding — token-bucket rate limits per
  client IP for the most sensitive endpoints.
- Clickjacking / mixed-content / XSS — strict security headers.

In-memory state is intentional for now (single-process FastAPI); for a
production multi-instance deploy, swap RateLimiter to a Redis backend.
"""

from __future__ import annotations

import html
import os
import re
import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware


# ---------------------------------------------------------------------------
# Prompt-injection / jailbreak pattern detection
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"\bignore\s+(?:the\s+|all\s+|any\s+|every\s+)?(?:previous|prior|above|earlier|preceding|original)\s+"
        r"(?:instructions?|prompts?|rules?|directives?|messages?|context|guidelines?)",
        re.I,
    ),
    re.compile(
        r"\bdisregard\s+(?:the\s+|all\s+|any\s+)?(?:previous|prior|above|safety|content)\s+"
        r"(?:instructions?|prompts?|rules?|filters?|guidelines?)",
        re.I,
    ),
    re.compile(r"\bforget\s+(?:everything|all|what\s+i\s+(?:said|told\s+you)|previous)", re.I),
    re.compile(r"\bsystem\s*(?:prompt|message|instructions?|role)\s*[:=]", re.I),
    re.compile(r"\bas\s+an?\s+(?:ai|language\s+model|assistant|chatbot|llm)\b", re.I),
    re.compile(r"\byou\s+are\s+(?:now|hereby|currently)\s+(?:a|an|the)\s+\w+", re.I),
    re.compile(r"\bdeveloper\s+(?:mode|prompt|role)\b", re.I),
    re.compile(r"\b(?:dan|jailbreak|do\s+anything\s+now)\b", re.I),
    re.compile(r"<\|[a-z_]+\|>", re.I),  # chat template control tokens
    re.compile(r"```\s*(?:bash|sh|shell|cmd|powershell|sql|python)\s*\n", re.I),
    re.compile(r"\b(?:curl|wget|nc|netcat|/bin/sh|/bin/bash|cmd\.exe|powershell\.exe)\s+", re.I),
    re.compile(r"\breveal\s+(?:the\s+|your\s+)?(?:system\s+|hidden\s+)?(?:prompt|instructions?|secret|token|key)", re.I),
    re.compile(r"\bprint\s+(?:the\s+|all\s+)?(?:env|environment|secrets?|keys?|tokens?|password|\.env)", re.I),
    re.compile(r"\boutput\s+(?:the\s+|your\s+)?(?:system|hidden|secret|raw|original)\s+(?:prompt|message)", re.I),
    re.compile(r"<\s*script\b", re.I),
    re.compile(r"\bjavascript\s*:", re.I),
    re.compile(r"\bon(?:load|error|click|mouseover)\s*=", re.I),
]


def detect_injection(text: str) -> tuple[bool, str | None]:
    """Return (is_injection, matched_pattern_excerpt) for the given text."""
    if not text:
        return False, None
    for pattern in _INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return True, match.group(0)[:80]
    return False, None


# ---------------------------------------------------------------------------
# Sensitive data scrubbing (output side)
# ---------------------------------------------------------------------------

_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED:AWS_ACCESS_KEY]"),
    (re.compile(r"ASIA[0-9A-Z]{16}"), "[REDACTED:AWS_TEMP_KEY]"),
    (re.compile(r"xox[baprs]-[0-9a-zA-Z\-]{10,}"), "[REDACTED:SLACK_TOKEN]"),
    (re.compile(r"\bgh[ps]_[A-Za-z0-9]{36}\b"), "[REDACTED:GITHUB_TOKEN]"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "[REDACTED:OPENAI_KEY]"),
    (re.compile(r"\bEAA[A-Za-z0-9_]{20,}\b"), "[REDACTED:META_TOKEN]"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}"), "Bearer [REDACTED]"),
    (
        re.compile(
            r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+PRIVATE KEY-----"
        ),
        "[REDACTED:PRIVATE_KEY]",
    ),
    # Fernet token shape produced by our own token encryption (precaution)
    (re.compile(r"\bfr:gAAAAA[A-Za-z0-9_\-=]{40,}"), "[REDACTED:ENCRYPTED_TOKEN]"),
    # Heuristic: long opaque string immediately following a secret-adjacent
    # field name. Conservative to avoid false positives on legitimate IDs.
    (
        re.compile(
            r"(?i)\b(password|secret|token|api[_-]?key|app_?secret)\b\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,}['\"]?"
        ),
        lambda m: f"{m.group(1)}=[REDACTED]",
    ),
]


def scrub_secrets(text: str | None) -> str | None:
    """Remove known secret patterns from a string before egress."""
    if not text:
        return text
    for pattern, replacement in _SECRET_PATTERNS:
        if callable(replacement):
            text = pattern.sub(replacement, text)
        else:
            text = pattern.sub(replacement, text)
    return text


# ---------------------------------------------------------------------------
# HTML / script stripping for user-supplied free text
# ---------------------------------------------------------------------------

_SCRIPT_BLOCK = re.compile(r"<script[\s\S]*?</script>", re.I)
_STYLE_BLOCK = re.compile(r"<style[\s\S]*?</style>", re.I)
_TAG = re.compile(r"<[^>]+>")
_JS_PROTOCOL = re.compile(r"javascript\s*:", re.I)


def strip_html(text: str) -> str:
    if not text:
        return text
    text = _SCRIPT_BLOCK.sub("", text)
    text = _STYLE_BLOCK.sub("", text)
    text = _TAG.sub("", text)
    text = _JS_PROTOCOL.sub("", text)
    return html.unescape(text)


# ---------------------------------------------------------------------------
# Rate limiter (token bucket per key, in-memory)
# ---------------------------------------------------------------------------


class RateLimiter:
    """Sliding-window rate limiter per arbitrary key (IP, session, etc.).

    Not safe across processes. For multi-process deploys, swap to Redis.
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits[key]
        cutoff = now - self.window
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= self.max:
            return False
        hits.append(now)
        return True

    def enforce(self, key: str, detail: str = "Too many requests. Please slow down.") -> None:
        if not self.check(key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail
            )


chat_rate_limiter = RateLimiter(max_requests=20, window_seconds=60)
auth_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
dsr_rate_limiter = RateLimiter(max_requests=3, window_seconds=300)


def client_key(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if fwd:
        return fwd
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# Assistant action whitelist (anti tool-poisoning)
# ---------------------------------------------------------------------------

ALLOWED_ASSISTANT_ACTIONS: frozenset[str] = frozenset(
    {"open_dsr_form", "open_signup", "open_login", "open_help"}
)


def validate_action_name(name: str | None) -> str | None:
    if name is None:
        return None
    if name in ALLOWED_ASSISTANT_ACTIONS:
        return name
    return None  # silently drop unknown actions


_ALLOWED_HREF_PREFIXES: tuple[str, ...] = (
    "/",
    "https://developers.facebook.com/",
    "https://business.facebook.com/",
    "mailto:",
)


def validate_action_href(href: str | None) -> str | None:
    if href is None:
        return None
    href = href.strip()
    if any(href.startswith(p) for p in _ALLOWED_HREF_PREFIXES):
        return href
    return None  # drop suspicious external URLs


# ---------------------------------------------------------------------------
# Log sanitizer — structlog processor
# ---------------------------------------------------------------------------

_SENSITIVE_KEY_PATTERNS = re.compile(
    r"(?i)(password|secret|token|api[_-]?key|authorization|cookie|bearer|access_token|"
    r"client_secret|app_secret|private_key|session_id)"
)


def sanitize_log_event(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """structlog processor: redact sensitive keys and scrub string values."""
    for key in list(event_dict.keys()):
        value = event_dict[key]
        if _SENSITIVE_KEY_PATTERNS.search(key):
            event_dict[key] = "[REDACTED]"
        elif isinstance(value, str):
            scrubbed = scrub_secrets(value)
            if scrubbed is not None:
                event_dict[key] = scrubbed
    return event_dict


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Sets defensive HTTP response headers on every response."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()",
        )
        # CSP: 'unsafe-inline' on scripts is required because index.html and
        # login.html include inline event handlers. Tighten with nonces when
        # those handlers are moved to external files.
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self' https://www.facebook.com https://checkout.stripe.com",
        )
        if os.getenv("FORCE_HTTPS", "").lower() in {"1", "true", "yes", "on"}:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response
