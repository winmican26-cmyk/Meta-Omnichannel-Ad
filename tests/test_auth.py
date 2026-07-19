from fastapi.testclient import TestClient

from app.auth import active_sessions
from app.main import app


def test_switch_account_updates_active_session() -> None:
    active_sessions["test-session"] = {
        "access_token": "token",
        "ad_account_id": "act_1",
        "ad_accounts": [{"id": "act_1", "name": "One"}, {"id": "act_2", "name": "Two"}],
    }

    client = TestClient(app)
    response = client.post(
        "/auth/switch-account/act_2",
        headers={"X-Session-ID": "test-session"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "switched", "ad_account_id": "act_2"}
    assert active_sessions["test-session"]["ad_account_id"] == "act_2"


def test_auth_me_requires_session() -> None:
    client = TestClient(app)
    response = client.get("/auth/me")

    assert response.status_code == 401
