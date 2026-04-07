from datetime import datetime

import app as app_module
import models
from tests.test_models_db_ops import bind_db


class FixedDateTime:
    @staticmethod
    def now():
        return datetime(2026, 4, 1, 12, 0, 0)

    def __call__(self, *args, **kwargs):
        return datetime(*args, **kwargs)


def test_dashboard_filter_helpers_and_filtered_stats(monkeypatch):
    filters = app_module._extract_dashboard_filters(
        {
            "from_date": "2026-03-31",
            "to_date": "2026-03-01",
            "petition_type": "invalid",
            "source_of_petition": "media",
            "received_at": "bad",
            "target_cvo": "apspdcl",
            "officer_id": "7",
        },
        {7: "Officer Seven"},
    )
    assert filters["from_date"].isoformat() == "2026-03-01"
    assert filters["to_date"].isoformat() == "2026-03-31"
    assert filters["petition_type"] == "all"
    assert filters["source_of_petition"] == "media"
    assert filters["received_at"] == "all"
    assert filters["target_cvo"] == "apspdcl"
    assert filters["officer_id"] == 7

    petitions = [
        {
            "id": 1,
            "received_date": datetime(2026, 3, 10).date(),
            "petition_type": "bribe",
            "source_of_petition": "media",
            "received_at": "jmd_office",
            "target_cvo": "apspdcl",
            "assigned_inspector_id": 7,
        },
        {
            "id": 2,
            "received_date": datetime(2026, 3, 20).date(),
            "petition_type": "other",
            "source_of_petition": "govt",
            "received_at": "cvo_apcpdcl_vijayawada",
            "target_cvo": "apcpdcl",
            "assigned_inspector_id": 11,
        },
    ]
    narrowed = app_module._apply_dashboard_filters(
        petitions,
        {
            "from_date": datetime(2026, 3, 1).date(),
            "to_date": datetime(2026, 3, 31).date(),
            "petition_type": "bribe",
            "source_of_petition": "media",
            "received_at": "jmd_office",
            "target_cvo": "apspdcl",
            "officer_id": 7,
        },
    )
    assert [p["id"] for p in narrowed] == [1]

    class ModelHelpers:
        @staticmethod
        def _get_workflow_stage_stats(items):
            return {"stage_1": len(items)}

        @staticmethod
        def _get_sla_stats_for_petitions(items):
            return {"sla_within": len(items), "sla_breached": 0}

        @staticmethod
        def _build_role_kpi_cards(role, items, user_id):
            return [{"role": role, "count": len(items), "user_id": user_id}]

    monkeypatch.setattr(app_module, "models", ModelHelpers)
    stats = app_module._build_filtered_dashboard_stats("po", 5, petitions, narrowed)
    assert stats["total_visible"] == 1
    assert stats["stage_1"] == 1
    assert stats["sla_within"] == 1
    assert stats["kpi_cards"][0]["count"] == 1


def test_analysis_report_data_empty_and_populated(monkeypatch):
    monkeypatch.setattr(app_module, "datetime", FixedDateTime())

    empty = app_module._build_analysis_report_data([])
    assert empty["total"] == 0
    assert len(empty["monthly_trend"]) == 6
    assert empty["sla_insights"] == []

    monkeypatch.setattr(
        app_module,
        "models",
        type(
            "M",
            (),
            {
                "get_sla_evaluation_rows": staticmethod(
                    lambda petitions: [
                        {
                            "id": 1,
                            "target_cvo": "apspdcl",
                            "assigned_inspector_id": 101,
                            "sla_bucket": "within",
                        },
                        {
                            "id": 2,
                            "target_cvo": "apcpdcl",
                            "assigned_inspector_id": 102,
                            "sla_bucket": "beyond",
                        },
                    ]
                )
            },
        )(),
    )
    petitions = [
        {
            "id": 1,
            "status": "closed",
            "petition_type": "electrical_accident",
            "source_of_petition": "media",
            "target_cvo": "apspdcl",
            "requires_permission": True,
            "is_overdue_escalated": False,
            "enquiry_type": "preliminary",
            "assigned_inspector_id": 101,
            "inspector_name": "Officer One",
            "received_date": datetime(2026, 3, 15),
        },
        {
            "id": 2,
            "status": "lodged",
            "petition_type": "bribe",
            "source_of_petition": "public_individual",
            "target_cvo": "apcpdcl",
            "requires_permission": False,
            "is_overdue_escalated": True,
            "enquiry_type": "detailed",
            "assigned_inspector_id": 102,
            "inspector_name": "Officer Two",
            "received_date": datetime(2026, 4, 1),
        },
        {
            "id": 3,
            "status": "assigned_to_inspector",
            "petition_type": "bribe",
            "source_of_petition": "public_individual",
            "target_cvo": "apcpdcl",
            "requires_permission": False,
            "is_overdue_escalated": True,
            "enquiry_type": "detailed",
            "assigned_inspector_id": 102,
            "inspector_name": "Officer Two",
            "received_date": datetime(2026, 2, 10),
        },
    ]
    report = app_module._build_analysis_report_data(petitions)
    assert report["total"] == 3
    assert report["closed"] == 1
    assert report["lodged"] == 1
    assert report["active"] == 1
    assert report["resolution_rate"] == 66.7
    assert report["sla_within"] == 1
    assert report["sla_beyond"] == 1
    assert report["overdue_count"] == 2
    assert report["permission_count"] == 1
    assert report["direct_count"] == 2
    assert report["enquiry_types"] == {"preliminary": 1, "detailed": 2}
    assert report["type_breakdown"][0]["type"] == "bribe"
    assert report["dept_stats"][0]["total"] >= report["dept_stats"][1]["total"]
    assert report["best_performers"][0]["name"] == "Officer One"
    assert report["top_defaulters"][0]["name"] == "Officer Two"
    assert report["talking_points"]
    assert report["dept_insights"]
    assert report["source_insights"]
    assert report["status_insights"]
    assert report["officer_insights"]
    assert report["sla_insights"]


