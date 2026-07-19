"""Tests for the Claude-powered CCCO optimizer.

These tests exercise the fallback paths (no API key, missing SDK, API failure,
malformed tool response) plus the happy path against a mocked Anthropic client.
The mock is injected via ``sys.modules`` so the test suite does not require the
real ``anthropic`` package to be installed.
"""

import asyncio
import sys
import types

import pytest

from app.ai_optimizer import OptimizeRequest


def _make_request(**overrides) -> OptimizeRequest:
    payload = {
        "session_id": "session-claude",
        "name": "Spring Promo",
        "event": "PURCHASE",
        "omnichannel": {"app": [], "pixel": []},
        "daily_budget": 5000,
        "web_url": "https://example.com/products",
        "android_deeplink": "myapp://products",
    }
    payload.update(overrides)
    return OptimizeRequest.model_validate(payload)


def _install_fake_anthropic(tool_input, *, raises: Exception | None = None) -> None:
    """Register a fake ``anthropic`` module with an AsyncAnthropic stub."""

    class _Block:
        def __init__(self, *, type_, name=None, input_=None):
            self.type = type_
            self.name = name
            self.input = input_

    class _Usage:
        input_tokens = 100
        output_tokens = 50
        cache_read_input_tokens = 0
        cache_creation_input_tokens = 100

    class _Response:
        def __init__(self):
            self.content = [_Block(type_="tool_use", name="submit_optimization", input_=tool_input)]
            self.stop_reason = "tool_use"
            self.usage = _Usage()

    class _Messages:
        async def create(self, **_kwargs):
            if raises is not None:
                raise raises
            return _Response()

    class _AsyncAnthropic:
        def __init__(self, **_kwargs):
            self.messages = _Messages()

    module = types.ModuleType("anthropic")
    module.AsyncAnthropic = _AsyncAnthropic
    sys.modules["anthropic"] = module


def _uninstall_fake_anthropic() -> None:
    sys.modules.pop("anthropic", None)


def test_claude_optimizer_falls_back_when_no_api_key(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from app.claude_optimizer import ClaudeOptimizer

    suggestion = asyncio.run(ClaudeOptimizer.get_suggestions(_make_request()))

    assert suggestion.recommendations[0].channel == "app"
    assert suggestion.suggested_bid_cap == 60


def test_claude_optimizer_falls_back_when_sdk_missing(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    _uninstall_fake_anthropic()
    monkeypatch.setitem(sys.modules, "anthropic", None)
    from app.claude_optimizer import ClaudeOptimizer

    suggestion = asyncio.run(ClaudeOptimizer.get_suggestions(_make_request()))

    assert suggestion.recommendations[0].channel == "app"


def test_claude_optimizer_returns_parsed_suggestion(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    _install_fake_anthropic(
        tool_input={
            "recommendations": [
                {
                    "channel": "app",
                    "weight_percent": 70,
                    "reason": "Trailing CPA of 11.2 with app share 62% justifies app lean.",
                    "expected_cpa_lift": 22.0,
                },
                {
                    "channel": "web",
                    "weight_percent": 30,
                    "reason": "Keep web open for non-installers; deep-link fallback handles it.",
                    "expected_cpa_lift": 8.5,
                },
            ],
            "suggested_bid_cap": 65,
            "predicted_cpa": 11.5,
            "creative_tip": "Use Advantage+ catalog with first-frame product hero in Reels 9:16.",
            "deep_link_routing_rule": "deeplink_with_web_fallback",
        }
    )

    try:
        from app.claude_optimizer import ClaudeOptimizer

        suggestion = asyncio.run(ClaudeOptimizer.get_suggestions(_make_request()))
    finally:
        _uninstall_fake_anthropic()

    assert [rec.channel for rec in suggestion.recommendations] == ["app", "web"]
    assert sum(rec.weight_percent for rec in suggestion.recommendations) == 100
    assert suggestion.suggested_bid_cap == 65
    assert suggestion.predicted_cpa == 11.5
    assert suggestion.deep_link_routing_rule == "deeplink_with_web_fallback"
    assert "Advantage+" in suggestion.creative_tip


def test_claude_optimizer_falls_back_when_api_raises(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    _install_fake_anthropic(tool_input={}, raises=RuntimeError("network down"))

    try:
        from app.claude_optimizer import ClaudeOptimizer

        suggestion = asyncio.run(ClaudeOptimizer.get_suggestions(_make_request()))
    finally:
        _uninstall_fake_anthropic()

    assert suggestion.recommendations[0].channel == "app"
    assert suggestion.suggested_bid_cap == 60


def test_claude_optimizer_falls_back_on_invalid_weights(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    _install_fake_anthropic(
        tool_input={
            "recommendations": [
                {
                    "channel": "app",
                    "weight_percent": 80,
                    "reason": "x",
                    "expected_cpa_lift": 10.0,
                },
                {
                    "channel": "web",
                    "weight_percent": 30,
                    "reason": "y",
                    "expected_cpa_lift": 5.0,
                },
            ],
            "suggested_bid_cap": None,
            "predicted_cpa": 12.0,
            "creative_tip": "Use Reels.",
            "deep_link_routing_rule": "deeplink_with_web_fallback",
        }
    )

    try:
        from app.claude_optimizer import ClaudeOptimizer

        suggestion = asyncio.run(ClaudeOptimizer.get_suggestions(_make_request()))
    finally:
        _uninstall_fake_anthropic()

    assert suggestion.recommendations[0].channel == "app"
    assert suggestion.suggested_bid_cap == 60
