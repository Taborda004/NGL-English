import json
import pytest
from pathlib import Path
from auth.license_manager import LicenseManager, OWNER_BYPASS_KEY


def test_get_machine_hwid_format():
    hwid = LicenseManager.get_machine_hwid()
    assert isinstance(hwid, str)
    assert hwid.startswith("NGL-")
    parts = hwid.split("-")
    assert len(parts) == 5
    assert all(len(p) == 4 for p in parts[1:])


def test_get_machine_hwid_deterministic():
    hwid1 = LicenseManager.get_machine_hwid()
    hwid2 = LicenseManager.get_machine_hwid()
    assert hwid1 == hwid2


def test_owner_bypass_key(monkeypatch):
    monkeypatch.setenv("OWNER_SECRET_KEY", "OWNER-TABORDA004-MASTER")
    is_valid, msg, details = LicenseManager.verify(license_key="OWNER-TABORDA004-MASTER")
    assert is_valid is True
    assert details["role"] == "owner"


def test_registry_valid_key(tmp_path):
    registry_file = tmp_path / "licenses.json"
    registry_file.write_text(json.dumps({
        "system_active": True,
        "authorized_keys": ["KEY-APPROVED-123"],
        "authorized_hwids": [],
        "banned_hwids": [],
        "banned_keys": []
    }), encoding="utf-8")

    is_valid, msg, details = LicenseManager.verify(
        license_key="KEY-APPROVED-123",
        endpoint_url="http://invalid-non-existent-domain-xyz123.test",
        local_fallback_file=registry_file
    )
    assert is_valid is True
    assert details["role"] == "licensed_user"


def test_registry_unauthorized_key(tmp_path):
    registry_file = tmp_path / "licenses.json"
    registry_file.write_text(json.dumps({
        "system_active": True,
        "authorized_keys": ["KEY-APPROVED-123"],
        "authorized_hwids": [],
        "banned_hwids": [],
        "banned_keys": []
    }), encoding="utf-8")

    is_valid, msg, details = LicenseManager.verify(
        license_key="UNKNOWN-KEY",
        endpoint_url="http://invalid-non-existent-domain-xyz123.test",
        local_fallback_file=registry_file
    )
    assert is_valid is False
    assert details["reason"] == "unauthorized"
    assert "HWID" in msg


def test_registry_banned_key(tmp_path):
    registry_file = tmp_path / "licenses.json"
    registry_file.write_text(json.dumps({
        "system_active": True,
        "authorized_keys": ["KEY-BANNED-456"],
        "authorized_hwids": [],
        "banned_hwids": [],
        "banned_keys": ["KEY-BANNED-456"]
    }), encoding="utf-8")

    is_valid, msg, details = LicenseManager.verify(
        license_key="KEY-BANNED-456",
        endpoint_url="http://invalid-non-existent-domain-xyz123.test",
        local_fallback_file=registry_file
    )
    assert is_valid is False
    assert details["reason"] == "key_banned"


def test_registry_system_disabled(tmp_path):
    registry_file = tmp_path / "licenses.json"
    registry_file.write_text(json.dumps({
        "system_active": False,
        "broadcast_message": "Mantenimiento general",
        "authorized_keys": ["KEY-APPROVED-123"],
        "authorized_hwids": [],
        "banned_hwids": [],
        "banned_keys": []
    }), encoding="utf-8")

    is_valid, msg, details = LicenseManager.verify(
        license_key="KEY-APPROVED-123",
        endpoint_url="http://invalid-non-existent-domain-xyz123.test",
        local_fallback_file=registry_file
    )
    assert is_valid is False
    assert details["reason"] == "system_disabled"
    assert "Mantenimiento general" in msg


