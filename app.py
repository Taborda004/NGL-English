import streamlit as st
import sys
import os
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from browser.browser_manager import BrowserManager
from browser.page_detector import PageDetector
from analyzer.content_extractor import ContentExtractor
from analyzer.exercise_detector import ExerciseDetector, ExerciseType
from ai.solver import AISolver
from interaction.form_filler import FormFiller
from history.history_manager import HistoryManager
from automation.chain_runner import ChainRunner
from config.settings import settings

st.set_page_config(page_title="NGL English Assistant", layout="wide")

# Prevent Google Chrome Auto-Translate from breaking React DOM reconciliation
st.html("""
<meta name="google" content="notranslate">
<style>
    body, html, [data-testid="stAppViewContainer"], .stApp {
        translate: no !important;
    }
</style>
<script>
    document.documentElement.setAttribute('translate', 'no');
    document.documentElement.classList.add('notranslate');
    if (document.body) {
        document.body.setAttribute('translate', 'no');
        document.body.classList.add('notranslate');
    }
</script>
""")

st.title("NGL ENGLISH ASSISTANT")

# Helper function to run playwright safely in Streamlit
def run_with_browser(func):
    manager = BrowserManager(port=settings.CHROME_DEBUGGING_PORT)
    if manager.connect():
        try:
            page = manager.get_current_page()
            return func(page)
        finally:
            manager.close()
    else:
        st.error("Failed to connect. Make sure Chrome is running with --remote-debugging-port=9222")
        return None

# Top level info
def get_info(page):
    detector = PageDetector(page)
    return detector.get_assignment_info()

info = run_with_browser(get_info)

