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
        
        STRICT RULES:
        1. Output an inline <svg> with viewBox="0 0 800 400".
        2. Include a <style> block INSIDE the SVG using CSS @keyframes to animate the elements sequentially (using animation-delay).
        3. Use basic shapes (<rect>, <circle>, <path>, <g>) and black strokes/no fill for a sketchy aesthetic.
        4. Add <text> labels that fade in.
        
        REQUIRED FORMAT (JSON):
        {
            "animated_svg": "<svg>...</svg>",
            "explanation": "Brief description of the animation steps."
        }
        """)
        
        try:
            res = self.llm.generate_text(prompt_tpl.substitute(
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
