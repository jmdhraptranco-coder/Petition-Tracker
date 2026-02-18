from datetime import datetime

import models


class CursorStub:
    def __init__(self, fetchone_items=None, fetchall_items=None, rowcount=1):
        self.fetchone_items = list(fetchone_items or [])
        self.fetchall_items = list(fetchall_items or [])
        self.rowcount = rowcount
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        if self.fetchone_items:
            return self.fetchone_items.pop(0)
        return None

    def fetchall(self):
        if self.fetchall_items:
            return self.fetchall_items.pop(0)
        return []


class ConnStub:
    def __init__(self, cursor):
        self.cursor_obj = cursor
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def bind_db(monkeypatch, fetchone_items=None, fetchall_items=None, rowcount=1):
    cursor = CursorStub(fetchone_items=fetchone_items, fetchall_items=fetchall_items, rowcount=rowcount)
    conn = ConnStub(cursor)
    monkeypatch.setattr(models, "get_db", lambda: conn)
    monkeypatch.setattr(models, "dict_cursor", lambda _conn: cursor)
    return conn, cursor


class FailingCursor(CursorStub):
    def execute(self, query, params=None):
        self.executed.append((query, params))
        raise Exception("forced db failure")


def bind_failing_db(monkeypatch):
    cursor = FailingCursor()
    conn = ConnStub(cursor)
    monkeypatch.setattr(models, "get_db", lambda: conn)
    monkeypatch.setattr(models, "dict_cursor", lambda _conn: cursor)
    return conn


def test_user_management_db_functions(monkeypatch):
    monkeypatch.setattr(models, "generate_password_hash", lambda pwd: f"h::{pwd}")
    monkeypatch.setattr(models, "check_password_hash", lambda h, p: h == f"h::{p}")

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"id": 9}])
    assert models.create_user("u1", "pass123", "User One", "po") == 9
    assert conn.commits == 1 and conn.closed

    bind_db(monkeypatch, fetchone_items=[{"password_hash": "h::ok", "id": 1, "username": "u"}])
    assert models.authenticate_user("u", "ok")["id"] == 1

    bind_db(monkeypatch, fetchone_items=[{"password_hash": "h::bad"}])
    assert models.authenticate_user("u", "ok") is None

    bind_db(monkeypatch, fetchone_items=[{"id": 2}])
    assert models.get_user_by_id(2)["id"] == 2
    bind_db(monkeypatch, fetchone_items=[{"id": 3}])
    assert models.get_user_by_username("x")["id"] == 3
    bind_db(monkeypatch, fetchall_items=[[{"id": 1}, {"id": 2}]])
    assert len(models.get_all_users()) == 2
    bind_db(monkeypatch, fetchall_items=[[{"id": 1}]])
    assert len(models.get_users_by_role("inspector", "apspdcl")) == 1

    bind_db(monkeypatch, fetchone_items=[{"id": 1, "role": "cvo_apspdcl", "cvo_office": "apspdcl"}], fetchall_items=[[{"id": 5}]])
    assert models.get_inspectors_by_cvo(1)[0]["id"] == 5

    bind_db(monkeypatch, fetchall_items=[[{"id": 99}]])
    assert models.get_cvo_users()[0]["id"] == 99

    conn, _ = bind_db(monkeypatch)
    models.toggle_user_status(7)
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch)
    models.update_user(1, "Name", "po")
    assert conn.commits == 1
    conn, _ = bind_db(monkeypatch)
    models.update_user(1, "Name", "po", password="secret123")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch)
    models.set_user_password(1, "secret123")
    assert conn.commits == 1
    bind_db(monkeypatch, fetchall_items=[[{"id": 1}]])
    assert models.get_role_login_users()[0]["id"] == 1

    conn, _ = bind_db(monkeypatch)
    models.set_username(1, "new.user")
    assert conn.commits == 1
    conn, _ = bind_db(monkeypatch)
    models.update_user_full_name(1, "New Name")
    assert conn.commits == 1

    bind_db(monkeypatch, fetchall_items=[[{"id": 10}]])
    assert models.get_inspector_mappings()[0]["id"] == 10
    conn, _ = bind_db(monkeypatch)
    models.map_inspector_to_cvo(2, 3)
    assert conn.commits == 1


