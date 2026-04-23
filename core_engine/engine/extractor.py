import cv2
import os
from .logger import get_logger

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
        
    def _save_frame(self, frame_count, timestamp, last_frame=None):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
        ret, frame = self.cap.read()
        if ret:
            # Resize to 540p
            h, w = frame.shape[:2]
            target_h = 540
            if h > target_h:
                aspect_ratio = w / h
                target_w = int(target_h * aspect_ratio)
                frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

            # Change Detection: Check if this frame is significantly different from the last one
            if last_frame is not None:
                diff = cv2.absdiff(frame, last_frame)
                non_zero_count = cv2.countNonZero(cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY))
                similarity = 1.0 - (non_zero_count / (frame.shape[0] * frame.shape[1]))
                if similarity > 0.98: # 98% similar means it's likely the same slide
                    return None, frame

            filename = os.path.join(self.output_dir, f"frame_{int(timestamp * 100) / 100}.jpg")
            cv2.imwrite(filename, frame)
            return filename, frame
        return None, None

    def extract_with_interval(self, interval_sec=0.5):
        logger.info(f"Extracting frames every {interval_sec}s from {self.video_path}...")
        extracted_paths = []
        last_frame_data = None
        
        # Calculate frame step
        step = int(interval_sec * self.fps)
        if step < 1: step = 1
        
        for frame_idx in range(0, self.total_frames, step):
            timestamp = frame_idx / self.fps
            path, last_frame_data = self._save_frame(frame_idx, timestamp, last_frame_data)
            if path:
                extracted_paths.append({"timestamp": timestamp, "path": path})
                if len(extracted_paths) % 10 == 0:
                    logger.info(f"Extracted {len(extracted_paths)} unique frames so far...")
        
        return extracted_paths

    def extract_n_frames(self, n):
        logger.info(f"Extracting {n} frames from {self.video_path}...")
        interval = self.total_frames // (n + 1)
        extracted_paths = []
        last_frame_data = None
        
        for i in range(1, n + 1):
            frame_idx = i * interval
            timestamp = frame_idx / self.fps
            path, last_frame_data = self._save_frame(frame_idx, timestamp, last_frame_data)
            if path:
                extracted_paths.append({"timestamp": timestamp, "path": path})
                logger.info(f"Extracted frame {i}/{n} at {timestamp:.2f}s")
        
        return extracted_paths

    def extract_at_timestamps(self, timestamps):
        logger.info(f"Extracting frames at specific timestamps: {timestamps}")
        extracted_paths = []
        for ts in timestamps:
            frame_idx = int(ts * self.fps)
            if frame_idx < self.total_frames:
                path, _ = self._save_frame(frame_idx, ts)
                if path:
                    extracted_paths.append({"timestamp": ts, "path": path})
                    logger.info(f"Extracted frame at {ts:.2f}s")
        return extracted_paths

    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()
