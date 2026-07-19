from app.ai_optimizer import AIOptimizer, OptimizeRequest


def test_optimizer_prioritizes_app_for_purchase_with_deeplink() -> None:
    request = OptimizeRequest.model_validate(
        {
            "session_id": "session-123",
            "name": "Spring Promo",
            "event": "PURCHASE",
            "omnichannel": {"app": [], "pixel": []},
            "daily_budget": 5000,
            "web_url": "https://example.com/products",
            "android_deeplink": "myapp://products",
        }
    )

    suggestion = AIOptimizer.get_suggestions(request)

    assert suggestion.recommendations[0].channel == "app"
    assert suggestion.recommendations[0].weight_percent == 65
    assert suggestion.suggested_bid_cap == 60
    assert suggestion.deep_link_routing_rule == "deeplink_with_web_fallback"


def test_optimizer_returns_balanced_when_no_deeplink() -> None:
    request = OptimizeRequest.model_validate(
        {
            "session_id": "session-123",
            "name": "Lead Promo",
            "event": "LEAD",
            "omnichannel": {"app": [], "pixel": []},
            "daily_budget": 5000,
            "web_url": "https://example.com/signup",
        }
    )

    suggestion = AIOptimizer.get_suggestions(request)

    assert suggestion.recommendations[0].channel == "balanced"
    assert suggestion.suggested_bid_cap is None
