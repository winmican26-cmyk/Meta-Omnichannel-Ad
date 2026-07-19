"""Claude-powered CCCO optimizer.

Tier 1 of the post-Meta roadmap. Replaces the rule-based ``AIOptimizer`` with
a Claude reasoning call while preserving the ``OptimizerSuggestion`` contract.
Falls back to the rule engine when ``ANTHROPIC_API_KEY`` is missing or the
Anthropic call fails for any reason, so the endpoint never breaks.
"""

from __future__ import annotations

import json
import os
from typing import Any

from app.ai_optimizer import (
    AIOptimizer,
    ChannelRecommendation,
    OptimizeRequest,
    OptimizerSuggestion,
)
from app.database import get_db, get_session_record, init_db
from app.utils.logging import structlog

logger = structlog.get_logger()

DEFAULT_MODEL = os.getenv("ANTHROPIC_OPTIMIZER_MODEL", "claude-sonnet-4-6")
DEFAULT_MAX_TOKENS = int(os.getenv("ANTHROPIC_OPTIMIZER_MAX_TOKENS", "1500"))
HISTORY_WINDOW_DAYS = 90
EVENT_BREAKDOWN_LIMIT = 6

SUBMIT_TOOL_NAME = "submit_optimization"

SYSTEM_PROMPT = """You are the Meta CCCO (Cross-Channel Conversion Optimization) optimizer for the OmniConvert platform.

Your job: given a campaign configuration and any historical performance from the operator's account, produce the optimal channel split (web pixel vs. mobile app conversion signals), bid cap, predicted CPA, creative guidance, and deep-link routing rule. You MUST call the `submit_optimization` tool exactly once with your final answer. Do not call any other tool. Do not return prose.

Background on Meta CCCO that you should treat as authoritative:

- A CCCO ad set has a `promoted_object.omnichannel_object` that fuses one or more pixel events with one or more app events. Meta's optimizer then allocates delivery across web and app placements automatically, but the channel split *weighting* and *bid cap* the operator chooses materially affect outcomes.
- Web pixel events (e.g. PURCHASE on a Pixel) and app events (e.g. PURCHASE custom_event_type tied to an `application_id`) are reported separately by Meta. The `channel_split_web` / `channel_split_app` percentages from `campaign_insights` reflect post-hoc share, not Meta's bid signal.
- High-intent commerce events (PURCHASE, ADD_TO_CART, INITIATE_CHECKOUT) with valid app deeplinks should generally lean app-heavy because app users complete checkout faster, deep-linking eliminates landing friction, and Meta's app-event optimization tends to deliver lower CPA when the SDK is healthy. Typical app-weighted split: 55–75%.
- LEAD, COMPLETE_REGISTRATION, and content-engagement events without deeplinks should generally be balanced (web 40–60 / app 40–60) until the operator collects enough conversion data per channel to justify a shift. Default to balanced when uncertain.
- VIEW_CONTENT and brand-awareness events are usually web-leaning because intent is low and app install friction is unjustified.
- Bid cap heuristic: ~1–1.5% of `daily_budget` (in cents) for high-intent commerce events when historical CPA is unknown. If historical CPA is available, set bid cap to roughly `predicted_cpa * 1.2 * 100` (cents). Return `null` for `suggested_bid_cap` when there is genuinely no signal to set one.
- Predicted CPA must be expressed in the same currency unit as historical `cpa` in `campaign_insights` (treated as dollars by the platform). If historical data exists, anchor your prediction to the trailing average and adjust by your channel-split confidence. If no history exists, use sensible defaults: PURCHASE ~12, ADD_TO_CART ~6, LEAD ~18, otherwise ~20.
- Deep-link routing rule values you may return: `deeplink_with_web_fallback` (default when at least one of android_deeplink/ios_deeplink is provided), `web_only` (no deeplinks), `app_only` (deeplinks present and event is a high-intent commerce event AND the operator's historical app split is already >= 70%).
- Creative tip should be one specific, actionable sentence aimed at this campaign, not a platitude. Mention placements (Reels, Stories, Feed) or formats (Advantage+ catalog, dynamic product ads, collection) when relevant.

Reasoning rules:

- If historical insights are provided, ground every recommendation in them. Cite the trailing CPA or the observed channel split in the `reason` field when it informs the recommendation.
- If no history is provided, say so plainly in the `reason` field and explain why your default applies.
- `recommendations` must sum to exactly 100 when there are multiple entries. A single entry must have `weight_percent = 100`.
- `expected_cpa_lift` is a percent (e.g. 18.0 means a 18% expected CPA improvement vs. an unoptimized split). Use 0–30 range. Be conservative when historical data is thin.
- Never invent ad account features. Never reference targeting decisions outside what the operator provided.

You will be given the request payload plus, when available, a 90-day historical snapshot pulled from the operator's `campaign_insights` table. Call `submit_optimization` once with your final answer."""


