"""Evidence-layer tests: account scoping, weighted math, backtest harness.

These are the tests that prove the optimizer reads only the right
advertiser's data, that historical CPA is spend-weighted (not flat-averaged),
and that the backtest harness produces comparable scores for Claude vs. the
rule engine on real-looking data.
"""

import asyncio
import importlib

from app.ai_optimizer import OptimizeRequest


def _reset_db(tmp_path, monkeypatch):
    db_path = tmp_path / "campaigns.db"
    monkeypatch.setenv("CCCO_DB_PATH", str(db_path))

    import app.database as database
    import app.analytics as analytics
    import app.claude_optimizer as claude_optimizer
    import app.optimizer_backtest as backtest

    database = importlib.reload(database)
    analytics = importlib.reload(analytics)
    claude_optimizer = importlib.reload(claude_optimizer)
    backtest = importlib.reload(backtest)
    database.init_db()
    return database, analytics, claude_optimizer, backtest


def _ingest(analytics, adset_id, rows, session_id, ad_account_id):
    insights = [
        analytics.InsightRecord(
            adset_id=adset_id,
            date=row["date"],
            conversions_web=row["web"],
            conversions_app=row["app"],
            spend=row["spend"],
            cpa=(row["spend"] / max(row["web"] + row["app"], 1)),
            channel_split_web=(row["web"] / max(row["web"] + row["app"], 1)) * 100,
            channel_split_app=(row["app"] / max(row["web"] + row["app"], 1)) * 100,
        )
        for row in rows
    ]
    analytics.AnalyticsService.ingest_insights(
        adset_id,
        insights,
        session_id=session_id,
        ad_account_id=ad_account_id,
    )


def test_history_is_strictly_account_scoped(tmp_path, monkeypatch) -> None:
    database, analytics, claude_optimizer, _ = _reset_db(tmp_path, monkeypatch)

    database.save_ccco_campaign(
        adset_id="adset-A",
        name="Account A campaign",
        event="PURCHASE",
        pixel_id="111",
        application_id="222",
        web_url="https://a.example.com",
        session_id="session-A",
        ad_account_id="act_A",
    )
    database.save_ccco_campaign(
        adset_id="adset-B",
        name="Account B campaign",
        event="PURCHASE",
        pixel_id="333",
        application_id="444",
        web_url="https://b.example.com",
        session_id="session-B",
        ad_account_id="act_B",
    )

    _ingest(
        analytics,
        "adset-A",
        [
            {"date": "2026-05-01", "web": 10, "app": 30, "spend": 200.0},
            {"date": "2026-05-02", "web": 5, "app": 15, "spend": 100.0},
        ],
        "session-A",
        "act_A",
    )
    _ingest(
        analytics,
        "adset-B",
        [
            {"date": "2026-05-01", "web": 100, "app": 0, "spend": 5000.0},
        ],
        "session-B",
        "act_B",
    )

    history_a = claude_optimizer._weighted_history_for_owner("session-A", "act_A")
    history_b = claude_optimizer._weighted_history_for_owner("session-B", "act_B")

    assert history_a["available"] is True
    assert history_a["total_spend"] == 300.0
    assert history_a["total_conversions"] == 60
    assert history_a["rows"] == 2

    assert history_b["available"] is True
    assert history_b["total_spend"] == 5000.0
    assert history_b["total_conversions"] == 100
    assert history_b["rows"] == 1

    # Session B must NOT see session A's spend.
    assert history_b["total_spend"] != 5300.0


def test_weighted_cpa_beats_flat_average_on_skewed_data(tmp_path, monkeypatch) -> None:
    database, analytics, claude_optimizer, _ = _reset_db(tmp_path, monkeypatch)

    database.save_ccco_campaign(
        adset_id="adset-skew",
        name="Skewed",
        event="PURCHASE",
        pixel_id="111",
        application_id="222",
        web_url="https://skew.example.com",
        session_id="session-skew",
        ad_account_id="act_skew",
    )
    # Day 1: low-spend, low-conversion day -> per-row cpa = 10
    # Day 2: high-spend, high-conversion day -> per-row cpa = 20
    # Flat AVG(cpa) = 15. Spend-weighted CPA = (10 + 2000) / (1 + 100) ~= 19.9.
    _ingest(
        analytics,
        "adset-skew",
        [
            {"date": "2026-05-01", "web": 1, "app": 0, "spend": 10.0},
            {"date": "2026-05-02", "web": 100, "app": 0, "spend": 2000.0},
        ],
        "session-skew",
        "act_skew",
    )

    history = claude_optimizer._weighted_history_for_owner("session-skew", "act_skew")

    assert history["available"] is True
    assert history["total_spend"] == 2010.0
    assert history["total_conversions"] == 101
    weighted_cpa = history["trailing_weighted_cpa"]
    assert weighted_cpa is not None
    assert abs(weighted_cpa - (2010.0 / 101.0)) < 0.01
    # Sanity: the weighted value is much closer to the high-spend day's CPA
    # than to a flat AVG(cpa) of 15. This is the whole point of the fix.
    assert weighted_cpa > 18.0


