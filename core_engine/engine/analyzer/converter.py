import os
import json
import logging
from .llm import LLMProcessor
from .researcher import Researcher

logger = logging.getLogger("analyzer.converter")

class KBConverter:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.llm = LLMProcessor()
        self.researcher = Researcher()

    def _process_moment(self, moment, output_dir, idx, total):
        """
        Synthesizes a single moment (scene) into a Knowledge Block.
        """
        # Add visual context if images exist
        visual_assets = []
        if moment.get('frame_path'):
            abs_path = os.path.join(output_dir, moment['frame_path'])
            visual_assets.append({'asset_path': abs_path, 'type': 'frame'})

        # Synthesize via Expert LLM
        analysis = self.llm.analyze_scene(
            ocr_text=moment.get('ocr_text', ''),
            transcript_text=moment.get('text', ''),
            global_context=moment.get('global_context', {}),
            visual_assets=visual_assets
        )
        
        return analysis
