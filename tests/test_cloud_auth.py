import json
import pytest
from pathlib import Path
from auth.cloud_auth import CloudAuthManager
from auth.license_manager import LicenseManager


@pytest.fixture
def mock_cloud_store(tmp_path, monkeypatch):
    store_file = tmp_path / "cloud_users.json"
    monkeypatch.setattr(CloudAuthManager, "get_users_store_path", classmethod(lambda cls: store_file))
    return store_file


def test_request_access_success(mock_cloud_store):
    success, msg = CloudAuthManager.request_access("Carlos Gomez", "carlos@test.com", "Grupo 4")
    assert success is True
    assert "correctamente" in msg

    users = CloudAuthManager.admin_list_users()
    assert len(users) == 1
    assert users[0]["email"] == "carlos@test.com"
    assert users[0]["status"] == "pending"


def test_request_access_invalid_email(mock_cloud_store):
    success, msg = CloudAuthManager.request_access("Carlos Gomez", "not-an-email")
    assert success is False
    assert "válido" in msg


def test_login_pending_user(mock_cloud_store):
    CloudAuthManager.request_access("Carlos Gomez", "carlos@test.com")
    auth_ok, msg, data = CloudAuthManager.authenticate_user("carlos@test.com")
    assert auth_ok is False
    assert "PENDIENTE" in msg


def test_admin_approve_and_login(mock_cloud_store):
    CloudAuthManager.request_access("Carlos Gomez", "carlos@test.com")
    appr_ok, appr_msg = CloudAuthManager.admin_approve_user("carlos@test.com")
    assert appr_ok is True

    auth_ok, msg, data = CloudAuthManager.authenticate_user("carlos@test.com")
    assert auth_ok is True
    assert "Bienvenido" in msg
    assert data["status"] == "approved"
    assert data["hwid"] == LicenseManager.get_machine_hwid()


def test_login_sharing_violation_mismatched_hwid(mock_cloud_store, monkeypatch):
    CloudAuthManager.request_access("Carlos Gomez", "carlos@test.com")
    CloudAuthManager.admin_approve_user("carlos@test.com")
    # First login binds to this machine
    CloudAuthManager.authenticate_user("carlos@test.com")

    # Simulate another machine trying to log in with Carlos's email
    monkeypatch.setattr(LicenseManager, "get_machine_hwid", classmethod(lambda cls: "NGL-FOREIGN-PC-8888"))
    auth_ok, msg, data = CloudAuthManager.authenticate_user("carlos@test.com")
    assert auth_ok is False
    assert "Violación de seguridad y clonación" in msg


def test_admin_revoke_user(mock_cloud_store):
    CloudAuthManager.request_access("Carlos Gomez", "carlos@test.com")
    CloudAuthManager.admin_approve_user("carlos@test.com")
    
    rev_ok, rev_msg = CloudAuthManager.admin_revoke_user("carlos@test.com")
    assert rev_ok is True

    auth_ok, msg, data = CloudAuthManager.authenticate_user("carlos@test.com")
    assert auth_ok is False
    assert "revocada" in msg


def test_admin_reset_hwid(mock_cloud_store, monkeypatch):
    CloudAuthManager.request_access("Carlos Gomez", "carlos@test.com")
    CloudAuthManager.admin_approve_user("carlos@test.com")
    CloudAuthManager.authenticate_user("carlos@test.com")

    # Reset HWID
    res_ok, res_msg = CloudAuthManager.admin_reset_hwid("carlos@test.com")
    assert res_ok is True

    # Now a new machine can bind
    monkeypatch.setattr(LicenseManager, "get_machine_hwid", classmethod(lambda cls: "NGL-NEW-LAPTOP-5555"))
    auth_ok, msg, data = CloudAuthManager.authenticate_user("carlos@test.com")
    assert auth_ok is True
    assert data["hwid"] == "NGL-NEW-LAPTOP-5555"
