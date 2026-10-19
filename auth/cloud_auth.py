"""
Módulo de Autenticación en la Nube y Gestión Autónoma de Usuarios (Cloud Login & Admin).
Permite a los usuarios solicitar acceso con su correo/nombre y al propietario administrar,
aprobar, revocar y vincular hardware en 1 solo clic desde el panel de control.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, Dict, Any, List, Optional

from .license_manager import LicenseManager

DEFAULT_USERS_FILE = Path(__file__).resolve().parent / "cloud_users.json"
SESSION_CACHE_FILE = Path.home() / ".ngl_assistant_session.json"


class CloudAuthManager:
    """Gestiona el ciclo de vida de usuarios, solicitudes de acceso y aprobaciones 1-clic."""

    @classmethod
    def get_users_store_path(cls) -> Path:
        """Ruta al almacén local/compartido de usuarios."""
        return DEFAULT_USERS_FILE

    @classmethod
    def load_registry(cls, endpoint_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Carga el registro de usuarios desde la nube (si está configurado)
        o desde el archivo persistente local.
        """
        url = endpoint_url or os.getenv("AUTH_CLOUD_ENDPOINT", "")
        if url and url.startswith("http"):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "NGL-CloudAuth/2.0", "Cache-Control": "no-cache"}
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    if resp.status == 200:
                        return json.loads(resp.read().decode("utf-8"))
            except Exception:
                pass

        # Fallback a archivo de registro local
        store_path = cls.get_users_store_path()
        if store_path.exists():
            try:
                with open(store_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        return {"users": {}, "meta": {"updated_at": datetime.now(timezone.utc).isoformat()}}

    @classmethod
    def save_registry(cls, data: Dict[str, Any], endpoint_url: Optional[str] = None) -> bool:
        """
        Guarda el registro de usuarios tanto en la nube (POST/PUT) como localmente.
        """
        data["meta"] = {"updated_at": datetime.now(timezone.utc).isoformat()}
        success_local = False

        # Guardado local
        store_path = cls.get_users_store_path()
        try:
            store_path.parent.mkdir(parents=True, exist_ok=True)
            with open(store_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            success_local = True
        except Exception:
            pass

        # Guardado remoto si existe endpoint con soporte de escritura
        url = endpoint_url or os.getenv("AUTH_CLOUD_ENDPOINT", "")
        if url and url.startswith("http"):
            try:
                payload_bytes = json.dumps(data).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=payload_bytes,
                    headers={"Content-Type": "application/json", "User-Agent": "NGL-CloudAuth/2.0"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    if resp.status in (200, 201, 204):
                        return True
            except Exception:
                pass

        return success_local

    @classmethod
    def request_access(cls, name: str, email: str, note: str = "") -> Tuple[bool, str]:
        """
        Registra una nueva solicitud de acceso para un cliente con su HWID capturado.
        """
        clean_email = email.strip().lower()
        clean_name = name.strip()

        if not clean_email or "@" not in clean_email:
            return False, "Por favor introduce un correo electrónico válido."
        if not clean_name:
            return False, "Por favor introduce tu nombre completo."

        hwid = LicenseManager.get_machine_hwid()
        data = cls.load_registry()
        users = data.setdefault("users", {})

        if clean_email in users:
            existing = users[clean_email]
            status = existing.get("status", "pending")
            if status == "approved":
                return False, "Este correo ya está aprobado. Ve a la pestaña 'Iniciar Sesión' para acceder."
            elif status == "pending":
                # Actualizar HWID y fecha por si intenta desde otro equipo
                existing["hwid"] = hwid
                existing["note"] = note
                existing["updated_at"] = datetime.now(timezone.utc).isoformat()
                cls.save_registry(data)
                return True, "Tu solicitud ya estaba registrada y se ha actualizado. Sigue en estado PENDIENTE de aprobación."
            elif status in ("revoked", "banned"):
                return False, "Esta cuenta ha sido suspendida por el administrador. Contacta al propietario."

        # Crear nuevo registro pendiente
        users[clean_email] = {
            "name": clean_name,
            "email": clean_email,
            "hwid": hwid,
            "note": note,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "approved_at": None,
            "last_login": None,
            "platform": f"{sys.platform} ({os.name})"
        }

        saved = cls.save_registry(data)
        if saved:
            return True, "Solicitud enviada correctamente. El administrador revisará tu petición para concederte acceso."
        return False, "No se pudo registrar la solicitud por un problema de guardado local/remoto."

    @classmethod
    def authenticate_user(cls, email: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Autentica un usuario por correo verificando que su estado sea 'approved'
        y que su hardware coincida estrictamente con el equipo vinculado.
        """
        clean_email = email.strip().lower()
        if not clean_email:
            return False, "Introduce tu correo electrónico.", {}

        hwid = LicenseManager.get_machine_hwid()
        data = cls.load_registry()
        users = data.get("users", {})

        if clean_email not in users:
            return False, "No existe ninguna cuenta registrada con este correo. Ve a 'Solicitar Acceso'.", {}

        user = users[clean_email]
        status = user.get("status", "pending")

        if status == "pending":
            return False, (
                "Tu cuenta se encuentra PENDIENTE de aprobación. "
                "El administrador (Taborda004) aún no ha autorizado tu acceso."
            ), user

        if status in ("revoked", "banned"):
            return False, "Tu cuenta ha sido revocada o suspendida por el administrador.", user

        if status == "approved":
            bound_hwid = (user.get("hwid") or "").strip().upper()
            
            # Si aún no tiene HWID fijado, se vincula automáticamente a este equipo en su primer login
            if not bound_hwid:
                user["hwid"] = hwid
                bound_hwid = hwid
                user["last_login"] = datetime.now(timezone.utc).isoformat()
                cls.save_registry(data)
                cls._save_cached_session(clean_email, user.get("name", ""))
                return True, f"Bienvenido {user.get('name')}. Tu equipo ha sido vinculado exitosamente.", user

            # Si ya tiene HWID fijado, validar que sea la misma máquina
            if bound_hwid != hwid.upper():
                return False, (
                    f"Violación de seguridad y clonación detectada: Esta cuenta está vinculada a otro equipo físico ({bound_hwid}). "
                    f"No está permitido compartir credenciales ni clonar cuentas en otras máquinas. "
                    f"Tu equipo actual es: {hwid}."
                ), user

            # Actualizar último acceso y guardar sesión
            user["last_login"] = datetime.now(timezone.utc).isoformat()
            cls.save_registry(data)
            cls._save_cached_session(clean_email, user.get("name", ""))
            return True, f"Inicio de sesión exitoso. Bienvenido de nuevo, {user.get('name')}.", user

        return False, f"Estado de cuenta no reconocido ('{status}').", user

    @classmethod
    def get_cached_session(cls) -> Optional[Dict[str, str]]:
        """Recupera la sesión activa guardada localmente."""
        if SESSION_CACHE_FILE.exists():
            try:
                with open(SESSION_CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    @classmethod
    def _save_cached_session(cls, email: str, name: str) -> None:
        """Persiste la sesión autenticada en el perfil del usuario."""
        try:
            with open(SESSION_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "email": email,
                    "name": name,
                    "hwid": LicenseManager.get_machine_hwid(),
                    "logged_in_at": datetime.now(timezone.utc).isoformat()
                }, f, indent=2)
        except Exception:
            pass

    @classmethod
    def clear_session(cls) -> None:
        """Cierra la sesión activa borrando la caché local."""
        try:
            if SESSION_CACHE_FILE.exists():
                SESSION_CACHE_FILE.unlink()
        except Exception:
            pass

    # =========================================================================
    # ACCIONES DEL PANEL DE ADMINISTRACIÓN (1-CLIC)
    # =========================================================================

    @classmethod
    def admin_list_users(cls) -> List[Dict[str, Any]]:
        """Retorna la lista completa de usuarios ordenada por fecha."""
        data = cls.load_registry()
        users = list(data.get("users", {}).values())
        users.sort(key=lambda u: u.get("created_at", ""), reverse=True)
        return users

    @classmethod
    def admin_approve_user(cls, email: str) -> Tuple[bool, str]:
        """Aprueba una solicitud de acceso y fija su estado como activo."""
        clean_email = email.strip().lower()
        data = cls.load_registry()
        users = data.get("users", {})

        if clean_email not in users:
            return False, "Usuario no encontrado."

        user = users[clean_email]
        user["status"] = "approved"
        user["approved_at"] = datetime.now(timezone.utc).isoformat()
        saved = cls.save_registry(data)
        if saved:
            return True, f"Usuario '{user.get('name')}' ({clean_email}) aprobado exitosamente."
        return False, "Error al guardar los cambios en el registro."

    @classmethod
    def admin_revoke_user(cls, email: str) -> Tuple[bool, str]:
        """Revoca o suspende el acceso a un usuario de inmediato."""
        clean_email = email.strip().lower()
        data = cls.load_registry()
        users = data.get("users", {})

        if clean_email not in users:
            return False, "Usuario no encontrado."

        user = users[clean_email]
        user["status"] = "revoked"
        user["revoked_at"] = datetime.now(timezone.utc).isoformat()
        saved = cls.save_registry(data)
        if saved:
            return True, f"Acceso revocado para '{user.get('name')}' ({clean_email})."
        return False, "Error al guardar los cambios."

    @classmethod
    def admin_reset_hwid(cls, email: str) -> Tuple[bool, str]:
        """
        Resetea la vinculación de hardware para permitir al usuario
        activar su cuenta en una computadora nueva legítimamente.
        """
        clean_email = email.strip().lower()
        data = cls.load_registry()
        users = data.get("users", {})

        if clean_email not in users:
            return False, "Usuario no encontrado."

        user = users[clean_email]
        user["hwid"] = ""
        user["reset_at"] = datetime.now(timezone.utc).isoformat()
        saved = cls.save_registry(data)
        if saved:
            return True, f"HWID restablecido para '{user.get('name')}'. Podrá vincular su nuevo equipo al iniciar sesión."
        return False, "Error al guardar los cambios."

    @classmethod
    def admin_delete_user(cls, email: str) -> Tuple[bool, str]:
        """Elimina permanentemente el registro de un usuario."""
        clean_email = email.strip().lower()
        data = cls.load_registry()
        users = data.get("users", {})

        if clean_email in users:
            del users[clean_email]
            cls.save_registry(data)
            return True, f"Usuario '{clean_email}' eliminado correctamente."
        return False, "Usuario no encontrado."
