from app.database import save_ccco_campaign
from app.models.omnichannel import OmnichannelObject, SupportedEvent
from app.services.meta_client import MetaClient
from app.utils.logging import structlog
from app.utils.validators import validate_tracking_specs

logger = structlog.get_logger()


class CampaignService:
    def __init__(self, access_token: str, ad_account_id: str):
        self.client = MetaClient(access_token)
        self.ad_account_id = ad_account_id

    async def create_cross_channel_adset(
        self,
        *,
        name: str,
        daily_budget: int,
        event: SupportedEvent,
        omnichannel: OmnichannelObject,
        pixel_id: str,
        application_id: str,
        page_id: str,
        web_url: str,
        message: str,
        countries: list[str],
        android_deeplink: str | None = None,
        ios_deeplink: str | None = None,
        session_id: str | None = None,
        bid_amount_cents: int | None = None,
    ) -> dict[str, str]:
        try:
            from facebook_business.adobjects.ad import Ad
            from facebook_business.adobjects.adcreative import AdCreative
            from facebook_business.adobjects.adset import AdSet
            if omnichannel.event != event:
                raise ValueError("Request event must match omnichannel custom_event_type")

            adset_payload: dict = {
                "name": f"{name} - CCCO",
                "daily_budget": daily_budget,
                "optimization_goal": "OFFSITE_CONVERSIONS",
                "billing_event": "IMPRESSIONS",
                "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                "promoted_object": {
                    "omnichannel_object": omnichannel.model_dump(),
                },
                "targeting": {"geo_locations": {"countries": countries}},
                "status": "PAUSED",
            }
            if bid_amount_cents is not None:
                # Apply the optimizer's suggested_bid_cap to actual Meta
                # delivery instead of leaving it advisory. This is the bridge
                # between /optimize/suggestions and the live ad set.
                adset_payload["bid_strategy"] = "LOWEST_COST_WITH_BID_CAP"
                adset_payload["bid_amount"] = int(bid_amount_cents)

            adset = AdSet(parent_id=self.ad_account_id)
            adset.update(adset_payload)
            adset.remote_create()
            logger.info(
                "adset_created_with_ccco",
                adset_id=adset.get_id(),
                bid_strategy=adset_payload["bid_strategy"],
                bid_amount_applied=bid_amount_cents,
            )

            omnichannel_link_spec: dict = {
                "web": {"url": web_url},
                "app": {
                    "application_id": application_id,
                    "platform_specs": {},
                },
            }
            if android_deeplink:
                omnichannel_link_spec["app"]["platform_specs"]["android"] = {"url": android_deeplink}
            if ios_deeplink:
                omnichannel_link_spec["app"]["platform_specs"]["ios"] = {"url": ios_deeplink}

            creative = AdCreative(parent_id=self.ad_account_id)
            creative.update(
                {
                    "name": f"{name} Creative",
                    "applink_treatment": "deeplink_with_web_fallback",
                    "object_story_spec": {
                        "page_id": page_id,
                        "link_data": {
                            "call_to_action": {"type": "LEARN_MORE"},
                            "link": web_url,
                            "message": message,
                        },
                    },
                    "omnichannel_link_spec": omnichannel_link_spec,
                }
            )
            creative.remote_create()
            logger.info("creative_created_with_omnichannel_link_spec", creative_id=creative.get_id())

            ad = Ad(parent_id=self.ad_account_id)
            ad.update(
                {
                    "name": f"{name} Ad",
                    "adset_id": adset.get_id(),
                    "creative": {"creative_id": creative.get_id()},
                    "status": "PAUSED",
                    "tracking_specs": validate_tracking_specs(pixel_id, application_id, event),
                }
            )
            ad.remote_create()
            logger.info("full_ccco_ad_created", adset_id=adset.get_id(), ad_id=ad.get_id())

            save_ccco_campaign(
                adset_id=adset.get_id(),
                name=name,
                event=event.value,
                pixel_id=pixel_id,
                application_id=application_id,
                web_url=web_url,
                status="PAUSED",
                session_id=session_id,
                ad_account_id=self.ad_account_id,
                android_deeplink=android_deeplink,
                ios_deeplink=ios_deeplink,
                daily_budget=daily_budget,
            )

            return {
                "adset_id": adset.get_id(),
                "creative_id": creative.get_id(),
                "ad_id": ad.get_id(),
            }
        except ModuleNotFoundError as exc:
            logger.error("campaign_creation_failed", error=str(exc))
            raise RuntimeError(
                "facebook-business is required for Meta API calls. Install requirements.txt before creating campaigns."
            ) from exc
        except Exception as e:
            logger.error("campaign_creation_failed", error=str(e))
            raise
