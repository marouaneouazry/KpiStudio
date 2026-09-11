import pytest
import os
import sys
import json
import shutil
from fastapi.testclient import TestClient

# Ensure app is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "app")))

os.environ["ALLOW_MOCK_LDAP"] = "True"
os.environ["JWT_SECRET"] = "cw2UsTpOKHjXPLq9eB792B7LaftCgV0dtXNdSHGeetBqt3gNP365svudl5_LMmohkorvV2pH7jGHALqPtdH46A"

from app.main import app
from app.auth.security import create_access_token
from app.core.config import settings

client = TestClient(app)

@pytest.fixture(autouse=True)
def preserve_sla_mapping():
    """Backup and restore config/sla_mapping.json to keep real config untouched."""
    sla_path = settings.SLA_MAPPING_PATH
    backup_path = sla_path + ".test_backup"
    if os.path.exists(sla_path):
        shutil.copyfile(sla_path, backup_path)
    yield
    if os.path.exists(backup_path):
        shutil.copyfile(backup_path, sla_path)
        os.remove(backup_path)

@pytest.fixture
def auth_headers():
    token = create_access_token({"sub": "test_admin", "display_name": "Admin Test"})
    return {"Authorization": f"Bearer {token}"}

def test_sla_mapping_unauthenticated_returns_401():
    res = client.get("/api/sla-mapping")
    assert res.status_code == 401

def test_sla_page_unauthenticated_redirects():
    res = client.get("/sla", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert "/login" in res.headers.get("location", "")

def test_sla_page_authenticated_returns_html(auth_headers):
    # Cookie or Bearer
    token = auth_headers["Authorization"].split(" ")[1]
    client.cookies.set("access_token", token)
    res = client.get("/sla")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "Référentiel SLA Sous-domaines" in res.text

def test_get_sla_mapping(auth_headers):
    res = client.get("/api/sla-mapping", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "2" in data
    assert "5" in data
    assert "15" in data
    assert isinstance(data["2"], list)

def test_post_sla_mapping_validation(auth_headers):
    # Missing name
    res = client.post("/api/sla-mapping", json={"name": "", "sla": "5"}, headers=auth_headers)
    assert res.status_code == 400

    # Invalid SLA category
    res = client.post("/api/sla-mapping", json={"name": "Test", "sla": "10"}, headers=auth_headers)
    assert res.status_code == 400

def test_crud_sla_lifecycle(auth_headers):
    test_domain = "TEST_AUTOMATED_SUBDOMAIN_XYZ"

    # 1. CREATE in 5j
    res = client.post("/api/sla-mapping", json={"name": test_domain, "sla": "5"}, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert test_domain in data["sla_mapping"]["5"]

    # 2. UPDATE: Move to 2j and rename
    updated_domain = "TEST_AUTOMATED_SUBDOMAIN_XYZ_RENAMED"
    res = client.put("/api/sla-mapping", json={
        "old_name": test_domain,
        "new_name": updated_domain,
        "old_sla": "5",
        "new_sla": "2"
    }, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert test_domain not in data["sla_mapping"]["5"]
    assert updated_domain in data["sla_mapping"]["2"]

    # 3. DELETE
    res = client.delete(f"/api/sla-mapping/2/{updated_domain}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert updated_domain not in data["sla_mapping"]["2"]

    # 4. DELETE nonexistent should return 404
    res = client.delete(f"/api/sla-mapping/2/{updated_domain}", headers=auth_headers)
    assert res.status_code == 404
