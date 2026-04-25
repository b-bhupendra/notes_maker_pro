import json
import logging
import os
from .llm import LLMProcessor

logger = logging.getLogger("analyzer.researcher")

class ResearchEngine:
    def __init__(self, llm_processor=None):
        self.llm = llm_processor or LLMProcessor()

    def perform_research(self, global_context, search_tool_callback=None):
        """
        Analyzes the global context for research gaps and triggers external research.
        """
        gaps = global_context.get("research_gaps", [])
        if not gaps:
            logger.info("No research gaps identified. Skipping research phase.")
            return global_context

        logger.info(f"Identified {len(gaps)} research gaps. Starting autonomous research...")
        
        extended_research = []
        
        for gap in gaps:
            logger.info(f"Researching: {gap}")
            
            # Step 1: Generate Search Query
            query_prompt = f"""
            You are a Research Assistant. Given this knowledge gap from a video, generate a precise search query to find external documentation, papers, or real-world examples.
            
            KNOWLEDGE GAP: {gap}
            
            Return ONLY the search query string.
            """
            # We use a text-only call here, non-JSON format for raw string
            # But generate_text currently expects format='json'. Let's adapt.
            search_query = self.llm.generate_text(query_prompt)
            # Handle if LLM returns JSON instead of string
            if isinstance(search_query, dict):
                search_query = search_query.get("query", gap)
            
            # Step 2: Trigger Research MCP (Web Search)
            research_data = "Search results unavailable."
            if search_tool_callback:
                try:
                    research_data = search_tool_callback(search_query)
                except Exception as e:
                    logger.error(f"Search tool failed for query '{search_query}': {e}")
            
            # Step 3: Synthesize Research
            synthesis_prompt = f"""
            Synthesize this external research data into a concise technical summary that can be appended to video notes.
            
            TOPIC: {gap}
            RESEARCH DATA: {research_data}
            
            REQUIRED FORMAT (JSON):
            {{
                "topic": "{gap}",
                "summary": "Deep technical summary including facts/data not in the original video.",
                "citations": ["URL 1", "URL 2"]
            }}
            """
            synthesized = self.llm.generate_text(synthesis_prompt)
            if synthesized:
                extended_research.append(synthesized)

        global_context["extended_research"] = extended_research
        return global_context
