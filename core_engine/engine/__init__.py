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
from .db_manager import DBManager

from .sleep_blocker import PreventSystemSleep

class VideoProcessor:
    """
    Orchestrates the relational 'Knowledge Lake' pipeline.
    """
    def __init__(self, video_path, output_dir="output", model_size=None, callback=None):
        self.video_path = video_path
        self.output_dir = output_dir
        self.logger = get_logger("processor", callback=callback)
        self.db = DBManager(os.path.join(self.output_dir, "knowledge_lake.db"))
        
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
        status = {"percent": percent, "message": message, "timestamp": time.time()}
        with open(os.path.join(self.output_dir, "status.json"), "w") as f:
            json.dump(status, f)
        self.logger.info(f"[PROGRESS {percent}%] {message}")

    def harvest(self, interval_sec=None):
        """Module 1: The Relational Harvester"""
        with PreventSystemSleep():
            self._update_status(5, "Registering Video in Knowledge Lake...")
            video_id = self.db.register_video(self.video_path, self.extractor.duration)
            
            self._update_status(10, "Extracting Visual Scenes...")
            if interval_sec:
                frames = self.extractor.extract_at_intervals(interval_sec=interval_sec)
            else:
                frames = self.extractor.extract_scenes(threshold=27.0)
                
            self._update_status(20, "Initializing Audio Transcriber...")
            transcriber = Transcriber(model_size=self.transcriber_model_size) if Transcriber else None
            
            self._update_status(25, "Transcribing Audio Stream...")
            transcript = transcriber.process_video(self.video_path) if transcriber else []
            
            self._update_status(40, "Committing Deterministic Data to SQLite...")
            synchronized = self._synchronize(frames, transcript)
            self.db.save_scenes(video_id, synchronized)
            self.db.update_video_status(video_id, 'harvested')
            
            # Save project_data.json for legacy/debugging
            with open(os.path.join(self.output_dir, "project_data.json"), "w") as f:
                json.dump({"video_id": video_id, "synchronized": synchronized}, f, indent=4)
                
            del transcriber
            import gc
            gc.collect()
            self._update_status(45, "Harvesting Complete.")
            return video_id

    def synthesize(self, cleanup=False):
        """Module 2: The Relational Synthesizer"""
        with PreventSystemSleep():
            sys_config = self._check_system()
            video_id = self.db.register_video(self.video_path, self.extractor.duration)
            scenes = self.db.get_scenes(video_id)
            
            if not scenes:
                self._update_status(0, "Error: No harvested scenes found in DB. Run Harvester first.")
                return None
                
            if not sys_config["ollama_ready"]:
                self._update_status(0, "Error: Ollama not ready.")
                return None

            self._update_status(50, "Synthesizer Initialized. Loading LLM...")
            self.kb_converter = KBConverter(self.output_dir)
            llm = self.kb_converter.llm
            
            # We need the full transcript for mapping
            full_transcript = " ".join([s['transcript'] for s in scenes])
            
            self._update_status(55, "Generating Global Context Map...")
            global_context = self._run_phase_mapping_raw(full_transcript, llm)
            global_context = self._run_phase_research(global_context, llm)
            global_context = self._run_phase_visuals(global_context, llm)
            
            self._update_status(80, f"Synthesizing {len(scenes)} Knowledge Blocks...")
            # Custom synthesis loop for DB
            kb_result = []
            for i, s in enumerate(scenes):
                self._update_status(80 + int((i/len(scenes))*15), f"Processing Block {i+1}/{len(scenes)}...")
                moment = {
                    "frame_path": s['frame_path'],
                    "text": s['transcript'],
                    "global_context": global_context,
                    "time_range": [s['start_time'], s['end_time']]
                }
                analysis = self.kb_converter._process_moment(moment, self.output_dir, i, len(scenes))
                self.db.save_synthesis(s['id'], analysis)
                kb_result.append(analysis)
            
            self._update_status(95, "Materializing Final Clinical Notes (HTML)...")
            exported_kb = self.db.export_knowledge_base(video_id)
            kb_file = os.path.join(self.output_dir, "knowledge_base.json")
            with open(kb_file, "w") as f: json.dump(exported_kb, f, indent=4)
            
            self._run_phase_html(exported_kb, global_context)
            self.db.update_video_status(video_id, 'completed')
            
            if cleanup:
                self._cleanup()
                
            self._update_status(100, "Pipeline Complete.")
            return exported_kb

    def process(self, interval_sec=None, cleanup=False):
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

    def _run_phase_mapping_raw(self, full_text, llm):
        mapper = ContextMapper(llm_processor=llm)
        path = os.path.join(self.output_dir, "global_context.json")
        return mapper.generate_global_context(full_text, [], output_path=path)

    def _run_phase_research(self, context, llm):
        engine = ResearchEngine(llm_processor=llm)
        return engine.perform_research(context)

    def _run_phase_visuals(self, context, llm):
        engine = DiagramEngine(llm_processor=llm)
        context["holistic_diagram"] = engine.generate_holistic_diagrams(context)
        return context

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
