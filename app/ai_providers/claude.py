"""Claude (Anthropic) AI provider.

Wraps the Anthropic API for chat completions. Falls back to the existing
rule-based optimizer when the API key is not configured.
"""

from __future__ import annotations

import os
from typing import Any

from app.ai_providers.base import AIProvider, ProviderConfig, ProviderStatus
from app.key_manager import get_key

# Attempt to import the Anthropic SDK; gracefully degrade if missing
try:
    import anthropic

    _HAS_ANTHROPIC = True
except ImportError:
    _HAS_ANTHROPIC = False


class ClaudeProvider(AIProvider):
    """Provider that uses Anthropic's Claude models for analysis & strategy."""

    _client = None
    _status = ProviderStatus.UNAVAILABLE

    @classmethod
    def display_name(cls) -> str:
        return "Claude (Anthropic)"

    @classmethod
    def description(cls) -> str:
        return (
            "Best for strategic analysis, optimization recommendations, "
            "campaign reasoning, and evidence-backed decisions."
        )

    @classmethod
    def capabilities(cls) -> list[str]:
        return [
            "analysis",
            "optimization",
            "recommendations",
            "forecasting",
            "strategic_reasoning",
        ]

    def _ensure_client(self) -> bool:
        """Lazy-init the Anthropic client if a key is available."""
        if self._client is not None:
            return True

        api_key = get_key("claude")
        if not api_key:
            self._status = ProviderStatus.NO_KEY
            return False

        if not _HAS_ANTHROPIC:
            self._status = ProviderStatus.ERROR
            return False

        try:
            self._client = anthropic.Anthropic(api_key=api_key)
            self._status = ProviderStatus.AVAILABLE
            return True
        except Exception:
            self._status = ProviderStatus.ERROR
            return False

    def is_available(self) -> bool:
        return self._ensure_client()

    def get_status(self) -> ProviderStatus:
        self._ensure_client()
        return self._status

    def chat(self, message: str, context: dict[str, Any] | None = None) -> str:
        if not self._ensure_client():
            return _fallback_response(message)

        try:
            system_prompt = (
                "You are Claude, the AI marketing strategist for Marketing OS. "
                "You help users optimize ad campaigns across Meta, Google, TikTok, and more. "
                "Be concise, data-driven, and actionable. "
                "When appropriate, include specific percentages, dollar amounts, or KPIs."
            )
            resp = self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": message}],
            )
            return resp.content[0].text if resp.content else ""
        except Exception as exc:
            return f"Claude encountered an error: {exc}"

    def validate_key(self, key: str) -> bool:
        if not _HAS_ANTHROPIC:
            return False
        try:
            client = anthropic.Anthropic(api_key=key)
            client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False


def _fallback_response(message: str) -> str:
    """Local rule-based fallback when Claude API is unavailable.

    Provides simple keyword-matched answers so the system remains useful
    even without an API key configured.
    """
    q = message.lower()

    if "roas" in q:
        return (
            "To improve ROAS, consider:\n"
            "1. **Refine audience targeting** — narrow to high-intent segments\n"
            "2. **Optimize creative** — test new ad variants (A/B test)\n"
            "3. **Adjust bidding** — switch to ROAS-based bidding if available\n"
            "4. **Audit placement** — pause underperforming placements\n\n"
            "Configure your Claude API key in Settings for a detailed analysis."
        )
    if "cpa" in q or "cost per acquisition" in q:
        return (
            "To lower CPA:\n"
            "1. Review audience targeting — remove low-converting segments\n"
            "2. Test new creative — refresh fatigued ads\n"
            "3. Optimize landing pages — improve conversion rate\n"
            "4. Adjust bid strategy — lower bids on expensive placements\n\n"
            "Add a Claude API key in Settings for an AI-powered audit."
        )
    if "budget" in q:
        return (
            "Budget optimization tips:\n"
            "1. Shift budget from low-ROAS to high-ROAS campaigns\n"
            "2. Use dayparting to focus spend on peak hours\n"
            "3. Increase budget gradually (max 20% per day)\n\n"
            "Connect Claude in Settings for automated budget recommendations."
        )
    if "creative" in q or "ad" in q:
        return (
            "Creative best practices:\n"
            "1. Test 3-5 variants per campaign\n"
            "2. Use bold visuals and clear CTAs\n"
            "3. Refresh creatives every 2-3 weeks\n"
            "4. Match creative to platform (square for Feed, vertical for Stories)\n\n"
            "Enable OpenAI in Settings for AI-powered creative generation."
        )
    return (
        "I'm running in offline mode. For AI-powered analysis and recommendations, "
        "configure your Claude API key in **Settings > Integrations > AI Providers**."
    )
