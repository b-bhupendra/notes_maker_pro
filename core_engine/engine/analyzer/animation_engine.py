import logging
from string import Template
from .llm import LLMProcessor

logger = logging.getLogger("analyzer.animator")

class AnimationEngine:
    def __init__(self, llm_processor):
        self.llm = llm_processor

    def generate_animation(self, transcript_chunk, global_context):
        logger.info("Generating CSS-animated SVG Explainer...")
        prompt_tpl = Template("""
        You are an expert SVG and CSS animator.
        
        CONTEXT: $context
        TRANSCRIPT: $transcript
        
        TASK:
        Generate an animated 'How It Works' visual explainer.
        
        STRICT RULES FOR BASIC MODELS:
        1. Output an inline <svg> with viewBox="0 0 800 400".
        2. Include a <style> block INSIDE the SVG using CSS @keyframes to animate elements sequentially (animation-delay).
        3. Do NOT use complex SVG <path> data (no 'd=' attributes with curves or arc commands).
           Use ONLY basic shapes: <rect>, <circle>, <line>, <text>.
        4. Limit the animation to MAX 3 steps total. Do NOT exceed this.
        5. Add <text> labels that fade in.
        6. Use black strokes and no fill for a sketchy aesthetic.
        
        REQUIRED FORMAT (JSON):
        {
            "animated_svg": "<svg>...</svg>",
            "explanation": "Brief description of the max-3-step animation."
        }
        """)
        
        try:
            # Fix 1: safe_substitute prevents crash if transcript/context contains '$' signs
            res = self.llm.generate_text(prompt_tpl.safe_substitute(
                context=str(global_context.get("core_thesis") if global_context else ""), 
                transcript=transcript_chunk
            ))
            # Handle potential dictionary response or stringified JSON
            if isinstance(res, str):
                import json
                res = json.loads(res)
                
            return res.get("animated_svg", "")
        except Exception as e:
            logger.error(f"Animation generation failed: {e}")
            return ""
