from .extractor import FrameExtractor
try:
    from .transcriber import Transcriber
except ImportError:
    Transcriber = None
from .analyzer.converter import KBConverter
from .logger import get_logger
import os
import json
import shutil
import requests

class VideoProcessor:
    def __init__(self, video_path, output_dir="output", model_size=None, callback=None):
        self.video_path = video_path
        self.output_dir = output_dir
        self.logger = get_logger("processor", callback=callback)
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        self.extractor = FrameExtractor(video_path, output_dir=os.path.join(self.output_dir, "frames"))
        self.transcriber = Transcriber(model_size=model_size)

    def check_prerequisites(self):
        """
        Verifies system readiness and tunes parameters based on available hardware.
        Returns a dict of tuned parameters.
        """
        self.logger.info("Checking system prerequisites...")
        import torch
        cuda_available = torch.cuda.is_available()
        
        # Tune workers based on GPU
        # Local LLMs can't handle 50 workers. 5 is stable for most GPUs.
        max_workers = 5 if cuda_available else 2
        
        # Check Ollama
        ollama_ready = False
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                ollama_ready = True
                self.logger.info("Ollama is reachable.")
            else:
                self.logger.warning(f"Ollama returned unexpected status: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Ollama connection check failed: {e}. Knowledge Base generation might fail.")

        self.logger.info(f"System Ready: CUDA={cuda_available}, Workers={max_workers}")
        return {
            "max_workers": max_workers,
            "cuda": cuda_available,
            "ollama_ready": ollama_ready
        }

    def process(self, num_frames=None, interval_sec=None, cleanup=False):
        # 0. Pre-flight Check
        config = self.check_prerequisites()
        
        self.logger.info("Starting full video processing...")
        
        # 1. Extract Frames
        if interval_sec:
            frames = self.extractor.extract_with_interval(interval_sec)
        else:
            frames = self.extractor.extract_n_frames(num_frames or 10)
        
        # 2. Transcribe Audio
        transcript = self.transcriber.process_video(self.video_path)
        
        # 3. Synchronize
        synchronized = []
        for frame in frames:
            ts = frame['timestamp']
            text_at_ts = ""
            if transcript:
                for segment in transcript:
                    if segment['start'] <= ts <= segment['end']:
                        text_at_ts = segment['text']
                        break
            
            rel_path = os.path.relpath(frame['path'], self.output_dir)
            synchronized.append({
                "timestamp": ts,
                "frame_path": rel_path,
                "text": text_at_ts
            })

        # 4. Save Metadata
        result = {
            "video_path": self.video_path,
            "frames": [{"timestamp": f['timestamp'], "path": os.path.relpath(f['path'], self.output_dir)} for f in frames],
            "transcript": transcript,
            "synchronized": synchronized
        }
        
        metadata_file = os.path.join(self.output_dir, "metadata.json")
        with open(metadata_file, "w") as f:
            json.dump(result, f, indent=4)
            
        # 5. Convert to Knowledge Base (Parallel OCR + LLM)
        if config["ollama_ready"]:
            kb_file = os.path.join(self.output_dir, "knowledge_base.json")
            kb_converter = KBConverter()
            kb_result = kb_converter.process_metadata(metadata_file, kb_file, max_workers=config["max_workers"])
        else:
            self.logger.error("Skipping Knowledge Base generation because Ollama is not reachable.")
            kb_result = None
        
        # 6. Generate HTML Visual Notes
        if kb_result:
            self.logger.info("Generating Visual Notes (HTML)...")
            from .html_generator import HTMLGenerator
            html_gen = HTMLGenerator(title=f"Visual Notes: {os.path.basename(self.video_path)}")
            html_output = os.path.join(self.output_dir, "visual_notes.html")
            html_gen.generate(kb_file, html_output)
            self.logger.info(f"Visual Notes saved to {html_output}")

        # 7. Optional Cleanup
        if cleanup:
            self.logger.info("Cleaning up temporary files...")
            frames_dir = os.path.join(self.output_dir, "frames")
            if os.path.exists(frames_dir):
                shutil.rmtree(frames_dir)
            
            for f in os.listdir(self.output_dir):
                if f.endswith(".mp3"):
                    os.remove(os.path.join(self.output_dir, f))
            self.logger.info("Cleanup complete.")

        self.logger.info(f"Processing complete.")
        return kb_result

