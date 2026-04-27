import ollama
import json
import logging
import time

logger = logging.getLogger("analyzer.llm")

class LLMProcessor:
    def __init__(self, model="llava:latest", base_url="http://localhost:11434"):
        self.model = model
        self.client = ollama.Client(host=base_url)

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
        logger.info(f"Generating text for prompt (length: {len(prompt)})")
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
        logger.info(f"Generating raw text for prompt (length: {len(prompt)})")
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

    def analyze_scene(self, visual_elements, ocr_text, transcript_text, global_context=None, retries=3):
        image_bytes_list = []
        for el in visual_elements:
            img_b64 = self._encode_image(el['asset_path'])
            if img_b64: image_bytes_list.append(img_b64)
        
        from string import Template
        global_context_str = json.dumps(global_context, indent=2) if global_context else "No global context available."

        prompt_tpl = Template("""
        You are a highly structured technical knowledge synthesizer.
        
        GLOBAL CONTEXT:
        $global_context
        
        LOCAL SCENE DATA:
        VISUAL TEXT (OCR): $ocr_text
        AUDIO TRANSCRIPT: $transcript_text
        
        TASK:
        Synthesize a cohesive, textbook-quality technical explanation of this scene. 
        Focus on flow and information density. Do not use conversational filler.
        
        REQUIRED OUTPUT FORMAT (JSON):
        {
            "core_assertion": "One single sentence stating the primary fact/thesis of this scene.",
            "technical_narrative": "A cohesive markdown-formatted explanation (2-3 paragraphs) that synthesizes visual and audio data into a smooth narrative. Use bold for key terms.",
            "definitions": [
                {"term": "Keyword", "definition": "Clinical technical definition"}
            ],
            "visual_elements": [
                {
                    "type": "diagram",
                    "mermaid_code": "graph TD\\n...orthogonal flowchart code here..."
                }
            ]
        }
        
        Return ONLY the JSON object.
        """)
        
        prompt = prompt_tpl.safe_substitute(
            global_context=global_context_str,
            ocr_text=str(ocr_text),
            transcript_text=str(transcript_text)
        )
        
        for attempt in range(retries):
            try:
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    images=image_bytes_list if image_bytes_list else None,
                    format='json',
                    options={'temperature': 0.1},
                    keep_alive='5m'
                )
                
                raw_response = response.get("response", "{}")
                parsed = self._clean_json(raw_response)
                
                if not parsed.get("technical_narrative") and not parsed.get("core_assertion"):
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
            "core_assertion": "Analysis failed.",
            "technical_narrative": "Detailed synthesis unavailable due to engine error.",
            "definitions": [],
            "visual_elements": []
        }
