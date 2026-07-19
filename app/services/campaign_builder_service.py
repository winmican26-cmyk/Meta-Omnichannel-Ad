"""Campaign Builder service — wizard-based campaign creation.

Hides Meta-specific terminology behind business-friendly labels. Manages the
full lifecycle: create draft → update step → validate → launch.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException

from app.auth import get_session
from app.database import (
    create_campaign_draft,
    delete_campaign_draft,
    get_campaign_draft,
    list_campaign_drafts,
    mark_campaign_draft_complete,
    update_campaign_draft_step,
)
from app.schemas.campaign import CampaignCreateRequest
from app.schemas.campaign_builder import (
    OBJECTIVE_TO_EVENT,
    STEP_REQUIRED_FIELDS,
    STEP_SCHEMA_MAP,
    CampaignObjective,
    CreativeStep,
    DraftListItem,
)
from app.services.campaign_service import CampaignService
from app.utils.logging import structlog
from app.models.omnichannel import (
    AppPromotedObject,
    OmnichannelObject,
    PixelPromotedObject,
)

logger = structlog.get_logger()


class CampaignBuilderService:
    """Handles the campaign builder wizard lifecycle."""

    # ------------------------------------------------------------------
    # Draft management
    # ------------------------------------------------------------------

    @staticmethod
    def create_draft(session_id: str) -> dict:
        """Create a new empty campaign draft. Returns the draft info."""
        session = get_session(session_id)
        ad_account_id = session.get("ad_account_id")
        draft_id = create_campaign_draft(
            session_id=session_id, ad_account_id=ad_account_id
        )
        return {"draft_id": draft_id, "current_step": 1, "step_data": {}}

    @staticmethod
    def get_draft(draft_id: int, session_id: str) -> dict | None:
        """Get a draft by ID."""
        return get_campaign_draft(draft_id, session_id)

    @staticmethod
    def list_drafts(session_id: str) -> list[dict]:
        """List all drafts for a session with friendly labels."""
        session = get_session(session_id)
        ad_account_id = session.get("ad_account_id")
        drafts = list_campaign_drafts(
            session_id=session_id, ad_account_id=ad_account_id
        )
        result = []
        for d in drafts:
            sd = d.get("step_data", {}) if isinstance(d.get("step_data"), dict) else {}
            objective_data = sd.get("objective", {})
            creative_data = sd.get("creative", {})
            result.append(
                DraftListItem(
                    id=d["id"],
                    current_step=d.get("current_step", 1),
                    is_complete=bool(d.get("is_complete", False)),
                    step_data=sd,
                    created_at=d.get("created_at", ""),
                    updated_at=d.get("updated_at", ""),
                    objective_label=(
                        objective_data.get("label")
                        if isinstance(objective_data, dict)
                        else None
                    ),
                    campaign_name=(
                        creative_data.get("campaign_name")
                        if isinstance(creative_data, dict)
                        else None
                    ),
                ).model_dump()
            )
        return result

    @staticmethod
    def delete_draft(draft_id: int, session_id: str) -> bool:
        """Delete a draft."""
        return delete_campaign_draft(draft_id, session_id)

    # ------------------------------------------------------------------
    # Step management
    # ------------------------------------------------------------------

    @staticmethod
    def update_step(
        draft_id: int,
        session_id: str,
        step: str,
        step_data: dict[str, Any],
    ) -> dict:
        """Validate and persist data for a single wizard step."""
        if step not in STEP_SCHEMA_MAP:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown step '{step}'. Valid steps: {', '.join(STEP_SCHEMA_MAP.keys())}",
            )

        # Validate the step data using the corresponding Pydantic schema
        schema_cls = STEP_SCHEMA_MAP[step]
        try:
            validated = schema_cls(**step_data)
        except Exception as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Step '{step}' validation failed: {exc}",
            ) from exc

        # Load existing draft
        draft = get_campaign_draft(draft_id, session_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")

        existing_step_data: dict = draft.get("step_data", {})
        if isinstance(existing_step_data, str):
            existing_step_data = json.loads(existing_step_data)

        # Normalize step data before storing
        normalized = CampaignBuilderService._normalize_step_data(step, validated)

        # Merge into existing step data
        existing_step_data[step] = normalized

        # Calculate current step (stay on same step unless user advances)
        current_step = draft.get("current_step", 1)
        step_index = list(STEP_SCHEMA_MAP.keys()).index(step) + 1
        if step_index >= current_step:
            current_step = min(step_index + 1, len(STEP_SCHEMA_MAP))

        # Persist
        updated = update_campaign_draft_step(
            draft_id=draft_id,
            session_id=session_id,
            step_data=existing_step_data,
            current_step=current_step,
        )
        if not updated:
            raise HTTPException(
                status_code=404, detail="Draft not found or not owned by session"
            )

        return {
            "draft_id": draft_id,
            "current_step": current_step,
            "step_data": existing_step_data,
        }

    @staticmethod
    def validate_step(
        draft_id: int,
        session_id: str,
        step: str,
    ) -> dict:
        """Validate that a step has all required fields filled in."""
        if step not in STEP_SCHEMA_MAP:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown step '{step}'",
            )

        draft = get_campaign_draft(draft_id, session_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")

        step_data: dict = draft.get("step_data", {})
        if isinstance(step_data, str):
            step_data = json.loads(step_data)

        step_content = step_data.get(step, {})
        if not isinstance(step_content, dict):
            step_content = {}

        missing = []
        for field in STEP_REQUIRED_FIELDS.get(step, []):
            if (
                field not in step_content
                or step_content.get(field) is None
                or step_content.get(field) == ""
            ):
                missing.append(field)
            # Special case: empty string for id fields
            if (
                isinstance(step_content.get(field), str)
                and step_content[field].strip() == ""
            ):
                missing.append(field)

        return {
            "valid": len(missing) == 0,
            "missing_fields": missing,
            "step": step,
        }

    # ------------------------------------------------------------------
    # Launch
    # ------------------------------------------------------------------

    @staticmethod
    async def launch(draft_id: int, session_id: str) -> dict:
        """Convert a completed draft into a live campaign via Meta API."""
        draft = get_campaign_draft(draft_id, session_id)
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")

        step_data: dict = draft.get("step_data", {})
        if isinstance(step_data, str):
            step_data = json.loads(step_data)

        # Validate all steps are complete
        for step_name in STEP_SCHEMA_MAP:
            if step_name not in step_data or not step_data[step_name]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot launch: Step '{step_name}' is incomplete",
                )

        # Extract step data
        objective_data = step_data.get("objective", {})
        audience_data = step_data.get("audience", {})
        budget_data = step_data.get("budget", {})
        creative_data = step_data.get("creative", {})

        # Map objective to event
        objective_str = objective_data.get("objective", "")
        try:
            objective = CampaignObjective(objective_str)
            event = OBJECTIVE_TO_EVENT[objective]
        except (ValueError, KeyError):
            raise HTTPException(
                status_code=400,
                detail=f"Unknown objective: {objective_str}",
            )

        # Build the OmnichannelObject
        campaign_name = creative_data.get("campaign_name", "Marketing OS Campaign")
        web_url = creative_data.get("web_url", "")
        application_id = creative_data.get("application_id", "")
        pixel_id = creative_data.get("pixel_id", "")
        page_id = creative_data.get("page_id", "")
        message = creative_data.get("message", "Shop now on web or app!")
        call_to_action = creative_data.get("call_to_action", "LEARN_MORE")
        countries = audience_data.get("countries", ["US"])
        daily_budget = budget_data.get("daily_budget_cents", 1000)
        bid_amount_cents = budget_data.get("bid_amount_cents")
        android_deeplink = creative_data.get("android_deeplink")
        ios_deeplink = creative_data.get("ios_deeplink")

        # Build app promoted object list
        app_objects = []
        pixel_objects = []
        app_store_url = (
            f"https://apps.apple.com/app/{application_id}"
            if application_id
            else "https://apps.apple.com/app/placeholder"
        )

        if application_id:
            app_objects.append(
                AppPromotedObject(
                    application_id=application_id,
                    custom_event_type=event,
                    object_store_urls=[app_store_url],
                )
            )

        if pixel_id:
            pixel_objects.append(
                PixelPromotedObject(
                    pixel_id=pixel_id,
                    custom_event_type=event,
                )
            )

        # Build the omnichannel object
        omnichannel = OmnichannelObject(
            app=app_objects
            or [
                AppPromotedObject(
                    application_id="placeholder",
                    custom_event_type=event,
                    object_store_urls=["https://apps.apple.com/app/placeholder"],
                )
            ],
            pixel=pixel_objects
            or [
                PixelPromotedObject(
                    pixel_id="placeholder",
                    custom_event_type=event,
                )
            ],
        )

        # Create the CampaignCreateRequest
        create_request = CampaignCreateRequest(
            name=campaign_name,
            session_id=session_id,
            page_id=page_id,
            daily_budget=daily_budget,
            event=event,
            omnichannel=omnichannel,
            pixel_id=pixel_id or "placeholder",
            application_id=application_id or "placeholder",
            web_url=web_url,
            message=message,
            countries=countries,
            android_deeplink=android_deeplink,
            ios_deeplink=ios_deeplink,
            bid_amount_cents=bid_amount_cents,
        )

        try:
            # Get session info for API call
            session = get_session(session_id)
            access_token = session.get("access_token")
            ad_account_id = session.get("ad_account_id")

            if not access_token or not ad_account_id:
                raise HTTPException(
                    status_code=400,
                    detail="No active Meta connection. Please connect your ad account in Settings.",
                )

            service = CampaignService(
                access_token=access_token,
                ad_account_id=ad_account_id,
            )
            result = await service.create_cross_channel_adset(
                name=create_request.name,
                daily_budget=create_request.daily_budget,
                event=create_request.event,
                omnichannel=create_request.omnichannel,
                pixel_id=create_request.pixel_id,
                application_id=create_request.application_id,
                page_id=create_request.page_id,
                web_url=str(create_request.web_url),
                message=create_request.message,
                countries=create_request.countries,
                android_deeplink=str(create_request.android_deeplink)
                if create_request.android_deeplink
                else None,
                ios_deeplink=str(create_request.ios_deeplink)
                if create_request.ios_deeplink
                else None,
                session_id=session_id,
                bid_amount_cents=create_request.bid_amount_cents,
            )

            # Mark draft as complete
            mark_campaign_draft_complete(draft_id=draft_id, session_id=session_id)

            logger.info(
                "campaign_launched_from_draft",
                draft_id=draft_id,
                adset_id=result.get("adset_id"),
                name=campaign_name,
            )

            return {
                "success": True,
                "adset_id": result.get("adset_id"),
                "creative_id": result.get("creative_id"),
                "ad_id": result.get("ad_id"),
                "message": f"Campaign '{campaign_name}' launched successfully!",
            }

        except HTTPException:
            raise
        except Exception as exc:
            logger.error(
                "campaign_launch_failed",
                draft_id=draft_id,
                error=str(exc),
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to launch campaign: {exc}",
            ) from exc

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_step_data(step: str, validated: Any) -> dict:
        """Convert validated Pydantic model to a serializable dict."""
        data = validated.model_dump()

        # Add friendly labels
        if step == "objective":
            data["label"] = validated.label()
            data["event"] = validated.to_event()
            data["meta"] = validated.metadata()

        if step == "creative":
            from app.schemas.campaign_builder import CTA_LABELS

            cta = data.get("call_to_action", "LEARN_MORE")
            data["call_to_action_label"] = CTA_LABELS.get(cta, cta)

        return data
