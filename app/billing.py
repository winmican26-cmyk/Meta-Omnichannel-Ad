import os
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import active_sessions, get_session
from app.database import update_session_subscription
from app.utils.logging import structlog

logger = structlog.get_logger()

router = APIRouter(tags=["billing"])

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID", "")
STRIPE_ENTERPRISE_PRICE_ID = os.getenv("STRIPE_ENTERPRISE_PRICE_ID", "")
BILLING_SUCCESS_URL = os.getenv("BILLING_SUCCESS_URL", "http://localhost:8765/billing/success")
BILLING_CANCEL_URL = os.getenv("BILLING_CANCEL_URL", "http://localhost:8765/")

PAID_TIERS = {"pro", "enterprise"}


class CheckoutRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    plan: Literal["pro", "enterprise"]


class CheckoutResponse(BaseModel):
    checkout_url: str


class BillingPortalRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    customer_id: str = Field(..., min_length=1)


class BillingPortalResponse(BaseModel):
    portal_url: str


def _stripe():
    try:
        import stripe
    except ModuleNotFoundError as exc:
        raise RuntimeError("stripe is required for billing. Install requirements.txt or run the Docker image.") from exc

    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY is not configured")
    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


def require_paid_subscription(session: dict) -> None:
    tier = session.get("subscription_tier", "free")
    if tier not in PAID_TIERS:
        raise HTTPException(status_code=402, detail="A Pro or Enterprise subscription is required")


def _price_id_for_plan(plan: str) -> str:
    if plan == "pro":
        return STRIPE_PRO_PRICE_ID
    return STRIPE_ENTERPRISE_PRICE_ID


@router.post("/billing/checkout", response_model=CheckoutResponse)
async def create_checkout(request: CheckoutRequest) -> CheckoutResponse:
    session = get_session(request.session_id)
    stripe = _stripe()
    price_id = _price_id_for_plan(request.plan)
    if not price_id:
        raise HTTPException(status_code=500, detail=f"Stripe price ID is not configured for {request.plan}")

    checkout = stripe.checkout.Session.create(
        customer_email=session.get("user_email"),
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=BILLING_SUCCESS_URL,
        cancel_url=BILLING_CANCEL_URL,
        metadata={"user_session_id": request.session_id, "plan": request.plan},
    )
    logger.info("stripe_checkout_created", session_id=request.session_id, plan=request.plan)
    return CheckoutResponse(checkout_url=checkout.url)


@router.post("/billing/portal", response_model=BillingPortalResponse)
async def create_billing_portal(request: BillingPortalRequest) -> BillingPortalResponse:
    get_session(request.session_id)
    stripe = _stripe()
    portal = stripe.billing_portal.Session.create(
        customer=request.customer_id,
        return_url=BILLING_SUCCESS_URL,
    )
    return BillingPortalResponse(portal_url=portal.url)


@router.post("/billing/webhook")
async def stripe_webhook(request: Request) -> dict[str, str]:
    stripe = _stripe()
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="STRIPE_WEBHOOK_SECRET is not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Stripe webhook: {exc}") from exc

    if event["type"] == "checkout.session.completed":
        checkout = event["data"]["object"]
        metadata = checkout.get("metadata", {})
        session_id = metadata.get("user_session_id")
        plan = metadata.get("plan", "pro")
        if session_id:
            update_session_subscription(session_id, plan)
            if session_id in active_sessions:
                active_sessions[session_id]["subscription_tier"] = plan
            logger.info("subscription_activated", session_id=session_id, plan=plan)

    if event["type"] in {"customer.subscription.deleted", "customer.subscription.paused"}:
        metadata = event["data"]["object"].get("metadata", {})
        session_id = metadata.get("user_session_id")
        if session_id:
            update_session_subscription(session_id, "free")
            if session_id in active_sessions:
                active_sessions[session_id]["subscription_tier"] = "free"
            logger.info("subscription_deactivated", session_id=session_id)

    return {"status": "ok"}
