import pytest
from unittest.mock import MagicMock, patch
from automation.chain_runner import ChainRunner
from analyzer.exercise_detector import ExerciseType


def test_chain_runner_init():
    runner = ChainRunner(port=9222, min_confidence=0.85, delay_between_exercises=1.5, max_exercises=10)
    assert runner.port == 9222
    assert runner.min_confidence == 0.85
    assert runner.delay_between_exercises == 1.5
    assert runner.max_exercises == 10


def test_chain_runner_no_browser_connection():
    runner = ChainRunner(port=9999)
    with patch("automation.chain_runner.BrowserManager") as mock_bm:
        instance = mock_bm.return_value
        instance.connect.return_value = False
        res = runner.run_chain()
        assert res["status"] == "paused_error"
        assert "No se pudo conectar a Chrome" in res["reason"]


def test_chain_runner_stops_on_user_request():
    runner = ChainRunner(port=9222)
    with patch("automation.chain_runner.BrowserManager") as mock_bm:
        instance = mock_bm.return_value
        instance.connect.return_value = True
        mock_page = MagicMock()
        mock_page.frames = []
        instance.get_current_page.return_value = mock_page

        # is_stopped returns True immediately
        res = runner.run_chain(is_stopped=lambda: True)
        assert res["status"] == "stopped"
        assert res["total_solved"] == 0


def test_chain_runner_pauses_on_unknown_exercise_type():
    runner = ChainRunner(port=9222)
    with patch("automation.chain_runner.BrowserManager") as mock_bm, \
         patch("automation.chain_runner.ExerciseDetector") as mock_det, \
         patch("automation.chain_runner.ContentExtractor") as mock_ext:
        
        instance = mock_bm.return_value
        instance.connect.return_value = True
        mock_page = MagicMock()
        mock_page.frames = []
        instance.get_current_page.return_value = mock_page

        mock_det.return_value.detect_type.return_value = ExerciseType.UNKNOWN
        mock_ext.return_value.extract_context.return_value = "Some text"
        mock_ext.return_value.extract_screenshot_b64.return_value = None
        mock_ext.return_value.extract_audios_b64.return_value = []

        res = runner.run_chain()
        assert res["status"] == "paused_error"
        assert "Tipo de ejercicio no reconocido" in res["reason"]


def test_chain_runner_pauses_on_incorrect_submission():
    runner = ChainRunner(port=9222)
    with patch("automation.chain_runner.BrowserManager") as mock_bm, \
         patch("automation.chain_runner.ExerciseDetector") as mock_det, \
         patch("automation.chain_runner.ContentExtractor") as mock_ext, \
         patch("automation.chain_runner.AISolver") as mock_solver, \
         patch("automation.chain_runner.FormFiller") as mock_filler:
        
        instance = mock_bm.return_value
        instance.connect.return_value = True
        mock_page = MagicMock()
        mock_page.frames = []
        instance.get_current_page.return_value = mock_page

        mock_det.return_value.detect_type.return_value = ExerciseType.FILL_BLANK
        mock_ext.return_value.extract_context.return_value = "Question text"
        mock_ext.return_value.extract_screenshot_b64.return_value = None
        mock_ext.return_value.extract_audios_b64.return_value = []

        mock_solver.return_value.solve.return_value = {
            "answer": "my answer",
            "confidence": 0.95
        }

        mock_filler.return_value.fill_answer.return_value = (True, "Filled")
        mock_filler.return_value.submit_done.return_value = (True, "Submitted")
        # Accuracy returns False (error detected)
        mock_filler.return_value.check_submission_accuracy.return_value = (
            False,
            "Se detectaron 1 respuestas incorrectas.",
            {"wrongCount": 1}
        )

        res = runner.run_chain()
        assert res["status"] == "paused_error"
        assert "RESPUESTA INCORRECTA DETECTADA" in res["reason"]
        assert res["total_solved"] == 0


