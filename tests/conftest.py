import importlib
import os
import sys
import time
from types import SimpleNamespace

import pytest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["SKIP_SCHEMA_UPDATES"] = "1"
app_module = importlib.import_module("app")


class ModelsStub(SimpleNamespace):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.users_by_id = {}
        self.create_petition = lambda data, user_id: self._record("create_petition", data=data, user_id=user_id) or {"id": 1, "sno": "VIG/PO/2026/0001"}
        self.send_for_permission = lambda petition_id, user_id, comments=None: self._record("send_for_permission", petition_id=petition_id, user_id=user_id, comments=comments)
        self.forward_petition_to_cvo = lambda petition_id, user_id, target_cvo, comments=None: self._record("forward_petition_to_cvo", petition_id=petition_id, user_id=user_id, target_cvo=target_cvo, comments=comments)
        self.get_petition_by_id = lambda petition_id: {"id": petition_id, "requires_permission": False, "status": "forwarded_to_cvo", "efile_no": None}
        self.get_user_by_id = lambda user_id: self.users_by_id.get(user_id) or {"id": user_id, "username": "tester", "full_name": "Test User", "role": "super_admin", "cvo_office": None, "phone": None, "email": None, "profile_photo": None, "session_version": 1, "is_active": True}
        self.submit_enquiry_report = lambda *args, **kwargs: self._record("submit_enquiry_report", args=args, kwargs=kwargs)
        self.po_update_efile_no = lambda petition_id, user_id, efile_no: self._record("po_update_efile_no", petition_id=petition_id, user_id=user_id, efile_no=efile_no) or True
        self.get_form_field_configs = lambda: {}
        self.upsert_form_field_config = lambda *args, **kwargs: self._record("upsert_form_field_config", args=args, kwargs=kwargs)

    def _record(self, name, **data):
        self.calls.append((name, data))
        return None


@pytest.fixture
def client(monkeypatch):
    stub = ModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    app_module.TEST_SERVER_SESSION_STORE.clear()
    app_module.PETITION_SUBMISSION_ATTEMPTS.clear()
    app_module.LOGIN_CAPTCHA_USED_TOKENS.clear()
    app_module.LOGIN_CAPTCHA_CHALLENGES.clear()
    with app_module.app.test_client() as c:
        c.models_stub = stub
        yield c


def login_as(client, user_id=1, role="super_admin", full_name="Test User", cvo_office=None):
    if cvo_office is None:
        if role in ("data_entry", "cvo_apspdcl"):
            cvo_office = "apspdcl"
        elif role == "cvo_apcpdcl":
            cvo_office = "apcpdcl"
        elif role == "cvo_apepdcl":
            cvo_office = "apepdcl"
    with client.session_transaction() as sess:
        now_ts = int(time.time())
        sess.pop("otp_pending_user", None)
        sess.pop("otp_pending_mobile", None)
        sess.pop("force_change_user_id", None)
        sess.pop("force_change_username", None)
        sess.pop("force_change_role", None)
        sess["user_id"] = user_id
        sess["user_role"] = role
        sess["full_name"] = full_name
        sess["username"] = "tester"
        sess["cvo_office"] = cvo_office
        sess["session_version"] = 1
        sess["auth_issued_at"] = now_ts
        sess["auth_last_seen_at"] = now_ts
    stub = getattr(client, "models_stub", None)
    if stub is not None and hasattr(stub, "users_by_id"):
        stub.users_by_id[user_id] = {
            "id": user_id,
            "username": "tester",
            "full_name": full_name,
            "role": role,
            "cvo_office": cvo_office,
            "phone": None,
            "email": None,
            "profile_photo": None,
            "session_version": 1,
            "is_active": True,
        }
