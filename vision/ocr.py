import pytesseract
from PIL import Image
import io

class OCRProcessor:
    @staticmethod
    def extract_text_from_bytes(image_bytes: bytes) -> str:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
