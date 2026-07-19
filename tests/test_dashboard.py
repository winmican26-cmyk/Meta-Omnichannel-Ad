import importlib
from types import SimpleNamespace

from app.auth import active_sessions


def test_dashboard_summary_returns_platform_overview(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "campaigns.db"
    monkeypatch.setenv("CCCO_DB_PATH", str(db_path))

    import app.database as database
    import app.dashboard as dashboard
    import app.migration as migration
    import app.templates as templates

    database = importlib.reload(database)
    templates = importlib.reload(templates)
    dashboard = importlib.reload(dashboard)
    database.init_db()

    active_sessions["summary-session"] = {
        "access_token": "token",
        "ad_account_id": "act_1",
        "ad_accounts": [{"id": "act_1"}],
        "subscription_tier": "pro",
    }

    database.save_ccco_campaign(
        adset_id="238500000000001",
        name="Spring Promo",
        event="PURCHASE",
        pixel_id="456",
        application_id="123",
        web_url="https://example.com",
        status="ACTIVE",
        session_id="summary-session",
        ad_account_id="act_1",
    )
    with database.get_db() as conn:
        conn.execute(
            """
            INSERT INTO campaign_insights
            (adset_id, date, conversions_web, conversions_app, spend, cpa,
             channel_split_web, channel_split_app, session_id, ad_account_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "238500000000001",
                "2026-07-01",
                10,
                10,
                200.0,
                10.0,
                50.0,
                50.0,
                "summary-session",
                "act_1",
            ),
        )
        conn.execute(
            """
            INSERT INTO campaign_templates (name, session_id, original_adset_id, config)
            VALUES (?, ?, ?, ?)
            """,
            ("Template One", "summary-session", "238500000000001", "{}"),
        )
        conn.commit()

    async def fake_scan(session_id: str):
        return [SimpleNamespace(campaign_id="111")]

    monkeypatch.setattr(
        dashboard.MigrationService, "scan_for_migration", staticmethod(fake_scan)
    )

    import asyncio

    summary = asyncio.run(dashboard.DashboardService.get_summary("summary-session"))

    assert summary.total_campaigns == 1
    assert summary.active_campaigns == 1
    assert summary.total_spend_last_30d == 200.0
    assert summary.avg_ccco_lift == 37.5
    assert summary.migration_candidates_count == 1
    assert summary.subscription_tier == "pro"
    assert summary.recent_templates[0]["name"] == "Template One"
