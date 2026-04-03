import io

import app as app_module

from conftest import login_as


class ValidationStub:
    def __init__(self):
        self.calls = []
        self.fail_names = set()

    def _record(self, name, **kwargs):
        self.calls.append((name, kwargs))

    def get_user_by_id(self, user_id):
        return {
            "id": user_id,
            "username": "tester",
            "full_name": "Tester",
            "role": "super_admin" if user_id == 1 else "po",
            "cvo_office": "apspdcl",
            "phone": "9999999999",
            "email": "tester@example.com",
            "profile_photo": None,
            "session_version": 1,
            "is_active": True,
        }

    def get_form_field_configs(self):
        return {}

    def get_system_settings(self, prefix=None):
        return {}

    def create_petition(self, data, user_id):
        self._record("create_petition", data=data, user_id=user_id)
        if "create_petition" in self.fail_names:
            raise Exception("create fail")
        return {"id": 11, "sno": "VIG/11"}

    def send_for_permission(self, petition_id, user_id, comments=None):
        self._record("send_for_permission", petition_id=petition_id, user_id=user_id, comments=comments)

    def forward_petition_to_cvo(self, petition_id, user_id, target_cvo, comments=None):
        self._record("forward_petition_to_cvo", petition_id=petition_id, user_id=user_id, target_cvo=target_cvo, comments=comments)

    def update_imported_petition_state(self, **kwargs):
        self._record("update_imported_petition_state", **kwargs)

    def upsert_form_field_config(self, *args, **kwargs):
        self._record("upsert_form_field_config", args=args, kwargs=kwargs)
        if "upsert_form_field_config" in self.fail_names:
            raise Exception("field fail")

    def upsert_system_settings(self, updates, updated_by):
        self._record("upsert_system_settings", updates=updates, updated_by=updated_by)
        if "upsert_system_settings" in self.fail_names:
            raise Exception("settings fail")

    def get_all_users(self):
        return [
            {"id": 2, "username": "cvo1", "role": "cvo_apspdcl", "is_active": True},
            {"id": 3, "username": "insp1", "role": "inspector", "is_active": True},
            {"id": 4, "username": "cmd1", "role": "cmd_apspdcl", "is_active": True},
        ]

    def get_cvo_users(self):
        return [{"id": 2, "full_name": "CVO"}]

    def get_role_login_users(self):
        return [{"id": 1}]

    def get_inspector_mappings(self):
        return [{"id": 1}]

    def get_pending_password_reset_requests(self):
        if "get_pending_password_reset_requests" in self.fail_names:
            raise Exception("reset fail")
        return []


def test_petition_new_extra_validation_and_failure_paths(monkeypatch):
    stub = ValidationStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    app_module.PETITION_SUBMISSION_ATTEMPTS.clear()

    with app_module.app.test_client() as client:
        login_as(client, role="data_entry", cvo_office="apspdcl")
        base = {
            "received_date": "2026-02-17",
            "received_at": "cvo_apspdcl_tirupathi",
            "petitioner_name": "Petitioner",
            "contact": "9999999999",
            "place": "Hyd",
            "subject": "Subject",
            "petition_type": "bribe",
            "source_of_petition": "media",
            "remarks": "ok",
            "target_cvo": "apspdcl",
            "permission_request_type": "direct_enquiry",
            "ereceipt_no": "ER-1",
        }

        extra_bad = [
            {"petitioner_identity_type": "identified", "petitioner_name": "", "contact": "9999999999", "place": "Hyd"},
            {"petitioner_identity_type": "identified", "petitioner_name": "Petitioner", "contact": "", "place": "Hyd"},
            {"petitioner_identity_type": "identified", "petitioner_name": "Petitioner", "contact": "9999999999", "place": ""},
            {"petitioner_name": "X" * 256},
            {"subject": "X" * 5001},
            {"place": "X" * 256},
            {"ereceipt_file": (io.BytesIO(b"%PDF-1.4"), "r.pdf")},
            {"ereceipt_no": "E" * 101, "ereceipt_file": (io.BytesIO(b"%PDF-1.4"), "r.pdf")},
        ]
        for patch in extra_bad:
            payload = dict(base)
            payload.update(patch)
            resp = client.post("/petitions/new", data=payload, content_type="multipart/form-data")
            assert resp.status_code in (200, 302)

        monkeypatch.setattr(app_module, "_consume_petition_submission_slot", lambda: (False, 45, ["user"]))
        blocked_payload = dict(base)
        blocked_payload["ereceipt_file"] = (io.BytesIO(b"%PDF-1.4"), "r.pdf")
        blocked = client.post("/petitions/new", data=blocked_payload, content_type="multipart/form-data")
        assert blocked.status_code == 429

        monkeypatch.setattr(app_module, "_consume_petition_submission_slot", lambda: (True, 0, ["user"]))
        stub.fail_names.add("create_petition")
        fail_payload = dict(base)
        fail_payload["ereceipt_file"] = (io.BytesIO(b"%PDF-1.4"), "r.pdf")
        assert client.post("/petitions/new", data=fail_payload, content_type="multipart/form-data").status_code == 200


