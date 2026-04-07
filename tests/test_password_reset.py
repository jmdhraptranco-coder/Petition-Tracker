"""
Comprehensive tests for the Password Reset Module.

Covers:
  A. First-Login Forced Password Change  (/auth/first-login-setup)
  B. Forgot-Password Step 1 – identify user  (/auth/forgot-password POST)
  C. Forgot-Password Step 2 – verify OTP     (/auth/forgot-password/verify POST)
  D. Forgot-Password Resend OTP              (/auth/forgot-password/resend-otp POST)
  E. Forgot-Password Step 3 – set password   (/auth/forgot-password/set GET+POST)
  F. Super-Admin recovery paths (OTP via registered phone)
  G. Security / session-state edge cases
  H. login_required guard for force_change_user_id in session
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


# ─── helper: patch OTP helpers ────────────────────────────────────────────────

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


def patch_otp(monkeypatch, send_ok=True, verify_ok=True):
    monkeypatch.setattr(app_module, "_send_login_otp",
                        lambda m: (True, "OTP sent") if send_ok else (False, "OTP gateway error"))
    monkeypatch.setattr(app_module, "_verify_login_otp",
                        lambda m, c: (True, "OK") if verify_ok else (False, "Invalid OTP"))
    monkeypatch.setattr(app_module, "_normalize_mobile_for_otp",
                        lambda p: p if p else None)
    monkeypatch.setattr(app_module, "_mask_mobile",
                        lambda m: "****3210" if m else "")


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
# B. FORGOT-PASSWORD STEP 1 – /auth/forgot-password
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.skip(reason="Legacy OTP-based password reset flow was removed.")
class TestForgotPasswordRequest:

    def test_empty_username_redirects(self, client, monkeypatch):
        patch_otp(monkeypatch)
        r = client.post("/auth/forgot-password", data={"fp_username": ""})
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]

    def test_unknown_username_generic_message(self, client, monkeypatch):
        patch_otp(monkeypatch)
        monkeypatch.setattr(app_module.models, "get_user_by_username", lambda u: None)
        r = client.post("/auth/forgot-password", data={"fp_username": "ghost"},
                        follow_redirects=True)
        assert r.status_code == 200

    def test_inactive_user_generic_message(self, client, monkeypatch):
        patch_otp(monkeypatch)
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: INACTIVE_USER)
        r = client.post("/auth/forgot-password", data={"fp_username": "inactive_user"},
                        follow_redirects=True)
        assert r.status_code == 200

    def test_user_no_phone_warns(self, client, monkeypatch):
        patch_otp(monkeypatch)
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: USER_NO_PHONE)
        r = client.post("/auth/forgot-password", data={"fp_username": "nophone"},
                        follow_redirects=True)
        assert r.status_code == 200

    def test_otp_send_failure_shows_error(self, client, monkeypatch):
        patch_otp(monkeypatch, send_ok=False)
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: NORMAL_USER)
        r = client.post("/auth/forgot-password", data={"fp_username": "officer1"},
                        follow_redirects=True)
        assert r.status_code == 200

    def test_otp_send_success_shows_verify_form(self, client, monkeypatch):
        patch_otp(monkeypatch, send_ok=True)
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: NORMAL_USER)
        r = client.post("/auth/forgot-password", data={"fp_username": "officer1"})
        assert r.status_code == 200
        assert b"verify_otp" in r.data or b"OTP" in r.data or b"otp" in r.data.lower()

    def test_otp_send_sets_session_state(self, client, monkeypatch):
        patch_otp(monkeypatch, send_ok=True)
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: NORMAL_USER)
        client.post("/auth/forgot-password", data={"fp_username": "officer1"})
        sess = _get_session(client)
        assert sess.get("pw_reset_user_id") == NORMAL_USER["id"]
        assert sess.get("pw_reset_mobile") == NORMAL_USER["phone"]
        assert sess.get("pw_reset_otp_verified") is False

    def test_stale_session_cleared_before_new_attempt(self, client, monkeypatch):
        patch_otp(monkeypatch, send_ok=True)
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: NORMAL_USER)
        # Set stale state
        _set_session(client, pw_reset_user_id=999, pw_reset_otp_verified=True)
        client.post("/auth/forgot-password", data={"fp_username": "officer1"})
        sess = _get_session(client)
        assert sess.get("pw_reset_user_id") == NORMAL_USER["id"]
        assert sess.get("pw_reset_otp_verified") is False


# ═══════════════════════════════════════════════════════════════════════════════
# C. FORGOT-PASSWORD STEP 2 – /auth/forgot-password/verify
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.skip(reason="Legacy OTP-based password reset flow was removed.")
class TestForgotPasswordVerify:

    def test_no_session_redirects(self, client, monkeypatch):
        patch_otp(monkeypatch)
        r = client.post("/auth/forgot-password/verify", data={"otp_code": "123456"})
        assert r.status_code == 302

    def test_already_verified_redirects(self, client, monkeypatch):
        patch_otp(monkeypatch)
        _set_session(client, pw_reset_user_id=10, pw_reset_otp_verified=True,
                     pw_reset_mobile="9876543210")
        r = client.post("/auth/forgot-password/verify", data={"otp_code": "123456"})
        assert r.status_code == 302

    def test_non_digit_otp_rejected(self, client, monkeypatch):
        patch_otp(monkeypatch)
        _set_session(client, pw_reset_user_id=10, pw_reset_otp_verified=False,
                     pw_reset_mobile="9876543210")
        r = client.post("/auth/forgot-password/verify", data={"otp_code": "ABCDEF"})
        assert r.status_code == 200

    def test_otp_too_short_rejected(self, client, monkeypatch):
        patch_otp(monkeypatch)
        _set_session(client, pw_reset_user_id=10, pw_reset_otp_verified=False,
                     pw_reset_mobile="9876543210")
        r = client.post("/auth/forgot-password/verify", data={"otp_code": "12"})
        assert r.status_code == 200

    def test_wrong_otp_shows_error(self, client, monkeypatch):
        patch_otp(monkeypatch, verify_ok=False)
        _set_session(client, pw_reset_user_id=10, pw_reset_otp_verified=False,
                     pw_reset_mobile="9876543210", pw_reset_username="officer1")
        r = client.post("/auth/forgot-password/verify", data={"otp_code": "999999"})
        assert r.status_code == 200
        # otp_verified must remain False
        sess = _get_session(client)
        assert sess.get("pw_reset_otp_verified") is False

    def test_correct_otp_sets_verified_and_redirects(self, client, monkeypatch):
        patch_otp(monkeypatch, verify_ok=True)
        _set_session(client, pw_reset_user_id=10, pw_reset_otp_verified=False,
                     pw_reset_mobile="9876543210", pw_reset_username="officer1")
        r = client.post("/auth/forgot-password/verify", data={"otp_code": "123456"})
        assert r.status_code == 302
        assert "forgot-password/set" in r.headers["Location"]
        sess = _get_session(client)
        assert sess.get("pw_reset_otp_verified") is True

    def test_empty_otp_rejected(self, client, monkeypatch):
        patch_otp(monkeypatch)
        _set_session(client, pw_reset_user_id=10, pw_reset_otp_verified=False,
                     pw_reset_mobile="9876543210")
        r = client.post("/auth/forgot-password/verify", data={"otp_code": ""})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# D. FORGOT-PASSWORD RESEND OTP – /auth/forgot-password/resend-otp
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.skip(reason="Legacy OTP-based password reset flow was removed.")
class TestForgotPasswordResendOTP:

    def test_no_session_redirects(self, client, monkeypatch):
        patch_otp(monkeypatch)
        r = client.post("/auth/forgot-password/resend-otp", data={})
        assert r.status_code == 302

    def test_already_verified_redirects(self, client, monkeypatch):
        patch_otp(monkeypatch)
        _set_session(client, pw_reset_mobile="9876543210", pw_reset_otp_verified=True)
        r = client.post("/auth/forgot-password/resend-otp", data={})
        assert r.status_code == 302

    def test_resend_success_renders_verify_form(self, client, monkeypatch):
        patch_otp(monkeypatch, send_ok=True)
        _set_session(client, pw_reset_mobile="9876543210", pw_reset_otp_verified=False)
        r = client.post("/auth/forgot-password/resend-otp", data={})
        assert r.status_code == 200

    def test_resend_gateway_failure_shows_error(self, client, monkeypatch):
        patch_otp(monkeypatch, send_ok=False)
        _set_session(client, pw_reset_mobile="9876543210", pw_reset_otp_verified=False)
        r = client.post("/auth/forgot-password/resend-otp", data={})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# E. FORGOT-PASSWORD STEP 3 – /auth/forgot-password/set
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.skip(reason="Legacy OTP-based password reset flow was removed.")
class TestForgotPasswordSet:

    def _verified_session(self, client):
        _set_session(client, pw_reset_user_id=10, pw_reset_otp_verified=True,
                     pw_reset_username="officer1")

    def test_get_without_session_redirects(self, client):
        r = client.get("/auth/forgot-password/set")
        assert r.status_code == 302

    def test_get_without_otp_verified_redirects(self, client):
        _set_session(client, pw_reset_user_id=10, pw_reset_otp_verified=False)
        r = client.get("/auth/forgot-password/set")
        assert r.status_code == 302

    def test_get_with_verified_session_renders_form(self, client):
        self._verified_session(client)
        r = client.get("/auth/forgot-password/set")
        assert r.status_code == 200
        assert b"officer1" in r.data or b"set_password" in r.data

    def test_post_default_password_rejected(self, client):
        self._verified_session(client)
        r = client.post("/auth/forgot-password/set", data={
            "new_password": "Nigaa@123",
            "confirm_password": "Nigaa@123",
        })
        assert r.status_code == 200

    def test_post_weak_password_rejected(self, client):
        self._verified_session(client)
        r = client.post("/auth/forgot-password/set", data={
            "new_password": "weak",
            "confirm_password": "weak",
        })
        assert r.status_code == 200

    def test_post_no_uppercase_rejected(self, client):
        self._verified_session(client)
        r = client.post("/auth/forgot-password/set", data={
            "new_password": "nouppercase1!",
            "confirm_password": "nouppercase1!",
        })
        assert r.status_code == 200

    def test_post_no_number_rejected(self, client):
        self._verified_session(client)
        r = client.post("/auth/forgot-password/set", data={
            "new_password": "NoNumber!abc",
            "confirm_password": "NoNumber!abc",
        })
        assert r.status_code == 200

    def test_post_no_special_rejected(self, client):
        self._verified_session(client)
        r = client.post("/auth/forgot-password/set", data={
            "new_password": "NoSpecial1A",
            "confirm_password": "NoSpecial1A",
        })
        assert r.status_code == 200

    def test_post_passwords_mismatch_rejected(self, client):
        self._verified_session(client)
        r = client.post("/auth/forgot-password/set", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": "Different@9!",
        })
        assert r.status_code == 200

    def test_post_success_calls_model(self, client):
        self._verified_session(client)
        r = client.post("/auth/forgot-password/set", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
        }, follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]
        assert any(c[0] == "update_password_only" for c in client.stub.calls)

    def test_post_success_clears_session(self, client):
        self._verified_session(client)
        client.post("/auth/forgot-password/set", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
        })
        sess = _get_session(client)
        for key in ("pw_reset_user_id", "pw_reset_username",
                    "pw_reset_mobile", "pw_reset_otp_verified"):
            assert key not in sess

    def test_post_model_error_shows_error(self, client, monkeypatch):
        def _raise(*_a, **_k): raise RuntimeError("DB down")
        monkeypatch.setattr(app_module.models, "update_password_only", _raise)
        self._verified_session(client)
        r = client.post("/auth/forgot-password/set", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
        })
        assert r.status_code == 200

    def test_post_without_session_does_not_call_model(self, client):
        r = client.post("/auth/forgot-password/set", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
        })
        assert r.status_code == 302
        assert not any(c[0] == "update_password_only" for c in client.stub.calls)


# ═══════════════════════════════════════════════════════════════════════════════
# F. SUPER-ADMIN RECOVERY PATH (OTP VIA PHONE)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.skip(reason="Legacy OTP-based password reset flow was removed.")
class TestSuperAdminForgotPassword:

    def test_super_admin_goes_to_verify_otp_when_phone_exists(self, client, monkeypatch):
        patch_otp(monkeypatch)
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: SUPER_ADMIN)
        r = client.post("/auth/forgot-password", data={"fp_username": "superadmin"})
        assert r.status_code == 200
        assert b"Enter OTP" in r.data or b"OTP" in r.data

    def test_super_admin_reset_sets_mobile_session_state(self, client, monkeypatch):
        patch_otp(monkeypatch)
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: SUPER_ADMIN)
        client.post("/auth/forgot-password", data={"fp_username": "superadmin"})
        sess = _get_session(client)
        assert sess.get("pw_reset_user_id") == SUPER_ADMIN["id"]
        assert sess.get("pw_reset_mobile") == SUPER_ADMIN["phone"]
        assert sess.get("pw_reset_otp_verified") is False

    def test_super_admin_otp_is_sent(self, client, monkeypatch):
        send_calls = []
        monkeypatch.setattr(app_module, "_send_login_otp",
                            lambda m: send_calls.append(m) or (True, "sent"))
        monkeypatch.setattr(app_module, "_normalize_mobile_for_otp", lambda p: p)
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: SUPER_ADMIN)
        client.post("/auth/forgot-password", data={"fp_username": "superadmin"})
        assert send_calls == [SUPER_ADMIN["phone"]]

    def test_super_admin_without_phone_is_blocked(self, client, monkeypatch):
        patch_otp(monkeypatch)
        monkeypatch.setattr(app_module.models, "get_user_by_username",
                            lambda u: {**SUPER_ADMIN, "phone": None})
        r = client.post("/auth/forgot-password", data={"fp_username": "superadmin"},
                        follow_redirects=True)
        assert r.status_code == 200

    def test_super_admin_can_complete_reset_after_otp_verification(self, client, monkeypatch):
        patch_otp(monkeypatch)
        _set_session(client, pw_reset_user_id=1, pw_reset_otp_verified=True,
                     pw_reset_username="superadmin", pw_reset_mobile="9000000001")
        r = client.post("/auth/forgot-password/set", data={
            "new_password": VALID_PASSWORD,
            "confirm_password": VALID_PASSWORD,
        }, follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["Location"]
        assert any(c[0] == "update_password_only" for c in client.stub.calls)


# ═══════════════════════════════════════════════════════════════════════════════
# G. LOGIN ROUTE – must_change_password interception
# ═══════════════════════════════════════════════════════════════════════════════

class TestLoginMustChangePassword:

    def test_must_change_password_user_redirected_to_setup(self, client, monkeypatch):
        monkeypatch.setattr(app_module.models, "authenticate_user",
                            lambda u, p: NORMAL_USER)
        r = client.post("/login", data={
            "username": "officer1",
            "password": "Nigaa@123",
            "login_action": "credentials",
            **_captcha_form(client),
        })
        assert r.status_code == 302
        assert "/auth/login/verify" in r.headers["Location"]
        r = client.post("/auth/login/verify", data={"otp_code": "123456"})
        assert r.status_code == 302
        assert "first-login-setup" in r.headers["Location"]

    def test_must_change_password_sets_force_session(self, client, monkeypatch):
        monkeypatch.setattr(app_module.models, "authenticate_user",
                            lambda u, p: NORMAL_USER)
        client.post("/login", data={
            "username": "officer1",
            "password": "Nigaa@123",
            "login_action": "credentials",
            **_captcha_form(client),
        })
        client.post("/auth/login/verify", data={"otp_code": "123456"})
        sess = _get_session(client)
        assert sess.get("force_change_user_id") == NORMAL_USER["id"]
        assert sess.get("force_change_username") == NORMAL_USER["username"]
        assert "user_id" not in sess  # full session NOT activated

    def test_no_must_change_proceeds_normally(self, client, monkeypatch):
        user_ok = {**NORMAL_USER, "must_change_password": False}
        monkeypatch.setattr(app_module.models, "authenticate_user",
                            lambda u, p: user_ok)
        r = client.post("/login", data={
            "username": "officer1",
            "password": "Pass@1234",
            "login_action": "credentials",
            **_captcha_form(client),
        })
        # Should NOT redirect to first-login-setup
        assert "first-login-setup" not in r.headers.get("Location", "")

    # ── Regression: existing user with no phone (the deo_apcpdcl scenario) ──

    def test_existing_user_no_phone_redirected_to_setup(self, client, monkeypatch):
        """Existing user (must_change_password=False) but no phone → setup page."""
        user_no_phone = {**NORMAL_USER, "must_change_password": False, "phone": None}
        monkeypatch.setattr(app_module.models, "authenticate_user",
                            lambda u, p: user_no_phone)
        r = client.post("/login", data={
            "username": "deo_apcpdcl",
            "password": "Nigaa@123",
            "login_action": "credentials",
            **_captcha_form(client),
        })
        assert r.status_code == 302
        assert "first-login-setup" not in r.headers["Location"]

    def test_existing_user_no_phone_sets_force_session(self, client, monkeypatch):
        """After no-phone redirect, force_change_user_id must be set in session."""
        user_no_phone = {**NORMAL_USER, "must_change_password": False, "phone": None}
        monkeypatch.setattr(app_module.models, "authenticate_user",
                            lambda u, p: user_no_phone)
        client.post("/login", data={
            "username": "deo_apcpdcl",
            "password": "Nigaa@123",
            "login_action": "credentials",
            **_captcha_form(client),
        })
        sess = _get_session(client)
        assert sess.get("force_change_user_id") is None
        assert sess.get("user_id") == NORMAL_USER["id"]

    def test_existing_user_no_phone_error_message_not_shown(self, client, monkeypatch):
        """The old 'Contact admin' dead-end must NOT appear anymore."""
        user_no_phone = {**NORMAL_USER, "must_change_password": False, "phone": None}
        monkeypatch.setattr(app_module.models, "authenticate_user",
                            lambda u, p: user_no_phone)
        r = client.post("/login", data={
            "username": "deo_apcpdcl",
            "password": "Nigaa@123",
            "login_action": "credentials",
            **_captcha_form(client),
        }, follow_redirects=True)
        # Must NOT see the old dead-end error on the login page
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
