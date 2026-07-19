from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
try:
    from facebook_business.exceptions import FacebookRequestError
except ModuleNotFoundError:
    class FacebookRequestError(Exception):
        def api_error_code(self) -> str | None:
            return None

        def api_error_subcode(self) -> str | None:
            return None

        def api_error_type(self) -> str:
            return "missing_facebook_business_sdk"

        def api_error_message(self) -> str:
            return str(self)

from app.utils.logging import structlog

logger = structlog.get_logger()


class MetaApiError(RuntimeError):
    """Raised when Meta Graph API operations fail."""

    def __init__(self, message: str, *, code: str | None = None, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(MetaApiError)
    async def meta_api_error_handler(_: Request, exc: MetaApiError) -> JSONResponse:
        logger.warning("meta_api_error", code=exc.code, details=exc.details)
        return JSONResponse(
            status_code=502,
            content={"error": "meta_api_error", "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(FacebookRequestError)
    async def facebook_request_error_handler(_: Request, exc: FacebookRequestError) -> JSONResponse:
        details = {
            "api_error_code": exc.api_error_code(),
            "api_error_subcode": exc.api_error_subcode(),
            "api_error_type": exc.api_error_type(),
            "api_error_message": exc.api_error_message(),
        }
        logger.warning("facebook_request_error", **details)
        return JSONResponse(
            status_code=502,
            content={"error": "facebook_request_error", "message": exc.api_error_message(), "details": details},
        )
