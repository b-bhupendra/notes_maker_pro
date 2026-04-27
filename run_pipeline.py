import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys
import argparse
import json
import logging

# Ensure core_engine is in path
sys.path.append(os.path.abspath("."))
from core_engine.engine import VideoProcessor

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--mode", choices=["harvest", "synthesize", "full"], default="full")
    parser.add_argument("--interval", type=int, default=180)
    args = parser.parse_args()

    processor = VideoProcessor(args.video, args.out)
    
    # In the new DB architecture, we always start by registering/harvesting to get a video_id
    # even if harvest is already done, harvest() will return the existing video_id
    video_id = processor.harvest(interval_sec=args.interval)
    
    if args.mode == "harvest":
        # Already done by harvest() call above
        print(f"Harvest complete for Video ID: {video_id}")
    elif args.mode == "synthesize":
        processor.synthesize(video_id, cleanup=False)
    else:
        processor.synthesize(video_id, cleanup=False)

if __name__ == "__main__":
    main()
