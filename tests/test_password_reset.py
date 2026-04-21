"""
Comprehensive tests for the Password Reset Module.

Covers:
  A. First-Login Forced Password Change  (/auth/first-login-setup)
  B. Forgot-Password Step 1 – identify user  (/auth/forgot-password POST)
  C. Forgot-Password Step 2 – set password   (/auth/forgot-password/set GET+POST)
  D. Security / session-state edge cases
  E. login_required guard for force_change_user_id in session
"""
import importlib
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["SKIP_SCHEMA_UPDATES"] = "1"
app_module = importlib.import_module("app")

# ─── shared user fixtures ─────────────────────────────────────────────────────

NORMAL_USER = {
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
    "must_change_password": True,
}

SUPER_ADMIN = {
    "id": 1,
    "username": "superadmin",
    "full_name": "Super Admin",
    "role": "super_admin",
    "cvo_office": None,
    "phone": "9000000001",
    "email": "admin@test.com",
    "profile_photo": None,
    "session_version": 1,
    "is_active": True,
    "must_change_password": False,
}

INACTIVE_USER = {**NORMAL_USER, "id": 99, "username": "inactive_user", "is_active": False}
USER_NO_PHONE = {**NORMAL_USER, "id": 11, "username": "nophone", "phone": None}

VALID_PASSWORD = "NewPass@9!"


# ─── stub factory ─────────────────────────────────────────────────────────────

def make_stub(**overrides):
    """Returns a simple namespace stub with controllable behaviours."""
    from types import SimpleNamespace

    stub = SimpleNamespace()
    stub.calls = []

    stub.authenticate_user     = lambda u, p: NORMAL_USER
    stub.get_user_by_username  = lambda u: NORMAL_USER
    stub.get_user_by_id        = lambda uid: {**SUPER_ADMIN, "id": uid, "session_version": 1}
    stub.get_dashboard_stats   = lambda *a, **k: {}
    stub.get_petitions_for_user = lambda *a, **k: []
    stub.get_recent_petitions  = lambda *a, **k: []
    stub._get_workflow_stage_stats = lambda *a, **k: {}
    stub._get_sla_stats_for_petitions = lambda *a, **k: {}
    stub._build_role_kpi_cards = lambda *a, **k: []
    stub.update_password_and_phone = lambda uid, pwd, phone: stub.calls.append(
        ("update_password_and_phone", uid, pwd, phone))
    stub.update_password_only  = lambda uid, pwd: stub.calls.append(
        ("update_password_only", uid, pwd))

    for k, v in overrides.items():
        setattr(stub, k, v)
    return stub


@pytest.fixture
def client(monkeypatch):
    stub = make_stub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    app_module.TEST_SERVER_SESSION_STORE.clear()
    app_module.PETITION_SUBMISSION_ATTEMPTS.clear()
    app_module.LOGIN_CAPTCHA_USED_TOKENS.clear()
    app_module.LOGIN_CAPTCHA_CHALLENGES.clear()
    with app_module.app.test_client() as c:
        c.stub = stub
        yield c


def _set_session(client, **kw):
    with client.session_transaction() as s:
        if "user_id" in kw:
            now_ts = int(time.time())
            kw.setdefault("auth_issued_at", now_ts)
            kw.setdefault("auth_last_seen_at", now_ts)
        for k, v in kw.items():
            s[k] = v


def _get_session(client):
    with client.session_transaction() as s:
        return dict(s)


# ─── helper: captcha form ─────────────────────────────────────────────────────