def test_import_and_admin_validation_branches(monkeypatch):
    stub = ValidationStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    app_module.PETITION_SUBMISSION_ATTEMPTS.clear()

    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")

        monkeypatch.setattr(
            app_module,
            "_parse_tabular_upload_rows",
            lambda *_a, **_k: [
                {
                    "received_date": "2026-02-17",
                    "received_at": "",
                    "target_cvo": "",
                    "petitioner_name": "",
                    "contact": "",
                    "place": "",
                    "subject": "",
                    "petition_type": "bad",
                    "source_of_petition": "government",
                    "govt_institution_type": "bad",
                    "enquiry_type": "weird",
                    "permission_request_type": "",
                    "requires_permission": "yes",
                    "permission_status": "",
                    "status": "open",
                    "assigned_inspector_username": "missing",
                    "remarks": "row one",
                    "efile_no": "",
                    "ereceipt_no": "",
                },
                {
                    "received_date": "2026-02-18",
                    "received_at": "cvo_apspdcl_tirupathi",
                    "target_cvo": "apspdcl",
                    "petitioner_name": "Done",
                    "contact": "9999999999",
                    "place": "Hyd",
                    "subject": "Imported",
                    "petition_type": "bribe",
                    "source_of_petition": "media",
                    "govt_institution_type": "",
                    "enquiry_type": "detailed",
                    "permission_request_type": "permission_required",
                    "requires_permission": "yes",
                    "permission_status": "approved",
                    "status": "action_instructed",
                    "assigned_inspector_username": "insp1",
                    "remarks": "row two",
                    "efile_no": "EO-2",
                    "ereceipt_no": "ER-2",
                },
            ],
        )
        assert client.post(
            "/petitions/import/upload",
            data={"petitions_file": (io.BytesIO(b"x"), "petitions.csv")},
            content_type="multipart/form-data",
        ).status_code == 302

        monkeypatch.setattr(
            app_module,
            "get_effective_form_field_configs",
            lambda: {"deo_petition.subject": {"label": "Subject", "type": "text", "required": False, "options": []}},
        )
        assert client.post(
            "/form-management",
            data={"action": "add_field", "new_form_key": "bad", "new_field_key": "ok_field", "new_label": "Label", "new_field_type": "text"},
        ).status_code == 302
        assert client.post(
            "/form-management",
            data={"action": "add_field", "new_form_key": "deo_petition", "new_field_key": "Bad Key", "new_label": "Label", "new_field_type": "text"},
        ).status_code == 302
        assert client.post(
            "/form-management",
            data={"action": "add_field", "new_form_key": "deo_petition", "new_field_key": "ok_field", "new_label": "", "new_field_type": "text"},
        ).status_code == 302
        assert client.post(
            "/form-management",
            data={"action": "add_field", "new_form_key": "deo_petition", "new_field_key": "ok_field", "new_label": "Label", "new_field_type": "bad"},
        ).status_code == 302
        assert client.post(
            "/form-management",
            data={"form_key": "bad", "field_key": "subject", "label": "Label", "field_type": "text"},
        ).status_code == 302

        first_key, first_meta = next(iter(app_module.SYSTEM_SETTING_DEFINITIONS.items()))
        assert client.post("/system-settings", data={first_key: ""}).status_code == 302
        assert client.post("/system-settings", data={first_key: "abc"}).status_code == 302
        bad_range = {k: str(int(v["max"]) + 1) for k, v in app_module.SYSTEM_SETTING_DEFINITIONS.items()}
        assert client.post("/system-settings", data=bad_range).status_code == 302

        stub.fail_names.update({"get_pending_password_reset_requests"})
        assert client.get("/users").status_code == 200
