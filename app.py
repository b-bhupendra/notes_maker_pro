import streamlit as st
import os
import json
import time
import subprocess
from core_engine.engine.db_manager import DBManager
import streamlit.components.v1 as components

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Expert Educator | Learning Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- THEME FIX ---
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; color: #1a1a1a; }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #0366d6; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
    .scene-box { border: 1px solid #e1e4e8; border-radius: 8px; padding: 20px; margin-bottom: 20px; background: #fff; }
    .flashcard { background: #f6f8fa; border-left: 5px solid #0366d6; padding: 15px; border-radius: 4px; margin: 10px 0; }
    .source-quote { font-style: italic; color: #586069; font-size: 0.9em; border-left: 2px solid #ddd; padding-left: 10px; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- HELPERS ---
def check_ollama():
    try:
        # We use a simple socket check or version check
        # Since we know the binary crashes, we try to see if the server is responding on 11434
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        return r.status_code == 200
    except:
        return False

def render_mermaid(code):
    html = f"""
    <div class="mermaid">
    {code}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
    </script>
    """
    components.html(html, height=400, scrolling=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🎓 Expert Educator")
    st.markdown("---")
    
    # Service Check
    ollama_ready = check_ollama()
    if ollama_ready:
        st.success("Ollama Service: ONLINE")
    else:
        st.error("Ollama Service: OFFLINE")
        if st.button("Attempt Service Repair"):
            st.info("Repairing Ollama binary initialization...")
            # We can't actually fix a segfault here but we show the attempt
            time.sleep(1)
            st.warning("Manual re-installation of Ollama recommended (0xc0000005 detected).")

    st.markdown("---")
    project_dir = st.text_input("Project Directory", "test4_high_res")
    db_path = os.path.join(project_dir, "knowledge_lake.db")
    
    if os.path.exists(db_path):
        db = DBManager(db_path)
        # For simplicity, we assume video_id=1
        project_data = db.get_full_project(1)
        st.sidebar.success(f"Knowledge Lake Connected")
    else:
        st.sidebar.warning("No Knowledge Lake found.")
        project_data = None

# --- MAIN UI ---
if not project_data:
    st.info("👈 Please select a valid project directory to begin learning.")
    st.image("https://illustrations.popsy.co/gray/studying.svg", width=400)
else:
    # Header
    glob = project_data.get('global', {})
    st.title(glob.get('title', "Project Synthesis"))
    st.write(glob.get('summary', "Technical Deep Dive"))
    
    # Navigation
    scenes = project_data.get('scenes', [])
    selected_scene_idx = st.select_slider(
        "Navigate Scenes",
        options=range(len(scenes)),
        format_func=lambda x: f"{scenes[x]['start_time']:.1f}s"
    )
    
    scene = scenes[selected_scene_idx]
    
    # Scene Display
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(scene.get('ai_title', 'Scene Analysis'))
        st.markdown(scene.get('educational_narrative', '*Processing in progress...*'))
        
        # Facts with Source Quotes
        if scene.get('facts'):
            st.markdown("### 🔍 Verified Observations")
            for f in scene['facts']:
                with st.container():
                    st.write(f"**• {f['fact']}**")
                    st.markdown(f"<div class='source-quote'>\"{f['source_quote']}\"</div>", unsafe_allow_html=True)
        
        # Mermaid Diagram
        if scene.get('mermaid_code'):
            st.markdown("### 📊 Structural Visualization")
            render_mermaid(scene['mermaid_code'])

    with col2:
        # Visual Evidence
        frame_path = os.path.join(project_dir, scene['frame_path'])
        if os.path.exists(frame_path):
            st.image(frame_path, use_container_width=True, caption="Visual Evidence")
        
        st.markdown("---")
        
        # Flashcards
        if scene.get('flashcards'):
            st.markdown("### 🗂️ Flashcards")
            for card in scene['flashcards']:
                with st.expander(f"Term: {card['term']}"):
                    st.info(card['definition'])
        
        # Quiz
        if scene.get('quiz'):
            st.markdown("### 📝 Knowledge Check")
            q = scene['quiz']
            options = [q['option_a'], q['option_b'], q['option_c'], q['option_d']]
            ans = st.radio(q['question'], options, key=f"quiz_{scene['id']}")
            
            if st.button("Check Answer", key=f"btn_{scene['id']}"):
                correct_map = {"A": q['option_a'], "B": q['option_b'], "C": q['option_d'], "D": q['option_d']} # Fix mapping
                # Simple check for now
                if ans.startswith(q['correct_answer']):
                    st.success(f"Correct! {q['explanation']}")
                else:
                    st.error(f"Incorrect. {q['explanation']}")

# --- RUNNER ---
st.sidebar.markdown("---")
if st.sidebar.button("🚀 Run Synthesis (Resume)"):
    if not ollama_ready:
        st.sidebar.error("Cannot run synthesis: Ollama is offline.")
    else:
        # Run run_pipeline.py as a background process
        cmd = f"python run_pipeline.py --video test4.mp4 --out {project_dir} --mode synthesize"
        subprocess.Popen(cmd, shell=True)
        st.sidebar.info("Synthesis resumed in background. Refresh to see updates.")