def _build_submit_tool() -> dict[str, Any]:
    return {
        "name": SUBMIT_TOOL_NAME,
        "description": "Submit the final CCCO optimization recommendation. Call this exactly once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "recommendations": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "channel": {"type": "string", "enum": ["web", "app", "balanced"]},
                            "weight_percent": {"type": "integer", "minimum": 0, "maximum": 100},
                            "reason": {"type": "string", "minLength": 1},
                            "expected_cpa_lift": {"type": "number", "minimum": 0, "maximum": 50},
                        },
                        "required": ["channel", "weight_percent", "reason", "expected_cpa_lift"],
                    },
                },
                "suggested_bid_cap": {"type": ["integer", "null"]},
                "predicted_cpa": {"type": "number", "minimum": 0},
                "creative_tip": {"type": "string", "minLength": 1},
                "deep_link_routing_rule": {
                    "type": "string",
                    "enum": ["deeplink_with_web_fallback", "web_only", "app_only"],
                },
            },
            "required": [
                "recommendations",
                "predicted_cpa",
                "creative_tip",
                "deep_link_routing_rule",
            ],
        },
    }


def _weighted_history_for_owner(
    session_id: str | None,
    ad_account_id: str | None,
    *,
    window_days: int = HISTORY_WINDOW_DAYS,
) -> dict[str, Any]:
    """Spend-weighted, account-scoped 90-day snapshot.

    Filters strictly by (session_id, ad_account_id) so one advertiser never
    reads another's performance. CPA is computed as ``SUM(spend) /
    SUM(conversions)``, not as a flat ``AVG(cpa)``, so low-spend days do not
    distort the trailing average. Channel splits are conversion-weighted,
    matching how Meta actually scores delivery.
    """
    if not session_id:
        return {"available": False, "reason": "no_session"}

    try:
        init_db()
        with get_db() as conn:
            row = conn.execute(
                f"""
                SELECT
                    COUNT(*) AS rows,
                    COALESCE(SUM(spend), 0) AS spend,
                    COALESCE(SUM(conversions_web), 0) AS web_conv,
                    COALESCE(SUM(conversions_app), 0) AS app_conv,
                    MIN(date) AS first_date,
                    MAX(date) AS last_date
                FROM campaign_insights
                WHERE session_id IS :sid
                  AND ad_account_id IS :acc
                  AND date >= date('now', '-{window_days} day')
                """,
                {"sid": session_id, "acc": ad_account_id},
            ).fetchone()

            event_rows = conn.execute(
                f"""
                SELECT
                    c.event AS event,
                    COALESCE(SUM(i.spend), 0) AS spend,
                    COALESCE(SUM(i.conversions_web), 0) AS web_conv,
                    COALESCE(SUM(i.conversions_app), 0) AS app_conv,
                    COUNT(DISTINCT i.adset_id) AS adsets
                FROM campaign_insights i
                JOIN ccco_campaigns c ON c.adset_id = i.adset_id
                WHERE i.session_id IS :sid
                  AND i.ad_account_id IS :acc
                  AND i.date >= date('now', '-{window_days} day')
                GROUP BY c.event
                ORDER BY spend DESC
                LIMIT {EVENT_BREAKDOWN_LIMIT}
                """,
                {"sid": session_id, "acc": ad_account_id},
            ).fetchall()
    except Exception:
        logger.exception(
            "claude_optimizer_history_load_failed",
            session_id=session_id,
            ad_account_id=ad_account_id,
        )
        return {"available": False, "reason": "query_failed"}

    if not row or not row["rows"]:
        return {"available": False, "reason": "no_rows_for_owner"}

    total_conv = int(row["web_conv"]) + int(row["app_conv"])
    total_spend = float(row["spend"])
    weighted_cpa = round(total_spend / total_conv, 2) if total_conv else None
    web_share = round((int(row["web_conv"]) / total_conv) * 100, 2) if total_conv else None
    app_share = round((int(row["app_conv"]) / total_conv) * 100, 2) if total_conv else None

    event_breakdown = []
    for ev in event_rows:
        ev_conv = int(ev["web_conv"]) + int(ev["app_conv"])
        event_breakdown.append(
            {
                "event": ev["event"],
                "adsets": int(ev["adsets"]),
                "total_spend": round(float(ev["spend"]), 2),
                "total_conversions": ev_conv,
                "weighted_cpa": round(float(ev["spend"]) / ev_conv, 2) if ev_conv else None,
                "weighted_app_split_percent": round((int(ev["app_conv"]) / ev_conv) * 100, 2)
                if ev_conv
                else None,
            }
        )

    return {
        "available": True,
        "window_days": window_days,
        "scope": {"session_id": session_id, "ad_account_id": ad_account_id},
        "rows": int(row["rows"]),
        "total_spend": round(total_spend, 2),
        "total_conversions": total_conv,
        "trailing_weighted_cpa": weighted_cpa,
        "trailing_weighted_web_split_percent": web_share,
        "trailing_weighted_app_split_percent": app_share,
        "first_date": row["first_date"],
        "last_date": row["last_date"],
        "by_event": event_breakdown,
    }