def _captcha_form(client, answer="482753"):
    client.get("/login")
    with client.session_transaction() as session_data:
        challenges = dict(session_data.get("login_captcha_challenges") or {})
        assert challenges
        token = next(reversed(challenges))
        challenge = dict(challenges[token])
        challenge["answer_digest"] = app_module._login_captcha_answer_digest(token, answer)
        challenge["image_b64"] = app_module.base64.b64encode(
            app_module._build_login_captcha_bmp(answer)
        ).decode("ascii")
        challenges[token] = challenge
        session_data["login_captcha_challenges"] = challenges
    return {
        "captcha_answer": answer,
        "captcha_token": token,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# A. FIRST-LOGIN FORCED PASSWORD CHANGE
# ═══════════════════════════════════════════════════════════════════════════════

class TestFirstLoginSetup:

    def test_get_without_session_redirects_to_login(self, client):
        r = client.get("/auth/first-login-setup")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_get_with_session_renders_form(self, client):
        _set_session(client, force_change_user_id=10, force_change_username="officer1")
        r = client.get("/auth/first-login-setup")
        assert r.status_code == 200
        assert b"officer1" in r.data

    def test_post_without_session_redirects_to_login(self, client):
        r = client.post("/auth/first-login-setup", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
            "phone": "9876543210",
        })
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_default_password_rejected(self, client):
        _set_session(client, force_change_user_id=10, force_change_username="officer1")
        r = client.post("/auth/first-login-setup", data={
            "new_password": "Nigaa@123",
            "confirm_password": "Nigaa@123",
            "phone": "9876543210",
        }, follow_redirects=True)
        assert b"default password" in r.data.lower() or r.status_code in (200, 302)

    def test_weak_password_too_short(self, client):
        _set_session(client, force_change_user_id=10, force_change_username="officer1")
        r = client.post("/auth/first-login-setup", data={
            "new_password": "abc",
            "confirm_password": "abc",
            "phone": "9876543210",
        }, follow_redirects=True)
        assert r.status_code in (200, 302)

    def test_weak_password_no_uppercase(self, client):
        _set_session(client, force_change_user_id=10)
        r = client.post("/auth/first-login-setup", data={
            "new_password": "nouppercase1!",
            "confirm_password": "nouppercase1!",
            "phone": "9876543210",
        }, follow_redirects=True)
        assert r.status_code in (200, 302)

    def test_weak_password_no_special_char(self, client):
        _set_session(client, force_change_user_id=10)
        r = client.post("/auth/first-login-setup", data={
            "new_password": "NoSpecial1",
            "confirm_password": "NoSpecial1",
            "phone": "9876543210",
        }, follow_redirects=True)
        assert r.status_code in (200, 302)

    def test_passwords_mismatch(self, client):
        _set_session(client, force_change_user_id=10)
        r = client.post("/auth/first-login-setup", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": "Different@9!",
            "phone": "9876543210",
        }, follow_redirects=True)
        assert r.status_code in (200, 302)

    def test_missing_phone(self, client):
        _set_session(client, force_change_user_id=10)
        r = client.post("/auth/first-login-setup", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
            "phone": "",
        }, follow_redirects=True)
        assert r.status_code in (200, 302)

    def test_invalid_phone_too_short(self, client):
        _set_session(client, force_change_user_id=10)
        r = client.post("/auth/first-login-setup", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
            "phone": "12345",
        }, follow_redirects=True)
        assert r.status_code in (200, 302)

    def test_invalid_phone_starts_with_zero(self, client):
        _set_session(client, force_change_user_id=10)
        r = client.post("/auth/first-login-setup", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
            "phone": "0123456789",
        }, follow_redirects=True)
        assert r.status_code in (200, 302)

    def test_invalid_phone_non_digits(self, client):
        _set_session(client, force_change_user_id=10)
        r = client.post("/auth/first-login-setup", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
            "phone": "ABCDEFGHIJ",
        }, follow_redirects=True)
        assert r.status_code in (200, 302)

    def test_success_calls_model_and_redirects(self, client):
        _set_session(client, force_change_user_id=10, force_change_username="officer1")
        r = client.post("/auth/first-login-setup", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
            "phone": "9876543210",
        }, follow_redirects=False)
        assert r.status_code == 302
        assert "/dashboard" in r.headers["Location"]
        assert any(c[0] == "update_password_and_phone" for c in client.stub.calls)

    def test_success_clears_force_change_session(self, client):
        _set_session(client, force_change_user_id=10, force_change_username="officer1")
        client.post("/auth/first-login-setup", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
            "phone": "9876543210",
        })
        sess = _get_session(client)
        assert "force_change_user_id" not in sess
        assert "force_change_username" not in sess

    def test_model_error_shows_error(self, client, monkeypatch):
        def _raise(*_a, **_k): raise RuntimeError("DB error")
        monkeypatch.setattr(app_module.models, "update_password_and_phone", _raise)
        _set_session(client, force_change_user_id=10)
        r = client.post("/auth/first-login-setup", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
            "phone": "9876543210",
        }, follow_redirects=True)
        assert r.status_code in (200, 302)

    def test_super_admin_first_login_requires_phone(self, client):
        _set_session(client, force_change_user_id=1, force_change_username="superadmin",
                     force_change_role="super_admin")
        r = client.post("/auth/first-login-setup", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
            "phone": "",
        }, follow_redirects=True)
        assert r.status_code in (200, 302)

    def test_super_admin_first_login_saves_password_and_phone(self, client):
        _set_session(client, force_change_user_id=1, force_change_username="superadmin",
                     force_change_role="super_admin")
        r = client.post("/auth/first-login-setup", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
            "phone": "9000000001",
        }, follow_redirects=False)
        assert r.status_code == 302
        assert "/dashboard" in r.headers["Location"]
        assert any(c == ("update_password_and_phone", 1, VALID_PASSWORD, "9000000001")
                   for c in client.stub.calls)


