import re
import logging
from string import Template

logger = logging.getLogger("analyzer.animation_engine")

# ---------------------------------------------------------------------------
# The canonical system prompt for the offline LLM SVG animator.
# Uses string.Template so the pipeline can safely inject transcript text via
# safe_substitute() — preventing crashes on '$' signs in transcript content.
# ---------------------------------------------------------------------------
ANIMATION_SYSTEM_PROMPT = Template(
    "You are an expert SVG and CSS animator. "
    "Analyze the transcript chunk and explain the physical or logical process occurring.\n\n"
    "Generate an inline <svg> with a viewBox=\"0 0 800 400\". "
    "Use a sketchy, hand-drawn aesthetic (black strokes, no fill for outlines, stroke-width=\"2\").\n"
    "Include a <style> block inside the SVG using CSS @keyframes. "
    "Use sequential animation-delay properties so the steps happen one after another.\n\n"
    "CRITICAL SPATIAL LAYOUT:\n"
    "- Draw a starting element on the left (x=100).\n"
    "- Draw a processing element in the center (x=400).\n"
    "- Draw an ending element on the right (x=700).\n"
    "- Connect them with a <line> or <polygon> (arrow).\n\n"
    "STRICT RULES FOR BASIC MODELS:\n"
    "1. Use ONLY basic shapes: <rect>, <circle>, <line>, <text>.\n"
    "2. Do NOT use complex <path> data.\n"
    "3. Keep it to MAX 3 visual elements to ensure valid syntax.\n\n"
    "Transcript Chunk:\n"
    "$transcript\n\n"
    "Return ONLY the raw SVG code starting with <svg> and ending with </svg>. "
    "No markdown formatting or explanation."
)

# Keywords that indicate a mechanistic/process-driven transcript segment.
# Mirrors the ContextMapper.detect_mechanism() spec from the design document.
_MECHANISM_KEYWORDS = [
    "how", "process", "mechanism", "entering", "exiting",
    "flow", "step", "works", "cycle", "algorithm", "path", "logic",
]


class ContextMapper:
    """
    Lightweight, keyword-based mechanism detector.

    Runs entirely offline with zero LLM calls — it gates the expensive
    AnimationEngine so SVGs are only generated for mechanistic/process chunks.

    Note: The heavy ContextMapper in context_mapper.py handles the global
    knowledge map (full-transcript, LLM-based). This class is a fast, local
    per-chunk trigger check only.
    """

    def detect_mechanism(self, transcript_chunk: str) -> bool:
        """
        Returns True if the transcript chunk appears to describe a physical
        or logical mechanism that warrants an animated SVG explainer.

        Args:
            transcript_chunk: The raw text of a single scene/transcript segment.

        Returns:
            bool: True if an animation should be generated for this chunk.
        """
        lowered = transcript_chunk.lower()
        return any(kw in lowered for kw in _MECHANISM_KEYWORDS)


class AnimationEngine:
    """
    Calls the offline LLM to generate a CSS-animated SVG explainer for a
    transcript chunk that describes a physical or logical mechanism.

    Integration point
    -----------------
    The converter (converter.py) owns the trigger logic and calls this engine:

        mapper  = ContextMapper()
        engine  = AnimationEngine(llm_processor)

        if mapper.detect_mechanism(transcript_chunk):
            svg = engine.generate_explainer(transcript_chunk, global_context)
            if svg:
                visual_elements.append({"type": "animated_explainer", "svg_code": svg})

    The generated SVG is stored in the knowledge base and rendered by
    HTMLGenerator as an .animated-explainer-box with a Replay button.
    """

    def __init__(self, llm_processor):
        """
        Args:
            llm_processor: An instance of LLMProcessor (from analyzer/llm.py).
                           Must expose .generate_text_raw(prompt) -> str.
        """
        self.llm = llm_processor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_explainer(self, transcript_chunk: str, global_context=None) -> str:
        """
        Generates and returns a raw <svg>...</svg> string for the given
        transcript chunk.

        Args:
            transcript_chunk: Text describing the process to animate.
            global_context:   Optional dict from the global context map.
                              If provided, the core thesis is prepended to
                              give the LLM richer context without changing
                              the SVG-only output contract.

        Returns:
            str: Raw SVG markup, or "" on failure.
        """
        logger.info("AnimationEngine: generating CSS-animated SVG explainer...")

        # Optionally enrich with the global core thesis so the LLM has
        # topic-level context even though we only ask for SVG output.
        preamble = ""
        if global_context and isinstance(global_context, dict):
            thesis = global_context.get("core_thesis", "")
            if thesis:
                preamble = f"[Video Topic: {thesis}]\n\n"

        enriched_chunk = preamble + transcript_chunk

        # safe_substitute() won't crash if the transcript contains '$' signs.
        prompt = ANIMATION_SYSTEM_PROMPT.safe_substitute(transcript=enriched_chunk)

        try:
            # generate_text_raw() skips format='json' so angle brackets in
            # SVG are never escaped by Ollama's JSON serialiser.
            raw = self.llm.generate_text_raw(prompt)
            return self._sanitize_svg(raw)
        except Exception as e:
            logger.error(f"AnimationEngine: generation failed — {e}")
            return ""

    # Legacy alias — keeps the existing converter.py call working unchanged
    # while the new integration path uses generate_explainer().
    def generate_animation(self, transcript_chunk: str, global_context=None) -> str:
        """Backward-compatible alias for generate_explainer()."""
        return self.generate_explainer(transcript_chunk, global_context)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_svg(raw: str) -> str:
        """
        Strips markdown code fences and extracts the first valid <svg>…</svg>
        block from the model's raw output.

        The model may wrap its output in ```svg … ``` or ```html … ```.
        This strips those fences and returns only the SVG element.
        """
        if not raw:
            return ""

        # Strip common code-fence wrappers
        for fence in ("```svg", "```html", "```xml", "```"):
            raw = raw.replace(fence, "")
        raw = raw.strip()

        # Extract the first <svg … </svg> block (case-insensitive)
        match = re.search(r"(<svg[\s\S]*?</svg>)", raw, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # If no SVG tag found but the output starts with '<svg', return as-is
        if raw.lower().startswith("<svg"):
            return raw

        logger.warning("AnimationEngine._sanitize_svg: no <svg> block found in LLM output.")
        return ""