def test_chain_runner_handles_presentation_exercise():
    runner = ChainRunner(port=9222, max_exercises=1)
    with patch("automation.chain_runner.BrowserManager") as mock_bm, \
         patch("automation.chain_runner.ExerciseDetector") as mock_det, \
         patch("automation.chain_runner.ContentExtractor") as mock_ext, \
         patch("automation.chain_runner.AISolver") as mock_solver, \
         patch("automation.chain_runner.FormFiller") as mock_filler:
        
        instance = mock_bm.return_value
        instance.connect.return_value = True
        mock_page = MagicMock()
        mock_page.frames = []
        instance.get_current_page.return_value = mock_page

        mock_det.return_value.detect_type.return_value = ExerciseType.PRESENTATION
        mock_ext.return_value.extract_context.return_value = "Listen to the sentences. Then repeat them."
        mock_ext.return_value.extract_screenshot_b64.return_value = None
        mock_ext.return_value.extract_audios_b64.return_value = []

        mock_solver.return_value.solve.return_value = {
            "answer": "N/A",
            "confidence": 1.0,
            "explanation": "Presentation"
        }

        mock_filler.return_value.fill_answer.return_value = (True, "Presentation ready")
        mock_filler.return_value.submit_done.return_value = (True, "Submitted")
        mock_filler.return_value.check_submission_accuracy.return_value = (
            True,
            "Actividad completada sin errores detectados.",
            {"wrongCount": 0}
        )
        mock_filler.return_value.click_next_exercise.return_value = (False, "No next exercise")

        res = runner.run_chain()
        assert res["status"] == "completed"
        assert res["total_solved"] == 1
        assert res["history"][0]["type"] == "PRESENTATION"


def test_chain_runner_stops_immediately_without_retry():
    runner = ChainRunner(port=9222, auto_retry=False)
    with patch("automation.chain_runner.BrowserManager") as mock_bm, \
         patch("automation.chain_runner.ExerciseDetector") as mock_det, \
         patch("automation.chain_runner.ContentExtractor") as mock_ext, \
         patch("automation.chain_runner.AISolver") as mock_solver, \
         patch("automation.chain_runner.FormFiller") as mock_filler:
        
        instance = mock_bm.return_value
        instance.connect.return_value = True
        mock_page = MagicMock()
        mock_page.frames = []
        instance.get_current_page.return_value = mock_page

        mock_det.return_value.detect_type.return_value = ExerciseType.MULTIPLE_CHOICE
        mock_ext.return_value.extract_context.return_value = "Question 1"
        mock_ext.return_value.extract_screenshot_b64.return_value = None
        mock_ext.return_value.extract_audios_b64.return_value = []

        mock_solver.return_value.solve.return_value = {
            "answer": "Option A",
            "confidence": 0.95
        }

        mock_filler.return_value.fill_answer.return_value = (True, "Filled")
        mock_filler.return_value.submit_done.return_value = (True, "Submitted")
        mock_filler.return_value.check_submission_accuracy.return_value = (
            False,
            "Se detectaron 1 respuestas incorrectas.",
            {"wrongCount": 1}
        )

        res = runner.run_chain()
        assert res["status"] == "paused_error"
        assert res["total_solved"] == 0
        assert "RESPUESTA INCORRECTA DETECTADA" in res["reason"]
        # Make sure solve was only called ONCE (no auto-retry attempted)
        assert mock_solver.return_value.solve.call_count == 1


def test_chain_runner_single_step_advances_and_stops():
    runner = ChainRunner(port=9222, max_exercises=1)
    with patch("automation.chain_runner.BrowserManager") as mock_bm, \
         patch("automation.chain_runner.ExerciseDetector") as mock_det, \
         patch("automation.chain_runner.ContentExtractor") as mock_ext, \
         patch("automation.chain_runner.AISolver") as mock_solver, \
         patch("automation.chain_runner.FormFiller") as mock_filler:
        
        instance = mock_bm.return_value
        instance.connect.return_value = True
        mock_page = MagicMock()
        mock_page.frames = []
        instance.get_current_page.return_value = mock_page

        mock_det.return_value.detect_type.return_value = ExerciseType.FILL_BLANK
        mock_ext.return_value.extract_context.return_value = "Vocabulary Question 1"
        mock_ext.return_value.extract_screenshot_b64.return_value = None
        mock_ext.return_value.extract_audios_b64.return_value = []

        mock_solver.return_value.solve.return_value = {
            "answer": "correct_word",
            "confidence": 0.98
        }

        mock_filler.return_value.fill_answer.return_value = (True, "Filled successfully")
        mock_filler.return_value.submit_done.return_value = (True, "Done clicked")
        mock_filler.return_value.check_submission_accuracy.return_value = (
            True,
            "100% de respuestas correctas",
            {"wrongCount": 0}
        )
        mock_filler.return_value.click_next_exercise.return_value = (True, "Avanzado al siguiente ejercicio")

        events_logged = []
        def log_cb(payload):
            events_logged.append(payload.get("event"))

        res = runner.run_chain(callback_log=log_cb)

        assert res["status"] == "completed"
        assert res["total_solved"] == 1
        assert "avanzado al siguiente" in res["reason"]
        # Verify it submitted and clicked next exercise
        mock_filler.return_value.submit_done.assert_called_once()
        mock_filler.return_value.click_next_exercise.assert_called_once()
        assert "step_success" in events_logged
        assert "completed" in events_logged


