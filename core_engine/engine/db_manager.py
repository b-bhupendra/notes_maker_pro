import sqlite3
import os
import json
import hashlib
from datetime import datetime

class DBManager:
    def __init__(self, db_path="knowledge_lake.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Videos Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_hash TEXT UNIQUE,
                    filename TEXT,
                    duration REAL,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Scenes Table (The "Harvester" data)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scenes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER,
                    start_time REAL,
                    end_time REAL,
                    frame_path TEXT,
                    transcript TEXT,
                    ocr_text TEXT,
                    FOREIGN KEY(video_id) REFERENCES videos(id) ON DELETE CASCADE
                )
            """)
            
            # Knowledge Blocks Table (The "Synthesizer" data)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scene_id INTEGER,
                    core_assertion TEXT,
                    technical_narrative TEXT,
                    FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE
                )
            """)
            
            # Definitions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS definitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scene_id INTEGER,
                    term TEXT,
                    definition TEXT,
                    FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE
                )
            """)
            
            # Visual Elements Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visual_elements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scene_id INTEGER,
                    type TEXT,
                    content TEXT,
                    FOREIGN KEY(scene_id) REFERENCES scenes(id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()

    def get_file_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def register_video(self, file_path, duration):
        file_hash = self.get_file_hash(file_path)
        filename = os.path.basename(file_path)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO videos (file_hash, filename, duration, status)
                VALUES (?, ?, ?, 'initialized')
                ON CONFLICT(file_hash) DO UPDATE SET
                    filename = excluded.filename,
                    duration = excluded.duration
                RETURNING id
            """, (file_hash, filename, duration))
            return cursor.fetchone()[0]

    def update_video_status(self, video_id, status):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE videos SET status = ? WHERE id = ?", (status, video_id))

    def save_scenes(self, video_id, scenes_data):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Clear existing scenes for this video (Update strategy)
            cursor.execute("DELETE FROM scenes WHERE video_id = ?", (video_id,))
            
            for scene in scenes_data:
                cursor.execute("""
                    INSERT INTO scenes (video_id, start_time, end_time, frame_path, transcript)
                    VALUES (?, ?, ?, ?, ?)
                """, (video_id, scene['time_range'][0], scene['time_range'][1], scene['frame_path'], scene['text']))
            conn.commit()

    def get_scenes(self, video_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scenes WHERE video_id = ?", (video_id,))
            return [dict(row) for row in cursor.fetchall()]

    def save_synthesis(self, scene_id, analysis):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Clear existing for this scene
            cursor.execute("DELETE FROM knowledge_blocks WHERE scene_id = ?", (scene_id,))
            cursor.execute("DELETE FROM definitions WHERE scene_id = ?", (scene_id,))
            cursor.execute("DELETE FROM visual_elements WHERE scene_id = ?", (scene_id,))
            
            # Narrative
            cursor.execute("INSERT INTO knowledge_blocks (scene_id, core_assertion, technical_narrative) VALUES (?, ?, ?)",
                           (scene_id, analysis.get('core_assertion'), analysis.get('technical_narrative')))
            
            # Definitions
            for d in analysis.get('definitions', []):
                cursor.execute("INSERT INTO definitions (scene_id, term, definition) VALUES (?, ?, ?)",
                               (scene_id, d.get('term'), d.get('definition')))
            
            # Visuals
            for v in analysis.get('visual_elements', []):
                cursor.execute("INSERT INTO visual_elements (scene_id, type, content) VALUES (?, ?, ?)",
                               (scene_id, v.get('type'), v.get('mermaid_code') or v.get('svg_code')))
            
            conn.commit()
            
    def export_knowledge_base(self, video_id):
        """Reconstructs the knowledge base JSON from the relational DB."""
        kb = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            scenes = cursor.execute("SELECT * FROM scenes WHERE video_id = ?", (video_id,)).fetchall()
            for s in scenes:
                block = {
                    "time_range": [s['start_time'], s['end_time']],
                    "frame_path": s['frame_path'],
                    "audio_text": s['transcript']
                }
                
                kb_data = cursor.execute("SELECT * FROM knowledge_blocks WHERE scene_id = ?", (s['id'],)).fetchone()
                if kb_data:
                    block.update({
                        "core_assertion": kb_data['core_assertion'],
                        "technical_narrative": kb_data['technical_narrative']
                    })
                
                defs = cursor.execute("SELECT * FROM definitions WHERE scene_id = ?", (s['id'],)).fetchall()
                block["definitions"] = [dict(d) for d in defs]
                
                vis = cursor.execute("SELECT * FROM visual_elements WHERE scene_id = ?", (s['id'],)).fetchall()
                block["visual_elements"] = []
                for v in vis:
                    item = {"type": v['type']}
                    if v['type'] == "diagram": item["mermaid_code"] = v['content']
                    else: item["svg_code"] = v['content']
                    block["visual_elements"].append(item)
                
                kb.append(block)
        return kb
