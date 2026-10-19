"""
Módulo de Gestión y Verificación de Licencias Criptográficas Remotas.
Soporte multiplataforma reforzado (Windows, macOS, Linux) con detección multifactorial
de hardware (Node-Locking 1:1), firma criptográfica HMAC-SHA256 anti-falsificación
y verificación de marcas de tiempo del servidor contra manipulación de reloj.
"""

import os
import sys
import uuid
import platform
import hashlib
import hmac
import json
import urllib.request
import urllib.error
import subprocess
from datetime import datetime, timezone
import email.utils
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

DEFAULT_ENDPOINT = "https://raw.githubusercontent.com/Taborda004/NGL-English/main/auth/licenses.json"
OWNER_BYPASS_KEY = "OWNER-TABORDA004-MASTER"
ROOT_SIGNATURE_SALT = "NGL-CORE-AUTH-SALT-2026-STABLE"


class LicenseManager:
    """Administrador criptográfico multiplataforma de licencias y hardware binding."""

    _ORIGINAL_VERIFY = None

    @classmethod
    def _collect_hardware_fingerprint(cls) -> str:
        """
        Recolecta múltiples fuentes independientes de entropía de hardware físico
        en Windows, macOS y Linux para crear una raíz de confianza inviolable.
        """
        sys_name = platform.system()
        entropy = []

        # 1. Identificadores de firmware y sistema operativo
        if sys_name == "Windows":
            # Registry MachineGuid
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                if guid:
                    entropy.append(f"WINGUID:{str(guid).strip()}")
            except Exception:
                pass

            # Motherboard BIOS UUID
            try:
                cmd = ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystemProduct).UUID"]
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
                if out and out != "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF":
                    entropy.append(f"WINBIOS:{out}")
            except Exception:
                pass

        elif sys_name == "Darwin":  # macOS
            try:
                cmd = ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"]
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
                for line in out.splitlines():
                    if "IOPlatformUUID" in line:
                        uuid_val = line.split("=")[-1].strip().strip('"')
                        if uuid_val:
                            entropy.append(f"MACUUID:{uuid_val}")
                    elif "IOPlatformSerialNumber" in line:
                        serial_val = line.split("=")[-1].strip().strip('"')
                        if serial_val:
                            entropy.append(f"MACSN:{serial_val}")
            except Exception:
                pass

        elif sys_name == "Linux":
            # Systemd machine-id y DMI product_uuid
            linux_paths = [
                ("/etc/machine-id", "LNXID"),
                ("/var/lib/dbus/machine-id", "DBUSID"),
                ("/sys/class/dmi/id/product_uuid", "DMIUUID"),
                ("/sys/class/dmi/id/board_serial", "BOARD")
            ]
            for p_path, tag in linux_paths:
                if os.path.exists(p_path):
                    try:
                        with open(p_path, "r", encoding="utf-8") as f:
                            val = f.read().strip()
                            if val:
                                entropy.append(f"{tag}:{val}")
                    except Exception:
                        pass

        # 2. Entropía física de red y procesador (común a todos los SO)
        try:
            entropy.append(f"MAC:{uuid.getnode()}")
        except Exception:
            pass

        entropy.append(f"NODE:{platform.node()}")
        entropy.append(f"SYS:{sys_name}")
        entropy.append(f"ARCH:{platform.machine()}")
        entropy.append(f"PROC:{platform.processor()}")

        raw = "|".join(entropy)
        return raw

    @classmethod
    def get_machine_hwid(cls) -> str:
        """
        Genera el identificador único de hardware (HWID) en formato NGL-XXXX-XXXX-XXXX-XXXX.
        """
        try:
            raw = cls._collect_hardware_fingerprint()
            digest = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
            return f"NGL-{digest[:4]}-{digest[4:8]}-{digest[8:12]}-{digest[12:16]}"
        except Exception:
            fallback = hashlib.sha256(b"FALLBACK_RESCUE_DEVICE").hexdigest().upper()
            return f"NGL-{fallback[:4]}-{fallback[4:8]}-{fallback[8:12]}-{fallback[12:16]}"

    @classmethod
    def compute_signature(cls, payload: Dict[str, Any], salt: str = ROOT_SIGNATURE_SALT) -> str:
        """Calcula una firma criptográfica HMAC-SHA256 determinista para un payload."""
        data_str = json.dumps(payload, sort_keys=True)
        return hmac.new(salt.encode("utf-8"), data_str.encode("utf-8"), hashlib.sha256).hexdigest()

    @classmethod
    def verify_signature(cls, payload: Dict[str, Any], signature: str, salt: str = ROOT_SIGNATURE_SALT) -> bool:
        """Verifica en tiempo constante una firma criptográfica para evitar ataques de canal lateral."""
        expected = cls.compute_signature(payload, salt)
        return hmac.compare_digest(expected.lower(), (signature or "").lower())

    @classmethod
    def derive_session_key(cls, hwid: str, license_key: str, salt: str = ROOT_SIGNATURE_SALT) -> str:
        """Deriva una clave de sesión criptográfica vinculada al hardware físico y la licencia."""
        combo = f"{hwid}:{license_key}:{salt}"
        return hashlib.sha256(combo.encode("utf-8")).hexdigest()

    @classmethod
    def fetch_remote_registry(cls, endpoint_url: str, timeout: float = 6.0) -> Tuple[Optional[Dict[str, Any]], Optional[datetime]]:
        """
        Descarga el registro de licencias desde el endpoint remoto en la nube
        y captura la marca de tiempo oficial del servidor HTTP (Date header) para evitar reloj falseado.
        """
        try:
            req = urllib.request.Request(
                endpoint_url,
                headers={"User-Agent": "NGL-English-Assistant-SecureAuth/2.0", "Cache-Control": "no-cache"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    data = response.read().decode("utf-8")
                    date_header = response.headers.get("Date")
                    server_time = None
                    if date_header:
                        try:
                            server_time = email.utils.parsedate_to_datetime(date_header)
                        except Exception:
                            pass
                    return json.loads(data), server_time
        except Exception:
            return None, None
        return None, None

    @classmethod
    def verify(
        cls,
        license_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        local_fallback_file: Optional[Path] = None,
        strict_clock_check: bool = False
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Valida la autorización de ejecución mediante comprobación multifactorial en la nube,
        enlace exclusivo de hardware 1:1, validación de integridad y firmas digitales.
        """
        hwid = cls.get_machine_hwid()
        key = (license_key if license_key is not None else os.getenv("LICENSE_KEY", "")).strip()
        url = (endpoint_url or os.getenv("AUTH_ENDPOINT_URL", DEFAULT_ENDPOINT)).strip()

        # 1. Validación de clave maestra del autor
        if key == OWNER_BYPASS_KEY:
            session_key = cls.derive_session_key(hwid, key)
            return True, "Acceso concedido mediante credencial maestra del propietario.", {
                "hwid": hwid,
                "role": "owner",
                "mode": "master_key",
                "session_key": session_key
            }

        # 2. Descarga del registro remoto
        registry, server_time = cls.fetch_remote_registry(url)

        # Fallback local únicamente en entorno de desarrollo/pruebas
        if registry is None and local_fallback_file and local_fallback_file.exists():
            try:
                with open(local_fallback_file, "r", encoding="utf-8") as f:
                    registry = json.load(f)
            except Exception:
                registry = None

        if registry is None:
            return False, (
                "No se pudo establecer conexión con el servidor de validación de licencias. "
                "Se requiere conexión activa a Internet para validar la autorización de uso."
            ), {"hwid": hwid, "reason": "offline_or_unreachable"}

        # 3. Comprobación de manipulación de reloj (Anti-Clock-Rollback)
        if strict_clock_check and server_time:
            local_now = datetime.now(timezone.utc)
            skew_seconds = abs((local_now - server_time).total_seconds())
            if skew_seconds > 86400:  # Más de 24 horas de diferencia con el servidor
                return False, (
                    "Manipulación de fecha/reloj detectada en el sistema local. "
                    "Ajusta la fecha y hora de tu equipo a la hora oficial de Internet."
                ), {"hwid": hwid, "reason": "clock_tampering_detected"}

        # 4. Comprobación del estado general del servicio
        if not registry.get("system_active", True):
            msg = registry.get("broadcast_message", "El software ha sido desactivado temporalmente por el propietario.")
            return False, msg, {"hwid": hwid, "reason": "system_disabled"}

        # 5. Listas de bloqueo global (Banned)
        banned_hwids = [h.strip().upper() for h in registry.get("banned_hwids", [])]
        banned_keys = [k.strip().upper() for k in registry.get("banned_keys", [])]

        if hwid.upper() in banned_hwids:
            return False, "Este equipo físico ha sido revocado permanentemente por el propietario.", {
                "hwid": hwid,
                "reason": "hwid_banned"
            }

        if key and key.upper() in banned_keys:
            return False, "La clave de licencia introducida ha sido revocada.", {
                "hwid": hwid,
                "reason": "key_banned"
            }

        # 6. Verificación de licencias estructuradas 1:1 (Node-Locking estricto)
        licenses_dict = registry.get("licenses", {})
        if key and isinstance(licenses_dict, dict):
            matched_entry = None
            for lic_k, lic_v in licenses_dict.items():
                if lic_k.strip().upper() == key.upper():
                    matched_entry = (lic_k, lic_v)
                    break

            if matched_entry:
                _, lic_data = matched_entry
                is_active = lic_data.get("active", True) if "active" in lic_data else (lic_data.get("status") == "active")
                if not is_active:
                    return False, "Esta clave de licencia ha sido desactivada por el propietario.", {
                        "hwid": hwid,
                        "key": key,
                        "reason": "license_deactivated"
                    }

                # Validación de firma digital anti-MITM si está presente
                sig = lic_data.get("signature")
                if sig:
                    payload_for_sig = {k: v for k, v in lic_data.items() if k != "signature"}
                    if not cls.verify_signature(payload_for_sig, sig):
                        return False, (
                            "Firma criptográfica de autorización inválida o manipulada. "
                            "Se detectó un intento de falsificación de respuesta."
                        ), {"hwid": hwid, "reason": "cryptographic_signature_invalid"}

                bound_hwid = (lic_data.get("bound_hwid") or "").strip().upper()
                holder = lic_data.get("holder", "Usuario Autorizado")

                # Comprobación de vinculación estricta de hardware
                if bound_hwid and bound_hwid != hwid.upper():
                    return False, (
                        f"Violación de seguridad y clonación detectada: Esta clave de licencia está vinculada "
                        f"exclusivamente al equipo físico ({bound_hwid}) de {holder}. "
                        f"No está permitido compartir credenciales ni transferir la instalación a otros dispositivos. "
                        f"El identificador de este equipo es: {hwid}."
                    ), {
                        "hwid": hwid,
                        "bound_hwid": bound_hwid,
                        "holder": holder,
                        "reason": "hwid_credential_sharing_violation"
                    }

                session_key = cls.derive_session_key(hwid, key)
                return True, f"Licencia de uso exclusivo validada para {holder}.", {
                    "hwid": hwid,
                    "key": key,
                    "holder": holder,
                    "role": "licensed_user_node_locked",
                    "session_key": session_key
                }

        # 7. Listas de autorización por HWID directo
        authorized_hwids = [h.strip().upper() for h in registry.get("authorized_hwids", [])]
        if hwid.upper() in authorized_hwids:
            session_key = cls.derive_session_key(hwid, "HWID_AUTH")
            return True, "Equipo físico autorizado directamente en el servidor de licencias.", {
                "hwid": hwid,
                "role": "authorized_hwid",
                "session_key": session_key
            }

        # 8. Claves simples autorizadas
        authorized_keys = [k.strip().upper() for k in registry.get("authorized_keys", [])]
        if key and key.upper() in authorized_keys:
            session_key = cls.derive_session_key(hwid, key)
            return True, "Licencia validada exitosamente con el servidor.", {
                "hwid": hwid,
                "key": key,
                "role": "licensed_user",
                "session_key": session_key
            }

        # 9. Rechazo por defecto
        return False, (
            "Acceso no autorizado. Este software es privado y requiere el consentimiento de su autor. "
            f"Proporciona tu identificador de equipo (HWID: {hwid}) al propietario para habilitar el acceso."
        ), {"hwid": hwid, "reason": "unauthorized"}

    @classmethod
    def ensure_cli_license(cls, env_path: Path) -> Tuple[bool, str]:
        """
        Verifica interactivamente en terminal si existe una clave válida.
        Si falta, solicita la clave al usuario y la persiste en el archivo .env.
        """
        hwid = cls.get_machine_hwid()
        is_valid, msg, _ = cls.verify()
        if is_valid:
            return True, msg

        print("\n" + "=" * 78)
        print(" CONTROL DE ACCESO Y LICENCIAMIENTO - NGL ENGLISH ASSISTANT")
        print("=" * 78)
        print(f" Identificador de tu equipo (HWID): {hwid}")
        print(" Este programa requiere autorización remota del propietario (Taborda004).")
        print("=" * 78)

        current_key = os.getenv("LICENSE_KEY", "").strip()
        if current_key:
            print(f" Estado de licencia actual: Invalida o no autorizada ('{current_key}')")

        try:
            user_input = input(" Introduce tu Clave de Licencia (o presiona Enter para salir): ").strip()
            if not user_input:
                return False, f"Ejecución cancelada. Tu HWID para solicitar autorización es: {hwid}"

            valid_new, msg_new, _ = cls.verify(license_key=user_input)
            if not valid_new:
                return False, f"La clave introducida no cuenta con autorización activa: {msg_new}"

            cls._save_key_to_env(env_path, user_input)
            os.environ["LICENSE_KEY"] = user_input
            return True, "Licencia activada y guardada correctamente."
        except (KeyboardInterrupt, EOFError):
            return False, "Operación cancelada por el usuario."

    @staticmethod
    def _save_key_to_env(env_path: Path, key: str) -> None:
        """Guarda o actualiza la clave de licencia en el archivo .env."""
        lines = []
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("LICENSE_KEY="):
                new_lines.append(f"LICENSE_KEY={key}\n")
                found = True
            else:
                new_lines.append(line)

        if not found:
            new_lines.append(f"LICENSE_KEY={key}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
