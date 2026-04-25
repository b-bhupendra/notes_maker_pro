try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None
import os
import subprocess
from .logger import get_logger
from .utils import safe_is_cuda_available

logger = get_logger("transcriber")

class Transcriber:
    def __init__(self, model_size=None, device=None):
        # Auto-detect CUDA safely
        cuda_available = safe_is_cuda_available()
        self.device = device or ("cuda" if cuda_available else "cpu")
        
        # If user didn't specify model, auto-select based on hardware
        if model_size is None:
            self.model_size = "medium" if cuda_available else "small"
        else:
            self.model_size = model_size

        # Check for local ffmpeg relative to this file
        self.bin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin"))
        if os.path.exists(os.path.join(self.bin_path, "ffmpeg.exe")):
            if self.bin_path not in os.environ["PATH"]:
                os.environ["PATH"] += os.pathsep + self.bin_path
                logger.info(f"Added {self.bin_path} to PATH for local ffmpeg usage.")
        
        logger.info(f"Loading Faster-Whisper model '{self.model_size}' on {self.device}...")
        try:
            # compute_type="int8" is very stable and fast on CPU
            compute_type = "float16" if self.device == "cuda" else "int8"
            self.model = WhisperModel(self.model_size, device=self.device, compute_type=compute_type)
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Faster-Whisper model: {e}")
            self.model = None

    def extract_audio(self, video_path, audio_output="temp_audio.mp3"):
        logger.info(f"Extracting audio from {video_path}...")
        try:
            command = [
                "ffmpeg", "-i", video_path,
                "-ab", "160k", "-ac", "2", "-ar", "44100", "-vn",
                "-y", audio_output
            ]
            subprocess.run(command, check=True, capture_output=True)
            logger.info(f"Audio extracted to {audio_output}")
            return audio_output
        except Exception as e:
            logger.error(f"Failed to extract audio: {str(e)}")
            return None

    def transcribe(self, audio_path):
        if not self.model:
            logger.error("No model loaded, skipping transcription.")
            return []

        logger.info(f"Starting transcription for {audio_path}...")
        # beam_size=5 is standard
        segments_gen, info = self.model.transcribe(audio_path, beam_size=5)
        
        segments = []
        for segment in segments_gen:
            segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip()
            })
            logger.info(f"[{segment.start:.2f}s -> {segment.end:.2f}s]: {segment.text.strip()}")
            
        return segments

    def process_video(self, video_path):
        audio_path = self.extract_audio(video_path)
        if audio_path:
            transcript = self.transcribe(audio_path)
            # Cleanup temp audio
            if os.path.exists(audio_path):
                os.remove(audio_path)
            return transcript
        return None
