import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    CHROME_DEBUGGING_PORT = int(os.getenv('CHROME_DEBUGGING_PORT', 9222))
    LICENSE_KEY = os.getenv('LICENSE_KEY', '')
    AUTH_ENDPOINT_URL = os.getenv(
        'AUTH_ENDPOINT_URL',
        'https://raw.githubusercontent.com/Taborda004/NGL-English/main/auth/licenses.json'
    )
    
    # Selectors for NGL Platform
    SELECTOR_ASSIGNMENT_CONTAINER = '.assignment-container' # Example placeholder
    SELECTOR_QUESTION = '.question-text'
    SELECTOR_OPTION = '.option-label'

settings = Settings()