def test_form_config_and_petition_queries(monkeypatch):
    bind_db(
        monkeypatch,
        fetchall_items=[
            [
                {
                    "form_key": "deo_petition",
                    "field_key": "subject",
                    "label": "Subject",
                    "field_type": "text",
                    "is_required": True,
                    "options_json": '[{"value":"a","label":"A"}]',
                }
            ]
        ],
    )
    cfg = models.get_form_field_configs()
    assert cfg["deo_petition.subject"]["required"] is True

    conn, _ = bind_db(monkeypatch)
    models.upsert_form_field_config("deo_petition", "subject", "Subject", "text", True, [], 1)
    assert conn.commits == 1

    class _FakeDateTime:
        @staticmethod
        def now():
            return datetime(2026, 2, 17, 10, 0, 0)

    monkeypatch.setattr(models, "datetime", _FakeDateTime)
    conn, _ = bind_db(monkeypatch, fetchone_items=[{"nextval": 12}])
    assert models.generate_sno("jmd_office") == "VIG/PO/2026/0012"
    assert conn.commits == 1

    monkeypatch.setattr(models, "generate_sno", lambda _r: "VIG/PO/2026/0001")
    conn, _ = bind_db(monkeypatch, fetchone_items=[{"id": 1, "sno": "VIG/PO/2026/0001"}])
    out = models.create_petition(
        {
            "received_at": "jmd_office",
            "petitioner_name": "Anon",
            "subject": "Subj",
            "petition_type": "other",
        },
        created_by=7,
    )
    assert out["id"] == 1
    assert conn.commits == 1

    bind_db(monkeypatch, fetchone_items=[{"id": 1, "subject": "X"}])
    assert models.get_petition_by_id(1)["id"] == 1

    bind_db(monkeypatch, fetchall_items=[[{"id": 1}, {"id": 2}]])
    assert len(models.get_petitions_for_user(1, "po", "apspdcl", "all", "direct")) == 2
    bind_db(monkeypatch, fetchall_items=[[{"id": 1}]])
    assert len(models.get_all_petitions(status_filter="received", enquiry_mode="permission")) == 1


def test_workflow_functions_success_paths(monkeypatch):
    conn, _ = bind_db(monkeypatch, fetchone_items=[{"role": "data_entry"}, {"status": "received"}, {"id": 2}])
    models.send_for_permission(1, 9, "send")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"id": 2}, {"status": "forwarded_to_cvo"}])
    models.cvo_send_receipt_to_po(1, 3, "ok")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"id": 4}])
    models.approve_permission(1, 2, "apspdcl", "EO-1", "ok", "preliminary")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch)
    models.reject_permission(1, 2, "reason")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "forwarded_to_cvo", "requires_permission": False}, {"id": 7}])
    models.assign_to_inspector(1, 2, 8, "assign", "detailed")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"ereceipt_no": "E1", "status": "forwarded_to_cvo"}])
    models.set_ereceipt(1, 5, "E2", "r.pdf")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"assigned_cvo_id": 4}])
    models.submit_enquiry_report(1, 8, "report", "", "rec", "file.pdf")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"id": 2}])
    models.cvo_add_comments(1, 4, "cmt")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "enquiry_report_submitted"}, {"id": 2}])
    models.cvo_request_detailed_enquiry(1, 4, "need details")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "enquiry_report_submitted"}])
    models.cvo_upload_consolidated_report(1, 4, "cvo.pdf")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch)
    models.po_give_conclusion(1, 2, "EO-1", "closed", "ins", "concl.pdf")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"target_cvo": "apspdcl", "status": "forwarded_to_po"}, {"id": 6}])
    models.po_send_to_cmd(1, 2, "do action", "EO-1")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "action_instructed"}, {"id": 2}])
    models.cmd_submit_action_report(1, 6, "done", "a.pdf")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "action_taken"}])
    models.po_lodge_petition(1, 2, "lodged", "EO-2")
    assert conn.commits == 1

    conn, cur = bind_db(monkeypatch, fetchone_items=[{"status": "forwarded_to_cvo", "efile_no": ""}, {"efile_no": "EO-3"}], rowcount=1)
    assert models.po_update_efile_number(1, 2, "EO-3", "set") is True
    assert conn.commits == 1 and cur.rowcount == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "sent_for_permission"}])
    models.po_direct_lodge_no_enquiry(1, 2, "direct", "EO-4")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch)
    models.cvo_take_action(1, 4, "action")
    assert conn.commits == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "lodged"}])
    models.close_petition(1, 2, "close")
    assert conn.commits == 1

    conn, cur = bind_db(monkeypatch, fetchone_items=[{"status": "forwarded_to_cvo", "current_handler_id": 4}], rowcount=1)
    assert models.po_update_efile_no(1, 2, "EO-5") is True
    assert conn.commits == 1 and cur.rowcount == 1

    bind_db(monkeypatch, fetchall_items=[[{"id": 1}]])
    assert models.get_petition_tracking(1)[0]["id"] == 1
    bind_db(monkeypatch, fetchone_items=[{"id": 11}])
    assert models.get_enquiry_report(1)["id"] == 11


