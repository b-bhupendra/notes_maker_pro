import json
import logging
import os
from .llm import LLMProcessor

logger = logging.getLogger("analyzer.diagram_engine")

class DiagramEngine:
    def __init__(self, llm_processor=None):
        self.llm = llm_processor or LLMProcessor()

    def generate_holistic_diagrams(self, global_context):
        logger.info("Generating Holistic Mermaid Mindmap...")
        
        knowledge_graph = global_context.get("knowledge_graph", [])
        core_thesis = global_context.get("core_thesis", "")
        
        prompt = f"""
        You are a Data Visualization Expert. Based on the video's Global Context, generate a Mermaid.js Mindmap summarizing the entire lifecycle.
        
        CORE THESIS: {core_thesis}
        KNOWLEDGE GRAPH: {json.dumps(knowledge_graph)}
        
        TASK:
        Output STRICT Mermaid.js syntax for a `mindmap`.
        Start with `mindmap\\n  root((Core Concept))` and branch out based on the knowledge graph.
        
        REQUIRED FORMAT (JSON):
        {{
            "mermaid_mindmap": "mindmap\\n  root((...))"
        }}
        """
        
        res = self.llm.generate_text(prompt)
        mindmap_code = ""
        if isinstance(res, dict):
            mindmap_code = res.get("mermaid_mindmap", "")
        elif isinstance(res, str):
            try:
                data = json.loads(res)
                mindmap_code = data.get("mermaid_mindmap", "")
            except:
                mindmap_code = res # Fallback
            
        return {
            "type": "mermaid_mindmap",
            "code": mindmap_code,
            "description": "A holistic mindmap of the entire video."
        }
