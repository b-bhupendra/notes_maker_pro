from .extractor import FrameExtractor
try:
    from .transcriber import Transcriber
except ImportError:
    Transcriber = None
from .analyzer.converter import KBConverter
from .logger import get_logger
import os
import json

class VideoProcessor:
    def __init__(self, video_path, output_dir="output", model_size="small", callback=None):
        self.video_path = video_path
        self.output_dir = output_dir
        self.logger = get_logger("processor", callback=callback)
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        self.extractor = FrameExtractor(video_path, output_dir=os.path.join(self.output_dir, "frames"))
        self.transcriber = Transcriber(model_size=model_size)

    def process(self, num_frames=None, interval_sec=None, cleanup=False):
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
        if transcript:
            for frame in frames:
                ts = frame['timestamp']
                text_at_ts = ""
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
        kb_file = os.path.join(self.output_dir, "knowledge_base.json")
        kb_converter = KBConverter()
        # Use 50 workers for extreme speedup
        kb_result = kb_converter.process_metadata(metadata_file, kb_file, max_workers=50)
        
        # 6. Optional Cleanup
        if cleanup:
            self.logger.info("Cleaning up temporary files (frames and audio)...")
            import shutil
            frames_dir = os.path.join(self.output_dir, "frames")
            if os.path.exists(frames_dir):
                shutil.rmtree(frames_dir)
            
            # Delete any mp3 files in output_dir
            for f in os.listdir(self.output_dir):
                if f.endswith(".mp3"):
                    os.remove(os.path.join(self.output_dir, f))
            self.logger.info("Cleanup complete.")

        self.logger.info(f"Processing complete. Knowledge Base saved to {kb_file}")
        return kb_result
