import time
import logging
from typing import Callable, Optional, Dict, Any

from browser.browser_manager import BrowserManager
from browser.page_detector import PageDetector
from analyzer.content_extractor import ContentExtractor
from analyzer.exercise_detector import ExerciseDetector, ExerciseType
from ai.solver import AISolver
from interaction.form_filler import FormFiller
from config.settings import settings

logger = logging.getLogger(__name__)


class ChainRunner:
    """
    Automated sequential runner for NGL English exercises.
    Solves exercises in a chain, verifies 100% correctness after submission,
    and pauses immediately upon any error or incorrect answer.
    """

    def __init__(
        self,
        port: int = settings.CHROME_DEBUGGING_PORT,
        min_confidence: float = 0.80,
        delay_between_exercises: float = 2.0,
        max_exercises: int = 50,
        auto_retry: bool = False,
        allow_exams: bool = True,
    ):
        self.port = port
        self.min_confidence = min_confidence
        self.delay_between_exercises = delay_between_exercises
        self.max_exercises = max_exercises
        self.auto_retry = auto_retry
        self.allow_exams = allow_exams

    def run_chain(
        self,
        callback_log: Optional[Callable[[Dict[str, Any]], None]] = None,
        is_stopped: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the autonomous chaining loop.
        
        Args:
            callback_log: Optional function called on each step/event with status dict.
            is_stopped: Optional function returning True if user requested stop.
            
        Returns:
            Dict containing final status: 'status' ('completed', 'paused_error', 'stopped'),
            'total_solved', 'history', 'reason'.
        """
        manager = BrowserManager(port=self.port)
        if not manager.connect():
            err_msg = "No se pudo conectar a Chrome en el puerto de depuración (9222)."
            return {"status": "paused_error", "total_solved": 0, "reason": err_msg, "history": []}

        history = []
        solved_count = 0

        try:
            page = manager.get_current_page()
            if not page:
                err_msg = "No se encontró la página activa de NGL en Chrome."
                return {"status": "paused_error", "total_solved": 0, "reason": err_msg, "history": []}

            def notify(event_type: str, data: Dict[str, Any]):
                if callback_log:
                    payload = {"event": event_type, "solved_count": solved_count, **data}
                    callback_log(payload)

            notify("info", {"message": "Iniciando cadena autónoma de resolución..."})

            while solved_count < self.max_exercises:
                # 1. Check user stop request
                if is_stopped and is_stopped():
                    notify("stopped", {"message": "Automatización detenida por el usuario."})
                    return {
                        "status": "stopped",
                        "total_solved": solved_count,
                        "reason": "Detenido manualmente por el usuario.",
                        "history": history,
                    }

                # 2. Detect page & exercise title
                detector = PageDetector(page)
                page_info = detector.get_assignment_info()
                assignment_title = page_info.get("title", "Asignación NGL")

                # Get exercise title from iframe or heading
                exercise_title = "Ejercicio"
                for f in page.frames:
                    if "cdn_proxy" in f.url or "avallain" in f.url:
                        try:
                            t = f.evaluate("() => $('.learningObject__title, h1, h2, .lo-title').text().trim() || document.title")
                            if t:
                                exercise_title = t
                                break
                        except Exception:
                            pass

                notify("step_start", {
                    "exercise_index": solved_count + 1,
                    "assignment_title": assignment_title,
                    "exercise_title": exercise_title,
                    "message": f"Analizando ejercicio {solved_count + 1}: {exercise_title}"
                })

                filler = FormFiller(page)

                # Check if current activity was already submitted with 100% success or finalized
                is_already_completed = False
                for f in page.frames:
                    if "cdn_proxy" in f.url or "avallain" in f.url:
                        try:
                            eval_res = f.evaluate("""() => {
                                const $ = window.jQuery;
                                if (!$) return false;
                                const doneVisible = $('button[data-event="done"], .learningObject__button--cal-done').filter(':visible').length > 0;
                                const retryVisible = $('button[data-event="retry"]').filter(':visible:not(.disabled):not([disabled])').length > 0;
                                const nextLoBtn = $('button[data-event="forward_lo"], .learningObject__controls-button:contains("Next")').filter(':visible:not(.inactive_button):not([disabled])');
                                const hasCorrect = $('.status-corrected, [class*="status-corrected"]').length > 0;
                                const wrong = $('.check.wrong, .check.incorrect, .status-wrong, .is-incorrect').filter(':visible').length;
                                
                                if (nextLoBtn.length > 0 && !doneVisible && !retryVisible) return true;
                                return (nextLoBtn.length > 0 || hasCorrect) && wrong === 0;
                            }""")
                            if eval_res is True:
                                is_already_completed = True
                                break
                        except Exception:
                            pass

                if is_already_completed is True:
                    notify("info", {"message": f"El ejercicio '{exercise_title}' ya se encuentra completado al 100%. Avanzando al siguiente..."})
                    solved_count += 1
                    time.sleep(self.delay_between_exercises)
                    next_ok, next_msg = filler.click_next_exercise()
                    if not next_ok:
                        notify("completed", {
                            "message": f"Asignación finalizada. Se resolvieron {solved_count} ejercicios exitosamente al 100%."
                        })
                        return {
                            "status": "completed",
                            "total_solved": solved_count,
                            "reason": "Asignación finalizada sin más ejercicios.",
                            "history": history,
                        }
                    continue

                # 2.5 Detección y manejo de exámenes / Unit Tests
                is_exam = any(kw in exercise_title.lower() for kw in ["unit test", "review test", "final test", "midterm test", "assessment"])
                if is_exam and not self.allow_exams:
                    reason = (
                        f"[ALERTA] DETECCIÓN DE EXAMEN: '{exercise_title}'. "
                        f"El modo autónomo para exámenes está desactivado. Actívalo en las opciones de configuración para resolverlo automáticamente."
                    )
                    notify("error", {"reason": reason, "exercise_title": exercise_title})
                    return {
                        "status": "paused_error",
                        "total_solved": solved_count,
                        "reason": reason,
                        "history": history,
                    }

                if is_exam:
                    notify("info", {"message": f"Examen/Unit Test detectado: '{exercise_title}'. Resolviendo en modo autónomo..."})

                # Bucle de pantallas de la actividad (resuelve multi-pantallas y exámenes completos)
                screen_count = 0
                max_screens_per_activity = 60
                last_answer_text = ""
                last_type = ""
                last_confidence = 1.0

                while screen_count < max_screens_per_activity:
                    screen_count += 1
                    if is_stopped and is_stopped():
                        notify("stopped", {"message": "Automatización detenida por el usuario."})
                        return {
                            "status": "stopped",
                            "total_solved": solved_count,
                            "reason": "Detenido manualmente por el usuario.",
                            "history": history,
                        }

                    # Obtener subtítulo detallado si es multi-pantalla
                    current_screen_name = exercise_title
                    for f in page.frames:
                        if "cdn_proxy" in f.url or "avallain" in f.url:
                            try:
                                s_info = f.evaluate("""() => {
                                    let active = $('.content-wrap:visible, .activity:visible').first();
                                    if (active.length === 0) {
                                        active = $('.content-wrap, .activity').filter(function() { return $(this).css('display') !== 'none'; }).first();
                                    }
                                    const rubric = active.find('.layout__rubric, .rubric, .learningObject__rubric').first().text().trim();
                                    const wraps = $('.content-wrap');
                                    let screenNum = '';
                                    if (wraps.length > 1 && active.length > 0) {
                                        const idx = wraps.index(active);
                                        if (idx !== -1) screenNum = `Pantalla ${idx + 1} de ${wraps.length}`;
                                    }
                                    const bodyText = document.body ? document.body.innerText : '';
                                    const screenMatch = bodyText.match(/Screen[:\\s]*(\\d+)\\s*of\\s*(\\d+)/i);
                                    if (screenMatch && !screenNum) screenNum = screenMatch[0];
                                    return { rubric, screenNum };
                                }""")
                                if isinstance(s_info, dict):
                                    parts = []
                                    if s_info.get('screenNum'): parts.append(s_info['screenNum'])
                                    if s_info.get('rubric'): parts.append(s_info['rubric'])
                                    if parts:
                                        current_screen_name = f"{exercise_title} ({' — '.join(parts)})"
                                    break
                            except Exception:
                                pass

                    # 3. Extract content & detect type
                    extractor = ContentExtractor(page)
                    ex_detector = ExerciseDetector(page)
                    filler = FormFiller(page)

                    text_content = extractor.extract_context()
                    image_b64 = extractor.extract_screenshot_b64()
                    audios_b64 = extractor.extract_audios_b64(page.context)
                    ex_type = ex_detector.detect_type()

                    # Pantalla final de resumen de puntuación
                    if ex_type == ExerciseType.UNKNOWN:
                        is_score_screen = False
                        for f in page.frames:
                            if "cdn_proxy" in f.url or "avallain" in f.url:
                                try:
                                    is_score_screen = f.evaluate("""() => {
                                        let active = $('.content-wrap:visible, .activity:visible').first();
                                        if (active.length === 0) {
                                            active = $('.content-wrap, .activity').filter(function() { return $(this).css('display') !== 'none'; }).first();
                                        }
                                        return active.text().includes('Your score') || $('.score, .summary').filter(':visible').length > 0;
                                    }""") is True
                                    if is_score_screen:
                                        break
                                except Exception:
                                    pass
                        if is_score_screen:
                            notify("info", {"message": f"Pantalla de resumen alcanzada en '{exercise_title}'."})
                            break

                    if not ex_type or ex_type.value == "UNKNOWN":
                        reason = f"Tipo de ejercicio no reconocido en '{current_screen_name}'. Automatización pausada para revisión manual."
                        notify("error", {"reason": reason, "exercise_title": current_screen_name})
                        return {
                            "status": "paused_error",
                            "total_solved": solved_count,
                            "reason": reason,
                            "history": history,
                        }

                    notify("analysis_ready", {
                        "type": ex_type.value,
                        "text_preview": text_content[:200] if text_content else "",
                        "has_audio": bool(audios_b64),
                        "has_image": bool(image_b64),
                        "message": f"[{current_screen_name}] Tipo detectado: {ex_type.value}. Consultando IA..."
                    })

                    # 4. Solve with AI
                    solver = AISolver()
                    sol = solver.solve(ex_type.value, text_content, image_b64, audios_b64)

                    if "error" in sol:
                        reason = f"Error en la IA al resolver '{current_screen_name}': {sol['error']}"
                        notify("error", {"reason": reason, "exercise_title": current_screen_name})
                        return {
                            "status": "paused_error",
                            "total_solved": solved_count,
                            "reason": reason,
                            "history": history,
                        }

                    confidence = float(sol.get("confidence", 1.0))
                    if confidence < self.min_confidence:
                        reason = f"Confianza de IA demasiado baja ({int(confidence * 100)}% < {int(self.min_confidence * 100)}%) en '{current_screen_name}'. Automatización pausada por seguridad."
                        notify("error", {"reason": reason, "exercise_title": current_screen_name, "confidence": confidence})
                        return {
                            "status": "paused_error",
                            "total_solved": solved_count,
                            "reason": reason,
                            "history": history,
                        }

                    answer_text = sol.get("answer", "")
                    notify("solution_ready", {
                        "answer": answer_text,
                        "confidence": confidence,
                        "explanation": sol.get("explanation", ""),
                        "message": f"Respuesta obtenida ({int(confidence * 100)}% confianza). Aplicando al formulario..."
                    })

                    # 5. Fill form (SPEAKING maneja automáticamente el streaming de audio TTS al cable virtual)
                    fill_ok, fill_msg = filler.fill_answer(answer_text, ex_type.value)

                    if not fill_ok:
                        reason = f"Fallo al rellenar el ejercicio '{current_screen_name}': {fill_msg}"
                        notify("error", {"reason": reason, "exercise_title": current_screen_name})
                        return {
                            "status": "paused_error",
                            "total_solved": solved_count,
                            "reason": reason,
                            "history": history,
                        }

                    notify("filled", {
                        "message": f"Pantalla completada: {fill_msg}"
                    })
                    last_answer_text = answer_text
                    last_type = ex_type.value
                    last_confidence = confidence

                    time.sleep(1.0)

                    # Verificar si existe otra pantalla en esta misma actividad/examen
                    has_more_screens = filler.has_next_screen() == True
                    if has_more_screens:
                        notify("info", {"message": "Avanzando a la siguiente pantalla del ejercicio/examen..."})
                        time.sleep(self.delay_between_exercises)
                        next_scr_ok, next_scr_msg = filler.click_next_screen()
                        if not next_scr_ok:
                            has_more_screens = False

                    if not has_more_screens:
                        # Se completó la última pantalla de la actividad
                        break

                # 6. Submit ("Done" / "Submit to Gradebook")
                notify("info", {
                    "message": f"Actividad finalizada ({screen_count} pantalla(s)). Enviando respuesta definitiva ('Done')..."
                })
                time.sleep(1.0)

                submit_ok, submit_msg = filler.submit_done()
                if not submit_ok and not is_exam:
                    reason = f"Fallo al presionar 'Done' en '{exercise_title}': {submit_msg}"
                    notify("error", {"reason": reason, "exercise_title": exercise_title})
                    return {
                        "status": "paused_error",
                        "total_solved": solved_count,
                        "reason": reason,
                        "history": history,
                    }

                # 7. Check accuracy (100% verification)
                time.sleep(1.5)
                is_perfect, acc_msg, details = filler.check_submission_accuracy()
                if not is_perfect:
                    # Solo reintentar automáticamente si está explícitamente habilitado y no es examen
                    if self.auto_retry and not is_exam:
                        has_retry = False
                        for f in page.frames:
                            if "cdn_proxy" in f.url or "avallain" in f.url:
                                try:
                                    has_retry = f.evaluate("""() => {
                                        const $ = window.jQuery;
                                        if (!$) return false;
                                        return $('button[data-event="retry"]:visible:not(.disabled):not([disabled])').length > 0;
                                    }""")
                                    if has_retry:
                                        break
                                except Exception:
                                    pass
                                    
                        if has_retry:
                            notify("info", {"message": f"Intento 1 con advertencia ({acc_msg}). Reintentando ejercicio '{exercise_title}' (segundo intento)..."})
                            for f in page.frames:
                                if "cdn_proxy" in f.url or "avallain" in f.url:
                                    try:
                                        f.evaluate("""() => {
                                            const $ = window.jQuery;
                                            const r = $('button[data-event="retry"]:visible:not(.disabled):not([disabled])');
                                            if (r.length > 0) r[0].click();
                                            const ok = $('.dialog button:contains("Yes"), .dialog button:contains("OK")');
                                            if (ok.length > 0) ok[0].click();
                                        }""")
                                    except Exception:
                                        pass
                            time.sleep(2.0)
                            
                            text_content = extractor.extract_context()
                            image_b64 = extractor.extract_screenshot_b64()
                            audios_b64 = extractor.extract_audios_b64(page.context)
                            
                            retry_sol = solver.solve(ex_type.value, text_content + f"\n\nNote: Previous submission had: {acc_msg}. Please review tenses, word order and choices with utmost precision.", image_b64, audios_b64)
                            retry_answer = retry_sol.get("answer", last_answer_text)
                            
                            fill_ok, fill_msg = filler.fill_answer(retry_answer, ex_type.value)
                            time.sleep(1.0)
                            submit_ok, submit_msg = filler.submit_done()
                            time.sleep(2.0)
                            
                            is_perfect, acc_msg, details = filler.check_submission_accuracy()
                            if is_perfect:
                                last_answer_text = retry_answer
                                last_confidence = float(retry_sol.get("confidence", 1.0))
                                notify("info", {"message": f"[OK] Segundo intento corregido al 100%: {acc_msg}"})

                    if not is_perfect and not is_exam:
                        reason = f"RESPUESTA INCORRECTA DETECTADA en '{exercise_title}': {acc_msg}. Automatización detenida de inmediato para conservar los intentos restantes y permitir corregir el código o la respuesta."
                        notify("error", {
                            "reason": reason,
                            "exercise_title": exercise_title,
                            "accuracy_details": details,
                            "submitted_answer": last_answer_text
                        })
                        return {
                            "status": "paused_error",
                            "total_solved": solved_count,
                            "reason": reason,
                            "history": history,
                        }
                    elif not is_perfect and is_exam:
                        notify("info", {"message": f"Resultado del examen: {acc_msg}"})

                # Successfully verified at 100%!
                solved_count += 1
                record_type = last_type if screen_count == 1 else f"Multi-pantalla ({screen_count})"
                record_answer = last_answer_text if screen_count == 1 else f"{screen_count} pantallas resueltas"
                record = {
                    "index": solved_count,
                    "exercise_title": exercise_title,
                    "type": record_type,
                    "answer": record_answer,
                    "confidence": last_confidence,
                    "result": acc_msg
                }
                history.append(record)

                notify("step_success", {
                    "record": record,
                    "message": f"Ejercicio {solved_count} completado: {acc_msg}"
                })

                # 8. Advance to next exercise
                time.sleep(self.delay_between_exercises)
                next_ok, next_msg = filler.click_next_exercise()

                if not next_ok:
                    notify("completed", {
                        "message": f"Asignación finalizada. Se resolvieron {solved_count} ejercicios exitosamente al 100%."
                    })
                    return {
                        "status": "completed",
                        "total_solved": solved_count,
                        "reason": "Asignación finalizada sin más ejercicios.",
                        "history": history,
                    }

                if solved_count < self.max_exercises:
                    notify("info", {"message": "Avanzando al siguiente ejercicio en la cadena..."})
                else:
                    notify("info", {"message": "Siguiente ejercicio cargado en pantalla. Pausando para control del usuario..."})

            if self.max_exercises == 1:
                notify("completed", {
                    "message": "Ejercicio resuelto al 100% y avanzado al siguiente con éxito."
                })
                return {
                    "status": "completed",
                    "total_solved": solved_count,
                    "reason": "Ejercicio resuelto al 100% y avanzado al siguiente con éxito.",
                    "history": history,
                }
            else:
                notify("completed", {
                    "message": f"Límite máximo de {self.max_exercises} ejercicios alcanzado."
                })
                return {
                    "status": "completed",
                    "total_solved": solved_count,
                    "reason": f"Límite máximo de {self.max_exercises} alcanzado.",
                    "history": history,
                }

        finally:
            manager.close()
