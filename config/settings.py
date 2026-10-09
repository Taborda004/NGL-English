import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    CHROME_DEBUGGING_PORT = int(os.getenv('CHROME_DEBUGGING_PORT', 9222))
    
    # Selectors for NGL Platform
    SELECTOR_ASSIGNMENT_CONTAINER = '.assignment-container' # Example placeholder
    SELECTOR_QUESTION = '.question-text'
    SELECTOR_OPTION = '.option-label'

settings = Settings()

