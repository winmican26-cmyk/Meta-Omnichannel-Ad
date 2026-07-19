from typing import Any, Literal

from pydantic import AnyUrl, BaseModel, Field

from app.ai_optimizer import AIOptimizer, OptimizeRequest
from app.models.omnichannel import OmnichannelLinkSpec, SupportedEvent
from app.utils.logging import structlog

logger = structlog.get_logger()


class CreativeGenerateRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    web_url: AnyUrl
    application_id: str = Field(..., min_length=1)
    page_id: str | None = None
    android_deeplink: AnyUrl | None = None
    ios_deeplink: AnyUrl | None = None
    event: SupportedEvent
    product_id: str | None = None
    catalog_mode: bool = False


class CreativeVariant(BaseModel):
    name: str
    creative_spec: dict[str, Any]
    omnichannel_link_spec: OmnichannelLinkSpec
    deep_link_routing: Literal["deeplink_with_web_fallback", "app_only", "web_only"]
    expected_ctr_lift: float


class CreativeStudio:
    @staticmethod
    def generate_creatives(req: CreativeGenerateRequest) -> list[CreativeVariant]:
        opt_req = OptimizeRequest(
            session_id=req.session_id,
            name=req.name,
            event=req.event,
            omnichannel={},
            daily_budget=1000,
            web_url=req.web_url,
            android_deeplink=str(req.android_deeplink) if req.android_deeplink else None,
            ios_deeplink=str(req.ios_deeplink) if req.ios_deeplink else None,
        )
        ai_suggestions = AIOptimizer.get_suggestions(opt_req)

        platform_specs: dict[str, dict[str, str]] = {}
        if req.android_deeplink:
            platform_specs["android"] = {"url": str(req.android_deeplink)}
        if req.ios_deeplink:
            platform_specs["ios"] = {"url": str(req.ios_deeplink)}

        routing: Literal["deeplink_with_web_fallback", "app_only", "web_only"]
        routing = "deeplink_with_web_fallback" if platform_specs else "web_only"

        default_variant = CreativeVariant(
            name="Omnichannel Default",
            creative_spec={
                "name": f"{req.name} - Omnichannel",
                "applink_treatment": routing,
                "object_story_spec": {
                    "page_id": req.page_id or "<PAGE_ID_FROM_SESSION>",
                    "link_data": {
                        "call_to_action": {"type": "LEARN_MORE"},
                        "link": str(req.web_url),
                        "message": "Shop on web or open in app for a better experience.",
                    },
                },
            },
            omnichannel_link_spec=OmnichannelLinkSpec.model_validate(
                {
                    "web": {"url": str(req.web_url)},
                    "app": {
                        "application_id": req.application_id,
                        "platform_specs": platform_specs,
                    },
                }
            ),
            deep_link_routing=routing,
            expected_ctr_lift=round(ai_suggestions.recommendations[0].expected_cpa_lift * 0.8, 2),
        )

        variants = [default_variant]

        if req.catalog_mode and req.product_id:
            product_deeplink = f"yourapp://product/{req.product_id}"
            variants.append(
                CreativeVariant(
                    name="Advantage+ Catalog Dynamic",
                    creative_spec={
                        "name": f"{req.name} - Catalog Dynamic",
                        "applink_treatment": "deeplink_with_web_fallback",
                        "template_url_spec": {
                            "android": {"url": "yourapp://product/{product.id}"},
                            "ios": {"url": "yourapp://product/{product.id}"},
                            "web": {"url": str(req.web_url)},
                            "config": {"app_id": req.application_id},
                        },
                    },
                    omnichannel_link_spec=OmnichannelLinkSpec.model_validate(
                        {
                            "web": {"url": str(req.web_url)},
                            "app": {
                                "application_id": req.application_id,
                                "platform_specs": {
                                    "android": {"url": product_deeplink},
                                    "ios": {"url": product_deeplink},
                                },
                            },
                        }
                    ),
                    deep_link_routing="deeplink_with_web_fallback",
                    expected_ctr_lift=42.0,
                )
            )

        logger.info("creative_variants_generated", name=req.name, count=len(variants))
        return variants
