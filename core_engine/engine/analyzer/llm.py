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

    def _clean_json(self, text):
        import re
        text = text.strip()
        # Remove markdown fences if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        return json.loads(text)

    def analyze_moment(self, image_path, ocr_text, transcript_text, retries=3):
        base64_image = self._encode_image(image_path)
        
        prompt = f"""
        Analyze the attached frame from an educational video alongside the provided text.
        
        VISUAL TEXT (OCR): {ocr_text}
        AUDIO TRANSCRIPT: {transcript_text}
        
        Your task is to extract all possible knowledge from this frame and categorize it into the following structured format. Use rich Markdown (callouts, bolding, bullet points) inside the text values.
        
        Format your response strictly as a JSON object with the following keys:
        - "key_concepts": A list of short strings representing the main ideas.
        - "detailed_explanations": A detailed Markdown formatted explanation of the topic.
        - "definitions": A list of objects, each with a "term" and "definition".
        - "flowcharts_illustrations": If a diagram, flowchart, or visual relationship is shown, provide the Mermaid.js code block (starting with ```mermaid) to recreate it as a sketch. If none, leave empty.
        - "summary": A brief 1-2 sentence summary of the moment.
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
                    timeout=180
                )
                response.raise_for_status()
                result = response.json()
                raw_response = result.get("response", "{}")
                return self._clean_json(raw_response)
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