def test_latest_enquiry_and_accident_stats(monkeypatch):
    bind_db(
        monkeypatch,
        fetchall_items=[
            [
                {
                    "petition_id": 10,
                    "accident_type": "fatal",
                    "deceased_category": "departmental",
                    "departmental_type": "regular",
                    "non_departmental_type": None,
                    "deceased_count": 2,
                    "general_public_count": 0,
                    "animals_count": 0,
                    "submitted_at": datetime(2026, 3, 1, 10, 0, 0),
                }
            ]
        ],
    )
    latest = models._get_latest_enquiry_reports_for_petitions([10])
    assert latest[0]["petition_id"] == 10
    assert models._get_latest_enquiry_reports_for_petitions([]) == []

    monkeypatch.setattr(
        models,
        "_get_latest_enquiry_reports_for_petitions",
        lambda _ids: [
            {
                "petition_id": 1,
                "accident_type": "fatal",
                "deceased_category": "departmental",
                "departmental_type": "regular",
                "deceased_count": 2,
                "general_public_count": 0,
                "animals_count": 0,
            },
            {
                "petition_id": 2,
                "accident_type": "non_fatal",
                "deceased_category": "non_departmental",
                "non_departmental_type": "contract_labour",
                "deceased_count": 3,
                "general_public_count": 0,
                "animals_count": 0,
            },
            {
                "petition_id": 3,
                "accident_type": "fatal",
                "deceased_category": "general_public",
                "deceased_count": 0,
                "general_public_count": 4,
                "animals_count": 0,
            },
            {
                "petition_id": 4,
                "accident_type": "non_fatal",
                "deceased_category": "animals",
                "deceased_count": 0,
                "general_public_count": 0,
                "animals_count": 5,
            },
        ],
    )
    stats = models._get_electrical_accident_stats_for_petitions(
        [
            {"id": 1, "petition_type": "electrical_accident"},
            {"id": 2, "petition_type": "electrical_accident"},
            {"id": 3, "petition_type": "electrical_accident"},
            {"id": 4, "petition_type": "electrical_accident"},
            {"id": 5, "petition_type": "bribe"},
        ]
    )
    assert stats["electrical_accident_total"] == 4
    assert stats["electrical_accident_fatal"] == 2
    assert stats["electrical_accident_non_fatal"] == 2
    assert stats["electrical_accident_departmental"] == 2
    assert stats["electrical_accident_non_departmental_contract"] == 3
    assert stats["electrical_accident_general_public_petitions"] == 1
    assert stats["electrical_accident_general_public_count"] == 4
    assert stats["electrical_accident_animals_petitions"] == 1
    assert stats["electrical_accident_animals_count"] == 5


