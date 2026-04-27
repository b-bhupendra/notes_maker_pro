import streamlit as st
import os
import sys
import json
import time
import subprocess
import threading
import logging
from datetime import datetime

# Ensure core_engine is in path
sys.path.append(os.path.abspath("core_engine"))
from engine import VideoProcessor

# Page Config
st.set_page_config(
    page_title="Animator Assistant | Hygienic Video Intelligence",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium/Clinical Look
st.markdown("""
    <style>
    .stApp {
        background-color: #ffffff;
    }
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3rem;
        background-color: #0366d6;
        color: white;
        border: none;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #0255b3;
    }
    .status-card {
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        background-color: #f8f9fa;
        margin-bottom: 1rem;
    }
    .log-container {
        background-color: #1a1a1a;
        color: #00ff00;
        font-family: 'Courier New', Courier, monospace;
        padding: 1rem;
        border-radius: 4px;
        height: 300px;
        overflow-y: scroll;
        font-size: 0.85rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Session State for Logs
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'output_ready' not in st.session_state:
    st.session_state.output_ready = False

class StreamlitLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        st.session_state.logs.append(msg)
        # Handle Progress indicators
        if "[PROGRESS" in msg:
            try:
                percent = int(msg.split("[PROGRESS ")[1].split("%]")[0])
                st.session_state.progress = percent
            except: pass

# Sidebar
with st.sidebar:
    st.image("https://www.svgrepo.com/show/303108/google-photos-logo.svg", width=50) # Just a placeholder icon
    st.title("Animator Assistant")
    st.markdown("---")
    
    st.subheader("System Status")
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=2)
        if resp.status_code == 200:
            st.success("Ollama: ONLINE")
        else:
            st.error("Ollama: UNSTABLE")
    except:
        st.error("Ollama: OFFLINE")
        
    try:
        import torch
        if torch.cuda.is_available():
            st.success(f"CUDA: {torch.cuda.get_device_name(0)}")
        else:
            st.warning("CUDA: NOT FOUND")
    except:
        st.warning("CUDA: UNKNOWN")
        
    st.markdown("---")
    st.subheader("Settings")
    interval = st.slider("Sampling Interval (sec)", 30, 300, 180)
    enable_research = st.checkbox("Autonomous Research (Internet)", value=True)
    cleanup = st.checkbox("Cleanup Temp Files", value=True)

# Main UI
st.header("🎬 Hygienic Video Intelligence Dashboard")
st.markdown("Transform clinical video data into structured, animated knowledge bases.")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Input Stream")
    uploaded_file = st.file_uploader("Upload MP4 Video", type=["mp4"])
    
    if uploaded_file:
        # Save uploaded file temporarily
        temp_path = os.path.join("temp_uploads", uploaded_file.name)
        if not os.path.exists("temp_uploads"): os.makedirs("temp_uploads")
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.video(temp_path)
        
        if st.button("Start Neural Processing"):
            st.session_state.processing = True
            st.session_state.logs = []
            st.session_state.progress = 0
            
            # Start Processing in a thread
            output_folder = f"notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            def run_pipeline():
                # Setup custom logger
                logger = logging.getLogger("processor")
                handler = StreamlitLogHandler()
                logger.addHandler(handler)
                
                try:
                    processor = VideoProcessor(temp_path, output_folder)
                    processor.process(interval_sec=interval, cleanup=cleanup)
                    st.session_state.output_path = os.path.join(output_folder, "visual_notes.html")
                    st.session_state.output_ready = True
                except Exception as e:
                    st.session_state.logs.append(f"[ERROR] {str(e)}")
                finally:
                    st.session_state.processing = False

            thread = threading.Thread(target=run_pipeline)
            thread.start()

with col2:
    st.subheader("Processing Insight")
    
    if st.session_state.processing:
        progress_val = st.session_state.get('progress', 0)
        st.progress(progress_val / 100.0)
        st.info(f"Pipeline active... Current phase: {st.session_state.logs[-1] if st.session_state.logs else 'Initializing'}")
        
    # Log Terminal
    st.markdown("<div class='log-container'>", unsafe_allow_html=True)
    for log in st.session_state.logs[-15:]:
        st.text(log)
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.session_state.output_ready:
        st.success("✅ Knowledge Base Materialized!")
        if st.button("Open Visual Notes"):
            # Use streamlit-to-html or just show the path
            st.info(f"File generated at: {st.session_state.output_path}")
            # Try to show in iframe if possible
            with open(st.session_state.output_path, "r", encoding="utf-8") as f:
                html_content = f.read()
                st.components.v1.html(html_content, height=800, scrolling=True)

if not st.session_state.processing and st.session_state.output_ready:
    st.balloons()
