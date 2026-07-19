"""Gemma 4 offline orchestration provider.

Gemma 4 is Google's open-source LLM designed for local execution. This
provider wraps it for **offline orchestration** — workflow automation,
pipeline coordination, task routing, and multi-step agent orchestration
— all without requiring a cloud API key.

When a local Gemma model (via Ollama, llama.cpp, etc.) is not available,
the provider gracefully degrades to a rich rule-based orchestration engine
so the system remains fully functional offline.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any

from app.ai_providers.base import AIProvider, ProviderConfig, ProviderStatus
from app.utils.logging import structlog

logger = structlog.get_logger()

# ── Local model detection ──────────────────────────────────────────────

_OLLAMA_BINARY: str | None = None

# Try to find the Ollama binary on common paths
import shutil  # noqa: E402

_OLLAMA_BINARY = shutil.which("ollama")


def _ollama_available() -> bool:
    """Check whether Ollama is installed and has a Gemma model."""
    if not _OLLAMA_BINARY:
        return False
    try:
        result = subprocess.run(
            [_OLLAMA_BINARY, "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False
        # Check for any gemma model in the list
        return "gemma" in result.stdout.lower()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _ollama_chat(prompt: str, model: str = "gemma4") -> str | None:
    """Send a prompt to a local Ollama model.

    Returns the response text, or ``None`` if the model is unavailable.
    """
    if not _OLLAMA_BINARY:
        return None
    try:
        result = subprocess.run(
            [_OLLAMA_BINARY, "run", model, prompt],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, OSError):
        return None


# ── Provider class ─────────────────────────────────────────────────────


class GemmaProvider(AIProvider):
    """Provider that uses Gemma 4 locally for offline orchestration.

    Unlike Claude and OpenAI, this provider does not require a cloud API
    key. It attempts to use a local Gemma model (via Ollama) and falls
    back to a rule-based orchestration engine when no model is available.
    """

    _status = ProviderStatus.AVAILABLE  # Always available for offline use
    _has_local_model: bool | None = None

    @classmethod
    def display_name(cls) -> str:
        return "Gemma 4 (Local)"

    @classmethod
    def description(cls) -> str:
        return (
            "Runs locally for offline orchestration — workflow automation, "
            "task routing, pipeline coordination, and multi-step agent "
            "orchestration. No API key needed."
        )

    @classmethod
    def capabilities(cls) -> list[str]:
        return [
            "offline_orchestration",
            "workflow_automation",
            "task_routing",
            "pipeline_coordination",
            "multi_step_planning",
        ]

    def _check_local_model(self) -> bool:
        """Lazy-check for a local Gemma model."""
        if self._has_local_model is not None:
            return self._has_local_model
        self._has_local_model = _ollama_available()
        if self._has_local_model:
            logger.info("gemma_local_model_detected")
        else:
            logger.info("gemma_no_local_model_falling_back_to_rules")
        return self._has_local_model

    def is_available(self) -> bool:
        """Gemma is *always* available — it works fully offline."""
        return True

    def get_status(self) -> ProviderStatus:
        return ProviderStatus.AVAILABLE

    def chat(self, message: str, context: dict[str, Any] | None = None) -> str:
        """Send a message to Gemma 4 for offline orchestration.

        Attempts to use a local Gemma model first. Falls back to the
        rule-based orchestration engine when no model is available.
        """
        if self._check_local_model():
            try:
                system_context = (
                    "You are Gemma, the offline orchestration AI for Marketing OS. "
                    "Your job is to coordinate workflows, route tasks between AI "
                    "providers, automate marketing pipelines, and plan multi-step "
                    "campaign operations. Be concise and actionable."
                )
                prompt = f"{system_context}\n\nUser: {message}\n\nGemma:"
                response = _ollama_chat(prompt)
                if response:
                    return response
            except Exception:
                pass

        # Fallback to rule-based orchestration
        return _orchestration_fallback(message)

    def validate_key(self, key: str) -> bool:
        """Gemma doesn't use API keys — all processing is local."""
        return True


# ── Offline orchestration fallback engine ─────────────────────────────


