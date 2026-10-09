import json
import os
from datetime import datetime

class HistoryManager:
    def __init__(self, filepath="history/history.json"):
        self.filepath = filepath
        self._ensure_file()
        
    def _ensure_file(self):
        if not os.path.exists('history'):
            os.makedirs('history')
        if not os.path.exists(self.filepath):
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump([], f)
                
    def load(self):
        with open(self.filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    def save_entry(self, assignment, exercise, question, proposed_answer, accepted_answer, explanation):
        history = self.load()
        entry = {
            "date": datetime.now().isoformat(),
            "assignment": assignment,
            "exercise": exercise,
            "question": question,
            "proposed_answer": proposed_answer,
            "accepted_answer": accepted_answer,
            "explanation": explanation
        }
        history.append(entry)
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4)
            
    def clear(self):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump([], f)
