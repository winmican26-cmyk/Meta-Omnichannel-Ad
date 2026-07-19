import pytest
from pydantic import ValidationError

from app.models.omnichannel import OmnichannelObject, SupportedEvent
from app.schemas.campaign import CampaignCreateRequest
from app.utils.validators import validate_tracking_specs


def valid_omnichannel() -> dict:
    return {
        "app": [
            {
                "application_id": "123",
                "custom_event_type": "PURCHASE",
                "object_store_urls": ["https://play.google.com/store/apps/details?id=com.example.app"],
            }
        ],
        "pixel": [{"pixel_id": "456", "custom_event_type": "PURCHASE"}],
    }


def test_omnichannel_requires_same_event_across_app_and_pixel() -> None:
    payload = valid_omnichannel()
    payload["pixel"][0]["custom_event_type"] = "LEAD"

    with pytest.raises(ValidationError, match="same custom_event_type"):
        OmnichannelObject.model_validate(payload)


def test_app_store_urls_must_be_store_urls() -> None:
    payload = valid_omnichannel()
    payload["app"][0]["object_store_urls"] = ["https://example.com/app"]

    with pytest.raises(ValidationError, match="Play Store or App Store"):
        OmnichannelObject.model_validate(payload)


def test_campaign_ids_must_match_omnichannel_objects() -> None:
    with pytest.raises(ValidationError, match="pixel_id must be present"):
        CampaignCreateRequest.model_validate(
            {
                "name": "Spring Promo",
                "session_id": "session-123",
                "page_id": "999",
                "daily_budget": 5000,
                "event": SupportedEvent.PURCHASE,
                "omnichannel": valid_omnichannel(),
                "pixel_id": "not-in-object",
                "application_id": "123",
                "web_url": "https://example.com",
            }
        )


def test_campaign_accepts_oauth_session_without_raw_token_or_account() -> None:
    request = CampaignCreateRequest.model_validate(
        {
            "name": "Spring Promo",
            "session_id": "session-123",
            "page_id": "999",
            "daily_budget": 5000,
            "event": SupportedEvent.PURCHASE,
            "omnichannel": valid_omnichannel(),
            "pixel_id": "456",
            "application_id": "123",
            "web_url": "https://example.com",
        }
    )

    assert request.session_id == "session-123"


def test_campaign_requires_session() -> None:
    with pytest.raises(ValidationError, match="session_id"):
        CampaignCreateRequest.model_validate(
            {
                "name": "Spring Promo",
                "page_id": "999",
                "daily_budget": 5000,
                "event": SupportedEvent.PURCHASE,
                "omnichannel": valid_omnichannel(),
                "pixel_id": "456",
                "application_id": "123",
                "web_url": "https://example.com",
            }
        )


def test_tracking_specs_include_web_event_app_event_and_install() -> None:
    specs = validate_tracking_specs("456", "123", SupportedEvent.PURCHASE)

    action_types = [spec["action.type"][0] for spec in specs]
    assert action_types == ["offsite_conversion", "app_custom_event", "mobile_app_install"]
    assert specs[0]["fb_pixel"] == ["456"]
    assert specs[1]["application"] == ["123"]
    assert specs[1]["custom_event_type"] == ["PURCHASE"]
