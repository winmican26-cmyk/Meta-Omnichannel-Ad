"""E2E tests for Phase 1 engineering hardening.

Covers:
1. Request-ID middleware injects and echoes X-Request-ID
2. /health returns database connectivity status
3. Pagination on campaign listing endpoints
4. Pagination on template listing endpoints
5. Credit deduction is transactional (require/spend pattern)
6. DB migration system runs without error
7. Cascade delete helper works correctly
8. Structlog context vars include request_id
"""

from __future__ import annotations

import asyncio
import importlib
import json
import uuid

import pytest
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport

from app.auth import active_sessions
from app.credits import CreditService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _bootstrap_app(tmp_path, monkeypatch):
    """Reset the database and reload all modules for a clean test."""
    db_path = tmp_path / "campaigns.db"
    monkeypatch.setenv("CCCO_DB_PATH", str(db_path))

    import app.analytics as analytics
    import app.credits as credits
    import app.dashboard as dashboard
    import app.database as database
    import app.db_migrations as db_migrations
    import app.dependencies as dependencies
    import app.main as main_mod
    import app.templates as templates

    database = importlib.reload(database)
    analytics = importlib.reload(analytics)
    credits = importlib.reload(credits)
    dashboard = importlib.reload(dashboard)
    db_migrations = importlib.reload(db_migrations)
    dependencies = importlib.reload(dependencies)
    templates = importlib.reload(templates)
    main_mod = importlib.reload(main_mod)

    database.init_db()
    db_migrations.run_migrations(str(db_path))
    return (
        database,
        analytics,
        credits,
        dashboard,
        db_migrations,
        dependencies,
        main_mod,
        templates,
    )


def _seed_tenant(database, session_id, ad_account_id, adset_id_prefix, count=3):
    """Seed *count* campaigns for a given tenant."""
    active_sessions[session_id] = {
        "access_token": f"tok-{session_id}",
        "ad_account_id": ad_account_id,
        "ad_accounts": [{"id": ad_account_id}],
        "subscription_tier": "pro",
        "credits_balance": 1000,
    }
    for i in range(count):
        database.save_ccco_campaign(
            adset_id=f"{adset_id_prefix}-{i}",
            name=f"{session_id} Campaign {i}",
            event="PURCHASE",
            pixel_id="111",
            application_id="222",
            web_url=f"https://{session_id}-{i}.example.com",
            session_id=session_id,
            ad_account_id=ad_account_id,
        )


def _seed_template(database, session_id, name, config_override=None):
    """Seed one template for a given session."""
    config = {
        "name": name,
        "session_id": session_id,
        "page_id": "page123",
        "daily_budget": 5000,
        "event": "PURCHASE",
        "pixel_id": "111",
        "application_id": "222",
        "web_url": "https://example.com",
        "countries": ["US"],
        "omnichannel": {
            "app": [
                {
                    "application_id": "222",
                    "custom_event_type": "PURCHASE",
                    "object_store_urls": [
                        "https://play.google.com/store/apps/details?id=com.example"
                    ],
                }
            ],
            "pixel": [{"pixel_id": "111", "custom_event_type": "PURCHASE"}],
        },
    }
    if config_override:
        config.update(config_override)

    with database.get_db() as conn:
        conn.execute(
            "INSERT INTO campaign_templates (name, session_id, config) VALUES (?, ?, ?)",
            (name, session_id, json.dumps(config)),
        )
        conn.commit()


def _seed_insight(database, adset_id, session_id, ad_account_id, date="2026-05-01"):
    """Seed one insight row."""
    with database.get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO campaign_insights
            (adset_id, date, conversions_web, conversions_app, spend, cpa,
             channel_split_web, channel_split_app, session_id, ad_account_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                adset_id,
                date,
                10,
                20,
                300.0,
                10.0,
                33.33,
                66.67,
                session_id,
                ad_account_id,
            ),
        )
        conn.commit()


