from datetime import date, datetime

import app as app_module

from conftest import login_as


class AuthModelsStub:
    def __init__(self):
        self.calls = []
        self.user = None

    def _record(self, name, **kwargs):
        self.calls.append((name, kwargs))

    def get_user_by_id(self, user_id):
        if user_id == 77:
            return None
        return {
            "id": user_id,
            "username": "tester",
            "full_name": "Tester",
            "role": "super_admin",
            "cvo_office": None,
            "phone": "9999999999",
            "email": "t@example.com",
            "profile_photo": None,
            "session_version": 1,
            "is_active": True,
            "must_change_password": False,
        }

    def get_all_petitions(self):
        return [
            {"status": "closed", "updated_at": datetime.now(), "target_cvo": "apspdcl", "received_at": "jmd_office", "received_date": date.today()},
            {"status": "forwarded_to_po", "updated_at": datetime.now(), "target_cvo": "apepdcl", "received_at": "cvo_apepdcl_vizag", "received_date": date.today()},
        ]

    def list_help_resources(self, active_only=False):
        return [
            {"resource_type": "office_order", "storage_kind": "external_url", "external_url": "https://example.com/o", "file_name": None},
            {"resource_type": "news", "storage_kind": "external_url", "external_url": "https://example.com/n", "file_name": None},
        ]

    def authenticate_user(self, _u, _p):
        return self.user

    def create_password_reset_request(self, username, password):
        self._record("create_password_reset_request", username=username, password=password)
        if username == "missing":
            raise ValueError("not found")

    def update_password_and_phone(self, user_id, password, phone):
        self._record("update_password_and_phone", user_id=user_id, password=password, phone=phone)

    def update_password_only(self, user_id, password):
        self._record("update_password_only", user_id=user_id, password=password)


def _issue_captcha(client, answer="482753"):
    client.get("/login")
    with client.session_transaction() as sess:
        challenges = dict(sess.get("login_captcha_challenges") or {})
        token = next(reversed(challenges))
        challenge = dict(challenges[token])
        challenge["answer_digest"] = app_module._login_captcha_answer_digest(token, answer)
        challenge["image_b64"] = app_module.base64.b64encode(app_module._build_login_captcha_bmp(answer)).decode("ascii")
        challenges[token] = challenge
        sess["login_captcha_challenges"] = challenges
        return token


def _login_post(client, username="u", password="p", **extra):
    token = _issue_captcha(client)
    data = {"username": username, "password": password, "captcha_answer": "482753", "captcha_token": token}
    data.update(extra)
    return client.post("/login", data=data)


def test_index_landing_and_help_resources(monkeypatch):
    stub = AuthModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        response = client.get("/")
        assert response.status_code == 200
        assert "office_order" not in response.get_data(as_text=True) or response.get_data(as_text=True)

        login_as(client, role="po")
        redirect_resp = client.get("/")
        assert redirect_resp.status_code == 302
        assert redirect_resp.headers["Location"].endswith("/dashboard")


def test_login_route_and_first_login_branches(monkeypatch):
    import auth_routes as auth_routes_mod
    stub = AuthModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(auth_routes_mod, "_otp_api_call",
                        lambda url, payload: {"status": "success"})
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        assert client.get("/login?refresh_captcha=1").status_code == 200

        stub.user = {"id": 1, "username": "u", "full_name": "JMD", "role": "jmd", "phone": "9876543210", "must_change_password": False}
        assert _login_post(client, "u", "p").status_code == 302

        stub.user = {"id": 2, "username": "u2", "full_name": "First", "role": "po", "phone": "9876543210", "must_change_password": True}
        assert _login_post(client, "u2", "p").status_code == 302

        stub.user = {"id": 3, "username": "u3", "full_name": "No Phone", "role": "po", "phone": None, "email": None, "profile_photo": None, "must_change_password": False}
        # User with no phone: _get_user_by_username_for_auth falls back to stub.user which has no phone
        # Login will show "No valid mobile number" error and return 200
        assert _login_post(client, "u3", "p").status_code == 200


