import importlib
import asyncio

from app.auth import active_sessions


def test_sync_adset_insights_persists_meta_rows(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "campaigns.db"
    monkeypatch.setenv("CCCO_DB_PATH", str(db_path))

    import app.database as database
    import app.meta_insights as meta_insights
    import app.services.meta_client as meta_client

    database = importlib.reload(database)
    meta_insights = importlib.reload(meta_insights)
    database.init_db()

    active_sessions["insights-session"] = {
        "access_token": "token",
        "ad_account_id": "act_1",
        "ad_accounts": [{"id": "act_1"}],
        "subscription_tier": "pro",
    }

    class FakeAdSet:
        def __init__(self, adset_id: str) -> None:
            self.adset_id = adset_id

        def get_insights(self, fields: list[str], params: dict) -> list[dict]:
            return [
                {
                    "date_start": "2026-05-12",
                    "spend": "120.0",
                    "actions": [
                        {"action_type": "offsite_conversion.purchase", "value": "8"},
                        {"action_type": "app_custom_event.fb_mobile_purchase", "value": "12"},
                    ],
                }
            ]

    monkeypatch.setattr(meta_client, "MetaClient", lambda access_token: None)
    monkeypatch.setattr(meta_insights.InsightsService, "_get_adset_class", staticmethod(lambda: FakeAdSet))

    result = asyncio.run(meta_insights.InsightsService.sync_adset_insights("insights-session", "238500000000001"))

    assert result == {"status": "synced", "records": 1}

    with database.get_db() as conn:
        row = conn.execute(
            "SELECT * FROM campaign_insights WHERE adset_id = ?",
            ("238500000000001",),
        ).fetchone()

    assert row["conversions_web"] == 8
    assert row["conversions_app"] == 12
    assert row["spend"] == 120.0
    assert row["cpa"] == 6.0
    assert row["channel_split_web"] == 40.0
    assert row["channel_split_app"] == 60.0