def test_workflow_and_error_branches(monkeypatch):
    conn, cur = bind_db(monkeypatch, fetchone_items=[{"status": "forwarded_to_cvo", "efile_no": "EO-1"}], rowcount=0)
    assert models.po_update_efile_number(1, 2, "EO-2") is False
    assert conn.rollbacks == 1 and cur.rowcount == 0

    conn, cur = bind_db(monkeypatch, fetchone_items=[{"status": "forwarded_to_cvo", "current_handler_id": 4}], rowcount=0)
    assert models.po_update_efile_no(1, 2, "EO-2") is False
    assert conn.rollbacks == 1 and cur.rowcount == 0

    conn, _ = bind_db(monkeypatch, fetchone_items=[None])
    try:
        models.po_send_to_cmd(99, 2, "x", "EO-1")
        assert False, "Expected exception"
    except Exception as exc:
        assert "Petition not found" in str(exc)
        assert conn.rollbacks == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"target_cvo": "invalid", "status": "x"}])
    try:
        models.po_send_to_cmd(1, 2, "x", "EO-1")
        assert False, "Expected exception"
    except Exception as exc:
        assert "No CMD role configured" in str(exc)
        assert conn.rollbacks == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"target_cvo": "apspdcl", "status": "x"}, None])
    try:
        models.po_send_to_cmd(1, 2, "x", "EO-1")
        assert False, "Expected exception"
    except Exception as exc:
        assert "No active user found" in str(exc)
        assert conn.rollbacks == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[None])
    try:
        models.cmd_submit_action_report(1, 2, "done")
        assert False, "Expected exception"
    except Exception as exc:
        assert "Petition not found" in str(exc)
        assert conn.rollbacks == 1

    conn, _ = bind_db(monkeypatch, fetchone_items=[{"status": "action_instructed"}, None])
    try:
        models.cmd_submit_action_report(1, 2, "done")
        assert False, "Expected exception"
    except Exception as exc:
        assert "No active PO user found" in str(exc)
        assert conn.rollbacks == 1


def test_schema_and_connection_helpers(monkeypatch):
    original_dict_cursor = models.dict_cursor
    cursor = CursorStub()
    conn = ConnStub(cursor)
    monkeypatch.setattr(models.psycopg2, "connect", lambda **_k: conn)
    monkeypatch.setattr(models, "dict_cursor", lambda _conn: cursor)
    models.ensure_schema_updates()
    assert conn.closed is True
    assert len(cursor.executed) >= 10

    class _ConnForCursor:
        def __init__(self):
            self.autocommit = None
            self.args = None

        def cursor(self, cursor_factory=None):
            self.args = cursor_factory
            return "CUR"

    conn2 = _ConnForCursor()
    monkeypatch.setattr(models.psycopg2, "connect", lambda **_k: conn2)
    got = models.get_db()
    assert got is conn2 and got.autocommit is False

    sentinel = object()
    monkeypatch.setattr(models, "dict_cursor", original_dict_cursor)
    monkeypatch.setattr(models.psycopg2.extras, "RealDictCursor", sentinel)
    assert models.dict_cursor(conn2) == "CUR"
    assert conn2.args is sentinel


def test_forward_and_dashboard_stats_helpers(monkeypatch):
    conn, _ = bind_db(
        monkeypatch,
        fetchone_items=[{"role": "data_entry"}, {"status": "received"}, {"id": 3}],
    )
    models.forward_petition_to_cvo(1, 2, "apspdcl", "note")
    assert conn.commits == 1

    monkeypatch.setattr(models, "get_petitions_for_user", lambda *_a, **_k: [{"status": "received"}, {"status": "closed"}])
    monkeypatch.setattr(models, "_build_role_kpi_cards", lambda *_a, **_k: [{"label": "Total", "value": 2}])
    monkeypatch.setattr(
        models,
        "_get_sla_stats_for_petitions",
        lambda _p: {"sla_total": 1, "sla_in_progress": 0, "sla_within": 1, "sla_breached": 0},
    )
    stats = models.get_dashboard_stats("po", 1, "apspdcl")
    assert stats["total_visible"] == 2
    assert stats["stage_1"] == 1
    assert stats["stage_6"] == 1


