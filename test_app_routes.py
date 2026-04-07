import pytest
from flask import session
from app import app as flask_app
from tests.test_models_db_ops import CursorStub, ConnStub


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


def test_login_page_loads(client):
    """Test that the login page loads correctly."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Sign In To Your Account' in response.data


def test_login_flow_success_and_logout(client, monkeypatch):
    """Test a successful login and subsequent logout."""
    user_data = {
        'id': 1, 'username': 'testuser', 'password_hash': 'h::password123',
        'full_name': 'Test User', 'role': 'po', 'is_active': True, 'phone': '1234567890'
    }
    monkeypatch.setattr('models.check_password_hash', lambda h, p: h == f"h::{p}")
    bind_db_for_app(monkeypatch, fetchone_items=[user_data])
    monkeypatch.setattr('app._is_otp_login_enabled', lambda: False)

    with client:
        # Prime the session with a valid CSRF token and captcha
        with client.session_transaction() as sess:
            sess['login_captcha_a'] = 5
            sess['login_captcha_b'] = 3
            sess['login_captcha_answer'] = 8

        # Attempt login
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'password123',
            'captcha_answer': '8'
        }, follow_redirects=True)

        assert response.status_code == 200
        assert b'Welcome, Test User!' in response.data
        assert b'Dashboard' in response.data
        with client.session_transaction() as sess:
            assert sess.get('user_id') == 1

        # Test logout
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
    assert b'Sign In' in response.data


def test_api_inspectors_unauthorized(client):
    """Test that a protected API endpoint returns 401 when not logged in."""
    response = client.get('/api/inspectors/1')
    assert response.status_code == 401
    assert response.json == {'message': 'Please login to access this page.'}