import io

from conftest import login_as


def test_petition_new_jmd_routes_to_po(client):
    login_as(client, role="data_entry")
    payload = {
        "received_date": "2026-02-17",
        "received_at": "jmd_office",
        "petitioner_name": "Anonymous",
        "subject": "Test subject",
        "petition_type": "bribe",
        "source_of_petition": "media",
        "remarks": "x",
    }
    resp = client.post("/petitions/new", data=payload)
    assert resp.status_code == 302
    call_names = [c[0] for c in client.models_stub.calls]
    assert "create_petition" in call_names
    assert "send_for_permission" in call_names
    assert "forward_petition_to_cvo" not in call_names


def test_petition_new_non_jmd_routes_to_cvo(client):
    login_as(client, role="data_entry")
    payload = {
        "received_date": "2026-02-17",
        "received_at": "cvo_apspdcl_tirupathi",
        "target_cvo": "apspdcl",
        "permission_request_type": "direct_enquiry",
        "petitioner_name": "Anonymous",
        "subject": "Test subject",
        "petition_type": "bribe",
        "source_of_petition": "media",
    }
    resp = client.post("/petitions/new", data=payload)
    assert resp.status_code == 302
    call_names = [c[0] for c in client.models_stub.calls]
    assert "create_petition" in call_names
    assert "forward_petition_to_cvo" in call_names
    assert "send_for_permission" not in call_names


def test_petition_new_requires_govt_institution_when_source_is_govt(client):
    login_as(client, role="data_entry")
    payload = {
        "received_date": "2026-02-17",
        "received_at": "jmd_office",
        "petitioner_name": "Anonymous",
        "subject": "Test subject",
        "petition_type": "bribe",
        "source_of_petition": "govt",
    }
    resp = client.post("/petitions/new", data=payload)
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Please select Type of Institution." in body


def test_submit_report_requires_file_when_required(client):
    login_as(client, role="inspector")
    payload = {
        "action": "submit_report",
        "report_text": "Conclusion",
        "recommendation": "Recommendation",
    }
    resp = client.post("/petitions/1/action", data=payload)
    assert resp.status_code == 302
    assert all(name != "submit_enquiry_report" for name, _ in client.models_stub.calls)


def test_submit_report_accepts_valid_pdf(client):
    login_as(client, role="inspector")
    payload = {
        "action": "submit_report",
        "report_text": "Conclusion",
        "recommendation": "Recommendation",
        "report_file": (io.BytesIO(b"%PDF-1.4 test"), "report.pdf"),
    }
    resp = client.post("/petitions/1/action", data=payload, content_type="multipart/form-data")
    assert resp.status_code == 302
    assert any(name == "submit_enquiry_report" for name, _ in client.models_stub.calls)


def test_update_efile_no_blocks_second_update(client, monkeypatch):
    login_as(client, role="po")

    state = {"efile_no": None}

    def get_petition(_petition_id):
        return {
            "id": 1,
            "requires_permission": False,
            "status": "forwarded_to_cvo",
            "efile_no": state["efile_no"],
        }

    def update_efile(_petition_id, _user_id, efile):
        if state["efile_no"]:
            return False
        state["efile_no"] = efile
        return True

    client.models_stub.get_petition_by_id = get_petition
    client.models_stub.po_update_efile_no = update_efile

    first = client.post("/petitions/1/action", data={"action": "update_efile_no", "efile_no": "EO-1"})
    second = client.post("/petitions/1/action", data={"action": "update_efile_no", "efile_no": "EO-2"})
    assert first.status_code == 302
    assert second.status_code == 302
    assert state["efile_no"] == "EO-1"


def test_form_management_requires_super_admin(client):
    login_as(client, role="po")
    resp = client.get("/form-management")
    assert resp.status_code == 302


def test_form_management_update_as_super_admin(client):
    login_as(client, role="super_admin")
    payload = {
        "form_key": "deo_petition",
        "field_key": "subject",
        "label": "Subject Line",
        "field_type": "textarea",
        "is_required": "on",
        "options_text": "",
    }
    resp = client.post("/form-management", data=payload)
    assert resp.status_code == 302
    assert any(name == "upsert_form_field_config" for name, _ in client.models_stub.calls)
