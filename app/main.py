from contextlib import asynccontextmanager
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.ai_optimizer import OptimizeRequest, OptimizerSuggestion
from app.claude_optimizer import (
    OPTIMIZER_LABEL_CLAUDE,
    ClaudeOptimizer,
)
from app.analytics import (
    AnalyticsService,
    DashboardResponse,
    IngestInsightsRequest,
    IngestInsightsResponse,
)
from app.auth import get_session, router as auth_router
from app.billing import router as billing_router
from app.creative_studio import CreativeGenerateRequest, CreativeStudio, CreativeVariant
from app.credits import CreditService
from app.database import (
    get_session_record,
    init_db,
    list_owned_ccco_campaigns,
    record_optimizer_run,
)
from app.dashboard import DashboardService, DashboardSummary
from app.dependencies import (
    require_adset_owner,
    require_campaign_subscription,
    require_creative_subscription,
    require_pro_subscription,
)
from app.exceptions import register_exception_handlers
from app.meta_insights import InsightsService
from app.migration import MigrationCandidate, MigrationPlan, MigrationService
from app.optimizer_backtest import BacktestRequest, BacktestResult, BacktestRunner
from app.assistant import router as assistant_router
from app.privacy import router as privacy_router
from app.security import SecurityHeadersMiddleware, sanitize_log_event
from app.schemas.campaign import (
    CampaignCreateRequest,
    CampaignCreateResponse,
    CampaignRecord,
    HealthResponse,
)
from app.services.campaign_service import CampaignService
from app.services.campaign_builder_service import CampaignBuilderService
from app.schemas.campaign_builder import (
    DraftCreateRequest,
    DraftCreateResponse,
    DraftUpdateStepRequest,
    DraftValidateRequest,
    DraftLaunchRequest,
    DraftLaunchResponse,
    DraftListItem,
)
from app.templates import (
    DuplicateTemplateRequest,
    SaveTemplateRequest,
    TemplateRecord,
    TemplatesService,
)
from app.ai_providers import list_providers, route_query
from app.key_manager import (
    delete_key,
    get_key,
    has_key,
    list_keys,
    save_key,
    validate_and_save_key,
)
from app.db_migrations import run_migrations
from app.utils.logging import structlog
from app.utils.request_id import RequestIDMiddleware

STATIC_DIR = Path(__file__).parent / "static"
FAVICON_PATH = STATIC_DIR / "favicon.svg"
LOGO_PATH = STATIC_DIR / "logo.svg"
LOGO_LIGHT_PATH = STATIC_DIR / "logo-light.svg"
INDEX_PATH = STATIC_DIR / "index.html"
ILLUSTRATION_ANALYST_PATH = STATIC_DIR / "illustration-analyst.svg"
PRIVACY_POLICY_PATH = STATIC_DIR / "privacy-policy.html"
TERMS_PATH = STATIC_DIR / "terms.html"
LEGAL_CSS_PATH = STATIC_DIR / "legal.css"
LOGIN_PATH = STATIC_DIR / "login.html"
ABOUT_PATH = STATIC_DIR / "about.html"
SITE_CSS_PATH = STATIC_DIR / "site.css"
SITE_JS_PATH = STATIC_DIR / "site.js"
HELP_PATH = STATIC_DIR / "help.html"
SETUP_PATH = STATIC_DIR / "setup.html"

