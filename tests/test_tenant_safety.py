"""Tenant-safety tests: cross-account leakage prevention.

These tests prove that one operator's session cannot read or write another
operator's campaign data. They exercise the `require_adset_owner` helper plus
the scoped query path used by listing / dashboard / ingest / sync.
"""

import asyncio
import importlib

import pytest
from fastapi import HTTPException

from app.auth import active_sessions


def _reset(tmp_path, monkeypatch):
    db_path = tmp_path / "campaigns.db"
    monkeypatch.setenv("CCCO_DB_PATH", str(db_path))

    import app.analytics as analytics
    import app.database as database
    import app.dependencies as dependencies
    import app.main as main_mod

    database = importlib.reload(database)
    analytics = importlib.reload(analytics)
    dependencies = importlib.reload(dependencies)
    main_mod = importlib.reload(main_mod)
    database.init_db()
    return database, analytics, dependencies, main_mod


def _seed_two_tenants(database):
    """Two Pro tenants each owning one adset, with rows in `campaign_insights`."""
    active_sessions["tenant-A"] = {
        "access_token": "tok-A",
        "ad_account_id": "act_A",
        "ad_accounts": [{"id": "act_A"}],
        "subscription_tier": "pro",
    }
    active_sessions["tenant-B"] = {
        "access_token": "tok-B",
        "ad_account_id": "act_B",
        "ad_accounts": [{"id": "act_B"}],
        "subscription_tier": "pro",
    }
    database.save_ccco_campaign(
        adset_id="adset-A",
        name="Tenant A Spring",
        event="PURCHASE",
        pixel_id="111",
        application_id="222",
        web_url="https://a.example.com",
        session_id="tenant-A",
        ad_account_id="act_A",
    )
    database.save_ccco_campaign(
        adset_id="adset-B",
        name="Tenant B Spring",
        event="PURCHASE",
        pixel_id="333",
        application_id="444",
        web_url="https://b.example.com",
        session_id="tenant-B",
        ad_account_id="act_B",
    )


def test_require_adset_owner_returns_row_for_owner(tmp_path, monkeypatch) -> None:
    database, _, dependencies, _ = _reset(tmp_path, monkeypatch)
    _seed_two_tenants(database)

    row = dependencies.require_adset_owner("tenant-A", "adset-A")
    assert row["adset_id"] == "adset-A"
    assert row["session_id"] == "tenant-A"
    assert row["ad_account_id"] == "act_A"


def test_require_adset_owner_404s_on_other_tenant_adset(tmp_path, monkeypatch) -> None:
    database, _, dependencies, _ = _reset(tmp_path, monkeypatch)
    _seed_two_tenants(database)

    with pytest.raises(HTTPException) as exc:
        dependencies.require_adset_owner("tenant-A", "adset-B")
    assert exc.value.status_code == 404


def test_require_adset_owner_404s_on_unknown_adset(tmp_path, monkeypatch) -> None:
    database, _, dependencies, _ = _reset(tmp_path, monkeypatch)
    _seed_two_tenants(database)

    with pytest.raises(HTTPException) as exc:
        dependencies.require_adset_owner("tenant-A", "does-not-exist")
    assert exc.value.status_code == 404


def test_campaign_listing_endpoint_is_scoped_to_owner(tmp_path, monkeypatch) -> None:
    database, _, _, main_mod = _reset(tmp_path, monkeypatch)
    _seed_two_tenants(database)

    a_results = asyncio.run(main_mod.get_ccco_campaigns(session_id="tenant-A"))
    b_results = asyncio.run(main_mod.get_ccco_campaigns(session_id="tenant-B"))

    a_ids = {r.adset_id for r in a_results}
    b_ids = {r.adset_id for r in b_results}
    assert a_ids == {"adset-A"}
    assert b_ids == {"adset-B"}
    assert a_ids.isdisjoint(b_ids)


def test_dashboard_endpoint_404s_for_non_owner(tmp_path, monkeypatch) -> None:
    database, _, _, main_mod = _reset(tmp_path, monkeypatch)
    _seed_two_tenants(database)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            main_mod.get_ccco_dashboard(adset_id="adset-B", session_id="tenant-A")
        )
    assert exc.value.status_code == 404


def test_dashboard_endpoint_allows_owner(tmp_path, monkeypatch) -> None:
    database, _, _, main_mod = _reset(tmp_path, monkeypatch)
    _seed_two_tenants(database)

    response = asyncio.run(
        main_mod.get_ccco_dashboard(adset_id="adset-A", session_id="tenant-A")
    )
    assert response.adset_id == "adset-A"


