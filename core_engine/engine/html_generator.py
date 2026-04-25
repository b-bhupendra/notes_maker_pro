import json
import os
import markdown

class HTMLGenerator:
    def __init__(self, title="Video Knowledge Notes"):
        self.title = title
        self.css = """
        :root {
            --bg-color: #1e1e24;
            --text-color: #e0e0e0;
            --accent-color: #a882ff;
            --accent-green: #4CAF50;
            --card-bg: #2b2b36;
            --border-color: #5c5c70;
            --font-hand: 'Caveat', cursive;
            --font-ui: 'Inter', sans-serif;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: var(--font-ui);
            line-height: 1.6;
            margin: 0;
            padding: 40px 20px;
            display: flex;
            justify-content: center;
        }

        .note-container {
            max-width: 850px;
            width: 100%;
        }

        h1, h2, h3 {
            font-family: var(--font-hand);
            color: var(--accent-color);
            letter-spacing: 1px;
            font-weight: 700;
        }

        h1 {
            font-size: 3.5rem;
            text-align: center;
            border-bottom: 2px dashed var(--border-color);
            padding-bottom: 15px;
            margin-bottom: 30px;
        }

        h2 {
            font-size: 2.5rem;
            margin-top: 40px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        h2::before {
            content: "❖";
            font-size: 1.5rem;
            color: var(--border-color);
        }

        .sketchy-box {
            background-color: var(--card-bg);
            border: 2px solid var(--border-color);
            border-radius: 255px 15px 225px 15px / 15px 225px 15px 255px; 
            padding: 25px 30px;
            margin-bottom: 25px;
            box-shadow: 5px 5px 0px rgba(0,0,0,0.3);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .sketchy-box:hover {
            transform: translateY(-2px) rotate(0.5deg);
            border-color: var(--accent-color);
            box-shadow: 7px 7px 0px rgba(168, 130, 255, 0.15);
        }

        .grid-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }

        .callout {
            border-left: 4px solid var(--accent-color);
            background-color: rgba(168, 130, 255, 0.08);
            padding: 15px 20px;
            margin: 15px 0;
            border-radius: 0 10px 10px 0;
            position: relative;
        }

        .callout .def-term {
            font-family: var(--font-hand);
            font-size: 1.8rem;
            color: var(--accent-color);
            display: block;
            margin-bottom: 5px;
        }
        
        .timestamp {
            font-size: 0.8rem;
            color: var(--border-color);
            margin-bottom: 10px;
            display: block;
            font-family: monospace;
        }

        img.frame {
            max-width: 100%;
            border-radius: 10px;
            margin-bottom: 15px;
            border: 1px solid var(--border-color);
        }
        """

    def _markdown_to_html(self, text):
        import re
        if not text: return ""
        
        # Robustness: Handle if LLM returned a dictionary (e.g. {"mermaid": "graph..."})
        if isinstance(text, dict):
            if "mermaid" in text:
                text = f"```mermaid\n{text['mermaid']}\n```"
            else:
                text = "\n\n".join(str(v) for v in text.values())
        elif not isinstance(text, str):
            text = str(text)
            
        # Extract mermaid blocks and replace them with HTML divs
        def mermaid_replacer(match):
            code = match.group(1)
            return f'<div class="mermaid">\n{code}\n</div>'
        
        # Regex to find ```mermaid ... ```
        text = re.sub(r'```mermaid\s*\n(.*?)\n```', mermaid_replacer, text, flags=re.DOTALL)
        
        return markdown.markdown(text)

    def _get_base64_image(self, kb_path, frame_rel_path):
        import base64
        # kb_path is like test_video_output/knowledge_base.json
        # frame_rel_path is like frames/frame_0.0.jpg
        base_dir = os.path.dirname(kb_path)
        img_path = os.path.join(base_dir, frame_rel_path)
        if not os.path.exists(img_path):
            return ""
        try:
            with open(img_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/jpeg;base64,{encoded}"
        except Exception:
            return ""

    def generate(self, kb_path, output_html="visual_notes.html"):
        if not os.path.exists(kb_path):
            print(f"Error: Knowledge base not found at {kb_path}")
            return False

        with open(kb_path, "r") as f:
            data = json.load(f)

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{self.title}</title>
            <link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
            <script type="module">
                import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
            </script>
            <style>{self.css}
            .mermaid {{
                background-color: var(--card-bg);
                border: 2px dashed var(--border-color);
                border-radius: 10px;
                padding: 20px;
                margin-top: 15px;
                text-align: center;
            }}
            </style>
        </head>
        <body>
            <div class="note-container">
                <h1>{self.title}</h1>
                <div class="tags">
                    <span class="tag">#video-notes</span>
                    <span class="tag">#auto-generated</span>
                </div>
        """

        # We will conjoin notes by grouping frames that share the same OCR text (meaning the visual slide hasn't changed much)
        # We'll aggregate the audio text and then just render one "sketchy-box" for the whole scene
        
        scenes = []
        current_scene = None

        for item in data:
            if not item.get("detailed_explanations") and not item.get("key_concepts"):
                continue

            # If it's the first item, or if the OCR text changed (meaning it's a new slide)
            # OR if we just want a simple heuristic: Group if it's the exact same frame path (if extractor deduplicated)
            # Since extractor deduplicates identical frames, the frame_path stays the same!
            frame_path = item.get("frame_path", "")
            
            if current_scene is None or current_scene["frame_path"] != frame_path:
                if current_scene is not None:
                    scenes.append(current_scene)
                current_scene = {
                    "start_time": item.get("timeframe", 0),
                    "end_time": item.get("timeframe", 0),
                    "frame_path": frame_path,
                    "key_concepts": item.get("key_concepts", []),
                    "detailed_explanations": item.get("detailed_explanations", ""),
                    "flowcharts_illustrations": item.get("flowcharts_illustrations", ""),
                    "definitions": item.get("definitions", []),
                    "summary": item.get("summary", "")
                }
            else:
                # Same visual scene! Just extend the end_time.
                current_scene["end_time"] = item.get("timeframe", 0)
                # We could aggregate transcripts here if we were extracting them, but the LLM already analyzed it.
                # Since the visual is the same, we just use the first LLM analysis of this scene.
        
        if current_scene is not None:
            scenes.append(current_scene)

        for scene in scenes:
            b64_img = self._get_base64_image(kb_path, scene['frame_path'])
            img_tag = f'<img class="frame" src="{b64_img}" alt="Scene from {scene["start_time"]}s">' if b64_img else ""
            
            time_label = f"{scene['start_time']:.2f}s"
            if scene['start_time'] != scene['end_time']:
                time_label = f"{scene['start_time']:.2f}s - {scene['end_time']:.2f}s"

            html_content += f"""
                <div class="sketchy-box" style="margin-top: 20px; border-color: var(--accent-color);">
                    <span class="timestamp">⏱️ Scene: {time_label}</span>
                    {img_tag}
            """

            # Key Concepts
            concepts = scene.get("key_concepts", [])
            if concepts:
                html_content += "<div style='margin-bottom: 15px;'><strong>Key Concepts:</strong> "
                html_content += ", ".join([f"<span class='highlight'>{c}</span>" for c in concepts])
                html_content += "</div>"

            # Detailed Explanations
            details = scene.get("detailed_explanations", "")
            if details:
                html_content += f"<div class='markdown-content'>{self._markdown_to_html(details)}</div>"

            # Flowcharts & Illustrations
            flowcharts = scene.get("flowcharts_illustrations", "")
            if flowcharts:
                html_content += f"<div style='margin-top: 15px;'><strong>Visual Analysis:</strong><br>{self._markdown_to_html(flowcharts)}</div>"

            # Definitions
            definitions = scene.get("definitions", [])
            if definitions:
                for df in definitions:
                    term = df.get("term", "")
                    definition = df.get("definition", "")
                    if term and definition:
                        html_content += f"""
                        <div class="callout">
                            <span class="def-term">{term}</span>
                            <p>{self._markdown_to_html(definition)}</p>
                        </div>
                        """
            
            html_content += "</div>" # End of main sketchy box

        html_content += """
            </div>
        </body>
        </html>
        """

        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        return True
