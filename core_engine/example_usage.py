from engine import VideoProcessor
import sys

def main_feedback_callback(message):
    """
    This callback allows the main application to receive updates 
    from the engine submodule.
    """
    print(f"[MAIN APP FEEDBACK]: {message}")

def main():
    video_path = "path/to/your/video.mp4" # Replace with actual path
    
    # Check if a path was provided as argument
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        print("Usage: python example_usage.py <video_path>")
        print("Using dummy path for demonstration purposes.")

    try:
        # Initialize processor with a callback for feedback
        processor = VideoProcessor(
            video_path=video_path,
            output_dir="my_notes_data",
            model_size="base", # Use 'base' for faster offline testing
            callback=main_feedback_callback
        )
        
        # Process video (extract 5 frames and transcribe)
        result = processor.process(num_frames=5)
        
        print("\nProcessing complete!")
        print(f"Extracted {len(result['frames'])} frames.")
        print(f"Transcribed {len(result['transcript'])} audio segments.")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
