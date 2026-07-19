from pydantic import BaseModel, Field

from app.database import get_db, init_db
from app.utils.logging import structlog

logger = structlog.get_logger()


class InsightRecord(BaseModel):
    adset_id: str
    date: str
    conversions_web: int = Field(..., ge=0)
    conversions_app: int = Field(..., ge=0)
    spend: float = Field(..., ge=0)
    cpa: float = Field(..., ge=0)
    channel_split_web: float = Field(..., ge=0, le=100)
    channel_split_app: float = Field(..., ge=0, le=100)


class IngestInsightsRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    adset_id: str
    insights: list[InsightRecord]


class IngestInsightsResponse(BaseModel):
    status: str
    count: int


class DashboardResponse(BaseModel):
    adset_id: str
    total_conversions: int
    total_spend: float
    avg_cpa: float
    ccco_lift_percent: float
    channel_breakdown: dict[str, float]
    daily_insights: list[InsightRecord]


class AnalyticsService:
    @staticmethod
    def ingest_insights(
        adset_id: str,
        insights: list[InsightRecord],
        *,
        session_id: str | None = None,
        ad_account_id: str | None = None,
    ) -> None:
        init_db()
        with get_db() as conn:
            if session_id is None or ad_account_id is None:
                row = conn.execute(
                    "SELECT session_id, ad_account_id FROM ccco_campaigns WHERE adset_id = ?",
                    (adset_id,),
                ).fetchone()
                if row:
                    session_id = session_id or row["session_id"]
                    ad_account_id = ad_account_id or row["ad_account_id"]
            for insight in insights:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO campaign_insights
                    (adset_id, date, conversions_web, conversions_app, spend, cpa,
                     channel_split_web, channel_split_app, session_id, ad_account_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        adset_id,
                        insight.date,
                        insight.conversions_web,
                        insight.conversions_app,
                        insight.spend,
                        insight.cpa,
                        insight.channel_split_web,
                        insight.channel_split_app,
                        session_id,
                        ad_account_id,
                    ),
                )
            conn.commit()
        logger.info(
            "insights_ingested",
            adset_id=adset_id,
            count=len(insights),
            session_scoped=session_id is not None,
        )

    @staticmethod
    def get_dashboard(adset_id: str) -> DashboardResponse:
        init_db()
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT * FROM campaign_insights
                WHERE adset_id = ? ORDER BY date DESC LIMIT 30
                """,
                (adset_id,),
            ).fetchall()

        if not rows:
            return DashboardResponse(
                adset_id=adset_id,
                total_conversions=0,
                total_spend=0.0,
                avg_cpa=0.0,
                ccco_lift_percent=0.0,
                channel_breakdown={"web": 0.0, "app": 0.0},
                daily_insights=[],
            )

        daily_insights = [InsightRecord(**dict(row)) for row in rows]
        total_web = sum(item.conversions_web for item in daily_insights)
        total_app = sum(item.conversions_app for item in daily_insights)
        total_conversions = total_web + total_app
        total_spend = round(sum(item.spend for item in daily_insights), 2)
        avg_cpa = round(total_spend / total_conversions, 2) if total_conversions else 0.0

        if total_conversions:
            channel_breakdown = {
                "web": round((total_web / total_conversions) * 100, 2),
                "app": round((total_app / total_conversions) * 100, 2),
            }
        else:
            channel_breakdown = {"web": 0.0, "app": 0.0}

        baseline_cpa = 16.0
        ccco_lift_percent = round(((baseline_cpa - avg_cpa) / baseline_cpa) * 100, 2) if avg_cpa else 0.0

        return DashboardResponse(
            adset_id=adset_id,
            total_conversions=total_conversions,
            total_spend=total_spend,
            avg_cpa=avg_cpa,
            ccco_lift_percent=ccco_lift_percent,
            channel_breakdown=channel_breakdown,
            daily_insights=daily_insights,
        )

    @staticmethod
    def get_aggregated_stats(
        *,
        session_id: str | None = None,
        ad_account_id: str | None = None,
    ) -> dict:
        """Owner-scoped 30-day rollup of spend, conversions, and CCCO lift.

        ``session_id`` is required for tenant safety. Callers that pass ``None``
        get a zeroed result rather than reading the global table.
        """
        init_db()
        if not session_id:
            return {
                "total_spend": 0.0,
                "total_conversions": 0,
                "avg_lift": 0.0,
                "last_synced": None,
            }
        with get_db() as conn:
            row = conn.execute(
                """
                SELECT
                    COALESCE(SUM(spend), 0) as total_spend,
                    COALESCE(SUM(conversions_web + conversions_app), 0) as total_conversions,
                    MAX(date) as last_synced
                FROM campaign_insights
                WHERE session_id IS :sid
                  AND ad_account_id IS :acc
                  AND date >= date('now', '-30 day')
                """,
                {"sid": session_id, "acc": ad_account_id},
            ).fetchone()

        total_spend = float(row["total_spend"] or 0)
        total_conversions = int(row["total_conversions"] or 0)
        avg_cpa = total_spend / total_conversions if total_conversions else 0
        baseline_cpa = 16.0
        avg_lift = round(((baseline_cpa - avg_cpa) / baseline_cpa) * 100, 2) if avg_cpa else 0.0
        return {
            "total_spend": round(total_spend, 2),
            "total_conversions": total_conversions,
            "avg_lift": avg_lift,
            "last_synced": row["last_synced"],
        }