def _resolve_owner(session_id: str) -> tuple[str, str | None]:
    """Return ``(session_id, ad_account_id)``. Missing session is OK at this layer."""
    record = get_session_record(session_id) if session_id else None
    ad_account_id = record.get("ad_account_id") if record else None
    return session_id, ad_account_id


def _load_historical_context(session_id: str) -> dict[str, Any]:
    sid, acc = _resolve_owner(session_id)
    return _weighted_history_for_owner(sid, acc)


def _serialize_request(req: OptimizeRequest) -> dict[str, Any]:
    return {
        "name": req.name,
        "event": req.event.value,
        "daily_budget_cents": req.daily_budget,
        "web_url": str(req.web_url),
        "android_deeplink": req.android_deeplink,
        "ios_deeplink": req.ios_deeplink,
        "has_app_deeplinks": bool(req.android_deeplink or req.ios_deeplink),
        "omnichannel_summary": {
            "pixel_entries": len(req.omnichannel.get("pixel", []) or []),
            "app_entries": len(req.omnichannel.get("app", []) or []),
        },
    }


def _build_user_message(req: OptimizeRequest, history: dict[str, Any]) -> str:
    return (
        "Campaign optimization request:\n"
        + json.dumps(_serialize_request(req), indent=2)
        + "\n\nHistorical context (operator account, last 90 days):\n"
        + json.dumps(history, indent=2)
        + "\n\nProduce the optimization now by calling `submit_optimization` exactly once."
    )


