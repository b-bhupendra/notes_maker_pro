import sys
import os
import json
import re
from unittest.mock import MagicMock

# Add core_engine to path
sys.path.append(os.path.join(os.getcwd(), "core_engine"))

from engine import VideoProcessor
from engine.analyzer.llm import LLMProcessor

def mock_generate(model, prompt, images=None, format=None, options=None, keep_alive=0):
    """Mocks the Ollama generate call dynamically based on prompt content."""
    
    # 1. Detect Topic from prompt
    topic = "General Knowledge"
    if "mitochondria" in prompt.lower() or "glycolysis" in prompt.lower():
        topic = "Mitochondria"
    elif "serverless" in prompt.lower() or "cloud" in prompt.lower() or "hosting" in prompt.lower():
        topic = "System Design"
    elif "krebs" in prompt.lower():
        topic = "Krebs Cycle"

    # 2. Phase 1: Global Knowledge Mapping
    if "Global Knowledge Mapping" in prompt or "Master Researcher" in prompt:
        if topic == "Mitochondria" or topic == "Krebs Cycle":
            return {
                "response": json.dumps({
                    "core_thesis": "Mitochondria are the powerhouses of the cell, converting glucose and oxygen into ATP.",
                    "glossary": [
                        { "term": "Mitochondria", "definition": "Double-membrane-bound organelle.", "significance": "Essential for energy." },
                        { "term": "Glycolysis", "definition": "The breakdown of glucose.", "significance": "First step in respiration." }
                    ],
                    "knowledge_graph": [{ "source": "Glucose", "target": "ATP", "relation": "Raw material" }],
                    "timeline_roadmap": [{ "timestamp": "00:00", "milestone": "Intro" }],
                    "research_gaps": ["Krebs cycle yield", "Mitochondrial diseases"]
                })
            }
        elif topic == "System Design":
            return {
                "response": json.dumps({
                    "core_thesis": "Choosing between Serverless and Managed instances depends on cost, complexity, and scale.",
                    "glossary": [
                        { "term": "Serverless", "definition": "On-demand compute execution.", "significance": "Low operational overhead." },
                        { "term": "Managed Instance", "definition": "Pre-allocated server capacity.", "significance": "High reliability for scale." }
                    ],
                    "knowledge_graph": [{ "source": "Request", "target": "Lambda", "relation": "Triggers execution" }],
                    "timeline_roadmap": [{ "timestamp": "00:00", "milestone": "Hosting basics" }],
                    "research_gaps": ["CDN edge latency", "Cold start optimizations"]
                })
            }
        else:
            return {
                "response": json.dumps({
                    "core_thesis": "Generic Topic Analysis.",
                    "glossary": [],
                    "knowledge_graph": [],
                    "timeline_roadmap": [],
                    "research_gaps": ["Further details needed"]
                })
            }

    # 3. Phase 2: Research Assistance
    elif "Research Assistant" in prompt:
        query = "detailed facts"
        match = re.search(r"Researching: (.*)", prompt)
        if match: query = match.group(1)
        return { "response": json.dumps({ "query": query }) }

    elif "Synthesize this external research" in prompt:
        return {
            "response": json.dumps({
                "topic": "External Fact",
                "summary": "This is a fact discovered through autonomous research injection.",
                "citations": ["https://research.mcp"]
            })
        }

    # 4. Phase 4: Diagram Engine
    elif "Data Visualization Expert" in prompt:
        return { "response": json.dumps({ "code": "print('Dynamic E2B Diagram Script')" }) }

    # 5. Phase 3: Scene Analysis
    else:
        # Extract snippet for dynamic summary
        snippet = "This scene discusses complex topics."
        combined_text = prompt
        match = re.search(r"AUDIO TRANSCRIPT: (.*)", prompt)
        if match: 
            raw_text = match.group(1).strip()
            snippet = (raw_text[:75] + '...') if len(raw_text) > 75 else raw_text
            combined_text = raw_text

        # Check for keywords to determine the topic
        topic = "General Knowledge"
        if "mitochondria" in combined_text.lower():
            topic = "Mitochondria"
        elif "serverless" in combined_text.lower() or "hosting" in combined_text.lower():
            topic = "System Design"
        elif "prim" in combined_text.lower() or "spanning tree" in combined_text.lower():
            topic = "Prim's Algorithm"
            
        if topic == "Prim's Algorithm":
            analysis = {
                "key_concepts": ["Minimum Spanning Tree", "Undirected Graph", "Greedy Algorithm"],
                "detailed_explanations": "* Prim's algorithm finds the Minimum Spanning Tree (MST) for a connected weighted undirected graph.\n* It builds the tree one vertex at a time, from an arbitrary starting vertex.\n* At each step, it adds the cheapest possible edge from the tree to another vertex.",
                "definitions": [{"term": "MST", "definition": "A subset of edges that connects all vertices without cycles and with minimum total weight."}],
                "visual_elements": [
                    {
                        "type": "diagram",
                        "mermaid_code": "graph TD\nNode[Start Vertex] --> Edge[Cheapest Neighbor] --> Tree[Extended MST]",
                        "caption": "Prim's Algorithm Progression"
                    }
                ],
                "summary": f"Discussion on Prim's Algorithm: {snippet}",
                "research_notes": "Prim's algorithm is functionally similar to Dijkstra's but minimizes total edge weight rather than path distance.",
                "foreshadowing": "This leads to a comparison with Kruskal's algorithm later in the series."
            }
        else:
            analysis = {
                "key_concepts": [topic] if topic != "General Knowledge" else ["Video Analysis"],
                "detailed_explanations": f"* {topic} is discussed in detail using the provided context.\n* Key facts about {topic} are extracted from the transcript and visual data.",
                "definitions": [],
                "visual_elements": [
                    {
                        "type": "diagram",
                        "mermaid_code": f"graph LR\nInputData --> {topic.replace(' ', '_')} --> FinalNotes",
                        "caption": f"Structural Map for {topic}"
                    }
                ],
                "summary": f"Discussion on {topic}: {snippet}",
                "research_notes": f"Extended research suggests {topic} is critical for system stability.",
                "foreshadowing": f"This connects to later revelations about {topic}."
            }
        
        return {
            "response": json.dumps(analysis)
        }

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_mocked_pipeline.py <video_path>")
        return
        
    video_path = sys.argv[1]
    output_dir = "mocked_test_output"
    
    if not os.path.exists(video_path):
        print(f"Error: {video_path} not found.")
        return

    # Patch ollama.Client and easyocr.Reader
    import ollama
    from unittest.mock import patch
    
    with patch("ollama.Client") as mock_client_class, \
         patch("easyocr.Reader") as mock_ocr_class:
        
        mock_client = MagicMock()
        mock_client.generate.side_effect = mock_generate
        mock_client_class.return_value = mock_client
        
        mock_ocr = MagicMock()
        mock_ocr.readtext.return_value = [] # Empty OCR for speed
        mock_ocr_class.return_value = mock_ocr
        
        print(f"Starting MOCKED Dynamic Pipeline for: {video_path}")
        
        # Mock connection checks
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            
            processor = VideoProcessor(
                video_path=video_path,
                output_dir=output_dir,
                model_size="small"
            )
            
            try:
                # Run the processor
                processor.process(cleanup=True)
                print("\nMOCKED Processing Complete!")
                print(f"Success! Knowledge Base generated at {output_dir}/knowledge_base.json")
            except Exception:
                import traceback
                traceback.print_exc(file=sys.stdout)
                sys.exit(1)

if __name__ == "__main__":
    main()
