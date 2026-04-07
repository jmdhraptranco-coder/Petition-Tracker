from datetime import date, datetime

import app as app_module

from conftest import login_as


class RouteModelsStub:
    def __init__(self):
        self.user = None

    def get_user_by_id(self, user_id):
        return {
            "id": user_id,
            "username": "tester",
            "full_name": "Tester",
            "role": "po",
            "cvo_office": None,
            "phone": "9999999999",
            "email": "t@example.com",
            "profile_photo": None,
            "session_version": 1,
            "is_active": True,
        }

    def authenticate_user(self, _u, _p):
        return self.user


def _issue_captcha(client, answer="482753", issued_at=None):
    client.get("/login")
    with client.session_transaction() as sess:
        challenges = dict(sess.get("login_captcha_challenges") or {})
        token = next(reversed(challenges))
        challenge = dict(challenges[token])
        challenge["answer_digest"] = app_module._login_captcha_answer_digest(token, answer)
        challenge["image_b64"] = app_module.base64.b64encode(app_module._build_login_captcha_bmp(answer)).decode("ascii")
        if issued_at is not None:
            challenge["issued_at"] = issued_at
        challenges[token] = challenge
        sess["login_captcha_challenges"] = challenges
        return token


def test_sla_dashboard_employee_and_analysis_routes(monkeypatch):
    stub = RouteModelsStub()
    stub.get_sla_dashboard_data_for_user = lambda *_a, **_k: {
        "summary": {"sla_total": 2},
        "employees": [{"officer_id": 7, "officer_name": "Officer One", "within": 1, "beyond": 1, "in_progress": 0}],
        "petitions": [{"id": 1, "sno": "VIG/1", "petitioner_name": "Ravi", "subject": "Sub", "status": "received", "sla_days": 15, "elapsed_days": 20, "sla_state": "beyond", "sla_bucket": "beyond", "closed_at": None, "assigned_at": datetime(2026, 2, 17)}],
    }
    stub.get_sla_employee_profile_for_user = lambda role, uid, office, officer_id: {
        "unauthorized": officer_id == 99,
        "officer": {"id": officer_id, "full_name": "Officer One"},
        "summary": {"total": 1},
        "petitions": [{"id": 1, "sno": "VIG/1", "petitioner_name": "Ravi", "subject": "Sub", "status": "received", "sla_days": 15, "elapsed_days": 20, "sla_state": "beyond", "sla_bucket": "beyond", "closed_at": None}],
    }
    monkeypatch.setattr(app_module, "models", stub)
    monkeypatch.setattr(
        app_module,
        "get_petitions_for_user_cached",
        lambda *_a, **_k: [
            {"id": 1, "received_date": date(2026, 2, 17), "petition_type": "bribe", "source_of_petition": "media", "received_at": "jmd_office", "target_cvo": "apspdcl", "assigned_inspector_id": 7, "inspector_name": "Officer One", "status": "closed"},
            {"id": 2, "received_date": date(2026, 2, 18), "petition_type": "other", "source_of_petition": "govt", "received_at": "cvo_apepdcl_vizag", "target_cvo": "apepdcl", "assigned_inspector_id": 8, "inspector_name": "Officer Two", "status": "assigned_to_inspector"},
        ],
    )
    monkeypatch.setattr(
        app_module,
        "_build_analysis_report_data",
        lambda petitions: {
            "total": len(petitions),
            "closed": 1,
            "lodged": 0,
            "active": max(0, len(petitions) - 1),
            "terminal": 1,
            "resolution_rate": 50,
            "sla_within": 1,
            "sla_beyond": 0,
            "sla_tracked": 1,
            "sla_compliance": 100,
            "overdue_count": 0,
            "direct_count": 1,
            "permission_count": 0,
            "enquiry_types": {"preliminary": 0, "detailed": len(petitions)},
            "status_breakdown": [],
            "type_breakdown": [],
            "source_breakdown": [],
            "dept_stats": [],
            "officer_stats": [],
            "best_performers": [],
            "top_defaulters": [],
            "talking_points": [],
            "monthly_trend": [],
            "dept_insights": [],
            "type_insights": [],
            "source_insights": [],
            "status_insights": [],
            "officer_insights": [],
            "sla_insights": [],
        },
    )
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="po")
        assert client.get("/sla-dashboard").status_code == 200
        assert client.get("/sla-dashboard/employee/99").status_code == 302
        assert client.get("/sla-dashboard/employee/7").status_code == 200
        assert client.get("/analysis-report?from_date=2026-02-18&to_date=2026-02-17&petition_type=bribe&source_of_petition=media&received_at=jmd_office&target_cvo=apspdcl&officer_id=7").status_code == 200