def test_get_petitions_for_user_role_query_branches(monkeypatch):
    roles = [
        "super_admin",
        "data_entry",
        "po",
        "cmd_apspdcl",
        "cmd_apepdcl",
        "cmd_apcpdcl",
        "cgm_hr_transco",
        "cvo_apspdcl",
        "cvo_apepdcl",
        "cvo_apcpdcl",
        "dsp",
        "inspector",
    ]
    for role in roles:
        conn, cur = bind_db(monkeypatch, fetchall_items=[[]])
        models.get_petitions_for_user(11, role, cvo_office="apspdcl", status_filter="received", enquiry_mode="direct")
        assert conn.closed is True
        assert len(cur.executed) >= 1
    conn, cur = bind_db(monkeypatch, fetchall_items=[[]])
    models.get_petitions_for_user(11, "po", status_filter="all", enquiry_mode="permission")
    assert len(cur.executed) >= 1


def test_get_all_petitions_query_branches(monkeypatch):
    conn, cur = bind_db(monkeypatch, fetchall_items=[[]])
    models.get_all_petitions(status_filter="received", enquiry_mode="direct")
    assert len(cur.executed) >= 1
    conn, cur = bind_db(monkeypatch, fetchall_items=[[]])
    models.get_all_petitions(status_filter=None, enquiry_mode="permission")
    assert len(cur.executed) >= 1
    conn, cur = bind_db(monkeypatch, fetchall_items=[[]])
    models.get_all_petitions(status_filter=None, enquiry_mode="all")
    assert len(cur.executed) >= 1


def test_models_workflow_rollback_paths(monkeypatch):
    cases = [
        lambda: models.create_user("u", "p", "name", "po"),
        lambda: models.toggle_user_status(1),
        lambda: models.update_user(1, "name", "po"),
        lambda: models.set_user_password(1, "secret123"),
        lambda: models.set_username(1, "u1"),
        lambda: models.update_user_full_name(1, "name"),
        lambda: models.map_inspector_to_cvo(1, 2),
        lambda: models.upsert_form_field_config("deo_petition", "subject", "s", "text", True, [], 1),
        lambda: models.generate_sno("jmd_office"),
        lambda: models.create_petition({"received_at": "jmd_office", "petitioner_name": "a", "subject": "s", "petition_type": "other"}, 1),
        lambda: models.forward_petition_to_cvo(1, 1, "apspdcl"),
        lambda: models.send_for_permission(1, 1),
        lambda: models.cvo_send_receipt_to_po(1, 1),
        lambda: models.approve_permission(1, 1, "apspdcl"),
        lambda: models.reject_permission(1, 1),
        lambda: models.assign_to_inspector(1, 1, 2),
        lambda: models.set_ereceipt(1, 1, "E1"),
        lambda: models.submit_enquiry_report(1, 1, "r", "", "rec"),
        lambda: models.cvo_add_comments(1, 1, "c"),
        lambda: models.cvo_request_detailed_enquiry(1, 1, "c"),
        lambda: models.cvo_upload_consolidated_report(1, 1, "f.pdf"),
        lambda: models.po_give_conclusion(1, 1, "EO-1", "c"),
        lambda: models.po_send_to_cmd(1, 1, "i", "EO-1"),
        lambda: models.cmd_submit_action_report(1, 1, "a"),
        lambda: models.po_lodge_petition(1, 1, "r", "EO-1"),
        lambda: models.po_update_efile_number(1, 1, "EO-1"),
        lambda: models.po_direct_lodge_no_enquiry(1, 1, "r", "EO-1"),
        lambda: models.cvo_take_action(1, 1, "a"),
        lambda: models.close_petition(1, 1, "c"),
        lambda: models.po_update_efile_no(1, 1, "EO-1"),
    ]
    for run_case in cases:
        conn = bind_failing_db(monkeypatch)
        try:
            run_case()
            assert False, "Expected failure"
        except Exception:
            assert conn.rollbacks >= 1
            assert conn.closed is True


def test_model_kpi_and_sla_remaining_branches(monkeypatch):
    assert models._get_po_permission_given_count(None) == 0
    bind_db(monkeypatch, fetchone_items=[None])
    assert models._get_po_permission_given_count(1) == 0

    petitions = [{"status": "received"}, {"status": "assigned_to_inspector"}, {"status": "forwarded_to_po"}]
    assert models._build_role_kpi_cards("super_admin", petitions)[0]["label"] == "Received"
    assert models._build_role_kpi_cards("cvo_apspdcl", petitions)[0]["label"] == "Received"
    assert models._build_role_kpi_cards("inspector", petitions)[0]["label"] == "Assigned"
    assert models._build_role_kpi_cards("data_entry", petitions)[0]["label"] == "Received"

    rows = [{"assigned_at": None, "closed_at": None, "enquiry_type": "detailed"}]
    cursor = CursorStub(fetchall_items=[rows])
    conn = ConnStub(cursor)
    monkeypatch.setattr(models, "dict_cursor", lambda _conn: cursor)
    out = models._get_sla_stats(conn, "inspector", user_id=2)
    assert out["sla_total"] == 0
