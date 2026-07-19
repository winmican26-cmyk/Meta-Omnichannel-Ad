"""Abstract base class for AI providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class ProviderStatus(Enum):
    AVAILABLE = "available"
    NO_KEY = "no_key"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


class ProviderConfig:
    """Configuration for an AI provider instance.

    Attributes:
        name: Provider identifier (e.g. ``"claude"``, ``"openai"``).
    """

    def __init__(self, name: str) -> None:
        self.name = name


class AIProvider(ABC):
    """Abstract interface for an AI model provider."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    # ------------------------------------------------------------------
    # Metadata (class-level, no instance needed)
    # ------------------------------------------------------------------

    @classmethod
    @abstractmethod
    def display_name(cls) -> str:
        """Human-readable name shown in the UI."""

    @classmethod
    @abstractmethod
    def description(cls) -> str:
        """Short description of the provider's strengths."""

    @classmethod
    @abstractmethod
    def capabilities(cls) -> list[str]:
        """List of task types this provider excels at."""

    # ------------------------------------------------------------------
    # Instance methods
    # ------------------------------------------------------------------

    @abstractmethod
    def is_available(self) -> bool:
        """Whether the provider has a key configured and is ready."""

    @abstractmethod
    def get_status(self) -> ProviderStatus:
        """Return current provider status."""

    @abstractmethod
    def chat(self, message: str, context: dict[str, Any] | None = None) -> str:
        """Send a chat message and return the response."""

    @abstractmethod
    def validate_key(self, key: str) -> bool:
        """Check whether *key* is valid for this provider."""