def test_optimizer_run_is_logged(tmp_path, monkeypatch) -> None:
    database, _, claude_optimizer, _ = _reset_db(tmp_path, monkeypatch)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    request = OptimizeRequest.model_validate(
        {
            "session_id": "session-log",
            "name": "Logged campaign",
            "event": "PURCHASE",
            "omnichannel": {"app": [], "pixel": []},
            "daily_budget": 5000,
            "web_url": "https://example.com",
            "android_deeplink": "myapp://x",
        }
    )

    suggestion, label = asyncio.run(claude_optimizer.ClaudeOptimizer.get_suggestions_with_meta(request))
    assert label == claude_optimizer.FALLBACK_NO_KEY

    database.record_optimizer_run(
        session_id="session-log",
        ad_account_id="act_log",
        campaign_name=request.name,
        event=request.event.value,
        optimizer=label,
        request_json=request.model_dump_json(),
        suggestion_json=suggestion.model_dump_json(),
        used_fallback=True,
    )

    with database.get_db() as conn:
        rows = conn.execute("SELECT * FROM optimizer_runs WHERE session_id = ?", ("session-log",)).fetchall()
    assert len(rows) == 1
    assert rows[0]["optimizer"] == claude_optimizer.FALLBACK_NO_KEY
    assert rows[0]["used_fallback"] == 1
    assert "Logged campaign" in rows[0]["request_json"]


def test_backtest_runs_rule_vs_rule_when_no_api_key(tmp_path, monkeypatch) -> None:
    """Without an API key, both paths use the rule engine. The backtest must
    still produce a valid report and surface a note explaining the situation.
    """
    database, analytics, _, backtest = _reset_db(tmp_path, monkeypatch)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    database.save_ccco_campaign(
        adset_id="adset-bt-1",
        name="Backtest PURCHASE",
        event="PURCHASE",
        pixel_id="111",
        application_id="222",
        web_url="https://bt.example.com",
        session_id="session-bt",
        ad_account_id="act_bt",
        android_deeplink="myapp://bt",
        daily_budget=5000,
    )
    _ingest(
        analytics,
        "adset-bt-1",
        [
            {"date": "2026-04-01", "web": 4, "app": 16, "spend": 250.0},
            {"date": "2026-04-02", "web": 5, "app": 20, "spend": 320.0},
            {"date": "2026-04-03", "web": 6, "app": 18, "spend": 290.0},
            {"date": "2026-04-04", "web": 4, "app": 22, "spend": 310.0},
            {"date": "2026-04-05", "web": 3, "app": 15, "spend": 240.0},
            {"date": "2026-04-06", "web": 5, "app": 19, "spend": 280.0},
            {"date": "2026-04-07", "web": 4, "app": 17, "spend": 260.0},
            {"date": "2026-04-08", "web": 3, "app": 14, "spend": 235.0},
        ],
        "session-bt",
        "act_bt",
    )

    payload = backtest.BacktestRequest(
        session_id="session-bt",
        ad_account_id="act_bt",
        history_ratio=0.5,
        min_rows=4,
        max_adsets=5,
    )
    result = asyncio.run(backtest.BacktestRunner.run(payload))

    assert result.adsets_evaluated == 1
    assert result.adsets_skipped_for_min_rows == 0
    assert result.rule is not None and result.rule.samples == 1
    assert result.claude is not None and result.claude.samples == 1
    # Realized CPA from the holdout window must be the spend-weighted CPA,
    # which is the same calculation we trust the rule engine on.
    only_row = result.per_adset[0]
    assert only_row.realized_cpa is not None and only_row.realized_cpa > 0
    assert only_row.realized_app_share_percent is not None
    # Without an API key the Claude path must explicitly note it used the
    # fallback. This is the honesty the critique demanded.
    assert any("rule-vs-rule" in note for note in result.notes)
    assert only_row.claude_optimizer_label == "rule_fallback_no_key"


def test_backtest_skips_adsets_below_min_rows(tmp_path, monkeypatch) -> None:
    database, analytics, _, backtest = _reset_db(tmp_path, monkeypatch)

    database.save_ccco_campaign(
        adset_id="adset-thin",
        name="Thin data",
        event="LEAD",
        pixel_id="111",
        application_id="222",
        web_url="https://thin.example.com",
        session_id="session-thin",
        ad_account_id="act_thin",
    )
    _ingest(
        analytics,
        "adset-thin",
        [
            {"date": "2026-04-01", "web": 1, "app": 0, "spend": 10.0},
            {"date": "2026-04-02", "web": 1, "app": 0, "spend": 10.0},
        ],
        "session-thin",
        "act_thin",
    )

    payload = backtest.BacktestRequest(session_id="session-thin", ad_account_id="act_thin", min_rows=7)
    result = asyncio.run(backtest.BacktestRunner.run(payload))

    assert result.adsets_evaluated == 0
    assert result.adsets_skipped_for_min_rows == 1
    assert result.per_adset == []
