import json
import logging
import os
from .llm import LLMProcessor

logger = logging.getLogger("analyzer.context_mapper")

class ContextMapper:
    def __init__(self, llm_processor=None):
        self.llm = llm_processor or LLMProcessor()

    def generate_global_context(self, full_transcript, ocr_texts, output_path=None):
        """
        Processes the entire transcript and OCR data to create a bird's-eye view of the video.
        """
        logger.info("Generating Global Context Map...")
        
        # Prepare the combined text data
        combined_ocr = " ".join(set(ocr_texts)) # Unique OCR snippets
        
        from string import Template
        
        prompt_tpl = Template("""
        You are a Master Researcher. Analyze the entire transcript and visual text of a video to create a 'Total Knowledge Map'.
        
        FULL TRANSCRIPT:
        $transcript
        
        VISUAL TEXT SNIPPETS:
        $ocr
        
        TASK:
        Generate a comprehensive Global Context JSON that acts as the 'brain' for a note-generation pipeline.
        
        REQUIRED JSON STRUCTURE:
        {
            "core_thesis": "The central message or goal of the video.",
            "glossary": [
                { "term": "Term Name", "definition": "Deep technical definition.", "significance": "Why this matters." }
            ],
            "knowledge_graph": [
                { "source": "Concept A", "target": "Concept B", "relation": "How they are linked." }
            ],
            "timeline_roadmap": [
                { "timestamp": "MM:SS", "milestone": "Critical revelation or concept introduced." }
            ],
            "research_gaps": [
                "Specific complex theory that needs more real-world examples",
                "Technical term that needs external documentation"
            ]
        }
        
        INSTRUCTIONS:
        1. Identify the core thesis.
        2. Create a glossary of every major term.
        3. Map how concepts at the beginning relate to those at the end (foreshadowing/linking).
        4. Identify areas where the video is 'thin' or 'complex' and needs external research.
        5. Return ONLY the JSON object.
        """)
        
        prompt = prompt_tpl.substitute(
            transcript=full_transcript[:15000],
            ocr=combined_ocr[:5000]
        )
        
        try:
            # We use a non-vision model call or just the text-based call
            # Assuming LLMProcessor has a map_context method or similar
            global_context = self.llm.generate_text(prompt)
            
            if output_path:
                with open(output_path, "w") as f:
                    json.dump(global_context, f, indent=4)
                logger.info(f"Global Context saved to {output_path}")
            
            return global_context
        except Exception as e:
            logger.error(f"Failed to generate global context: {e}")
            return {
                "core_thesis": "Unable to map context.",
                "glossary": [],
                "knowledge_graph": [],
                "timeline_roadmap": [],
                "research_gaps": ["Error during mapping phase"]
            }
