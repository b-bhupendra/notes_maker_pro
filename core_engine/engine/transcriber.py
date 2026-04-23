try:
    import whisper
except ImportError:
    whisper = None
import os
import subprocess
from .logger import get_logger

logger = get_logger("transcriber")

class Transcriber:
    def __init__(self, model_size="small", device="cpu"):
        # Check for local ffmpeg relative to this file
        self.bin_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin"))
        if os.path.exists(os.path.join(self.bin_path, "ffmpeg.exe")):
            os.environ["PATH"] += os.pathsep + self.bin_path
            logger.info(f"Added {self.bin_path} to PATH for local ffmpeg usage.")
        else:
            logger.warning("Local bin/ffmpeg.exe not found. Ensure ffmpeg is in your system PATH.")

        logger.info(f"Loading Whisper model '{model_size}' (offline)...")
        self.model = whisper.load_model(model_size, device=device)
        logger.info("Model loaded successfully.")

    def extract_audio(self, video_path, audio_output="temp_audio.mp3"):
        logger.info(f"Extracting audio from {video_path}...")
        try:
            # Using ffmpeg directly to avoid moviepy overhead if possible
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
