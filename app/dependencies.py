from fastapi import HTTPException

from app.auth import get_session
from app.billing import PAID_TIERS
from app.creative_studio import CreativeGenerateRequest
from app.database import get_db, init_db
from app.schemas.campaign import CampaignCreateRequest


def require_pro_subscription(session_id: str) -> dict:
    session = get_session(session_id)
    if session.get("subscription_tier", "free") not in PAID_TIERS:
        raise HTTPException(status_code=402, detail="Pro subscription required for this action")
    return session


def require_campaign_subscription(request: CampaignCreateRequest) -> dict | None:
    return require_pro_subscription(request.session_id)


def require_creative_subscription(request: CreativeGenerateRequest) -> dict:
    return require_pro_subscription(request.session_id)


def require_adset_owner(session_id: str, adset_id: str) -> dict:
    """Verify the calling session owns ``adset_id``.

    Returns the campaign row when ownership is confirmed. Raises 404 in every
    failure mode (missing adset, mismatched session, mismatched ad account) so
    the API never reveals whether an adset exists in another tenant.
    """
    if not session_id or not adset_id:
        raise HTTPException(status_code=404, detail="Ad set not found")
    session = get_session(session_id)
    ad_account_id = session.get("ad_account_id")
    init_db()
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT * FROM ccco_campaigns
            WHERE adset_id = :adset
              AND session_id IS :sid
              AND ad_account_id IS :acc
            """,
            {"adset": adset_id, "sid": session_id, "acc": ad_account_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Ad set not found")
    return dict(row)
