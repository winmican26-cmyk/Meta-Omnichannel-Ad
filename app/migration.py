import asyncio
from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app.auth import get_session
from app.billing import PAID_TIERS
from app.services.meta_client import MetaClient
from app.utils.logging import structlog

logger = structlog.get_logger()


class MigrationCandidate(BaseModel):
    campaign_id: str
    name: str
    current_type: Literal["web_only", "app_only", "unknown"]
    suggested_event: str
    expected_cpa_lift_percent: float


class MigrationPlan(BaseModel):
    old_campaign_id: str
    new_name: str
    status: Literal["ready_for_inputs"]
    expected_cpa_lift_percent: float
    recommended_config: dict[str, Any]
    required_inputs: list[str] = Field(default_factory=list)


class MigrationService:
    @staticmethod
    def _get_adaccount_class():
        try:
            from facebook_business.adobjects.adaccount import AdAccount
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "facebook-business is required for migration scans. Install requirements.txt or run the Docker image."
            ) from exc
        return AdAccount

    @staticmethod
    def _require_paid_session(session_id: str) -> dict[str, Any]:
        session = get_session(session_id)
        if session.get("subscription_tier", "free") not in PAID_TIERS:
            raise HTTPException(status_code=402, detail="Pro subscription required for migration tools")
        return session

    @staticmethod
    def _campaign_get(campaign: Any, key: str, default: Any = None) -> Any:
        if isinstance(campaign, dict):
            return campaign.get(key, default)
        try:
            return campaign.get(key, default)
        except TypeError:
            return campaign.get(key) or default
        except AttributeError:
            return getattr(campaign, key, default)

    @staticmethod
    def _campaign_id(campaign: Any) -> str:
        if hasattr(campaign, "get_id"):
            return str(campaign.get_id())
        return str(MigrationService._campaign_get(campaign, "id", ""))

    @staticmethod
    def _infer_current_type(campaign: Any) -> Literal["web_only", "app_only", "unknown"]:
        payload = str(campaign).lower()
        if "pixel" in payload or "offsite" in payload or "website" in payload:
            return "web_only"
        if "application" in payload or "mobile_app" in payload or "app_install" in payload:
            return "app_only"
        return "unknown"

    @staticmethod
    async def scan_for_migration(session_id: str) -> list[MigrationCandidate]:
        session = MigrationService._require_paid_session(session_id)
        access_token = session.get("access_token")
        ad_account_id = session.get("ad_account_id")
        if not access_token or not ad_account_id:
            raise HTTPException(status_code=400, detail="Active access token and ad account are required")

        def _sync_scan():
            client = MetaClient(access_token)
            AdAccount = MigrationService._get_adaccount_class()
            account = AdAccount(ad_account_id, api=client.get_api())
            return account.get_campaigns(fields=["id", "name", "objective", "promoted_object"])

        campaigns = await asyncio.to_thread(_sync_scan)
        candidates: list[MigrationCandidate] = []
        for campaign in campaigns:
            promoted_object = MigrationService._campaign_get(campaign, "promoted_object", {}) or {}
            if "omnichannel_object" in promoted_object:
                continue
            candidates.append(
                MigrationCandidate(
                    campaign_id=MigrationService._campaign_id(campaign),
                    name=MigrationService._campaign_get(campaign, "name", "Untitled Campaign"),
                    current_type=MigrationService._infer_current_type(campaign),
                    suggested_event="PURCHASE",
                    expected_cpa_lift_percent=28.0,
                )
            )

        logger.info("migration_scan_completed", session_id=session_id, candidates=len(candidates))
        return candidates

    @staticmethod
    async def plan_migration(session_id: str, old_campaign_id: str, new_name: str) -> MigrationPlan:
        MigrationService._require_paid_session(session_id)
        return MigrationPlan(
            old_campaign_id=old_campaign_id,
            new_name=new_name,
            status="ready_for_inputs",
            expected_cpa_lift_percent=28.0,
            recommended_config={
                "name": new_name,
                "session_id": session_id,
                "event": "PURCHASE",
                "optimization_goal": "OFFSITE_CONVERSIONS",
                "billing_event": "IMPRESSIONS",
                "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                "applink_treatment": "deeplink_with_web_fallback",
                "promoted_object": {
                    "omnichannel_object": {
                        "app": ["<application_id + object_store_urls required>"],
                        "pixel": ["<pixel_id required>"],
                    }
                },
                "tracking_specs": ["offsite_conversion", "app_custom_event", "mobile_app_install"],
                "recommended_omnichannel_config": {
                    "app": [
                        {
                            "application_id": "<APPLICATION_ID>",
                            "custom_event_type": "PURCHASE",
                            "object_store_urls": ["<PLAY_STORE_OR_APP_STORE_URL>"],
                        }
                    ],
                    "pixel": [
                        {
                            "pixel_id": "<PIXEL_ID>",
                            "custom_event_type": "PURCHASE",
                        }
                    ],
                },
            },
            required_inputs=[
                "page_id",
                "pixel_id",
                "application_id",
                "object_store_urls",
                "web_url",
                "android_deeplink or ios_deeplink",
                "daily_budget",
            ],
        )
