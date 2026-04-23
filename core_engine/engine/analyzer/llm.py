import requests
import json
import logging
import time

logger = logging.getLogger("analyzer.llm")

class LLMProcessor:
    def __init__(self, model="gemma4:e2b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def _encode_image(self, image_path):
        import base64
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            return None

    def analyze_moment(self, image_path, ocr_text, transcript_text, retries=3):
        base64_image = self._encode_image(image_path)
        
        prompt = f"""
        Analyze the attached frame from an educational video alongside the provided text.
        
        VISUAL TEXT (OCR): {ocr_text}
        AUDIO TRANSCRIPT: {transcript_text}
        
        Your task is to extract all possible knowledge from this frame using both the image and the text:
        1. **Data Tables**: If a table is visible in the image, convert it to Markdown format.
        2. **Graphs/Diagrams**: Describe any charts, flowcharts, or diagrams shown in the image in detail.
        3. **Visual Description**: A comprehensive description of the slide/scene layout and visuals.
        4. **Key Takeaways**: Strategic points mentioned or shown.
        
        Format your response as a JSON object with keys:
        "total_description", "key_takeaways", "structured_data" (include markdown tables or diagram descriptions here).
        """
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        if base64_image:
            payload["images"] = [base64_image]
        
        for attempt in range(retries):
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=180 # Increased timeout for stable vision processing
                )
                response.raise_for_status()
                result = response.json()
                return json.loads(result.get("response", "{}"))
            except Exception as e:
                logger.warning(f"LLM Attempt {attempt+1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(5) # Wait before retry
                else:
                    logger.error(f"LLM Analysis failed after {retries} attempts.")
        
        return {
            "total_description": "Analysis unavailable.",
            "key_takeaways": [],
            "structured_data": ""
        }
