import asyncio

from app.auth import active_sessions


def test_scan_for_migration_filters_non_ccco_campaigns(monkeypatch) -> None:
    import app.migration as migration

    active_sessions["migration-session"] = {
        "access_token": "token",
        "ad_account_id": "act_1",
        "ad_accounts": [{"id": "act_1"}],
        "subscription_tier": "pro",
    }

    class FakeCampaign:
        def __init__(self, campaign_id: str, name: str, promoted_object: dict) -> None:
            self._id = campaign_id
            self._data = {"id": campaign_id, "name": name, "promoted_object": promoted_object}

        def get_id(self) -> str:
            return self._id

        def get(self, key: str, default=None):
            return self._data.get(key, default)

        def __str__(self) -> str:
            return str(self._data)

    class FakeAdAccount:
        def __init__(self, ad_account_id: str, api=None) -> None:
            self.ad_account_id = ad_account_id
            self.api = api

        def get_campaigns(self, fields: list[str]) -> list[FakeCampaign]:
            return [
                FakeCampaign("111", "Web Only", {"pixel_id": "456"}),
                FakeCampaign("222", "Already CCCO", {"omnichannel_object": {"app": [], "pixel": []}}),
            ]

    class FakeMetaClient:
        def __init__(self, access_token: str) -> None:
            self.access_token = access_token

        def get_api(self):
            return "fake-api"

    monkeypatch.setattr(migration, "MetaClient", FakeMetaClient)
    monkeypatch.setattr(migration.MigrationService, "_get_adaccount_class", staticmethod(lambda: FakeAdAccount))

    candidates = asyncio.run(migration.MigrationService.scan_for_migration("migration-session"))

    assert len(candidates) == 1
    assert candidates[0].campaign_id == "111"
    assert candidates[0].name == "Web Only"
    assert candidates[0].current_type == "web_only"
    assert candidates[0].expected_cpa_lift_percent == 28.0


def test_migrate_campaign_returns_ready_plan() -> None:
    import app.migration as migration

    active_sessions["migration-session"] = {
        "access_token": "token",
        "ad_account_id": "act_1",
        "ad_accounts": [{"id": "act_1"}],
        "subscription_tier": "pro",
    }

    plan = asyncio.run(
        migration.MigrationService.plan_migration(
            "migration-session",
            "111",
            "CCCO Upgrade",
        )
    )

    assert plan.old_campaign_id == "111"
    assert plan.new_name == "CCCO Upgrade"
    assert plan.status == "ready_for_inputs"
    assert "promoted_object" in plan.recommended_config
    assert "recommended_omnichannel_config" in plan.recommended_config
