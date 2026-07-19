from typing import Any, Literal

from pydantic import AnyUrl, BaseModel, Field

from app.models.omnichannel import SupportedEvent
from app.utils.logging import structlog

logger = structlog.get_logger()


class OptimizeRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    event: SupportedEvent
    omnichannel: dict[str, Any]
    daily_budget: int = Field(..., ge=100)
    web_url: AnyUrl
    android_deeplink: str | None = None
    ios_deeplink: str | None = None


class ChannelRecommendation(BaseModel):
    channel: Literal["web", "app", "balanced"]
    weight_percent: int
    reason: str
    expected_cpa_lift: float


class OptimizerSuggestion(BaseModel):
    recommendations: list[ChannelRecommendation]
    suggested_bid_cap: int | None
    predicted_cpa: float
    creative_tip: str
    deep_link_routing_rule: str


class AIOptimizer:
    @staticmethod
    def get_suggestions(req: OptimizeRequest) -> OptimizerSuggestion:
        has_app_deeplinks = bool(req.android_deeplink or req.ios_deeplink)

        if has_app_deeplinks and req.event in {SupportedEvent.PURCHASE, SupportedEvent.ADD_TO_CART}:
            recommendations = [
                ChannelRecommendation(
                    channel="app",
                    weight_percent=65,
                    reason="App deeplinks are available for a high-intent commerce event.",
                    expected_cpa_lift=18.0,
                ),
                ChannelRecommendation(
                    channel="web",
                    weight_percent=35,
                    reason="Web fallback keeps acquisition open for users without the app installed.",
                    expected_cpa_lift=8.0,
                ),
            ]
            predicted_cpa = 12.4
            bid_cap = int(req.daily_budget * 0.012)
        else:
            recommendations = [
                ChannelRecommendation(
                    channel="balanced",
                    weight_percent=100,
                    reason="No strong channel signal yet; keep delivery balanced while collecting conversion data.",
                    expected_cpa_lift=5.0,
                )
            ]
            predicted_cpa = 18.7
            bid_cap = None

        logger.info("optimizer_suggestions_generated", name=req.name, conversion_event=req.event.value)
        return OptimizerSuggestion(
            recommendations=recommendations,
            suggested_bid_cap=bid_cap,
            predicted_cpa=predicted_cpa,
            creative_tip="Use dynamic product deep links in Advantage+ catalog ads to reduce landing friction.",
            deep_link_routing_rule="deeplink_with_web_fallback",
        )
