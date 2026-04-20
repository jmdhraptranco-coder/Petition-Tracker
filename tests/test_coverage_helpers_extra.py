import io
import json
import time
from datetime import datetime
from pathlib import Path

from werkzeug.datastructures import FileStorage

import app as app_module
import models
from tests.test_models_db_ops import bind_db


def _upload(name, payload=b"data", content_type="application/octet-stream"):
    return FileStorage(stream=io.BytesIO(payload), filename=name, content_type=content_type)


def test_storage_and_filename_helpers(monkeypatch):
    base_dir = Path("test_artifacts_uploads")
    if base_dir.exists():
        import shutil
        shutil.rmtree(base_dir)
    base_dir.mkdir()

    assert app_module._normalize_storage_relpath("a/b.pdf") == "a/b.pdf"
    assert app_module._normalize_storage_relpath("../bad") is None
    assert app_module._normalize_storage_relpath("a//b") is None

    abs_path = app_module._storage_abspath(str(base_dir), "a/b.pdf")
    assert abs_path.endswith("a\\b.pdf") or abs_path.endswith("a/b.pdf")
    assert app_module._storage_abspath(str(base_dir), "../evil.txt") is None

    ok, rel = app_module._save_uploaded_file(_upload("x.pdf", b"abc"), str(base_dir), "x.pdf", "Test")
    assert ok is True
    assert rel
    assert app_module._uploaded_file_exists(str(base_dir), rel) is True
    app_module._delete_uploaded_file(str(base_dir), rel)
    assert app_module._uploaded_file_exists(str(base_dir), rel) is False

    ok, msg = app_module._save_uploaded_file(None, str(base_dir), "x.pdf", "Test")
    assert ok is False and "missing" in msg.lower()

    assert app_module._build_storage_filename("report", "My File.PDF", petition_id=9).startswith("report_9_")
    assert app_module._build_storage_filename("report", "My File.PDF").startswith("report_")
    assert app_module._build_storage_filename("", "x.pdf") is None
    import shutil
    shutil.rmtree(base_dir)


def test_session_interface_and_session_record_helpers(monkeypatch):
    app_module.app.config["TESTING"] = True
    app_module.TEST_SERVER_SESSION_STORE.clear()
    iface = app_module.DatabaseSessionInterface()

    with app_module.app.test_request_context("/"):
        new_sess = iface.open_session(app_module.app, app_module.request)
        assert new_sess.new is True
        assert new_sess.sid

        response = app_module.app.make_response("ok")
        iface.save_session(app_module.app, new_sess, response)

        new_sess["user_id"] = 5
        new_sess.modified = True
        response = app_module.app.make_response("ok")
        iface.save_session(app_module.app, new_sess, response)
        assert new_sess.sid in app_module.TEST_SERVER_SESSION_STORE

    with app_module.app.test_request_context(
        "/",
        headers={"Cookie": f"{app_module.app.config['SESSION_COOKIE_NAME']}={new_sess.sid}"},
    ):
        loaded = iface.open_session(app_module.app, app_module.request)
        assert loaded.sid == new_sess.sid
        loaded.clear()
        loaded.modified = True
        response = app_module.app.make_response("ok")
        iface.save_session(app_module.app, loaded, response)
        assert new_sess.sid not in app_module.TEST_SERVER_SESSION_STORE

    app_module.app.config["TESTING"] = False
    calls = []
    monkeypatch.setattr(app_module.models, "get_server_session", lambda sid: calls.append(("get", sid)) or None)
    monkeypatch.setattr(app_module.models, "save_server_session", lambda sid, data, user_id, expires_at: calls.append(("save", sid, user_id)))
    monkeypatch.setattr(app_module.models, "delete_server_session", lambda sid: calls.append(("delete", sid)))
    assert app_module._load_server_session_record("abc") is None
    app_module._save_server_session_record("abc", {"x": 1}, 9, None)
    app_module._delete_server_session_record("abc")
    assert [item[0] for item in calls] == ["get", "save", "delete"]
    app_module.app.config["TESTING"] = True


