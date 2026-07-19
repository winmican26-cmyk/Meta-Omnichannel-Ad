"""AI provider registry and smart router.

Exposes :func:`route_query` which classifies a user message by task type and
routes it to the most capable available provider.
"""

from __future__ import annotations

from app.ai_providers.base import AIProvider, ProviderConfig, ProviderStatus
from app.ai_providers.claude import ClaudeProvider
from app.ai_providers.openai import OpenAIProvider

# Registry of available providers (name -> class)
_PROVIDER_CLASSES: dict[str, type[AIProvider]] = {
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
}

# Cache of initialized provider instances
_providers: dict[str, AIProvider] = {}

# Task classification rules: (keywords, recommended_provider)
_TASK_ROUTES = [
    # Claude is best at
    (
        [
            "optimize",
            "optimisation",
            "improve roas",
            "improve cpa",
            "lower cpa",
            "increase roas",
            "bid",
            "budget",
            "strategy",
            "strategic",
            "recommendation",
            "suggest",
            "analysis",
            "analyze",
            "analyse",
            "why is",
            "explain",
            "reason",
            "evidence",
            "compare",
            "trend",
            "performance",
            "insight",
            "forecast",
            "predict",
        ],
        "claude",
    ),
    # OpenAI is best at
    (
        [
            "generate",
            "create",
            "write",
            "draft",
            "copy",
            "headline",
            "creative",
            "image",
            "picture",
            "photo",
            "design",
            "ad copy",
            "caption",
            "description",
            "video script",
            "storyboard",
            "brainstorm",
            "idea",
            "variant",
            "variation",
        ],
        "openai",
    ),
]

_DEFAULT_PROVIDER = "claude"


def get_provider(name: str) -> AIProvider | None:
    """Get (or create) a cached provider instance by name."""
    if name not in _PROVIDER_CLASSES:
        return None
    if name not in _providers:
        cfg = ProviderConfig(name=name)
        _providers[name] = _PROVIDER_CLASSES[name](cfg)
    return _providers[name]


def list_providers() -> list[dict]:
    """Return status info for every registered provider."""
    result = []
    for name, cls in _PROVIDER_CLASSES.items():
        provider = get_provider(name)
        status = provider.get_status() if provider else ProviderStatus.UNAVAILABLE
        result.append(
            {
                "name": name,
                "label": cls.display_name(),
                "status": status.value,
                "description": cls.description(),
                "capabilities": cls.capabilities(),
            }
        )
    return result


def classify_task(query: str) -> str:
    """Classify a user query into a provider name based on keyword matching.

    Returns the provider name best suited to handle the query.
    """
    q = query.lower()
    for keywords, provider in _TASK_ROUTES:
        if any(kw in q for kw in keywords):
            return provider
    return _DEFAULT_PROVIDER


def route_query(query: str) -> tuple[AIProvider | None, str]:
    """Route *query* to the best available provider.

    Returns ``(provider, classification_reason)``.
    If the preferred provider has no key configured, falls back to any
    available provider.
    """
    preferred = classify_task(query)

    # Try preferred provider
    provider = get_provider(preferred)
    if provider and provider.is_available():
        return provider, f"routed to {preferred} (best for this task)"

    # Fallback: try any available provider
    for name in _PROVIDER_CLASSES:
        if name == preferred:
            continue
        provider = get_provider(name)
        if provider and provider.is_available():
            return provider, f"routed to {name} (fallback — {preferred} unavailable)"

    return None, "no AI provider available (configure API keys in Settings)"


__all__ = [
    "AIProvider",
    "ProviderConfig",
    "ProviderStatus",
    "get_provider",
    "list_providers",
    "classify_task",
    "route_query",
]