load_dotenv()

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        sanitize_log_event,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()
ENABLE_API_DOCS = os.getenv("ENABLE_API_DOCS", "").lower() in {"1", "true", "yes", "on"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    run_migrations(os.getenv("CCCO_DB_PATH", "campaigns.db"))
    logger.info("database_initialized")
    yield


app = FastAPI(
    title="Meta CCCO Engine",
    description="Core backend for Meta cross-channel conversion optimization campaign creation.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json" if ENABLE_API_DOCS else None,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
register_exception_handlers(app)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(privacy_router)
app.include_router(assistant_router)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(INDEX_PATH, media_type="text/html")


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.svg", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(FAVICON_PATH, media_type="image/svg+xml")


@app.get("/logo.svg", include_in_schema=False)
async def logo() -> FileResponse:
    return FileResponse(LOGO_PATH, media_type="image/svg+xml")


@app.get("/logo-light.svg", include_in_schema=False)
async def logo_light() -> FileResponse:
    return FileResponse(LOGO_LIGHT_PATH, media_type="image/svg+xml")


@app.get("/illustration-analyst.svg", include_in_schema=False)
async def illustration_analyst() -> FileResponse:
    return FileResponse(ILLUSTRATION_ANALYST_PATH, media_type="image/svg+xml")


@app.get("/legal.css", include_in_schema=False)
async def legal_css() -> FileResponse:
    return FileResponse(LEGAL_CSS_PATH, media_type="text/css")


@app.get("/privacy-policy", include_in_schema=False)
async def privacy_policy_page() -> FileResponse:
    return FileResponse(PRIVACY_POLICY_PATH, media_type="text/html")


@app.get("/terms", include_in_schema=False)
async def terms_page() -> FileResponse:
    return FileResponse(TERMS_PATH, media_type="text/html")


@app.get("/login", include_in_schema=False)
async def login_page() -> FileResponse:
    return FileResponse(LOGIN_PATH, media_type="text/html")


@app.get("/signup", include_in_schema=False)
async def signup_page() -> RedirectResponse:
    return RedirectResponse(url="/login?mode=signup")


@app.get("/about", include_in_schema=False)
async def about_page() -> FileResponse:
    return FileResponse(ABOUT_PATH, media_type="text/html")


@app.get("/site.css", include_in_schema=False)
async def site_css() -> FileResponse:
    return FileResponse(SITE_CSS_PATH, media_type="text/css")


@app.get("/site.js", include_in_schema=False)
async def site_js() -> FileResponse:
    return FileResponse(SITE_JS_PATH, media_type="application/javascript")


@app.get("/help", include_in_schema=False)
async def help_page() -> FileResponse:
    return FileResponse(HELP_PATH, media_type="text/html")


@app.get("/setup", include_in_schema=False)
async def setup_page() -> FileResponse:
    return FileResponse(SETUP_PATH, media_type="text/html")


@app.get("/docs", include_in_schema=False)
async def swagger_ui():
    if not ENABLE_API_DOCS or not app.openapi_url:
        raise HTTPException(status_code=404, detail="Not found")
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Docs",
        swagger_favicon_url="/favicon.svg",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_ui():
    if not ENABLE_API_DOCS or not app.openapi_url:
        raise HTTPException(status_code=404, detail="Not found")
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_favicon_url="/favicon.svg",
    )


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Health check with database connectivity probe."""
    db_status = "disconnected"
    try:
        from app.database import get_db

        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
        db_status = "connected"
    except Exception as exc:
        logger.warning("health_check_db_failed", error=str(exc))
    return HealthResponse(database=db_status)


@app.post("/campaigns/ccco", response_model=CampaignCreateResponse, tags=["campaigns"])
async def create_ccco_campaign(
    request: CampaignCreateRequest,
    _: dict | None = Depends(require_campaign_subscription),
) -> CampaignCreateResponse:
    return await _create_ccco_campaign_from_request(request)


async def _create_ccco_campaign_from_request(
    request: CampaignCreateRequest,
) -> CampaignCreateResponse:
    session = get_session(request.session_id)
    access_token = session.get("access_token")
    ad_account_id = session.get("ad_account_id")
    if not access_token or not ad_account_id:
        raise HTTPException(
            status_code=400, detail="No active access token or ad account is available"
        )

    logger.info(
        "create_ccco_campaign_requested", name=request.name, ad_account_id=ad_account_id
    )
    service = CampaignService(
        access_token=access_token,
        ad_account_id=ad_account_id,
    )
    result = await service.create_cross_channel_adset(
        name=request.name,
        daily_budget=request.daily_budget,
        event=request.event,
        omnichannel=request.omnichannel,
        pixel_id=request.pixel_id,
        application_id=request.application_id,
        page_id=request.page_id,
        web_url=str(request.web_url),
        message=request.message,
        countries=request.countries,
        android_deeplink=str(request.android_deeplink)
        if request.android_deeplink
        else None,
        ios_deeplink=str(request.ios_deeplink) if request.ios_deeplink else None,
        session_id=request.session_id,
        bid_amount_cents=request.bid_amount_cents,
    )
    return CampaignCreateResponse(**result)


@app.get("/campaigns/ccco", response_model=list[CampaignRecord], tags=["campaigns"])
async def get_ccco_campaigns(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    _: dict = Depends(require_pro_subscription),
) -> list[CampaignRecord]:
    # Clamp pagination params for safety
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    session = get_session(session_id)
    ad_account_id = session.get("ad_account_id") if isinstance(session, dict) else None
    rows = list_owned_ccco_campaigns(
        session_id=session_id, ad_account_id=ad_account_id, limit=limit, offset=offset
    )
    return [CampaignRecord(**row) for row in rows]


def require_save_template_subscription(payload: SaveTemplateRequest) -> dict:
    return require_pro_subscription(payload.session_id)


@app.post("/campaigns/templates", tags=["campaigns"])
async def save_template(
    payload: SaveTemplateRequest,
    _: dict = Depends(require_save_template_subscription),
) -> dict[str, str]:
    TemplatesService.save_as_template(
        session_id=payload.session_id,
        name=payload.name,
        config=payload.config,
        original_adset_id=payload.original_adset_id,
    )
    return {"status": "saved"}


def require_template_list_subscription(session_id: str) -> dict:
    return require_pro_subscription(session_id)


@app.get(
    "/campaigns/templates", response_model=list[TemplateRecord], tags=["campaigns"]
)
async def list_templates(
    session_id: str,
    limit: int = Query(
        default=50, ge=1, le=200, description="Maximum number of templates to return"
    ),
    offset: int = Query(default=0, ge=0, description="Number of templates to skip"),
    _: dict = Depends(require_template_list_subscription),
) -> list[TemplateRecord]:
    return TemplatesService.list_templates(session_id, limit=limit, offset=offset)


def require_duplicate_subscription(payload: DuplicateTemplateRequest) -> dict:
    return require_pro_subscription(payload.session_id)


@app.post(
    "/campaigns/duplicate/{template_id}",
    response_model=CampaignCreateResponse,
    tags=["campaigns"],
)
async def duplicate_campaign(
    template_id: int,
    payload: DuplicateTemplateRequest,
    _: dict = Depends(require_duplicate_subscription),
) -> CampaignCreateResponse:
    new_config = TemplatesService.duplicate_from_template(
        template_id=template_id,
        session_id=payload.session_id,
        new_name=payload.new_name,
        new_daily_budget=payload.new_daily_budget,
    )
    return await _create_ccco_campaign_from_request(new_config)


# ---------------------------------------------------------------------------
# Campaign Builder endpoints (Phase 2, Step 4)
# ---------------------------------------------------------------------------


@app.post("/campaigns/builder/draft", tags=["campaigns"])
async def create_builder_draft(payload: DraftCreateRequest) -> DraftCreateResponse:
    """Create a new empty campaign draft for the wizard."""
    get_session(payload.session_id)  # validate session exists
    result = CampaignBuilderService.create_draft(payload.session_id)
    return DraftCreateResponse(**result)


@app.get(
    "/campaigns/builder/drafts", response_model=list[DraftListItem], tags=["campaigns"]
)
async def list_builder_drafts(session_id: str) -> list[dict]:
    """List all campaign drafts for the current session."""
    get_session(session_id)
    return CampaignBuilderService.list_drafts(session_id)


@app.get("/campaigns/builder/draft/{draft_id}", tags=["campaigns"])
async def get_builder_draft(draft_id: int, session_id: str) -> dict:
    """Get a specific campaign draft with full step data."""
    draft = CampaignBuilderService.get_draft(draft_id, session_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@app.put("/campaigns/builder/draft/{draft_id}/step/{step}", tags=["campaigns"])
async def update_builder_step(
    draft_id: int,
    step: str,
    payload: DraftUpdateStepRequest,
) -> dict:
    """Update a single wizard step's data for a draft."""
    return CampaignBuilderService.update_step(
        draft_id=draft_id,
        session_id=payload.session_id,
        step=step,
        step_data=payload.step_data,
    )


@app.post("/campaigns/builder/draft/{draft_id}/validate", tags=["campaigns"])
async def validate_builder_step(
    draft_id: int,
    step: str,
    payload: DraftValidateRequest,
) -> dict:
    """Check if a wizard step has all required fields filled."""
    return CampaignBuilderService.validate_step(
        draft_id=draft_id,
        session_id=payload.session_id,
        step=step,
    )


@app.post(
    "/campaigns/builder/draft/{draft_id}/launch",
    response_model=DraftLaunchResponse,
    tags=["campaigns"],
)
async def launch_builder_draft(
    draft_id: int,
    payload: DraftLaunchRequest,
) -> DraftLaunchResponse:
    """Convert a completed draft into a live campaign."""
    result = await CampaignBuilderService.launch(draft_id, payload.session_id)
    return DraftLaunchResponse(**result)


@app.delete("/campaigns/builder/draft/{draft_id}", tags=["campaigns"])
async def delete_builder_draft(draft_id: int, session_id: str) -> dict:
    """Delete a campaign draft."""
    deleted = CampaignBuilderService.delete_draft(draft_id, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"status": "deleted"}


@app.post("/optimize/backtest", response_model=BacktestResult, tags=["ai"])
async def run_optimizer_backtest(payload: BacktestRequest) -> BacktestResult:
    """Backtest Claude vs. the rule engine against this account's history.

    Splits each owned adset's insights into a leak-free history window and a
    holdout window, then scores both optimizers' predictions against realized
    CPA and app-share. Returns MAE/RMSE plus per-adset wins.
    """
    require_pro_subscription(payload.session_id)
    # Check credits before the expensive operation, deduct after it succeeds
    CreditService.require_credits(payload.session_id, amount=50)
    result = await BacktestRunner.run(payload)
    CreditService.spend_credits(payload.session_id, amount=50)
    return result


@app.post("/optimize/suggestions", response_model=OptimizerSuggestion, tags=["ai"])
async def get_optimization_suggestions(request: OptimizeRequest) -> OptimizerSuggestion:
    require_pro_subscription(request.session_id)
    CreditService.require_credits(request.session_id, amount=15)
    suggestion, label = await ClaudeOptimizer.get_suggestions_with_meta(request)
    CreditService.spend_credits(request.session_id, amount=15)
    session_record = get_session_record(request.session_id)
    record_optimizer_run(
        session_id=request.session_id,
        ad_account_id=session_record.get("ad_account_id") if session_record else None,
        campaign_name=request.name,
        event=request.event.value,
        optimizer=label,
        request_json=request.model_dump_json(),
        suggestion_json=suggestion.model_dump_json(),
        used_fallback=label != OPTIMIZER_LABEL_CLAUDE,
    )
    return suggestion


def require_ingest_subscription(payload: IngestInsightsRequest) -> dict:
    return require_pro_subscription(payload.session_id)


@app.post(
    "/analytics/ingest", response_model=IngestInsightsResponse, tags=["analytics"]
)
async def ingest_campaign_insights(
    payload: IngestInsightsRequest,
    _: dict = Depends(require_ingest_subscription),
) -> IngestInsightsResponse:
    owner = require_adset_owner(payload.session_id, payload.adset_id)
    AnalyticsService.ingest_insights(
        payload.adset_id,
        payload.insights,
        session_id=payload.session_id,
        ad_account_id=owner.get("ad_account_id"),
    )
    return IngestInsightsResponse(status="ingested", count=len(payload.insights))


class SyncRequest(BaseModel):
    session_id: str


def require_sync_subscription(payload: SyncRequest) -> dict:
    return require_pro_subscription(payload.session_id)


@app.post("/analytics/sync/{adset_id}", tags=["analytics"])
async def sync_insights(
    adset_id: str,
    payload: SyncRequest,
    _: dict = Depends(require_sync_subscription),
) -> dict[str, int | str]:
    require_adset_owner(payload.session_id, adset_id)
    CreditService.require_credits(payload.session_id, amount=20)
    result = await InsightsService.sync_adset_insights(payload.session_id, adset_id)
    CreditService.spend_credits(payload.session_id, amount=20)
    return result


@app.get(
    "/dashboard/ccco/{adset_id}", response_model=DashboardResponse, tags=["dashboard"]
)
async def get_ccco_dashboard(
    adset_id: str,
    session_id: str,
    _: dict = Depends(require_pro_subscription),
) -> DashboardResponse:
    require_adset_owner(session_id, adset_id)
    return AnalyticsService.get_dashboard(adset_id)


@app.get("/dashboard/summary", response_model=DashboardSummary, tags=["dashboard"])
async def get_dashboard_summary(session_id: str) -> DashboardSummary:
    return await DashboardService.get_summary(session_id)


@app.post("/creative/generate", response_model=list[CreativeVariant], tags=["creative"])
async def generate_creatives(
    request: CreativeGenerateRequest,
    _: dict = Depends(require_creative_subscription),
) -> list[CreativeVariant]:
    CreditService.require_credits(request.session_id, amount=25)
    variants = CreativeStudio.generate_creatives(request)
    CreditService.spend_credits(request.session_id, amount=25)
    return variants


def require_query_subscription(session_id: str) -> dict:
    return require_pro_subscription(session_id)


@app.get("/migration/scan", response_model=list[MigrationCandidate], tags=["migration"])
async def scan_for_migration(
    session_id: str,
    _: dict = Depends(require_query_subscription),
) -> list[MigrationCandidate]:
    CreditService.require_credits(session_id, amount=30)
    candidates = await MigrationService.scan_for_migration(session_id)
    CreditService.spend_credits(session_id, amount=30)
    return candidates


@app.post(
    "/migration/plan/{old_campaign_id}",
    response_model=MigrationPlan,
    tags=["migration"],
)
async def plan_migration(
    old_campaign_id: str,
    new_name: str,
    session_id: str,
    _: dict = Depends(require_query_subscription),
) -> MigrationPlan:
    CreditService.require_credits(session_id, amount=30)
    plan = await MigrationService.plan_migration(session_id, old_campaign_id, new_name)
    CreditService.spend_credits(session_id, amount=30)
    return plan


# ---------------------------------------------------------------------------
# AI Provider endpoints
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    provider: str | None = None  # If None, smart-route automatically


class ChatResponse(BaseModel):
    response: str
    provider_used: str
    routing_note: str


class SaveKeyRequest(BaseModel):
    provider: str
    key: str


class KeyStatusResponse(BaseModel):
    provider: str
    configured: bool
    label: str | None = None


@app.get("/ai/providers", tags=["ai"])
async def get_ai_providers() -> list[dict]:
    """List all registered AI providers with their status and capabilities."""
    return list_providers()


@app.post("/ai/chat", response_model=ChatResponse, tags=["ai"])
async def ai_chat(request: ChatRequest) -> ChatResponse:
    """Send a message to the best available AI provider.

    If ``provider`` is specified, that provider is used directly.
    Otherwise, the message is classified and routed to the most capable
    available provider (Claude for analysis, OpenAI for creative).
    """
    if request.provider:
        from app.ai_providers import get_provider

        provider = get_provider(request.provider)
        if provider is None:
            raise HTTPException(
                status_code=404, detail=f"Unknown provider: {request.provider}"
            )
        if not provider.is_available():
            raise HTTPException(
                status_code=503,
                detail=f"{provider.display_name()} is not available. Configure its API key in Settings.",
            )
        response = provider.chat(request.message)
        return ChatResponse(
            response=response,
            provider_used=request.provider,
            routing_note=f"forced route to {request.provider}",
        )

    # Smart routing
    provider, note = route_query(request.message)
    if provider is None:
        return ChatResponse(
            response="No AI provider is available. Configure API keys in **Settings > Integrations > AI Providers**.",
            provider_used="none",
            routing_note=note,
        )
    response = provider.chat(request.message)
    return ChatResponse(
        response=response,
        provider_used=provider.config.name,
        routing_note=note,
    )


@app.get("/ai/keys", tags=["ai"])
async def get_ai_keys() -> list[dict]:
    """List stored provider keys (metadata only)."""
    return list_keys()


@app.post("/ai/keys", tags=["ai"])
async def save_ai_key(request: SaveKeyRequest) -> dict:
    """Save an AI provider API key (validates before saving, but saves even if
    validation fails so users can configure keys offline)."""
    from app.key_manager import save_key

    save_key(request.provider, request.key)
    # Attempt validation in background; ignore failures
    try:
        success, message = validate_and_save_key(request.provider, request.key)
        return {"status": "saved", "message": message}
    except Exception:
        return {"status": "saved", "message": f"Key saved for {request.provider}"}


@app.delete("/ai/keys/{provider}", tags=["ai"])
async def delete_ai_key(provider: str) -> dict:
    """Remove a stored AI provider API key."""
    deleted = delete_key(provider)
    return {"status": "deleted" if deleted else "not_found"}


@app.get("/ai/keys/{provider}/status", response_model=KeyStatusResponse, tags=["ai"])
async def ai_key_status(provider: str) -> KeyStatusResponse:
    """Check whether a provider has a key configured."""
    from app.ai_providers import get_provider

    configured = has_key(provider)
    prov = get_provider(provider)
    label = None
    if configured:
        keys = list_keys()
        for k in keys:
            if k["provider"] == provider:
                label = k.get("label")
                break
    return KeyStatusResponse(
        provider=provider,
        configured=configured,
        label=label,
    )


@app.get("/credits/balance", tags=["billing"])
async def get_credits_balance(session_id: str) -> dict[str, int]:
    return {"credits_balance": CreditService.get_balance(session_id)}
