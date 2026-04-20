import io
import time
from datetime import date, datetime

import app as app_module

from conftest import login_as


class RichModelsStub:
    def __init__(self):
        self.calls = []
        self.fail_methods = set()
        self.system_settings = {}
        self.user = {
            "id": 1,
            "username": "tester",
            "full_name": "Tester",
            "role": "super_admin",
            "cvo_office": None,
            "session_version": 1,
        }
        self.petition = {
            "id": 1,
            "requires_permission": False,
            "status": "forwarded_to_cvo",
            "efile_no": None,
            "enquiry_type": "preliminary",
            "target_cvo": "apspdcl",
        }

    def _record(self, name, **kwargs):
        self.calls.append((name, kwargs))
        return None

    def authenticate_user(self, _u, _p):
        return self.user

    def get_petitions_for_user(self, *_a, **_k):
        return [
            {
                "id": 1,
                "sno": "VIG/PO/2026/0001",
                "efile_no": None,
                "petitioner_name": "Pet One",
                "subject": "Subject One",
                "petition_type": "bribe",
                "status": "received",
                "received_date": date(2026, 2, 17),
            },
            {
                "id": 2,
                "sno": "VIG/PO/2026/0002",
                "efile_no": "EO-1",
                "petitioner_name": "Pet Two",
                "subject": "Subject Two",
                "petition_type": "other",
                "status": "closed",
                "received_date": date(2026, 2, 17),
            },
        ]

    def get_dashboard_stats(self, *_a, **_k):
        return {"sla_within": 1, "sla_breached": 0, "kpi_cards": []}

    def get_all_petitions(self, *_a, **_k):
        return [{"id": 1, "sno": "VIG/PO/2026/0001", "subject": "Subject", "status": "received"}]

    def get_petition_by_id(self, _pid):
        return dict(self.petition)

    def get_petition_tracking(self, _pid):
        return []

    def get_enquiry_report(self, _pid):
        return {"id": 99}

    def can_user_access_petition(self, user_id, user_role, cvo_office, petition_id):
        return True

    def get_all_enquiry_reports(self, _pid):
        return []

    def get_inspectors_by_cvo(self, _uid):
        return [{"id": 8, "full_name": "Inspector"}]

    def get_cvo_users(self):
        return [{"id": 2, "full_name": "CVO"}]

    def get_cmd_cgm_users(self):
        return [{"id": 6, "full_name": "CMD User", "username": "cmd1", "role": "cmd_apspdcl"}]

    def get_form_field_configs(self):
        return {}

    def get_system_settings(self, prefix=None):
        if not prefix:
            return dict(self.system_settings)
        return {k: v for k, v in self.system_settings.items() if str(k).startswith(prefix)}

    def upsert_system_settings(self, settings, updated_by):
        self.system_settings.update({str(k): str(v) for k, v in (settings or {}).items()})
        self._record("upsert_system_settings", settings=dict(settings or {}), updated_by=updated_by)

    def get_all_users(self):
        return [{"id": 1}]

    def get_role_login_users(self):
        return [{"id": 1}]

    def get_inspector_mappings(self):
        return [{"id": 1}]

    def get_pending_reset_requests(self):
        return []

    def get_pending_password_reset_requests(self):
        return []

    def get_user_by_id(self, _uid):
        return {"id": _uid, "role": "super_admin", "username": "tester", "full_name": "Tester", "cvo_office": None, "phone": None, "email": None, "profile_photo": None, "session_version": 1, "is_active": True}

    def get_user_by_username(self, _uname):
        return {"id": 2, "role": "cvo_apspdcl", "username": _uname, "full_name": "CVO User", "cvo_office": "apspdcl", "phone": "9000000001", "email": None, "profile_photo": None, "session_version": 1, "is_active": True}

    def get_dashboard_drilldown(self, *_a, **_k):
        return [{"id": 1, "sno": "VIG/PO/2026/0001", "petitioner_name": "X", "subject": "S", "status": "received", "received_date": date(2026, 2, 17)}]

    def _get_workflow_stage_stats(self, *_a, **_k):
        return {
            "stage_1": 1,
            "stage_2": 1,
            "stage_3": 0,
            "stage_4": 0,
            "stage_5": 0,
            "stage_6": 0,
        }

    def _get_sla_stats_for_petitions(self, *_a, **_k):
        return {
            "sla_total": 2,
            "sla_within": 1,
            "sla_breached": 0,
            "sla_in_progress": 1,
            "sla_open_total": 1,
            "sla_closed_total": 1,
            "sla_open_within": 1,
            "sla_open_beyond": 0,
            "sla_closed_within": 1,
            "sla_closed_beyond": 0,
            "sla_total_within": 2,
            "sla_total_beyond": 0,
        }

    def _build_role_kpi_cards(self, *_a, **_k):
        return []

    def __getattr__(self, name):
        def _fn(*args, **kwargs):
            if name in self.fail_methods:
                raise Exception(f"forced failure in {name}")
            self._record(name, args=args, kwargs=kwargs)
            if name == "create_user":
                return 7
            if name == "create_petition":
                return {"id": 1, "sno": "VIG/PO/2026/0001"}
            return None

        return _fn


def _pdf(name="file.pdf"):
    return (io.BytesIO(b"%PDF-1.4 test"), name)


def _post_action(client, role, action, data=None, multipart=False):
    login_as(client, role=role)
    payload = {"action": action}
    if data:
        payload.update(data)
    if multipart:
        return client.post("/petitions/1/action", data=payload, content_type="multipart/form-data")
    return client.post("/petitions/1/action", data=payload)


def _issue_login_captcha(client, answer="482753", issued_at=None):
    client.get("/login")
    with client.session_transaction() as session_data:
        challenges = dict(session_data.get("login_captcha_challenges") or {})
        assert challenges
        captcha_token = next(reversed(challenges))
        challenge = dict(challenges[captcha_token])
        challenge["answer_digest"] = app_module._login_captcha_answer_digest(captcha_token, answer)
        challenge["image_b64"] = app_module.base64.b64encode(
            app_module._build_login_captcha_bmp(answer)
        ).decode("ascii")
        if issued_at is not None:
            challenge["issued_at"] = issued_at
        challenges[captcha_token] = challenge
        session_data["login_captcha_challenges"] = challenges
        return captcha_token


def _post_login(client, username="u", password="p"):
    captcha_token = _issue_login_captcha(client, "482753")
    return client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "captcha_answer": "482753",
            "captcha_token": captcha_token,
        },
    )