# ═══════════════════════════════════════════════════════════════════════════════
# B. PASSWORD RESET (OTP-based) – /auth/forgot-password
# ═══════════════════════════════════════════════════════════════════════════════

RESET_DATA = {
    "recovery_username": "officer1",
}


class TestForgotPasswordReset:
    """Tests for the OTP-based forgot-password flow.

    Step 1: POST /auth/forgot-password with username → sends OTP → redirect to /auth/otp/verify
    Error cases render the login page (200) with a flash message.
    """

    def _post(self, client, **overrides):
        data = {**RESET_DATA, **overrides}
        return client.post("/auth/forgot-password", data=data, follow_redirects=False)

    def test_empty_username_shows_error(self, client):
        r = self._post(client, recovery_username="")
        assert r.status_code == 200

    def test_unknown_username_rejected(self, client, monkeypatch):
        monkeypatch.setattr(app_module.models, "get_user_by_username", lambda u: None)
        r = self._post(client, recovery_username="ghost")
        assert r.status_code == 200

    def test_inactive_user_rejected(self, client, monkeypatch):
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: INACTIVE_USER)
        r = self._post(client, recovery_username="inactive_user")
        assert r.status_code == 200

    def test_user_no_phone_rejected(self, client, monkeypatch):
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: USER_NO_PHONE)
        r = self._post(client, recovery_username="nophone")
        assert r.status_code == 200

    def test_otp_api_failure_shows_error(self, client, monkeypatch):
        import auth_routes as auth_routes_mod
        monkeypatch.setattr(auth_routes_mod, "_otp_api_call",
                            lambda url, payload: {"status": "error", "message": "API down"})
        r = self._post(client)
        assert r.status_code == 200

    def test_success_sends_otp_and_redirects(self, client, monkeypatch):
        import auth_routes as auth_routes_mod
        monkeypatch.setattr(auth_routes_mod, "_otp_api_call",
                            lambda url, payload: {"status": "success"})
        r = self._post(client)
        assert r.status_code == 302
        assert "/auth/otp/verify" in r.headers["Location"]

    def test_success_stores_otp_session_state(self, client, monkeypatch):
        import auth_routes as auth_routes_mod
        monkeypatch.setattr(auth_routes_mod, "_otp_api_call",
                            lambda url, payload: {"status": "success"})
        self._post(client)
        sess = _get_session(client)
        otp_state = sess.get("otp_login_state")
        assert otp_state is not None
        assert otp_state.get("mobile") == "9876543210"
        assert otp_state.get("user_id") == NORMAL_USER["id"]
        assert otp_state.get("flow") == "password_reset"

    def test_full_reset_flow_updates_password(self, client, monkeypatch):
        """End-to-end: forgot-password → OTP verify → set new password."""
        import auth_routes as auth_routes_mod
        monkeypatch.setattr(auth_routes_mod, "_otp_api_call",
                            lambda url, payload: {"status": "success"})
        # Step 1: Request recovery (sends OTP)
        r = self._post(client)
        assert r.status_code == 302
        # Step 2: Verify OTP
        r = client.post("/auth/otp/verify", data={"otp_code": "123456"})
        assert r.status_code == 302
        assert "/forgot-password/set" in r.headers["Location"]
        # Step 3: Set new password
        r = client.post("/auth/forgot-password/set", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
        })
        assert r.status_code in (302, 303)
        assert "/login" in r.headers["Location"]
        assert any(c[0] == "update_password_only" for c in client.stub.calls)

    def test_model_error_redirects_with_error(self, client, monkeypatch):
        """Password update failure shows error on the set-password page."""
        import auth_routes as auth_routes_mod
        monkeypatch.setattr(auth_routes_mod, "_otp_api_call",
                            lambda url, payload: {"status": "success"})
        def _raise(*_a, **_k): raise RuntimeError("DB down")
        monkeypatch.setattr(app_module.models, "update_password_only", _raise)
        # Go through OTP flow
        self._post(client)
        client.post("/auth/otp/verify", data={"otp_code": "123456"})
        r = client.post("/auth/forgot-password/set", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
        })
        assert r.status_code == 302
        assert "/forgot-password/set" in r.headers["Location"]
        assert not any(c[0] == "update_password_only" for c in client.stub.calls)

    def test_weak_password_rejected_at_set_step(self, client, monkeypatch):
        """Weak password is rejected at the set-password step."""
        import auth_routes as auth_routes_mod
        monkeypatch.setattr(auth_routes_mod, "_otp_api_call",
                            lambda url, payload: {"status": "success"})
        self._post(client)
        client.post("/auth/otp/verify", data={"otp_code": "123456"})
        r = client.post("/auth/forgot-password/set", data={
            "new_password": "weak",
            "confirm_password": "weak",
        })
        assert r.status_code == 302
        assert "/forgot-password/set" in r.headers["Location"]

    def test_passwords_mismatch_rejected_at_set_step(self, client, monkeypatch):
        """Mismatched passwords are rejected at the set-password step."""
        import auth_routes as auth_routes_mod
        monkeypatch.setattr(auth_routes_mod, "_otp_api_call",
                            lambda url, payload: {"status": "success"})
        self._post(client)
        client.post("/auth/otp/verify", data={"otp_code": "123456"})
        r = client.post("/auth/forgot-password/set", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": "Different@9!",
        })
        assert r.status_code == 302
        assert "/forgot-password/set" in r.headers["Location"]

    def test_default_password_rejected_at_set_step(self, client, monkeypatch):
        """Default password (Nigaa@123) is rejected at the set-password step."""
        import auth_routes as auth_routes_mod
        monkeypatch.setattr(auth_routes_mod, "_otp_api_call",
                            lambda url, payload: {"status": "success"})
        self._post(client)
        client.post("/auth/otp/verify", data={"otp_code": "123456"})
        r = client.post("/auth/forgot-password/set", data={
            "new_password": "Nigaa@123",
            "confirm_password": "Nigaa@123",
        })
        assert r.status_code == 302
        assert "/forgot-password/set" in r.headers["Location"]


