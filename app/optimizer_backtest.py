"""Backtest harness for the CCCO optimizer.

This is the evidence layer that turns "we added Claude" into "we can prove
Claude beats the baseline." For each adset owned by the operator we:

1. Split that adset's ``campaign_insights`` rows chronologically into a
   ``history`` window and a ``holdout`` window.
2. Reconstruct an ``OptimizeRequest`` from the stored ``ccco_campaigns`` row.
3. Run *both* optimizers using only the history window (the Claude path is
   handed a leak-free history snapshot via ``history_override``).
4. Score each optimizer's ``predicted_cpa`` and predicted app-share against
   the *realized* CPA and app-share in the holdout window.

The aggregate report exposes mean absolute error (MAE) for CPA and for app
split, plus per-optimizer "wins" so the operator can see which engine
predicts their account's future better.

Account scoping is strict: the runner only loads rows where
``(session_id, ad_account_id)`` matches the operator's session.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.ai_optimizer import AIOptimizer, OptimizeRequest, OptimizerSuggestion
from app.claude_optimizer import ClaudeOptimizer
from app.database import get_db, get_session_record, init_db
from app.models.omnichannel import SupportedEvent
from app.utils.logging import structlog

logger = structlog.get_logger()

DEFAULT_MIN_ROWS = 7
DEFAULT_HISTORY_RATIO = 0.5
DEFAULT_MAX_ADSETS = 25


class BacktestRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    ad_account_id: str | None = None
    history_ratio: float = Field(default=DEFAULT_HISTORY_RATIO, gt=0.0, lt=1.0)
    min_rows: int = Field(default=DEFAULT_MIN_ROWS, ge=4)
    max_adsets: int = Field(default=DEFAULT_MAX_ADSETS, ge=1, le=100)
    include_claude: bool = True
    include_rule: bool = True


class _OptimizerScores(BaseModel):
    samples: int
    cpa_mae: float | None
    cpa_rmse: float | None
    app_share_mae: float | None
    wins_cpa: int
    wins_app_share: int


class BacktestAdsetResult(BaseModel):
    adset_id: str
    name: str
    event: str
    history_days: int
    holdout_days: int
    realized_cpa: float | None
    realized_app_share_percent: float | None
    claude_predicted_cpa: float | None = None
    claude_predicted_app_share_percent: float | None = None
    claude_optimizer_label: str | None = None
    rule_predicted_cpa: float | None = None
    rule_predicted_app_share_percent: float | None = None


class BacktestResult(BaseModel):
    session_id: str
    ad_account_id: str | None
    adsets_evaluated: int
    adsets_skipped_for_min_rows: int
    history_ratio: float
    min_rows: int
    claude: _OptimizerScores | None = None
    rule: _OptimizerScores | None = None
    head_to_head: dict[str, Any] | None = None
    per_adset: list[BacktestAdsetResult]
    notes: list[str] = Field(default_factory=list)


def _predicted_app_share(suggestion: OptimizerSuggestion) -> float | None:
    """Collapse the optimizer's channel recommendations to a single app-share %.

    - A "balanced" 100% entry maps to 50% app share.
    - Otherwise the "app" weight is taken as the app share; if absent it is
      ``100 - web_weight``; if neither is present we return ``None``.
    """
    app_weight: float | None = None
    web_weight: float | None = None
    balanced_weight: float = 0.0
    for rec in suggestion.recommendations:
        if rec.channel == "app":
            app_weight = float(rec.weight_percent)
        elif rec.channel == "web":
            web_weight = float(rec.weight_percent)
        elif rec.channel == "balanced":
            balanced_weight += float(rec.weight_percent)
    if app_weight is not None:
        return app_weight + balanced_weight * 0.5
    if web_weight is not None:
        return (100.0 - web_weight) - balanced_weight * 0.5
    if balanced_weight > 0:
        return 50.0
    return None


def _load_owned_adsets(session_id: str, ad_account_id: str | None) -> list[dict]:
    init_db()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM ccco_campaigns
            WHERE session_id IS :sid AND ad_account_id IS :acc
            ORDER BY created_at DESC
            """,
            {"sid": session_id, "acc": ad_account_id},
        ).fetchall()
    return [dict(row) for row in rows]


