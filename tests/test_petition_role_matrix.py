import time

import app as app_module
import pytest

from conftest import login_as


@pytest.mark.parametrize(
    "path",
    [
        "/petitions",
        "/petitions/new",
        "/petitions/1",
        "/petitions/import",
    ],
)
def test_petition_endpoints_require_login(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.headers.get("Location", "").endswith("/login")


def test_petitions_reject_expired_session(client):
    login_as(client, role="po")

    with client.session_transaction() as session_data:
        now_ts = int(time.time())
        session_data["auth_issued_at"] = now_ts
        session_data["auth_last_seen_at"] = now_ts - app_module._session_inactivity_seconds() - 5

    response = client.get("/petitions")
    assert response.status_code == 302
    assert response.headers.get("Location", "").endswith("/login")


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("super_admin", True),
        ("data_entry", True),
        ("po", False),
        ("inspector", False),
        ("cvo_apspdcl", False),
        ("jmd", False),
        ("cmd_apspdcl", False),
    ],
)
def test_petition_new_role_matrix(client, role, allowed):
    login_as(client, role=role)
    response = client.get("/petitions/new")

    if allowed:
        assert response.status_code == 200
    else:
        assert response.status_code == 302
        assert response.headers.get("Location", "").endswith("/dashboard")


@pytest.mark.parametrize(
    "role,allowed",
    [
        ("super_admin", True),
        ("po", True),
        ("data_entry", False),
        ("inspector", False),
        ("cvo_apspdcl", False),
        ("jmd", False),
    ],
)
def test_petitions_import_role_matrix(client, role, allowed):
    login_as(client, role=role)
    response = client.get("/petitions/import")

    if allowed:
        assert response.status_code == 200
    else:
        assert response.status_code == 302
        assert response.headers.get("Location", "").endswith("/dashboard")


def test_petition_view_and_action_forbidden_when_access_scope_fails(client, monkeypatch):
    login_as(client, role="po")
    monkeypatch.setattr(
        app_module.models,
        "can_user_access_petition",
        lambda user_id, user_role, cvo_office, petition_id: False,
        raising=False,
    )

    view_response = client.get("/petitions/1")
    assert view_response.status_code == 302
    assert view_response.headers.get("Location", "").endswith("/petitions")

    action_response = client.post("/petitions/1/action", data={"action": "send_for_permission"})
    assert action_response.status_code == 302
    assert action_response.headers.get("Location", "").endswith("/petitions")


def test_public_petition_search_no_login_required(client, monkeypatch):
    """Public petition search should work without login and return minimal info (no PII)."""
    monkeypatch.setattr(
        app_module.models,
        "public_petition_status_lookup",
        lambda q, field, office: [
            {
                "sno": "VIG/PO/2026/0001",
                "status": "permission_approved",
                "received_date": __import__("datetime").date(2026, 2, 17),
                "received_at": "jmd_office",
            }
        ],
        raising=False,
    )

    # No login needed for public search
    response = client.get("/petition-search?q=VIG/PO&field=sno")
    assert response.status_code == 200
    json_data = response.get_json()
    assert "results" in json_data
    assert len(json_data["results"]) == 1
    assert json_data["results"][0]["sno"] == "VIG/PO/2026/0001"
    assert json_data["results"][0]["status"] == "Permission Approved"


def test_public_petition_search_validates_input(client, monkeypatch):
    """Public petition search should validate minimum query length."""
    monkeypatch.setattr(
        app_module.models,
        "public_petition_status_lookup",
        lambda q, field, office: [],
        raising=False,
    )
    response = client.get("/petition-search?q=VI")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["results"] == []
    assert "at least 3 characters" in json_data.get("message", "").lower()


def test_public_petition_search_database_error_handled(client, monkeypatch):
    """Public petition search should gracefully handle database errors."""
    monkeypatch.setattr(
        app_module.models,
        "public_petition_status_lookup",
        lambda q, field, office: (_ for _ in ()).throw(Exception("DB connection failed")),
        raising=False,
    )

    response = client.get("/petition-search?q=VIG/PO/2026/0001&field=sno")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["results"] == []
    assert "Could not connect to database" in json_data.get("message", "")