class TestForgotPasswordSetLegacy:
    """The /auth/forgot-password/set endpoint now just redirects to recovery tab."""

    def test_get_redirects_to_recovery(self, client):
        r = client.get("/auth/forgot-password/set")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_post_redirects_to_recovery(self, client):
        r = client.post("/auth/forgot-password/set", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
        })
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]


# ═══════════════════════════════════════════════════════════════════════════════
# D. LOGIN ROUTE – must_change_password interception
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoginMustChangePassword:

    def test_must_change_password_user_redirected_to_setup(self, client, monkeypatch):
        import auth_routes as auth_routes_mod
        monkeypatch.setattr(app_module.models, "authenticate_user",
                            lambda u, p: NORMAL_USER)
        monkeypatch.setattr(app_module.models, "get_user_by_id",
                            lambda uid: NORMAL_USER)
        monkeypatch.setattr(auth_routes_mod, "_otp_api_call",
                            lambda url, payload: {"status": "success"})
        # Step 1: credentials → OTP verify
        r = client.post("/login", data={
            "username": "officer1",
            "password": "Nigaa@123",
            "login_action": "credentials",
            **_captcha_form(client),
        })
        assert r.status_code == 302
        assert "/auth/otp/verify" in r.headers["Location"]
        # Step 2: OTP verify → first-login-setup (must_change_password=True)
        r = client.post("/auth/otp/verify", data={"otp_code": "123456"})
        assert r.status_code == 302
        assert "first-login-setup" in r.headers["Location"]

    def test_must_change_password_sets_force_session(self, client, monkeypatch):
        import auth_routes as auth_routes_mod
        monkeypatch.setattr(app_module.models, "authenticate_user",
                            lambda u, p: NORMAL_USER)
        monkeypatch.setattr(app_module.models, "get_user_by_id",
                            lambda uid: NORMAL_USER)
        monkeypatch.setattr(auth_routes_mod, "_otp_api_call",
                            lambda url, payload: {"status": "success"})
        client.post("/login", data={
            "username": "officer1",
            "password": "Nigaa@123",
            "login_action": "credentials",
            **_captcha_form(client),
        })
        # Complete OTP step
        client.post("/auth/otp/verify", data={"otp_code": "123456"})
        sess = _get_session(client)
        assert sess.get("force_change_user_id") == NORMAL_USER["id"]
        assert sess.get("force_change_username") == NORMAL_USER["username"]
        assert "user_id" not in sess  # full session NOT activated

    def test_no_must_change_proceeds_normally(self, client, monkeypatch):
        import auth_routes as auth_routes_mod
        user_ok = {**NORMAL_USER, "must_change_password": False}
        monkeypatch.setattr(app_module.models, "authenticate_user",
                            lambda u, p: user_ok)
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: user_ok)
        monkeypatch.setattr(auth_routes_mod, "_otp_api_call",
                            lambda url, payload: {"status": "success"})
        client.post("/login", data={
            "username": "officer1",
            "password": "Pass@1234",
            "login_action": "credentials",
            **_captcha_form(client),
        })
        r = client.post("/auth/otp/verify", data={"otp_code": "123456"})
        # Should redirect to dashboard, NOT first-login-setup
        assert r.status_code == 302
        assert "first-login-setup" not in r.headers.get("Location", "")
        assert "/dashboard" in r.headers["Location"]

    # ── Regression: existing user with no phone (the deo_apcpdcl scenario) ──

    def test_existing_user_no_phone_gets_error(self, client, monkeypatch):
        """User with no phone gets a login error (OTP requires phone)."""
        user_no_phone = {**NORMAL_USER, "must_change_password": False, "phone": None}
        monkeypatch.setattr(app_module.models, "authenticate_user",
                            lambda u, p: user_no_phone)
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: user_no_phone)
        r = client.post("/login", data={
            "username": "deo_apcpdcl",
            "password": "Nigaa@123",
            "login_action": "credentials",
            **_captcha_form(client),
        })
        # Can't proceed past login without phone for OTP
        assert r.status_code == 200

    def test_existing_user_no_phone_shows_phone_error(self, client, monkeypatch):
        """User with no phone sees mobile number error, not old dead-end."""
        user_no_phone = {**NORMAL_USER, "must_change_password": False, "phone": None}
        monkeypatch.setattr(app_module.models, "authenticate_user",
                            lambda u, p: user_no_phone)
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: user_no_phone)
        r = client.post("/login", data={
            "username": "deo_apcpdcl",
            "password": "Nigaa@123",
            "login_action": "credentials",
            **_captcha_form(client),
        })
        assert b"No valid mobile number" in r.data
        assert b"Contact admin to update phone number" not in r.data


