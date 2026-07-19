import os
import re
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.security import (
    chat_rate_limiter,
    client_key,
    detect_injection,
    scrub_secrets,
    strip_html,
    validate_action_href,
    validate_action_name,
)
from app.utils.logging import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/assistant", tags=["assistant"])

ASSISTANT_PROVIDER = os.getenv("ASSISTANT_PROVIDER", "deterministic").strip().lower()
ASSISTANT_API_KEY = os.getenv("ASSISTANT_API_KEY", "").strip()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None


class ChatAction(BaseModel):
    label: str
    href: str | None = None
    action: Literal["open_dsr_form", "open_signup", "open_login", "open_help"] | None = None


class ChatResponse(BaseModel):
    message: str
    actions: list[ChatAction] = []
    source: Literal["deterministic", "llm", "fallback"] = "deterministic"


# ---------------------------------------------------------------------------
# Deterministic FAQ matcher
# Order matters — more specific patterns first.
# ---------------------------------------------------------------------------

_FAQ: list[tuple[re.Pattern[str], ChatResponse]] = [
    (
        re.compile(r"\b(hi|hello|hey|yo|sup|hola)\b", re.I),
        ChatResponse(
            message="Hi there! I'm the Meta Omni Channel Ad assistant. Ask me about getting started, creating campaigns, the AI Optimizer, billing, or your privacy rights.",
            actions=[
                ChatAction(label="Open Help & Tutorial", href="/help"),
                ChatAction(label="Get Started", action="open_signup"),
            ],
        ),
    ),
    (
        re.compile(r"\b(sign\s*up|register|create.*account|join)\b", re.I),
        ChatResponse(
            message="You can sign up with Meta Business Login or with email. Meta Business Login is recommended because it sets up ad-account access immediately.",
            actions=[
                ChatAction(label="Sign up", action="open_signup"),
                ChatAction(label="See tutorial", href="/help#connect"),
            ],
        ),
    ),
    (
        re.compile(r"\b(sign\s*in|log\s*in|login)\b", re.I),
        ChatResponse(
            message="Sign in lives on the /login page. If you used Meta Business Login before, click 'Continue with Meta'. If you used email, fill in the email form.",
            actions=[ChatAction(label="Open Sign in", action="open_login")],
        ),
    ),
    (
        re.compile(r"\b(price|pricing|cost|how much|subscription|plan)\b", re.I),
        ChatResponse(
            message="Every session starts with 150 free credits. Pro and Enterprise subscriptions unlock unlimited AI optimization, creative generation, insights sync, and migration scans. Pricing is configured on the billing page once you're signed in.",
            actions=[ChatAction(label="See credit costs", href="/help#billing")],
        ),
    ),
    (
        re.compile(r"\b(credit|credits|how many credits)\b", re.I),
        ChatResponse(
            message="Starting balance is 150 credits per session. Optimizer: 15 credits. Creative generation: 25. Insights sync: 20. Migration scan: 30.",
            actions=[ChatAction(label="See breakdown", href="/help#billing")],
        ),
    ),
    (
        re.compile(r"\b(ccco|cross[-\s]?channel|omnichannel|omni.channel)\b", re.I),
        ChatResponse(
            message="CCCO (Cross-Channel Conversion Optimization) lets one Meta campaign optimise across web, app, and offline events on a single conversion goal. You declare the same event for your pixel and app, and Meta picks the best surface per user.",
            actions=[ChatAction(label="Read more", href="/help#campaign")],
        ),
    ),
    (
        re.compile(r"\b(privacy|gdpr|data rights|delete.*data|erasure|dsr|right to be forgotten)\b", re.I),
        ChatResponse(
            message="You have full GDPR rights — access, rectification, erasure, portability, restriction, objection, and withdrawing consent. Submit a request on the home page and we respond within one calendar month.",
            actions=[
                ChatAction(label="Submit a request", action="open_dsr_form"),
                ChatAction(label="Read Privacy Policy", href="/privacy-policy"),
            ],
        ),
    ),
    (
        re.compile(r"\b(cookie|cookies)\b", re.I),
        ChatResponse(
            message="We use strictly necessary cookies to keep you signed in. With your consent we also use optional analytics cookies. You can change your choice anytime from the 'Cookie preferences' link in the footer.",
            actions=[ChatAction(label="Privacy Policy", href="/privacy-policy")],
        ),
    ),
    (
        re.compile(r"\b(meta.*(app.*id|secret)|app.*secret|where.*meta.*key|how.*get.*meta)\b", re.I),
        ChatResponse(
            message="Go to developers.facebook.com/apps, create or open your app, then Settings → Basic. The App ID and App Secret are there. Paste them into your .env as META_APP_ID and META_APP_SECRET, then restart the server.",
            actions=[ChatAction(label="Meta Developer Apps", href="https://developers.facebook.com/apps/")],
        ),
    ),
    (
        re.compile(r"\b(app review|standard access|advanced access|full access|limited access)\b", re.I),
        ChatResponse(
            message="To serve other advertisers' accounts via OAuth you need Full Access on the Marketing API, which requires App Review plus Business Verification. Limited Access (default) only works on accounts where the app admin is an admin.",
            actions=[ChatAction(label="App Review docs", href="https://developers.facebook.com/docs/app-review")],
        ),
    ),
    (
        re.compile(r"\b(token|access[-_\s]?token|encrypt|encryption|stored)\b", re.I),
        ChatResponse(
            message="OAuth access tokens are encrypted at rest in SQLite using Fernet (AES-128-CBC + HMAC-SHA256). The key lives in the TOKEN_ENCRYPTION_KEY env var. Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"",
        ),
    ),
    (
        re.compile(r"\b(insights|sync.*insight|analytics|dashboard|lift|cpa)\b", re.I),
        ChatResponse(
            message="Click 'Sync Insights' on any CCCO ad set and the engine pulls the last 30 days from Meta — channel splits, daily breakdowns, CCCO lift, average CPA. Sync costs 20 credits and is idempotent on (ad_set, date).",
            actions=[ChatAction(label="Read tutorial", href="/help#insights")],
        ),
    ),
    (
        re.compile(r"\b(optimizer|optimi[sz]e|budget split|bid cap|predicted cpa|ai)\b", re.I),
        ChatResponse(
            message="The AI Optimizer returns a recommended web/app budget split, predicted CPA, a suggested bid cap, deep-link routing rule, and a creative tip — all in one call (15 credits).",
            actions=[ChatAction(label="See Optimizer guide", href="/help#optimize")],
        ),
    ),
    (
        re.compile(r"\b(creative|ad copy|catalog|advantage\+?|deep[-\s]?link|link spec)\b", re.I),
        ChatResponse(
            message="Creative Studio generates Meta-ready creative variants with the omnichannel link spec, the right deep-link treatment, and optional Advantage+ Catalog template URL spec. Set catalog_mode=true with a product_id for shopping ads.",
            actions=[ChatAction(label="Creative guide", href="/help#creative")],
        ),
    ),
    (
        re.compile(r"\b(migrate|migration|legacy|web.only|app.only)\b", re.I),
        ChatResponse(
            message="Click 'Scan for Migration' to find web-only and app-only legacy campaigns. Each candidate shows the recommended event and an expected CPA lift. Generate a migration plan, fill in the placeholders, and ship the CCCO upgrade.",
            actions=[ChatAction(label="Migration walkthrough", href="/help#migration")],
        ),
    ),
    (
        re.compile(r"\b(template|duplicate|reuse|copy.*campaign)\b", re.I),
        ChatResponse(
            message="Save any successful campaign as a template, then duplicate it later with a new name, budget, and target audience — useful for rolling out the same play across regions or product lines.",
            actions=[ChatAction(label="Templates guide", href="/help#templates")],
        ),
    ),
    (
        re.compile(r"\b(paused|why.*pause|active|publish)\b", re.I),
        ChatResponse(
            message="Every new ad set and ad is created PAUSED on purpose — so you can review the structure in Ads Manager before any spend. Flip to ACTIVE when you're ready.",
        ),
    ),
    (
        re.compile(r"\b(revoke|disconnect|remove app|cancel.*access)\b", re.I),
        ChatResponse(
            message="Go to Meta Business Settings → Business Integrations, find this app, and click 'Remove'. Meta will send us a signed deletion request and we'll purge your tokens. You'll get a confirmation code for the deletion status.",
        ),
    ),
    (
        re.compile(r"\b(help|tutorial|guide|how.*do.*i|how to|getting started)\b", re.I),
        ChatResponse(
            message="The full quick-start tutorial covers Meta connection, campaign creation, the AI Optimizer, creatives, insights sync, migration, templates, billing, and FAQ.",
            actions=[ChatAction(label="Open Help & Tutorial", action="open_help")],
        ),
    ),
    (
        re.compile(r"\b(contact|support|email|reach.*you|talk.*human)\b", re.I),
        ChatResponse(
            message="Product/support: support@your-domain.example. Privacy: privacy@your-domain.example. Security: security@your-domain.example.",
        ),
    ),
    (
        re.compile(r"\b(terms|tos|legal|liability)\b", re.I),
        ChatResponse(
            message="Our Terms of Service cover account use, subscriptions, acceptable use, liability limits, and termination.",
            actions=[ChatAction(label="Read Terms", href="/terms")],
        ),
    ),
    (
        re.compile(r"\b(thank|thanks|ty|appreciate)\b", re.I),
        ChatResponse(
            message="You're welcome! Anything else I can help you with?",
        ),
    ),
]


