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
            logger.info("Initializing EasyOCR (CPU mode to save VRAM)...")
            OCRProcessor._reader = easyocr.Reader(['en'], gpu=False)
        
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
