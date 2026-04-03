import os

os.environ["SKIP_SCHEMA_UPDATES"] = "1"

import pytest
from flask import session
from app import app as flask_app
from tests.test_models_db_ops import CursorStub, ConnStub
import app as app_module


@pytest.fixture
def app():
    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-for-routes",
    })
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def bind_db_for_app(monkeypatch, fetchone_items=None, fetchall_items=None, rowcount=1):
    cursor = CursorStub(fetchone_items=fetchone_items, fetchall_items=fetchall_items, rowcount=rowcount)
    conn = ConnStub(cursor)
    monkeypatch.setattr('models.get_db', lambda: conn)
    monkeypatch.setattr('models.dict_cursor', lambda _conn: cursor)
    return conn, cursor


def issue_login_captcha(client, answer="482753"):
    client.get('/login')
    with client.session_transaction() as sess:
        challenges = dict(sess.get('login_captcha_challenges') or {})
        assert challenges
        token = next(reversed(challenges))
        challenge = dict(challenges[token])
        challenge['answer_digest'] = app_module._login_captcha_answer_digest(token, answer)
        challenge['image_b64'] = app_module.base64.b64encode(
            app_module._build_login_captcha_bmp(answer)
        ).decode('ascii')
        challenges[token] = challenge
        sess['login_captcha_challenges'] = challenges
    return token


def test_login_page_loads(client):
    """Test that the login page loads correctly."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Verify &amp; Sign In' in response.data


def test_login_flow_success_and_logout(client, monkeypatch):
    """Test a successful login and subsequent logout."""
    user_data = {
        'id': 1, 'username': 'testuser', 'password_hash': 'h::password123',
        'full_name': 'Test User', 'role': 'po', 'is_active': True, 'phone': '1234567890'
    }
    monkeypatch.setattr('app.models.authenticate_user', lambda u, p: user_data)
    monkeypatch.setattr('app.models.get_user_by_id', lambda _uid: {
        **user_data,
        'cvo_office': None,
        'email': None,
        'profile_photo': None,
        'session_version': 1,
        'must_change_password': False,
    })
    with client:
        captcha_token = issue_login_captcha(client, "482753")

        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'password123',
            'captcha_answer': '482753',
            'captcha_token': captcha_token,
            'login_action': 'credentials',
        }, follow_redirects=False)

        assert response.status_code == 302
        assert response.headers['Location'].endswith('/dashboard')
        with client.session_transaction() as sess:
            assert sess.get('user_id') == 1

        response = client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'You have been logged out.' in response.data
        with client.session_transaction() as sess:
            assert 'user_id' not in sess


def test_dashboard_requires_login(client):
    """Test that a protected route like the dashboard redirects to login."""
    response = client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'Please login to access this page.' in response.data
    assert b'Verify &amp; Sign In' in response.data


def test_api_inspectors_unauthorized(client):
    """Test that a protected API endpoint returns 401 when not logged in."""
    response = client.get('/api/inspectors/1')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/login')
