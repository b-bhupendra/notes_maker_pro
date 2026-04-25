import json
import logging
import os
from .llm import LLMProcessor

logger = logging.getLogger("analyzer.diagram_engine")

class DiagramEngine:
    def __init__(self, llm_processor=None):
        self.llm = llm_processor or LLMProcessor()

    def generate_holistic_diagrams(self, global_context):
        """
        Uses the global context to generate complex Python scripts for E2B diagrams.
        These diagrams represent the lifecycle of concepts across the entire video.
        """
        logger.info("Generating Holistic E2B Diagrams...")
        
        knowledge_graph = global_context.get("knowledge_graph", [])
        core_thesis = global_context.get("core_thesis", "")
        
        prompt = f"""
        You are a Data Visualization Expert. Based on the Global Context of this video, generate a Python script (compatible with E2B or standard Matplotlib/NetworkX) that visualizes the 'Entire Concept Lifecycle'.
        
        CORE THESIS: {core_thesis}
        KNOWLEDGE GRAPH: {json.dumps(knowledge_graph)}
        
        TASK:
        Write a Python script that:
        1. Uses Matplotlib or NetworkX to draw a professional, textbook-style diagram.
        2. Illustrates how concepts evolve from start to finish.
        3. Saves the output as 'concept_lifecycle.png'.
        
        Return ONLY the Python code in a code block.
        """
        
        # We use a text-only call to get the Python script
        python_script = self.llm.generate_text(prompt)
        # Handle if LLM returns JSON
        if isinstance(python_script, dict):
            python_script = python_script.get("code", "")
            
        return {
            "type": "e2b_diagram",
            "python_script": python_script,
            "description": "A holistic visualization of the entire knowledge lifecycle mapped from the video."
        }