if info:
    st.sidebar.success("● Navegador conectado")
    st.sidebar.markdown(f"**Asignación:**\n{info.get('title', 'NGL')}")
    if not settings.GEMINI_API_KEY:
        st.sidebar.error("⚠️ GEMINI_API_KEY no configurada en .env")
        st.warning("⚠️ **Clave de API de Gemini no detectada.** Recuerda configurar tu `GEMINI_API_KEY` en el archivo `.env` para que la IA pueda resolver los ejercicios.")
    st.sidebar.markdown("---")

    # Initialize session state for execution
    if 'auto_history' not in st.session_state:
        st.session_state.auto_history = []
    if 'auto_status' not in st.session_state:
        st.session_state.auto_status = "idle"  # idle, running, stopped, paused_error, completed
    if 'auto_error_reason' not in st.session_state:
        st.session_state.auto_error_reason = None
    if 'last_run_mode' not in st.session_state:
        st.session_state.last_run_mode = "single_step"
    if 'safe_history' not in st.session_state:
        st.session_state.safe_history = []
    if 'safe_status' not in st.session_state:
        st.session_state.safe_status = "idle"
    if 'safe_stop_requested' not in st.session_state:
        st.session_state.safe_stop_requested = False

    # Mode Selector
    st.sidebar.subheader("Modo de Operación")
    selected_mode = st.sidebar.radio(
        "Elige cómo deseas trabajar:",
        [
            "🛡️ Asistido Seguro (Responder sin Enviar + Revisar)",
            "🎯 Paso a Paso Autónomo (1 Ejercicio, Envía y Avanza)",
            "🤖 Modo Autónomo en Cadena",
            "✍️ Modo Manual (Inspección)"
        ],
        index=0,
        help=(
            "• Asistido Seguro: Responde y avanza pregunta por pregunta SIN enviar nada. Al final revisas todo y confirmas el envío.\n"
            "• Paso a Paso: Resuelve y envía ('Done') 1 ejercicio a la vez al 100%.\n"
            "• En Cadena: Resuelve y envía múltiples ejercicios seguidos en bucle continuo.\n"
            "• Modo Manual: Inspecciona y edita respuestas antes de ingresarlas."
        )
    )

    st.header("Asignación Actual")
    st.write(f"**Título:** {info.get('title')}")

    def run_autonomous_execution(max_ex: int, is_single_step: bool, min_conf: int, delay_sec: float, auto_retry_choice: bool, allow_exams_choice: bool = True):
        st.session_state.auto_stop_requested = False
        st.session_state.auto_status = "running"
        st.session_state.auto_error_reason = None
        st.session_state.auto_history = []
        st.session_state.last_run_mode = "single_step" if is_single_step else "chain"

        status_box = st.container(border=True)
        status_header = status_box.empty()
        if is_single_step:
            status_header.markdown("### 🔄 Resolviendo ejercicio en pantalla...")
        else:
            status_header.markdown("### 🔄 Ejecutando cadena autónoma...")
        log_display = status_box.empty()
        log_messages = []

        def update_log(payload: dict):
            event = payload.get("event")
            msg = payload.get("message", "")
            
            line = ""
            if event == "info":
                line = f"ℹ️ {msg}"
            elif event == "step_start":
                line = f"📝 **[{payload.get('exercise_title')}]** - Analizando..."
            elif event == "analysis_ready":
                line = f"🔍 Tipo: `{payload.get('type')}`"
            elif event == "solution_ready":
                line = f"💡 Solución lista ({int(payload.get('confidence', 0)*100)}% conf): `{payload.get('answer')}`"
            elif event == "filled":
                line = f"✍️ {msg}"
            elif event == "step_success":
                line = f"✅ {msg}"
            elif event == "error":
                line = f"❌ **ERROR:** {payload.get('reason')}"
            elif event == "completed":
                line = f"🏁 {msg}"
            
            if line:
                log_messages.append(line)
                log_display.markdown("\n\n".join(log_messages[-25:]))

        runner = ChainRunner(
            port=settings.CHROME_DEBUGGING_PORT,
            min_confidence=min_conf / 100.0,
            delay_between_exercises=delay_sec,
            max_exercises=max_ex,
            auto_retry=auto_retry_choice,
            allow_exams=allow_exams_choice
        )

        result = runner.run_chain(
            callback_log=update_log,
            is_stopped=lambda: st.session_state.get('auto_stop_requested', False)
        )

        st.session_state.auto_status = result.get("status")
        st.session_state.auto_error_reason = result.get("reason")
        st.session_state.auto_history = result.get("history", [])

        if result.get("status") == "completed":
            if is_single_step:
                status_header.markdown("### 🎉 ¡Ejercicio resuelto al 100% y avanzado al siguiente!")
            else:
                status_header.markdown("### 🎉 ¡Asignación finalizada con éxito al 100%!")
        elif result.get("status") == "paused_error":
            status_header.markdown("### ⛔ Automatización pausada por error o protección de examen.")
        elif result.get("status") == "stopped":
            status_header.markdown("### ⏹ Automatización detenida por el usuario.")

    def render_execution_feedback():
        if st.session_state.auto_status == "paused_error" and st.session_state.auto_error_reason:
            st.error(
                f"### ⛔ ALERTA: Automatización Pausada\n\n"
                f"**Causa:** {st.session_state.auto_error_reason}\n\n"
                f"> **Acción requerida:** Revisa la ventana de Chrome. No se enviaron más intentos para evitar errores en tu calificación."
            )
        elif st.session_state.auto_status == "completed":
            if st.session_state.get("last_run_mode") == "single_step":
                st.success(
                    "### 🎉 Ejercicio Resuelto al 100% y Avanzado con Éxito\n\n"
                    "El ejercicio actual fue completado con 100% de precisión y se avanzó a la siguiente actividad en Chrome. "
                    "Revisa la ventana del navegador y presiona nuevamente cuando desees resolver el siguiente."
                )
            else:
                st.success(
                    f"### 🎉 Cadena Finalizada Exitosamente\n\n"
                    f"Se completaron **{len(st.session_state.auto_history)}** ejercicios correctamente sin errores."
                )
        elif st.session_state.auto_status == "stopped":
            st.warning("La automatización fue detenida por el usuario.")

        if st.session_state.auto_history:
            st.markdown("### 📊 Historial de Ejercicios Resueltos")
            st.dataframe(
                st.session_state.auto_history,
                column_config={
                    "index": "#",
                    "exercise_title": "Ejercicio",
                    "type": "Tipo",
                    "answer": "Respuesta enviada",
                    "confidence": st.column_config.ProgressColumn(
                        "Confianza IA", format="%.0f%%", min_value=0, max_value=1
                    ),
                    "result": "Verificación"
                },
                use_container_width=True,
                hide_index=True,
                key="auto_history_table"
            )

    def run_safe_assisted_execution(max_steps: int, is_single_step: bool, min_conf: int, delay_sec: float):
        st.session_state.safe_stop_requested = False
        st.session_state.safe_status = "running"
        
        status_box = st.container(border=True)
        status_header = status_box.empty()
        if is_single_step:
            status_header.markdown("### 🔄 Respondiendo pregunta actual...")
        else:
            status_header.markdown("### 🔄 Respondiendo preguntas en bucle asistido...")
            
        log_display = status_box.empty()
        log_messages = []
        
        def log(msg):
            log_messages.append(msg)
            log_display.markdown("\n\n".join(log_messages[-25:]))
            
        manager = BrowserManager(port=settings.CHROME_DEBUGGING_PORT)
        if not manager.connect():
            st.error("No se pudo conectar a Chrome.")
            return

        solved_count = 0
        try:
            page = manager.get_current_page()
            if not page:
                st.error("No se encontró la página activa en Chrome.")
                return

            while solved_count < max_steps:
                if st.session_state.get('safe_stop_requested', False):
                    log("⏹ Proceso detenido por el usuario.")
                    break

                # 1. Title & screen info
                exercise_title = "Pregunta / Pantalla"
                for f in page.frames:
                    if "cdn_proxy" in f.url or "avallain" in f.url:
                        try:
                                let active = $('.content-wrap:visible, .activity:visible').first();
                                if (active.length === 0) {
                                    active = $('.content-wrap, .activity').filter(function() { return $(this).css('display') !== 'none'; }).first();
                                }
                                const title = $('.learningObject__title, h1, h2, .lo-title').first().text().trim() || document.title;
                                const rubric = active.find('.layout__rubric, .rubric, .learningObject__rubric').first().text().trim();
                                const wraps = $('.content-wrap');
                                let screenNum = '';
                                if (wraps.length > 1 && active.length > 0) {
                                    const idx = wraps.index(active);
                                    if (idx !== -1) screenNum = `Pantalla ${idx + 1} de ${wraps.length}`;
                                }
                                // Also check body for "Screen X of Y" (Unit Test counter)
                                const bodyText = document.body ? document.body.innerText : '';
                                const screenMatch = bodyText.match(/Screen[:\\s]*(\\d+)\\s*of\\s*(\\d+)/i);
                                if (screenMatch && !screenNum) screenNum = screenMatch[0];
                                return { title: title, rubric: rubric, screenNum: screenNum };
                            }""")
                            if info:
                                parts = []
                                if info.get('screenNum'): parts.append(info['screenNum'])
                                if info.get('rubric'): parts.append(info['rubric'])
                                elif info.get('title'): parts.append(info['title'])
                                exercise_title = " — ".join(parts)
                                break
                        except Exception:
                            pass

                log(f"📝 **Analizando:** {exercise_title}")

                # 2. Extract & Detect
                ext = ContentExtractor(page)
                det = ExerciseDetector(page)
                filler = FormFiller(page)

                txt = ext.extract_context()
                img = ext.extract_screenshot_b64()
                aud = ext.extract_audios_b64(page.context)
                ex_type = det.detect_type()

                # Check if this is a final score/summary screen
                if ex_type == ExerciseType.UNKNOWN:
                    is_score_screen = False
                    for f in page.frames:
                        if "cdn_proxy" in f.url or "avallain" in f.url:
                            try:
                                    let active = $('.content-wrap:visible, .activity:visible').first();
                                    if (active.length === 0) {
                                        active = $('.content-wrap, .activity').filter(function() { return $(this).css('display') !== 'none'; }).first();
                                    }
                                    return active.text().includes('Your score') || $('.score, .summary').filter(':visible').length > 0;
                                }""")
                                if is_score_screen:
                                    break
                            except:
                                pass
                    if is_score_screen:
                        log("🏁 **Pantalla final de resumen alcanzada.** ¡Todas las preguntas del examen fueron completadas!")
                        break

                log(f"🔍 Tipo detectado: `{ex_type.value}`. Consultando IA...")

                # 3. Solve with AI
                solver = AISolver()
                sol = solver.solve(ex_type.value, txt, img, aud)

                if "error" in sol:
                    log(f"❌ Error en la IA: {sol['error']}")
                    break

                answer = sol.get("answer", "")
                conf = float(sol.get("confidence", 1.0))
                expl = sol.get("explanation", "")

                if ex_type == ExerciseType.SPEAKING:
                    log(f"🗣️ **Respuesta sugerida para pronunciar ({int(conf*100)}% conf):** `{answer}`")
                else:
                    log(f"💡 Respuesta generada ({int(conf*100)}% conf): `{answer}`")

                # 4. Fill answer in Chrome
                fill_ok, fill_msg = filler.fill_answer(answer, ex_type.value)
                if not fill_ok:
                    log(f"⚠️ Nota de llenado: {fill_msg}")
                else:
                    log(f"✍️ {fill_msg}")

                time.sleep(0.8)

                # Record in session state for review
                record = {
                    "index": len(st.session_state.safe_history) + 1,
                    "screen_title": exercise_title,
                    "type": ex_type.value,
                    "answer": answer,
                    "confidence": conf,
                    "explanation": expl
                }
                st.session_state.safe_history.append(record)
                solved_count += 1

                time.sleep(delay_sec)

                # 6. Advance to next screen
                next_ok, next_msg = filler.click_next_screen()
                
                if is_single_step:
                    if next_ok:
                        log("➡️ Se avanzó a la siguiente pregunta/pantalla exitosamente.")
                    else:
                        log(f"ℹ️ {next_msg}")
                    break
                else:
                    if not next_ok:
                        log(f"🏁 {next_msg}")
                        log("🎉 ¡Llegaste a la última pantalla del examen/actividad!")
                        break
                    else:
                        log("➡️ Avanzando a la siguiente pregunta en Chrome...")

            if is_single_step:
                status_header.markdown("### ✅ Pregunta respondida y avanzada")
            else:
                status_header.markdown("### 📋 Proceso asistido completado")

        finally:
            manager.close()

    # ==========================================

    # MODO 1: ASISTIDO SEGURO (RESPONDER SIN ENVIAR + REVISAR)
    # ==========================================
    if selected_mode == "🛡️ Asistido Seguro (Responder sin Enviar + Revisar)":
        st.subheader("🛡️ Asistido Seguro: Responder sin Enviar + Revisión Final")
        st.info(
            "💡 **Modo Asistido Seguro Activo:** Este modo resuelve y rellena automáticamente cada pregunta o pantalla en Chrome, "
            "y avanza a la siguiente **SIN ENVIAR NADA**. No quema ningún intento. Todas las respuestas se registran abajo "
            "para que al finalizar puedas verificar todo al 100% antes de confirmar el envío definitivo."
        )

        with st.expander("⚙️ Opciones de Configuración Asistida", expanded=False):
            col_cfg1, col_cfg2 = st.columns(2)
            with col_cfg1:
                safe_conf = st.slider("Confianza mínima de IA (%)", min_value=50, max_value=99, value=80, step=5, key="safe_conf")
            with col_cfg2:
                safe_delay = st.slider("Pausa antes de avanzar (seg)", min_value=1.0, max_value=5.0, value=1.5, step=0.5, key="safe_delay")

        col_safe1, col_safe2, col_safe_stop = st.columns([2, 2, 1])
        single_safe_clicked = col_safe1.button("▶ Responder Esta Pregunta y Avanzar", type="primary", help="Responde la pregunta actual en Chrome y avanza a la siguiente pantalla sin enviar nada.")
        all_safe_clicked = col_safe2.button("⏩ Responder Todo hasta el Final", help="Responde y avanza automáticamente todas las preguntas hasta la pantalla final sin enviar nada.")
        stop_safe_clicked = col_safe_stop.button("⏹ Detener")

        if stop_safe_clicked:
            st.session_state.safe_stop_requested = True
            st.warning("Se solicitó detener el proceso asistido.")

        if single_safe_clicked:
            run_safe_assisted_execution(max_steps=1, is_single_step=True, min_conf=safe_conf, delay_sec=safe_delay)
        elif all_safe_clicked:
            run_safe_assisted_execution(max_steps=50, is_single_step=False, min_conf=safe_conf, delay_sec=safe_delay)

        # Panel de Revisión
        st.markdown("---")
        st.subheader("📋 Panel de Revisión de Respuestas")
        st.write("Verifica aquí todas las preguntas y respuestas colocadas por el asistente antes de enviar:")

        if st.session_state.safe_history:
            st.dataframe(
                st.session_state.safe_history,
                column_config={
                    "index": "#",
                    "screen_title": "Pantalla / Ejercicio",
                    "type": "Tipo",
                    "answer": "Respuesta colocada",
                    "confidence": st.column_config.ProgressColumn(
                        "Confianza IA", format="%.0f%%", min_value=0, max_value=1
                    ),
                    "explanation": "Explicación"
                },
                use_container_width=True,
                hide_index=True,
                key="safe_history_table"
            )

            col_nav1, col_nav2, col_clear = st.columns([1, 1, 1])
            with col_nav1:
                if st.button("⬅️ Ver Pantalla Anterior en Chrome"):
                    def prev_fn(page):
                        return FormFiller(page).click_previous_screen()
                    ok, msg = run_with_browser(prev_fn)
                    if ok: st.info(msg)
            with col_nav2:
                if st.button("➡️ Ver Pantalla Siguiente en Chrome"):
                    def next_fn(page):
                        return FormFiller(page).click_next_screen()
                    ok, msg = run_with_browser(next_fn)
                    if ok: st.info(msg)
            with col_clear:
                if st.button("🗑️ Limpiar Historial de Revisión"):
                    st.session_state.safe_history = []
                    st.rerun()

            # Envío Definitivo Protegido
            with st.container(border=True):
                st.markdown("### 📤 Envío Definitivo de Calificación")
                st.write("Solo cuando hayas verificado todas las respuestas y estés 100% satisfecho, envía la calificación:")
                confirm_done = st.checkbox("☑️ He revisado todas las respuestas y confirmo que deseo enviar la calificación a la plataforma.")
                if st.button("🚀 Enviar Todo Definitivamente (Done / Submit to Gradebook)", type="primary", disabled=not confirm_done):
                    def submit_final_fn(page):
                        return FormFiller(page).submit_done()
                    ok, msg = run_with_browser(submit_final_fn)
                    if ok:
                        st.success("🎉 ¡Asignación / Examen enviado exitosamente a la plataforma!")
                    else:
                        st.error(f"No se pudo enviar: {msg}")
        else:
            st.info("Aún no has respondido preguntas en esta sesión. Presiona **'▶ Responder Esta Pregunta y Avanzar'** para comenzar.")

    # ==========================================
    # MODO 2: PASO A PASO AUTÓNOMO (1 EJERCICIO, ENVÍA Y AVANZA)
    # ==========================================
    elif selected_mode == "🎯 Paso a Paso Autónomo (1 Ejercicio, Envía y Avanza)":
        st.subheader("🎯 Paso a Paso Autónomo: 1 Ejercicio y Avanzar")
        st.write(
            "Este modo resuelve con IA **únicamente el ejercicio actual en pantalla**, envía la respuesta ('Done'), "
            "verifica que obtenga el 100%, **avanza al siguiente ejercicio** en Chrome y se detiene automáticamente. "
            "Ideal para lecciones regulares donde deseas enviar y calificar cada ejercicio de inmediato."
        )

        with st.expander("⚙️ Opciones de Configuración", expanded=False):
            col_cfg1, col_cfg2 = st.columns(2)
            with col_cfg1:
                min_conf = st.slider("Confianza mínima de IA (%)", min_value=50, max_value=99, value=80, step=5, key="step_conf")
            with col_cfg2:
                delay_sec = st.slider("Pausa antes de avanzar (seg)", min_value=1.0, max_value=5.0, value=2.0, step=0.5, key="step_delay")

            allow_exams_step = st.checkbox(
                "🔓 Permitir resolver exámenes y Unit Tests automáticamente",
                value=True,
                key="step_allow_exams",
                help="Permite resolver exámenes y Unit Tests multi-pantalla de forma autónoma hasta enviarlos."
            )

            auto_retry_choice = st.checkbox(
                "Reintentar automáticamente antes de pausar (Intento 2)",
                value=False,
                key="step_retry",
                help="Desactivado por defecto para proteger tus intentos. Al estar desactivado, el sistema se detendrá inmediatamente si alguna respuesta no es 100% correcta."
            )

        col_run, col_stop = st.columns([2, 1])
        step_clicked = col_run.button("▶ Resolver Ejercicio Actual y Avanzar", type="primary")
        stop_clicked = col_stop.button("⏹ Detener")

        if stop_clicked:
            st.session_state.auto_stop_requested = True
            st.session_state.auto_status = "stopped"
            st.warning("Se solicitó detener la automatización.")

        if step_clicked:
            run_autonomous_execution(
                max_ex=1,
                is_single_step=True,
                min_conf=min_conf,
                delay_sec=delay_sec,
                auto_retry_choice=auto_retry_choice,
                allow_exams_choice=allow_exams_step
            )

        render_execution_feedback()

    # ==========================================
    # MODO 2: MODO 100% AUTÓNOMO EN CADENA
    # ==========================================
    elif selected_mode == "🤖 Modo Autónomo en Cadena":
        st.subheader("🤖 Modo 100% Autónomo en Cadena")
        st.write(
            "El sistema resolverá, completará y enviará cada ejercicio secuencialmente en cadena continua. "
            "**Se detendrá de inmediato** si ocurre un error, si la confianza de la IA es baja, o si la respuesta enviada no obtiene el 100%."
        )

        with st.expander("⚙️ Opciones de Configuración Autónoma", expanded=False):
            col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
            with col_cfg1:
                min_conf = st.slider("Confianza mínima de IA (%)", min_value=50, max_value=99, value=80, step=5, key="chain_conf")
            with col_cfg2:
                delay_sec = st.slider("Pausa entre ejercicios (seg)", min_value=1.0, max_value=5.0, value=2.0, step=0.5, key="chain_delay")
            with col_cfg3:
                max_ex = st.number_input("Máximo de ejercicios en cadena", min_value=1, max_value=100, value=30, step=1, key="chain_max")

            allow_exams_chain = st.checkbox(
                "🔓 Resolver exámenes y Unit Tests automáticamente (Full Autónomo)",
                value=True,
                key="chain_allow_exams",
                help="Permite resolver exámenes y Unit Tests acumulativos con todas sus preguntas y pronunciación de forma continua y autónoma."
            )

            auto_retry_choice = st.checkbox(
                "Reintentar automáticamente antes de pausar (Intento 2)",
                value=False,
                key="chain_retry",
                help="Desactivado por defecto para proteger tus intentos. Al estar desactivado, el sistema se detendrá inmediatamente si alguna respuesta no es 100% correcta."
            )

        col_step, col_chain, col_stop = st.columns([2, 2, 1])
        step_clicked = col_step.button("▶ Resolver Solo 1 y Avanzar", help="Resuelve únicamente el ejercicio en pantalla y se detiene.")
        start_clicked = col_chain.button("⏩ Iniciar Cadena Continua", type="primary")
        stop_clicked = col_stop.button("⏹ Detener")

        if stop_clicked:
            st.session_state.auto_stop_requested = True
            st.session_state.auto_status = "stopped"
            st.warning("Se solicitó detener la automatización.")

        if step_clicked:
            run_autonomous_execution(
                max_ex=1,
                is_single_step=True,
                min_conf=min_conf,
                delay_sec=delay_sec,
                auto_retry_choice=auto_retry_choice,
                allow_exams_choice=allow_exams_chain
            )
        elif start_clicked:
            run_autonomous_execution(
                max_ex=max_ex,
                is_single_step=False,
                min_conf=min_conf,
                delay_sec=delay_sec,
                auto_retry_choice=auto_retry_choice,
                allow_exams_choice=allow_exams_chain
            )

        render_execution_feedback()

    # ==========================================
    # MODO 4: MODO MANUAL (INSPECCIÓN)
    # ==========================================
    elif selected_mode == "✍️ Modo Manual (Inspección)":
        st.subheader("✍️ Modo Manual (Inspección)")
        st.info(
            "💡 **Modo Manual Activo:** Haz clic en 'Analizar' para que la IA proponga la solución. Puedes editarla antes de completarla. "
            "En exámenes o actividades, puedes completar cada pantalla e inspeccionar todo antes de enviar."
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Analizar", type="primary"):
                with st.spinner("Analizando ejercicio en pantalla..."):
                    def analyze_logic(page):
                        extractor = ContentExtractor(page)
                        ex_detector = ExerciseDetector(page)
                        text_content = extractor.extract_context()
                        image_b64 = extractor.extract_screenshot_b64()
                        audios_b64 = extractor.extract_audios_b64(page.context)
                        ex_type = ex_detector.detect_type()
                        return text_content, image_b64, audios_b64, ex_type
                    
                    result = run_with_browser(analyze_logic)
                    if result:
                        text_content, image_b64, audios_b64, ex_type = result
                        st.session_state.current_analysis = {
                            "text": text_content,
                            "image_b64": image_b64,
                            "audios_b64": audios_b64,
                            "type": ex_type.value
                        }
                        solver = AISolver()
                        sol = solver.solve(ex_type.value, text_content, image_b64, audios_b64)
                        st.session_state.current_solution = sol

        # Display Results
        if 'current_analysis' in st.session_state:
            st.subheader("Análisis")
            st.write(f"**Tipo:** {st.session_state.current_analysis['type']}")
            with st.expander("Contenido Extraído"):
                st.text(st.session_state.current_analysis['text'])
                
        if 'current_solution' in st.session_state:
            sol = st.session_state.current_solution
            if "error" in sol:
                st.error(f"Error de la IA: {sol['error']}")
            else:
                st.success("Solución Lista")
                st.write(f"**Pregunta:** {sol.get('question')}")
                st.write(f"**Respuesta IA:** {sol.get('answer')}")
                st.write(f"**Confianza:** {int(sol.get('confidence', 0)*100)}%")
                st.info(f"**Explicación:** {sol.get('explanation')}")
                
                edited_answer = st.text_area("Editar respuesta:", value=sol.get('answer'), height=150)
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if st.button("✓ Aceptar respuesta (Completar)"):
                        def fill_logic(page):
                            filler = FormFiller(page)
                            return filler.fill_answer(edited_answer, st.session_state.current_analysis['type'])
                            
                        fill_result = run_with_browser(fill_logic)
                        if fill_result:
                            success, msg = fill_result
                            if success:
                                st.success(f"Respuesta ingresada: {msg}")
                            else:
                                st.error(f"Fallo al ingresar respuesta: {msg}")
                with col_b:
                    if st.button("✗ Rechazar"):
                        st.session_state.pop('current_solution', None)
                        st.rerun()
                with col_c:
                    if st.button("➡️ Siguiente Pantalla / Ejercicio"):
                        def next_logic(page):
                            filler = FormFiller(page)
                            return filler.click_next_screen()

                        next_result = run_with_browser(next_logic)
                        if next_result:
                            ok, msg = next_result
                            if ok:
                                st.success(msg)
                                st.session_state.pop('current_solution', None)
                                st.session_state.pop('current_analysis', None)
                                time.sleep(1.0)
                                st.rerun()
                            else:
                                st.error(msg)

        # Diagnóstico de navegación (expandible, para cuando el botón ➡ no funciona)
        with st.expander("🔧 Diagnóstico: Inspeccionar botón de navegación del test"):
            st.write("Haz clic en el botón de abajo para ver todos los botones visibles en la página del Unit Test. Útil para depurar cuando el botón ➡ no se detecta automáticamente.")
            if st.button("🔍 Inspeccionar botones de navegación en Chrome"):
                def inspect_nav_buttons(page):
                    results = []
                    for i, frame in enumerate([page] + page.frames):
                        try:
                            frame_url = getattr(frame, 'url', 'main')
                            btns = frame.evaluate("""() => {
                                const buttons = Array.from(document.querySelectorAll('button, a[role="button"], [class*="nav"], [class*="arrow"], [class*="next"], [data-direction], [data-event]'));
                                return buttons.slice(0, 30).map(b => ({
                                    tag: b.tagName,
                                    text: (b.textContent || '').trim().slice(0, 50),
                                    className: b.className.slice(0, 80),
                                    dataEvent: b.getAttribute('data-event') || '',
                                    dataDirection: b.getAttribute('data-direction') || '',
                                    ariaLabel: b.getAttribute('aria-label') || '',
                                    title: b.getAttribute('title') || '',
                                    visible: b.offsetParent !== null,
                                    rect: (() => {
                                        const r = b.getBoundingClientRect();
                                        return { x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) };
                                    })()
                                }));
                            }""")
                            if btns:
                                results.append({"frame": i, "url": frame_url[:60], "buttons": btns})
                        except Exception as e:
                            results.append({"frame": i, "url": getattr(frame, 'url', '?')[:60], "error": str(e)})
                    return results

                diag_result = run_with_browser(inspect_nav_buttons)
                if diag_result:
                    for frame_data in diag_result:
                        st.markdown(f"**Frame {frame_data['frame']}:** `{frame_data.get('url', '?')}`")
                        if "error" in frame_data:
                            st.warning(f"Error: {frame_data['error']}")
                        elif frame_data.get("buttons"):
                            visible_btns = [b for b in frame_data["buttons"] if b.get("visible")]
                            if visible_btns:
                                st.dataframe(visible_btns, use_container_width=True)
                        st.markdown("---")

else:
    st.info("👋 **¡Bienvenido a NGL English Assistant!** Esperando conexión con tu navegador Chromium (Brave, Opera, Edge, Chrome)...")
    
    with st.container(border=True):
        st.subheader("📋 Pasos rápidos para comenzar:")
        
        # Estado de la API Key
        if settings.GEMINI_API_KEY:
            st.success("✅ **Clave de Gemini configurada:** `.env` cargado correctamente.")
        else:
            st.warning("⚠️ **Clave de Gemini no detectada:** Copia `.env.example` como `.env` e introduce tu `GEMINI_API_KEY` gratuita de [Google AI Studio](https://aistudio.google.com/).")
        
        st.markdown("---")
        st.markdown("### 1️⃣ Iniciar tu navegador en modo depuración remota")
        st.write("El asistente es compatible con **Brave, Opera, Opera GX, Microsoft Edge y Google Chrome**. Cierra tu navegador y ábrelo con el comando correspondiente:")
        
        tab_brave, tab_opera, tab_edge, tab_chrome, tab_other = st.tabs([
            "🦁 Brave", "🔴 Opera / Opera GX", "🌐 Microsoft Edge", "🟡 Google Chrome", "🍎 Mac / 🐧 Linux"
        ])
        with tab_brave:
            st.markdown("**Comando para Brave Browser (Windows):**")
            st.code(r'"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" --remote-debugging-port=9222 --user-data-dir="C:\brave-dev-profile"', language="cmd")
            st.caption("Si instalaste Brave a nivel de usuario: `%LOCALAPPDATA%\\BraveSoftware\\Brave-Browser\\Application\\brave.exe`.")
        with tab_opera:
            st.markdown("**Comando para Opera GX (Windows):**")
            st.code(r'"%LOCALAPPDATA%\Programs\Opera GX\launcher.exe" --remote-debugging-port=9222 --user-data-dir="C:\opera-dev-profile"', language="cmd")
            st.markdown("**Comando para Opera Estándar (Windows):**")
            st.code(r'"%LOCALAPPDATA%\Programs\Opera\launcher.exe" --remote-debugging-port=9222 --user-data-dir="C:\opera-dev-profile"', language="cmd")
        with tab_edge:
            st.markdown("**Comando para Microsoft Edge (preinstalado en todo Windows):**")
            st.code(r'"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="C:\edge-dev-profile"', language="cmd")
        with tab_chrome:
            st.markdown("**Comando para Google Chrome (Windows):**")
            st.code(r'"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-dev-profile"', language="cmd")
        with tab_other:
            st.markdown("**macOS (Brave, Opera, Chrome o Edge):**")
            st.code('/Applications/Brave\\ Browser.app/Contents/MacOS/Brave\\ Browser --remote-debugging-port=9222 --user-data-dir="/tmp/brave-dev-profile"', language="bash")
            st.markdown("**Linux:**")
            st.code('brave-browser --remote-debugging-port=9222 --user-data-dir="/tmp/brave-dev-profile"', language="bash")
            
        st.markdown("### 2️⃣ Iniciar sesión en National Geographic Learning")
        st.write("En la ventana del navegador que se abrió, ingresa a [learn.eltngl.com](https://learn.eltngl.com) y entra al ejercicio que deseas resolver.")
        
        st.markdown("### 3️⃣ Conectar el Asistente")
        if st.button("🔄 Reintentar Conexión con el Navegador", type="primary"):
            st.rerun()
