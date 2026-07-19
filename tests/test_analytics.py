import importlib

from app.analytics import AnalyticsService, InsightRecord


def test_analytics_ingest_and_dashboard_aggregation(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "campaigns.db"
    monkeypatch.setenv("CCCO_DB_PATH", str(db_path))

    import app.database as database
    import app.analytics as analytics

    database = importlib.reload(database)
    analytics = importlib.reload(analytics)
    database.init_db()

    insights = [
        InsightRecord(
            adset_id="238500000000001",
            date="2026-05-11",
            conversions_web=10,
            conversions_app=20,
            spend=300.0,
            cpa=10.0,
            channel_split_web=33.33,
            channel_split_app=66.67,
        ),
        InsightRecord(
            adset_id="238500000000001",
            date="2026-05-12",
            conversions_web=5,
            conversions_app=15,
            spend=200.0,
            cpa=10.0,
            channel_split_web=25.0,
            channel_split_app=75.0,
        ),
    ]

    analytics.AnalyticsService.ingest_insights("238500000000001", insights)
    dashboard = analytics.AnalyticsService.get_dashboard("238500000000001")

    assert dashboard.total_conversions == 50
    assert dashboard.total_spend == 500.0
    assert dashboard.avg_cpa == 10.0
    assert dashboard.channel_breakdown == {"web": 30.0, "app": 70.0}
    assert len(dashboard.daily_insights) == 2


def test_dashboard_without_insights_returns_zeros_not_demo_data(tmp_path, monkeypatch) -> None:
    """An owned ad set with no synced insights must return zeros, not the old
    1247-conversion / $15k demo stub. Real evidence-grade measurement cannot
    rely on impressive-looking placeholder metrics."""
    db_path = tmp_path / "campaigns.db"
    monkeypatch.setenv("CCCO_DB_PATH", str(db_path))

    import app.database as database
    import app.analytics as analytics

    database = importlib.reload(database)
    analytics = importlib.reload(analytics)
    database.init_db()

    dashboard = analytics.AnalyticsService.get_dashboard("missing-adset")

    assert dashboard.total_conversions == 0
    assert dashboard.total_spend == 0.0
    assert dashboard.avg_cpa == 0.0
    assert dashboard.ccco_lift_percent == 0.0
    assert dashboard.channel_breakdown == {"web": 0.0, "app": 0.0}
    assert dashboard.daily_insights == []