def test_tabular_and_normalization_helpers(monkeypatch):
    assert app_module.parse_date_input("2026-02-17").isoformat() == "2026-02-17"
    assert app_module.parse_date_input("bad") is None
    assert app_module.parse_flexible_date("17-02-2026").isoformat() == "2026-02-17"
    assert app_module.parse_flexible_date("02/17/2026").isoformat() == "2026-02-17"
    assert app_module.parse_flexible_date("bad") is None

    assert app_module._normalize_header_key("Received Date") == "received_date"
    assert app_module._normalize_received_at("vizag") == "cvo_apepdcl_vizag"
    assert app_module._normalize_target_cvo("hq") == "headquarters"
    assert app_module._normalize_source("government") == "govt"
    assert app_module._normalize_source("weird") == "public_individual"
    assert app_module._normalize_petition_type("Electrical Accident") == "electrical_accident"
    assert app_module._normalize_petition_type("weird") == "other"
    assert app_module._to_bool("yes") is True
    assert app_module._to_bool("direct") is False
    assert app_module._normalize_petitioner_name("  Ravi   Kumar  ") == "Ravi Kumar"

    csv_upload = _upload("rows.csv", b"Received Date,Subject\n2026-02-17,One\n", "text/csv")
    rows = app_module._parse_tabular_upload_rows(csv_upload, {"subject"}, set(app_module.IMPORT_PETITION_HEADERS))
    assert rows[0]["subject"] == "One"

    bad_csv = _upload("rows.csv", b"Bad,Header\nx,y\n", "text/csv")
    try:
        app_module._parse_tabular_upload_rows(bad_csv, {"subject"}, set(app_module.IMPORT_PETITION_HEADERS))
        assert False
    except ValueError:
        assert True

    class FakeSheet:
        @staticmethod
        def iter_rows(values_only=True):
            return iter([
                ("Received Date", "Subject"),
                ("2026-02-17", "Two"),
            ])

    class FakeWorkbook:
        active = FakeSheet()

    monkeypatch.setattr(app_module, "load_workbook", lambda *_a, **_k: FakeWorkbook())
    xlsx_upload = _upload("rows.xlsx", b"x", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    rows = app_module._parse_tabular_upload_rows(xlsx_upload, {"subject"}, set(app_module.IMPORT_PETITION_HEADERS))
    assert rows[0]["subject"] == "Two"


def test_petitioner_profile_and_misc_helper_views(monkeypatch):
    with app_module.app.test_request_context("/x"):
        payload = app_module._build_petitioner_profile_payload(
            [
                {"id": 1, "sno": "VIG/1", "petitioner_name": "Ravi Kumar", "subject": "Sub 1", "status": "closed", "petition_type": "bribe", "source_of_petition": "govt", "received_date": datetime(2026, 2, 17).date()},
                {"id": 2, "sno": "VIG/2", "petitioner_name": "Ravi Kumar", "subject": "Sub 2", "status": "received", "petition_type": "other", "source_of_petition": "media", "received_date": datetime(2026, 3, 17).date()},
                {"id": 3, "sno": "VIG/3", "petitioner_name": "Anonymous", "subject": "Sub 3", "status": "received", "petition_type": "other", "source_of_petition": "media", "received_date": datetime(2026, 4, 17).date()},
            ],
            "Ravi Kumar",
        )
        assert payload["total_petitions"] == 2
        assert payload["closed_count"] == 1
        assert payload["recent_petitions"][0]["sno"] == "VIG/2"
        assert app_module.status_labels_for_api()["closed"] == "Closed"

        assert app_module._login_captcha_image_url("tok").endswith("/auth/login-captcha/tok")
        assert app_module._login_captcha_image_data_url("missing") == ""


def test_profile_and_help_upload_validators(monkeypatch):
    monkeypatch.setattr(app_module, "uuid4", lambda: type("U", (), {"hex": "abcd" * 8})())

    ok, name, err = app_module.validate_profile_photo_upload(_upload("photo.png", b"1234"), user_id=7)
    assert ok is True and name == "user_7_" + ("abcd" * 8) + ".png" and err is None

    ok, _, err = app_module.validate_profile_photo_upload(_upload("photo.txt", b"1234"), user_id=7)
    assert ok is False and "jpg" in err.lower()

    ok, _, mime, err = app_module.validate_help_resource_upload(_upload("guide.pdf", b"1234"))
    assert ok is True and mime == "application/pdf" and err is None

    ok, _, _, err = app_module.validate_help_resource_upload(_upload("guide.exe", b"1234"))
    assert ok is False and "not supported" in err.lower()


def test_input_validator_error_matrix(monkeypatch):
    empty_pdf = _upload("empty.pdf", b"", "application/pdf")
    ok, msg = app_module.validate_pdf_upload(empty_pdf, "Upload")
    assert ok is False and "empty" in msg.lower()

    text_pdf = _upload("bad.pdf", b"text", "application/pdf")
    ok, msg = app_module.validate_pdf_upload(text_pdf, "Upload")
    assert ok is False and "valid pdf" in msg.lower()

    monkeypatch.setattr(app_module, "MAX_UPLOAD_SIZE_BYTES", 4)
    big_pdf = _upload("big.pdf", b"%PDF-abcdef", "application/pdf")
    ok, msg = app_module.validate_pdf_upload(big_pdf, "Upload")
    assert ok is False and "below" in msg.lower()
    monkeypatch.setattr(app_module, "MAX_UPLOAD_SIZE_BYTES", app_module.config.MAX_UPLOAD_SIZE_MB * 1024 * 1024)

    assert app_module.validate_contact("abc") is False
    assert app_module.validate_email("bad-email") is False

    ok, msg = app_module.validate_password_strength("short", "Password")
    assert ok is False and "8 characters" in msg
    ok, msg = app_module.validate_password_strength("lowercase9@", "Password")
    assert ok is False and "uppercase" in msg
    ok, msg = app_module.validate_password_strength("UPPERCASE9@", "Password")
    assert ok is False and "lowercase" in msg
    ok, msg = app_module.validate_password_strength("NoNumber@", "Password")
    assert ok is False and "number" in msg
    ok, msg = app_module.validate_password_strength("NoSpecial9", "Password")
    assert ok is False and "special" in msg


def test_error_and_request_preference_helpers(monkeypatch):
    with app_module.app.test_request_context("/api/x", headers={"Accept": "application/json"}):
        assert app_module._request_prefers_json() is True
        response = app_module._render_http_error(404, "Missing", "Nope")
        assert response.status_code == 404
        assert response.get_json()["error"] == "Missing"

        response = app_module._render_transient_error(503, "Retry", "Later")
        assert response.status_code == 503
        assert response.headers["Retry-After"] == "4"

    with app_module.app.test_request_context("/page", headers={"Accept": "text/html"}):
        html_response = app_module._render_http_error(403, "Denied", "No access")
        assert html_response[1] == 403

        html_response = app_module._render_transient_error(502, "Upstream", "Busy", retry_after_seconds=2, max_retries=3)
        assert html_response[1] == 502
        assert html_response[2]["Retry-After"] == "2"

    with app_module.app.test_request_context("/page", headers={"Accept": "text/html,application/json;q=0.1"}):
        assert app_module._request_prefers_json() is False


def test_security_headers_and_safe_redirects(monkeypatch):
    monkeypatch.setattr(app_module.config, "IS_PRODUCTION", True, raising=False)

    with app_module.app.test_request_context("/login"):
        assert app_module._safe_internal_redirect_target("https://evil.example", "dashboard") == "/dashboard"
        assert app_module._safe_internal_redirect_target("petitions", "dashboard") == "/dashboard"
        assert app_module._safe_internal_redirect_target("/petitions?x=1", "dashboard") == "/petitions?x=1"

    with app_module.app.test_request_context("/login", headers={"X-Forwarded-For": "10.1.1.1"}, environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        monkeypatch.setattr(app_module.config, "TRUST_PROXY_HEADERS", True, raising=False)
        assert app_module._client_ip() == "10.1.1.1"

    with app_module.app.test_request_context("/dashboard"):
        from flask import session
        session["user_id"] = 1
        response = app_module.app.make_response("ok")
        response = app_module._security_after_request(response)
        assert response.headers["Cache-Control"].startswith("no-store")
        assert response.headers["Strict-Transport-Security"].startswith("max-age")


def test_login_failure_tracking_and_rate_limit_fallback(monkeypatch):
    monkeypatch.setattr(app_module.config, "LOGIN_RATE_LIMIT_WINDOW_SECONDS", 60, raising=False)
    monkeypatch.setattr(app_module.config, "LOGIN_RATE_LIMIT_MAX_ATTEMPTS", 2, raising=False)
    monkeypatch.setattr(app_module.config, "LOGIN_RATE_LIMIT_BLOCK_SECONDS", 120, raising=False)
    app_module.LOGIN_ATTEMPTS.clear()

    with app_module.app.test_request_context("/login", environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        monkeypatch.setattr(app_module.time, "time", lambda: 1000)
        app_module._register_login_failure()
        blocked, retry = app_module._is_login_blocked()
        assert blocked is False and retry == 0

        monkeypatch.setattr(app_module.time, "time", lambda: 1001)
        app_module._register_login_failure()
        blocked, retry = app_module._is_login_blocked()
        assert blocked is True and retry > 0

        app_module._clear_login_failures()
        blocked, _ = app_module._is_login_blocked()
        assert blocked is False

    monkeypatch.setattr(app_module, "models", object())
    monkeypatch.setattr(app_module.config, "PETITION_USER_RATE_LIMIT_WINDOW_SECONDS", 60, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_USER_RATE_LIMIT_MAX_SUBMISSIONS", 1, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_USER_RATE_LIMIT_BLOCK_SECONDS", 60, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_IP_RATE_LIMIT_WINDOW_SECONDS", 60, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_IP_RATE_LIMIT_MAX_SUBMISSIONS", 5, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_IP_RATE_LIMIT_BLOCK_SECONDS", 60, raising=False)
    app_module.PETITION_SUBMISSION_ATTEMPTS.clear()

    with app_module.app.test_request_context("/petitions/new", environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        from flask import session
        session["user_id"] = 11
        monkeypatch.setattr(app_module.time, "time", lambda: 2000)
        allowed, retry_after, scopes = app_module._consume_petition_submission_slot()
        assert allowed is True and retry_after == 0 and "user" in scopes
        monkeypatch.setattr(app_module.time, "time", lambda: 2001)
        allowed, retry_after, scopes = app_module._consume_petition_submission_slot()
        assert allowed is False and retry_after > 0 and "user" in scopes


def test_otp_helper_matrix():
    # OTP helpers were removed with password-only login.
    assert True


def test_otp_post_and_success_edge_matrix():
    # OTP transport code was removed with password-only login.
    assert True


def test_access_and_tracking_helpers(monkeypatch):
    with app_module.app.test_request_context("/x"):
        from flask import session
        session["user_id"] = 1
        session["user_role"] = "cvo_apspdcl"
        assert app_module._parse_requested_petition_id("4") == 4
        assert app_module._parse_requested_petition_id("-1") is None
        assert app_module._petition_id_from_filename("rep_12_file.pdf") == 12
        assert app_module._has_pending_inspector_detailed_request([
            {"action": "Enquiry Report Submitted"},
            {"action": "Inspector Requested Detailed Enquiry Permission"},
        ]) is True
        assert app_module._is_conversion_permission_stage(
            {"status": "sent_for_permission"},
            [{"action": "Requested PO Permission for Detailed Enquiry"}],
        ) is True
        assert app_module._has_conversion_request_history(
            [{"action": "Inspector Requested Detailed Enquiry Permission"}]
        ) is True

    monkeypatch.setattr(app_module, "models", type("M", (), {
        "can_user_access_petition": staticmethod(lambda uid, role, cvo, pid: pid == 5),
        "get_user_by_id": staticmethod(lambda uid: {
            1: {"id": 1, "role": "cvo_apspdcl", "cvo_office": "apspdcl"},
            2: {"id": 2, "role": "cvo_apcpdcl", "cvo_office": "apcpdcl"},
            3: {"id": 3, "role": "dsp", "cvo_office": "headquarters"},
        }.get(uid)),
        "find_petition_id_by_filename": staticmethod(lambda fn: 77 if "fallback" in fn else None),
    })())

    with app_module.app.test_request_context("/x"):
        from flask import session
        session["user_id"] = 1
        session["user_role"] = "cvo_apspdcl"
        assert app_module._can_access_petition(5) is True
        assert app_module._can_access_petition("bad") is False
        assert app_module._can_access_cvo_scope(2) is True
        assert app_module._can_access_cvo_scope(3) is False
        assert app_module._resolve_petition_id_for_file("fallback_name.pdf") == 77


def test_session_helpers(monkeypatch):
    class FakeModels:
        @staticmethod
        def get_server_session(_sid):
            return None

        @staticmethod
        def save_server_session(*_a, **_k):
            return None

        @staticmethod
        def delete_server_session(*_a, **_k):
            return None

        @staticmethod
        def get_user_by_id(uid):
            return {
                "id": uid,
                "username": "u",
                "full_name": "User",
                "role": "po",
                "cvo_office": None,
                "phone": "9999999999",
                "email": "u@example.com",
                "profile_photo": None,
                "session_version": 2,
                "is_active": True,
            }

    monkeypatch.setattr(app_module, "models", FakeModels)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_request_context("/x"):
        from flask import session
        session["user_id"] = 9
        session["auth_issued_at"] = 100
        session["auth_last_seen_at"] = 100
        session["session_version"] = 2
        user = app_module.refresh_session_user()
        assert user["id"] == 9
        assert session["username"] == "u"

        app_module._clear_authenticated_session()
        assert session.get("user_id") is None


def test_session_absolute_timeout(monkeypatch):
    class FakeModels:
        @staticmethod
        def get_user_by_id(uid):
            return {
                "id": uid,
                "username": "u",
                "full_name": "User",
                "role": "po",
                "cvo_office": None,
                "phone": "9999999999",
                "email": "u@example.com",
                "profile_photo": None,
                "session_version": 2,
                "is_active": True,
            }

    monkeypatch.setattr(app_module, "models", FakeModels)
    monkeypatch.setattr(app_module.time, "time", lambda: 50_000)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_request_context("/x"):
        from flask import session, g

        session["user_id"] = 9
        session["auth_issued_at"] = 50_000 - app_module._session_absolute_seconds() - 1
        session["auth_last_seen_at"] = 50_000
        session["session_version"] = 2
        assert app_module._load_current_authenticated_user() is None
        assert getattr(g, "auth_invalid_reason") == "session_absolute_timeout"


def test_concurrent_session_control_uses_server_side_pruning(monkeypatch):
    calls = []

    class FakeModels:
        @staticmethod
        def prune_user_server_sessions(user_id, max_sessions, keep_session_id=None):
            calls.append((user_id, max_sessions, keep_session_id))

    monkeypatch.setattr(app_module, "models", FakeModels)
    monkeypatch.setattr(app_module.config, "MAX_CONCURRENT_SESSIONS", 2, raising=False)
    monkeypatch.setattr(app_module.config, "REVOKE_OTHER_SESSIONS_ON_LOGIN", False, raising=False)

    with app_module.app.test_request_context("/x"):
        from flask import session

        session.sid = "sid-current"
        app_module._enforce_concurrent_session_control(7)

    assert calls == [(7, 2, "sid-current")]


def test_destroy_current_session_removes_server_record(monkeypatch):
    deleted = []
    monkeypatch.setattr(app_module, "_delete_server_session_record", lambda sid: deleted.append(sid))

    with app_module.app.test_request_context("/x"):
        from flask import session

        session.sid = "sid-to-delete"
        session["user_id"] = 11
        session["username"] = "tester"
        app_module._destroy_current_session()
        assert "user_id" not in session

    assert deleted == ["sid-to-delete"]


def test_session_interface_touches_store_when_cookie_refreshes(monkeypatch):
    touched = []
    app_module.app.config["TESTING"] = False
    monkeypatch.setattr(app_module, "_touch_server_session_record", lambda sid, expires_at: touched.append((sid, expires_at)))

    class DummyResponse:
        def __init__(self):
            self.deleted = []
            self.cookies = []

        def delete_cookie(self, *args, **kwargs):
            self.deleted.append((args, kwargs))

        def set_cookie(self, *args, **kwargs):
            self.cookies.append((args, kwargs))

    with app_module.app.test_request_context("/x"):
        session_obj = app_module.DatabaseBackedSession({"user_id": 1}, sid="sid-1", new=False)
        response = DummyResponse()
        interface = app_module.DatabaseSessionInterface()
        monkeypatch.setattr(interface, "should_set_cookie", lambda *_a, **_k: True)
        interface.save_session(app_module.app, session_obj, response)

    app_module.app.config["TESTING"] = True
    assert touched
    assert touched[0][0] == "sid-1"
    assert response.cookies


def test_touch_server_session_record_respects_threshold_in_testing(monkeypatch):
    app_module.app.config["TESTING"] = True
    sid = "sid-threshold"
    now_dt = datetime.now(app_module.timezone.utc).replace(tzinfo=None)
    app_module.TEST_SERVER_SESSION_STORE[sid] = {
        "user_id": 1,
        "data": {"user_id": 1},
        "expires_at": now_dt + app_module.timedelta(minutes=30),
        "last_accessed_at": now_dt,
    }
    touched = app_module._touch_server_session_record(sid, now_dt + app_module.timedelta(minutes=30))
    assert touched is False


def test_security_after_request_dedupes_session_cookie_headers():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_request_context("/dashboard"):
        response = app_module.Response("ok", status=200)
        cookie_name = app_module.app.config["SESSION_COOKIE_NAME"]
        response.headers.add("Set-Cookie", f"{cookie_name}=old; Path=/; HttpOnly")
        response.headers.add("Set-Cookie", "other=value; Path=/")
        response.headers.add("Set-Cookie", f"{cookie_name}=new; Path=/; HttpOnly")
        cleaned = app_module._security_after_request(response)
        cookies = cleaned.headers.getlist("Set-Cookie")
        assert "other=value; Path=/" in cookies
        assert sum(1 for value in cookies if value.startswith(f"{cookie_name}=")) == 1


def test_logout_all_sessions_uses_security_version(monkeypatch):
    calls = []

    class FakeModels:
        @staticmethod
        def get_user_by_id(user_id):
            return {
                "id": user_id,
                "username": "u",
                "full_name": "User",
                "role": "po",
                "cvo_office": None,
                "phone": None,
                "email": None,
                "profile_photo": None,
                "session_version": 1,
                "is_active": True,
            }

        @staticmethod
        def bump_user_session_version(user_id):
            calls.append(("bump", user_id))
            return 9

        @staticmethod
        def delete_user_server_sessions(user_id):
            calls.append(("delete", user_id))

    monkeypatch.setattr(app_module, "models", FakeModels)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = 3
            sess["user_role"] = "po"
            sess["username"] = "u"
            sess["full_name"] = "User"
            sess["session_version"] = 1
            sess["auth_issued_at"] = int(time.time())
            sess["auth_last_seen_at"] = int(time.time())
        response = client.post("/logout/all")
        assert response.status_code == 302
    assert calls == [("bump", 3), ("delete", 3)]


def test_session_validation_failures_and_csrf(monkeypatch):
    class FakeModels:
        @staticmethod
        def get_user_by_id(uid):
            if uid == 4:
                return None
            return {
                "id": uid,
                "username": "u",
                "full_name": "User",
                "role": "po",
                "cvo_office": None,
                "phone": "9999999999",
                "email": "u@example.com",
                "profile_photo": None,
                "session_version": 2 if uid != 5 else 3,
                "is_active": False if uid == 6 else True,
            }

    monkeypatch.setattr(app_module, "models", FakeModels)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_request_context("/x"):
        from flask import session, g
        session["user_id"] = 1
        assert app_module._get_or_create_csrf_token()
        assert app_module._current_csrf_token()

    cases = [
        ({"user_id": 1, "auth_issued_at": "bad", "auth_last_seen_at": 1, "session_version": 2}, "missing_session_metadata"),
        ({"user_id": 2, "auth_issued_at": 9_999_999_999, "auth_last_seen_at": 9_999_999_999, "session_version": 2}, "invalid_session_timestamp"),
        ({"user_id": 3, "auth_issued_at": 1, "auth_last_seen_at": 1, "session_version": 2}, "session_inactive"),
        ({"user_id": 4, "auth_issued_at": int(time.time()), "auth_last_seen_at": int(time.time()), "session_version": 2}, "missing_user"),
        ({"user_id": 5, "auth_issued_at": int(time.time()), "auth_last_seen_at": int(time.time()), "session_version": 2}, "credential_change"),
        ({"user_id": 6, "auth_issued_at": int(time.time()), "auth_last_seen_at": int(time.time()), "session_version": 2}, "inactive_user"),
    ]
    for values, expected_reason in cases:
        with app_module.app.test_request_context("/x"):
            from flask import session, g
            session.clear()
            session.update(values)
            assert app_module._load_current_authenticated_user() is None
            assert getattr(g, "auth_invalid_reason") == expected_reason


def test_misc_captcha_and_deo_helpers(monkeypatch):
    with app_module.app.test_request_context("/x"):
        assert app_module.get_deo_office_flow("po", "apspdcl") is None
        assert app_module.get_deo_target_options("po", "apspdcl") == []
        assert app_module.get_deo_target_options("data_entry", "bad-office") == []

    with app_module.app.test_request_context("/login"):
        _, token = app_module.generate_login_captcha("482753", issued_at=int(time.time()) + 10)
        assert app_module.validate_login_captcha("482753", token) is False

        _, token = app_module.generate_login_captcha("482753")
        store = app_module._get_login_captcha_challenges_store()
        challenge = dict(store[token])
        challenge["answer_digest"] = ""
        store[token] = challenge
        assert app_module.validate_login_captcha("482753", token) is False


def test_auth_session_helpers_and_decorators(monkeypatch):
    with app_module.app.test_request_context("/x"):
        from flask import session

        session.update(
            {
                "user_id": 1,
                "username": "tester",
                "full_name": "User",
                "user_role": "po",
                "cvo_office": None,
                "phone": "9999999999",
                "email": "u@example.com",
                "profile_photo": None,
                "session_version": 1,
                "auth_issued_at": 1,
                "auth_last_seen_at": 1,
                "auth_method": "password",
                "_csrf_token": "tok",
            }
        )
        app_module._clear_authenticated_session()
        assert "user_id" not in session

        session.sid = "old-sid"
        expired = []
        monkeypatch.setattr(app_module, "_expire_server_session_soon", lambda sid, seconds: expired.append(sid))
        monkeypatch.setattr(app_module, "_register_rotation_grace", lambda old, new: None)
        app_module._rotate_session_identifier()
        assert session.sid != "old-sid"
        assert expired == ["old-sid"]

        monkeypatch.setattr(app_module.time, "time", lambda: 12345)
        app_module._activate_login_session(
            {
                "id": 7,
                "username": "tester",
                "full_name": "Tester",
                "role": "po",
                "cvo_office": None,
                "phone": "9999999999",
                "email": "t@example.com",
                "profile_photo": None,
                "session_version": 2,
            }
        )
        assert session["user_id"] == 7
        assert session["auth_issued_at"] == 12345
        assert session.permanent is True

    assert app_module.resolve_efile_no_for_action({"efile_no": "EO-1"}, "EO-2") == ("EO-1", None)
    assert app_module.resolve_efile_no_for_action({"efile_no": ""}, "", "required")[1] == "required"
    assert app_module.resolve_efile_no_for_action({"efile_no": ""}, "X" * 101)[1] == "E-Office File No is too long."

    @app_module.login_required
    def _protected():
        return "ok"

    @app_module.role_required("po")
    def _po_only():
        return "po-ok"

    with app_module.app.test_request_context("/secure"):
        from flask import session, g

        response = _protected()
        assert response.status_code == 302

        session.clear()
        session["force_change_user_id"] = 1
        response = _protected()
        assert response.status_code == 302

        session.clear()
        monkeypatch.setattr(app_module, "_load_current_authenticated_user", lambda refresh_activity=True: None)
        g.auth_invalid_reason = "inactive_user"
        response = _protected()
        assert response.status_code == 302

        monkeypatch.setattr(app_module, "_load_current_authenticated_user", lambda refresh_activity=True: {"role": "inspector"})
        response = _po_only()
        assert response.status_code == 302

        g.current_user = {"role": "po"}
        assert _po_only() == "po-ok"


def test_login_attempt_cleanup_and_system_setting_defaults(monkeypatch):
    now = 2_000
    app_module.LOGIN_ATTEMPTS.clear()
    app_module.LOGIN_ATTEMPTS["old"] = {"last_seen": 0}
    app_module.LOGIN_ATTEMPTS["new"] = {"last_seen": now}
    app_module._cleanup_login_attempts(now)
    assert "old" not in app_module.LOGIN_ATTEMPTS
    assert "new" in app_module.LOGIN_ATTEMPTS

    monkeypatch.setattr(
        app_module,
        "models",
        type("M", (), {"get_system_settings": staticmethod(lambda prefix=None: {"petition_user_rate_limit_max_submissions": "abc", "petition_ip_rate_limit_max_submissions": "77"})})(),
    )
    with app_module.app.test_request_context("/x"):
        effective = app_module.get_effective_system_settings()
        assert effective["petition_ip_rate_limit_max_submissions"] == 77


def test_model_signup_reset_settings_and_sessions(monkeypatch):
    monkeypatch.setattr(models, "generate_password_hash", lambda pwd: f"h::{pwd}")

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"id": 2, "username": "u"}, {"id": 10}])
    assert models.create_password_reset_request("u", "pass") == 10
    assert conn.commits == 1

    bind_db(monkeypatch, fetchall_items=[[{"id": 1}]])
    assert models.get_pending_password_reset_requests()[0]["id"] == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"id": 1, "status": "pending", "user_id": 4, "requested_password_hash": "h::x"}, {"id": 4}])
    models.approve_password_reset_request(1, 77)
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "pending"}])
    models.reject_password_reset_request(1, 77, "no")
    assert conn.commits == 1

    bind_db(monkeypatch, fetchall_items=[[{"setting_key": "petition_user_rate_limit_max_submissions", "setting_value": "12"}]])
    assert models.get_system_settings()["petition_user_rate_limit_max_submissions"] == "12"

    conn, _ = bind_db(monkeypatch)
    models.upsert_system_settings({"petition_x": 5}, 1)
    assert conn.commits == 1

    future = datetime(2099, 1, 1, 0, 0, 0)
    bind_db(monkeypatch, fetchone_items=[{"session_id": "s1", "user_id": 1, "session_data_json": json.dumps({"a": 1}), "expires_at": future}])
    assert models.get_server_session("s1")["data"]["a"] == 1

    conn, _ = bind_db(monkeypatch)
    models.save_server_session("s1", {"a": 1}, 1, future)
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch)
    models.delete_server_session("s1")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch)
    models.delete_user_server_sessions(1, exclude_session_id="s2")
    assert conn.commits == 1