def _load_adset_insights(adset_id: str, session_id: str, ad_account_id: str | None) -> list[dict]:
    init_db()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT date, conversions_web, conversions_app, spend
            FROM campaign_insights
            WHERE adset_id = :adset
              AND session_id IS :sid
              AND ad_account_id IS :acc
            ORDER BY date ASC
            """,
            {"adset": adset_id, "sid": session_id, "acc": ad_account_id},
        ).fetchall()
    return [dict(row) for row in rows]


def _weighted_metrics(rows: list[dict]) -> tuple[float | None, float | None, float]:
    total_spend = sum(float(r["spend"]) for r in rows)
    total_web = sum(int(r["conversions_web"]) for r in rows)
    total_app = sum(int(r["conversions_app"]) for r in rows)
    total_conv = total_web + total_app
    if total_conv == 0:
        return None, None, total_spend
    weighted_cpa = round(total_spend / total_conv, 4)
    app_share = round((total_app / total_conv) * 100.0, 4)
    return weighted_cpa, app_share, total_spend


def _build_history_snapshot(rows: list[dict], session_id: str, ad_account_id: str | None) -> dict:
    weighted_cpa, app_share, total_spend = _weighted_metrics(rows)
    total_web = sum(int(r["conversions_web"]) for r in rows)
    total_app = sum(int(r["conversions_app"]) for r in rows)
    total_conv = total_web + total_app
    return {
        "available": total_conv > 0,
        "window_days": len(rows),
        "scope": {"session_id": session_id, "ad_account_id": ad_account_id},
        "rows": len(rows),
        "total_spend": round(total_spend, 2),
        "total_conversions": total_conv,
        "trailing_weighted_cpa": weighted_cpa,
        "trailing_weighted_web_split_percent": (
            round((total_web / total_conv) * 100, 2) if total_conv else None
        ),
        "trailing_weighted_app_split_percent": app_share,
        "first_date": rows[0]["date"] if rows else None,
        "last_date": rows[-1]["date"] if rows else None,
        "by_event": [],
    }


def _reconstruct_request(
    campaign: dict,
    history_rows: list[dict],
    session_id: str,
) -> OptimizeRequest | None:
    try:
        event = SupportedEvent(campaign["event"])
    except (ValueError, KeyError):
        return None

    web_url = campaign.get("web_url") or "https://example.com/"

    # daily_budget: prefer stored value; otherwise derive from average daily
    # spend in history (spend is in dollars; budget field is in cents).
    daily_budget = campaign.get("daily_budget")
    if not daily_budget:
        if history_rows:
            avg_spend = sum(float(r["spend"]) for r in history_rows) / len(history_rows)
            daily_budget = max(int(round(avg_spend * 100)), 100)
        else:
            daily_budget = 5000

    pixel_id = str(campaign.get("pixel_id") or "0")
    application_id = str(campaign.get("application_id") or "0")

    history_app_conv = sum(int(r["conversions_app"]) for r in history_rows)
    has_app_signal = bool(campaign.get("android_deeplink") or campaign.get("ios_deeplink") or history_app_conv > 0)

    omnichannel: dict[str, Any] = {
        "pixel": [{"pixel_id": pixel_id, "custom_event_type": event.value}],
        "app": (
            [
                {
                    "application_id": application_id,
                    "custom_event_type": event.value,
                    "object_store_urls": [],
                }
            ]
            if has_app_signal
            else []
        ),
    }

    payload = {
        "session_id": session_id,
        "name": campaign["name"],
        "event": event.value,
        "omnichannel": omnichannel,
        "daily_budget": int(daily_budget),
        "web_url": web_url,
        "android_deeplink": campaign.get("android_deeplink"),
        "ios_deeplink": campaign.get("ios_deeplink"),
    }
    try:
        return OptimizeRequest.model_validate(payload)
    except Exception:
        logger.exception("backtest_request_reconstruction_failed", adset_id=campaign.get("adset_id"))
        return None


def _score(samples: list[tuple[float, float, float | None, float | None]]) -> _OptimizerScores | None:
    """Compute MAE/RMSE for CPA and MAE for app-share, plus win counters.

    Each sample is ``(realized_cpa, realized_app_share, pred_cpa, pred_app_share)``.
    Wins are counted by lower absolute error vs. the other optimizer; the
    caller fills those in.
    """
    if not samples:
        return None
    cpa_errors = [abs(p - r) for r, _, p, _ in samples if p is not None]
    cpa_squared = [(p - r) ** 2 for r, _, p, _ in samples if p is not None]
    app_errors = [abs(pa - ra) for _, ra, _, pa in samples if pa is not None and ra is not None]
    return _OptimizerScores(
        samples=len(samples),
        cpa_mae=round(sum(cpa_errors) / len(cpa_errors), 4) if cpa_errors else None,
        cpa_rmse=round((sum(cpa_squared) / len(cpa_squared)) ** 0.5, 4) if cpa_squared else None,
        app_share_mae=round(sum(app_errors) / len(app_errors), 4) if app_errors else None,
        wins_cpa=0,
        wins_app_share=0,
    )


class BacktestRunner:
    @staticmethod
    async def run(req: BacktestRequest) -> BacktestResult:
        ad_account_id = req.ad_account_id
        if ad_account_id is None:
            session = get_session_record(req.session_id)
            ad_account_id = session.get("ad_account_id") if session else None

        campaigns = _load_owned_adsets(req.session_id, ad_account_id)
        per_adset: list[BacktestAdsetResult] = []
        skipped = 0

        claude_samples: list[tuple[float, float, float | None, float | None]] = []
        rule_samples: list[tuple[float, float, float | None, float | None]] = []

        evaluated = 0
        for campaign in campaigns:
            if evaluated >= req.max_adsets:
                break
            adset_id = campaign.get("adset_id")
            if not adset_id:
                continue

            insights = _load_adset_insights(adset_id, req.session_id, ad_account_id)
            if len(insights) < req.min_rows:
                skipped += 1
                continue

            cut = max(2, int(len(insights) * req.history_ratio))
            history_rows = insights[:cut]
            holdout_rows = insights[cut:]
            if not holdout_rows:
                skipped += 1
                continue

            realized_cpa, realized_app_share, _ = _weighted_metrics(holdout_rows)
            if realized_cpa is None or realized_app_share is None:
                skipped += 1
                continue

            request = _reconstruct_request(campaign, history_rows, req.session_id)
            if request is None:
                skipped += 1
                continue

            history_snapshot = _build_history_snapshot(history_rows, req.session_id, ad_account_id)

            row = BacktestAdsetResult(
                adset_id=adset_id,
                name=campaign.get("name") or adset_id,
                event=campaign.get("event") or "UNKNOWN",
                history_days=len(history_rows),
                holdout_days=len(holdout_rows),
                realized_cpa=realized_cpa,
                realized_app_share_percent=realized_app_share,
            )

            if req.include_claude:
                claude_suggestion, label = await ClaudeOptimizer.get_suggestions_with_meta(
                    request, history_override=history_snapshot
                )
                row.claude_predicted_cpa = round(float(claude_suggestion.predicted_cpa), 4)
                row.claude_predicted_app_share_percent = _predicted_app_share(claude_suggestion)
                row.claude_optimizer_label = label
                claude_samples.append(
                    (
                        realized_cpa,
                        realized_app_share,
                        row.claude_predicted_cpa,
                        row.claude_predicted_app_share_percent,
                    )
                )

            if req.include_rule:
                rule_suggestion = AIOptimizer.get_suggestions(request)
                row.rule_predicted_cpa = round(float(rule_suggestion.predicted_cpa), 4)
                row.rule_predicted_app_share_percent = _predicted_app_share(rule_suggestion)
                rule_samples.append(
                    (
                        realized_cpa,
                        realized_app_share,
                        row.rule_predicted_cpa,
                        row.rule_predicted_app_share_percent,
                    )
                )

            per_adset.append(row)
            evaluated += 1

        claude_scores = _score(claude_samples) if req.include_claude else None
        rule_scores = _score(rule_samples) if req.include_rule else None

        head_to_head: dict[str, Any] | None = None
        notes: list[str] = []
        if req.include_claude and req.include_rule and claude_scores and rule_scores:
            claude_cpa_wins = 0
            rule_cpa_wins = 0
            claude_app_wins = 0
            rule_app_wins = 0
            for row in per_adset:
                if (
                    row.claude_predicted_cpa is not None
                    and row.rule_predicted_cpa is not None
                    and row.realized_cpa is not None
                ):
                    if abs(row.claude_predicted_cpa - row.realized_cpa) < abs(
                        row.rule_predicted_cpa - row.realized_cpa
                    ):
                        claude_cpa_wins += 1
                    elif abs(row.rule_predicted_cpa - row.realized_cpa) < abs(
                        row.claude_predicted_cpa - row.realized_cpa
                    ):
                        rule_cpa_wins += 1
                if (
                    row.claude_predicted_app_share_percent is not None
                    and row.rule_predicted_app_share_percent is not None
                    and row.realized_app_share_percent is not None
                ):
                    if abs(row.claude_predicted_app_share_percent - row.realized_app_share_percent) < abs(
                        row.rule_predicted_app_share_percent - row.realized_app_share_percent
                    ):
                        claude_app_wins += 1
                    elif abs(row.rule_predicted_app_share_percent - row.realized_app_share_percent) < abs(
                        row.claude_predicted_app_share_percent - row.realized_app_share_percent
                    ):
                        rule_app_wins += 1
            claude_scores.wins_cpa = claude_cpa_wins
            claude_scores.wins_app_share = claude_app_wins
            rule_scores.wins_cpa = rule_cpa_wins
            rule_scores.wins_app_share = rule_app_wins

            cpa_winner = None
            if claude_scores.cpa_mae is not None and rule_scores.cpa_mae is not None:
                if claude_scores.cpa_mae < rule_scores.cpa_mae:
                    cpa_winner = "claude"
                elif rule_scores.cpa_mae < claude_scores.cpa_mae:
                    cpa_winner = "rule"
                else:
                    cpa_winner = "tie"
            app_winner = None
            if claude_scores.app_share_mae is not None and rule_scores.app_share_mae is not None:
                if claude_scores.app_share_mae < rule_scores.app_share_mae:
                    app_winner = "claude"
                elif rule_scores.app_share_mae < claude_scores.app_share_mae:
                    app_winner = "rule"
                else:
                    app_winner = "tie"
            head_to_head = {"cpa_winner": cpa_winner, "app_share_winner": app_winner}

            claude_fallbacks = sum(
                1
                for row in per_adset
                if row.claude_optimizer_label and row.claude_optimizer_label != "claude"
            )
            if claude_fallbacks == evaluated and evaluated > 0:
                notes.append(
                    "ANTHROPIC_API_KEY is unset or the SDK is unavailable; all 'claude' samples used the rule fallback, so the head-to-head is rule-vs-rule."
                )
            elif claude_fallbacks > 0:
                notes.append(
                    f"{claude_fallbacks} of {evaluated} adsets fell back to the rule engine inside the Claude path; check optimizer logs."
                )

        return BacktestResult(
            session_id=req.session_id,
            ad_account_id=ad_account_id,
            adsets_evaluated=evaluated,
            adsets_skipped_for_min_rows=skipped,
            history_ratio=req.history_ratio,
            min_rows=req.min_rows,
            claude=claude_scores,
            rule=rule_scores,
            head_to_head=head_to_head,
            per_adset=per_adset,
            notes=notes,
        )
