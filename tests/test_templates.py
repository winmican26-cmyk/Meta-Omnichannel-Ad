import importlib

from app.schemas.campaign import CampaignCreateRequest


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


def campaign_request() -> CampaignCreateRequest:
    return CampaignCreateRequest.model_validate(
        {
            "name": "Spring Promo",
            "session_id": "template-session",
            "page_id": "999",
            "daily_budget": 5000,
            "event": "PURCHASE",
            "omnichannel": valid_omnichannel(),
            "pixel_id": "456",
            "application_id": "123",
            "web_url": "https://example.com/products",
        }
    )


def test_save_list_and_duplicate_template(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "campaigns.db"
    monkeypatch.setenv("CCCO_DB_PATH", str(db_path))

    import app.database as database
    import app.templates as templates

    database = importlib.reload(database)
    templates = importlib.reload(templates)
    database.init_db()

    templates.TemplatesService.save_as_template(
        session_id="template-session",
        name="Reusable Spring Promo",
        config=campaign_request(),
        original_adset_id="238500000000001",
    )

    rows = templates.TemplatesService.list_templates("template-session")
    assert len(rows) == 1
    assert rows[0].name == "Reusable Spring Promo"
    assert rows[0].original_adset_id == "238500000000001"

    duplicate = templates.TemplatesService.duplicate_from_template(
        template_id=rows[0].id,
        session_id="template-session",
        new_name="Duplicated Promo",
        new_daily_budget=7500,
    )

    assert duplicate.name == "Duplicated Promo"
    assert duplicate.daily_budget == 7500
    assert duplicate.session_id == "template-session"
