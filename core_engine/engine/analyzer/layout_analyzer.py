import cv2
import os
import numpy as np
from ..logger import get_logger

logger = get_logger("analyzer.layout")

class LayoutAnalyzer:
    def __init__(self, output_dir="screenshots"):
        self.output_dir = output_dir

    def detect_and_crop(self, image_path, base_name):
        """
        Fallback Layout Analysis using OpenCV Contours.
        Detects large blocks that are likely figures or charts.
        Returns a list of visual elements with their cropped asset paths.
        """
        visual_elements = []
        if not os.path.exists(image_path):
            return visual_elements

        img = cv2.imread(image_path)
        if img is None:
            return visual_elements

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Adaptive thresholding to handle different lighting
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Morphological operations to group nearby pixels into solid blocks
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        dilated = cv2.dilate(thresh, kernel, iterations=2)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        img_h, img_w = img.shape[:2]
        min_area = (img_w * img_h) * 0.05 # At least 5% of the image
        max_area = (img_w * img_h) * 0.85 # At most 85% of the image
        
        crop_count = 0
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if min_area < area < max_area:
                x, y, w, h = cv2.boundingRect(cnt)
                
                # Filter out likely text lines (very wide and short)
                aspect_ratio = w / float(h)
                if aspect_ratio > 10.0:
                    continue
                    
                crop_img = img[y:y+h, x:x+w]
                crop_filename = f"{base_name}_crop_{crop_count}.jpg"
                crop_path = os.path.join(self.output_dir, crop_filename)
                
                cv2.imwrite(crop_path, crop_img)
                
                # Heuristically classify as diagram
                visual_elements.append({
                    "type": "diagram",
                    "asset_path": crop_path,
                    "caption": "" # To be filled by LLM
                })
                crop_count += 1
                
        # If no specific figures found, consider the whole frame as a diagram to prevent missing data
        if not visual_elements:
             # We won't crop the whole image, just pass the original image path
             visual_elements.append({
                 "type": "diagram",
                 "asset_path": image_path,
                 "caption": ""
             })
             
        return visual_elements
