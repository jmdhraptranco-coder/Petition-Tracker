import io
from datetime import datetime, timedelta

from werkzeug.datastructures import FileStorage

import app as app_module
import models


def _pdf_file(name="ok.pdf", payload=b"%PDF-1.4 test"):
    return FileStorage(stream=io.BytesIO(payload), filename=name, content_type="application/pdf")


def test_parse_and_validate_helpers():
    assert app_module.parse_optional_int("5") == 5
    assert app_module.parse_optional_int("0") is None
    assert app_module.parse_optional_int("x") is None
    assert app_module.parse_date_input("2026-02-17").isoformat() == "2026-02-17"
    assert app_module.parse_date_input("17-02-2026") is None
    assert app_module.validate_contact("+91 9876543210")
    assert not app_module.validate_contact("abc")
    assert app_module.validate_email("a@b.com")
    assert not app_module.validate_email("a@b")


def test_validate_pdf_upload_variants():
    ok, filename = app_module.validate_pdf_upload(None, "File")
    assert ok and filename is None

    ok, msg = app_module.validate_pdf_upload(_pdf_file(name="note.txt"), "File")
    assert not ok and "PDF format" in msg

    ok, msg = app_module.validate_pdf_upload(_pdf_file(payload=b"plain text"), "File")
    assert not ok and "not a valid PDF" in msg

    ok, filename = app_module.validate_pdf_upload(_pdf_file(), "File")
    assert ok and filename == "ok.pdf"


def test_resolve_efile_logic():
    petition = {"efile_no": "EO-1"}
    efile, err = app_module.resolve_efile_no_for_action(petition, "EO-2")
    assert efile is None
    assert "already set" in err

    efile, err = app_module.resolve_efile_no_for_action(petition, "")
    assert efile == "EO-1"
    assert err is None

    efile, err = app_module.resolve_efile_no_for_action({}, "", required_message="required")
    assert efile is None
    assert err == "required"

    efile, err = app_module.resolve_efile_no_for_action({}, "X" * 101)
    assert efile is None
    assert "too long" in err

    efile, err = app_module.resolve_efile_no_for_action({}, "EO-NEW")
    assert efile == "EO-NEW"
    assert err is None


def test_form_field_config_merge(monkeypatch):
    monkeypatch.setattr(
        app_module.models,
        "get_form_field_configs",
        lambda: {
            "deo_petition.subject": {
                "label": "Subject Line",
                "type": "textarea",
                "required": True,
            },
            "deo_petition.govt_institution_type": {
                "type": "select",
                "required": True,
                "options": [
                    {"value": "a", "label": "A"},
                    {"value": "", "label": "bad"},
                    {"value": "b", "label": "B"},
                ],
            },
        },
    )
    merged = app_module.get_effective_form_field_configs()
    assert merged["deo_petition.subject"]["label"] == "Subject Line"
    assert merged["deo_petition.subject"]["required"] is True
    assert merged["deo_petition.govt_institution_type"]["options"] == [
        {"value": "a", "label": "A"},
        {"value": "b", "label": "B"},
    ]


def test_build_dashboard_analytics_summary():
    petitions = [
        {
            "status": "closed",
            "petition_type": "bribe",
            "source_of_petition": "govt",
            "requires_permission": True,
            "received_at": "jmd_office",
            "received_date": datetime.now().date(),
        },
        {
            "status": "forwarded_to_po",
            "petition_type": "other",
            "source_of_petition": "media",
            "requires_permission": False,
            "received_at": "cvo_apspdcl_tirupathi",
            "received_date": datetime.now().date(),
        },
    ]
    analytics = app_module._build_dashboard_analytics(petitions, {"sla_within": 1, "sla_breached": 0})
    assert analytics["summary"]["total_visible"] == 2
    assert analytics["summary"]["closed"] == 1
    assert analytics["summary"]["active"] == 1
    assert "Permission" in analytics["enquiry_mode_split"]["labels"]
    assert "Direct" in analytics["enquiry_mode_split"]["labels"]


def test_model_count_and_kpi_helpers(monkeypatch):
    petitions = [
        {"status": "forwarded_to_cvo"},
        {"status": "action_taken"},
        {"status": "forwarded_to_po"},
        {"status": "forwarded_to_jmd"},
    ]
    counts = models._count_statuses(petitions)
    assert counts["forwarded_to_cvo"] == 1
    assert models._count_multi(counts, ["forwarded_to_po", "forwarded_to_jmd"]) == 2

    monkeypatch.setattr(models, "_get_po_permission_given_count", lambda _uid: 7)
    po_cards = models._build_role_kpi_cards("po", petitions, user_id=99)
    assert any(card["label"] == "Permission Given" and card["value"] == 7 for card in po_cards)

    cgm_cards = models._build_role_kpi_cards("cgm_hr_transco", petitions)
    assert len(cgm_cards) == 2

    fallback_cards = models._build_role_kpi_cards("unknown", petitions)
    assert fallback_cards[0]["label"] == "Total"