def test_petitions_list_sorting_and_auth_edge_branches(monkeypatch):
    stub = RouteModelsStub()
    stub.get_all_petitions = lambda status_filter=None, enquiry_mode="all": [
        {"id": 1, "sno": "VIG/1", "subject": "Sub One", "petitioner_name": "Ravi", "efile_no": None, "current_handler_id": 1, "handler_name": "PO", "received_date": date(2026, 2, 17), "status": "received"},
        {"id": 2, "sno": "VIG/2", "subject": "Sub Two", "petitioner_name": "Sita", "efile_no": "EO-2", "current_handler_id": 1, "handler_name": "PO", "received_date": date(2026, 2, 18), "status": "received"},
    ]
    stub.get_petitions_for_user = lambda *_a, **_k: [{"id": 3, "sno": "VIG/3", "subject": "Sub Three", "petitioner_name": "Kiran", "efile_no": None, "current_handler_id": 1, "handler_name": "PO", "received_date": date(2026, 2, 19), "status": "received"}]
    stub.get_sla_evaluation_rows = lambda petitions: [{"id": 1, "elapsed_days": 5}, {"id": 2, "elapsed_days": 9}, {"id": 3, "elapsed_days": 1}]
    stub.get_latest_enquiry_report_accident_details = lambda ids: {2: {"accident_type": "fatal", "deceased_category": "departmental", "departmental_type": "regular", "deceased_count": 1}}
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        login_as(client, role="super_admin")
        assert client.get("/petitions?status=beyond_sla").status_code == 200

        monkeypatch.setattr(app_module, "_is_login_blocked", lambda: (True, 60))
        token = _issue_captcha(client)
        blocked = client.post("/login", data={"username": "u", "password": "p", "captcha_answer": "482753", "captcha_token": token})
        assert blocked.status_code == 302


def test_login_captcha_image_and_login_failure_edges(monkeypatch):
    stub = RouteModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    real_time = __import__("time").time
    with app_module.app.test_client() as client:
        assert client.get("/auth/login-captcha/bad-token").status_code == 404

        token = _issue_captcha(client, issued_at=1)
        monkeypatch.setattr(app_module.time, "time", lambda: 1 + app_module.LOGIN_CAPTCHA_TTL_SECONDS + 10)
        assert client.get(f"/auth/login-captcha/{token}").status_code == 404

    monkeypatch.setattr(app_module.time, "time", real_time)
    with app_module.app.test_client() as client:
        stub.user = {"id": 5, "username": "u5", "full_name": "Login User", "role": "po", "phone": "9999999999", "email": None, "profile_photo": None, "must_change_password": False}
        token = _issue_captcha(client)
        response = client.post("/login", data={"username": "u5", "password": "p", "captcha_answer": "482753", "captcha_token": token})
        assert response.status_code == 302


def test_login_success_creates_session_immediately(monkeypatch):
    stub = RouteModelsStub()
    stub.user = {"id": 5, "username": "u5", "full_name": "Login User", "role": "po", "phone": "9999999999", "email": None, "profile_photo": None, "must_change_password": False}
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True

    with app_module.app.test_client() as client:
        token = _issue_captcha(client)
        response = client.post("/login", data={"username": "u5", "password": "p", "captcha_answer": "482753", "captcha_token": token})
        assert response.status_code == 302

        with client.session_transaction() as sess:
            assert sess.get("user_id") == 5


def test_legacy_signup_and_password_reset_routes_redirect_to_login(monkeypatch):
    stub = RouteModelsStub()
    monkeypatch.setattr(app_module, "models", stub)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as client:
        signup_response = client.post("/auth/request-signup", follow_redirects=True)
        assert signup_response.status_code == 200
        assert b"Self signup is disabled." in signup_response.data

        reset_response = client.get("/auth/forgot-password/set", follow_redirects=True)
        assert reset_response.status_code == 200
        assert b"Direct password reset is unavailable." in reset_response.data