def _match_deterministic(message: str) -> ChatResponse | None:
    for pattern, response in _FAQ:
        if pattern.search(message):
            return response.model_copy(update={"source": "deterministic"})
    return None


async def _query_llm(message: str) -> ChatResponse | None:
    """Stub for future LLM provider integration.

    Wire this to Llama-via-Bedrock, Together AI, Replicate, OpenAI, Claude,
    or any other provider by setting ASSISTANT_PROVIDER and ASSISTANT_API_KEY.
    Returns None if no provider is configured.
    """
    if ASSISTANT_PROVIDER in {"", "deterministic", "none"} or not ASSISTANT_API_KEY:
        return None

    # Placeholder. Implementation would call the chosen provider here.
    logger.info("assistant_llm_provider_called_but_not_implemented", provider=ASSISTANT_PROVIDER)
    return None


def _sanitize_response(response: ChatResponse) -> ChatResponse:
    """Apply output scrubbing and action whitelisting before egress."""
    safe_actions: list[ChatAction] = []
    for action in response.actions:
        validated_action = validate_action_name(action.action)
        validated_href = validate_action_href(action.href)
        # Drop actions where both action and href were rejected
        if action.action and validated_action is None:
            continue
        if action.href and validated_href is None:
            continue
        safe_actions.append(
            ChatAction(
                label=action.label[:60],
                href=validated_href,
                action=validated_action,
            )
        )
    return ChatResponse(
        message=scrub_secrets(response.message) or "",
        actions=safe_actions,
        source=response.source,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    chat_rate_limiter.enforce(
        f"chat:{client_key(request)}",
        detail="You're sending messages too fast. Please wait a moment.",
    )

    # Strip any HTML / script the user may have inserted, then trim
    message = strip_html(payload.message).strip()
    if not message:
        return _sanitize_response(
            ChatResponse(
                message="Could you rephrase that? I didn't catch a question.",
                source="fallback",
            )
        )

    is_injection, matched = detect_injection(message)
    if is_injection:
        logger.warning(
            "assistant_injection_blocked",
            client=client_key(request),
            pattern=matched,
        )
        return _sanitize_response(
            ChatResponse(
                message=(
                    "I can only help with questions about the Meta Omni Channel Ad product — "
                    "getting started, campaigns, billing, privacy, and similar topics. "
                    "If you have a different need, please email support."
                ),
                actions=[
                    ChatAction(label="Open Help", action="open_help"),
                    ChatAction(label="Email support", href="mailto:support@your-domain.example"),
                ],
                source="fallback",
            )
        )

    deterministic = _match_deterministic(message)
    if deterministic is not None:
        return _sanitize_response(deterministic)

    llm = await _query_llm(message)
    if llm is not None:
        return _sanitize_response(llm)

    return _sanitize_response(
        ChatResponse(
            message=(
                "I don't have a confident answer for that yet. The Help page has a full tutorial, "
                "or you can email support@your-domain.example and a human will get back to you."
            ),
            actions=[
                ChatAction(label="Open Help", action="open_help"),
                ChatAction(label="Email support", href="mailto:support@your-domain.example"),
            ],
            source="fallback",
        )
    )
