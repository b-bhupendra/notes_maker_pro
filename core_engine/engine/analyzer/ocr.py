import cv2
import logging

logger = logging.getLogger("analyzer.ocr")

try:
    import pytesseract
except ImportError:
    pytesseract = None

class OCRProcessor:
    def __init__(self):
        if pytesseract is None:
            logger.warning("pytesseract not found. OCR will be disabled.")
        
    def extract_text(self, image_path):
        if pytesseract is None:
            return ""
            
        try:
            image = cv2.imread(image_path)
            # Basic preprocessing: grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # OCR
            text = pytesseract.image_to_string(gray)
            return text.strip()
        except Exception as e:
            logger.error(f"OCR failed for {image_path}: {e}")
            return ""
