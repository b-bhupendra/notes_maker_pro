import cv2
import os
from .logger import get_logger
from scenedetect import detect, ContentDetector, open_video

logger = get_logger("extractor")

class FrameExtractor:
    def __init__(self, video_path, output_dir="screenshots"):
        self.video_path = video_path
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            logger.error(f"Could not open video file: {video_path}")
            raise ValueError("Invalid video path")
            
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.duration = self.total_frames / self.fps

    def _save_frame(self, frame_count, timestamp):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
        ret, frame = self.cap.read()
        if ret:
            # Resize to 720p
            h, w = frame.shape[:2]
            target_h = 720
            if h > target_h:
                aspect_ratio = w / h
                target_w = int(target_h * aspect_ratio)
                frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

            filename = os.path.join(self.output_dir, f"frame_{int(timestamp * 100) / 100}.jpg")
            cv2.imwrite(filename, frame)
            return filename, frame
        return None, None

    def extract_scenes(self, threshold=27.0):
        logger.info(f"Detecting scenes in {self.video_path} (Duration: {self.duration:.2f}s)...")
        
        # Logic Fix: If video is very short, treat as one block immediately
        if self.duration < 15.0:
            logger.info("Video under 15s. Treating as single semantic block.")
            scene_list = []
        else:
            scene_list = detect(self.video_path, ContentDetector(threshold=threshold))
        
        extracted_paths = []
        
        if not scene_list:
            # If no scenes detected or short video, treat whole video as one scene
            start_time = 0.0
            end_time = self.duration
            scene_list = [(start_time, end_time)]
        
        for i, scene in enumerate(scene_list):
            if isinstance(scene[0], float):
                start_time = scene[0]
                end_time = scene[1]
            else:
                start_time = scene[0].get_seconds()
                end_time = scene[1].get_seconds()
            
            # Extract frame at the middle of the scene
            mid_time = start_time + (end_time - start_time) / 2.0
            mid_frame_idx = int(mid_time * self.fps)
            
            logger.info(f"Scene {i+1}: {start_time:.2f}s to {end_time:.2f}s")
            path, _ = self._save_frame(mid_frame_idx, mid_time)
            
            if path:
                extracted_paths.append({
                    "time_range": [start_time, end_time],
                    "path": path,
                    "timestamp": mid_time
                })
                
        logger.info(f"Total unique scenes extracted: {len(extracted_paths)}")
        return extracted_paths

    def extract_at_intervals(self, interval_sec=10.0):
        logger.info(f"Extracting frames at {interval_sec}s intervals...")
        extracted_paths = []
        current_time = 0.0
        while current_time < self.duration:
            frame_idx = int(current_time * self.fps)
            path, _ = self._save_frame(frame_idx, current_time)
            if path:
                extracted_paths.append({
                    "time_range": [current_time, min(current_time + interval_sec, self.duration)],
                    "path": path,
                    "timestamp": current_time
                })
            current_time += interval_sec
        return extracted_paths

    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()
