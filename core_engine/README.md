# Core Engine: Video Knowledge Extraction API

This submodule provides a robust, offline-first API for extracting visual (frames) and textual (transcription) knowledge from video files.

## 🚀 Quick Start

```python
import sys
import os
# Ensure the core_engine is in your path
sys.path.append("path/to/core_engine")

from engine import VideoProcessor

def my_callback(msg):
    print(f"Update: {msg}")

processor = VideoProcessor(
    video_path="lecture.mp4",
    output_dir="output_folder",
    model_size="base",  # whisper model: 'tiny', 'base', 'small', 'medium'
    callback=my_callback
)

# Extract 70 frames and transcribe with synchronization
result = processor.process(num_frames=70)

print(f"Extracted {len(result['frames'])} frames.")
print(f"Synchronized data count: {len(result['synchronized'])}")
# Access synchronized data
for entry in result['synchronized']:
    print(f"At {entry['timestamp']}s (Image: {entry['frame_path']}): {entry['text']}")
```

## 📂 Directory Structure
- `engine/`: Main Python package.
- `bin/`: **CRITICAL**. Place `ffmpeg.exe` and `ffprobe.exe` here for audio extraction.
- `tests/`: Pytest suite for verifying components.

## 🛠 Main Classes

### `VideoProcessor`
The main orchestrator class.
- `__init__(video_path, output_dir="output", model_size="small", callback=None)`
    - `video_path`: Path to source video.
    - `output_dir`: Where results will be saved.
    - `model_size`: Whisper model to use (runs offline).
    - `callback`: Optional function `fn(message: str)` to receive real-time progress updates.
- `process(num_frames=None, interval_sec=None, cleanup=False)`
    - Coordinates extraction, transcription, synchronization, and knowledge base generation.
    - **interval_sec**: Set to e.g. `0.5` for high-frequency sampling.
    - **cleanup**: Set to `True` to automatically delete all screenshots and audio files after the `knowledge_base.json` is generated.

### `FrameExtractor` (Internal)
Handles visual sampling.
- Automatically resizes screenshots to **720p** if the source is higher resolution.
- Saves frames as `frame_<timestamp>.jpg`.

### `Transcriber` (Internal)
Handles audio extraction and transcription.
- Automatically detects and uses local `bin/ffmpeg.exe`.
- Returns timestamped text segments: `{"start": float, "end": float, "text": str}`.

### `KBConverter`
Transforms raw metadata into a high-level Knowledge Base using OCR and Multimodal LLM analysis.
- `__init__(model="gemma4:e2b")`: Targets the specified LLM model.
- `process_metadata(metadata_path, output_path)`: 
    1.  Runs **OCR** on every frame.
    2.  Sends **actual images (Base64)** + OCR + Audio Transcript to **Gemma** for thematic analysis.
    3.  Generates `knowledge_base.json` with `total_description` and `key_takeaways`.

## 📋 Requirements
- `opencv-python`
- `openai-whisper`
- `torch` (CPU version recommended for general use)
- `ffmpeg.exe` (must be in `core_engine/bin/`)

## 🧪 Testing
Run `pytest` from the `core_engine` directory to verify all components (Extractor, Transcriber, and Analyzer) are working.