def test_registry_authorized_hwid(tmp_path, monkeypatch):
    monkeypatch.setenv("LICENSE_KEY", "")
    my_hwid = LicenseManager.get_machine_hwid()
    registry_file = tmp_path / "licenses.json"
    registry_file.write_text(json.dumps({
        "system_active": True,
        "authorized_keys": [],
        "authorized_hwids": [my_hwid],
        "banned_hwids": [],
        "banned_keys": []
    }), encoding="utf-8")

    is_valid, msg, details = LicenseManager.verify(
        license_key="",
        endpoint_url="http://invalid-non-existent-domain-xyz123.test",
        local_fallback_file=registry_file
    )
    assert is_valid is True
    assert details["role"] == "authorized_hwid"


def test_node_locked_license_valid_matching_hwid(tmp_path, monkeypatch):
    monkeypatch.setenv("LICENSE_KEY", "")
    my_hwid = LicenseManager.get_machine_hwid()
    registry_file = tmp_path / "licenses.json"
    registry_file.write_text(json.dumps({
        "system_active": True,
        "licenses": {
            "LIC-ALEX-2026": {
                "holder": "Alex",
                "bound_hwid": my_hwid,
                "status": "active"
            }
        }
    }), encoding="utf-8")

    is_valid, msg, details = LicenseManager.verify(
        license_key="LIC-ALEX-2026",
        endpoint_url="http://invalid-non-existent-domain-xyz123.test",
        local_fallback_file=registry_file
    )
    assert is_valid is True
    assert details["role"] == "licensed_user_node_locked"
    assert details["holder"] == "Alex"


def test_node_locked_license_sharing_violation_mismatched_hwid(tmp_path, monkeypatch):
    monkeypatch.setenv("LICENSE_KEY", "")
    registry_file = tmp_path / "licenses.json"
    registry_file.write_text(json.dumps({
        "system_active": True,
        "licenses": {
            "LIC-ALEX-2026": {
                "holder": "Alex",
                "bound_hwid": "NGL-FOREIGN-PC-9999",
                "status": "active"
            }
        }
    }), encoding="utf-8")

    is_valid, msg, details = LicenseManager.verify(
        license_key="LIC-ALEX-2026",
        endpoint_url="http://invalid-non-existent-domain-xyz123.test",
        local_fallback_file=registry_file
    )
    assert is_valid is False
    assert details["reason"] == "hwid_credential_sharing_violation"
    assert "clonación detectada" in msg.lower()


def test_compute_and_verify_signature():
    payload = {"key": "TEST-KEY-1", "bound_hwid": "NGL-1111-2222-3333-4444", "status": "active"}
    sig = LicenseManager.compute_signature(payload)
    assert isinstance(sig, str)
    assert len(sig) == 64
    assert LicenseManager.verify_signature(payload, sig) is True
    assert LicenseManager.verify_signature(payload, "invalid_sig_1234567890abcdef") is False


def test_tampered_signature_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("LICENSE_KEY", "")
    my_hwid = LicenseManager.get_machine_hwid()
    tampered_entry = {
        "holder": "Attacker",
        "bound_hwid": my_hwid,
        "status": "active",
        "signature": "forged_signature_000000000000000000000000000000000000000000000000000000"
    }
    registry_file = tmp_path / "licenses.json"
    registry_file.write_text(json.dumps({
        "system_active": True,
        "licenses": {"LIC-TAMPERED": tampered_entry}
    }), encoding="utf-8")

    is_valid, msg, details = LicenseManager.verify(
        license_key="LIC-TAMPERED",
        endpoint_url="http://invalid-non-existent-domain-xyz123.test",
        local_fallback_file=registry_file
    )
    assert is_valid is False
    assert details["reason"] == "cryptographic_signature_invalid"
    assert "firma criptográfica" in msg.lower()


def test_derive_session_key_unique_per_device():
    hwid_a = "NGL-AAAA-BBBB-CCCC-DDDD"
    hwid_b = "NGL-1111-2222-3333-4444"
    key = "LIC-TEST-2026"

    session_a = LicenseManager.derive_session_key(hwid_a, key)
    session_b = LicenseManager.derive_session_key(hwid_b, key)

    assert isinstance(session_a, str)
    assert session_a != session_b