def test_workflow_stage_and_drilldown_filters(monkeypatch):
    petitions = [
        {"id": 1, "status": "assigned_to_inspector"},
        {"id": 2, "status": "closed"},
        {"id": 3, "status": "unknown_status"},
    ]
    stages = models._get_workflow_stage_stats(petitions)
    assert stages["stage_2"] == 1
    assert stages["stage_6"] == 1
    assert stages["stage_1"] == 1

    monkeypatch.setattr(models, "get_petitions_for_user", lambda *_args, **_kwargs: petitions)
    monkeypatch.setattr(models, "_get_sla_filtered_petitions", lambda _p, _m: [{"id": 10}, {"id": 11}])
    assert len(models.get_dashboard_drilldown("po", 1, None, "status:closed")) == 1
    assert len(models.get_dashboard_drilldown("po", 1, None, "multi:closed,assigned_to_inspector")) == 2
    assert len(models.get_dashboard_drilldown("po", 1, None, "stage_1")) == 1
    assert len(models.get_dashboard_drilldown("po", 1, None, "sla_total")) == 2
    assert models.get_dashboard_drilldown("po", 1, None, "unsupported_metric") == []


class _FakeCursor:
    def __init__(self, fetchall_results=None):
        self.fetchall_results = list(fetchall_results or [])
        self.queries = []

    def execute(self, query, params=None):
        self.queries.append((query, params))

    def fetchall(self):
        if self.fetchall_results:
            return self.fetchall_results.pop(0)
        return []


class _FakeConn:
    def __init__(self, cursor):
        self.cursor = cursor
        self.closed = False

    def close(self):
        self.closed = True


def test_drilldown_po_permission_given_branch(monkeypatch):
    petitions = [
        {"id": 1, "status": "closed"},
        {"id": 2, "status": "closed"},
    ]
    monkeypatch.setattr(models, "get_petitions_for_user", lambda *_args, **_kwargs: petitions)
    cursor = _FakeCursor(
        fetchall_results=[
            [{"petition_id": 1}, {"petition_id": 2}],
            [{"id": 2}, {"id": 1}],
        ]
    )
    conn = _FakeConn(cursor)
    monkeypatch.setattr(models, "get_db", lambda: conn)
    monkeypatch.setattr(models, "dict_cursor", lambda _conn: cursor)

    out = models.get_dashboard_drilldown("po", 5, None, "po_permission_given")
    assert [p["id"] for p in out] == [2, 1]
    assert conn.closed is True


def test_sla_filtered_and_summary_helpers(monkeypatch):
    now = datetime(2026, 2, 17, 10, 0, 0)

    class _FakeDateTime:
        @staticmethod
        def now():
            return now

    petitions = [
        {"id": 1, "enquiry_type": "preliminary"},
        {"id": 2, "enquiry_type": "detailed"},
        {"id": 3, "enquiry_type": "preliminary"},
    ]
    tracking_rows = [
        {"petition_id": 1, "assigned_at": now - timedelta(days=5), "closed_at": now},
        {"petition_id": 2, "assigned_at": now - timedelta(days=60), "closed_at": None},
        {"petition_id": 3, "assigned_at": now - timedelta(days=2), "closed_at": None},
    ]

    def _new_conn():
        cursor = _FakeCursor(fetchall_results=[tracking_rows])
        return _FakeConn(cursor)

    monkeypatch.setattr(models, "get_db", _new_conn)
    monkeypatch.setattr(models, "dict_cursor", lambda conn: conn.cursor)
    monkeypatch.setattr(models, "datetime", _FakeDateTime)

    assert len(models._get_sla_filtered_petitions(petitions, "sla_total")) == 3
    assert len(models._get_sla_filtered_petitions(petitions, "sla_within")) == 1
    assert len(models._get_sla_filtered_petitions(petitions, "sla_breached")) == 1
    assert len(models._get_sla_filtered_petitions(petitions, "sla_in_progress")) == 1

    summary = models._get_sla_stats_for_petitions(petitions)
    assert summary == {
        "sla_total": 3,
        "sla_in_progress": 1,
        "sla_within": 1,
        "sla_breached": 1,
    }


def test_sla_stats_with_conn_role_filters(monkeypatch):
    now = datetime(2026, 2, 17, 10, 0, 0)
    rows = [
        {"assigned_at": now - timedelta(days=3), "closed_at": now, "enquiry_type": "preliminary"},
        {"assigned_at": now - timedelta(days=50), "closed_at": None, "enquiry_type": "detailed"},
        {"assigned_at": now - timedelta(days=60), "closed_at": now, "enquiry_type": "detailed"},
    ]
    cursor = _FakeCursor(fetchall_results=[rows])
    conn = _FakeConn(cursor)

    class _FakeDateTime:
        @staticmethod
        def now():
            return now

    monkeypatch.setattr(models, "dict_cursor", lambda _conn: cursor)
    monkeypatch.setattr(models, "datetime", _FakeDateTime)

    stats = models._get_sla_stats(conn, "cvo_apspdcl", user_id=None)
    assert stats["sla_total"] == 3
    assert stats["sla_within"] == 1
    assert stats["sla_breached"] == 2
    assert stats["sla_in_progress"] == 0
    assert any("WHERE p.target_cvo = %s" in q for q, _ in cursor.queries)
