import logging
import json
from string import Template
from .llm import LLMProcessor

logger = logging.getLogger("analyzer.animation_engine")

class AnimationEngine:
    def __init__(self, llm_processor: LLMProcessor):
        self.llm = llm_processor

    def generate_animation(self, context_summary, transcript_chunk):
        """Generates a sequential CSS/SVG animation based on a process description."""
        
        prompt_tpl = Template("""
        You are an expert SVG and CSS animator. Analyze the transcript chunk and explain the physical or logical process occurring.
        
        CONTEXT:
        $context
        
        TRANSCRIPT:
        $transcript
        
        STRICT RULES:
        1. Generate an inline <svg> with a viewBox="0 0 800 400".
        2. Use our sketchy, hand-drawn aesthetic (black strokes, no fill for outlines, stroke-width="2").
        3. Include a <style> block inside the SVG. Use CSS @keyframes to animate the elements.
        4. Use sequential animation-delay properties so the steps happen one after another.
        5. The total animation loop should last between 5 to 10 seconds.
        6. Include <text> elements that act as labels, fading in when the relevant part of the animation occurs.
        7. DO NOT use external libraries like GSAP or React.
        8. The SVG must be self-contained.
        
        INSTRUCTIONS:
        - Break down the process (e.g., 'data flowing through a pipe', 'molecule entering a cell') into 3-5 sequential steps.
        - Elements should fade in (opacity), move (transform: translate), or change color to explain the mechanism.
        
        REQUIRED OUTPUT FORMAT (JSON):
        {
            "svg_code": "<svg ...><style>...</style>...</svg>",
            "explanation": "Step-by-step breakdown of what the animation shows"
        }
        """)
        
        prompt = prompt_tpl.substitute(
            context=context_summary,
            transcript=transcript_chunk
        )
        
        try:
            logger.info("Generating CSS/SVG animation...")
            res = self.llm.generate_text(prompt)
            svg_code = res.get("svg_code", "")
            explanation = res.get("explanation", "")
            
            if "<svg" in svg_code and "<style" in svg_code:
                return {
                    "svg_code": svg_code,
                    "explanation": explanation
                }
            else:
                logger.warning("Generated animation was incomplete (missing SVG or Style tags).")
                return None
        except Exception as e:
            logger.error(f"Animation generation failed: {e}")
            return None
