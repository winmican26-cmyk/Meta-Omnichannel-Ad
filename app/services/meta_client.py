import os

from app.utils.logging import structlog

logger = structlog.get_logger()

META_API_VERSION = "v25.0"


class MetaClient:
    def __init__(
        self,
        access_token: str | None = None,
        *,
        app_id: str | None = None,
        app_secret: str | None = None,
    ):
        self.access_token = access_token or os.getenv("META_ACCESS_TOKEN")
        self.app_id = app_id or os.getenv("META_APP_ID")
        self.app_secret = app_secret or os.getenv("META_APP_SECRET")

        if not self.access_token:
            raise ValueError("Meta access token is required")

        try:
            from facebook_business.api import FacebookAdsApi
            from facebook_business.exceptions import FacebookRequestError
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "facebook-business is required for Meta API calls. Install requirements.txt before creating campaigns."
            ) from exc

        try:
            FacebookAdsApi.init(
                app_id=self.app_id,
                app_secret=self.app_secret,
                access_token=self.access_token,
                api_version=META_API_VERSION,
            )
        except FacebookRequestError:
            logger.warning("meta_sdk_initialization_failed", api_version=META_API_VERSION)
            raise

        logger.info("meta_sdk_initialized", api_version=META_API_VERSION)

    def get_api(self):
        from facebook_business.api import FacebookAdsApi

        return FacebookAdsApi.get_default_api()
