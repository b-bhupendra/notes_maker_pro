import ollama
import json
import logging
import time

logger = logging.getLogger("analyzer.llm")

class LLMProcessor:
    def __init__(self, model="llava:latest", base_url="http://localhost:11434"):
        self.model = model
        # Explicitly enforce a 5-minute timeout on the client socket
        import httpx
        custom_client = httpx.Client(timeout=300.0) 
        self.client = ollama.Client(host=base_url, client=custom_client)

    def unload_model(self):
        """Explicitly unloads the model from VRAM."""
        try:
            logger.info(f"Explicitly unloading model {self.model} from VRAM...")
            self.client.generate(model=self.model, prompt="", keep_alive=0)
        except Exception as e:
            logger.warning(f"Failed to unload model: {e}")

    def _encode_image(self, image_path):
        import base64
        from PIL import Image
        import io
        try:
            with Image.open(image_path) as img:
                if img.width > 800:
                    ratio = 800 / float(img.width)
                    height = int(float(img.height) * ratio)
                    img = img.resize((800, height), Image.Resampling.LANCZOS)
                
                img_byte_arr = io.BytesIO()
                img.convert("RGB").save(img_byte_arr, format='JPEG', quality=70)
                return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encode/resize image {image_path}: {e}")
            return None

    def _clean_json(self, text):
        if isinstance(text, dict): return text
        import re
        text = text.strip()
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            candidate = match.group()
            try:
                return json.loads(candidate)
            except Exception:
                pass
        return {}

    def generate_text(self, prompt, retries=3):
        for attempt in range(retries):
            try:
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    format='json',
                    options={'temperature': 0.1},
                    keep_alive='5m'
                )
                raw_response = response.get("response", "{}")
                return self._clean_json(raw_response)
            except Exception as e:
                logger.warning(f"Text Generation Attempt {attempt+1}/{retries} failed: {e}")
                if attempt < retries - 1: time.sleep(2)
        return {}

    def generate_text_raw(self, prompt, retries=3):
        for attempt in range(retries):
            try:
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    options={'temperature': 0.3},
                    keep_alive='5m'
                )
                raw = response.get("response", "").strip()
                if raw: return raw
            except Exception as e:
                logger.warning(f"Raw Text Generation Attempt {attempt+1}/{retries} failed: {e}")
                if attempt < retries - 1: time.sleep(2)
        return ""

    def analyze_scene(self, ocr_text, transcript_text, global_context=None, visual_assets=None, retries=2):
        """
        Synthesizes raw video data into an Expert Educational Knowledge Block.
        """
        image_bytes_list = []
        if visual_assets:
            for el in visual_assets:
                img_b64 = self._encode_image(el['asset_path'])
                if img_b64: image_bytes_list.append(img_b64)
        
        global_context_str = json.dumps(global_context, indent=2) if global_context else "No global context available."

        prompt = f"""
        SYSTEM: You are an Expert Technical Educator. Your goal is to transform video raw data into high-fidelity, hygienic study material.
        
        GLOBAL CONTEXT:
        {global_context_str}
        
        LOCAL SCENE DATA:
        VISUAL TEXT (OCR): {ocr_text}
        AUDIO TRANSCRIPT: {transcript_text}
        
        STRICT RULES:
        1. The AUDIO TRANSCRIPT is the absolute source of truth. Ignore OCR noise if it contradicts the audio.
        2. DO NOT hallucinate. Every fact must be verifiable by a source quote.
        3. Persona: Professional, dense, clinical, and pedagogical.
        
        REQUIRED JSON OUTPUT SCHEMA:
        {{
            "scene_title": "A crisp, technical heading (4-7 words)",
            "educational_narrative": "A 2-3 paragraph explanation in beautiful Markdown. Connect audio concepts with visual evidence. Flow like a high-end textbook.",
            "extracted_facts": [
                {{"fact": "Technical statement", "source_quote": "Exact substring from audio transcript proving this"}},
                ...
            ],
            "mermaid_code": "A technical Mermaid.js diagram representing the process.",
            "flashcards": [
                {{"term": "Key term", "definition": "Clinical definition"}},
                ...
            ],
            "quiz": {{
                "question": "A challenging technical question",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "A",
                "explanation": "Technical justification for the answer"
            }}
        }}

        Output ONLY valid JSON.
        """
        
        for attempt in range(retries):
            try:
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    images=image_bytes_list if image_bytes_list else None,
                    format='json',
                    options={'temperature': 0.0},
                    keep_alive='5m'
                )
                
                raw_response = response.get("response", "{}")
                parsed = self._clean_json(raw_response)
                
                if not parsed.get("educational_narrative") and not parsed.get("scene_title"):
                    logger.warning("LLM returned empty content. Retrying...")
                    continue
                    
                return parsed
            except Exception as e:
                error_msg = str(e).lower()
                if any(kw in error_msg for kw in ["memory", "resource", "failed to load"]) and image_bytes_list:
                    logger.warning("Resource pressure. Retrying without images...")
                    image_bytes_list = []
                    continue
                
                logger.warning(f"LLM Attempt {attempt+1}/{retries} failed: {e}")
                if attempt < retries - 1: time.sleep(5)
        
        return {
            "scene_title": "Analysis failed.",
            "educational_narrative": "Detailed synthesis unavailable due to engine error.",
            "extracted_facts": [],
            "flashcards": [],
            "quiz": None
        }
