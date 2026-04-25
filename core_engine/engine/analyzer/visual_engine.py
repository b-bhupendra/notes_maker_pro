import json
import logging
import re
from string import Template

logger = logging.getLogger("analyzer.visual")

class VisualEngine:
    """
    Handles generation and validation of structural diagrams (Mermaid) 
    and visual metaphors (SVG).
    """
    def __init__(self, llm_processor):
        self.llm = llm_processor

    def generate_mermaid_flowchart(self, context_summary, retries=2):
        """Generates a strictly formatted Mermaid.js flowchart."""
        prompt_tpl = Template("""
        You are a Data Visualization Expert. Generate a structural Mermaid.js flowchart for the following context:
        
        CONTEXT:
        $context
        
        INSTRUCTIONS:
        1. Output STRICT Mermaid.js syntax.
        2. Use ONLY 'graph LR' or 'graph TD'.
        3. No HTML tags inside nodes.
        
        STRICT RULES FOR BASIC MODELS:
        - Use VERY SIMPLE shapes and labels only.
        - Limit to MAX 3 nodes total. Do NOT add more.
        - Analyze the context. YOU MUST map the EXACT entities mentioned.
        - DO NOT output generic placeholders like 'A[Start] --> B[Process]'.
        - If the context doesn't describe a clear process or structure, return an empty string.
        - If there is no flowchart logic in the input, return "".
        """)
        
        # Fix 1: safe_substitute prevents crash if context contains '$' signs
        prompt = prompt_tpl.safe_substitute(context=context_summary)
        
        for attempt in range(retries + 1):
            try:
                json_prompt_tpl = Template("""
                You are a Data Visualization Expert. Generate a structural Mermaid.js flowchart for the following context.
                
                CONTEXT:
                $context
                
                STRICT RULES FOR BASIC MODELS:
                - Use VERY SIMPLE shapes. Limit to MAX 3 nodes. Do NOT add more nodes.
                - YOU MUST map EXACT entities from the context. No 'A', 'B', 'Start', 'Process' unless they appear verbatim in the text.
                - If no flowchart logic is found, return empty mermaid_code.
                
                REQUIRED OUTPUT FORMAT (JSON):
                {
                    "mermaid_code": "graph LR\\nEntity1-->Entity2",
                    "explanation": "Brief explanation"
                }
                """)
                
                # Fix 1: safe_substitute prevents crash if context contains '$' signs
                res = self.llm.generate_text(json_prompt_tpl.safe_substitute(context=context_summary))
                code = res.get("mermaid_code", "")
                
                if code and self._validate_mermaid(code):
                    return code
                elif not code:
                    return ""
                else:
                    logger.warning(f"Mermaid validation failed on attempt {attempt+1}")
            except Exception as e:
                logger.error(f"Mermaid generation failed: {e}")
                
        return ""

    def generate_svg_illustration(self, context_summary):
        """Generates a simple, sketchy inline SVG illustration."""
        prompt_tpl = Template("""
        You are a Visual Metaphor Designer. Generate a raw inline SVG for the following concept:
        
        CONCEPT:
        $context
        
        STRICT RULES FOR BASIC MODELS:
        - Use VERY SIMPLE shapes ONLY: <rect>, <circle>, <line>, <text>.
        - Do NOT use complex <path> data (e.g. 'd=' attributes with curves). Use rectangles and circles instead.
        - Generate a meaningful visual metaphor based ONLY on the concept.
        - No generic circles unless the concept is 'Circle' or 'Loop'.
        - If the concept is too abstract for a simple SVG, return an empty svg_code.
        
        INSTRUCTIONS:
        1. Use raw inline <svg> code.
        2. Use attributes: stroke="currentColor", stroke-width="2", fill="none".
        3. The SVG must be responsive (viewBox).
        
        REQUIRED OUTPUT FORMAT (JSON):
        {
            "svg_code": "<svg ...>...</svg>",
            "metaphor_explanation": "What this represents"
        }
        """)
        
        try:
            # Fix 1: safe_substitute prevents crash if context contains '$' signs
            res = self.llm.generate_text(prompt_tpl.safe_substitute(context=context_summary))
            return res.get("svg_code", "")
        except Exception as e:
            logger.error(f"SVG generation failed: {e}")
            return ""

    def _validate_mermaid(self, code):
        """Basic syntax validation for Mermaid."""
        if not code: return False
        valid_starts = ('graph LR', 'graph TD', 'flowchart LR', 'flowchart TD')
        if not any(code.strip().startswith(s) for s in valid_starts):
            return False
        # Check for balanced brackets/quotes could go here
        if "<html>" in code.lower() or "<div" in code.lower():
            return False
        return True
