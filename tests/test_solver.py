import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.prompts import build_user_prompt

def test_build_user_prompt():
    prompt = build_user_prompt("MULTIPLE_CHOICE", "Question: ...")
    assert "MULTIPLE_CHOICE" in prompt
    assert "Question:" in prompt
