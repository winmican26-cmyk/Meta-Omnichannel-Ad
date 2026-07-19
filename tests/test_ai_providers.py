"""E2E tests for the AI provider system, smart routing, and key management.

Tests require the FastAPI backend to be running (handled automatically via
``TestClient``).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.database import init_db, DB_PATH
from app.main import app


@pytest.fixture(autouse=True)
def _clean_db():
    """Ensure a clean database for each test."""
    init_db()
    yield
    # Clean up api_keys table after each test (only if it exists)
    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        if "api_keys" in tables:
            conn.execute("DELETE FROM api_keys")
            conn.commit()
    finally:
        conn.close()


client = TestClient(app)


class TestAIProviderRouting:
    """Tests for the smart routing engine."""

    def test_classify_analysis_routes_to_claude(self):
        """Analysis/optimization queries should route to Claude."""
        from app.ai_providers import classify_task

        assert classify_task("How can I improve my ROAS?") == "claude"
        assert classify_task("Optimize my budget across campaigns") == "claude"
        assert classify_task("Why is my CPA rising?") == "claude"
        assert classify_task("Analyze campaign performance trends") == "claude"

    def test_classify_creative_routes_to_openai(self):
        """Creative/generation queries should route to OpenAI."""
        from app.ai_providers import classify_task

        assert classify_task("Generate ad headlines for Spring Sale") == "openai"
        assert classify_task("Create 3 ad copy variants") == "openai"
        assert classify_task("Write a video script") == "openai"
        assert classify_task("Brainstorm creative ideas") == "openai"

    def test_classify_defaults_to_claude(self):
        """Unclassified queries should default to Claude."""
        from app.ai_providers import classify_task

        assert classify_task("Hello, what can you do?") == "claude"
        assert classify_task("Tell me about marketing") == "claude"

    def test_list_providers_returns_both(self):
        """list_providers should return Claude and OpenAI entries."""
        from app.ai_providers import list_providers

        providers = list_providers()
        names = {p["name"] for p in providers}
        assert "claude" in names
        assert "openai" in names

    def test_providers_have_capabilities(self):
        """Each provider should list its capabilities."""
        from app.ai_providers import list_providers

        providers = list_providers()
        for p in providers:
            assert len(p["capabilities"]) > 0
            assert p["label"] is not None
            assert p["description"] is not None

    def test_route_query_fallback_no_keys(self):
        """route_query should gracefully handle no configured keys."""
        from app.ai_providers import route_query

        provider, note = route_query("How can I improve my ROAS?")
        assert provider is None or note is not None


class TestKeyManager:
    """Tests for encrypted API key storage."""

    def test_save_and_get_key(self):
        """Keys should be encryptable and retrievable."""
        from app.key_manager import save_key, get_key

        save_key("claude", "sk-ant-test123")
        retrieved = get_key("claude")
        assert retrieved == "sk-ant-test123"

    def test_has_key_true_after_save(self):
        """has_key should return True after saving a key."""
        from app.key_manager import save_key, has_key

        assert has_key("openai") is False
        save_key("openai", "sk-openai-test456")
        assert has_key("openai") is True

    def test_has_key_false_before_save(self):
        """has_key should return False for providers without keys."""
        from app.key_manager import has_key

        assert has_key("nonexistent") is False

    def test_delete_key(self):
        """Delete should remove a stored key."""
        from app.key_manager import save_key, has_key, delete_key

        save_key("claude", "sk-ant-test789")
        assert has_key("claude") is True
        deleted = delete_key("claude")
        assert deleted is True
        assert has_key("claude") is False

    def test_delete_nonexistent_key_returns_false(self):
        """Deleting a key that doesn't exist should return False."""
        from app.key_manager import delete_key

        assert delete_key("nonexistent") is False

    def test_list_keys_metadata_only(self):
        """list_keys should return metadata, not plaintext keys."""
        from app.key_manager import save_key, list_keys

        save_key("claude", "sk-ant-secret", label="Production")
        save_key("openai", "sk-openai-secret")
        keys = list_keys()
        assert len(keys) == 2
        for k in keys:
            assert "provider" in k
            assert "encrypted_key" not in k  # Must not expose encrypted blob
            assert "created_at" in k

    def test_multiple_keys_independent(self):
        """Multiple providers should store their keys independently."""
        from app.key_manager import save_key, get_key

        save_key("claude", "claude-key-1")
        save_key("openai", "openai-key-1")
        assert get_key("claude") == "claude-key-1"
        assert get_key("openai") == "openai-key-1"


class TestAIEndpoints:
    """Tests for the AI REST API endpoints."""

    def test_get_providers_list(self):
        """GET /ai/providers should return the provider list."""
        resp = client.get("/ai/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        names = {p["name"] for p in data}
        assert "claude" in names
        assert "openai" in names

    def test_chat_returns_fallback_when_no_keys(self):
        """POST /ai/chat should return a helpful fallback without keys."""
        resp = client.post("/ai/chat", json={"message": "How can I improve my ROAS?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert data["provider_used"] is not None
        assert len(data["response"]) > 0

    def test_chat_creative_routes_to_openai_fallback(self):
        """Creative queries should return a helpful response even without keys."""
        resp = client.post(
            "/ai/chat", json={"message": "Generate ad headlines for a new campaign"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert len(data["response"]) > 0
        # Should indicate offline/fallback mode when no keys configured
        assert any(
            word in data["response"].lower()
            for word in [
                "offline",
                "offline mode",
                "key",
                "openai",
                "headline",
                "configure",
            ]
        )

    def test_chat_forced_provider_needs_key(self):
        """A specific provider returns 503 when no key is configured."""
        resp = client.post("/ai/chat", json={"message": "Hello", "provider": "claude"})
        # Without a configured key, the provider is unavailable
        assert resp.status_code == 503

    def test_chat_invalid_provider_returns_404(self):
        """An invalid provider name should return 404."""
        resp = client.post(
            "/ai/chat", json={"message": "Hello", "provider": "nonexistent"}
        )
        assert resp.status_code == 404

    def test_save_and_delete_key_via_api(self):
        """The full key lifecycle should work via REST API."""
        # Save
        resp = client.post(
            "/ai/keys",
            json={"provider": "claude", "key": "sk-ant-e2e-test-key"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "saved"

        # Check status
        resp = client.get("/ai/keys/claude/status")
        assert resp.status_code == 200
        assert resp.json()["configured"] is True

        # Delete
        resp = client.delete("/ai/keys/claude")
        assert resp.status_code == 200

        # Verify deleted
        resp = client.get("/ai/keys/claude/status")
        assert resp.status_code == 200
        assert resp.json()["configured"] is False

    def test_key_status_for_unknown_provider(self):
        """Unknown providers should return configured=False."""
        resp = client.get("/ai/keys/nonexistent/status")
        assert resp.status_code == 200
        assert resp.json()["configured"] is False
        assert resp.json()["provider"] == "nonexistent"

    def test_list_keys_empty_initially(self):
        """GET /ai/keys should return an empty list initially."""
        resp = client.get("/ai/keys")
        assert resp.status_code == 200
        assert resp.json() == []
