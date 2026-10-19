"""
Interfaz de Usuario para el Portal de Acceso Autónomo y Panel de Administración de Licencias.
Permite a los usuarios solicitar acceso con su correo/nombre y al propietario administrar,
aprobar en 1-clic, revocar y restablecer hardware vinculado.
"""

import streamlit as st
from datetime import datetime, timezone
from typing import Dict, Any

from .cloud_auth import CloudAuthManager
from .license_manager import LicenseManager, OWNER_BYPASS_KEY


def render_login_portal() -> None:
    """Muestra el portal de inicio de sesión y solicitud de acceso para clientes."""
    st.title("NGL ENGLISH ASSISTANT")
    st.subheader("Portal de Acceso y Licenciamiento Autónomo")
    st.markdown(
        "Este software es privado y está protegido. Para utilizarlo, inicia sesión con tu cuenta "
        "autorizada o envía una solicitud de acceso al administrador."
    )

    tab_login, tab_register, tab_admin_login = st.tabs([
        "Iniciar Sesion",
        "Solicitar Acceso (Nuevo Usuario)",
        "Acceso de Administrador"
    ])

    hwid = LicenseManager.get_machine_hwid()

    # --- TAB 1: INICIAR SESIÓN ---
    with tab_login:
        st.markdown("##### Iniciar Sesión con Correo Registrado")
        login_email = st.text_input("Correo Electrónico:", key="portal_login_email", placeholder="tu.correo@ejemplo.com")
        
        if st.button("Ingresar al Asistente", type="primary", key="btn_do_login"):
            if not login_email:
                st.warning("Por favor introduce tu correo electrónico.")
            else:
                with st.spinner("Verificando autorización en la nube..."):
                    ok, msg, user_data = CloudAuthManager.authenticate_user(login_email)
                    if ok:
                        st.success(msg)
                        st.session_state.authenticated = True
                        st.session_state.user_email = login_email
                        st.session_state.user_role = "client"
                        st.session_state.user_name = user_data.get("name", "Usuario")
                        st.rerun()
                    else:
                        st.error(msg)

        st.caption(f"Identificador de este equipo (HWID): `{hwid}`")

    # --- TAB 2: SOLICITAR ACCESO ---
    with tab_register:
        st.markdown("##### Enviar Solicitud de Acceso")
        st.info(
            "Al enviar tu solicitud, el administrador la recibirá en su panel de control. "
            "En cuanto sea aprobada, podrás entrar inmediatamente con tu correo."
        )

        with st.form("form_request_access"):
            req_name = st.text_input("Nombre Completo:")
            req_email = st.text_input("Correo Electrónico:")
            req_note = st.text_area("Grupo / Curso / Nota (Opcional):", placeholder="Ej: Estudiante Grupo 4, Inglés Avanzado")
            
            submitted = st.form_submit_button("Enviar Solicitud de Acceso")
            if submitted:
                with st.spinner("Registrando solicitud en la nube..."):
                    ok, msg = CloudAuthManager.request_access(req_name, req_email, req_note)
                    if ok:
                        st.success(f"{msg}")
                        st.balloons()
                    else:
                        st.error(msg)

        st.caption(f"Tu equipo físico será registrado automáticamente: `{hwid}`")

    # --- TAB 3: ACCESO DE ADMINISTRADOR ---
    with tab_admin_login:
        st.markdown("##### Acceso de Administrador")
        admin_key = st.text_input("Clave Maestra de Administrador:", type="password", key="portal_admin_key")
        
        if st.button("Validar Credencial de Administrador", key="btn_admin_login"):
            if LicenseManager.is_owner_key(admin_key):
                st.session_state.authenticated = True
                st.session_state.user_role = "owner"
                st.session_state.user_name = "Administrador"
                st.session_state.admin_panel_open = True
                st.success("Acceso concedido al panel maestro.")
                st.rerun()
            else:
                st.error("Clave de administrador incorrecta.")


