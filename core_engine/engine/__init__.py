import os
import json
import shutil
import requests
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
    Orchestrates the Two-Pass Map-Reduce Architecture for video knowledge synthesis.
    """
    def __init__(self, video_path, output_dir="output", model_size=None, callback=None):
        self.video_path = video_path
        self.output_dir = output_dir
        self.logger = get_logger("processor", callback=callback)
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        self.extractor = FrameExtractor(video_path, output_dir=os.path.join(self.output_dir, "frames"))
        self.transcriber = Transcriber(model_size=model_size) if Transcriber else None
        self.kb_converter = None # Initialized during process

    def _check_system(self):
        cuda_available = safe_is_cuda_available()
        # FIX: Restrict to 1 worker for local multimodal LLMs to prevent VRAM OOM
        max_workers = 1 
        ollama_ready = False
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            ollama_ready = (response.status_code == 200)
        except: pass
        return {"max_workers": max_workers, "ollama_ready": ollama_ready, "cuda_available": cuda_available}

    def process(self, interval_sec=None, cleanup=False):
        sys_config = self._check_system()
        self.logger.info(f"System State: Ollama={sys_config['ollama_ready']}, Workers={sys_config['max_workers']}")
        
        # 1. Ingestion Phase
        self.logger.info("Step 1: Ingesting video (Scenes + Transcription)...")
        if interval_sec:
            frames = self.extractor.extract_at_intervals(interval_sec=interval_sec)
        else:
            frames = self.extractor.extract_scenes(threshold=27.0)
            
        transcript = self.transcriber.process_video(self.video_path) if self.transcriber else []
        
        # --- NEW: WATERFALL MEMORY CLEAR ---
        self.logger.info("Freeing Audio Transcriber from memory...")
        import gc
        del self.transcriber
        self.transcriber = None
        gc.collect()
        try:
            if sys_config.get("cuda_available"):
                import torch
                torch.cuda.empty_cache()
        except ImportError:
            pass
        # -----------------------------------
        
        # Synchronize data for metadata
        synchronized = self._synchronize(frames, transcript)
        metadata_file = os.path.join(self.output_dir, "metadata.json")
        with open(metadata_file, "w") as f:
            json.dump({"video_path": self.video_path, "synchronized": synchronized}, f, indent=4)

        # 2. Map-Reduce Pipeline
        kb_result = None
        if sys_config["ollama_ready"]:
            self.kb_converter = KBConverter()
            llm = self.kb_converter.llm
            
            # Pass 1: Global Context & Research
            global_context = self._run_phase_mapping(transcript, llm)
            global_context = self._run_phase_research(global_context, llm)
            global_context = self._run_phase_visuals(global_context, llm)
            
            # Pass 2: Context-Injected Synthesis
            kb_result = self._run_phase_synthesis(metadata_file, global_context, sys_config["max_workers"])
            
            # Phase 5: Final Materialization
            self._run_phase_html(kb_result, global_context)
        else:
            self.logger.error("Ollama not found. Skipping AI synthesis.")

        if cleanup:
            self._cleanup()
            
        return kb_result

    def _synchronize(self, frames, transcript):
        sync = []
        # Ensure transcript is iterable
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
        self.logger.info("Phase 1: Mapping Global Context...")
        mapper = ContextMapper(llm_processor=llm)
        transcript_data = transcript if transcript is not None else []
        full_text = " ".join([t['text'] for t in transcript_data])
        path = os.path.join(self.output_dir, "global_context.json")
        return mapper.generate_global_context(full_text, [], output_path=path)

    def _run_phase_research(self, context, llm):
        self.logger.info("Phase 2: Autonomous Research Expansion...")
        engine = ResearchEngine(llm_processor=llm)
        def search(q): 
            self.logger.info(f"Researching: {q}")
            return f"Simulated insight for {q}"
        return engine.perform_research(context, search_tool_callback=search)

    def _run_phase_visuals(self, context, llm):
        self.logger.info("Phase 4: Generating Holistic E2B Diagrams...")
        engine = DiagramEngine(llm_processor=llm)
        context["holistic_diagram"] = engine.generate_holistic_diagrams(context)
        return context

    def _run_phase_synthesis(self, metadata_file, context, workers):
        self.logger.info("Phase 3: Context-Injected 'Reduce' Synthesis...")
        kb_file = os.path.join(self.output_dir, "knowledge_base.json")
        return self.kb_converter.process_metadata(metadata_file, kb_file, global_context=context, max_workers=workers)

    def _run_phase_html(self, kb, context):
        if not kb: return
        self.logger.info("Phase 5: Materializing Visual Notes (HTML)...")
        from .html_generator import HTMLGenerator
        html_gen = HTMLGenerator(title=f"Visual Notes: {os.path.basename(self.video_path)}")
        ctx_path = os.path.join(self.output_dir, "global_context.json")
        # Save context one last time
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