def test_sla_evaluation_rows_and_filtered_views(monkeypatch):
    monkeypatch.setattr(models, "datetime", FixedDateTime())
    bind_db(
        monkeypatch,
        fetchall_items=[
            [
                {
                    "petition_id": 1,
                    "assigned_at": datetime(2026, 3, 1),
                    "closed_at": datetime(2026, 3, 10),
                    "converted_to_detailed": 0,
                },
                {
                    "petition_id": 2,
                    "assigned_at": datetime(2025, 12, 31),
                    "closed_at": None,
                    "converted_to_detailed": 0,
                },
                {
                    "petition_id": 3,
                    "assigned_at": datetime(2026, 3, 20),
                    "closed_at": None,
                    "converted_to_detailed": 1,
                },
            ]
        ],
    )
    petitions = [
        {
            "id": 1,
            "petition_type": "bribe",
            "source_of_petition": "govt",
            "enquiry_type": "preliminary",
            "target_cvo": "apspdcl",
            "assigned_inspector_id": 51,
        },
        {
            "id": 2,
            "petition_type": "electrical_accident",
            "source_of_petition": "media",
            "enquiry_type": "detailed",
            "target_cvo": "apcpdcl",
            "assigned_inspector_id": 52,
        },
        {
            "id": 3,
            "petition_type": "corruption",
            "source_of_petition": "govt",
            "enquiry_type": "detailed",
            "target_cvo": "apcpdcl",
            "assigned_inspector_id": 53,
        },
        {"id": 4, "petition_type": "bribe"},
    ]
    rows = models.get_sla_evaluation_rows(petitions)
    assert [row["id"] for row in rows] == [1, 2, 3]
    assert rows[0]["sla_rule_code"] == "PRELIMINARY_15"
    assert rows[0]["sla_state"] == "within"
    assert rows[1]["sla_rule_code"] == "DETAILED_SPECIAL_45_ESC60"
    assert rows[1]["sla_bucket"] == "beyond"
    assert rows[1]["is_beyond_sla_for_po"] is True
    assert rows[2]["sla_rule_code"] == "DETAILED_GENERAL_90"
    assert rows[2]["sla_bucket"] == "within"

    monkeypatch.setattr(models, "get_sla_evaluation_rows", lambda _petitions: list(rows))
    assert len(models._get_sla_filtered_petitions(petitions, "sla_total")) == 3
    assert len(models._get_sla_filtered_petitions(petitions, "sla_closed_within")) == 1
    assert len(models._get_sla_filtered_petitions(petitions, "sla_open_beyond")) == 1
    assert len(models._get_sla_filtered_petitions(petitions, "sla_in_progress")) == 2
    stats = models._get_sla_stats_for_petitions(petitions)
    assert stats["sla_total"] == 3
    assert stats["sla_closed_total"] == 1
    assert stats["sla_open_total"] == 2
    assert stats["sla_within"] == 2
    assert stats["sla_breached"] == 1


