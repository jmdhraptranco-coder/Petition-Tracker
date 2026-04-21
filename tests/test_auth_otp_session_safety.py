import importlib
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["SKIP_SCHEMA_UPDATES"] = "1"
app_module = importlib.import_module("app")


USER = {
    "id": 10,
    "username": "officer1",
    "full_name": "Test Officer",
    "role": "data_entry",
    "cvo_office": "apspdcl",
    "phone": "9876543210",
    "email": "officer@test.com",
    "profile_photo": None,
    "session_version": 1,
    "is_active": True,
    "must_change_password": False,
}


def _set_captcha(client, answer="482753"):
    client.get("/login")
    with client.session_transaction() as session_data:
        challenges = dict(session_data.get("login_captcha_challenges") or {})
        token = next(reversed(challenges))
        challenge = dict(challenges[token])
        challenge["answer_digest"] = app_module._login_captcha_answer_digest(token, answer)
        challenge["image_b64"] = app_module.base64.b64encode(
            app_module._build_login_captcha_bmp(answer)
        ).decode("ascii")
        challenges[token] = challenge
        session_data["login_captcha_challenges"] = challenges
    return {"captcha_answer": answer, "captcha_token": token}


def _stub_models():
    from types import SimpleNamespace

    stub = SimpleNamespace()
    stub.authenticate_user = lambda u, p: USER if u == USER["username"] else None
    stub.get_user_by_username = lambda u: USER if u == USER["username"] else None
    stub.get_user_by_id = lambda uid: {**USER, "id": uid}
    stub.update_password_only = lambda uid, pwd: None
    stub.update_password_and_phone = lambda uid, pwd, phone: None
    stub.get_dashboard_stats = lambda *a, **k: {}
    stub.get_petitions_for_user = lambda *a, **k: []
    stub.get_recent_petitions = lambda *a, **k: []
    stub._get_workflow_stage_stats = lambda *a, **k: {}
    stub._get_sla_stats_for_petitions = lambda *a, **k: {}
    stub._build_role_kpi_cards = lambda *a, **k: []
    return stub


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "models", _stub_models())
    app_module.app.config["TESTING"] = True
    app_module.TEST_SERVER_SESSION_STORE.clear()
    with app_module.app.test_client() as client:
        yield client


def test_login_rotates_session_after_successful_auth(client, monkeypatch):
    import auth_routes as auth_routes_mod
    monkeypatch.setattr(auth_routes_mod, "_otp_api_call",
                        lambda url, payload: {"status": "success"})
    client.get("/login")
    with client.session_transaction() as sess:
        sid_before = sess.sid

    # Step 1: credentials → OTP verify redirect
    response = client.post(
        "/login",
        data={
            "username": USER["username"],
            "password": "Pass@1234",
            "login_action": "credentials",
            **_set_captcha(client),
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/auth/otp/verify" in response.headers["Location"]

    # Step 2: OTP verify → dashboard redirect
    response = client.post("/auth/otp/verify", data={"otp_code": "123456"})
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]
    with client.session_transaction() as sess:
        assert sess.sid != sid_before
        assert sess.get("user_id") == USER["id"]


def test_password_reset_does_not_create_login_session(client):
    with client.session_transaction() as sess:
        sid_before = sess.sid

    response = client.get("/auth/forgot-password/set")

    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert "user_id" not in sess
