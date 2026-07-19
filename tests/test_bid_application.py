"""Tier 1 forward-step: optimizer's suggested_bid_cap is actually applied.

When `bid_amount_cents` flows into campaign creation, the ad set must be
created with `bid_strategy='LOWEST_COST_WITH_BID_CAP'` and the supplied
`bid_amount`. When it is absent, the ad set must use the default
`LOWEST_COST_WITHOUT_CAP` strategy.

These tests prove the bridge from /optimize/suggestions to actual Meta
delivery, not just a JSON response field.
"""

import asyncio
import sys
import types
from typing import Any

import pytest


class _Recorder:
    """Records every payload passed to a stub Meta SDK object's update()."""

    def __init__(self):
        self.last_update: dict[str, Any] | None = None


def _install_fake_facebook_business(recorder: _Recorder) -> None:
    """Register a minimal facebook_business module tree in ``sys.modules``."""

    class _BaseObj:
        def __init__(self, parent_id=None, *args, **kwargs):
            self._fields: dict[str, Any] = {}

        def update(self, payload):
            # Ad and AdCreative stubs do not touch the recorder; only AdSet
            # below does. That keeps `recorder.last_update` pinned to the
            # AdSet payload we want to assert against.
            if isinstance(payload, dict):
                self._fields.update(payload)

        def remote_create(self):
            return self

        def get_id(self):
            return self._fields.get("name", "stub-id")

    fb_pkg = types.ModuleType("facebook_business")
    adobj_pkg = types.ModuleType("facebook_business.adobjects")

    ad_mod = types.ModuleType("facebook_business.adobjects.ad")

    class _Ad(_BaseObj):
        pass

    ad_mod.Ad = _Ad

    creative_mod = types.ModuleType("facebook_business.adobjects.adcreative")

    class _Creative(_BaseObj):
        pass

    creative_mod.AdCreative = _Creative

    adset_mod = types.ModuleType("facebook_business.adobjects.adset")

    class _AdSet(_BaseObj):
        # Only the AdSet update payload is the one we want to inspect.
        def update(self, payload):
            recorder.last_update = dict(payload) if isinstance(payload, dict) else {}
            self._fields.update(recorder.last_update)

    adset_mod.AdSet = _AdSet

    exc_mod = types.ModuleType("facebook_business.exceptions")

    class _FacebookRequestError(Exception):
        pass

    exc_mod.FacebookRequestError = _FacebookRequestError

    api_mod = types.ModuleType("facebook_business.api")

    class _FacebookAdsApi:
        @staticmethod
        def init(*args, **kwargs):
            return None

    api_mod.FacebookAdsApi = _FacebookAdsApi

    sys.modules["facebook_business"] = fb_pkg
    sys.modules["facebook_business.adobjects"] = adobj_pkg
    sys.modules["facebook_business.adobjects.ad"] = ad_mod
    sys.modules["facebook_business.adobjects.adcreative"] = creative_mod
    sys.modules["facebook_business.adobjects.adset"] = adset_mod
    sys.modules["facebook_business.exceptions"] = exc_mod
    sys.modules["facebook_business.api"] = api_mod


def _make_omnichannel_request_payload(bid_amount_cents=None):
    return {
        "session_id": "session-bid",
        "name": "Bid test campaign",
        "page_id": "page-1",
        "daily_budget": 5000,
        "event": "PURCHASE",
        "pixel_id": "px-1",
        "application_id": "app-1",
        "web_url": "https://bid.example.com/",
        "omnichannel": {
            "event": "PURCHASE",
            "app": [
                {
                    "application_id": "app-1",
                    "custom_event_type": "PURCHASE",
                    "object_store_urls": [
                        "https://play.google.com/store/apps/details?id=com.example",
                    ],
                }
            ],
            "pixel": [{"pixel_id": "px-1", "custom_event_type": "PURCHASE"}],
        },
        "bid_amount_cents": bid_amount_cents,
    }


def _run_create(payload):
    import importlib

    import app.database as database

    database = importlib.reload(database)
    database.init_db()

    from app.schemas.campaign import CampaignCreateRequest
    from app.services.campaign_service import CampaignService

    request = CampaignCreateRequest.model_validate(payload)
    service = CampaignService(access_token="tok", ad_account_id="act_bid")
    return asyncio.run(
        service.create_cross_channel_adset(
            name=request.name,
            daily_budget=request.daily_budget,
            event=request.event,
            omnichannel=request.omnichannel,
            pixel_id=request.pixel_id,
            application_id=request.application_id,
            page_id=request.page_id,
            web_url=str(request.web_url),
            message=request.message,
            countries=request.countries,
            android_deeplink=None,
            ios_deeplink=None,
            session_id=request.session_id,
            bid_amount_cents=request.bid_amount_cents,
        )
    )


def test_bid_amount_cents_applies_lowest_cost_with_bid_cap(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CCCO_DB_PATH", str(tmp_path / "campaigns.db"))
    recorder = _Recorder()
    _install_fake_facebook_business(recorder)

    try:
        _run_create(_make_omnichannel_request_payload(bid_amount_cents=6000))
    finally:
        for name in list(sys.modules):
            if name.startswith("facebook_business"):
                sys.modules.pop(name, None)

    assert recorder.last_update is not None
    # The last AdSet.update() before remote_create() is the one we care about.
    payload = recorder.last_update
    assert payload["bid_strategy"] == "LOWEST_COST_WITH_BID_CAP"
    assert payload["bid_amount"] == 6000


def test_missing_bid_amount_keeps_lowest_cost_without_cap(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CCCO_DB_PATH", str(tmp_path / "campaigns.db"))
    recorder = _Recorder()
    _install_fake_facebook_business(recorder)

    try:
        _run_create(_make_omnichannel_request_payload(bid_amount_cents=None))
    finally:
        for name in list(sys.modules):
            if name.startswith("facebook_business"):
                sys.modules.pop(name, None)

    assert recorder.last_update is not None
    payload = recorder.last_update
    assert payload["bid_strategy"] == "LOWEST_COST_WITHOUT_CAP"
    assert "bid_amount" not in payload
