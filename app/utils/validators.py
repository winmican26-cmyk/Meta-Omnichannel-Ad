from app.models.omnichannel import SupportedEvent


def validate_tracking_specs(
    pixel_id: str,
    application_id: str,
    event: SupportedEvent,
) -> list[dict]:
    if not pixel_id:
        raise ValueError("pixel_id is required for tracking_specs")
    if not application_id:
        raise ValueError("application_id is required for tracking_specs")

    return [
        {"action.type": ["offsite_conversion"], "fb_pixel": [pixel_id]},
        {
            "action.type": ["app_custom_event"],
            "application": [application_id],
            "custom_event_type": [event.value],
        },
        {"action.type": ["mobile_app_install"], "application": [application_id]},
    ]
