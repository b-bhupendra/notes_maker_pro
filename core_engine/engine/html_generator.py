import json
import os
import markdown
import re

class HTMLGenerator:
    def __init__(self, title="Video Knowledge Notes"):
        self.title = title
        # Updated CSS for two-column layout and paper aesthetic
        self.css = """
        :root {
            --bg-color: #fdfaf3; /* Paper-like background */
            --sidebar-bg: #f5f0e6;
            --text-color: #2c3e50;
            --accent-color: #6c5ce7;
            --accent-green: #00b894;
            --card-bg: #ffffff;
            --border-color: #dcdde1;
            --font-hand: 'Caveat', cursive;
            --font-ui: 'Inter', sans-serif;
            --sidebar-width: 280px;
        }

        body {
            background-color: var(--bg-color);
            background-image: url("https://www.transparenttextures.com/patterns/paper-fibers.png");
            color: var(--text-color);
            font-family: var(--font-ui);
            margin: 0;
            padding: 0;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        /* Sidebar Styling */
        .sidebar {
            width: var(--sidebar-width);
            background-color: var(--sidebar-bg);
            border-right: 2px solid var(--border-color);
            height: 100%;
            overflow-y: auto;
            padding: 20px;
            box-sizing: border-box;
            box-shadow: 2px 0 10px rgba(0,0,0,0.05);
        }

        .sidebar h3 {
            font-family: var(--font-hand);
            font-size: 2rem;
            margin-top: 0;
            border-bottom: 2px solid var(--accent-color);
            padding-bottom: 10px;
        }

        .toc-item {
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid transparent;
            font-size: 0.9rem;
        }

        .toc-item:hover {
            background: white;
            border-color: var(--accent-color);
            transform: translateX(5px);
        }

        .toc-item.active {
            background: var(--accent-color);
            color: white;
        }

        .toc-timestamp {
            font-family: monospace;
            font-weight: bold;
            display: block;
            color: var(--accent-color);
        }
        .toc-item.active .toc-timestamp { color: white; }

        /* Main Content Styling */
        .main-content {
            flex: 1;
            overflow-y: auto;
            padding: 40px 60px;
            scroll-behavior: smooth;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
        }

        h1, h2, h3 {
            font-family: var(--font-hand);
            color: var(--accent-color);
            font-weight: 700;
        }

        h1 { font-size: 4rem; text-align: center; margin-bottom: 40px; }
        h2 { font-size: 2.8rem; margin-top: 50px; border-bottom: 1px dashed var(--border-color); }

        .sketchy-box {
            background-color: var(--card-bg);
            border: 2px solid var(--border-color);
            border-radius: 255px 15px 225px 15px / 15px 225px 15px 255px; 
            padding: 30px;
            margin-bottom: 40px;
            box-shadow: 8px 8px 0px rgba(0,0,0,0.05);
            position: relative;
        }

        .timestamp-badge {
            position: absolute;
            top: -15px;
            left: 20px;
            background: var(--accent-color);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
            font-family: monospace;
        }

        .mermaid {
            background-color: #f9f9f9;
            border: 1px solid var(--border-color);
            padding: 20px;
            margin: 20px 0;
            border-radius: 10px;
        }

        .svg-illustration {
            text-align: center;
            margin: 20px 0;
        }
        .svg-illustration svg {
            max-width: 100%;
            height: auto;
            filter: drop-shadow(2px 2px 2px rgba(0,0,0,0.1));
        }

        .markdown-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .markdown-content th, .markdown-content td {
            border: 1px solid var(--border-color);
            padding: 12px;
            text-align: left;
        }
        .markdown-content th { background: #f8f9fa; }

        .highlight {
            background: rgba(108, 92, 231, 0.1);
            padding: 2px 8px;
            border-radius: 4px;
            color: var(--accent-color);
            font-weight: 500;
        }

        .research-block {
            background: rgba(0, 184, 148, 0.05);
            border-left: 5px solid var(--accent-green);
            padding: 20px;
            margin: 20px 0;
            border-radius: 0 15px 15px 0;
        }

        .animated-explainer-box {
            background: #2c3e50; /* Dark contrast to make sketchy SVG pop */
            border-radius: 15px;
            padding: 40px;
            margin: 20px 0;
            position: relative;
            text-align: center;
            box-shadow: inset 0 0 20px rgba(0,0,0,0.3);
        }
        .animated-explainer-box svg {
            max-width: 100%;
            height: auto;
        }
        .replay-btn {
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(255,255,255,0.1);
            color: white;
            border: 1px solid rgba(255,255,255,0.2);
            padding: 5px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
            transition: all 0.2s;
            z-index: 10;
        }
        .replay-btn:hover { background: rgba(255,255,255,0.2); }
        .explainer-caption {
            color: #bdc3c7;
            font-size: 0.9rem;
            margin-top: 15px;
            font-style: italic;
        }
        """

        self.js = """
        function scrollToScene(id) {
            const element = document.getElementById(id);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                // Update active state in sidebar
                document.querySelectorAll('.toc-item').forEach(item => item.classList.remove('active'));
                const activeItem = document.querySelector(`[onclick="scrollToScene('${id}')"]`);
                if (activeItem) activeItem.classList.add('active');
            }
        }

        // Highlight TOC as we scroll
        document.querySelector('.main-content').addEventListener('scroll', () => {
            const scenes = document.querySelectorAll('.sketchy-box');
            let current = "";
            scenes.forEach(scene => {
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
            const container = btn.closest('.animated-explainer-box');
            const svg = container.querySelector('svg');
            if (svg) {
                const newSvg = svg.cloneNode(true);
                svg.parentNode.replaceChild(newSvg, svg);
            }
        }
        """

    def _markdown_to_html(self, text):
        if not text: return ""
        return markdown.markdown(str(text), extensions=['tables', 'fenced_code'])

    def generate(self, kb_path, output_html="visual_notes.html", global_context_path=None):
        if not os.path.exists(kb_path):
            return False

        with open(kb_path, "r") as f:
            data = json.load(f)

        # Build Global Section
        global_html = self._generate_global_section(global_context_path)
        
        # Build TOC
        toc_html = "<h3>Contents</h3>"
        for i, scene in enumerate(data):
            time_range = scene.get("time_range", [0, 0])
            summary = scene.get("summary", "Scene Analysis")
            if len(summary) > 40: summary = summary[:40] + "..."
            toc_id = f"scene-{i}"
            toc_html += f"""
            <div class="toc-item" onclick="scrollToScene('{toc_id}')">
                <span class="toc-timestamp">{time_range[0]:.2f}s - {time_range[1]:.2f}s</span>
                {summary}
            </div>
            """

        # Build Main Content
        scenes_html = ""
        for i, scene in enumerate(data):
            toc_id = f"scene-{i}"
            time_range = scene.get("time_range", [0, 0])
            time_label = f"{time_range[0]:.2f}s - {time_range[1]:.2f}s"
            
            scenes_html += f"""
            <div class="sketchy-box" id="{toc_id}">
                <div class="timestamp-badge">{time_label}</div>
                <h2>{scene.get('summary', 'Scene Analysis')}</h2>
            """
            
            # Key Concepts
            concepts = scene.get("key_concepts", [])
            if concepts:
                scenes_html += "<div style='margin-bottom: 20px;'>"
                scenes_html += " ".join([f"<span class='highlight'>#{c}</span>" for c in concepts])
                scenes_html += "</div>"
                
            # Details
            details = scene.get("detailed_explanations", "")
            if details:
                scenes_html += f"<div class='markdown-content'>{self._markdown_to_html(details)}</div>"
                
            # Visuals
            visuals = scene.get("visual_elements", [])
            for vis in visuals:
                if vis.get("type") == "diagram":
                    code = vis.get("mermaid_code", "")
                    if code:
                        scenes_html += f'<div class="mermaid">{code}</div>'
                elif vis.get("type") == "svg_illustration":
                    svg_code = vis.get("svg_code", "")
                    if svg_code:
                        scenes_html += f'<div class="svg-illustration">{svg_code}</div>'
                elif vis.get("type") == "animated_explainer":
                    svg_code = vis.get("svg_code", "")
                    if svg_code:
                        scenes_html += f'''
                        <div class="animated-explainer-box" style="background:#1e1e1e; padding:20px; border-radius:10px; margin:20px 0; position:relative;">
                            <button onclick="this.nextElementSibling.innerHTML = this.nextElementSibling.innerHTML" 
                                    style="position:absolute; top:10px; right:10px; cursor:pointer; background:var(--accent-color); color:white; border:none; padding:5px 10px; border-radius:5px;">
                                🔄 Replay
                            </button>
                            <div class="animation-container">{svg_code}</div>
                        </div>
                        '''
                        
            # Research
            res_notes = scene.get("research_notes", "")
            if res_notes:
                scenes_html += f"""
                <div class="research-block">
                    <strong>💡 Research Insight:</strong>
                    <p>{res_notes}</p>
                </div>
                """
            
            # Foreshadowing
            foreshadow = scene.get("foreshadowing", "")
            if foreshadow:
                scenes_html += f"""
                <div style='color: var(--accent-color); font-style: italic; margin-top: 15px;'>
                    🔮 Connection: {foreshadow}
                </div>
                """
            
            scenes_html += "</div>"

        # Final Assembly
        final_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>{self.title}</title>
            <link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
            <script type="module">
                import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs';
                mermaid.initialize({{ 
                    startOnLoad: true, 
                    theme: 'base',
                    look: 'handDrawn',
                    themeVariables: {{
                        fontFamily: 'Caveat',
                        primaryColor: '#6c5ce7',
                        lineColor: '#2c3e50'
                    }}
                }});
            </script>
            <style>{self.css}</style>
        </head>
        <body>
            <div class="sidebar">
                {toc_html}
            </div>
            <div class="main-content">
                <div class="container">
                    <h1>{self.title}</h1>
                    {global_html}
                    {scenes_html}
                </div>
            </div>
            <script>{self.js}</script>
        </body>
        </html>
        """
        
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(final_html)
        return True

    def _generate_global_section(self, path):
        if not path or not os.path.exists(path): return ""
        with open(path, "r") as f:
            ctx = json.load(f)
        
        html = f"""
        <div class="sketchy-box" style="background: linear-gradient(135deg, #fff 0%, #f9f9f9 100%);">
            <h2>Global Knowledge Map</h2>
            <p style="font-size: 1.2rem; border-left: 4px solid var(--accent-color); padding-left: 20px;">
                <strong>Core Thesis:</strong> {ctx.get('core_thesis', 'Not defined')}
            </p>
        """

        # FIX: Render Holistic Mindmap
        holistic = ctx.get("holistic_diagram", {})
        if isinstance(holistic, dict) and holistic.get("code"):
            html += f"""
            <h3 style='margin-top:30px;'>Total Knowledge Mindmap</h3>
            <div class="mermaid">{holistic.get("code")}</div>
            """
        
        glossary = ctx.get("glossary", [])
        if glossary:
            html += "<div style='display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-top:20px;'>"
            for item in glossary:
                html += f"""
                <div style='border-bottom: 1px solid var(--border-color); padding-bottom:10px;'>
                    <strong style='color:var(--accent-color);'>{item.get('term')}</strong>: {item.get('definition')}
                </div>
                """
            html += "</div>"
            
        research = ctx.get("extended_research", [])
        if research:
            html += "<h3 style='margin-top:30px;'>Autonomous Research Appendix</h3>"
            for res in research:
                html += f"""
                <div class="research-block">
                    <strong>{res.get('topic')}</strong>
                    <p>{res.get('summary')}</p>
                </div>
                """
        html += "</div>"
        return html