def test_ingest_endpoint_rejects_writes_to_other_tenants_adset(
    tmp_path, monkeypatch
) -> None:
    database, analytics, _, main_mod = _reset(tmp_path, monkeypatch)
    _seed_two_tenants(database)

    insights = [
        analytics.InsightRecord(
            adset_id="adset-B",
            date="2026-05-12",
            conversions_web=999,
            conversions_app=999,
            spend=99999.0,
            cpa=0.5,
            channel_split_web=50.0,
            channel_split_app=50.0,
        )
    ]
    payload = analytics.IngestInsightsRequest(
        session_id="tenant-A",
        adset_id="adset-B",
        insights=insights,
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(main_mod.ingest_campaign_insights(payload=payload))
    assert exc.value.status_code == 404

    # And the poisonous rows must not have made it into the table.
    with database.get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM campaign_insights WHERE adset_id = ?",
            ("adset-B",),
        ).fetchone()
    assert row["c"] == 0


def test_sync_endpoint_rejects_other_tenants_adset(tmp_path, monkeypatch) -> None:
    database, _, _, main_mod = _reset(tmp_path, monkeypatch)
    _seed_two_tenants(database)

    class _Payload:
        session_id = "tenant-A"

    with pytest.raises(HTTPException) as exc:
        asyncio.run(main_mod.sync_insights(adset_id="adset-B", payload=_Payload()))
    assert exc.value.status_code == 404


def _seed_summary_data(
    database, *, spend, conversions, session_id, ad_account_id, adset_id
):
    """Insert one ACTIVE campaign + one insights row scoped to the given tenant."""
    database.save_ccco_campaign(
        adset_id=adset_id,
        name=f"{session_id} Spring",
        event="PURCHASE",
        pixel_id="111",
        application_id="222",
        web_url=f"https://{session_id}.example.com",
        status="ACTIVE",
        session_id=session_id,
        ad_account_id=ad_account_id,
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
                adset_id,
                "2026-07-01",
                conversions // 2,
                conversions - conversions // 2,
                spend,
                spend / conversions if conversions else 0,
                50.0,
                50.0,
                session_id,
                ad_account_id,
            ),
        )
        conn.commit()


def test_dashboard_summary_is_scoped_to_owner(tmp_path, monkeypatch) -> None:
    database, _, _, main_mod = _reset(tmp_path, monkeypatch)
    _seed_two_tenants(database)

    import app.dashboard as dashboard_mod
    from types import SimpleNamespace

    async def _no_migration(session_id: str):
        return []

    monkeypatch.setattr(
        dashboard_mod.MigrationService,
        "scan_for_migration",
        staticmethod(_no_migration),
    )
    monkeypatch.setattr(dashboard_mod, "AnalyticsService", main_mod.AnalyticsService)

    _seed_summary_data(
        database,
        spend=500.0,
        conversions=20,
        session_id="tenant-A",
        ad_account_id="act_A",
        adset_id="adset-A-summary",
    )
    _seed_summary_data(
        database,
        spend=99999.0,
        conversions=200,
        session_id="tenant-B",
        ad_account_id="act_B",
        adset_id="adset-B-summary",
    )

    a_summary = asyncio.run(dashboard_mod.DashboardService.get_summary("tenant-A"))
    b_summary = asyncio.run(dashboard_mod.DashboardService.get_summary("tenant-B"))

    # Tenant A must see only its own row (one seeded above plus one from the
    # tenant fixture, both owned by act_A). Critically, it must not see B's
    # $99,999 of spend or B's campaign names.
    a_recent_names = {row["name"] for row in a_summary.recent_campaigns}
    b_recent_names = {row["name"] for row in b_summary.recent_campaigns}
    assert "tenant-B Spring" not in a_recent_names
    assert "tenant-A Spring" not in b_recent_names

    assert a_summary.total_spend_last_30d == 500.0
    assert b_summary.total_spend_last_30d == 99999.0
    assert a_summary.total_campaigns < b_summary.total_campaigns + 99  # sanity
    assert a_summary.total_campaigns >= 1
    assert b_summary.total_campaigns >= 1
    # Total spend must never bleed across tenants.
    assert a_summary.total_spend_last_30d != b_summary.total_spend_last_30d


def test_owned_adset_with_no_insights_returns_zeros_not_fake(
    tmp_path, monkeypatch
) -> None:
    """The fake demo dashboard (1247 conversions / $15k spend) used to leak out
    of /dashboard/ccco/{adset_id} for any owned adset without insights. After
    the fix it must return zeros and an empty daily_insights list."""
    database, _, _, main_mod = _reset(tmp_path, monkeypatch)
    _seed_two_tenants(database)

    response = asyncio.run(
        main_mod.get_ccco_dashboard(adset_id="adset-A", session_id="tenant-A")
    )
    assert response.adset_id == "adset-A"
    assert response.total_conversions == 0
    assert response.total_spend == 0.0
    assert response.avg_cpa == 0.0
    assert response.ccco_lift_percent == 0.0
    assert response.channel_breakdown == {"web": 0.0, "app": 0.0}
    assert response.daily_insights == []