def render_admin_dashboard() -> None:
    """Muestra el panel de control y administración de licencias 1-clic para el autor."""
    st.markdown("---")
    st.header("Panel de Administración de Usuarios y Licencias")
    st.caption("Gestiona solicitudes, concede permisos en 1 clic y administra equipos vinculados.")

    users = CloudAuthManager.admin_list_users()

    # Métricas generales
    total_users = len(users)
    pending_users = [u for u in users if u.get("status") == "pending"]
    approved_users = [u for u in users if u.get("status") == "approved"]
    revoked_users = [u for u in users if u.get("status") in ("revoked", "banned")]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Registrados", total_users)
    col2.metric("Pendientes", len(pending_users), delta=f"{len(pending_users)} por revisar", delta_color="inverse" if pending_users else "normal")
    col3.metric("Aprobados / Activos", len(approved_users))
    col4.metric("Revocados", len(revoked_users))

    st.markdown("---")

    # SECCIÓN 1: SOLICITUDES PENDIENTES (1-CLIC)
    st.subheader(f"Solicitudes Pendientes de Aprobación ({len(pending_users)})")
    if not pending_users:
        st.info("No hay solicitudes pendientes en este momento. Todas las peticiones están al día.")
    else:
        for idx, u in enumerate(pending_users):
            email = u.get("email", "")
            name = u.get("name", "Sin nombre")
            hwid = u.get("hwid", "No especificado")
            note = u.get("note", "Sin nota")
            created_at = u.get("created_at", "")[:19].replace("T", " ")

            with st.container():
                st.markdown(f"**{name}** (`{email}`)")
                st.caption(f"HWID: `{hwid}` | Solicitado: {created_at} | Nota: {note}")
                
                c_btn1, c_btn2, _ = st.columns([1, 1, 3])
                if c_btn1.button("Aprobar Acceso (1-Clic)", key=f"btn_appr_{email}_{idx}", type="primary"):
                    ok, msg = CloudAuthManager.admin_approve_user(email)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

                if c_btn2.button("Rechazar / Denegar", key=f"btn_rej_{email}_{idx}"):
                    ok, msg = CloudAuthManager.admin_revoke_user(email)
                    if ok:
                        st.warning(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                st.divider()

    # SECCIÓN 2: USUARIOS APROBADOS Y ACTIVOS
    st.subheader(f"Usuarios Autorizados ({len(approved_users)})")
    if approved_users:
        for idx, u in enumerate(approved_users):
            email = u.get("email", "")
            name = u.get("name", "")
            hwid = u.get("hwid") or "Pendiente de primer inicio"
            approved_at = (u.get("approved_at") or "")[:19].replace("T", " ")
            last_login = (u.get("last_login") or "Nunca")[:19].replace("T", " ")

            with st.expander(f"{name} ({email}) - {u.get('status', 'approved').upper()}"):
                st.write(f"**Hardware Vinculado:** `{hwid}`")
                st.write(f"**Aprobado el:** {approved_at} | **Ultimo acceso:** {last_login}")
                
                curr_status = u.get("status", "approved")
                status_choices = ["approved", "pending", "revoked"]
                status_names = {"approved": "Aprobado (Activo)", "pending": "Pendiente", "revoked": "Revocado (Suspendido)"}
                
                c_sel, _ = st.columns([2, 3])
                with c_sel:
                    new_sel = st.selectbox(
                        "Seleccionar Estado:",
                        options=[status_names[s] for s in status_choices],
                        index=status_choices.index(curr_status) if curr_status in status_choices else 0,
                        key=f"sel_status_{email}_{idx}"
                    )
                    chosen_status = [k for k, v in status_names.items() if v == new_sel][0]
                    if chosen_status != curr_status:
                        ok, msg = CloudAuthManager.admin_set_status(email, chosen_status)
                        if ok:
                            st.success(msg)
                            st.rerun()

                st.markdown("---")
                col_a, col_b, col_c = st.columns([1.5, 2, 1.5])
                if col_a.button("Revocar Acceso", key=f"btn_rev_{email}_{idx}", type="secondary"):
                    ok, msg = CloudAuthManager.admin_revoke_user(email)
                    if ok:
                        st.warning(msg)
                        st.rerun()

                if col_b.button("Resetear HWID (Cambio de PC)", key=f"btn_res_{email}_{idx}"):
                    ok, msg = CloudAuthManager.admin_reset_hwid(email)
                    if ok:
                        st.info(msg)
                        st.rerun()

                if col_c.button("Eliminar Usuario", key=f"btn_del_{email}_{idx}"):
                    ok, msg = CloudAuthManager.admin_delete_user(email)
                    if ok:
                        st.success(msg)
                        st.rerun()

    # SECCIÓN 3: USUARIOS REVOCADOS / SUSPENDIDOS
    if revoked_users:
        with st.expander(f"Ver Usuarios Revocados / Suspendidos ({len(revoked_users)})"):
            for idx, u in enumerate(revoked_users):
                email = u.get("email", "")
                name = u.get("name", "")
                st.write(f"- **{name}** (`{email}`)")
                col_r1, col_r2 = st.columns([1, 1])
                if col_r1.button("Reactivar Acceso", key=f"btn_reappr_{email}_{idx}"):
                    ok, msg = CloudAuthManager.admin_approve_user(email)
                    if ok:
                        st.success(msg)
                        st.rerun()
                if col_r2.button("Eliminar", key=f"btn_del_rev_{email}_{idx}"):
                    ok, msg = CloudAuthManager.admin_delete_user(email)
                    if ok:
                        st.rerun()
