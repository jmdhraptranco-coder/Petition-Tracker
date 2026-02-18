import importlib
import os
from types import SimpleNamespace

import pytest


os.environ["SKIP_SCHEMA_UPDATES"] = "1"
app_module = importlib.import_module("app")


class ModelsStub(SimpleNamespace):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.create_petition = lambda data, user_id: self._record("create_petition", data=data, user_id=user_id) or {"id": 1, "sno": "VIG/PO/2026/0001"}
        self.send_for_permission = lambda petition_id, user_id, comments=None: self._record("send_for_permission", petition_id=petition_id, user_id=user_id, comments=comments)
        self.forward_petition_to_cvo = lambda petition_id, user_id, target_cvo, comments=None: self._record("forward_petition_to_cvo", petition_id=petition_id, user_id=user_id, target_cvo=target_cvo, comments=comments)
        self.get_petition_by_id = lambda petition_id: {"id": petition_id, "requires_permission": False, "status": "forwarded_to_cvo", "efile_no": None}
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
    with app_module.app.test_client() as c:
        c.models_stub = stub
        yield c


def login_as(client, user_id=1, role="super_admin", full_name="Test User"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_role"] = role
        sess["full_name"] = full_name
        sess["username"] = "tester"