def test_sla_dashboard_and_profile_views(monkeypatch):
    petitions = [
        {
            "id": 1,
            "created_by": 20,
            "current_handler_id": 201,
            "assigned_inspector_id": 301,
            "handler_name": "CVO One",
            "inspector_name": "Inspector One",
        },
        {
            "id": 2,
            "created_by": 21,
            "current_handler_id": 0,
            "assigned_inspector_id": 302,
            "handler_name": "",
            "inspector_name": "Inspector Two",
        },
        {
            "id": 3,
            "created_by": 99,
            "current_handler_id": 999,
            "assigned_inspector_id": 303,
            "handler_name": "Ignored Officer",
            "inspector_name": "Inspector Three",
        },
    ]
    eval_rows = [
        {
            "id": 1,
            "current_handler_id": 201,
            "assigned_inspector_id": 301,
            "handler_name": "CVO One",
            "inspector_name": "Inspector One",
            "sla_bucket": "within",
            "sla_state": "within",
            "closed_at": datetime(2026, 3, 20),
        },
        {
            "id": 2,
            "current_handler_id": 0,
            "assigned_inspector_id": 302,
            "handler_name": "",
            "inspector_name": "Inspector Two",
            "sla_bucket": "beyond",
            "sla_state": "beyond",
            "closed_at": None,
        },
        {
            "id": 3,
            "current_handler_id": 999,
            "assigned_inspector_id": 303,
            "handler_name": "Ignored Officer",
            "inspector_name": "Inspector Three",
            "sla_bucket": "within",
            "sla_state": "within",
            "closed_at": None,
        },
    ]
    monkeypatch.setattr(models, "get_petitions_for_user", lambda *_a, **_k: list(petitions))
    monkeypatch.setattr(
        models,
        "get_sla_evaluation_rows",
        lambda items: [row for row in eval_rows if row["id"] in {item["id"] for item in items}],
    )
    monkeypatch.setattr(
        models,
        "_get_sla_stats_for_petitions",
        lambda _items: {"sla_total": 3, "sla_within": 2, "sla_breached": 1},
    )
    monkeypatch.setattr(
        models,
        "_get_user_roles_map",
        lambda _ids: {201: "cvo_apspdcl", 301: "inspector", 302: "inspector", 999: "clerk", 303: "inspector"},
    )
    monkeypatch.setattr(
        models,
        "_get_all_sla_officers",
        lambda: [
            {"id": 201, "full_name": "CVO One", "role": "cvo_apspdcl"},
            {"id": 301, "full_name": "Inspector One", "role": "inspector"},
            {"id": 302, "full_name": "Inspector Two", "role": "inspector"},
            {"id": 303, "full_name": "Inspector Three", "role": "inspector"},
        ],
    )
    monkeypatch.setattr(models, "get_user_by_id", lambda officer_id: {"id": officer_id, "full_name": f"Officer {officer_id}"})

    po_dashboard = models.get_sla_dashboard_data_for_user("po", 10, "apspdcl")
    assert po_dashboard["summary"]["sla_total"] == 3
    assert [employee["officer_id"] for employee in po_dashboard["employees"]] == [302, 201, 303, 301]

    data_entry_dashboard = models.get_sla_dashboard_data_for_user("data_entry", 20, "apspdcl")
    # data_entry has no per-officer breakdown; scoping is handled in get_petitions_for_user.
    assert data_entry_dashboard["employees"] == []
    # Petitions list is driven by the (mocked) get_petitions_for_user return value.
    assert len(data_entry_dashboard["petitions"]) == 3

    unauthorized = models.get_sla_employee_profile_for_user("data_entry", 20, "apspdcl", 302)
    assert unauthorized["unauthorized"] is True
    assert unauthorized["petitions"] == []

    authorized = models.get_sla_employee_profile_for_user("po", 10, "apspdcl", 302)
    assert authorized["unauthorized"] is False
    assert authorized["summary"]["total"] == 1
    assert authorized["summary"]["open_total"] == 1
    assert authorized["summary"]["beyond"] == 1
    assert authorized["officer"]["id"] == 302


def test_sla_policy_resolution_and_row_officer_helpers():
    assert models._resolve_sla_policy_for_petition({"enquiry_type": "preliminary"})["sla_days"] == 15
    assert models._resolve_sla_policy_for_petition({"petition_type": "electrical_accident", "enquiry_type": "detailed"})["sla_days"] == 45
    assert models._resolve_sla_policy_for_petition({"source_of_petition": "media", "enquiry_type": "detailed"})["escalation_days"] == 60
    assert models._resolve_sla_days_for_petition({"petition_type": "bribe", "enquiry_type": "detailed"}) == 90
    assert models._is_po_beyond_sla_row({"closed_at": None, "auto_escalate_to_po_days": 90, "elapsed_days": 91}) is True
    assert models._is_po_beyond_sla_row({"closed_at": datetime(2026, 1, 1), "auto_escalate_to_po_days": 90, "elapsed_days": 91}) is False

    officer_id, officer_name = models._resolve_sla_row_officer(
        {"current_handler_id": 11, "handler_name": "Handler", "assigned_inspector_id": 21, "inspector_name": "Inspector"},
        user_roles={11: "cvo_apspdcl", 21: "inspector"},
    )
    assert (officer_id, officer_name) == (11, "Handler")

    officer_id, officer_name = models._resolve_sla_row_officer(
        {"current_handler_id": 12, "handler_name": "Other", "assigned_inspector_id": 22, "inspector_name": "Inspector Two"},
        user_roles={12: "clerk", 22: "inspector"},
    )
    assert (officer_id, officer_name) == (22, "Inspector Two")

    assert models._resolve_sla_row_officer({"current_handler_id": 0, "assigned_inspector_id": 0}, user_roles={}) == (0, "")


