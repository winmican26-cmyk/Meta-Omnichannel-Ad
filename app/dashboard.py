from pydantic import BaseModel

from app.analytics import AnalyticsService
from app.auth import get_session
from app.credits import CreditService
from app.database import get_db, init_db
from app.migration import MigrationService
from app.templates import TemplatesService


class DashboardSummary(BaseModel):
    total_campaigns: int
    active_campaigns: int
    total_spend_last_30d: float
    avg_ccco_lift: float
    recent_campaigns: list[dict]
    recent_templates: list[dict]
    migration_candidates_count: int
    subscription_tier: str
    credits_balance: int
    last_synced: str | None


class DashboardService:
    @staticmethod
    async def get_summary(session_id: str) -> DashboardSummary:
        """Owner-scoped product summary.

        Every aggregate is filtered by ``(session_id, ad_account_id)`` so one
        operator never sees another's campaign counts, recent campaigns, spend,
        or lift. See [[feedback-tenant-safety-first]].
        """
        session = get_session(session_id)
        ad_account_id = session.get("ad_account_id") if isinstance(session, dict) else None
        init_db()
        with get_db() as conn:
            campaign_counts = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    COALESCE(SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END), 0) as active
                FROM ccco_campaigns
                WHERE session_id IS :sid AND ad_account_id IS :acc
                """,
                {"sid": session_id, "acc": ad_account_id},
            ).fetchone()
            recent_campaign_rows = conn.execute(
                """
                SELECT adset_id, name, event, status, created_at
                FROM ccco_campaigns
                WHERE session_id IS :sid AND ad_account_id IS :acc
                ORDER BY created_at DESC
                LIMIT 5
                """,
                {"sid": session_id, "acc": ad_account_id},
            ).fetchall()

        templates = TemplatesService.list_templates(session_id)[:5]
        analytics = AnalyticsService.get_aggregated_stats(
            session_id=session_id, ad_account_id=ad_account_id
        )

        try:
            migration_candidates = await MigrationService.scan_for_migration(session_id)
        except Exception:
            migration_candidates = []

        return DashboardSummary(
            total_campaigns=int(campaign_counts["total"] or 0),
            active_campaigns=int(campaign_counts["active"] or 0),
            total_spend_last_30d=analytics["total_spend"],
            avg_ccco_lift=analytics["avg_lift"],
            recent_campaigns=[dict(row) for row in recent_campaign_rows],
            recent_templates=[template.model_dump() for template in templates],
            migration_candidates_count=len(migration_candidates),
            subscription_tier=session.get("subscription_tier", "free"),
            credits_balance=CreditService.get_balance(session_id),
            last_synced=analytics.get("last_synced"),
        )
