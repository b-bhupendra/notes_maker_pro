import ollama
import json
import logging
import time

logger = logging.getLogger("analyzer.llm")

class LLMProcessor:
    def __init__(self, model="llava:latest", base_url="http://localhost:11434"):
        self.model = model
        self.client = ollama.Client(host=base_url)

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
        """Hyper-aggressive JSON cleaner for small/basic LLM output."""
        if isinstance(text, dict): return text
        import re
        text = text.strip()

        # Step 1: Strip markdown code fences (handles ```json ... ``` and ``` ... ```)
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
        text = text.strip()

        # Step 2: Try standard parse first (fast path)
        try:
            return json.loads(text)
        except Exception:
            pass

        # Step 3: Greedy extraction — grab from first '{' to LAST '}'
        # This strips any conversational prefix/suffix the model appended.
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            candidate = match.group()
            try:
                return json.loads(candidate)
            except Exception:
                pass

        # Step 4: Nuclear fallback — safe eval (no builtins) for Python-style dicts
        try:
            import ast
            result = ast.literal_eval(text)
            if isinstance(result, dict):
                return result
        except Exception:
            pass

        # Step 5: Return empty dict instead of crashing the thread
        logger.warning("_clean_json: All parsing strategies failed. Returning empty dict.")
        return {}

    def generate_text(self, prompt, retries=3):
        """Standard text generation without images."""
        logger.info(f"Generating text for prompt (length: {len(prompt)})")
        
        for attempt in range(retries):
            try:
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    format='json',
                    options={'temperature': 0.1},
                    keep_alive=0
                )
                
                raw_response = response.get("response", "{}")
                return self._clean_json(raw_response)
            except Exception as e:
                logger.warning(f"Text Generation Attempt {attempt+1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(2)
        
        return {}

    def analyze_scene(self, visual_elements, ocr_text, transcript_text, global_context=None, retries=3):
        image_bytes_list = []
        for el in visual_elements:
            img_b64 = self._encode_image(el['asset_path'])
            if img_b64:
                image_bytes_list.append(img_b64)
        
        logger.info(f"Analyzing scene with {len(image_bytes_list)} images and {len(transcript_text)} chars of transcript.")

        from string import Template
        
        global_context_str = json.dumps(global_context, indent=2) if global_context else "No global context available."

        prompt_tpl = Template("""
        You are drafting a section of high-fidelity visual notes. 
        
        GLOBAL CONTEXT (The 'Total Knowledge' of the video):
        $global_context
        
        LOCAL SCENE DATA:
        VISUAL TEXT: $ocr_text
        AUDIO TRANSCRIPT: $transcript_text
        
        INSTRUCTIONS:
        1. Process this local scene while ensuring it aligns with the GLOBAL CORE THESIS.
        2. Reference terms from the GLOBAL GLOSSARY where applicable.
        3. If EXTENDED RESEARCH is available in the global context, inject relevant facts into this section.
        4. If this scene relates to a future concept mapped in the GLOBAL TIMELINE, add a 'Foreshadowing' note.
        5. PRESERVE ALL TECHNICAL KNOWLEDGE.
        
        ANTI-HALLUCINATION RULES:
        - Do NOT use generic phrases like 'In this section, we see a deep dive...'. 
        - Write direct, factual bullet points based ONLY on the provided transcript and image.
        - For Mermaid: Analyze the provided image and transcript. YOU MUST map the EXACT entities shown in the image. DO NOT output generic placeholders like 'A --> B'. If there is no flowchart in the image, return an empty string for 'mermaid_code'.
        - If no diagram is warranted, return an empty array for 'visual_elements'.

        REQUIRED OUTPUT FORMAT (JSON):
        {
            "key_concepts": ["Concept 1", "Concept 2"],
            "detailed_explanations": "Full markdown explanation.",
            "definitions": [{"term": "X", "definition": "Y"}],
            "visual_elements": [
                {
                    "type": "diagram",
                    "mermaid_code": "graph LR\\nA-->B",
                    "caption": "Hand-drawn style diagram"
                }
            ],
            "summary": "Brief summary.",
            "research_notes": "Extra context from external research.",
            "foreshadowing": "Notes on how this connects to later parts of the video."
        }
        
        Return ONLY the JSON object.
        """)
        
        # Fix 1: safe_substitute prevents crashes when transcript/OCR contains '$' signs
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
                    keep_alive=0 # Force unload after each call to save VRAM
                )
                
                raw_response = response.get("response", "{}")
                logger.debug(f"Raw LLM Response: {raw_response[:500]}...")
                parsed = self._clean_json(raw_response)
                
                if not parsed.get("detailed_explanations") and not parsed.get("summary"):
                    logger.warning("LLM returned empty content. Retrying...")
                    continue
                    
                return parsed
            except Exception as e:
                error_msg = str(e).lower()
                # Memory issues often manifest as "memory", "resource limitations", or "failed to load"
                is_resource_error = any(kw in error_msg for kw in ["memory", "resource", "failed to load"])
                
                if is_resource_error and image_bytes_list:
                    logger.warning(f"Resource pressure detected ({error_msg}). Falling back to text-only analysis...")
                    # Retry without images, but keep the OCR text as context
                    image_bytes_list = []
                    continue
                
                logger.warning(f"LLM Attempt {attempt+1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    time.sleep(5)
                else:
                    logger.error(f"LLM Analysis failed after {retries} attempts.")
        
        return {
            "key_concepts": [],
            "detailed_explanations": "Analysis unavailable.",
            "definitions": [],
            "visual_elements": [],
            "summary": "Analysis failed."
        }
