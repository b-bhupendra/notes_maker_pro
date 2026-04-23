from engine.extractor import FrameExtractor
import os

video_path = "test_video.mp4"
output_dir = "test_frames"

if not os.path.exists(video_path):
    print(f"Error: {video_path} not found.")
else:
    print(f"Testing frame extraction on {video_path}...")
    extractor = FrameExtractor(video_path, output_dir=output_dir)
    frames = extractor.extract_n_frames(3)
    print(f"Successfully extracted {len(frames)} frames to {output_dir}/")
    for f in frames:
        print(f" - {f['path']} at {f['timestamp']:.2f}s")
