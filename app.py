import streamlit as st
import os
import sys
import json
import time
import sqlite3
import subprocess
from datetime import datetime

# Page Config
st.set_page_config(
    page_title="Animator Assistant | Relational Knowledge Lake",
    page_icon="🎬",
    layout="wide"
)

# Custom Styling (Light Mode Force)
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; }
    .status-panel { padding: 1rem; border: 1px solid #eee; border-radius: 8px; background: #fafafa; margin-bottom: 1rem;}
    .report-frame { border: 1px solid #ddd; border-radius: 8px; width: 100%; height: 800px; }
    .db-card { padding: 1rem; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 0.5rem; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

# Initialization
if 'project_root' not in st.session_state:
    st.session_state.project_root = "output"
    if not os.path.exists("output"): os.makedirs("output")

DB_PATH = os.path.join(st.session_state.project_root, "knowledge_lake.db")

def get_db_videos():
    if not os.path.exists(DB_PATH): return []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()
    except: return []

def get_status(project_dir):
    status_path = os.path.join(project_dir, "status.json")
    if os.path.exists(status_path):
        try:
            with open(status_path, "r") as f: return json.load(f)
        except: return None
    return None

# Sidebar: Knowledge Lake Explorer
with st.sidebar:
    st.title("🎬 Animator Assistant")
    st.markdown("---")
    
    st.subheader("Knowledge Lake Explorer")
    videos = get_db_videos()
    if not videos:
        st.info("Knowledge Lake is empty.")
    for v in videos:
        with st.container():
            st.markdown(f"""
            <div class='db-card'>
                <b>{v['filename']}</b><br/>
                Status: <span style='color: {"#0366d6" if v["status"]=="completed" else "#ff9800"}'>{v['status']}</span><br/>
                <small>{v['created_at']}</small>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Load", key=f"load_{v['id']}"):
                st.session_state.current_video = v['filename']
                st.session_state.project_dir = os.path.join(st.session_state.project_root, v['filename'].replace(".mp4", ""))
    
    st.markdown("---")
    st.subheader("New Project")
    video_file = st.file_uploader("Upload Video Source", type=["mp4"])
    interval = st.slider("Sampling Interval (sec)", 30, 600, 180)
    
    if video_file:
        project_name = video_file.name.replace(".mp4", "")
        st.session_state.project_dir = os.path.join(st.session_state.project_root, project_name)
        if not os.path.exists(st.session_state.project_dir):
            os.makedirs(st.session_state.project_dir)
            # Save the video
            with open(os.path.join(st.session_state.project_dir, "source.mp4"), "wb") as f:
                f.write(video_file.getbuffer())
        st.session_state.current_video = video_file.name

# Main Dashboard
col1, col2 = st.columns([1, 2.5])

with col1:
    st.header("Relational Pipeline")
    if 'current_video' in st.session_state:
        st.write(f"Current Video: **{st.session_state.current_video}**")
        
        lake_path = os.path.join(st.session_state.project_dir, "project_data.json")
        lake_exists = os.path.exists(lake_path)
        
        st.subheader("Module 1: The Harvester")
        if st.button("🔥 Run Harvester"):
            source_path = os.path.join(st.session_state.project_dir, "source.mp4")
            cmd = [sys.executable, "run_pipeline.py", "--video", source_path, "--out", st.session_state.project_dir, "--mode", "harvest", "--interval", str(interval)]
            
            # FIX: Redirect to file to prevent Pipe Deadlock
            log_path = os.path.join(st.session_state.project_dir, "pipeline_execution.log")
            with open(log_path, "a") as log_file:
                subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
            st.rerun()

        st.subheader("Module 2: The Synthesizer")
        if st.button("🧠 Run Synthesizer"):
            source_path = os.path.join(st.session_state.project_dir, "source.mp4")
            cmd = [sys.executable, "run_pipeline.py", "--video", source_path, "--out", st.session_state.project_dir, "--mode", "synthesize"]
            
            # FIX: Redirect to file to prevent Pipe Deadlock
            log_path = os.path.join(st.session_state.project_dir, "pipeline_execution.log")
            with open(log_path, "a") as log_file:
                subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT)
            st.rerun()

        # Telemetry
        status = get_status(st.session_state.project_dir)
        if status:
            st.markdown("---")
            st.subheader("Live Telemetry")
            st.progress(status.get("percent", 0) / 100.0)
            st.code(f"{status.get('message', 'Idle')}")
            if status.get("percent", 0) < 100:
                time.sleep(1)
                st.rerun()
    else:
        st.info("Upload a video or select one from the Knowledge Lake to begin.")

with col2:
    st.header("Clinical Knowledge Base")
    
    if 'project_dir' in st.session_state:
        notes_path = os.path.join(st.session_state.project_dir, "visual_notes.html")
        if os.path.exists(notes_path):
            with open(notes_path, "r", encoding="utf-8") as f:
                html_content = f.read()
                st.components.v1.html(html_content, height=1000, scrolling=True)
        else:
            st.info("Visual notes not yet materialized for this project.")