def test_chain_runner_blocks_exam_when_allow_exams_false():
    runner = ChainRunner(port=9222, allow_exams=False)
    with patch("automation.chain_runner.BrowserManager") as mock_bm:
        instance = mock_bm.return_value
        instance.connect.return_value = True
        mock_page = MagicMock()
        mock_frame = MagicMock()
        mock_frame.url = "https://cdn_proxy.eltngl.com"
        mock_frame.evaluate.return_value = "Unit 8 | Unit Test"
        mock_page.frames = [mock_frame]
        instance.get_current_page.return_value = mock_page

        res = runner.run_chain()
        assert res["status"] == "paused_error"
        assert "DETECCIÓN DE EXAMEN" in res["reason"]


def test_chain_runner_solves_exam_when_allow_exams_true():
    runner = ChainRunner(port=9222, allow_exams=True, max_exercises=1)
    with patch("automation.chain_runner.BrowserManager") as mock_bm, \
         patch("automation.chain_runner.ExerciseDetector") as mock_det, \
         patch("automation.chain_runner.ContentExtractor") as mock_ext, \
         patch("automation.chain_runner.AISolver") as mock_solver, \
         patch("automation.chain_runner.FormFiller") as mock_filler:

        instance = mock_bm.return_value
        instance.connect.return_value = True
        mock_page = MagicMock()
        mock_frame = MagicMock()
        mock_frame.url = "https://cdn_proxy.eltngl.com"
        mock_frame.evaluate.return_value = "Unit 8 | Unit Test"
        mock_page.frames = [mock_frame]
        instance.get_current_page.return_value = mock_page

        mock_det.return_value.detect_type.return_value = ExerciseType.MULTIPLE_CHOICE
        mock_ext.return_value.extract_context.return_value = "Exam question 1"
        mock_ext.return_value.extract_screenshot_b64.return_value = None
        mock_ext.return_value.extract_audios_b64.return_value = []

        mock_solver.return_value.solve.return_value = {
            "answer": "choice b",
            "confidence": 0.99
        }

        mock_filler.return_value.has_next_screen.return_value = False
        mock_filler.return_value.fill_answer.return_value = (True, "Marked choice b")
        mock_filler.return_value.submit_done.return_value = (True, "Submitted to gradebook")
        mock_filler.return_value.check_submission_accuracy.return_value = (
            True,
            "100% de respuestas correctas",
            {"wrongCount": 0}
        )
        mock_filler.return_value.click_next_exercise.return_value = (False, "Assignment completed")

        res = runner.run_chain()
        assert res["status"] == "completed"
        assert res["total_solved"] == 1
        mock_filler.return_value.submit_done.assert_called_once()


def test_chain_runner_solves_multi_screen_activity():
    runner = ChainRunner(port=9222, allow_exams=True, max_exercises=1)
    with patch("automation.chain_runner.BrowserManager") as mock_bm, \
         patch("automation.chain_runner.ExerciseDetector") as mock_det, \
         patch("automation.chain_runner.ContentExtractor") as mock_ext, \
         patch("automation.chain_runner.AISolver") as mock_solver, \
         patch("automation.chain_runner.FormFiller") as mock_filler:

        instance = mock_bm.return_value
        instance.connect.return_value = True
        mock_page = MagicMock()
        mock_page.frames = []
        instance.get_current_page.return_value = mock_page

        mock_det.return_value.detect_type.return_value = ExerciseType.FILL_BLANK
        mock_ext.return_value.extract_context.return_value = "Screen text"
        mock_ext.return_value.extract_screenshot_b64.return_value = None
        mock_ext.return_value.extract_audios_b64.return_value = []

        mock_solver.return_value.solve.return_value = {
            "answer": "answer",
            "confidence": 0.95
        }

        # Simulates 2 screens: has_next_screen is True on screen 1, False on screen 2
        mock_filler.return_value.has_next_screen.side_effect = [True, False]
        mock_filler.return_value.click_next_screen.return_value = (True, "Advanced to screen 2")
        mock_filler.return_value.fill_answer.return_value = (True, "Filled")
        mock_filler.return_value.submit_done.return_value = (True, "Done clicked")
        mock_filler.return_value.check_submission_accuracy.return_value = (
            True,
            "100% correcto",
            {"wrongCount": 0}
        )
        mock_filler.return_value.click_next_exercise.return_value = (False, "End of assignment")

        res = runner.run_chain()
        assert res["status"] == "completed"
        assert res["total_solved"] == 1
        # Form should be filled twice (for both screens)
        assert mock_filler.return_value.fill_answer.call_count == 2
        # Next screen should be clicked once
        mock_filler.return_value.click_next_screen.assert_called_once()
        # Submit done called once at the end
        mock_filler.return_value.submit_done.assert_called_once()


