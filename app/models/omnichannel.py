from enum import Enum
from typing import Any, Literal

from pydantic import AnyUrl, BaseModel, Field, HttpUrl, field_validator, model_validator


class SupportedEvent(str, Enum):
    PURCHASE = "PURCHASE"
    COMPLETE_REGISTRATION = "COMPLETE_REGISTRATION"
    ADD_PAYMENT_INFO = "ADD_PAYMENT_INFO"
    ADD_TO_CART = "ADD_TO_CART"
    INITIATED_CHECKOUT = "INITIATED_CHECKOUT"
    SEARCH = "SEARCH"
    CONTENT_VIEW = "CONTENT_VIEW"
    LEAD = "LEAD"
    ADD_TO_WISHLIST = "ADD_TO_WISHLIST"
    SUBSCRIBE = "SUBSCRIBE"
    START_TRIAL = "START_TRIAL"


class PixelRule(BaseModel):
    event: dict[str, Any] | None = None
    url: dict[str, Any] | None = None


class AppPromotedObject(BaseModel):
    application_id: str = Field(..., min_length=1)
    custom_event_type: SupportedEvent
    object_store_urls: list[HttpUrl] = Field(..., min_length=1)

    @field_validator("object_store_urls")
    @classmethod
    def validate_store_urls(cls, value: list[HttpUrl]) -> list[HttpUrl]:
        allowed_hosts = {"play.google.com", "apps.apple.com", "itunes.apple.com"}
        for url in value:
            if url.host not in allowed_hosts:
                raise ValueError("object_store_urls must be Play Store or App Store URLs")
        return value


class PixelPromotedObject(BaseModel):
    pixel_id: str = Field(..., min_length=1)
    custom_event_type: SupportedEvent
    pixel_rule: PixelRule | dict[str, Any] | None = None


class OmnichannelObject(BaseModel):
    app: list[AppPromotedObject] = Field(..., min_length=1)
    pixel: list[PixelPromotedObject] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_same_event_across_channels(self) -> "OmnichannelObject":
        events = {item.custom_event_type for item in [*self.app, *self.pixel]}
        if len(events) > 1:
            raise ValueError("All app and pixel objects must use the same custom_event_type")
        return self

    @property
    def event(self) -> SupportedEvent:
        return self.app[0].custom_event_type


class Platform(str, Enum):
    ANDROID = "android"
    IOS = "ios"


class AppPlatformSpec(BaseModel):
    url: AnyUrl


class OmnichannelLinkAppSpec(BaseModel):
    application_id: str = Field(..., min_length=1)
    platform_specs: dict[Literal["android", "ios"], AppPlatformSpec] = Field(default_factory=dict)


class OmnichannelLinkSpec(BaseModel):
    web: dict[Literal["url"], AnyUrl]
    app: OmnichannelLinkAppSpec
