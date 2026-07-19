from pydantic import AnyUrl, BaseModel, Field, HttpUrl, model_validator

from app.models.omnichannel import OmnichannelObject, SupportedEvent


class CampaignCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    session_id: str = Field(..., min_length=1)
    page_id: str = Field(..., min_length=1)
    daily_budget: int = Field(..., ge=100)
    event: SupportedEvent
    omnichannel: OmnichannelObject
    pixel_id: str = Field(..., min_length=1)
    application_id: str = Field(..., min_length=1)
    web_url: HttpUrl
    message: str = Field("Shop now on web or app!", min_length=1, max_length=500)
    countries: list[str] = Field(default_factory=lambda: ["US"], min_length=1)
    android_deeplink: AnyUrl | None = None
    ios_deeplink: AnyUrl | None = None
    bid_amount_cents: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Optional per-result bid cap in account-currency minor units (cents). "
            "When provided, the ad set is created with bid_strategy="
            "'LOWEST_COST_WITH_BID_CAP' and bid_amount=this value, applying the "
            "optimizer's suggested_bid_cap to actual Meta delivery instead of "
            "leaving it advisory."
        ),
    )

    @model_validator(mode="after")
    def validate_event_and_ids(self) -> "CampaignCreateRequest":
        if self.omnichannel.event != self.event:
            raise ValueError("event must match omnichannel custom_event_type")

        app_ids = {item.application_id for item in self.omnichannel.app}
        pixel_ids = {item.pixel_id for item in self.omnichannel.pixel}
        if self.application_id not in app_ids:
            raise ValueError("application_id must be present in omnichannel.app")
        if self.pixel_id not in pixel_ids:
            raise ValueError("pixel_id must be present in omnichannel.pixel")
        return self


class CampaignCreateResponse(BaseModel):
    adset_id: str
    creative_id: str
    ad_id: str


class CampaignRecord(BaseModel):
    id: int
    adset_id: str
    name: str
    event: str
    pixel_id: str
    application_id: str
    web_url: str | None = None
    created_at: str
    status: str


class HealthResponse(BaseModel):
    status: str = "ok"
    database: str = "connected"
    version: str = "0.1.0"