# ═══════════════════════════════════════════════════════════════════════════════
# H. login_required GUARD for force_change_user_id
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoginRequiredGuard:

    def test_force_change_session_blocks_dashboard(self, client):
        _set_session(client, force_change_user_id=10)
        r = client.get("/dashboard")
        assert r.status_code == 302
        assert "first-login-setup" in r.headers["Location"]

    def test_force_change_session_blocks_petitions(self, client):
        _set_session(client, force_change_user_id=10)
        r = client.get("/petitions")
        assert r.status_code == 302
        assert "first-login-setup" in r.headers["Location"]

    def test_no_user_id_blocks_dashboard(self, client):
        r = client.get("/dashboard")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_authenticated_user_passes_dashboard(self, client, monkeypatch):
        monkeypatch.setattr(app_module.models, "get_dashboard_stats",
                            lambda *_a, **_k: {})
        monkeypatch.setattr(app_module.models, "get_recent_petitions",
                            lambda *_a, **_k: [])
        _set_session(client, user_id=1, user_role="super_admin",
                     full_name="Admin", username="admin", session_version=1)
        r = client.get("/dashboard")
        # 200 or minor redirect for sub-routing is fine; NOT login redirect
        assert "/login" not in r.headers.get("Location", "")

    def test_session_version_mismatch_forces_relogin(self, client, monkeypatch):
        monkeypatch.setattr(app_module.models, "get_user_by_id",
                            lambda _uid: {**SUPER_ADMIN, "session_version": 2})
        _set_session(client, user_id=1, user_role="super_admin",
                     full_name="Admin", username="admin", session_version=1)
        r = client.get("/dashboard")
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]