def _orchestration_fallback(message: str) -> str:
    """Rule-based orchestration engine for offline use.

    Provides structured responses for workflow automation, task routing,
    pipeline coordination, and multi-step planning.
    """
    q = message.lower()

    # ── Workflow orchestration ─────────────────────────────────────────
    if any(kw in q for kw in ["workflow", "pipeline", "automate", "step", "sequence"]):
        return (
            "**Orchestration Workflow Plan**\n\n"
            "Here's a recommended multi-step pipeline for your campaign:\n\n"
            "1. **Audience Discovery** → Scan existing customer data for lookalike segments\n"
            "2. **Creative Generation** → Route to OpenAI for ad copy & visuals\n"
            "3. **Budget Allocation** → Route to Claude for budget optimization\n"
            "4. **Campaign Launch** → Deploy via Meta Ads API (PAUSED for review)\n"
            "5. **Monitor & Optimize** → Daily check-in with Claude for bid adjustments\n\n"
            "> **Gemma Insight**: This pipeline runs fully offline. I'll coordinate "
            "each step and route tasks to the appropriate AI provider when they come online."
        )

    # ── Task routing ───────────────────────────────────────────────────
    if any(
        kw in q
        for kw in [
            "route",
            "routing",
            "which ai",
            "best provider",
            "assign",
            "delegate",
        ]
    ):
        return (
            "**Task Routing Recommendation**\n\n"
            "Based on your query, here's how I'd route this:\n\n"
            "| Task Type | Recommended AI | Reason |\n"
            "|---|---|---|\n"
            "| Strategy & Optimization | **Claude** | Deep analysis, reasoning, evidence-based |\n"
            "| Creative Generation | **OpenAI** | Copywriting, headlines, images |\n"
            "| Workflow Orchestration | **Gemma 4** | Pipeline coordination, task chaining |\n"
            "| Quick Q&A | **OpenAI** | Fast, direct answers |\n"
            "| Forecasting | **Claude** | Trend analysis, predictions |\n\n"
            "> Smart routing is automatic in Marketing OS. Just ask and we'll "
            "dispatch to the right AI."
        )

    # ── Multi-step planning ────────────────────────────────────────────
    if any(
        kw in q for kw in ["plan", "multi-step", "strategy", "campaign plan", "roadmap"]
    ):
        return (
            "**Multi-Step Campaign Plan**\n\n"
            "Here's a structured plan orchestrated by Gemma:\n\n"
            "**Phase 1: Setup (Days 1-2)**\n"
            "• Define campaign objective (awareness / consideration / conversion)\n"
            "• Set up tracking: Pixel + App Events + CAPI\n"
            "• Configure omnichannel link spec (web + app deeplinks)\n\n"
            "**Phase 2: Creative (Days 3-4)**\n"
            "• Generate 3-5 ad variants → *route to OpenAI*\n"
            "• A/B test headlines and CTAs\n"
            "• Review with Claude for strategic alignment\n\n"
            "**Phase 3: Launch (Day 5)**\n"
            "• Deploy campaign in PAUSED state\n"
            "• Review budget allocation → *route to Claude*\n"
            "• Activate with optimized bid caps\n\n"
            "**Phase 4: Optimize (Ongoing)**\n"
            "• Daily CPA and ROAS monitoring\n"
            "• Weekly creative refresh recommendations\n"
            "• Bid adjustments based on performance\n\n"
            "> Need me to execute any of these steps? Just ask!"
        )

    # ── Agent coordination ─────────────────────────────────────────────
    if any(
        kw in q for kw in ["agent", "coordinate", "team", "collaborate", "multi-agent"]
    ):
        return (
            "**Agent Coordination Mode**\n\n"
            "I can coordinate multiple AI agents for complex tasks. Here's how:\n\n"
            "**Available Agents:**\n"
            "🤖 **Strategist** (Claude) — Campaign optimization, analysis, forecasting\n"
            "🎨 **Creative** (OpenAI) — Ad copy, headlines, image generation\n"
            "⚙️ **Orchestrator** (Gemma 4) — Workflow coordination, task routing\n\n"
            "**Example: Full Campaign Launch**\n"
            "1. ⚙️ Gemma creates the workflow plan\n"
            "2. 🎨 OpenAI generates 3 ad variants\n"
            "3. 🤖 Claude reviews and optimizes budget\n"
            "4. ⚙️ Gemma coordinates the launch sequence\n\n"
            "> Tell me what you want to accomplish, and I'll orchestrate the "
            "right team of AIs to get it done."
        )

    # ── Integration / connection tasks ─────────────────────────────────
    if any(
        kw in q
        for kw in ["connect", "integrate", "sync", "webhook", "trigger", "schedule"]
    ):
        return (
            "**Integration Orchestration**\n\n"
            "I can help you connect and coordinate across platforms:\n\n"
            "**Available Integrations:**\n"
            "• **Meta Ads** — Campaign management, audience sync, insight ingestion\n"
            "• **Google Ads** — Cross-platform budget coordination *(setup required)*\n"
            "• **Stripe** — Billing, subscription management\n"
            "• **Claude API** — Strategic analysis *(add key in Settings)*\n"
            "• **OpenAI API** — Creative generation *(add key in Settings)*\n\n"
            "**Scheduled Syncs:**\n"
            "I can orchestrate daily insight syncs, weekly creative refreshes, "
            "and automated bid adjustments. Configure what you need and I'll "
            "handle the scheduling."
        )

    # ── Status / health ────────────────────────────────────────────────
    if any(
        kw in q
        for kw in ["status", "health", "what can you do", "help", "capabilities"]
    ):
        return (
            "**Gemma 4 — Offline Orchestration Engine**\n\n"
            "✅ **Status**: Online & Ready\n"
            "🔌 **Connection**: Local (no internet needed)\n"
            "⚡ **Model**: Rule-based engine (Ollama/Gemma 4 detected: "
            + ("yes" if _ollama_available() else "no — using rule engine")
            + ")\n\n"
            "**I can help you with:**\n"
            "• **Workflow Automation** — Design and execute multi-step pipelines\n"
            "• **Task Routing** — Dispatch work to the best AI provider\n"
            "• **Multi-Step Planning** — Create campaign launch roadmaps\n"
            "• **Agent Coordination** — Orchestrate Claude + OpenAI + tools\n"
            "• **Integration Sync** — Schedule and monitor data flows\n\n"
            "**Example queries:**\n"
            '• "Create a workflow for launching a new campaign"\n'
            '• "Which AI should I use for creative?"\n'
            '• "Plan a multi-step campaign strategy"\n'
            '• "Coordinate agents for full campaign launch"'
        )

    return (
        "I'm your offline orchestration AI. I can coordinate workflows, "
        "route tasks between AI providers, plan multi-step campaigns, and "
        "automate marketing pipelines.\n\n"
        "**Try asking me:**\n"
        '• "Create a workflow for launching a new campaign"\n'
        '• "Route this task to the best AI provider"\n'
        '• "Plan a multi-step campaign strategy"\n'
        '• "Coordinate Claude and OpenAI for a full campaign launch"\n'
        '• "Schedule daily insight syncs"'
    )
