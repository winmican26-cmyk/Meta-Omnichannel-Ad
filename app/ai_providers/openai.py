"""OpenAI AI provider.

Wraps OpenAI's GPT-4o model for creative generation, quick answers, and
ad copy creation. Falls back to a local template-based generator when the
API key is not configured.
"""

from __future__ import annotations

import os
from typing import Any

from app.ai_providers.base import AIProvider, ProviderConfig, ProviderStatus
from app.key_manager import get_key

try:
    import openai

    _HAS_OPENAI = True
except ImportError:
    _HAS_OPENAI = False


class OpenAIProvider(AIProvider):
    """Provider that uses OpenAI GPT-4o for creative & generation tasks."""

    _client = None
    _status = ProviderStatus.UNAVAILABLE

    @classmethod
    def display_name(cls) -> str:
        return "OpenAI (GPT-4o)"

    @classmethod
    def description(cls) -> str:
        return (
            "Best for creative generation (ad copy, headlines, image prompts), "
            "quick Q&A, and structured data extraction."
        )

    @classmethod
    def capabilities(cls) -> list[str]:
        return [
            "creative_generation",
            "copywriting",
            "quick_answer",
            "image_generation",
            "brainstorming",
        ]

    def _ensure_client(self) -> bool:
        if self._client is not None:
            return True

        api_key = get_key("openai")
        if not api_key:
            self._status = ProviderStatus.NO_KEY
            return False

        if not _HAS_OPENAI:
            self._status = ProviderStatus.ERROR
            return False

        try:
            self._client = openai.OpenAI(api_key=api_key)
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
            return _fallback_creative(message)

        try:
            system_prompt = (
                "You are a creative marketing AI assistant. You help generate "
                "ad copy, headlines, creative briefs, and marketing ideas. "
                "Be concise, specific, and ready-to-use. "
                "When generating ad copy, provide 2-3 options with rationale."
            )
            resp = self._client.chat.completions.create(
                model="gpt-4o",
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            return f"OpenAI encountered an error: {exc}"

    def validate_key(self, key: str) -> bool:
        if not _HAS_OPENAI:
            return False
        try:
            client = openai.OpenAI(api_key=key)
            client.models.list()
            return True
        except Exception:
            return False


def _fallback_creative(message: str) -> str:
    """Local template-based fallback for creative generation.

    Provides useful output even without an OpenAI API key.
    """
    q = message.lower()

    if "headline" in q or "headline" in message:
        return (
            "Here are 3 headline options:\n\n"
            '1. **"Don\'t Just Sell. Scale."** — Short, punchy, action-oriented\n'
            '2. **"Your Next Best Customer Is Waiting."** — Curiosity-driven\n'
            '3. **"Results You Can Measure. Growth You Can Trust."** — Trust-focused\n\n'
            "Connect OpenAI in Settings for AI-generated headlines tailored to your brand."
        )
    if "ad copy" in q or "copy" in q:
        return (
            "Ad copy framework:\n\n"
            "**Hook** (first 3 seconds): Lead with the biggest benefit\n"
            "**Problem**: Name the pain point\n"
            "**Solution**: Present your offer\n"
            "**Proof**: Social proof or statistic\n"
            "**CTA**: Clear next step\n\n"
            "Example for a DTC brand:\n"
            '> "Tired of high CPA? Our AI optimizes your ad spend in real-time. '
            'Customers see 34% lower costs in the first week. Try it free."\n\n'
            "Add an OpenAI key in Settings for unlimited AI-generated copy."
        )
    if "image" in q or "visual" in q:
        return (
            "Image generation requires an OpenAI API key with DALL-E access. "
            "Once configured, I can generate:\n"
            "- Product lifestyle photos\n"
            "- Social media creatives\n"
            "- A/B test variants\n"
            "- Campaign mood boards"
        )
    if "brainstorm" in q or "idea" in q:
        return (
            "Brainstorming prompt ideas:\n\n"
            '1. **Social Proof** — "Join 10,000+ marketers who cut CPA by 30%"\n'
            '2. **Curiosity Gap** — "The one metric your dashboard is hiding"\n'
            '3. **Loss Aversion** — "Don\'t let another $1,000 vanish on bad ads"\n'
            '4. **Authority** — "Built by ex-Google engineers. Used by top brands."\n\n'
            "Enable OpenAI for more creative options."
        )
    return (
        "I'm running in offline creative mode. For AI-powered copy, headlines, "
        "and image generation, configure your OpenAI API key in "
        "**Settings > Integrations > AI Providers**."
    )
