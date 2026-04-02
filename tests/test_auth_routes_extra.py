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


def test_login_route_otp_and_first_login_branches(monkeypatch):
    stub = AuthModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(app_module, "_send_login_otp", lambda mobile: (True, None))
    monkeypatch.setattr(app_module, "_verify_login_otp", lambda mobile, code: (code == "1234", "bad otp"))
    monkeypatch.setattr(app_module, "_is_otp_login_enabled", lambda: True)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        assert client.get("/login?refresh_captcha=1").status_code == 200

        with client.session_transaction() as sess:
            sess["otp_pending_user"] = {"id": 1, "full_name": "Tester", "username": "tester", "role": "po"}
            sess["otp_pending_mobile"] = "919999999999"
        assert client.get("/login?reset_otp=1").status_code == 200

        with client.session_transaction() as sess:
            sess["otp_pending_user"] = {"id": 1, "full_name": "Tester", "username": "tester", "role": "po"}
            sess["otp_pending_mobile"] = "919999999999"
        assert client.post("/login", data={"login_action": "resend_otp"}).status_code == 302
        assert client.post("/login", data={"login_action": "verify_otp", "otp_code": "abcd"}).status_code == 302
        assert client.post("/login", data={"login_action": "verify_otp", "otp_code": "0000"}).status_code == 302

        with client.session_transaction() as sess:
            sess["otp_pending_user"] = {"id": 1, "full_name": "Tester", "username": "tester", "role": "po"}
            sess["otp_pending_mobile"] = "919999999999"
        assert client.post("/login", data={"login_action": "verify_otp", "otp_code": "1234"}).status_code == 302

        stub.user = {"id": 1, "username": "u", "full_name": "JMD", "role": "jmd", "must_change_password": False}
        assert _login_post(client, "u", "p").status_code == 302

        stub.user = {"id": 2, "username": "u2", "full_name": "First", "role": "po", "must_change_password": True}
        assert _login_post(client, "u2", "p").status_code == 302

        stub.user = {"id": 3, "username": "u3", "full_name": "No Phone", "role": "po", "phone": None, "email": None, "profile_photo": None, "must_change_password": False}
        assert _login_post(client, "u3", "p").status_code == 302


def test_otp_verify_uses_current_user_session_version(monkeypatch):
    stub = AuthModelsStub()
    stub.user = {
        "id": 7,
        "username": "otpuser",
        "full_name": "OTP User",
        "role": "po",
        "phone": "919999999999",
        "email": None,
        "profile_photo": None,
        "must_change_password": False,
        "session_version": 5,
        "is_active": True,
    }
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(app_module, "_verify_login_otp", lambda mobile, code: (True, None))
    monkeypatch.setattr(stub, "get_user_by_id", lambda user_id: dict(stub.user) if user_id == 7 else None)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["otp_pending_user"] = {"id": 7, "full_name": "OTP User", "username": "otpuser", "role": "po"}
            sess["otp_pending_mobile"] = "919999999999"
        response = client.post("/login", data={"login_action": "verify_otp", "otp_code": "1234"})
        assert response.status_code == 302
        with client.session_transaction() as sess:
            assert sess.get("user_id") == 7
            assert sess.get("session_version") == 5


def test_request_recovery_and_first_login_setup(monkeypatch):
    stub = AuthModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        assert client.post("/auth/request-recovery", data={}).status_code == 302
        assert client.post("/auth/request-recovery", data={"recovery_username": "u", "recovery_password": "weak", "recovery_confirm_password": "weak"}).status_code == 302
        assert client.post("/auth/request-recovery", data={"recovery_username": "u", "recovery_password": "StrongPass@9", "recovery_confirm_password": "Mismatch@9"}).status_code == 302
        assert client.post("/auth/request-recovery", data={"recovery_username": "missing", "recovery_password": "StrongPass@9", "recovery_confirm_password": "StrongPass@9"}).status_code == 302
        assert client.post("/auth/request-recovery", data={"recovery_username": "u", "recovery_password": "StrongPass@9", "recovery_confirm_password": "StrongPass@9"}).status_code == 302

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


def test_login_auxiliary_otp_paths(monkeypatch):
    stub = AuthModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(app_module, "_is_otp_login_enabled", lambda: True)
    monkeypatch.setattr(app_module, "_send_login_otp", lambda mobile: (False, "otp send failed"))
    monkeypatch.setattr(app_module, "_verify_login_otp", lambda mobile, code: (False, "otp verify failed"))
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        response = client.post("/login", data={"login_action": "reset_otp"})
        assert response.status_code == 302

        response = client.post("/login", data={"login_action": "resend_otp"})
        assert response.status_code == 302

        with client.session_transaction() as sess:
            sess["otp_pending_user"] = {"id": 1, "full_name": "Tester", "username": "tester", "role": "po"}
            sess["otp_pending_mobile"] = "919999999999"
        response = client.post("/login", data={"login_action": "resend_otp"})
        assert response.status_code == 302

        with client.session_transaction() as sess:
            sess["otp_pending_user"] = {"id": 1, "full_name": "Tester", "username": "tester", "role": "po"}
            sess["otp_pending_mobile"] = "919999999999"
        response = client.post("/login", data={"login_action": "verify_otp", "otp_code": "1234"})
        assert response.status_code == 302

        with client.session_transaction() as sess:
            sess["otp_pending_user"] = {"id": 1, "full_name": "Tester", "username": "tester", "role": "po"}
            sess["otp_pending_mobile"] = "919999999999"
        html = client.get("/login").get_data(as_text=True)
        assert "otp" in html.lower()
