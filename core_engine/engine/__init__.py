import os
import json
import logging
import time
from .setup_bins import setup_ffmpeg
from .extractor import SceneExtractor
from .transcriber import Transcriber
from .db_manager import DBManager
from .analyzer.converter import KBConverter
from .sleep_blocker import SleepBlocker

logger = logging.getLogger("processor")

class VideoProcessor:
    def __init__(self, video_path, output_dir, transcriber_model="small", db_path="knowledge_lake.db"):
        self.video_path = video_path
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Use DB path in output dir
        actual_db_path = os.path.join(self.output_dir, db_path)
        self.db = DBManager(actual_db_path)
        
        self.transcriber_model_size = transcriber_model
        self.status_file = os.path.join(self.output_dir, "status.json")
        self._update_status(0, "Ready")

    def _update_status(self, progress, message):
        status = {"progress": progress, "message": message, "last_update": time.time()}
        with open(self.status_file, "w") as f:
            json.dump(status, f)
        logger.info(f"[PROGRESS {progress}%] {message}")

    def harvest(self, interval_sec=None):
        """Phase 1: Deterministic Harvesting. Frames + Audio."""
        with SleepBlocker():
            self._update_status(5, "Registering Video in Knowledge Lake...")
            duration = 0 # Need real duration if possible
            video_id = self.db.register_video(self.video_path, duration)
            
            self._update_status(10, "Extracting Visual Scenes...")
            frames_dir = os.path.join(self.output_dir, "frames")
            os.makedirs(frames_dir, exist_ok=True)
            extractor = SceneExtractor(self.video_path, frames_dir)
            frames = extractor.extract_frames(interval_sec or 60)
            
            self._update_status(20, "Initializing Audio Transcriber...")
            transcriber = Transcriber(model_size=self.transcriber_model_size)
            
            self._update_status(25, "Transcribing Audio Stream...")
            transcript = transcriber.transcribe(self.video_path)
            
            self._update_status(40, "Committing Deterministic Data to SQLite...")
            synced = self._synchronize(frames, transcript)
            self.db.save_scenes(video_id, synced)
            
            self._update_status(45, "Harvesting Complete.")
            return video_id

    def synthesize(self, video_id, cleanup=False):
        """Phase 2: Expert Synthesis. Resumable per-scene logic."""
        with SleepBlocker():
            self._update_status(50, "Synthesizer Initialized. Loading LLM...")
            kb_converter = KBConverter(self.output_dir)
            llm = kb_converter.llm
            
            unprocessed = self.db.get_unprocessed_scenes(video_id)
            if not unprocessed:
                self._update_status(100, "Synthesis already complete. Knowledge Lake is full.")
                return self.db.get_full_project(video_id)

            total = len(unprocessed)
            # Load Global context if exists
            project_data = self.db.get_full_project(video_id)
            global_context = project_data.get('global', {})

            for i, scene in enumerate(unprocessed):
                progress = 50 + int((i / total) * 45)
                self._update_status(progress, f"Analyzing Scene {i+1}/{total} (Resumable)...")
                
                # Expert synthesis call
                analysis = llm.analyze_scene(
                    ocr_text="", # Add OCR if needed
                    transcript_text=scene['transcript'],
                    global_context=global_context
                )
                
                if analysis:
                    self.db.save_synthesis(scene['id'], analysis)
                else:
                    logger.error(f"Synthesis failed for scene {scene['id']}")

            self._update_status(95, "Synthesizing Final Materialization...")
            self.db.update_video_status(video_id, 'completed')
            
            if cleanup:
                # Cleanup logic
                pass
                
            self._update_status(100, "Pipeline Complete. Expert Platform Synchronized.")
            return self.db.get_full_project(video_id)

    def process(self, interval_sec=None, cleanup=False):
        video_id = self.harvest(interval_sec=interval_sec)
        return self.synthesize(video_id, cleanup=cleanup)

    def _synchronize(self, frames, transcript):
        sync = []
        transcript_data = transcript if transcript is not None else []
        for frame in frames:
            # Simple sync based on timestamp
            t_start = frame['timestamp']
            t_end = t_start + 10 # Buffer
            
            segment_text = ""
            for seg in transcript_data:
                if seg['start'] >= t_start and seg['start'] < t_end:
                    segment_text += seg['text'] + " "
            
            sync.append({
                "time_range": [t_start, t_end],
                "frame_path": frame['frame_path'],
                "text": segment_text.strip()
            })
        return sync