def test_auth_dashboard_and_core_views(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        root_response = client.get("/")
        assert root_response.status_code == 200
        assert b"Portal Nigaa" in root_response.data
        assert client.get("/login").status_code == 200
        assert _post_login(client, "u", "p").status_code == 302
        assert client.get("/dashboard").status_code == 200

        stub.get_user_by_id = lambda _uid: {
            "id": _uid,
            "role": "super_admin",
            "username": "tester",
            "full_name": "Tester",
            "cvo_office": None,
            "phone": None,
            "email": None,
            "profile_photo": None,
            "session_version": 1,
            "is_active": True,
        }
        login_as(client, role="super_admin")
        assert client.get("/petitions").status_code == 200
        assert client.get("/petitions/1").status_code == 200
        assert client.get("/users").status_code == 200
        assert client.get("/api/inspectors/2").status_code == 200
        assert client.get("/api/stats").status_code == 200
        assert client.get("/api/dashboard-drilldown?metric=status:received").status_code == 200
        assert client.get("/healthz").status_code == 200
        assert client.get("/e-receipts/missing.pdf").status_code in (200, 404)
        assert client.get("/enquiry-files/missing.pdf").status_code in (200, 404)


def test_login_session_cookie_is_opaque(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    app_module.TEST_SERVER_SESSION_STORE.clear()
    with app_module.app.test_client() as client:
        captcha_token = _issue_login_captcha(client, "482753")
        response = client.post(
            "/login",
            data={
                "username": "tester",
                "password": "p",
                "captcha_answer": "482753",
                "captcha_token": captcha_token,
            },
        )
        assert response.status_code == 302
        set_cookie = response.headers.get("Set-Cookie", "")
        assert "session=" in set_cookie
        assert "super_admin" not in set_cookie
        assert "tester" not in set_cookie
        assert "9000000001" not in set_cookie


def test_anonymous_public_pages_only_create_session_when_login_captcha_state_is_needed(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    app_module.TEST_SERVER_SESSION_STORE.clear()
    with app_module.app.test_client() as client:
        landing = client.get("/")
        assert landing.status_code == 200
        assert "session=" not in (landing.headers.get("Set-Cookie") or "")
        assert not app_module.TEST_SERVER_SESSION_STORE

        login_page = client.get("/login")
        assert login_page.status_code == 200
        assert "session=" in (login_page.headers.get("Set-Cookie") or "")
        assert len(app_module.TEST_SERVER_SESSION_STORE) == 1
        session_record = next(iter(app_module.TEST_SERVER_SESSION_STORE.values()))
        assert session_record.get("user_id") is None
        assert "login_captcha_challenges" in (session_record.get("data") or {})


def test_client_ip_ignores_forwarded_for_by_default(monkeypatch):
    monkeypatch.setattr(app_module.config, "TRUST_PROXY_HEADERS", False, raising=False)
    with app_module.app.test_request_context("/", headers={"X-Forwarded-For": "203.0.113.10"}, environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        assert app_module._client_ip() == "127.0.0.1"


def test_petition_actions_success_paths(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        stub.petition = {"id": 1, "requires_permission": True, "status": "forwarded_to_cvo", "efile_no": None}
        assert _post_action(client, "data_entry", "forward_to_cvo", {"target_cvo": "apspdcl"}).status_code == 302
        assert _post_action(client, "po", "send_for_permission").status_code == 302
        assert _post_action(client, "cvo_apspdcl", "send_receipt_to_po").status_code == 302

        stub.petition = {"id": 1, "requires_permission": True, "status": "sent_for_permission", "efile_no": None}
        assert _post_action(
            client,
            "po",
            "approve_permission",
            {"target_cvo": "apspdcl", "enquiry_type_decision": "preliminary", "efile_no": "EO-1"},
        ).status_code == 302
        assert _post_action(client, "po", "reject_permission", {"comments": "no"}).status_code == 302

        stub.petition = {"id": 1, "requires_permission": False, "status": "forwarded_to_cvo", "efile_no": None}
        assert _post_action(
            client,
            "cvo_apspdcl",
            "assign_inspector",
            {"inspector_id": "8", "enquiry_type_decision": "detailed"},
        ).status_code == 302

        assert _post_action(
            client,
            "inspector",
            "submit_report",
            {"report_text": "ok", "recommendation": "rec", "report_file": _pdf("rep.pdf")},
            multipart=True,
        ).status_code == 302

        assert _post_action(
            client,
            "cvo_apspdcl",
            "cvo_comments",
            {"cvo_comments": "remarks", "consolidated_report_file": _pdf("cvo.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "cvo_apspdcl",
            "cvo_send_back_reenquiry",
            {"inspector_id": "8", "comments": "redo enquiry"},
        ).status_code == 302

        stub.petition = {"id": 1, "status": "enquiry_report_submitted", "enquiry_type": "preliminary", "efile_no": None}
        assert _post_action(
            client,
            "cvo_apspdcl",
            "upload_consolidated_report",
            {"consolidated_report_file": _pdf("cc.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "cvo_apspdcl",
            "request_detailed_enquiry",
            {"cvo_comments": "need details"},
        ).status_code == 302

        stub.petition = {"id": 1, "status": "forwarded_to_po", "efile_no": None, "requires_permission": False}
        assert _post_action(
            client,
            "po",
            "po_send_back_reenquiry",
            {"comments": "insufficient report"},
        ).status_code == 302
        assert _post_action(
            client,
            "po",
            "give_conclusion",
            {"efile_no": "EO-2", "final_conclusion": "done", "instructions": "ok", "conclusion_file": _pdf("po.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(client, "po", "send_to_cmd", {"efile_no": "EO-2", "cmd_instructions": "act", "cmd_handler_id": "6"}).status_code == 302
        assert _post_action(client, "po", "update_efile_no", {"efile_no": "EO-3"}).status_code == 302
        assert _post_action(
            client,
            "cmd_apspdcl",
            "cmd_submit_action_report",
            {"action_taken": "taken", "action_report_file": _pdf("ar.pdf")},
            multipart=True,
        ).status_code == 302

        stub.petition = {"id": 1, "status": "action_taken", "efile_no": None}
        assert _post_action(client, "po", "po_lodge", {"lodge_remarks": "lodge", "efile_no": "EO-4"}).status_code == 302
        stub.petition = {"id": 1, "status": "sent_for_permission", "efile_no": None}
        assert _post_action(client, "po", "po_direct_lodge", {"lodge_remarks": "lodge", "efile_no": "EO-5"}).status_code == 302
        stub.petition = {"id": 1, "status": "lodged", "efile_no": "EO-5"}
        assert _post_action(client, "po", "close", {"comments": "close"}).status_code == 302


def test_petition_actions_validation_and_error_paths(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        stub.petition = {"id": 1, "requires_permission": False, "status": "forwarded_to_cvo", "efile_no": "EO-1"}
        assert _post_action(client, "po", "approve_permission", {"target_cvo": "bad", "enquiry_type_decision": "bad"}).status_code == 302
        assert _post_action(client, "po", "update_efile_no", {"efile_no": "X" * 101}).status_code == 302
        assert _post_action(client, "po", "po_direct_lodge", {"lodge_remarks": "x" * 6000}).status_code == 302
        assert _post_action(client, "po", "close", {"comments": "x" * 6000}).status_code == 302
        assert _post_action(client, "po", "unsupported_action").status_code == 302


def test_form_and_user_management_routes(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")
        assert client.get("/form-management").status_code == 200
        assert client.post(
            "/form-management",
            data={
                "form_key": "deo_petition",
                "field_key": "subject",
                "label": "Subject",
                "field_type": "textarea",
                "is_required": "on",
                "options_text": "",
            },
        ).status_code == 302

        assert client.post(
            "/users/new",
            data={
                "username": "testuser",
                "password": "secret123",
                "full_name": "Test User",
                "role": "po",
            },
        ).status_code == 302

        csv_data = io.BytesIO(
            b"username,password,full_name,role,cvo_office,assigned_cvo_username\n"
            b"ins1,secret1,Inspector One,inspector,apspdcl,cvo_user\n"
        )
        assert client.post(
            "/users/upload",
            data={"users_file": (csv_data, "users.csv")},
            content_type="multipart/form-data",
        ).status_code == 302

        assert client.post("/users/1/toggle").status_code == 302
        assert client.post(
            "/users/1/edit",
            data={"full_name": "Edit User", "role": "po", "phone": "+919999999999", "email": "a@b.com"},
        ).status_code == 302
        assert client.post("/users/1/reset-password", data={"new_password": "secret123"}).status_code == 302
        assert client.post("/users/1/reset-username", data={"new_username": "new.user"}).status_code == 302
        assert client.post("/users/1/update-name", data={"full_name": "Updated Name"}).status_code == 302
        assert client.post("/users/8/map-cvo", data={"cvo_id": "2"}).status_code == 302


def test_inactive_help_resource_file_is_hidden_from_non_admin(monkeypatch):
    stub = RichModelsStub()
    stub.get_help_resource_by_file_name = lambda _filename: {
        "id": 44,
        "file_name": "manual.pdf",
        "is_active": False,
    }
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="data_entry")
        response = client.get("/help-resources/files/manual.pdf")
        assert response.status_code == 404


def test_help_resource_svg_is_forced_download(monkeypatch):
    stub = RichModelsStub()
    stub.get_help_resource_by_file_name = lambda _filename: {
        "id": 45,
        "file_name": "diagram.svg",
        "mime_type": "image/svg+xml",
        "is_active": True,
    }
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(app_module, "_uploaded_file_exists", lambda *_a, **_k: True)
    sent = {}
    monkeypatch.setattr(
        app_module,
        "send_from_directory",
        lambda directory, filename, as_attachment=False: sent.update(
            {"directory": directory, "filename": filename, "as_attachment": as_attachment}
        ) or app_module.Response("ok", status=200),
    )
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="po")
        response = client.get("/help-resources/files/diagram.svg")
        assert response.status_code == 200
        assert sent["filename"] == "diagram.svg"
        assert sent["as_attachment"] is True


def test_validate_help_resource_upload_rejects_svg():
    upload = io.BytesIO(b"<svg></svg>")
    upload.filename = "diagram.svg"
    ok, stored_name, mime_type, error = app_module.validate_help_resource_upload(upload)
    assert ok is False
    assert stored_name is None
    assert mime_type is None
    assert "not supported" in error.lower()


def test_petition_new_validation_matrix(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="data_entry")
        base = {
            "received_date": "2026-02-17",
            "received_at": "jmd_office",
            "petitioner_name": "Anonymous",
            "contact": "+919999999999",
            "place": "Hyd",
            "subject": "Test",
            "petition_type": "bribe",
            "source_of_petition": "media",
            "remarks": "ok",
        }
        assert client.get("/petitions/new").status_code == 200

        bad_cases = [
            {"received_date": ""},
            {"received_at": "invalid"},
            {"subject": ""},
            {"petition_type": "invalid"},
            {"source_of_petition": "invalid"},
            {"contact": "bad-phone"},
            {"remarks": "x" * 5001},
            {"source_of_petition": "govt", "govt_institution_type": ""},
            {"source_of_petition": "govt", "govt_institution_type": "bad"},
        ]
        for patch in bad_cases:
            payload = dict(base)
            payload.update(patch)
            resp = client.post("/petitions/new", data=payload)
            assert resp.status_code == 200

        non_jmd = dict(base)
        non_jmd.update(
            {
                "received_at": "cvo_apspdcl_tirupathi",
                "target_cvo": "apspdcl",
                "permission_request_type": "direct_enquiry",
                "ereceipt_no": "ER-1001",
                "ereceipt_file": _pdf("deo.pdf"),
            }
        )
        assert client.post("/petitions/new", data=non_jmd, content_type="multipart/form-data").status_code == 302

        jmd_ok = dict(base)
        jmd_ok["ereceipt_file"] = _pdf("deo2.pdf")
        assert client.post("/petitions/new", data=jmd_ok, content_type="multipart/form-data").status_code == 200


def test_petition_new_rate_limit_blocks_burst_submissions(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(app_module.config, "PETITION_USER_RATE_LIMIT_WINDOW_SECONDS", 300, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_USER_RATE_LIMIT_MAX_SUBMISSIONS", 1, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_USER_RATE_LIMIT_BLOCK_SECONDS", 300, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_IP_RATE_LIMIT_WINDOW_SECONDS", 300, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_IP_RATE_LIMIT_MAX_SUBMISSIONS", 50, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_IP_RATE_LIMIT_BLOCK_SECONDS", 180, raising=False)
    app_module.PETITION_SUBMISSION_ATTEMPTS.clear()
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="data_entry")
        payload = {
            "received_date": "2026-02-17",
            "received_at": "cvo_apspdcl_tirupathi",
            "petitioner_name": "Petitioner One",
            "contact": "+919999999999",
            "place": "Hyd",
            "subject": "Test burst petition",
            "petition_type": "bribe",
            "source_of_petition": "media",
            "remarks": "ok",
            "target_cvo": "apspdcl",
            "permission_request_type": "direct_enquiry",
            "ereceipt_no": "ER-1001",
        }
        first_payload = dict(payload)
        first_payload["ereceipt_file"] = _pdf("deo.pdf")
        assert client.post("/petitions/new", data=first_payload, content_type="multipart/form-data").status_code == 302
        second_payload = dict(payload)
        second_payload["ereceipt_file"] = _pdf("deo.pdf")
        second = client.post("/petitions/new", data=second_payload, content_type="multipart/form-data")
        assert second.status_code == 429


def test_petition_new_ip_limit_allows_parallel_users_until_ip_threshold(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(app_module.config, "PETITION_USER_RATE_LIMIT_WINDOW_SECONDS", 300, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_USER_RATE_LIMIT_MAX_SUBMISSIONS", 10, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_USER_RATE_LIMIT_BLOCK_SECONDS", 300, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_IP_RATE_LIMIT_WINDOW_SECONDS", 300, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_IP_RATE_LIMIT_MAX_SUBMISSIONS", 2, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_IP_RATE_LIMIT_BLOCK_SECONDS", 180, raising=False)
    app_module.PETITION_SUBMISSION_ATTEMPTS.clear()
    app_module.app.config["TESTING"] = True
    base_payload = {
        "received_date": "2026-02-17",
        "received_at": "cvo_apspdcl_tirupathi",
        "petitioner_name": "Petitioner One",
        "contact": "+919999999999",
        "place": "Hyd",
        "subject": "Shared IP petition",
        "petition_type": "bribe",
        "source_of_petition": "media",
        "remarks": "ok",
        "target_cvo": "apspdcl",
        "permission_request_type": "direct_enquiry",
        "ereceipt_no": "ER-1002",
    }
    with app_module.app.test_client() as client_a:
        login_as(client_a, user_id=11, role="data_entry", full_name="DEO One", cvo_office="apspdcl")
        payload_a = dict(base_payload)
        payload_a["ereceipt_file"] = _pdf("deo-a.pdf")
        assert client_a.post("/petitions/new", data=payload_a, content_type="multipart/form-data").status_code == 302
    with app_module.app.test_client() as client_b:
        login_as(client_b, user_id=12, role="data_entry", full_name="DEO Two", cvo_office="apspdcl")
        payload_b = dict(base_payload)
        payload_b["ereceipt_file"] = _pdf("deo-b.pdf")
        assert client_b.post("/petitions/new", data=payload_b, content_type="multipart/form-data").status_code == 302
    with app_module.app.test_client() as client_c:
        login_as(client_c, user_id=13, role="data_entry", full_name="DEO Three", cvo_office="apspdcl")
        payload_c = dict(base_payload)
        payload_c["ereceipt_file"] = _pdf("deo-c.pdf")
        third = client_c.post("/petitions/new", data=payload_c, content_type="multipart/form-data")
        assert third.status_code == 429


def test_petitions_import_routes_and_upload_paths(monkeypatch):
    stub = RichModelsStub()
    stub.get_all_users = lambda: [
        {"id": 5, "username": "cvo.user", "role": "cvo_apspdcl", "is_active": True},
        {"id": 6, "username": "insp.user", "role": "inspector", "is_active": True},
        {"id": 7, "username": "cmd.user", "role": "cmd_apspdcl", "is_active": True},
    ]
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        login_as(client, role="po")
        page = client.get("/petitions/import")
        assert page.status_code == 200
        assert "assigned_inspector_username" in page.get_data(as_text=True)

        template = client.get("/petitions/import/template")
        assert template.status_code == 200
        assert template.mimetype == "text/csv"
        assert "attachment; filename=petition_bulk_import_template.csv" in template.headers["Content-Disposition"]
        assert "received_date,received_at,target_cvo" in template.get_data(as_text=True)

        assert client.post("/petitions/import/upload", data={}).status_code == 302

        monkeypatch.setattr(app_module, "_parse_tabular_upload_rows", lambda *_a, **_k: [])
        assert client.post(
            "/petitions/import/upload",
            data={"petitions_file": (io.BytesIO(b"x"), "petitions.csv")},
            content_type="multipart/form-data",
        ).status_code == 302

        def raising_parser(*_a, **_k):
            raise ValueError("bad upload")

        monkeypatch.setattr(app_module, "_parse_tabular_upload_rows", raising_parser)
        assert client.post(
            "/petitions/import/upload",
            data={"petitions_file": (io.BytesIO(b"x"), "petitions.xlsx")},
            content_type="multipart/form-data",
        ).status_code == 302

        monkeypatch.setattr(
            app_module,
            "_parse_tabular_upload_rows",
            lambda *_a, **_k: [
                {
                    "received_date": "2026-02-17",
                    "received_at": "jmd_office",
                    "target_cvo": "headquarters",
                    "petitioner_name": "Imported One",
                    "contact": "9999999999",
                    "place": "Hyd",
                    "subject": "Imported subject",
                    "petition_type": "bribe",
                    "source_of_petition": "govt",
                    "govt_institution_type": "bad",
                    "enquiry_type": "preliminary",
                    "permission_request_type": "direct_enquiry",
                    "requires_permission": "no",
                    "permission_status": "",
                    "status": "permission_rejected",
                    "assigned_inspector_username": "insp.user",
                    "remarks": "row one",
                },
                {
                    "received_date": "2026-02-18",
                    "received_at": "cvo_apcpdcl_vijayawada",
                    "target_cvo": "",
                    "petitioner_name": "Imported Two",
                    "contact": "8888888888",
                    "place": "VJA",
                    "subject": "Imported subject 2",
                    "petition_type": "other",
                    "source_of_petition": "public_individual",
                    "govt_institution_type": "",
                    "enquiry_type": "detailed",
                    "permission_request_type": "permission_required",
                    "requires_permission": "yes",
                    "permission_status": "pending",
                    "status": "bad_status",
                    "assigned_inspector_username": "missing.user",
                    "remarks": "row two",
                },
            ],
        )
        response = client.post(
            "/petitions/import/upload",
            data={"petitions_file": (io.BytesIO(b"ok"), "petitions.csv"), "_return_to": "help"},
            content_type="multipart/form-data",
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/help")
        call_names = [name for name, _ in stub.calls]
        assert call_names.count("create_petition") == 2
        assert call_names.count("update_imported_petition_state") == 2


def test_petition_view_with_files_and_super_admin_handler_scope(monkeypatch):
    stub = RichModelsStub()
    seen = {"cvo_lookup": 0}
    stub.petition = {
        "id": 1,
        "requires_permission": False,
        "status": "permission_approved",
        "efile_no": "EO-1",
        "enquiry_type": "preliminary",
        "target_cvo": "apspdcl",
        "current_handler_id": 42,
        "assigned_inspector_id": 8,
        "ereceipt_file": "ereceipt.pdf",
        "conclusion_file": "conclusion.pdf",
    }
    stub.get_petition_tracking = lambda _pid: [
        {
            "action": "Inspector Requested Detailed Enquiry Permission",
            "attachment_file": None,
            "created_at": None,
        },
        {
            "action": "Assigned to Inspector",
            "attachment_file": "memo.pdf",
            "from_name": "CVO Officer",
            "created_at": datetime(2026, 2, 17, 10, 0),
            "comments": "Please enquire",
        },
    ]
    stub.get_enquiry_report = lambda _pid: {
        "id": 99,
        "report_file": "report.pdf",
        "cvo_consolidated_report_file": "consolidated.pdf",
        "cmd_action_report_file": "cmd.pdf",
    }
    stub.get_inspectors_by_cvo = lambda _uid: seen.__setitem__("cvo_lookup", seen["cvo_lookup"] + 1) or [{"id": 8, "full_name": "Inspector"}]
    stub.get_user_by_id = lambda uid: {
        "id": uid,
        "role": "cvo_apspdcl",
        "username": "cvo.user",
        "full_name": "CVO Officer",
        "cvo_office": "apspdcl",
        "phone": None,
        "email": None,
        "profile_photo": None,
        "session_version": 1,
        "is_active": True,
    }
    stub.get_sla_evaluation_rows = lambda _rows: [
        {"is_beyond_sla_for_po": True, "closed_at": None}
    ]
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(app_module, "_uploaded_file_exists", lambda _base, name: name != "cmd.pdf")
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")
        response = client.get("/petitions/1")
        assert response.status_code == 200
        assert seen["cvo_lookup"] == 1


def test_petition_view_guard_and_cvo_scope_branches(monkeypatch):
    stub = RichModelsStub()
    stub.get_petition_by_id = lambda _pid: None
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        login_as(client, role="po")
        monkeypatch.setattr(app_module, "_can_access_petition", lambda petition_id: False)
        assert client.get("/petitions/1").status_code == 302

        monkeypatch.setattr(app_module, "_can_access_petition", lambda petition_id: True)
        assert client.get("/petitions/1").status_code == 302

    stub.petition = {
        "id": 1,
        "requires_permission": False,
        "status": "forwarded_to_cvo",
        "efile_no": None,
        "enquiry_type": "detailed",
        "target_cvo": "apspdcl",
        "current_handler_id": None,
    }
    stub.get_petition_tracking = lambda _pid: []
    stub.get_enquiry_report = lambda _pid: None
    stub.get_inspectors_by_cvo = lambda _uid: [{"id": 8, "full_name": "Inspector"}]
    stub.get_sla_evaluation_rows = lambda _rows: (_ for _ in ()).throw(Exception("sla fail"))
    stub.get_user_by_id = lambda _uid: {
        "id": _uid,
        "role": "cvo_apspdcl",
        "username": "cvo.user",
        "full_name": "CVO User",
        "cvo_office": "apspdcl",
        "phone": None,
        "email": None,
        "profile_photo": None,
        "session_version": 1,
        "is_active": True,
    }
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(app_module, "_can_access_petition", lambda petition_id: True)
    with app_module.app.test_client() as client:
        login_as(client, role="cvo_apspdcl")
        assert client.get("/petitions/1").status_code in (200, 302)


def test_petition_action_additional_success_branches(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        stub.petition = {"id": 1, "status": "forwarded_to_cvo", "requires_permission": False}
        assert _post_action(client, "cvo_apspdcl", "cvo_set_enquiry_mode", {"permission_request_type": "direct_enquiry", "enquiry_type_decision": "preliminary"}).status_code == 302

        stub.petition = {"id": 1, "status": "forwarded_to_cvo", "requires_permission": False}
        assert _post_action(
            client,
            "cvo_apspdcl",
            "cvo_route_petition",
            {
                "permission_request_type": "direct_enquiry",
                "enquiry_type_decision": "detailed",
                "inspector_id": "8",
                "assignment_memo_file": _pdf("memo.pdf"),
            },
            multipart=True,
        ).status_code == 302

        stub.petition = {"id": 1, "status": "forwarded_to_cvo", "requires_permission": False}
        assert _post_action(
            client,
            "cvo_apspdcl",
            "send_receipt_to_po",
            {
                "permission_file": _pdf("permission.pdf"),
            },
            multipart=True,
        ).status_code == 302

        stub.petition = {"id": 1, "status": "enquiry_report_submitted", "source_of_petition": "media"}
        assert _post_action(client, "cvo_apspdcl", "cvo_direct_lodge", {"lodge_remarks": "Media lodge"}).status_code == 302

        stub.petition = {
            "id": 1,
            "status": "forwarded_to_cvo",
            "target_cvo": "apspdcl",
            "received_at": "cvo_apspdcl_tirupathi",
            "enquiry_type": "detailed",
            "efile_no": None,
        }
        stub.get_sla_evaluation_rows = lambda _rows: [{"is_beyond_sla_for_po": True, "closed_at": None}]
        assert _post_action(
            client,
            "po",
            "po_beyond_sla_send_to_cvo",
            {"target_cvo": "apspdcl", "efile_no": "EO-9", "permission_file": _pdf("beyond.pdf")},
            multipart=True,
        ).status_code == 302

        call_names = [name for name, _ in stub.calls]
        assert "cvo_mark_direct_enquiry" in call_names
        assert "assign_to_inspector" in call_names
        assert "cvo_send_receipt_to_po" in call_names
        assert "cvo_direct_lodge_petition" in call_names
        assert "approve_permission" in call_names


def test_system_settings_page_and_save(monkeypatch):
    stub = RichModelsStub()
    stub.system_settings = {
        "petition_user_rate_limit_max_submissions": "12",
        "petition_ip_rate_limit_max_submissions": "75",
    }
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")
        response = client.get("/system-settings")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "System Settings" in body
        assert 'value="12"' in body
        assert 'value="75"' in body

        post_response = client.post(
            "/system-settings",
            data={
                "petition_user_rate_limit_window_seconds": "420",
                "petition_user_rate_limit_max_submissions": "14",
                "petition_user_rate_limit_block_seconds": "360",
                "petition_ip_rate_limit_window_seconds": "420",
                "petition_ip_rate_limit_max_submissions": "90",
                "petition_ip_rate_limit_block_seconds": "240",
            },
        )
        assert post_response.status_code == 302
        assert stub.system_settings["petition_user_rate_limit_max_submissions"] == "14"
        assert stub.system_settings["petition_ip_rate_limit_max_submissions"] == "90"
        assert any(call[0] == "upsert_system_settings" for call in stub.calls)


def test_effective_system_settings_use_database_overrides(monkeypatch):
    stub = RichModelsStub()
    stub.system_settings = {
        "petition_user_rate_limit_window_seconds": "480",
        "petition_user_rate_limit_max_submissions": "15",
        "petition_user_rate_limit_block_seconds": "420",
        "petition_ip_rate_limit_window_seconds": "540",
        "petition_ip_rate_limit_max_submissions": "95",
        "petition_ip_rate_limit_block_seconds": "300",
    }
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(app_module.config, "PETITION_USER_RATE_LIMIT_MAX_SUBMISSIONS", 10, raising=False)
    monkeypatch.setattr(app_module.config, "PETITION_IP_RATE_LIMIT_MAX_SUBMISSIONS", 60, raising=False)

    with app_module.app.test_request_context("/petitions/new"):
        effective = app_module.get_effective_system_settings()
        assert effective["petition_user_rate_limit_max_submissions"] == 15
        assert effective["petition_ip_rate_limit_max_submissions"] == 95
        user_settings = app_module._petition_rate_limit_settings("user")
        ip_settings = app_module._petition_rate_limit_settings("ip")
        assert user_settings["window_seconds"] == 480
        assert user_settings["max_submissions"] == 15
        assert user_settings["block_seconds"] == 420
        assert ip_settings["window_seconds"] == 540
        assert ip_settings["max_submissions"] == 95
        assert ip_settings["block_seconds"] == 300


def test_inactive_authenticated_session_forces_relogin(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")
        with client.session_transaction() as sess:
            sess["auth_last_seen_at"] = int(time.time()) - (app_module.config.SESSION_LIFETIME_MINUTES * 60) - 5
        response = client.get("/users")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


def test_role_required_uses_refreshed_user_role(monkeypatch):
    stub = RichModelsStub()
    stub.get_user_by_id = lambda _uid: {
        "id": _uid,
        "username": "tester",
        "full_name": "Tester",
        "role": "data_entry",
        "cvo_office": "apspdcl",
        "phone": None,
        "email": None,
        "profile_photo": None,
        "session_version": 1,
        "is_active": True,
    }
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")
        response = client.get("/users")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/dashboard")


def test_user_and_upload_validation_paths(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")

        assert client.post("/users/new", data={"username": "ab"}).status_code == 302
        assert client.post(
            "/users/new",
            data={
                "username": "uvalid",
                "password": "secret123",
                "full_name": "CV One",
                "role": "cvo_apspdcl",
                "cvo_office": "",
            },
        ).status_code == 302
        assert client.post(
            "/users/new",
            data={
                "username": "insuser",
                "password": "secret123",
                "full_name": "Ins User",
                "role": "inspector",
                "cvo_office": "apspdcl",
                "assigned_cvo_id": "",
            },
        ).status_code == 302

        assert client.post(
            "/users/1/edit",
            data={"full_name": "Ed", "role": "po"},
        ).status_code == 302
        assert client.post("/users/1/reset-password", data={"new_password": "x"}).status_code == 302
        assert client.post("/users/1/reset-username", data={"new_username": "??"}).status_code == 302
        assert client.post("/users/1/update-name", data={"full_name": "x"}).status_code == 302
        assert client.post("/users/8/map-cvo", data={"cvo_id": "bad"}).status_code == 302

        assert client.post("/users/upload", data={}).status_code == 302
        bad_ext = io.BytesIO(b"dummy")
        assert client.post(
            "/users/upload",
            data={"users_file": (bad_ext, "bad.txt")},
            content_type="multipart/form-data",
        ).status_code == 302
        bad_csv = io.BytesIO(b"a,b\n1,2\n")
        assert client.post(
            "/users/upload",
            data={"users_file": (bad_csv, "users.csv")},
            content_type="multipart/form-data",
        ).status_code == 302


def test_profile_password_change_refreshes_session(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")
        response = client.post(
            "/profile",
            data={
                "full_name": "Test User",
                "username": "tester",
                "phone": "",
                "email": "",
                "current_password": "OldPass@9!",
                "new_password": "NewPass@9!",
                "confirm_password": "NewPass@9!",
            },
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/profile")
        with client.session_transaction() as sess:
            assert sess.get("user_id") == 1


def test_profile_password_change_requires_current_password(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")
        response = client.post(
            "/profile",
            data={
                "full_name": "Test User",
                "username": "tester",
                "phone": "",
                "email": "",
                "new_password": "NewPass@9!",
                "confirm_password": "NewPass@9!",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Current password is required" in response.data


def test_profile_password_change_rejects_wrong_current_password(monkeypatch):
    stub = RichModelsStub()
    stub.authenticate_user = lambda _u, _p: None
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")
        response = client.post(
            "/profile",
            data={
                "full_name": "Test User",
                "username": "tester",
                "phone": "",
                "email": "",
                "current_password": "WrongPass@9!",
                "new_password": "NewPass@9!",
                "confirm_password": "NewPass@9!",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Current password is incorrect." in response.data


def test_help_page_admin_upload_toggle_and_external_url(monkeypatch):
    stub = RichModelsStub()
    stub.list_help_resources = lambda active_only=False: [
        {
            "id": 1,
            "title": "Manual",
            "resource_type": "manual",
            "storage_kind": "upload",
            "file_name": "manual.pdf",
            "mime_type": "application/pdf",
            "is_active": True,
        },
        {
            "id": 2,
            "title": "Video",
            "resource_type": "video",
            "storage_kind": "external_url",
            "external_url": "https://example.com/video",
            "file_name": None,
            "mime_type": None,
            "is_active": False,
        },
    ]
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="po")
        assert client.get("/help-center").status_code == 302
        page = client.get("/help")
        assert page.status_code == 200

        assert client.post("/help", data={"action": "toggle_active", "resource_id": "", "activate": "1"}).status_code == 302
        assert client.post("/help", data={"action": "toggle_active", "resource_id": "1", "activate": "1"}).status_code == 302
        assert any(name == "set_help_resource_active" for name, _ in stub.calls)

        assert client.post("/help", data={"title": "", "resource_type": "manual", "storage_kind": "upload"}).status_code == 302
        assert client.post("/help", data={"title": "Guide", "resource_type": "bad", "storage_kind": "upload"}).status_code == 302
        assert client.post("/help", data={"title": "Guide", "resource_type": "manual", "storage_kind": "bad"}).status_code == 302
        assert client.post("/help", data={"title": "Guide", "resource_type": "manual", "storage_kind": "external_url", "external_url": "notaurl"}).status_code == 302

        assert client.post(
            "/help",
            data={"title": "External Guide", "resource_type": "manual", "storage_kind": "external_url", "external_url": "https://example.com/guide", "display_order": "2"},
        ).status_code == 302
        assert any(name == "create_help_resource" for name, _ in stub.calls)


def test_password_reset_approval_and_rejection_routes(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")
        assert client.post("/users/password-reset-requests/6/approve").status_code == 302
        assert client.post("/users/password-reset-requests/6/reject", data={"decision_notes": "reject"}).status_code == 302

        call_names = [name for name, _ in stub.calls]
        assert "approve_password_reset_request" in call_names
        assert "reject_password_reset_request" in call_names


def test_user_update_contact_and_profile_photo_paths(monkeypatch):
    stub = RichModelsStub()
    user_rows = {
        1: {
            "id": 1,
            "role": "super_admin",
            "username": "tester",
            "full_name": "Tester",
            "cvo_office": None,
            "phone": "9999999999",
            "email": "old@example.com",
            "profile_photo": "old.png",
            "session_version": 1,
            "is_active": True,
        }
    }
    stub.get_user_by_id = lambda uid: dict(user_rows.get(uid)) if uid in user_rows else None
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")
        assert client.post("/users/1/update-contact", data={"phone": "bad"}).status_code == 302
        assert client.post("/users/1/update-contact", data={"phone": "9999999999", "email": "bad"}).status_code == 302
        assert client.post("/users/77/update-contact", data={"phone": "9999999999", "email": "a@b.com"}).status_code == 302

        response = client.post(
            "/users/1/update-contact",
            data={"phone": "9999999999", "email": "a@b.com", "remove_photo": "on"},
        )
        assert response.status_code == 302
        call_names = [name for name, _ in stub.calls]
        assert "update_user_profile_info" in call_names
        assert "set_user_profile_photo" in call_names

        response = client.post(
            "/users/1/update-contact",
            data={"phone": "9999999999", "email": "a@b.com", "profile_photo": (io.BytesIO(b"png"), "avatar.png")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 302


def test_api_dashboard_and_petitioner_helpers(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(
        app_module,
        "get_petitions_for_user_cached",
        lambda *_a, **_k: [
            {
                "id": 1,
                "sno": "VIG/1",
                "petitioner_name": "Ravi Kumar",
                "subject": "Transformer issue",
                "status": "received",
                "received_date": date(2026, 2, 17),
                "petition_type": "electrical_accident",
                "source_of_petition": "media",
                "received_at": "jmd_office",
                "target_cvo": "apspdcl",
                "assigned_inspector_id": 8,
                "inspector_name": "Inspector One",
            },
            {
                "id": 2,
                "sno": "VIG/2",
                "petitioner_name": "Ravi Kumar",
                "subject": "Billing issue",
                "status": "closed",
                "received_date": date(2026, 2, 18),
                "petition_type": "bribe",
                "source_of_petition": "public_individual",
                "received_at": "jmd_office",
                "target_cvo": "apspdcl",
                "assigned_inspector_id": 8,
                "inspector_name": "Inspector One",
            },
            {
                "id": 3,
                "sno": "VIG/3",
                "petitioner_name": "Anonymous",
                "subject": "Ignore",
                "status": "closed",
                "received_date": date(2026, 2, 18),
                "petition_type": "other",
                "source_of_petition": "public_individual",
                "received_at": "jmd_office",
                "target_cvo": "apspdcl",
            },
        ],
    )
    monkeypatch.setattr(app_module, "_build_petitioner_profile_payload", lambda petitions, name: {"name": name, "total": len(petitions)})
    stub.get_latest_enquiry_report_accident_details = lambda ids: {1: {"accident_type": "fatal", "deceased_category": "departmental", "departmental_type": "regular", "deceased_count": 1}}
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="po")
        analytics = client.get("/api/dashboard-analytics?petition_type=bribe")
        assert analytics.status_code == 200
        assert "analytics" in analytics.get_json()

        short = client.get("/api/petitioner-suggestions?q=r")
        assert short.status_code == 200
        assert short.get_json()["items"] == []

        suggestions = client.get("/api/petitioner-suggestions?q=ra")
        assert suggestions.status_code == 200
        assert suggestions.get_json()["items"][0]["name"] == "Ravi Kumar"

        missing = client.get("/api/petitioner-profile")
        assert missing.status_code == 400

        profile = client.get("/api/petitioner-profile?name=Ravi Kumar")
        assert profile.status_code == 200
        assert profile.get_json()["name"] == "Ravi Kumar"


def test_api_inspectors_forbidden_and_profile_photo_missing(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(
        app_module,
        "_can_access_cvo_scope",
        lambda cvo_id: False if cvo_id == 99 else True,
    )
    monkeypatch.setattr(app_module, "_uploaded_file_exists", lambda _base, _name: False)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="data_entry")
        forbidden = client.get("/api/inspectors/99")
        assert forbidden.status_code == 403

        photo = client.get("/profile-photos/missing.png")
        assert photo.status_code == 403


def test_misc_auth_and_api_edge_paths(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        stub.user = None
        assert _post_login(client, "bad", "bad").status_code == 200
        stub.user = {"id": 1, "username": "u", "full_name": "JMD", "role": "jmd"}
        assert _post_login(client, "u", "p").status_code == 302
        stub.user = {"id": 1, "username": "u", "full_name": "A", "role": "po", "cvo_office": None}
        assert _post_login(client, "u", "p").status_code == 302

        login_as(client, role="po")
        assert client.get("/api/dashboard-drilldown").status_code == 200
        assert client.get("/logout").status_code == 302


def test_safe_internal_redirect_target_rejects_external_urls():
    with app_module.app.test_request_context('/login'):
        assert app_module._safe_internal_redirect_target('https://evil.example/phish', 'dashboard') == '/dashboard'
        assert app_module._safe_internal_redirect_target('//evil.example/phish', 'dashboard') == '/dashboard'
        assert app_module._safe_internal_redirect_target('/petitions?status=all', 'dashboard') == '/petitions?status=all'


def test_login_page_does_not_embed_captcha_answer_in_html():
    app_module.LOGIN_CAPTCHA_CHALLENGES.clear()
    app_module.LOGIN_CAPTCHA_USED_TOKENS.clear()
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        response = client.get("/login")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'data:image/bmp;base64,' in html
        assert '482753' not in html


def test_login_captcha_image_is_served_from_session_state():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        captcha_token = _issue_login_captcha(client, "482753")
        response = client.get(f"/auth/login-captcha/{captcha_token}")
        assert response.status_code == 200
        assert response.mimetype == "image/bmp"
        assert response.headers["Cache-Control"].startswith("no-store")


def test_login_page_generated_captcha_survives_to_next_request(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(stub, "authenticate_user", lambda _u, _p: None)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        response = client.get("/login")
        assert response.status_code == 200
        with client.session_transaction() as sess:
            challenges = dict(sess.get("login_captcha_challenges") or {})
            assert challenges
            captcha_token = next(reversed(challenges))
            challenge = dict(challenges[captcha_token])
            challenge["answer_digest"] = app_module._login_captcha_answer_digest(captcha_token, "482753")
            challenge["image_b64"] = app_module.base64.b64encode(
                app_module._build_login_captcha_bmp("482753")
            ).decode("ascii")
            challenges[captcha_token] = challenge
            sess["login_captcha_challenges"] = challenges
        response = client.post(
            "/login",
            data={
                "username": "wrong-user",
                "password": "wrong-pass",
                "captcha_answer": "482753",
                "captcha_token": captcha_token,
            },
        )
        html = response.get_data(as_text=True)
        assert "Captcha answer is incorrect." not in html
        assert "Invalid username or password." in html


def test_login_page_reuses_existing_captcha_until_refresh_requested():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        response = client.get("/login")
        assert response.status_code == 200
        with client.session_transaction() as sess:
            challenges = dict(sess.get("login_captcha_challenges") or {})
            assert len(challenges) == 1
            first_token = next(reversed(challenges))
        response = client.get("/login")
        assert response.status_code == 200
        with client.session_transaction() as sess:
            challenges = dict(sess.get("login_captcha_challenges") or {})
            assert len(challenges) == 1
            assert next(reversed(challenges)) == first_token
        response = client.get("/login?refresh_captcha=1")
        assert response.status_code == 200
        with client.session_transaction() as sess:
            challenges = dict(sess.get("login_captcha_challenges") or {})
            assert len(challenges) == 1
            assert next(reversed(challenges)) != first_token


def test_login_page_captcha_validates_even_if_challenge_store_is_cleared(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(stub, "authenticate_user", lambda _u, _p: None)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        response = client.get("/login")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        token_match = app_module.re.search(r'name="captcha_token" value="([^"]+)"', html)
        proof_match = app_module.re.search(r'name="captcha_proof" value="([^"]+)"', html)
        assert token_match
        assert proof_match
        captcha_token = token_match.group(1)
        captcha_proof = proof_match.group(1)
        with client.session_transaction() as sess:
            challenges = dict(sess.get("login_captcha_challenges") or {})
            assert challenges
            challenge = dict(challenges[captcha_token])
            challenge["answer_digest"] = app_module._login_captcha_answer_digest(captcha_token, "482753")
            challenge["image_b64"] = app_module.base64.b64encode(
                app_module._build_login_captcha_bmp("482753")
            ).decode("ascii")
            challenge["proof"] = app_module._build_login_captcha_proof(captcha_token, "482753", challenge["issued_at"])
            challenges[captcha_token] = challenge
            sess["login_captcha_challenges"] = {}
            captcha_proof = challenge["proof"]
        response = client.post(
            "/login",
            data={
                "username": "wrong-user",
                "password": "wrong-pass",
                "captcha_answer": "482753",
                "captcha_token": captcha_token,
                "captcha_proof": captcha_proof,
            },
        )
        html = response.get_data(as_text=True)
        assert "Captcha answer is incorrect." not in html
        assert "Invalid username or password." in html


def test_request_entity_too_large_rejects_external_referer(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="data_entry")
        response = client.post(
            "/petitions/new",
            headers={"Referer": "https://evil.example/phish"},
            environ_overrides={"CONTENT_LENGTH": str((app_module.config.MAX_UPLOAD_SIZE_MB * 1024 * 1024) + 1)},
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/petitions")


def test_login_captcha_token_is_single_use():
    app_module.LOGIN_CAPTCHA_USED_TOKENS.clear()
    app_module.LOGIN_CAPTCHA_CHALLENGES.clear()
    with app_module.app.test_request_context("/login"):
        _, captcha_token = app_module.generate_login_captcha("482753")
        assert app_module.validate_login_captcha("482753", captcha_token) is True
        assert app_module.validate_login_captcha("482753", captcha_token) is False


def test_login_captcha_token_expires(monkeypatch):
    app_module.LOGIN_CAPTCHA_USED_TOKENS.clear()
    app_module.LOGIN_CAPTCHA_CHALLENGES.clear()
    now_ts = 1_800_000_000
    with app_module.app.test_request_context("/login"):
        _, captcha_token = app_module.generate_login_captcha(
            "482753",
            issued_at=now_ts - app_module.LOGIN_CAPTCHA_TTL_SECONDS - 1,
        )
        monkeypatch.setattr(app_module.time, "time", lambda: now_ts)
        assert app_module.validate_login_captcha("482753", captcha_token) is False


def test_petition_action_negative_matrix(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="po")
        assert client.post("/petitions/1/action", data={"action": ""}).status_code == 302

        assert _post_action(client, "inspector", "forward_to_cvo", {"target_cvo": "apspdcl"}).status_code == 302
        assert _post_action(client, "data_entry", "forward_to_cvo", {"target_cvo": "bad"}).status_code == 302

        assert _post_action(client, "inspector", "send_for_permission").status_code == 302
        assert _post_action(client, "po", "send_receipt_to_po").status_code == 302
        stub.petition = {"id": 1, "requires_permission": False, "status": "forwarded_to_cvo", "efile_no": None}
        assert _post_action(client, "cvo_apspdcl", "send_receipt_to_po").status_code == 302

        assert _post_action(client, "inspector", "approve_permission").status_code == 302
        stub.petition = None
        assert _post_action(client, "po", "approve_permission", {"target_cvo": "apspdcl", "enquiry_type_decision": "preliminary"}).status_code == 302
        stub.petition = {"id": 1, "requires_permission": True, "status": "sent_for_permission", "efile_no": None}
        assert _post_action(client, "po", "approve_permission", {"target_cvo": "apspdcl", "enquiry_type_decision": "bad"}).status_code == 302
        assert _post_action(client, "po", "approve_permission", {"target_cvo": "apspdcl", "enquiry_type_decision": "preliminary", "efile_no": ""}).status_code == 302

        assert _post_action(client, "inspector", "reject_permission", {"comments": "x"}).status_code == 302
        assert _post_action(client, "po", "reject_permission", {"comments": ""}).status_code == 302

        assert _post_action(client, "po", "assign_inspector", {"inspector_id": "8"}).status_code == 302
        stub.petition = {"id": 1, "requires_permission": True, "status": "forwarded_to_cvo"}
        assert _post_action(client, "cvo_apspdcl", "assign_inspector", {"inspector_id": "8"}).status_code == 302
        stub.petition = {"id": 1, "requires_permission": False, "status": "action_taken"}
        assert _post_action(client, "cvo_apspdcl", "assign_inspector", {"inspector_id": "8"}).status_code == 302
        stub.petition = {"id": 1, "requires_permission": False, "status": "forwarded_to_cvo"}
        assert _post_action(client, "cvo_apspdcl", "assign_inspector", {"inspector_id": "bad"}).status_code == 302
        assert _post_action(client, "cvo_apspdcl", "assign_inspector", {"inspector_id": "8", "enquiry_type_decision": "bad"}).status_code == 302

        assert _post_action(client, "po", "submit_report").status_code == 302
        assert _post_action(client, "inspector", "submit_report", {"report_text": "", "recommendation": "rec"}).status_code == 302
        assert _post_action(client, "inspector", "submit_report", {"report_text": "x" * 20001, "recommendation": "rec"}).status_code == 302
        assert _post_action(client, "inspector", "submit_report", {"report_text": "ok", "recommendation": ""}).status_code == 302
        assert _post_action(client, "inspector", "submit_report", {"report_text": "ok", "recommendation": "x" * 5001}).status_code == 302
        assert _post_action(client, "inspector", "submit_report", {"report_text": "ok", "recommendation": "ok", "report_file": (io.BytesIO(b"txt"), "bad.pdf")}, multipart=True).status_code == 302

        assert _post_action(client, "po", "cvo_comments", {"cvo_comments": "x"}).status_code == 302
        assert _post_action(client, "cvo_apspdcl", "cvo_comments", {"cvo_comments": ""}).status_code == 302
        assert _post_action(client, "cvo_apspdcl", "cvo_comments", {"cvo_comments": "x", "consolidated_report_file": (io.BytesIO(b"txt"), "bad.pdf")}, multipart=True).status_code == 302

        assert _post_action(client, "po", "upload_consolidated_report").status_code == 302
        stub.petition = {"id": 1, "status": "forwarded_to_po"}
        assert _post_action(client, "cvo_apspdcl", "upload_consolidated_report").status_code == 302
        stub.petition = {"id": 1, "status": "enquiry_report_submitted"}
        assert _post_action(client, "cvo_apspdcl", "upload_consolidated_report").status_code == 302
        assert _post_action(client, "cvo_apspdcl", "upload_consolidated_report", {"consolidated_report_file": (io.BytesIO(b"txt"), "bad.pdf")}, multipart=True).status_code == 302

        assert _post_action(client, "po", "request_detailed_enquiry", {"cvo_comments": "x"}).status_code == 302
        stub.petition = {"id": 1, "enquiry_type": "detailed"}
        assert _post_action(client, "cvo_apspdcl", "request_detailed_enquiry", {"cvo_comments": "x"}).status_code == 302
        stub.petition = {"id": 1, "enquiry_type": "preliminary"}
        assert _post_action(client, "cvo_apspdcl", "request_detailed_enquiry", {"cvo_comments": ""}).status_code == 302
        assert _post_action(client, "po", "cvo_send_back_reenquiry", {"inspector_id": "8", "comments": "x"}).status_code == 302
        stub.petition = {"id": 1, "status": "forwarded_to_po"}
        assert _post_action(client, "cvo_apspdcl", "cvo_send_back_reenquiry", {"inspector_id": "8", "comments": "x"}).status_code == 302
        stub.petition = {"id": 1, "status": "enquiry_report_submitted"}
        assert _post_action(client, "cvo_apspdcl", "cvo_send_back_reenquiry", {"inspector_id": "", "comments": "x"}).status_code == 302
        assert _post_action(client, "cvo_apspdcl", "cvo_send_back_reenquiry", {"inspector_id": "8", "comments": ""}).status_code == 302
        assert _post_action(client, "inspector", "po_send_back_reenquiry", {"comments": "x"}).status_code == 302
        stub.petition = {"id": 1, "status": "action_taken"}
        assert _post_action(client, "po", "po_send_back_reenquiry", {"comments": "x"}).status_code == 302
        stub.petition = {"id": 1, "status": "forwarded_to_po"}
        assert _post_action(client, "po", "po_send_back_reenquiry", {"comments": ""}).status_code == 302

        assert _post_action(client, "inspector", "give_conclusion").status_code == 302
        stub.petition = None
        assert _post_action(client, "po", "give_conclusion", {"efile_no": "EO", "final_conclusion": "ok"}).status_code == 302
        stub.petition = {"id": 1, "efile_no": None}
        assert _post_action(client, "po", "give_conclusion", {"efile_no": "", "final_conclusion": "ok"}).status_code == 302
        assert _post_action(client, "po", "give_conclusion", {"efile_no": "EO", "final_conclusion": ""}).status_code == 302
        assert _post_action(client, "po", "give_conclusion", {"efile_no": "EO", "final_conclusion": "x" * 10001}).status_code == 302
        assert _post_action(client, "po", "give_conclusion", {"efile_no": "EO", "final_conclusion": "ok", "instructions": "x" * 5001}).status_code == 302
        assert _post_action(client, "po", "give_conclusion", {"efile_no": "EO", "final_conclusion": "ok", "conclusion_file": (io.BytesIO(b"txt"), "bad.pdf")}, multipart=True).status_code == 302

        assert _post_action(client, "inspector", "send_to_cmd").status_code == 302
        stub.petition = None
        assert _post_action(client, "po", "send_to_cmd", {"efile_no": "EO"}).status_code == 302
        stub.petition = {"id": 1, "efile_no": None}
        assert _post_action(client, "po", "send_to_cmd", {"efile_no": "", "cmd_instructions": "ok"}).status_code == 302
        assert _post_action(client, "po", "send_to_cmd", {"efile_no": "EO", "cmd_instructions": "x" * 5001}).status_code == 302

        assert _post_action(client, "inspector", "update_efile_no", {"efile_no": "EO"}).status_code == 302
        assert _post_action(client, "po", "update_efile_no", {"efile_no": ""}).status_code == 302
        stub.petition = None
        assert _post_action(client, "po", "update_efile_no", {"efile_no": "EO"}).status_code == 302
        stub.petition = {"id": 1, "requires_permission": True, "status": "forwarded_to_cvo", "efile_no": None}
        assert _post_action(client, "po", "update_efile_no", {"efile_no": "EO"}).status_code == 302
        stub.petition = {"id": 1, "requires_permission": False, "status": "closed", "efile_no": None}
        assert _post_action(client, "po", "update_efile_no", {"efile_no": "EO"}).status_code == 302
        stub.petition = {"id": 1, "requires_permission": False, "status": "forwarded_to_cvo", "efile_no": "EO"}
        assert _post_action(client, "po", "update_efile_no", {"efile_no": "EO2"}).status_code == 302

        assert _post_action(client, "po", "cmd_submit_action_report").status_code == 302
        assert _post_action(client, "cmd_apspdcl", "cmd_submit_action_report", {"action_taken": ""}).status_code == 302
        assert _post_action(client, "cmd_apspdcl", "cmd_submit_action_report", {"action_taken": "x" * 10001}).status_code == 302
        assert _post_action(client, "cmd_apspdcl", "cmd_submit_action_report", {"action_taken": "ok", "action_report_file": (io.BytesIO(b"txt"), "bad.pdf")}, multipart=True).status_code == 302

        assert _post_action(client, "inspector", "po_lodge").status_code == 302
        stub.petition = None
        assert _post_action(client, "po", "po_lodge", {"lodge_remarks": "x", "efile_no": "EO"}).status_code == 302
        stub.petition = {"id": 1, "status": "action_taken", "efile_no": None}
        assert _post_action(client, "po", "po_lodge", {"lodge_remarks": "x" * 5001, "efile_no": "EO"}).status_code == 302
        assert _post_action(client, "inspector", "po_direct_lodge").status_code == 302
        stub.petition = {"id": 1, "status": "closed", "efile_no": None}
        assert _post_action(client, "po", "po_direct_lodge", {"lodge_remarks": "ok", "efile_no": "EO"}).status_code == 302

        assert _post_action(client, "inspector", "close", {"comments": "x"}).status_code == 302
        stub.petition = {"id": 1, "status": "forwarded_to_po"}
        assert _post_action(client, "po", "close", {"comments": "x"}).status_code == 302


def test_submit_report_electrical_accident_matrix(monkeypatch):
    stub = RichModelsStub()
    stub.petition = {
        "id": 1,
        "requires_permission": False,
        "status": "assigned_to_inspector",
        "efile_no": None,
        "enquiry_type": "preliminary",
        "petition_type": "electrical_accident",
        "target_cvo": "apspdcl",
    }
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        assert _post_action(
            client,
            "inspector",
            "submit_report",
            {"report_text": "ok", "recommendation": "ok", "accident_type": "", "deceased_category": "departmental", "deceased_count": "1", "report_file": _pdf("r.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "inspector",
            "submit_report",
            {"report_text": "ok", "recommendation": "ok", "accident_type": "fatal", "deceased_category": "", "deceased_count": "1", "report_file": _pdf("r.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "inspector",
            "submit_report",
            {"report_text": "ok", "recommendation": "ok", "accident_type": "fatal", "deceased_category": "departmental", "deceased_count": "0", "report_file": _pdf("r.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "inspector",
            "submit_report",
            {"report_text": "ok", "recommendation": "ok", "accident_type": "fatal", "deceased_category": "departmental", "departmental_type": "", "deceased_count": "1", "report_file": _pdf("r.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "inspector",
            "submit_report",
            {"report_text": "ok", "recommendation": "ok", "accident_type": "fatal", "deceased_category": "non_departmental", "non_departmental_type": "", "deceased_count": "1", "report_file": _pdf("r.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "inspector",
            "submit_report",
            {"report_text": "ok", "recommendation": "ok", "accident_type": "fatal", "deceased_category": "general_public", "deceased_count": "1", "general_public_count": "0", "report_file": _pdf("r.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "inspector",
            "submit_report",
            {"report_text": "ok", "recommendation": "ok", "accident_type": "fatal", "deceased_category": "animals", "deceased_count": "1", "animals_count": "0", "report_file": _pdf("r.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "inspector",
            "submit_report",
            {
                "report_text": "ok",
                "recommendation": "ok",
                "accident_type": "fatal",
                "deceased_category": "non_departmental",
                "non_departmental_type": "private_electricians",
                "deceased_count": "1",
                "report_file": _pdf("r.pdf"),
            },
            multipart=True,
        ).status_code == 302


def test_petition_action_success_with_upload_variants(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        stub.petition = {
            "id": 1,
            "requires_permission": False,
            "status": "forwarded_to_cvo",
            "efile_no": None,
            "enquiry_type": "preliminary",
            "target_cvo": "apspdcl",
            "received_at": "jmd_office",
            "source_of_petition": "media",
        }
        assert _post_action(
            client,
            "cvo_apspdcl",
            "send_receipt_to_po",
            {"permission_file": _pdf("perm.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "cvo_apspdcl",
            "cvo_route_petition",
            {
                "permission_request_type": "direct_enquiry",
                "enquiry_type_decision": "detailed",
                "inspector_id": "8",
                "assignment_memo_file": _pdf("memo.pdf"),
            },
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "cvo_apspdcl",
            "cvo_set_enquiry_mode",
            {"permission_request_type": "direct_enquiry", "enquiry_type_decision": "preliminary"},
        ).status_code == 302

        stub.petition = {
            "id": 1,
            "requires_permission": True,
            "status": "sent_for_permission",
            "efile_no": None,
            "enquiry_type": "preliminary",
            "target_cvo": "apspdcl",
            "received_at": "jmd_office",
        }
        assert _post_action(
            client,
            "po",
            "approve_permission",
            {"target_cvo": "apspdcl", "organization": "aptransco", "enquiry_type_decision": "preliminary", "efile_no": "EO-10"},
        ).status_code == 302
        assert _post_action(client, "po", "reject_permission", {"comments": "Rejected for record"}).status_code == 302

        stub.petition = {
            "id": 1,
            "requires_permission": True,
            "status": "permission_approved",
            "efile_no": None,
            "enquiry_type": "detailed",
            "assigned_inspector_id": 8,
        }
        assert _post_action(
            client,
            "cvo_apspdcl",
            "assign_inspector",
            {"inspector_id": "8", "assignment_memo_file": _pdf("assign.pdf")},
            multipart=True,
        ).status_code == 302

        stub.petition = {
            "id": 1,
            "requires_permission": False,
            "status": "enquiry_report_submitted",
            "efile_no": None,
            "enquiry_type": "preliminary",
            "source_of_petition": "media",
        }
        assert _post_action(
            client,
            "cvo_apspdcl",
            "request_detailed_enquiry",
            {"cvo_comments": "Need detailed", "prima_facie_file": _pdf("prima.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "cvo_apspdcl",
            "upload_consolidated_report",
            {"consolidated_report_file": _pdf("consolidated.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "cvo_apspdcl",
            "cvo_comments",
            {"cvo_comments": "Forwarding", "consolidated_report_file": _pdf("review.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "cvo_apspdcl",
            "cvo_direct_lodge",
            {"lodge_remarks": "Media closed at CVO"},
        ).status_code == 302

        stub.petition = {
            "id": 1,
            "requires_permission": False,
            "status": "forwarded_to_po",
            "efile_no": None,
            "enquiry_type": "preliminary",
        }
        assert _post_action(
            client,
            "po",
            "give_conclusion",
            {"efile_no": "EO-20", "final_conclusion": "Final", "instructions": "Act", "conclusion_file": _pdf("conclusion.pdf")},
            multipart=True,
        ).status_code == 302
        assert _post_action(
            client,
            "po",
            "send_to_cmd",
            {"efile_no": "EO-21", "cmd_instructions": "Take action", "cmd_handler_id": "6"},
        ).status_code == 302

        stub.petition = {
            "id": 1,
            "requires_permission": False,
            "status": "action_instructed",
            "efile_no": "EO-30",
        }
        assert _post_action(
            client,
            "cmd_apspdcl",
            "cmd_submit_action_report",
            {"action_taken": "Completed", "action_report_file": _pdf("action.pdf")},
            multipart=True,
        ).status_code == 302

        stub.petition = {
            "id": 1,
            "requires_permission": False,
            "status": "forwarded_to_po",
            "efile_no": None,
        }
        assert _post_action(client, "po", "po_lodge", {"lodge_remarks": "Lodge", "efile_no": "EO-40"}).status_code == 302
        assert _post_action(client, "po", "po_direct_lodge", {"lodge_remarks": "Direct lodge", "efile_no": "EO-41"}).status_code == 302

        stub.petition = {
            "id": 1,
            "requires_permission": False,
            "status": "action_taken",
            "efile_no": "EO-42",
        }
        assert _post_action(client, "po", "close", {"comments": "Closed finally"}).status_code == 302


def test_exception_branches_in_actions_and_admin_routes(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="data_entry")
        stub.fail_methods.add("forward_petition_to_cvo")
        assert client.post("/petitions/1/action", data={"action": "forward_to_cvo", "target_cvo": "apspdcl"}).status_code == 302

        login_as(client, role="super_admin")
        stub.fail_methods.add("upsert_form_field_config")
        assert client.post(
            "/form-management",
            data={"form_key": "deo_petition", "field_key": "subject", "field_type": "textarea", "label": "S"},
        ).status_code == 302
        assert client.post(
            "/form-management",
            data={"form_key": "bad", "field_key": "subject", "field_type": "textarea", "label": "S"},
        ).status_code == 302
        assert client.post(
            "/form-management",
            data={"form_key": "deo_petition", "field_key": "subject", "field_type": "bad", "label": "S"},
        ).status_code == 302
        assert client.post(
            "/form-management",
            data={
                "form_key": "deo_petition",
                "field_key": "govt_institution_type",
                "field_type": "select",
                "label": "Inst",
                "options_text": "a|A\nb|B",
            },
        ).status_code == 302


def test_help_profile_and_admin_positive_flows(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(app_module, "ensure_upload_dirs", lambda: None)
    monkeypatch.setattr(
        app_module,
        "validate_profile_photo_upload",
        lambda upload, user_id: (True, "profile/test.png", None),
    )
    monkeypatch.setattr(
        app_module,
        "_save_uploaded_file",
        lambda upload, base_dir, file_name, label, use_date_subdir=False: (True, file_name),
    )
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")
        response = client.post(
            "/help",
            data={
                "title": "Guide",
                "resource_type": "manual",
                "storage_kind": "external_url",
                "external_url": "https://example.com/guide",
                "display_order": "2",
            },
        )
        assert response.status_code == 302

        response = client.post(
            "/help",
            data={
                "title": "PDF Guide",
                "resource_type": "manual",
                "storage_kind": "upload",
                "display_order": "1",
                "resource_file": _pdf("guide.pdf"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 302

        response = client.post(
            "/help",
            data={"action": "toggle_active", "resource_id": "4", "activate": "1"},
        )
        assert response.status_code == 302

        stub.user = {
            "id": 1,
            "username": "tester",
            "full_name": "Tester Name",
            "role": "super_admin",
            "cvo_office": None,
            "phone": "9999999999",
            "email": "t@example.com",
            "profile_photo": None,
            "session_version": 1,
            "is_active": True,
            "must_change_password": False,
        }
        response = client.post(
            "/profile",
            data={
                "full_name": "Tester Prime",
                "username": "tester_new",
                "phone": "9999999999",
                "email": "new@example.com",
                "current_password": "oldpass",
                "new_password": "StrongPass@9",
                "confirm_password": "StrongPass@9",
                "profile_photo": _pdf("photo.png"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 302

        monkeypatch.setattr(app_module, "get_effective_form_field_configs", lambda: {})
        response = client.post(
            "/form-management",
            data={
                "action": "add_field",
                "new_form_key": "deo_petition",
                "new_field_key": "new_field",
                "new_label": "New Field",
                "new_field_type": "text",
                "new_is_required": "on",
            },
        )
        assert response.status_code == 302

        monkeypatch.setattr(
            app_module,
            "get_effective_form_field_configs",
            lambda: {
                "deo_petition.petition_type": {
                    "label": "Petition Type",
                    "type": "select",
                    "required": False,
                    "options": [{"value": "existing", "label": "Existing"}],
                }
            },
        )
        response = client.post(
            "/form-management",
            data={
                "form_key": "deo_petition",
                "field_key": "petition_type",
                "label": "Petition Type",
                "field_type": "select",
                "is_required": "on",
                "options_text": "bribe|Bribe\nother|Other",
            },
        )
        assert response.status_code == 302

        response = client.post(
            "/system-settings",
            data={
                key: str(meta["min"])
                for key, meta in app_module.SYSTEM_SETTING_DEFINITIONS.items()
            },
        )
        assert response.status_code == 302

        csv_bytes = io.BytesIO(
            b"username,full_name,role,cvo_office,assigned_cvo_username,phone,email\n"
            b"ins_one,Inspector One,inspector,apspdcl,cvo1,9999999999,ins1@example.com\n"
            b"deo_one,Data Entry,data_entry,apspdcl,,9999999998,deo@example.com\n"
        )
        response = client.post(
            "/users/upload",
            data={"users_file": (csv_bytes, "users.csv")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 302

        response = client.post(
            "/users/5/edit",
            data={
                "full_name": "Officer Updated",
                "role": "inspector",
                "cvo_office": "apspdcl",
                "assigned_cvo_id": "2",
                "phone": "9999999999",
                "email": "updated@example.com",
                "password": "StrongPass@9",
            },
        )
        assert response.status_code == 302

        assert client.post("/users/5/reset-password").status_code == 302
        assert client.post("/users/5/reset-username", data={"new_username": "user_renamed"}).status_code == 302
        assert client.post("/users/5/update-name", data={"full_name": "Officer Final"}).status_code == 302

        stub.fail_methods.update({"toggle_user_status", "update_user", "set_user_password", "set_username", "update_user_full_name", "map_inspector_to_cvo"})
        assert client.post("/users/1/toggle").status_code == 302
        assert client.post("/users/1/edit", data={"full_name": "Valid Name", "role": "po"}).status_code == 302
        assert client.post("/users/1/reset-password", data={"new_password": "secret123"}).status_code == 302
        assert client.post("/users/1/reset-username", data={"new_username": "valid.name"}).status_code == 302
        assert client.post("/users/1/update-name", data={"full_name": "Valid Name"}).status_code == 302
        assert client.post("/users/8/map-cvo", data={"cvo_id": "2"}).status_code == 302


def test_form_management_select_option_edge_parsing(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")
        assert client.post(
            "/form-management",
            data={
                "form_key": "deo_petition",
                "field_key": "govt_institution_type",
                "field_type": "select",
                "label": "Institution",
                "options_text": "\nsolo\n",
            },
        ).status_code == 302
        assert client.post(
            "/form-management",
            data={
                "form_key": "deo_petition",
                "field_key": "govt_institution_type",
                "field_type": "select",
                "label": "Institution",
                "options_text": "",
            },
        ).status_code == 302


def test_user_create_and_edit_more_validation_branches(monkeypatch):
    stub = RichModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")
        assert client.post("/users/new", data={"username": "good", "password": "123"}).status_code == 302
        assert client.post("/users/new", data={"username": "good", "password": "secret123", "full_name": "x"}).status_code == 302
        assert client.post("/users/new", data={"username": "good", "password": "secret123", "full_name": "Valid", "role": "bad"}).status_code == 302
        assert client.post("/users/new", data={"username": "good", "password": "secret123", "full_name": "Valid", "role": "po", "cvo_office": "bad"}).status_code == 302
        assert client.post("/users/new", data={"username": "good", "password": "secret123", "full_name": "Valid", "role": "po", "phone": "bad"}).status_code == 302
        assert client.post("/users/new", data={"username": "good", "password": "secret123", "full_name": "Valid", "role": "po", "email": "bad"}).status_code == 302
        assert client.post("/users/new", data={"username": "good", "password": "secret123", "full_name": "Valid", "role": "inspector"}).status_code == 302
        assert client.post(
            "/users/new",
            data={"username": "good", "password": "secret123", "full_name": "Valid", "role": "dsp", "cvo_office": ""},
        ).status_code == 302
        assert client.post(
            "/users/new",
            data={
                "username": "good",
                "password": "secret123",
                "full_name": "Valid",
                "role": "inspector",
                "cvo_office": "apspdcl",
                "assigned_cvo_id": "2",
            },
        ).status_code == 302

        assert client.post("/users/1/edit", data={"full_name": "Valid Name", "role": "bad"}).status_code == 302
        assert client.post("/users/1/edit", data={"full_name": "Valid Name", "role": "po", "cvo_office": "bad"}).status_code == 302
        assert client.post("/users/1/edit", data={"full_name": "Valid Name", "role": "po", "password": "123"}).status_code == 302
        assert client.post("/users/1/edit", data={"full_name": "Valid Name", "role": "po", "phone": "bad"}).status_code == 302
        assert client.post("/users/1/edit", data={"full_name": "Valid Name", "role": "po", "email": "bad"}).status_code == 302
        assert client.post("/users/1/edit", data={"full_name": "Valid Name", "role": "inspector"}).status_code == 302
        assert client.post("/users/1/edit", data={"full_name": "Valid Name", "role": "dsp"}).status_code == 302
        assert client.post(
            "/users/1/edit",
            data={"full_name": "Valid Name", "role": "inspector", "cvo_office": "apspdcl", "assigned_cvo_id": "2"},
        ).status_code == 302

        assert client.post("/users/1/reset-username", data={"new_username": ""}).status_code == 302
        stub.fail_methods.add("set_username")
        assert client.post("/users/1/reset-username", data={"new_username": "valid.name"}).status_code == 302
        assert client.post("/users/8/map-cvo", data={"cvo_id": ""}).status_code == 302


def test_users_upload_xlsx_and_row_level_validation(monkeypatch):
    stub = RichModelsStub()

    def _fake_user_by_username(username):
        if username == "badcvo":
            return {"id": 77, "role": "po"}
        return {"id": 2, "role": "cvo_apspdcl"}

    stub.get_user_by_username = _fake_user_by_username
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")

        monkeypatch.setattr(app_module, "load_workbook", None)
        assert client.post(
            "/users/upload",
            data={"users_file": (io.BytesIO(b"dummy"), "users.xlsx")},
            content_type="multipart/form-data",
        ).status_code == 302

        def _raise_wb(*_a, **_k):
            raise ValueError("parse boom")

        monkeypatch.setattr(app_module, "load_workbook", _raise_wb)
        assert client.post(
            "/users/upload",
            data={"users_file": (io.BytesIO(b"dummy"), "users.xlsx")},
            content_type="multipart/form-data",
        ).status_code == 302

        csv_payload = (
            "username,password,full_name,role,cvo_office,assigned_cvo_username,phone,email\n"
            ",secret123,Name,po,,,+919999999999,a@b.com\n"
            "u1,secret123,Name,bad,,,+919999999999,a@b.com\n"
            "u2,secret123,Name,po,bad,,+919999999999,a@b.com\n"
            "ab,secret123,Name,po,,,+919999999999,a@b.com\n"
            "u4,123,Name,po,,,+919999999999,a@b.com\n"
            "u5,secret123,ab,po,,,+919999999999,a@b.com\n"
            "u6,secret123,Name,po,,,bad,a@b.com\n"
            "u7,secret123,Name,po,,,+919999999999,bad\n"
            "u8,secret123,Name,inspector,apspdcl,,+919999999999,a@b.com\n"
            "u9,secret123,Name,cvo_apspdcl,,,+919999999999,a@b.com\n"
            "u10,secret123,Name,po,,cvo_user,+919999999999,a@b.com\n"
            "u11,secret123,Name,inspector,apspdcl,badcvo,+919999999999,a@b.com\n"
            "u12,secret123,Name,inspector,apspdcl,cvo_user,+919999999999,a@b.com\n"
        ).encode("utf-8")
        stub.fail_methods.add("create_user")
        assert client.post(
            "/users/upload",
            data={"users_file": (io.BytesIO(csv_payload), "users.csv")},
            content_type="multipart/form-data",
        ).status_code == 302
