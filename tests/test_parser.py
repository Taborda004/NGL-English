import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzer.exercise_detector import ExerciseDetector, ExerciseType

class MockPage:
    def __init__(self, html):
        self.html = html
    def content(self):
        return self.html

def test_detect_multiple_choice():
    page = MockPage('<div><input type="radio" name="q1">Option A</div>')
    detector = ExerciseDetector(page)
    assert detector.detect_type() == ExerciseType.MULTIPLE_CHOICE

def test_detect_fill_blank():
    page = MockPage('<div>She <input type="text"> to the store.</div>')
    detector = ExerciseDetector(page)
    assert detector.detect_type() == ExerciseType.FILL_BLANK

def test_detect_sorting():
    page = MockPage('<div class="osSorting"><div class="os-sorting-element">item</div></div>')
    detector = ExerciseDetector(page)
    assert detector.detect_type() == ExerciseType.SORTING

def test_detect_dropdown():
    page = MockPage('<div class="listbox wrapper-dropdown"><ul class="listbox__choices"></ul></div>')
    detector = ExerciseDetector(page)
    assert detector.detect_type() == ExerciseType.DROPDOWN

def test_detect_matching():
    page = MockPage('<div class="interaction is-linking-lines"><div class="ll_element_view"></div></div>')
    detector = ExerciseDetector(page)
    assert detector.detect_type() == ExerciseType.MATCHING

def test_detect_speaking():
    page = MockPage('<div class="contentblock contentblock--SpeakingAndRecording"><button class="record">Record</button></div>')
    detector = ExerciseDetector(page)
    assert detector.detect_type() == ExerciseType.SPEAKING

def test_clean_fill_blanks():
    import re
    answer_text = "1. application | 2. intend | 3. arrangement | 4. consideration | 5. decide | 6. recommend"
    raw_chunks = answer_text.split('|')
    clean = []
    for c in raw_chunks:
        c = c.strip()
        val = re.sub(r'^\s*\d+[\.\)\-]\s*', '', c).strip()
        if val:
            clean.append(val)
    assert clean == ["application", "intend", "arrangement", "consideration", "decide", "recommend"]

def test_parse_matching_pairs():
    import re
    answer_text = "1. create a resume = write a summary | 2. do an internship = get work experience"
    parts = [p.strip() for p in re.split(r'[|\n]', answer_text) if p.strip()]
    raw_pairs = []
    for part in parts:
        clean = re.sub(r'^\s*\d+[\.\)\-]\s*', '', part).strip()
        if '=' in clean:
            s, t = clean.split('=', 1)
            raw_pairs.append((s.strip(), t.strip()))
    assert raw_pairs == [("create a resume", "write a summary"), ("do an internship", "get work experience")]