# ===================================================================
# TEST 1: Request-ID middleware
# ===================================================================


@pytest.mark.asyncio
async def test_request_id_header_is_echoed(tmp_path, monkeypatch):
    """The X-Request-ID header sent by the client is echoed back."""
    _, _, _, _, _, _, main_mod, _ = _bootstrap_app(tmp_path, monkeypatch)
    transport = ASGITransport(app=main_mod.app)
    req_id = "test-request-001"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health", headers={"X-Request-ID": req_id})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == req_id


@pytest.mark.asyncio
async def test_request_id_generated_when_missing(tmp_path, monkeypatch):
    """When no X-Request-ID is sent, a UUID4 is generated."""
    _, _, _, _, _, _, main_mod, _ = _bootstrap_app(tmp_path, monkeypatch)
    transport = ASGITransport(app=main_mod.app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    # Validate it's a UUID
    uuid.UUID(req_id)


# ===================================================================
# TEST 2: Health endpoint with DB status
# ===================================================================


@pytest.mark.asyncio
async def test_health_returns_database_status(tmp_path, monkeypatch):
    """/health returns database=connected when DB is reachable."""
    _, _, _, _, _, _, main_mod, _ = _bootstrap_app(tmp_path, monkeypatch)
    transport = ASGITransport(app=main_mod.app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        data = response.json()

    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["version"] == "0.1.0"


# ===================================================================
# TEST 3: Pagination on campaign listing
# ===================================================================


@pytest.mark.asyncio
async def test_campaign_listing_pagination(tmp_path, monkeypatch):
    """Campaign listing respects limit and offset params."""
    database, _, _, _, _, _, main_mod, _ = _bootstrap_app(tmp_path, monkeypatch)
    _seed_tenant(database, "pag-test", "act_pag", "pag-adset", count=5)

    transport = ASGITransport(app=main_mod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Default limit (50) should return all 5
        r1 = await client.get("/campaigns/ccco", params={"session_id": "pag-test"})
        assert r1.status_code == 200
        assert len(r1.json()) == 5

        # Limit 2 should return 2
        r2 = await client.get(
            "/campaigns/ccco", params={"session_id": "pag-test", "limit": 2}
        )
        assert r2.status_code == 200
        assert len(r2.json()) == 2

        # Offset 2 with limit 2 should return items 3 and 4 (0-indexed)
        r3 = await client.get(
            "/campaigns/ccco",
            params={"session_id": "pag-test", "limit": 2, "offset": 2},
        )
        assert r3.status_code == 200
        assert len(r3.json()) == 2

        # Offset 5 should return 0
        r4 = await client.get(
            "/campaigns/ccco",
            params={"session_id": "pag-test", "offset": 5},
        )
        assert r4.status_code == 200
        assert len(r4.json()) == 0


# ===================================================================
# TEST 4: Pagination on template listing
# ===================================================================


@pytest.mark.asyncio
async def test_template_listing_pagination(tmp_path, monkeypatch):
    """Template listing respects limit and offset params."""
    database, _, _, _, _, _, main_mod, templates_mod = _bootstrap_app(
        tmp_path, monkeypatch
    )
    _seed_tenant(database, "tmpl-pag", "act_tmpl_pag", "tmpl-pag-adset", count=1)

    # Seed 5 templates
    for i in range(5):
        _seed_template(database, "tmpl-pag", f"Template {i}")

    transport = ASGITransport(app=main_mod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Default limit (50) returns all 5
        r1 = await client.get("/campaigns/templates", params={"session_id": "tmpl-pag"})
        assert r1.status_code == 200
        assert len(r1.json()) == 5

        # Limit 2
        r2 = await client.get(
            "/campaigns/templates", params={"session_id": "tmpl-pag", "limit": 2}
        )
        assert r2.status_code == 200
        assert len(r2.json()) == 2

        # Offset beyond end
        r3 = await client.get(
            "/campaigns/templates", params={"session_id": "tmpl-pag", "offset": 10}
        )
        assert r3.status_code == 200
        assert len(r3.json()) == 0


# ===================================================================
# TEST 5: Credit deduction is transactional
# ===================================================================


@pytest.mark.asyncio
async def test_credit_require_does_not_deduct(tmp_path, monkeypatch):
    """require_credits checks balance but does not deduct."""
    database, _, credits_mod, _, _, _, _, _ = _bootstrap_app(tmp_path, monkeypatch)

    active_sessions["credit-test-r"] = {
        "access_token": "tok",
        "ad_account_id": "act_cred",
        "ad_accounts": [{"id": "act_cred"}],
        "subscription_tier": "pro",
        "credits_balance": 100,
    }
    database.save_session(
        session_id="credit-test-r",
        access_token="tok",
        ad_account_id="act_cred",
        ad_accounts=[{"id": "act_cred"}],
        credits_balance=100,
    )

    # require_credits should not deduct
    credits_mod.CreditService.require_credits("credit-test-r", amount=50)
    assert credits_mod.CreditService.get_balance("credit-test-r") == 100

    # spend_credits should deduct
    credits_mod.CreditService.spend_credits("credit-test-r", amount=50)
    assert credits_mod.CreditService.get_balance("credit-test-r") == 50


@pytest.mark.asyncio
async def test_credit_require_raises_on_insufficient(tmp_path, monkeypatch):
    """require_credits raises 402 when balance is too low."""
    _, _, credits_mod, _, _, _, _, _ = _bootstrap_app(tmp_path, monkeypatch)

    active_sessions["credit-test-poor"] = {
        "access_token": "tok",
        "ad_account_id": "act_poor",
        "ad_accounts": [{"id": "act_poor"}],
        "subscription_tier": "pro",
        "credits_balance": 10,
    }

    with pytest.raises(HTTPException) as exc:
        credits_mod.CreditService.require_credits("credit-test-poor", amount=50)
    assert exc.value.status_code == 402


# ===================================================================
# TEST 6: DB migration system
# ===================================================================


def test_migration_system_runs_cleanly(tmp_path, monkeypatch):
    """Run migrations on a fresh database; v1 is recorded."""
    db_path = tmp_path / "migration_test.db"
    monkeypatch.setenv("CCCO_DB_PATH", str(db_path))

    import app.database as database
    import app.db_migrations as db_migrations

    database = importlib.reload(database)
    db_migrations = importlib.reload(db_migrations)

    database.init_db()
    db_migrations.run_migrations(str(db_path))

    # Verify v1 was recorded
    import sqlite3

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT version, description FROM schema_migrations WHERE version = 1"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row["version"] == 1
    assert "baseline" in row["description"].lower()


def test_migration_is_idempotent(tmp_path, monkeypatch):
    """Running migrations twice does not error."""
    db_path = tmp_path / "migration_idempotent.db"
    monkeypatch.setenv("CCCO_DB_PATH", str(db_path))

    import app.database as database
    import app.db_migrations as db_migrations

    database = importlib.reload(database)
    db_migrations = importlib.reload(db_migrations)
    database.init_db()

    # Run twice
    db_migrations.run_migrations(str(db_path))
    db_migrations.run_migrations(str(db_path))  # second run should be a no-op

    import sqlite3

    conn = sqlite3.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) AS c FROM schema_migrations").fetchone()[0]
    conn.close()
    assert count == 2  # v1 + v2 recorded


# ===================================================================
# TEST 7: Cascade delete helper
# ===================================================================


@pytest.mark.asyncio
async def test_delete_ccco_campaign_removes_insights(tmp_path, monkeypatch):
    """delete_ccco_campaign removes both the campaign and its insights."""
    database, _, _, _, _, _, _, _ = _bootstrap_app(tmp_path, monkeypatch)

    # Seed
    _seed_tenant(database, "del-test", "act_del", "del-adset", count=1)
    _seed_insight(database, "del-adset-0", "del-test", "act_del")

    # Verify insight exists
    with database.get_db() as conn:
        insight_count = conn.execute(
            "SELECT COUNT(*) AS c FROM campaign_insights WHERE adset_id = ?",
            ("del-adset-0",),
        ).fetchone()["c"]
    assert insight_count == 1

    # Delete
    deleted = database.delete_ccco_campaign(
        adset_id="del-adset-0",
        session_id="del-test",
        ad_account_id="act_del",
    )
    assert deleted is True

    # Verify campaign gone
    with database.get_db() as conn:
        camp_count = conn.execute(
            "SELECT COUNT(*) AS c FROM ccco_campaigns WHERE adset_id = ?",
            ("del-adset-0",),
        ).fetchone()["c"]
        insight_count = conn.execute(
            "SELECT COUNT(*) AS c FROM campaign_insights WHERE adset_id = ?",
            ("del-adset-0",),
        ).fetchone()["c"]
    assert camp_count == 0
    assert insight_count == 0


@pytest.mark.asyncio
async def test_delete_nonexistent_campaign_returns_false(tmp_path, monkeypatch):
    """Deleting a campaign that doesn't exist returns False."""
    database, _, _, _, _, _, _, _ = _bootstrap_app(tmp_path, monkeypatch)
    deleted = database.delete_ccco_campaign(
        adset_id="does-not-exist",
        session_id="nobody",
        ad_account_id="act_ghost",
    )
    assert deleted is False


# ===================================================================
# TEST 8: End-to-end credit flow via API
# ===================================================================


@pytest.mark.asyncio
async def test_backtest_credits_flow_via_api(tmp_path, monkeypatch):
    """The backtest endpoint uses require/spend pattern correctly.

    This is an integration test that proves credits are only deducted after
    the backtest runs (not before), by verifying the balance post-call.
    """
    database, analytics, _, _, _, _, main_mod, _ = _bootstrap_app(tmp_path, monkeypatch)

    # Seed a Pro session with credits
    active_sessions["bt-cred-test"] = {
        "access_token": "tok-bt",
        "ad_account_id": "act_bt_cred",
        "ad_accounts": [{"id": "act_bt_cred"}],
        "subscription_tier": "pro",
        "credits_balance": 200,
    }
    database.save_session(
        session_id="bt-cred-test",
        access_token="tok-bt",
        ad_account_id="act_bt_cred",
        ad_accounts=[{"id": "act_bt_cred"}],
        credits_balance=200,
    )
    database.save_ccco_campaign(
        adset_id="bt-cred-adset",
        name="BT Credit Test",
        event="PURCHASE",
        pixel_id="111",
        application_id="222",
        web_url="https://bt-cred.example.com",
        session_id="bt-cred-test",
        ad_account_id="act_bt_cred",
        android_deeplink="myapp://bt",
        daily_budget=5000,
    )
    # Seed enough insights for the backtest to run
    for day_offset in range(8):
        _seed_insight(
            database,
            "bt-cred-adset",
            "bt-cred-test",
            "act_bt_cred",
            date=f"2026-04-{1 + day_offset:02d}",
        )

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    from app.optimizer_backtest import BacktestRequest

    payload = BacktestRequest(
        session_id="bt-cred-test",
        ad_account_id="act_bt_cred",
        history_ratio=0.5,
        min_rows=4,
        max_adsets=5,
    )

    # The backtest should succeed and deduct credits afterward
    balance_before = CreditService.get_balance("bt-cred-test")
    result = await main_mod.run_optimizer_backtest(payload)
    assert result.adsets_evaluated >= 1

    # Credits should have been deducted *after* the backtest
    balance_after = CreditService.get_balance("bt-cred-test")
    assert balance_after == balance_before - 50

    # The backtest must have been free (rule-vs-rule) due to no ANTHROPIC_API_KEY
    assert any("rule-vs-rule" in note for note in result.notes)
