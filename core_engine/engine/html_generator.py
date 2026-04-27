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

        .container { max-width: 850px; margin: 0 auto; }

        h1 { font-size: 2.5rem; font-weight: 700; margin-bottom: 48px; border-bottom: 2px solid var(--border-color); padding-bottom: 16px;}
        h2 { font-size: 1.5rem; font-weight: 600; margin-top: 0; margin-bottom: 16px; }
        h4 { font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-top: 24px; margin-bottom: 12px; }

        .hygienic-box {
            background-color: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 32px;
            margin-bottom: 32px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            position: relative;
        }

        .timestamp-badge {
            display: inline-block;
            background: #f1f3f4;
            color: var(--text-muted);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-family: var(--font-mono);
            margin-bottom: 16px;
            border: 1px solid var(--border-color);
        }

        .fact-list { margin: 0; padding-left: 20px; }
        .fact-list li { margin-bottom: 8px; }

        .definition-grid {
            display: grid;
            grid-template-columns: 200px 1fr;
            gap: 16px;
            border-top: 1px solid var(--border-color);
            margin-top: 24px;
            padding-top: 16px;
        }
        .def-term { font-weight: 600; color: var(--accent-color); }
        .def-desc { color: var(--text-color); }

        .mermaid {
            background-color: #ffffff;
            border: 1px solid var(--border-color);
            padding: 24px;
            margin: 24px 0;
            border-radius: 8px;
            display: flex;
            justify-content: center;
        }

        .animated-explainer-box {
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 24px;
            margin: 24px 0;
            position: relative;
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.03);
            overflow: hidden;
            min-height: 300px;
            display: flex;
            flex-direction: column;
        }
        .animated-explainer-box svg {
            max-width: 100%;
            height: auto;
            flex: 1;
        }
        .animation-container {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        .replay-btn {
            position: absolute;
            top: 12px;
            right: 12px;
            background: #f8f9fa;
            color: var(--text-muted);
            border: 1px solid var(--border-color);
            padding: 4px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.75rem;
            font-family: var(--font-mono);
            transition: all 0.2s;
            z-index: 10;
        }
        .replay-btn:hover { background: #e8f0fe; color: var(--accent-color); border-color: #d2e3fc; }
        .explainer-caption {
            color: var(--text-muted);
            font-size: 0.8rem;
            margin-top: 12px;
            font-style: italic;
            text-align: center;
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
            const scenes = document.querySelectorAll('.hygienic-box');
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

    def generate(self, kb_path, output_html="visual_notes.html", global_context_path=None):
        if not os.path.exists(kb_path):
            return False

        with open(kb_path, "r") as f:
            data = json.load(f)

        global_html = self._generate_global_section(global_context_path)
        
        toc_html = "<h3>Contents</h3>"
        for i, scene in enumerate(data):
            time_range = scene.get("time_range", [0, 0])
            summary = scene.get("core_assertion", "Scene Analysis")
            if len(summary) > 40: summary = summary[:40] + "..."
            toc_id = f"scene-{i}"
            toc_html += f"""
            <div class="toc-item" onclick="scrollToScene('{toc_id}')">
                <span class="toc-timestamp">{time_range[0]:.2f}s - {time_range[1]:.2f}s</span>
                {summary}
            </div>
            """

        scenes_html = ""
        for i, scene in enumerate(data):
            toc_id = f"scene-{i}"
            time_range = scene.get("time_range", [0, 0])
            time_label = f"{time_range[0]:.2f}s - {time_range[1]:.2f}s"
            
            scenes_html += f"""
            <div class="hygienic-box" id="{toc_id}">
                <div class="timestamp-badge">{time_label}</div>
                <h2>{scene.get('core_assertion', 'Scene Segment')}</h2>
            """
            
            steps = scene.get("sequential_steps", [])
            if steps:
                scenes_html += "<h4>Process Steps</h4><ol class='fact-list'>"
                for step in steps: scenes_html += f"<li>{step}</li>"
                scenes_html += "</ol>"

            facts = scene.get("extracted_facts", [])
            if facts:
                scenes_html += "<h4>Extracted Facts</h4><ul class='fact-list'>"
                for fact in facts: scenes_html += f"<li>{fact}</li>"
                scenes_html += "</ul>"
                
            defs = scene.get("definitions", [])
            if defs:
                scenes_html += "<div class='definition-grid'>"
                for d in defs:
                    scenes_html += f"<div class='def-term'>{d.get('term', '')}</div><div class='def-desc'>{d.get('definition', '')}</div>"
                scenes_html += "</div>"
                
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
                        <div class="animated-explainer-box">
                            <button onclick="replayAnimation(this)" class="replay-btn">
                                &#x1F504; Replay
                            </button>
                            <div class="animation-container">{svg_code}</div>
                            <p class="explainer-caption">&#x1F3AC; Animated Explainer &mdash; auto-generated from transcript</p>
                        </div>
                        '''
                        
            res_notes = scene.get("research_notes", "")
            if res_notes:
                scenes_html += f"""
                <div class="research-block" style="border-radius: 8px; border: 1px solid var(--border-color); border-left: 4px solid var(--accent-color); background: #fcfcfc; padding: 16px; margin-top: 24px;">
                    <strong>💡 Research Insight:</strong>
                    <p style="margin: 8px 0 0 0;">{res_notes}</p>
                </div>
                """
            scenes_html += "</div>"

        # Using f-strings carefully to avoid brace issues
        final_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{self.title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ 
            startOnLoad: true, 
            theme: 'neutral',
            look: 'classic',
            flowchart: {{ curve: 'stepBefore' }},
            themeVariables: {{
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                lineColor: '#5f6368',
                primaryColor: '#f8f9fa',
                primaryBorderColor: '#dadce0'
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
</html>"""

        with open(output_html, "w", encoding="utf-8") as f:
            f.write(final_html)
        return True

    def _generate_global_section(self, path):
        if not path or not os.path.exists(path): return ""
        with open(path, "r") as f:
            ctx = json.load(f)
        
        html = f"""
        <div class="hygienic-box" style="background: linear-gradient(135deg, #fff 0%, #fcfcfc 100%);">
            <h2>Global Knowledge Map</h2>
            <p style="font-size: 1.1rem; border-left: 4px solid var(--accent-color); padding-left: 20px; color: var(--text-color);">
                <strong>Core Thesis:</strong> {ctx.get('core_thesis', 'Not defined')}
            </p>
        """

        holistic = ctx.get("holistic_diagram", {})
        if isinstance(holistic, dict) and holistic.get("code"):
            html += f"""
            <h4>Total Knowledge Mindmap</h4>
            <div class="mermaid">{holistic.get("code")}</div>
            """
        
        glossary = ctx.get("glossary", [])
        if glossary:
            html += "<h4>Technical Glossary</h4>"
            html += "<div class='definition-grid' style='border-top:none; margin-top:0;'>"
            for item in glossary:
                html += f"""
                <div class="def-term">{item.get('term')}</div>
                <div class="def-desc">{item.get('definition')}</div>
                """
            html += "</div>"
            
        research = ctx.get("extended_research", [])
        if research:
            html += "<h4>Autonomous Research Appendix</h4>"
            for res in research:
                html += f"""
                <div class="research-block" style="border-radius: 8px; border: 1px solid var(--border-color); border-left: 4px solid var(--accent-color); background: #fcfcfc; padding: 16px; margin-top: 12px;">
                    <strong style="color: var(--accent-color);">{res.get('topic')}</strong>
                    <p style="margin: 8px 0 0 0; font-size: 0.9rem;">{res.get('summary')}</p>
                </div>
                """
        html += "</div>"
        return html
