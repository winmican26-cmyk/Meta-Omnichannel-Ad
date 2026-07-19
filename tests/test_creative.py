from app.creative_studio import CreativeGenerateRequest, CreativeStudio


def test_creative_generator_returns_default_omnichannel_variant() -> None:
    request = CreativeGenerateRequest.model_validate(
        {
            "session_id": "session-123",
            "name": "Spring Promo",
            "web_url": "https://example.com/products",
            "application_id": "123",
            "page_id": "999",
            "android_deeplink": "https://example.com/app/products",
            "event": "PURCHASE",
        }
    )

    variants = CreativeStudio.generate_creatives(request)

    assert len(variants) == 1
    assert variants[0].name == "Omnichannel Default"
    assert variants[0].deep_link_routing == "deeplink_with_web_fallback"
    assert variants[0].omnichannel_link_spec.app.application_id == "123"
    assert "android" in variants[0].omnichannel_link_spec.app.platform_specs


def test_creative_generator_adds_catalog_variant() -> None:
    request = CreativeGenerateRequest.model_validate(
        {
            "session_id": "session-123",
            "name": "Catalog Promo",
            "web_url": "https://example.com/products",
            "application_id": "123",
            "event": "ADD_TO_CART",
            "product_id": "sku-123",
            "catalog_mode": True,
        }
    )

    variants = CreativeStudio.generate_creatives(request)

    assert len(variants) == 2
    assert variants[1].name == "Advantage+ Catalog Dynamic"
    assert "template_url_spec" in variants[1].creative_spec
