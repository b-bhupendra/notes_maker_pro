try:
    import whisper
except ImportError:
    whisper = None
import os
import subprocess
from .logger import get_logger

logger = get_logger("transcriber")

class Transcriber:
    def __init__(self, model_size=None, device=None):
        import torch
        # Auto-detect CUDA
        cuda_available = torch.cuda.is_available()
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
        
        logger.info(f"Loading Whisper model '{self.model_size}' on {self.device}...")
        self.model = whisper.load_model(self.model_size, device=self.device)
        logger.info("Model loaded successfully.")

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
        logger.info(f"Starting transcription for {audio_path}...")
        result = self.model.transcribe(audio_path, verbose=False)
        
        segments = []
        for segment in result['segments']:
            segments.append({
                "start": segment['start'],
                "end": segment['end'],
                "text": segment['text'].strip()
            })
            logger.info(f"[{segment['start']:.2f}s -> {segment['end']:.2f}s]: {segment['text'].strip()}")
            
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