def test_dashboard_drilldown_and_sla_stats_helpers(monkeypatch):
    petitions = [
        {
            "id": 1,
            "status": "received",
            "petition_type": "electrical_accident",
            "source_of_petition": "media",
            "requires_permission": True,
            "received_at": "jmd_office",
            "assigned_inspector_id": 11,
            "received_date": datetime(2026, 3, 1),
            "created_at": datetime(2026, 3, 2),
        },
        {
            "id": 2,
            "status": "assigned_to_inspector",
            "petition_type": "bribe",
            "source_of_petition": "govt",
            "requires_permission": False,
            "received_at": "cvo_apcpdcl_vijayawada",
            "assigned_inspector_id": 12,
            "received_date": datetime(2026, 4, 1),
            "created_at": datetime(2026, 4, 2),
        },
        {
            "id": 3,
            "status": "closed",
            "petition_type": "electrical_accident",
            "source_of_petition": "public_individual",
            "requires_permission": False,
            "received_at": "jmd_office",
            "assigned_inspector_id": 11,
            "received_date": datetime(2026, 4, 1),
            "created_at": datetime(2026, 4, 3),
        },
    ]
    monkeypatch.setattr(models, "get_petitions_for_user", lambda *_a, **_k: list(petitions))
    monkeypatch.setattr(
        models,
        "_get_latest_enquiry_reports_for_petitions",
        lambda _ids: [
            {"petition_id": 1, "accident_type": "fatal", "deceased_category": "departmental"},
            {"petition_id": 3, "accident_type": "non_fatal", "deceased_category": "animals"},
        ],
    )
    monkeypatch.setattr(models, "_get_sla_filtered_petitions", lambda _petitions, metric: [{"metric": metric}] if metric.startswith("sla_") else [])

    assert len(models.get_dashboard_drilldown("po", 9, "apspdcl", "all")) == 3
    assert len(models.get_dashboard_drilldown("po", 9, "apspdcl", "active")) == 2
    assert len(models.get_dashboard_drilldown("po", 9, "apspdcl", "stage_1")) == 1
    assert len(models.get_dashboard_drilldown("po", 9, "apspdcl", "status:closed")) == 1
    assert len(models.get_dashboard_drilldown("po", 9, "apspdcl", "multi:received,closed")) == 2
    assert len(models.get_dashboard_drilldown("po", 9, "apspdcl", "petition_type:bribe")) == 1
    assert len(models.get_dashboard_drilldown("po", 9, "apspdcl", "accident:electrical_total")) == 2
    assert len(models.get_dashboard_drilldown("po", 9, "apspdcl", "accident:fatal")) == 1
    assert len(models.get_dashboard_drilldown("po", 9, "apspdcl", "source:govt")) == 1
    assert len(models.get_dashboard_drilldown("po", 9, "apspdcl", "mode:permission")) == 1
    assert len(models.get_dashboard_drilldown("po", 9, "apspdcl", "mode:direct")) == 2
    assert len(models.get_dashboard_drilldown("po", 9, "apspdcl", "received_at:jmd_office")) == 2
    assert len(models.get_dashboard_drilldown("po", 9, "apspdcl", "officer:11")) == 2
    assert len(models.get_dashboard_drilldown("po", 9, "apspdcl", "month:2026-04")) == 2
    assert models.get_dashboard_drilldown("po", 9, "apspdcl", "officer:bad") == []
    assert models.get_dashboard_drilldown("po", 9, "apspdcl", "unknown") == []
    assert models.get_dashboard_drilldown("po", 9, "apspdcl", "sla_beyond")[0]["metric"] == "sla_beyond"

    bind_db(
        monkeypatch,
        fetchall_items=[
            [
                {
                    "id": 1,
                    "enquiry_type": "preliminary",
                    "source_of_petition": "govt",
                    "assigned_at": datetime(2026, 3, 1),
                    "closed_at": datetime(2026, 3, 5),
                    "converted_to_detailed": 0,
                },
                {
                    "id": 2,
                    "enquiry_type": "detailed",
                    "source_of_petition": "media",
                    "assigned_at": datetime(2026, 1, 1),
                    "closed_at": None,
                    "converted_to_detailed": 0,
                },
            ]
        ],
    )
    monkeypatch.setattr(models, "datetime", FixedDateTime())
    stats = models._get_sla_stats(models.get_db(), "po", 9)
    assert stats["sla_total"] == 2
    assert stats["sla_within"] == 1
    assert stats["sla_breached"] == 1
    assert stats["sla_in_progress"] == 0


def test_dashboard_drilldown_po_permission_given_branch(monkeypatch):
    monkeypatch.setattr(models, "get_petitions_for_user", lambda *_a, **_k: [])
    bind_db(
        monkeypatch,
        fetchall_items=[
            [{"petition_id": 7}, {"petition_id": 8}],
            [{"id": 8, "created_at": datetime(2026, 4, 1)}, {"id": 7, "created_at": datetime(2026, 3, 1)}],
        ],
    )
    results = models.get_dashboard_drilldown("po", 88, "apspdcl", "po_permission_given")
    assert [row["id"] for row in results] == [8, 7]
