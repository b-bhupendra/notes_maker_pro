import cv2
import logging
import os

logger = logging.getLogger("analyzer.ocr")

try:
    import easyocr
    import torch
except ImportError:
    easyocr = None
    torch = None

class OCRProcessor:
    _reader = None

    def __init__(self):
        if easyocr is None:
            logger.warning("easyocr not found. OCR will be disabled.")
            return
        
        if OCRProcessor._reader is None:
            use_gpu = torch.cuda.is_available() if torch else False
            logger.info(f"Initializing EasyOCR (GPU={use_gpu})...")
            # Using 'en' for English. Add other languages if needed.
            OCRProcessor._reader = easyocr.Reader(['en'], gpu=use_gpu)
        
    def extract_text(self, image_path):
        if OCRProcessor._reader is None:
            return ""
            
        try:
            # EasyOCR can take image path directly
            results = OCRProcessor._reader.readtext(image_path, detail=0)
            return " ".join(results).strip()
        except Exception as e:
            logger.error(f"OCR failed for {image_path}: {e}")
            return ""