def test_model_help_resource_and_profile_helpers(monkeypatch):
    bind_db(monkeypatch, fetchall_items=[[{"id": 1, "title": "Guide"}]])
    assert models.get_cmd_cgm_users()[0]["id"] == 1

    bind_db(monkeypatch, fetchall_items=[[{"id": 2, "title": "Manual", "resource_type": "manual"}]])
    assert models.list_help_resources(active_only=True)[0]["id"] == 2

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"id": 5}])
    assert models.create_help_resource("Guide", "manual", "upload", "guide.pdf", None, "application/pdf", 1, 9) == 5
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch)
    models.set_help_resource_active(5, True)
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch)
    models.set_must_change_password(7, True)
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch)
    models.update_user_profile_info(7, "Tester", "9999999999", "a@b.com")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch)
    models.set_user_profile_photo(7, "avatar.png")
    assert conn.commits == 1


def test_model_imported_state_and_accident_detail_helpers(monkeypatch):
    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "received"}])
    models.update_imported_petition_state(
        1,
        99,
        status="forwarded_to_cvo",
        current_handler_id=5,
        assigned_inspector_id=8,
        target_cvo="apspdcl",
        requires_permission=True,
        permission_status="pending",
        enquiry_type="detailed",
        received_date=datetime(2026, 2, 17).date(),
        remarks="Imported",
    )
    assert conn.commits == 1

    bind_db(
        monkeypatch,
        fetchall_items=[
            [
                {
                    "petition_id": 1,
                    "accident_type": "fatal",
                    "deceased_category": "departmental",
                    "departmental_type": "regular",
                    "non_departmental_type": None,
                    "deceased_count": 1,
                    "general_public_count": 0,
                    "animals_count": 0,
                }
            ]
        ],
    )
    details = models.get_latest_enquiry_report_accident_details([1])
    assert details[1]["accident_type"] == "fatal"
    assert models.get_latest_enquiry_report_accident_details([]) == {}
