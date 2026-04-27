import os
import sys
import argparse
import json
import logging

# Ensure core_engine is in path
sys.path.append(os.path.abspath("core_engine"))
from engine import VideoProcessor

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--mode", choices=["harvest", "synthesize", "full"], default="full")
    parser.add_argument("--interval", type=int, default=180)
    args = parser.parse_args()

    processor = VideoProcessor(args.video, args.out)
    
    if args.mode == "harvest":
        processor.harvest(interval_sec=args.interval)
    elif args.mode == "synthesize":
        processor.synthesize(cleanup=False)
    else:
        processor.process(interval_sec=args.interval, cleanup=False)

if __name__ == "__main__":
    main()
