import asyncio
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException

from app import database
from app.auth import get_session
from app.utils.logging import structlog

logger = structlog.get_logger()


class InsightsService:
    @staticmethod
    def _get_adset_class():
        try:
            from facebook_business.adobjects.adset import AdSet
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "facebook-business is required for Meta insights sync. Install requirements.txt or run the Docker image."
            ) from exc
        return AdSet

    @staticmethod
    def _get_facebook_request_error_class():
        try:
            from facebook_business.exceptions import FacebookRequestError
        except ModuleNotFoundError:
            return ()
        return (FacebookRequestError,)

    @staticmethod
    def _parse_conversions(actions: list[dict[str, Any]]) -> tuple[int, int]:
        conversions_web = 0
        conversions_app = 0
        for action in actions:
            action_type = str(action.get("action_type", "")).lower()
            value = int(float(action.get("value", 0) or 0))
            if "app_custom_event" in action_type or "mobile_app" in action_type:
                conversions_app += value
            elif "offsite_conversion" in action_type or action_type in {"purchase", "lead"}:
                conversions_web += value
        return conversions_web, conversions_app

    @staticmethod
    async def sync_adset_insights(session_id: str, adset_id: str) -> dict[str, int | str]:
        session = get_session(session_id)
        access_token = session.get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="No active access token for session")

        try:
            from app.services.meta_client import MetaClient

            since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            until = datetime.now().strftime("%Y-%m-%d")
            MetaClient(access_token)
            AdSet = InsightsService._get_adset_class()

            def _sync_fetch_insights():
                adset = AdSet(adset_id)
                return adset.get_insights(
                    fields=[
                        "date_start",
                        "date_stop",
                        "impressions",
                        "spend",
                        "actions",
                        "action_values",
                    ],
                    params={
                        "time_range": {"since": since, "until": until},
                        "time_increment": 1,
                        "level": "adset",
                    },
                )

            insights = await asyncio.to_thread(_sync_fetch_insights)
        except InsightsService._get_facebook_request_error_class() as exc:
            logger.error("meta_insights_request_failed", adset_id=adset_id, error=str(exc))
            raise
        except Exception as exc:
            logger.error("insights_sync_failed", adset_id=adset_id, error=str(exc))
            raise

        database.init_db()
        ad_account_id = session.get("ad_account_id") if isinstance(session, dict) else None
        records = 0
        with database.get_db() as conn:
            for insight in insights:
                actions = insight.get("actions", []) or []
                conversions_web, conversions_app = InsightsService._parse_conversions(actions)
                total_conversions = conversions_web + conversions_app
                spend = float(insight.get("spend", 0) or 0)
                cpa = spend / total_conversions if total_conversions else 0
                channel_split_web = round((conversions_web / total_conversions) * 100, 2) if total_conversions else 0
                channel_split_app = round((conversions_app / total_conversions) * 100, 2) if total_conversions else 0

                conn.execute(
                    """
                    INSERT OR REPLACE INTO campaign_insights
                    (adset_id, date, conversions_web, conversions_app, spend, cpa,
                     channel_split_web, channel_split_app, session_id, ad_account_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        adset_id,
                        insight["date_start"],
                        conversions_web,
                        conversions_app,
                        spend,
                        cpa,
                        channel_split_web,
                        channel_split_app,
                        session_id,
                        ad_account_id,
                    ),
                )
                records += 1
            conn.commit()

        logger.info("insights_synced", adset_id=adset_id, records=records)
        return {"status": "synced", "records": records}