def _parse_tool_response(tool_input: dict[str, Any]) -> OptimizerSuggestion:
    recs_raw = tool_input.get("recommendations") or []
    recommendations = [
        ChannelRecommendation(
            channel=item["channel"],
            weight_percent=int(item["weight_percent"]),
            reason=str(item["reason"]).strip(),
            expected_cpa_lift=float(item["expected_cpa_lift"]),
        )
        for item in recs_raw
    ]
    if not recommendations:
        raise ValueError("Claude returned no recommendations")

    total_weight = sum(rec.weight_percent for rec in recommendations)
    if total_weight != 100:
        raise ValueError(f"Claude recommendations summed to {total_weight}, expected 100")

    bid_cap_raw = tool_input.get("suggested_bid_cap")
    suggested_bid_cap = int(bid_cap_raw) if bid_cap_raw is not None else None

    return OptimizerSuggestion(
        recommendations=recommendations,
        suggested_bid_cap=suggested_bid_cap,
        predicted_cpa=float(tool_input["predicted_cpa"]),
        creative_tip=str(tool_input["creative_tip"]).strip(),
        deep_link_routing_rule=str(tool_input["deep_link_routing_rule"]),
    )


OPTIMIZER_LABEL_CLAUDE = "claude"
OPTIMIZER_LABEL_RULE = "rule"
FALLBACK_NO_KEY = "rule_fallback_no_key"
FALLBACK_SDK_MISSING = "rule_fallback_sdk_missing"
FALLBACK_API_ERROR = "rule_fallback_api_error"
FALLBACK_MISSING_TOOL_USE = "rule_fallback_missing_tool_use"
FALLBACK_PARSE_ERROR = "rule_fallback_parse_error"


class ClaudeOptimizer:
    """Anthropic-backed optimizer with a rule-engine safety net."""

    @staticmethod
    async def get_suggestions(req: OptimizeRequest) -> OptimizerSuggestion:
        suggestion, _ = await ClaudeOptimizer.get_suggestions_with_meta(req)
        return suggestion

    @staticmethod
    async def get_suggestions_with_meta(
        req: OptimizeRequest,
        *,
        history_override: dict[str, Any] | None = None,
    ) -> tuple[OptimizerSuggestion, str]:
        """Return ``(suggestion, optimizer_label)`` so callers can log which path ran.

        ``history_override`` lets the backtest harness supply a leak-free
        as-of snapshot instead of letting the optimizer read the full table.
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.info("claude_optimizer_fallback_no_api_key", campaign=req.name)
            return AIOptimizer.get_suggestions(req), FALLBACK_NO_KEY

        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            logger.warning("claude_optimizer_fallback_missing_sdk", campaign=req.name)
            return AIOptimizer.get_suggestions(req), FALLBACK_SDK_MISSING

        history = (
            history_override
            if history_override is not None
            else _load_historical_context(req.session_id)
        )
        client = AsyncAnthropic(api_key=api_key)

        try:
            response = await client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=DEFAULT_MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=[_build_submit_tool()],
                tool_choice={"type": "tool", "name": SUBMIT_TOOL_NAME},
                messages=[{"role": "user", "content": _build_user_message(req, history)}],
            )
        except Exception:
            logger.exception("claude_optimizer_api_call_failed", campaign=req.name)
            return AIOptimizer.get_suggestions(req), FALLBACK_API_ERROR

        tool_use = next(
            (block for block in response.content if getattr(block, "type", None) == "tool_use"),
            None,
        )
        if tool_use is None or tool_use.name != SUBMIT_TOOL_NAME:
            logger.warning(
                "claude_optimizer_missing_tool_use",
                campaign=req.name,
                stop_reason=getattr(response, "stop_reason", None),
            )
            return AIOptimizer.get_suggestions(req), FALLBACK_MISSING_TOOL_USE

        try:
            suggestion = _parse_tool_response(tool_use.input)
        except Exception:
            logger.exception("claude_optimizer_parse_failed", campaign=req.name)
            return AIOptimizer.get_suggestions(req), FALLBACK_PARSE_ERROR

        usage = getattr(response, "usage", None)
        logger.info(
            "claude_optimizer_suggestions_generated",
            campaign=req.name,
            conversion_event=req.event.value,
            model=DEFAULT_MODEL,
            history_available=history.get("available", False),
            input_tokens=getattr(usage, "input_tokens", None) if usage else None,
            output_tokens=getattr(usage, "output_tokens", None) if usage else None,
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", None) if usage else None,
            cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", None) if usage else None,
        )
        return suggestion, OPTIMIZER_LABEL_CLAUDE
