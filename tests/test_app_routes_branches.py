import io
import time
from datetime import date

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

    def get_pending_signup_requests(self):
        return []

    def get_pending_reset_requests(self):
        return []

    def get_pending_password_reset_requests(self):
        return []

    def get_user_by_id(self, _uid):
        return {"id": _uid, "role": "super_admin", "username": "tester", "full_name": "Tester", "cvo_office": None, "phone": None, "email": None, "profile_photo": None, "session_version": 1, "is_active": True}

    def get_user_by_username(self, _uname):
        return {"id": 2, "role": "cvo_apspdcl"}

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


def test_anonymous_public_pages_do_not_create_server_session(monkeypatch):
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
        assert "session=" not in (login_page.headers.get("Set-Cookie") or "")
        assert not app_module.TEST_SERVER_SESSION_STORE


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


def test_profile_password_change_forces_relogin(monkeypatch):
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
        assert response.headers["Location"].endswith("/login")
        with client.session_transaction() as sess:
            assert "user_id" not in sess


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


def test_misc_auth_and_api_edge_paths(monkeypatch):
    monkeypatch.setenv("OTP_ENABLED", "0")
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
        assert '/auth/login-captcha/' in html
        assert '<img src="/auth/login-captcha/' in html


def test_login_captcha_image_is_served_from_session_state():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        captcha_token = _issue_login_captcha(client, "482753")
        response = client.get(f"/auth/login-captcha/{captcha_token}")
        assert response.status_code == 200
        assert response.mimetype == "image/bmp"
        assert response.headers["Cache-Control"].startswith("no-store")


def test_request_entity_too_large_rejects_external_referer(monkeypatch):
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
