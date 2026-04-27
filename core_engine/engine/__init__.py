import os
import json
import shutil
import requests
import time
from .extractor import FrameExtractor
try:
    from .transcriber import Transcriber
except ImportError:
    Transcriber = None
from .analyzer.converter import KBConverter
from .analyzer.context_mapper import ContextMapper
from .analyzer.researcher import ResearchEngine
from .analyzer.diagram_engine import DiagramEngine
from .logger import get_logger
from .utils import safe_is_cuda_available

class VideoProcessor:
    """
    Orchestrates the temporal modularization of the pipeline.
    Module 1: Harvest (Extraction + Transcription)
    Module 2: Synthesize (LLM + Research + HTML)
    """
    def __init__(self, video_path, output_dir="output", model_size=None, callback=None):
        self.video_path = video_path
        self.output_dir = output_dir
        self.logger = get_logger("processor", callback=callback)
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        self.extractor = FrameExtractor(video_path, output_dir=os.path.join(self.output_dir, "frames"))
        self.transcriber_model_size = model_size

    def _check_system(self):
        cuda_available = safe_is_cuda_available()
        max_workers = 1 
        ollama_ready = False
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            ollama_ready = (response.status_code == 200)
        except: pass
        return {"max_workers": max_workers, "ollama_ready": ollama_ready, "cuda_available": cuda_available}

    def _update_status(self, percent, message):
        """Saves status to a file for Streamlit to poll."""
        status = {"percent": percent, "message": message, "timestamp": time.time()}
        with open(os.path.join(self.output_dir, "status.json"), "w") as f:
            json.dump(status, f)
        self.logger.info(f"[PROGRESS {percent}%] {message}")

    def harvest(self, interval_sec=None):
        """
        Module 1: The Harvester (Deterministic)
        Extracts frames and transcript, then stops.
        """
        self._update_status(5, "Initializing Harvester...")
        
        # 1. Extraction
        self._update_status(10, "Extracting Visual Scenes...")
        if interval_sec:
            frames = self.extractor.extract_at_intervals(interval_sec=interval_sec)
        else:
            frames = self.extractor.extract_scenes(threshold=27.0)
            
        # 2. Transcription
        self._update_status(20, "Initializing Audio Transcriber...")
        transcriber = Transcriber(model_size=self.transcriber_model_size) if Transcriber else None
        
        self._update_status(25, "Transcribing Audio Stream...")
        transcript = transcriber.process_video(self.video_path) if transcriber else []
        
        # 3. Data Lake Preservation
        self._update_status(40, "Preserving Data to Lake (project_data.json)...")
        synchronized = self._synchronize(frames, transcript)
        project_data = {
            "video_path": self.video_path,
            "duration": self.extractor.duration,
            "synchronized": synchronized,
            "raw_transcript": transcript
        }
        with open(os.path.join(self.output_dir, "project_data.json"), "w") as f:
            json.dump(project_data, f, indent=4)
            
        # 4. Memory Cleanup
        del transcriber
        import gc
        gc.collect()
        self._update_status(45, "Harvester Complete. Memory Purged.")
        return project_data

    def synthesize(self, cleanup=False):
        """
        Module 2: The Synthesizer (Generative AI)
        Loads raw data and applies LLM synthesis.
        """
        sys_config = self._check_system()
        data_path = os.path.join(self.output_dir, "project_data.json")
        
        if not os.path.exists(data_path):
            self._update_status(0, "Error: project_data.json not found. Run Harvester first.")
            return None
            
        with open(data_path, "r") as f:
            project_data = json.load(f)
            
        if not sys_config["ollama_ready"]:
            self._update_status(0, "Error: Ollama not ready.")
            return None

        self._update_status(50, "Synthesizer Initialized. Loading LLM...")
        self.kb_converter = KBConverter(self.output_dir)
        llm = self.kb_converter.llm
        
        # Phase: Global Mapping
        self._update_status(55, "Generating Global Context Map...")
        global_context = self._run_phase_mapping(project_data["raw_transcript"], llm)
        
        # Phase: Research
        self._update_status(65, "Expanding Knowledge via Autonomous Research...")
        global_context = self._run_phase_research(global_context, llm)
        
        # Phase: Visuals
        self._update_status(75, "Generating Holistic Diagrams...")
        global_context = self._run_phase_visuals(global_context, llm)
        
        # Phase: Synthesis (The Reduce)
        num_scenes = len(project_data["synchronized"])
        self._update_status(80, f"Synthesizing {num_scenes} Knowledge Blocks...")
        # NOTE: Pass 'keep_alive' info to converter if needed, or rely on internal logic
        kb_result = self._run_phase_synthesis(data_path, global_context, sys_config["max_workers"])
        
        # Phase: Materialization
        self._update_status(95, "Materializing Final Clinical Notes (HTML)...")
        self._run_phase_html(kb_result, global_context)
        
        if cleanup:
            self._cleanup()
            
        self._update_status(100, "Pipeline Complete. Knowledge Base Materialized.")
        return kb_result

    def process(self, interval_sec=None, cleanup=False):
        """Legacy entry point: Runs Harvester and Synthesizer sequentially."""
        self.harvest(interval_sec=interval_sec)
        return self.synthesize(cleanup=cleanup)

    def _synchronize(self, frames, transcript):
        sync = []
        transcript_data = transcript if transcript is not None else []
        for frame in frames:
            start, end = frame['time_range']
            text = " ".join([seg['text'] for seg in transcript_data if not (seg['end'] < start or seg['start'] > end)])
            sync.append({
                "time_range": frame['time_range'],
                "timestamp": frame['timestamp'],
                "frame_path": os.path.relpath(frame['path'], self.output_dir),
                "text": text
            })
        return sync

    def _run_phase_mapping(self, transcript, llm):
        mapper = ContextMapper(llm_processor=llm)
        transcript_data = transcript if transcript is not None else []
        full_text = " ".join([t['text'] for t in transcript_data])
        path = os.path.join(self.output_dir, "global_context.json")
        return mapper.generate_global_context(full_text, [], output_path=path)

    def _run_phase_research(self, context, llm):
        engine = ResearchEngine(llm_processor=llm)
        return engine.perform_research(context)

    def _run_phase_visuals(self, context, llm):
        engine = DiagramEngine(llm_processor=llm)
        context["holistic_diagram"] = engine.generate_holistic_diagrams(context)
        return context

    def _run_phase_synthesis(self, project_data_file, context, workers):
        kb_file = os.path.join(self.output_dir, "knowledge_base.json")
        return self.kb_converter.process_metadata(project_data_file, kb_file, global_context=context, max_workers=workers)

    def _run_phase_html(self, kb, context):
        if not kb: return
        from .html_generator import HTMLGenerator
        html_gen = HTMLGenerator(title=f"Visual Notes: {os.path.basename(self.video_path)}")
        ctx_path = os.path.join(self.output_dir, "global_context.json")
        with open(ctx_path, "w") as f: json.dump(context, f, indent=4)
        html_gen.generate(os.path.join(self.output_dir, "knowledge_base.json"), 
                         os.path.join(self.output_dir, "visual_notes.html"), 
                         global_context_path=ctx_path)

    def _cleanup(self):
        self.logger.info("Cleaning up...")
        frames_dir = os.path.join(self.output_dir, "frames")
        if os.path.exists(frames_dir): shutil.rmtree(frames_dir)
        for f in os.listdir(self.output_dir):
            if f.endswith(".mp3"): os.remove(os.path.join(self.output_dir, f))
