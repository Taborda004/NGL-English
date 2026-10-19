import os
import json
import pytest
from pathlib import Path
from auth.cloud_auth import CloudAuthManager, SESSION_CACHE_FILE
from auth.license_manager import LicenseManager, OWNER_BYPASS_KEY


@pytest.fixture
def isolated_cloud_env(tmp_path, monkeypatch):
    """Aisla las rutas locales y el endpoint de red para pruebas de seguridad herméticas."""
    store_file = tmp_path / "cloud_users.json"
    session_file = tmp_path / ".session_cache.json"

    monkeypatch.setattr(CloudAuthManager, "get_users_store_path", classmethod(lambda cls: store_file))
    monkeypatch.setattr("auth.cloud_auth.SESSION_CACHE_FILE", session_file)
    monkeypatch.setattr("auth.cloud_auth.DEFAULT_CLOUD_ENDPOINT", "")
    monkeypatch.setenv("AUTH_CLOUD_ENDPOINT", "")

    return {
        "store": store_file,
        "session": session_file
    }


def test_tampered_cached_session_hwid_purged(isolated_cloud_env, monkeypatch):
    """
    Auditoría de Seguridad: Si un atacante copia un archivo de sesión (.ngl_assistant_session.json)
    de otra máquina con un HWID distinto, el sistema debe detectarlo, rechazarlo y eliminar el archivo.
    """
    session_file = isolated_cloud_env["session"]
    legitimate_hwid = "NGL-ORIGINAL-PC-1111"
    attacker_hwid = "NGL-ATTACKER-PC-9999"

    # Simular sesión generada en la máquina de la víctima
    session_file.write_text(json.dumps({
        "email": "victima@test.com",
        "name": "Victima Legítima",
        "hwid": legitimate_hwid,
        "logged_in_at": "2026-10-18T00:00:00Z"
    }), encoding="utf-8")

    # Atacante intenta ejecutar en su equipo con HWID diferente
    monkeypatch.setattr(LicenseManager, "get_machine_hwid", classmethod(lambda cls: attacker_hwid))

    cached = CloudAuthManager.get_cached_session()
    # Debe ser rechazado
    assert cached is None
    # El archivo falsificado debe ser purgado del disco inmediatamente
    assert not session_file.exists()


def test_unauthorized_user_blocked_at_login(isolated_cloud_env):
    """
    Auditoría de Seguridad: Un usuario sin aprobación explícita debe ser
    bloqueado en el punto de autenticación.
    """
    CloudAuthManager.request_access("Pedro Prueba", "pedro@test.com")
    auth_ok, msg, _ = CloudAuthManager.authenticate_user("pedro@test.com")
    assert auth_ok is False
    assert "PENDIENTE" in msg


def test_cloned_hwid_security_violation(isolated_cloud_env, monkeypatch):
    """
    Auditoría de Seguridad: Clonación de credenciales. Si un usuario aprobado
    comparte su correo con otra persona en otra máquina, la otra máquina debe ser bloqueada.
    """
    email = "carlos@compartido.com"
    pc_1_hwid = "NGL-PC-AUTORIZADA-0001"
    pc_2_hwid = "NGL-PC-CLONADA-0002"

    monkeypatch.setattr(LicenseManager, "get_machine_hwid", classmethod(lambda cls: pc_1_hwid))
    CloudAuthManager.request_access("Carlos", email)
    CloudAuthManager.admin_approve_user(email)

    # Primer login en PC 1: se vincula a PC 1
    ok1, msg1, data1 = CloudAuthManager.authenticate_user(email)
    assert ok1 is True
    assert data1["hwid"] == pc_1_hwid

    # Intento de acceso en PC 2 con las mismas credenciales
    monkeypatch.setattr(LicenseManager, "get_machine_hwid", classmethod(lambda cls: pc_2_hwid))
    ok2, msg2, data2 = CloudAuthManager.authenticate_user(email)
    assert ok2 is False
    assert "Violación de seguridad y clonación detectada" in msg2


def test_env_file_is_git_ignored():
    """
    Auditoría de Seguridad: El archivo .env que contiene las credenciales
    reales jamás debe ser rastreado o subido a Git.
    """
    gitignore_path = Path(__file__).resolve().parent.parent / ".gitignore"
    assert gitignore_path.exists()
    content = gitignore_path.read_text(encoding="utf-8")
    assert ".env" in content
    assert "*.env" in content


def test_owner_key_tampering_rejected(monkeypatch):
    """
    Auditoría de Seguridad: La clave maestra no debe ser eludible por prefijos o mutaciones,
    y se valida mediante hash SHA-256 seguro.
    """
    import hashlib
    test_key = "NGL-TEST-OWNER-KEY-12345"
    test_hash = hashlib.sha256(test_key.encode("utf-8")).hexdigest()
    monkeypatch.setattr("auth.license_manager.OWNER_KEY_HASH", test_hash)
    monkeypatch.setenv("LICENSE_KEY", "")
    assert LicenseManager.is_owner_key(test_key) is True
    tampered_keys = [
        test_key + "-EXTRA",
        test_key[:-5],
        "WRONG-KEY-PREFIX",
        "",
        " "
    ]
    for tk in tampered_keys:
        assert LicenseManager.is_owner_key(tk) is False
        is_valid, _, _ = LicenseManager.verify(license_key=tk)
        assert is_valid is False


def test_sanitized_key_prevents_firebase_injection():
    """
    Auditoría de Seguridad: Comprueba que caracteres prohibidos en Firebase
    (puntos, arrobas, barras, corchetes, signos de dólar) sean sanitizados
    para evitar inyección de rutas en la base de datos NoSQL.
    """
    malicious_email = "test/../admin[$#]@hack.com"
    sanitized = CloudAuthManager._email_to_key(malicious_email)
    forbidden = [".", "@", "$", "#", "[", "]", "/"]
    for char in forbidden:
        assert char not in sanitized
