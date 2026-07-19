import importlib


def test_init_save_and_list_owned_campaigns(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "campaigns.db"
    monkeypatch.setenv("CCCO_DB_PATH", str(db_path))

    import app.database as database

    database = importlib.reload(database)
    database.init_db()
    database.save_ccco_campaign(
        adset_id="238500000000001",
        name="Spring Promo",
        event="PURCHASE",
        pixel_id="456",
        application_id="123",
        web_url="https://example.com/products",
        session_id="session-x",
        ad_account_id="act_x",
    )

    rows = database.list_owned_ccco_campaigns(session_id="session-x", ad_account_id="act_x")
    assert len(rows) == 1
    assert rows[0]["adset_id"] == "238500000000001"
    assert rows[0]["status"] == "PAUSED"

    # A different session must not see this campaign.
    other = database.list_owned_ccco_campaigns(session_id="session-y", ad_account_id="act_y")
    assert other == []


def test_session_persistence_helpers(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "campaigns.db"
    monkeypatch.setenv("CCCO_DB_PATH", str(db_path))

    import app.database as database

    database = importlib.reload(database)
    database.init_db()
    database.save_session(
        session_id="session-123",
        access_token="long-lived-token",
        ad_account_id="act_1",
        ad_accounts=[{"id": "act_1", "name": "One"}, {"id": "act_2", "name": "Two"}],
        user_id="user-1",
        user_name="Meta User",
    )
    database.update_session_ad_account("session-123", "act_2")

    session = database.get_session_record("session-123")
    assert session is not None
    assert session["access_token"] == "long-lived-token"
    assert session["ad_account_id"] == "act_2"
    assert session["ad_accounts"][1]["name"] == "Two"