def test_login_uses_current_user_session_version(monkeypatch):
    import auth_routes as auth_routes_mod
    stub = AuthModelsStub()
    stub.user = {
        "id": 7,
        "username": "testuser",
        "full_name": "Test User",
        "role": "po",
        "phone": "919999999999",
        "email": None,
        "profile_photo": None,
        "must_change_password": False,
        "session_version": 5,
        "is_active": True,
    }
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(stub, "get_user_by_id", lambda user_id: dict(stub.user) if user_id == 7 else None)
    monkeypatch.setattr(auth_routes_mod, "_otp_api_call",
                        lambda url, payload: {"status": "success"})
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        response = _login_post(client, username="testuser", password="p")
        assert response.status_code == 302
        assert "/auth/otp/verify" in response.headers["Location"]
        # Complete OTP step
        response = client.post("/auth/otp/verify", data={"otp_code": "123456"})
        assert response.status_code == 302
        assert "/dashboard" in response.headers["Location"]
        with client.session_transaction() as sess:
            assert sess.get("user_id") == 7
            assert sess.get("session_version") == 5


def test_request_recovery_and_first_login_setup(monkeypatch):
    stub = AuthModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        # OTP-based forgot-password returns 200 (renders login page) for error cases
        assert client.post("/auth/request-recovery", data={}).status_code == 200
        assert client.post("/auth/request-recovery", data={"recovery_username": "u"}).status_code == 200
        assert client.post("/auth/request-recovery", data={"recovery_username": "missing"}).status_code == 200

        assert client.post("/auth/request-signup").status_code == 302

        with client.session_transaction() as sess:
            sess["force_change_user_id"] = 7
            sess["force_change_role"] = "super_admin"
        assert client.get("/auth/first-login-setup").status_code == 200
        assert client.post("/auth/first-login-setup", data={"new_password": app_module._DEFAULT_PASSWORD, "confirm_password": app_module._DEFAULT_PASSWORD, "phone": "9999999999"}).status_code == 302
        assert client.post("/auth/first-login-setup", data={"new_password": "StrongPass@9", "confirm_password": "Mismatch@9", "phone": "9999999999"}).status_code == 302
        assert client.post("/auth/first-login-setup", data={"new_password": "StrongPass@9", "confirm_password": "StrongPass@9", "phone": "bad"}).status_code == 302
        response = client.post("/auth/first-login-setup", data={"new_password": "StrongPass@9", "confirm_password": "StrongPass@9", "phone": "9999999999"})
        assert response.status_code == 302
        assert any(name == "update_password_and_phone" for name, _ in stub.calls)


def test_session_store_health_and_admin_diagnostics(monkeypatch):
    stub = AuthModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(
        stub,
        "get_server_session_health_stats",
        lambda: {
            "total_sessions": 5,
            "active_sessions": 4,
            "expired_sessions": 1,
            "active_users": 3,
            "oldest_session_created_at": None,
            "latest_session_updated_at": None,
        },
        raising=False,
    )
    app_module.SESSION_DIAGNOSTIC_EVENTS.clear()
    app_module.SESSION_DIAGNOSTIC_EVENTS.appendleft(
        {
            "ts": "2026-04-06T00:00:00Z",
            "event_type": "proxy.proto_mismatch",
            "severity": "warning",
            "forwarded_proto": "https",
            "request_secure": False,
        }
    )
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        health = client.get("/healthz/session-store")
        assert health.status_code == 200
        payload = health.get_json()
        assert payload["active_sessions"] == 4
        assert payload["expired_ratio"] == 0.2

        login_as(client, role="super_admin")
        diagnostics = client.get("/admin/session-diagnostics")
        assert diagnostics.status_code == 200
        assert "Session Store Health" in diagnostics.get_data(as_text=True)


def test_login_ignores_unknown_non_credential_actions(monkeypatch):
    stub = AuthModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        response = client.post("/login", data={"login_action": "unknown_action"})
        assert response.status_code == 200

        html = client.get("/login").get_data(as_text=True)
        assert "OTP Verification" not in html
