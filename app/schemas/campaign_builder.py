"""Pydantic schemas for the Campaign Builder wizard (Phase 2, Step 4).

The Campaign Builder hides Meta-specific terminology behind business-friendly
labels. Each wizard step maps to a schema that validates the user's input
before it is persisted as JSON in the ``campaign_drafts`` table.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import AnyUrl, BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Objective mapping — business labels → Meta events
# ---------------------------------------------------------------------------


class CampaignObjective(str, Enum):
    """Business-friendly campaign objectives (no Meta terminology)."""

    DRIVE_SALES = "DRIVE_SALES"
    GET_LEADS = "GET_LEADS"
    BOOST_REGISTRATIONS = "BOOST_REGISTRATIONS"
    ADD_PAYMENT_INFO = "ADD_PAYMENT_INFO"
    ADD_TO_CART = "ADD_TO_CART"
    COMPLETE_CHECKOUT = "COMPLETE_CHECKOUT"
    DRIVE_TRAFFIC = "DRIVE_TRAFFIC"
    CONTENT_VIEWS = "CONTENT_VIEWS"
    ADD_TO_WISHLIST = "ADD_TO_WISHLIST"
    DRIVE_SUBSCRIPTIONS = "DRIVE_SUBSCRIPTIONS"
    START_FREE_TRIAL = "START_FREE_TRIAL"
    SEARCH_RETARGETING = "SEARCH_RETARGETING"


# Maps business label → Meta SupportedEvent
OBJECTIVE_TO_EVENT: dict[CampaignObjective, str] = {
    CampaignObjective.DRIVE_SALES: "PURCHASE",
    CampaignObjective.GET_LEADS: "LEAD",
    CampaignObjective.BOOST_REGISTRATIONS: "COMPLETE_REGISTRATION",
    CampaignObjective.ADD_PAYMENT_INFO: "ADD_PAYMENT_INFO",
    CampaignObjective.ADD_TO_CART: "ADD_TO_CART",
    CampaignObjective.COMPLETE_CHECKOUT: "INITIATED_CHECKOUT",
    CampaignObjective.DRIVE_TRAFFIC: "SEARCH",
    CampaignObjective.CONTENT_VIEWS: "CONTENT_VIEW",
    CampaignObjective.ADD_TO_WISHLIST: "ADD_TO_WISHLIST",
    CampaignObjective.DRIVE_SUBSCRIPTIONS: "SUBSCRIBE",
    CampaignObjective.START_FREE_TRIAL: "START_TRIAL",
    CampaignObjective.SEARCH_RETARGETING: "SEARCH",
}

OBJECTIVE_METADATA: dict[CampaignObjective, dict[str, str]] = {
    CampaignObjective.DRIVE_SALES: {
        "icon": "ShoppingCart",
        "description": "Optimize for purchase conversions",
        "color": "green",
    },
    CampaignObjective.GET_LEADS: {
        "icon": "Users",
        "description": "Collect leads and contact info",
        "color": "blue",
    },
    CampaignObjective.BOOST_REGISTRATIONS: {
        "icon": "UserPlus",
        "description": "Drive sign-ups and account creation",
        "color": "purple",
    },
    CampaignObjective.ADD_PAYMENT_INFO: {
        "icon": "CreditCard",
        "description": "Encourage saved payment methods",
        "color": "orange",
    },
    CampaignObjective.ADD_TO_CART: {
        "icon": "ShoppingBag",
        "description": "Get users to add items to cart",
        "color": "green",
    },
    CampaignObjective.COMPLETE_CHECKOUT: {
        "icon": "CheckCircle",
        "description": "Drive completed checkouts",
        "color": "blue",
    },
    CampaignObjective.DRIVE_TRAFFIC: {
        "icon": "MousePointerClick",
        "description": "Send traffic to your website or app",
        "color": "purple",
    },
    CampaignObjective.CONTENT_VIEWS: {
        "icon": "Eye",
        "description": "Boost content or product page views",
        "color": "orange",
    },
    CampaignObjective.ADD_TO_WISHLIST: {
        "icon": "Heart",
        "description": "Encourage users to save items",
        "color": "green",
    },
    CampaignObjective.DRIVE_SUBSCRIPTIONS: {
        "icon": "Bell",
        "description": "Grow recurring subscriptions",
        "color": "blue",
    },
    CampaignObjective.START_FREE_TRIAL: {
        "icon": "FlaskConical",
        "description": "Promote free trial starts",
        "color": "purple",
    },
    CampaignObjective.SEARCH_RETARGETING: {
        "icon": "Search",
        "description": "Retarget users based on search behavior",
        "color": "orange",
    },
}


# ---------------------------------------------------------------------------
# Call-to-Action mapping
# ---------------------------------------------------------------------------


class CallToActionOption(str, Enum):
    SHOP_NOW = "SHOP_NOW"
    LEARN_MORE = "LEARN_MORE"
    SIGN_UP = "SIGN_UP"
    CONTACT_US = "CONTACT_US"
    DOWNLOAD = "DOWNLOAD"
    GET_OFFER = "GET_OFFER"
    GET_QUOTE = "GET_QUOTE"
    APPLY_NOW = "APPLY_NOW"
    BOOK_TRAVEL = "BOOK_TRAVEL"
    SUBSCRIBE = "SUBSCRIBE"


CTA_LABELS: dict[CallToActionOption, str] = {
    CallToActionOption.SHOP_NOW: "Shop Now",
    CallToActionOption.LEARN_MORE: "Learn More",
    CallToActionOption.SIGN_UP: "Sign Up",
    CallToActionOption.CONTACT_US: "Contact Us",
    CallToActionOption.DOWNLOAD: "Download",
    CallToActionOption.GET_OFFER: "Get Offer",
    CallToActionOption.GET_QUOTE: "Get Quote",
    CallToActionOption.APPLY_NOW: "Apply Now",
    CallToActionOption.BOOK_TRAVEL: "Book Travel",
    CallToActionOption.SUBSCRIBE: "Subscribe",
}


# ---------------------------------------------------------------------------
# Step schemas — each validates the data a user submits for that wizard step
# ---------------------------------------------------------------------------


class ObjectiveStep(BaseModel):
    """Step 1: Choose a marketing objective."""

    objective: CampaignObjective

    def to_event(self) -> str:
        return OBJECTIVE_TO_EVENT[self.objective]

    def label(self) -> str:
        return self.objective.value.replace("_", " ").title()

    def metadata(self) -> dict[str, str]:
        return OBJECTIVE_METADATA[self.objective]


class AudienceStep(BaseModel):
    """Step 2: Define the target audience."""

    countries: list[str] = Field(default_factory=lambda: ["US"], min_length=1)
    country_names: list[str] = Field(default_factory=lambda: ["United States"])


class BudgetStep(BaseModel):
    """Step 3: Set budget and bidding."""

    daily_budget_cents: int = Field(
        ..., ge=100, description="Daily budget in minor currency units (cents)"
    )
    bid_amount_cents: int | None = Field(
        default=None,
        ge=1,
        description="Optional bid cap in minor currency units (cents)",
    )
    has_bid_cap: bool = False


class CreativeStep(BaseModel):
    """Step 4: Configure the ad creative."""

    campaign_name: str = Field(..., min_length=1, max_length=120)
    web_url: str = Field(..., min_length=1)
    message: str = Field(
        default="Shop now on web or app!", min_length=1, max_length=500
    )
    page_id: str = Field(..., min_length=1)
    application_id: str = Field(default="", min_length=0)
    pixel_id: str = Field(default="", min_length=0)
    android_deeplink: str | None = None
    ios_deeplink: str | None = None
    call_to_action: CallToActionOption = CallToActionOption.LEARN_MORE

    @field_validator("web_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("web_url must start with http:// or https://")
        return v


class ReviewStep(BaseModel):
    """Step 5: Review is just a pass-through — data was already validated."""

    confirmed: bool = True


# ---------------------------------------------------------------------------
# Wizard step name constants
# ---------------------------------------------------------------------------

WIZARD_STEPS = [
    "objective",
    "audience",
    "budget",
    "creative",
    "review",
]

STEP_NAMES: dict[str, str] = {
    "objective": "Objective",
    "audience": "Audience",
    "budget": "Budget",
    "creative": "Creative",
    "review": "Review & Launch",
}

STEP_REQUIRED_FIELDS: dict[str, list[str]] = {
    "objective": ["objective"],
    "audience": ["countries"],
    "budget": ["daily_budget_cents"],
    "creative": ["campaign_name", "web_url", "page_id"],
    "review": ["confirmed"],
}

STEP_SCHEMA_MAP: dict[str, type[BaseModel]] = {
    "objective": ObjectiveStep,
    "audience": AudienceStep,
    "budget": BudgetStep,
    "creative": CreativeStep,
    "review": ReviewStep,
}


# ---------------------------------------------------------------------------
# API request/response schemas
# ---------------------------------------------------------------------------


class DraftCreateRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


class DraftCreateResponse(BaseModel):
    draft_id: int
    current_step: int = 1
    step_data: dict[str, Any] = Field(default_factory=dict)


class DraftUpdateStepRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    step_data: dict[str, Any] = Field(...)


class DraftValidateRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


class DraftLaunchRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


class DraftLaunchResponse(BaseModel):
    success: bool
    adset_id: str | None = None
    creative_id: str | None = None
    ad_id: str | None = None
    message: str = ""


class DraftListItem(BaseModel):
    id: int
    current_step: int
    is_complete: bool
    step_data: dict[str, Any]
    created_at: str
    updated_at: str
    objective_label: str | None = None
    campaign_name: str | None = None
