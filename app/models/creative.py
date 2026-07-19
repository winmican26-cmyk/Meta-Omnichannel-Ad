from enum import Enum

from pydantic import BaseModel, Field, HttpUrl

from app.models.omnichannel import OmnichannelLinkSpec


class CallToActionType(str, Enum):
    APPLY_NOW = "APPLY_NOW"
    BOOK_TRAVEL = "BOOK_TRAVEL"
    CONTACT_US = "CONTACT_US"
    DOWNLOAD = "DOWNLOAD"
    GET_OFFER = "GET_OFFER"
    GET_QUOTE = "GET_QUOTE"
    LEARN_MORE = "LEARN_MORE"
    SHOP_NOW = "SHOP_NOW"
    SIGN_UP = "SIGN_UP"
    SUBSCRIBE = "SUBSCRIBE"


class LinkData(BaseModel):
    link: HttpUrl
    message: str = Field(..., min_length=1, max_length=500)
    call_to_action: dict[str, CallToActionType]


class ObjectStorySpec(BaseModel):
    page_id: str = Field(..., min_length=1)
    link_data: LinkData


class CreativeSpec(BaseModel):
    name: str = Field(..., min_length=1)
    applink_treatment: str = "deeplink_with_web_fallback"
    object_story_spec: ObjectStorySpec
    omnichannel_link_spec: OmnichannelLinkSpec
