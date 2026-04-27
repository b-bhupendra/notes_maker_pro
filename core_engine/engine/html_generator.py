import json
import os
import markdown
import re

class HTMLGenerator:
    def __init__(self, title="Video Knowledge Notes"):
        self.title = title
        # Clinical CSS for "Hygienic" notes
        self.css = """
        :root {
            --bg-color: #ffffff;
            --sidebar-bg: #f8f9fa;
            --text-color: #1a1a1a;
            --text-muted: #5f6368;
            --border-color: #e0e0e0;
            --accent-color: #0366d6;
            --font-main: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --font-mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
            --sidebar-width: 300px;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: var(--font-main);
            margin: 0;
            padding: 0;
            display: flex;
            height: 100vh;
            overflow: hidden;
            line-height: 1.6;
        }

        .sidebar {
            width: var(--sidebar-width);
            background-color: var(--sidebar-bg);
            border-right: 1px solid var(--border-color);
            height: 100%;
            overflow-y: auto;
            padding: 24px;
            box-sizing: border-box;
        }

        .sidebar h3 {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-top: 0;
            margin-bottom: 16px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 8px;
        }

        .toc-item {
            padding: 8px 12px;
            margin-bottom: 4px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            border: 1px solid transparent;
            transition: all 0.15s;
        }

        .toc-item:hover { background: #f1f3f4; }
        .toc-item.active { background: #e8f0fe; color: var(--accent-color); border: 1px solid #d2e3fc; font-weight: 600;}

        .toc-timestamp {
            font-family: var(--font-mono);
            font-size: 0.8rem;
            display: block;
            color: var(--text-muted);
        }

        .main-content {
            flex: 1;
            overflow-y: auto;
            padding: 48px;
            scroll-behavior: smooth;
        }

        .container { max-width: 900px; margin: 0 auto; }

        h1 { font-size: 2.5rem; font-weight: 700; margin-bottom: 48px; border-bottom: 2px solid var(--border-color); padding-bottom: 16px;}
        h2 { font-size: 1.5rem; font-weight: 600; margin-top: 0; margin-bottom: 16px; color: var(--accent-color); }
        h4 { font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-top: 24px; margin-bottom: 12px; }

        .hygienic-box {
            background-color: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 40px;
            margin-bottom: 48px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            position: relative;
        }

        .timestamp-badge {
            display: inline-block;
            background: var(--sidebar-bg);
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 0.75rem;
            padding: 4px 12px;
            border-radius: 20px;
            border: 1px solid var(--border-color);
            margin-bottom: 20px;
        }

        .evidence-grid {
            display: grid;
            grid-template-columns: 1.5fr 1fr;
            gap: 32px;
            margin-top: 24px;
        }

        .narrative-text {
            font-size: 1.05rem;
            color: #333;
        }

        .visual-evidence {
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid var(--border-color);
            background: #f1f3f4;
        }

        .visual-evidence img {
            width: 100%;
            height: auto;
            display: block;
        }

        .definition-grid {
            display: grid;
            grid-template-columns: 120px 1fr;
            gap: 8px 16px;
            margin-top: 24px;
            font-size: 0.9rem;
            border-top: 1px solid var(--border-color);
            padding-top: 24px;
        }

        .def-term { font-weight: 700; color: var(--text-color); }
        .def-desc { color: var(--text-muted); }

        .mermaid { margin-top: 32px; background: #fdfdfd; padding: 20px; border-radius: 8px; border: 1px solid var(--border-color); }
        
        .animated-explainer-box {
            margin-top: 32px;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            background: #fafafa;
        }
        
        .replay-btn {
            background: #fff;
            border: 1px solid #ddd;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin: 10px;
        }

        .animation-container { padding: 20px; display: flex; justify-content: center; }

        .research-box {
            background-color: #f0f7ff;
            border: 1px solid #c2e0ff;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 32px;
        }
        """

        self.js = """
        function scrollToScene(id) {
            const el = document.getElementById(id);
            if (el) el.scrollIntoView({ behavior: 'smooth' });
        }

        window.addEventListener('scroll', () => {
            let current = "";
            document.querySelectorAll('.hygienic-box').forEach(scene => {
                const sectionTop = scene.offsetTop;
                if (document.querySelector('.main-content').scrollTop >= sectionTop - 100) {
                    current = scene.getAttribute('id');
                }
            });
            
            document.querySelectorAll('.toc-item').forEach(item => {
                item.classList.remove('active');
                if (item.getAttribute('onclick').includes(current)) {
                    item.classList.add('active');
                }
            });
        });

        function replayAnimation(btn) {
            const container = btn.closest('.animated-explainer-box').querySelector('.animation-container');
            if (!container) return;
            const svg = container.querySelector('svg');
            if (svg) {
                const clone = svg.cloneNode(true);
                svg.replaceWith(clone);
            }
        }
        """

    def _markdown_to_html(self, text):
        if not text: return ""
        return markdown.markdown(str(text), extensions=['tables', 'fenced_code'])

    def _get_base64_image(self, path):
        import base64
        if not os.path.exists(path): return ""
        try:
            with open(path, "rb") as img_file:
                ext = path.split(".")[-1]
                encoded = base64.b64encode(img_file.read()).decode('utf-8')
                return f"data:image/{ext};base64,{encoded}"
        except: return ""

    def generate(self, kb_path, output_html="visual_notes.html", global_context_path=None):
        if not os.path.exists(kb_path): return False
        with open(kb_path, "r") as f: data = json.load(f)
        
        kb_dir = os.path.dirname(kb_path)

        toc_html = "<h3>Contents</h3>"
        for i, scene in enumerate(data):
            summary = scene.get("core_assertion", "Scene Analysis")
            if len(summary) > 40: summary = summary[:40] + "..."
            toc_html += f'<div class="toc-item" onclick="scrollToScene(\'scene-{i}\')"><span class="toc-timestamp">{scene.get("time_range",[0,0])[0]:.2f}s</span>{summary}</div>'

        scenes_html = ""
        for i, scene in enumerate(data):
            toc_id = f"scene-{i}"
            narrative = self._markdown_to_html(scene.get("technical_narrative", ""))
            
            # Resolve and Embed Image
            rel_img_path = scene.get("frame_path", "")
            abs_img_path = os.path.join(kb_dir, rel_img_path) if rel_img_path else ""
            b64_img = self._get_base64_image(abs_img_path)
            
            scenes_html += f"""
            <div class="hygienic-box" id="{toc_id}">
                <div class="timestamp-badge">{scene.get('time_range',[0,0])[0]:.2f}s - {scene.get('time_range',[0,0])[1]:.2f}s</div>
                <h2>{scene.get('core_assertion', 'Technical Analysis')}</h2>
                
                <div class="evidence-grid">
                    <div class="narrative-text">{narrative}</div>
                    <div class="visual-evidence">
                        {f'<img src="{b64_img}" alt="Visual Evidence">' if b64_img else '<div style="padding:40px; text-align:center; color:#ccc;">No Visual Data</div>'}
                    </div>
                </div>
            """
            
            defs = scene.get("definitions", [])
            if defs:
                scenes_html += "<div class='definition-grid'>"
                for d in defs: scenes_html += f"<div class='def-term'>{d.get('term','')}</div><div class='def-desc'>{d.get('definition','')}</div>"
                scenes_html += "</div>"
                
            visuals = scene.get("visual_elements", [])
            for vis in visuals:
                if vis.get("type") == "diagram":
                    scenes_html += f'<div class="mermaid">{vis.get("mermaid_code","")}</div>'
                elif vis.get("type") == "animated_explainer":
                    scenes_html += f'<div class="animated-explainer-box"><button onclick="replayAnimation(this)" class="replay-btn">&#x1F504; Replay</button><div class="animation-container">{vis.get("svg_code","")}</div></div>'
            
            scenes_html += "</div>"

        # Global Section
        global_html = ""
        if global_context_path and os.path.exists(global_context_path):
            with open(global_context_path, "r") as f: gdata = json.load(f)
            global_html = f'<div class="research-box"><h1>{gdata.get("title", "Project Synthesis")}</h1><p>{gdata.get("description", "")}</p></div>'

        full_html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{self.title}</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{ startOnLoad: true, theme: 'neutral', look: 'classic', flowchart: {{ curve: 'stepBefore' }} }});
        </script>
        <style>{self.css}</style></head><body>
        <div class="sidebar">{toc_html}</div>
        <div class="main-content"><div class="container">{global_html}{scenes_html}</div></div>
        <script>{self.js}</script></body></html>"""
        
        with open(output_html, "w", encoding="utf-8") as f: f.write(full_html)
        return True
