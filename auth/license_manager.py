"""
Módulo de Gestión y Verificación de Licencias Remotas para NGL English Assistant.
Controla el acceso y ejecución del software mediante autorización remota en la nube (HWID / License Key).
"""

import os
import sys
import uuid
import platform
import hashlib
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

DEFAULT_ENDPOINT = "https://raw.githubusercontent.com/Taborda004/NGL-English/main/auth/licenses.json"
OWNER_BYPASS_KEY = "OWNER-TABORDA004-MASTER"


class LicenseManager:
    """Administra la identificación de hardware y la validación de licencias en la nube."""

    @staticmethod
    def _get_platform_uuid() -> str:
        """Obtiene el identificador criptográfico único del sistema operativo."""
        sys_name = platform.system()
        if sys_name == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                return str(guid).strip()
            except Exception:
                pass
        elif sys_name == "Linux":
            for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            return f.read().strip()
                    except Exception:
                        pass
        elif sys_name == "Darwin":
            try:
                import subprocess
                cmd = ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"]
                out = subprocess.check_output(cmd, text=True)
                for line in out.splitlines():
                    if "IOPlatformUUID" in line:
                        return line.split("=")[-1].strip().strip('"')
            except Exception:
                pass
        return ""

    @classmethod
    def get_machine_hwid(cls) -> str:
        """
        Genera un identificador único, determinista e inmutable de hardware (HWID)
        basado en el UUID del sistema operativo, dirección MAC y arquitectura física.
        """
        try:
            plat_uuid = cls._get_platform_uuid()
            mac = str(uuid.getnode())
            node = platform.node()
            system = platform.system()
            machine = platform.machine()
            raw_fingerprint = f"{plat_uuid}:{mac}:{node}:{system}:{machine}"
            digest = hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest().upper()
            return f"NGL-{digest[:4]}-{digest[4:8]}-{digest[8:12]}-{digest[12:16]}"
        except Exception:
            fallback = hashlib.sha256(b"FALLBACK_DEVICE").hexdigest().upper()
            return f"NGL-{fallback[:4]}-{fallback[4:8]}-{fallback[8:12]}-{fallback[12:16]}"

    @classmethod
    def fetch_remote_registry(cls, endpoint_url: str, timeout: float = 6.0) -> Optional[Dict[str, Any]]:
        """
        Descarga el registro de licencias desde el endpoint remoto en la nube.
        Soporta URLs crudas de GitHub, GitHub Gist o endpoints API JSON.
        """
        try:
            req = urllib.request.Request(
                endpoint_url,
                headers={"User-Agent": "NGL-English-Assistant-Auth/1.0", "Cache-Control": "no-cache"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    data = response.read().decode("utf-8")
                    return json.loads(data)
        except Exception:
            return None
        return None

    @classmethod
    def verify(
        cls,
        license_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        local_fallback_file: Optional[Path] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Valida si la máquina actual o la clave de licencia provista cuentan con autorización activa.
        
        Retorna:
            (is_authorized, message, details)
        """
        hwid = cls.get_machine_hwid()
        key = (license_key or os.getenv("LICENSE_KEY", "")).strip()
        url = (endpoint_url or os.getenv("AUTH_ENDPOINT_URL", DEFAULT_ENDPOINT)).strip()

        # Validación inmediata por clave maestra del propietario
        if key == OWNER_BYPASS_KEY:
            return True, "Acceso concedido mediante credencial maestra del propietario.", {
                "hwid": hwid,
                "role": "owner",
                "mode": "master_key"
            }

        # Consulta al registro en la nube
        registry = cls.fetch_remote_registry(url)

        # Fallback local únicamente si se especifica y el endpoint remoto no responde
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

        # Verificar si el sistema global se encuentra activo
        if not registry.get("system_active", True):
            msg = registry.get("broadcast_message", "El software ha sido desactivado temporalmente por el propietario.")
            return False, msg, {"hwid": hwid, "reason": "system_disabled"}

        # Comprobar listas de bloqueo (banned)
        banned_hwids = [h.strip().upper() for h in registry.get("banned_hwids", [])]
        banned_keys = [k.strip().upper() for k in registry.get("banned_keys", [])]

        if hwid.upper() in banned_hwids:
            return False, "Este equipo ha sido suspendido por el propietario del software.", {
                "hwid": hwid,
                "reason": "hwid_banned"
            }

        if key and key.upper() in banned_keys:
            return False, "La clave de licencia introducida ha sido revocada.", {
                "hwid": hwid,
                "reason": "key_banned"
            }

        # Comprobar licencias estructuradas vinculadas a hardware específico (Node-Locking 1:1)
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
                    
                bound_hwid = (lic_data.get("bound_hwid") or "").strip().upper()
                holder = lic_data.get("holder", "Usuario Autorizado")
                
                # Si la licencia ya está vinculada a otro equipo físico: BLOQUEO INMEDIATO POR CLONACIÓN
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
                    
                return True, f"Licencia de uso exclusivo validada para {holder}.", {
                    "hwid": hwid,
                    "key": key,
                    "holder": holder,
                    "role": "licensed_user_node_locked"
                }

        # Comprobar listas de autorización activa
        authorized_hwids = [h.strip().upper() for h in registry.get("authorized_hwids", [])]
        authorized_keys = [k.strip().upper() for k in registry.get("authorized_keys", [])]

        if hwid.upper() in authorized_hwids:
            return True, "Equipo autorizado directamente en el servidor de licencias.", {
                "hwid": hwid,
                "role": "authorized_hwid"
            }

        if key and key.upper() in authorized_keys:
            return True, "Licencia validada exitosamente con el servidor.", {
                "hwid": hwid,
                "key": key,
                "role": "licensed_user"
            }

        # Acceso denegado
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

            # Probar la clave ingresada
            valid_new, msg_new, _ = cls.verify(license_key=user_input)
            if not valid_new:
                return False, f"La clave introducida no cuenta con autorización activa: {msg_new}"

            # Guardar en archivo .env
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
