try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None
import os
import subprocess
from .logger import get_logger
from .utils import safe_is_cuda_available
from .setup_bins import ensure_ffmpeg

logger = get_logger("transcriber")

class Transcriber:
    def __init__(self, model_size=None, device="cpu"):
        # Force CPU for stability on 8GB RAM systems
        self.device = "cpu"
        cuda_available = safe_is_cuda_available()
        
        # If user didn't specify model, auto-select based on hardware
        if model_size is None:
            self.model_size = "medium" if cuda_available else "small"
        else:
            self.model_size = model_size

        # Ensure ffmpeg is available (auto-downloads if missing)
        ffmpeg_ready = ensure_ffmpeg()
        if not ffmpeg_ready:
            logger.warning(
                "ffmpeg could not be found or downloaded. "
                "Audio transcription will be skipped."
            )
        self.ffmpeg_ready = ffmpeg_ready
        
        print(f"DEBUG: Loading Whisper model '{self.model_size}' on {self.device}...")
        try:
            # Try Faster-Whisper first
            if WhisperModel is not None:
                print("DEBUG: Attempting Faster-Whisper initialization...")
                compute_type = "float16" if self.device == "cuda" else "int8"
                self.model = WhisperModel(self.model_size, device=self.device, compute_type=compute_type)
                print("DEBUG: Faster-Whisper loaded successfully.")
                return
            
            # Fallback to standard OpenAI Whisper
            logger.info("Faster-Whisper missing or failed. Falling back to openai-whisper...")
            import whisper
            self.model = whisper.load_model(self.model_size, device=self.device)
            logger.info("OpenAI Whisper loaded successfully (Fallback).")
            
        except Exception as e:
            logger.error(f"Failed to load any Whisper model: {e}")
            self.model = None

    def extract_audio(self, video_path, audio_output="temp_audio.mp3"):
        if not getattr(self, "ffmpeg_ready", False):
            logger.warning("Skipping audio extraction: ffmpeg is not available.")
            return None
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
        
        segments = []
        try:
            # Check if it's Faster-Whisper (returns generator) or OpenAI (returns dict)
            if hasattr(self.model, "transcribe") and callable(getattr(self.model, "transcribe")):
                # Faster-Whisper style
                try:
                    # Faster-whisper returns (generator, info)
                    segments_gen, _ = self.model.transcribe(audio_path, beam_size=5)
                    for segment in segments_gen:
                        segments.append({
                            "start": segment.start,
                            "end": segment.end,
                            "text": segment.text.strip()
                        })
                except Exception:
                    # Maybe it's OpenAI whisper style (dict)
                    result = self.model.transcribe(audio_path)
                    for segment in result.get("segments", []):
                        segments.append({
                            "start": segment.get("start", 0),
                            "end": segment.get("end", 0),
                            "text": segment.get("text", "").strip()
                        })
            
            for s in segments[:3]: # Log first few for verification
                logger.info(f"[{s['start']:.2f}s -> {s['end']:.2f}s]: {s['text']}")
                
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            
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
