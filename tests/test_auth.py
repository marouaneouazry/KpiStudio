import pytest
from fastapi.testclient import TestClient
import os
import sys

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

# Enable mock LDAP mode for tests before loading app
os.environ["ALLOW_MOCK_LDAP"] = "True"
os.environ["JWT_SECRET"] = "cw2UsTpOKHjXPLq9eB792B7LaftCgV0dtXNdSHGeetBqt3gNP365svudl5_LMmohkorvV2pH7jGHALqPtdH46A"

from app.main import app
from app.auth.security import create_access_token, decode_access_token
from app.auth.config import settings

client = TestClient(app)

def test_jwt_token_create_and_decode():
    data = {"sub": "testuser", "display_name": "Test User", "email": "test@example.com"}
    token = create_access_token(data)
    assert token is not None

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "testuser"
    assert decoded["display_name"] == "Test User"

def test_unauthenticated_access_redirects():
    # Root endpoint / should redirect unauthenticated user to /login
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307 or response.status_code == 302 or response.status_code == 200
    if response.status_code in (302, 307):
        assert "/login" in response.headers.get("location", "")

def test_unauthenticated_api_access_returns_401():
    # Unauthenticated API calls should return 401
    response = client.get("/api/config")
    assert response.status_code == 401

    response = client.get("/api/download/test-job-id")
    assert response.status_code == 401

    response = client.get("/api/auth/me")
    assert response.status_code == 401

def test_jwt_secret_production_missing_raises_error(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    
    from app.core.config import Settings
    s = Settings()
    with pytest.raises(RuntimeError) as exc_info:
        _ = s.JWT_SECRET
    assert "refusing to start" in str(exc_info.value).lower() or "missing" in str(exc_info.value).lower()

def test_jwt_secret_production_default_raises_error(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "default_insecure_jwt_secret_change_me_in_production")
    
    from app.core.config import Settings
    s = Settings()
    with pytest.raises(RuntimeError) as exc_info:
        _ = s.JWT_SECRET
    assert "refusing to start" in str(exc_info.value).lower() or "insecure" in str(exc_info.value).lower()

def test_jwt_secret_production_valid_returns_secret(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "super_secure_production_secret_key_1234567890_64bytes_length")
    
    from app.core.config import Settings
    s = Settings()
    assert s.JWT_SECRET == "super_secure_production_secret_key_1234567890_64bytes_length"

def test_cookie_security_production_defaults(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    monkeypatch.delenv("COOKIE_SAMESITE", raising=False)
    
    from app.core.config import Settings
    s = Settings()
    assert s.COOKIE_SECURE is True
    assert s.COOKIE_SAMESITE == "strict"

def test_login_failed_credentials():
    response = client.post("/api/auth/login", json={
        "username": "user1",
        "password": "invalid"
    })
    assert response.status_code == 401
    assert "detail" in response.json()

def test_login_success_mock_ldap():
    response = client.post("/api/auth/login", json={
        "username": "validuser",
        "password": "validpassword"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "validuser"

    # Check that cookie is set
    assert "access_token" in response.cookies

def test_authenticated_api_access_with_cookie():
    # First login to get cookie
    login_res = client.post("/api/auth/login", json={
        "username": "validuser",
        "password": "validpassword"
    })
    assert login_res.status_code == 200

    # Now make request using cookies from client
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "validuser"

    config_res = client.get("/api/config")
    assert config_res.status_code == 200
    assert "sla_mapping" in config_res.json()

def test_logout():
    # Login first
    client.post("/api/auth/login", json={
        "username": "validuser",
        "password": "validpassword"
    })
    # Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

    # Me should now fail with 401
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 401
