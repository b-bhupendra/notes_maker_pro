import sys
import os
import json

# Add core_engine to path so we can import the engine
sys.path.append(os.path.join(os.getcwd(), "core_engine"))

try:
    from engine import VideoProcessor
except ImportError:
    print("Error: Could not find the engine in core_engine/ folder.")
    sys.exit(1)

def main():
    video_path = "test3.mp4"
    output_dir = "test_video_output"
    
    if not os.path.exists(video_path):
        print(f"Error: {video_path} not found in the current directory.")
        return

    # Pre-run cleanup: Ensure a fresh start
    if os.path.exists(output_dir):
        print(f"Cleaning up previous results in {output_dir}...")
        import shutil
        shutil.rmtree(output_dir)

    print(f"Processing {video_path}...")
    
    # Initialize processor with small model
    processor = VideoProcessor(
        video_path=video_path,
        output_dir=output_dir,
        model_size="small"
    )
    
    # Process (1s interval + automatic KB + cleanup)
    try:
        # cleanup=True will delete the massive 'frames/' folder after KB is done
        # interval_sec=1.0 for better speed, max_workers handles parallel LLM calls
        result = processor.process(interval_sec=1.0, cleanup=True)
        print(f"Success! Knowledge Base generated at {output_dir}/knowledge_base.json")
        
    except Exception as e:
        print(f"Processing failed: {e}")

if __name__ == "__main__":
    main()
