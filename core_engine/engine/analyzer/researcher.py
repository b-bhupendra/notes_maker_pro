try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

logger = logging.getLogger("analyzer.researcher")

class ResearchEngine:
    def __init__(self, llm_processor=None):
        self.llm = llm_processor or LLMProcessor()

    def _default_search(self, query):
        if not DDGS:
            return "Search tool not installed (duckduckgo-search)."
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                return "\n".join([f"{r['title']}: {r['body']}" for r in results])
        except Exception as e:
            logger.error(f"DDG Search failed: {e}")
            return "Search failed."

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
            # Fix 2: generate_text() forces format='json' on Ollama, so the prompt MUST
            # request JSON back — asking for a raw string causes a silent parse failure
            # returning {} every time, permanently skipping all research.
            query_prompt = f"""
            You are a Research Assistant. Given this knowledge gap from a video, generate a precise search query to find external documentation, papers, or real-world examples.
            
            KNOWLEDGE GAP: {gap}
            
            REQUIRED FORMAT (JSON):
            {{"query": "exact search terms here"}}
            
            Return ONLY the JSON object. No extra text.
            """
            search_query_result = self.llm.generate_text(query_prompt)
            # Safely extract the query string; fall back to the raw gap text if parsing fails
            if isinstance(search_query_result, dict):
                search_query = search_query_result.get("query", gap)
            else:
                search_query = gap
            
            # Step 2: Trigger Research (Web Search)
            research_data = "Search results unavailable."
            search_func = search_tool_callback or self._default_search
            try:
                research_data = search_func(search_query)
            except Exception as e:
                logger.error(f"Search failed for query '{search_query}': {e}")
            
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
