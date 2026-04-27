import json
import os
from .ocr import OCRProcessor
from .llm import LLMProcessor
from .visual_engine import VisualEngine
from .animation_engine import AnimationEngine, ContextMapper
from ..logger import get_logger

logger = get_logger("analyzer")

class KBConverter:
    def __init__(self, model="gemma4:e2b"):
        self.ocr = OCRProcessor()
        self.llm = LLMProcessor(model=model)
        self.visual_engine = VisualEngine(self.llm)
        self.animation_engine = AnimationEngine(self.llm)
        self.context_mapper = ContextMapper()  # Per-chunk mechanism detector

    def _process_moment(self, moment, metadata_path, i, total, layout_analyzer):
        logger.info(f"Processing scene {i+1}/{total} from {moment.get('time_range', [0,0])}")
        
        frame_path = moment['frame_path']
        output_dir = os.path.dirname(metadata_path)
        if not os.path.isabs(frame_path):
            frame_path = os.path.join(output_dir, frame_path)
        
        # 1. OCR Extraction (Failsafe)
        ocr_text = self.ocr.extract_text(frame_path)

        # Fix 1: LayoutAnalyzer removed — it was doing expensive OpenCV crop work
        # (layout_analyzer.detect_and_crop) only to be overwritten on the very next line.
        # Pass the full frame directly to the LLM, saving CPU, disk I/O, and temp files.
        absolute_visual_elements = [{"asset_path": frame_path}]

        # 2. LLM Analysis (Multimodal with Global Context)
        # Fix 3 (prev): Use .get() to avoid KeyError if transcriber returned empty segments
        text_content = moment.get('text', '')
        try:
            analysis = self.llm.analyze_scene(absolute_visual_elements, ocr_text, text_content, global_context=moment.get('global_context'))
        except Exception as e:
            logger.error(f"LLM analysis failed for scene {i+1}: {e}")
            analysis = {}
        
        # 4. Visual Enhancement
        visual_elements_out = []
        for vis in analysis.get("visual_elements", []):
            try:
                if vis.get("type") == "diagram":
                    code = vis.get("mermaid_code", "")
                    if code and not self.visual_engine._validate_mermaid(code):
                        logger.info("Fixing Mermaid syntax via VisualEngine...")
                        code = self.visual_engine.generate_mermaid_flowchart(text_content)
                    if code:
                        visual_elements_out.append({
                            "type": "diagram",
                            "mermaid_code": code,
                            "caption": vis.get("caption", "System Diagram")
                        })
                elif vis.get("type") == "illustration":
                    logger.info("Generating SVG illustration metaphor...")
                    svg = self.visual_engine.generate_svg_illustration(text_content)
                    if svg:
                        visual_elements_out.append({
                            "type": "svg_illustration",
                            "svg_code": svg,
                            "metaphor_explanation": vis.get("metaphor_explanation", "")
                        })
            except Exception as ev:
                logger.error(f"Visual enhancement failed for scene {i+1}: {ev}")

        # 4. Animation Trigger Logic — delegated to ContextMapper.detect_mechanism()
        # Combines audio transcript + LLM-derived explanations for the check so
        # the detector can catch mechanistic descriptions the LLM surfaces even
        # when the raw transcript text alone lacks trigger keywords.
        combined_text = text_content + " " + analysis.get("detailed_explanations", "")
        if self.context_mapper.detect_mechanism(combined_text):
            logger.info(f"ContextMapper: mechanism detected for scene {i+1} — generating animated explainer...")
            animated_svg = self.animation_engine.generate_explainer(
                text_content, moment.get("global_context")
            )
            if animated_svg:
                visual_elements_out.append({
                    "type": "animated_explainer",
                    "svg_code": animated_svg
                })
        
        return {
            "time_range": moment.get('time_range', [moment.get('timestamp', 0), moment.get('timestamp', 0)]),
            "frame_path": moment.get('frame_path', ''),
            "ocr_text": ocr_text,
            "audio_text": text_content,  # Fix 3: use the safe variable, not moment['text']
            "key_concepts": analysis.get("key_concepts", []),
            "detailed_explanations": analysis.get("detailed_explanations", ""),
            "definitions": analysis.get("definitions", []),
            "visual_elements": visual_elements_out,
            "summary": analysis.get("summary", ""),
            "research_notes": analysis.get("research_notes", ""),
            "foreshadowing": analysis.get("foreshadowing", "")
        }

    def process_metadata(self, metadata_path, output_path="knowledge_base.json", global_context=None, max_workers=10):
        from concurrent.futures import ThreadPoolExecutor
        
        if not os.path.exists(metadata_path):
            logger.error(f"Metadata file not found: {metadata_path}")
            return None
            
        with open(metadata_path, "r") as f:
            data = json.load(f)
            
        synchronized_data = data.get("synchronized", [])
        total = len(synchronized_data)
        
        # Fix 1: LayoutAnalyzer fully removed — no assets dir creation, no init needed.
        logger.info(f"Parallel Conversion: Analyzing {total} scenes using {max_workers} workers...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Inject global context into each moment before dispatching workers
            for moment in synchronized_data:
                moment['global_context'] = global_context

            futures = [
                executor.submit(self._process_moment, moment, metadata_path, i, total)
                for i, moment in enumerate(synchronized_data)
            ]
            knowledge_base = [f.result() for f in futures]
            
        # Sort by start time to maintain order
        knowledge_base.sort(key=lambda x: x['time_range'][0])
            
        with open(output_path, "w") as f:
            json.dump(knowledge_base, f, indent=4)
            
        logger.info(f"Knowledge Base saved to {output_path}")
        return knowledge_base
