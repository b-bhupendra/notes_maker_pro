import streamlit as st
import os
import sys
import json
import time
import subprocess
from datetime import datetime

# Page Config
st.set_page_config(
    page_title="Animator Assistant | Data Lake Dashboard",
    page_icon="🎬",
    layout="wide"
)

# Custom Styling
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; }
    .status-panel { padding: 1rem; border: 1px solid #eee; border-radius: 8px; background: #fafafa; margin-bottom: 1rem;}
    .report-frame { border: 1px solid #ddd; border-radius: 8px; width: 100%; height: 800px; }
    </style>
    """, unsafe_allow_html=True)

# Initialization
if 'project_dir' not in st.session_state:
    st.session_state.project_dir = "output/default"

def get_status():
    status_path = os.path.join(st.session_state.project_dir, "status.json")
    if os.path.exists(status_path):
        try:
            with open(status_path, "r") as f:
                return json.load(f)
        except: return None
    return None

# Sidebar: Environment & Settings
with st.sidebar:
    st.title("🎬 Animator Assistant")
    st.markdown("---")
    
    st.subheader("Project Settings")
    video_file = st.file_uploader("Upload Video Source", type=["mp4"])
    interval = st.slider("Sampling Interval (sec)", 30, 600, 180)
    
    if video_file:
        project_name = video_file.name.replace(".mp4", "")
        st.session_state.project_dir = f"output/{project_name}"
        if not os.path.exists(st.session_state.project_dir):
            os.makedirs(st.session_state.project_dir)
            # Save the video to the project dir
            with open(os.path.join(st.session_state.project_dir, "source.mp4"), "wb") as f:
                f.write(video_file.getbuffer())

    st.markdown("---")
    st.info(f"Working Directory: `{st.session_state.project_dir}`")

# Main Dashboard
col1, col2 = st.columns([1, 2])

with col1:
    st.header("Temporal Controls")
    st.write("Modularize your pipeline to iterate faster.")
    
    # Check if Harvest Data exists
    lake_path = os.path.join(st.session_state.project_dir, "project_data.json")
    lake_exists = os.path.exists(lake_path)
    
    # 1. Harvest Phase
    st.subheader("Module 1: The Harvester")
    st.caption("Extracts frames, audio, and transcript. (Deterministic)")
    if st.button("🔥 Run Harvester", disabled=not video_file):
        cmd = [sys.executable, "run_pipeline.py", "--video", os.path.join(st.session_state.project_dir, "source.mp4"), "--out", st.session_state.project_dir, "--mode", "harvest", "--interval", str(interval)]
        subprocess.Popen(cmd)
        st.rerun()

    # 2. Synthesize Phase
    st.subheader("Module 2: The Synthesizer")
    st.caption("Applies AI Synthesis & Research. (Generative)")
    if st.button("🧠 Run Synthesizer", disabled=not lake_exists):
        cmd = [sys.executable, "run_pipeline.py", "--video", "none", "--out", st.session_state.project_dir, "--mode", "synthesize"]
        subprocess.Popen(cmd)
        st.rerun()

    st.markdown("---")
    
    # Progress Polling
    status = get_status()
    if status:
        st.subheader("Live Telemetry")
        st.progress(status.get("percent", 0) / 100.0)
        st.code(f"{status.get('message', 'Idle')}")
        if status.get("percent", 0) < 100:
            time.sleep(1)
            st.rerun()

with col2:
    st.header("Visual Evidence Notes")
    
    notes_path = os.path.join(st.session_state.project_dir, "visual_notes.html")
    if os.path.exists(notes_path):
        st.success("Materialized Knowledge Base Ready.")
        with open(notes_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            # Inject base path for images
            # Streamlit serves static files weirdly, but if we run from root, relative paths should work in iframe if we use the right approach.
            st.components.v1.html(html_content, height=1000, scrolling=True)
    else:
        st.info("Awaiting synthesis... Run Module 1 & 2 to generate notes.")
        if lake_exists:
            st.warning("Harvest data found! Run 'Synthesizer' to generate the clinical notes.")
