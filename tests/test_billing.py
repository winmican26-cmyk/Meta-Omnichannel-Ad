from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.auth import active_sessions
from app.main import app


def test_checkout_flow_returns_stripe_checkout_url(monkeypatch) -> None:
    import app.billing as billing

    active_sessions["billing-session"] = {
        "access_token": "token",
        "ad_account_id": "act_1",
        "ad_accounts": [{"id": "act_1"}],
        "user_email": "buyer@example.com",
        "subscription_tier": "free",
    }

    class FakeCheckoutSession:
        @staticmethod
        def create(**kwargs):
            assert kwargs["mode"] == "subscription"
            assert kwargs["metadata"] == {"user_session_id": "billing-session", "plan": "pro"}
            return SimpleNamespace(url="https://checkout.stripe.test/session")

    fake_stripe = SimpleNamespace(checkout=SimpleNamespace(Session=FakeCheckoutSession))
    monkeypatch.setattr(billing, "_stripe", lambda: fake_stripe)
    monkeypatch.setattr(billing, "STRIPE_PRO_PRICE_ID", "price_pro")

    client = TestClient(app)
    response = client.post("/billing/checkout", json={"session_id": "billing-session", "plan": "pro"})

    assert response.status_code == 200
    assert response.json() == {"checkout_url": "https://checkout.stripe.test/session"}


def test_paid_subscription_required_for_paid_operations() -> None:
    from app.billing import require_paid_subscription

    require_paid_subscription({"subscription_tier": "pro"})
    require_paid_subscription({"subscription_tier": "enterprise"})
