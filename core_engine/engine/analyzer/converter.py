import json
import os
from .ocr import OCRProcessor
from .llm import LLMProcessor
from ..logger import get_logger

logger = get_logger("analyzer")

class KBConverter:
    def __init__(self, model="gemma4:e2b"):
        self.ocr = OCRProcessor()
        self.llm = LLMProcessor(model=model)

    def _process_moment(self, moment, metadata_path, i, total):
        logger.info(f"Processing moment {i+1}/{total} at {moment['timestamp']:.2f}s")
        
        frame_path = moment['frame_path']
        if not os.path.isabs(frame_path):
            frame_path = os.path.join(os.path.dirname(metadata_path), frame_path)
        
        # 1. OCR Extraction (Failsafe)
        ocr_text = self.ocr.extract_text(frame_path)
        
        # 2. LLM Analysis (Multimodal)
        analysis = self.llm.analyze_moment(frame_path, ocr_text, moment['text'])
        
        return {
            "timeframe": moment['timestamp'],
            "frame_path": moment['frame_path'],
            "ocr_text": ocr_text,
            "audio_text": moment['text'],
            "key_concepts": analysis.get("key_concepts", []),
            "detailed_explanations": analysis.get("detailed_explanations", ""),
            "definitions": analysis.get("definitions", []),
            "flowcharts_illustrations": analysis.get("flowcharts_illustrations", ""),
            "summary": analysis.get("summary", "")
        }

    def process_metadata(self, metadata_path, output_path="knowledge_base.json", max_workers=10):
        from concurrent.futures import ThreadPoolExecutor
        
        if not os.path.exists(metadata_path):
            logger.error(f"Metadata file not found: {metadata_path}")
            return None
            
        with open(metadata_path, "r") as f:
            data = json.load(f)
            
        synchronized_data = data.get("synchronized", [])
        total = len(synchronized_data)
        
        logger.info(f"Parallel Conversion: Analyzing {total} moments using {max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Map the processing function across all moments
            futures = [
                executor.submit(self._process_moment, moment, metadata_path, i, total)
                for i, moment in enumerate(synchronized_data)
            ]
            knowledge_base = [f.result() for f in futures]
            
        # Sort by timeframe to maintain order
        knowledge_base.sort(key=lambda x: x['timeframe'])
            
        with open(output_path, "w") as f:
            json.dump(knowledge_base, f, indent=4)
            
        logger.info(f"Knowledge Base saved to {output_path}")
        return knowledge_base
