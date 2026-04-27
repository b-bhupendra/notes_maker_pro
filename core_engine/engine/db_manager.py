import sqlite3
import os
import json
import hashlib
from datetime import datetime

class DBManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # Videos (Projects)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hash TEXT UNIQUE,
                    path TEXT,
                    duration REAL,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Global Context (Project Summary)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS global_context (
                    video_id INTEGER PRIMARY KEY,
                    title TEXT,
                    summary TEXT,
                    research_insight TEXT,
                    FOREIGN KEY(video_id) REFERENCES videos(id)
                )
            """)

            # Scenes (Deterministic frames/audio)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scenes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER,
                    start_time REAL,
                    end_time REAL,
                    frame_path TEXT,
                    transcript TEXT,
                    processed INTEGER DEFAULT 0,
                    FOREIGN KEY(video_id) REFERENCES videos(id)
                )
            """)

            # Knowledge Blocks (AI Synthesized Education)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scene_id INTEGER UNIQUE,
                    title TEXT,
                    educational_narrative TEXT,
                    mermaid_code TEXT,
                    svg_code TEXT,
                    FOREIGN KEY(scene_id) REFERENCES scenes(id)
                )
            """)

            # Facts (Anti-hallucination layer)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scene_id INTEGER,
                    fact TEXT,
                    source_quote TEXT,
                    FOREIGN KEY(scene_id) REFERENCES scenes(id)
                )
            """)

            # Flashcards
            conn.execute("""
                CREATE TABLE IF NOT EXISTS flashcards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scene_id INTEGER,
                    term TEXT,
                    definition TEXT,
                    FOREIGN KEY(scene_id) REFERENCES scenes(id)
                )
            """)

            # Quizzes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quizzes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scene_id INTEGER,
                    question TEXT,
                    option_a TEXT,
                    option_b TEXT,
                    option_c TEXT,
                    option_d TEXT,
                    correct_answer TEXT,
                    explanation TEXT,
                    FOREIGN KEY(scene_id) REFERENCES scenes(id)
                )
            """)
            conn.commit()

    def register_video(self, video_path, duration):
        # Hash based on file size and path for quick deduplication
        file_hash = hashlib.sha256(f"{video_path}_{os.path.getsize(video_path)}".encode()).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id FROM videos WHERE hash = ?", (file_hash,))
            row = cursor.fetchone()
            if row:
                return row[0]
            
            cursor = conn.execute(
                "INSERT INTO videos (hash, path, duration, status) VALUES (?, ?, ?, ?)",
                (file_hash, video_path, duration, 'registered')
            )
            return cursor.lastrowid

    def save_scenes(self, video_id, scenes_data):
        with sqlite3.connect(self.db_path) as conn:
            for s in scenes_data:
                # Check if scene at this exact timestamp already exists
                cursor = conn.execute(
                    "SELECT id FROM scenes WHERE video_id = ? AND start_time = ?", 
                    (video_id, s['time_range'][0])
                )
                if cursor.fetchone(): continue

                conn.execute(
                    "INSERT INTO scenes (video_id, start_time, end_time, frame_path, transcript) VALUES (?, ?, ?, ?, ?)",
                    (video_id, s['time_range'][0], s['time_range'][1], s['frame_path'], s['text'])
                )
            conn.commit()

    def save_synthesis(self, scene_id, data):
        """Atomically saves the AI synthesis and marks the scene as processed."""
        with sqlite3.connect(self.db_path) as conn:
            # Save main block
            conn.execute(
                "INSERT OR REPLACE INTO knowledge_blocks (scene_id, title, educational_narrative, mermaid_code, svg_code) VALUES (?, ?, ?, ?, ?)",
                (scene_id, data.get('scene_title'), data.get('educational_narrative'), data.get('mermaid_code'), data.get('svg_code'))
            )
            
            # Save facts
            conn.execute("DELETE FROM facts WHERE scene_id = ?", (scene_id,))
            for f in data.get('extracted_facts', []):
                conn.execute("INSERT INTO facts (scene_id, fact, source_quote) VALUES (?, ?, ?)", 
                             (scene_id, f.get('fact'), f.get('source_quote')))
            
            # Save flashcards
            conn.execute("DELETE FROM flashcards WHERE scene_id = ?", (scene_id,))
            for card in data.get('flashcards', []):
                conn.execute("INSERT INTO flashcards (scene_id, term, definition) VALUES (?, ?, ?)",
                             (scene_id, card.get('term'), card.get('definition')))
            
            # Save quiz
            conn.execute("DELETE FROM quizzes WHERE scene_id = ?", (scene_id,))
            q = data.get('quiz', {})
            if q:
                conn.execute(
                    "INSERT INTO quizzes (scene_id, question, option_a, option_b, option_c, option_d, correct_answer, explanation) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (scene_id, q.get('question'), q.get('options', [""]*4)[0], q.get('options', [""]*4)[1], 
                     q.get('options', [""]*4)[2], q.get('options', [""]*4)[3], q.get('correct_answer'), q.get('explanation'))
                )
            
            # Mark as processed
            conn.execute("UPDATE scenes SET processed = 1 WHERE id = ?", (scene_id,))
            conn.commit()

    def get_unprocessed_scenes(self, video_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM scenes WHERE video_id = ? AND processed = 0 ORDER BY start_time", (video_id,))
            return [dict(r) for r in cursor.fetchall()]

    def get_full_project(self, video_id):
        """Reconstructs the entire project from the DB for rendering."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Global
            cursor = conn.execute("SELECT * FROM global_context WHERE video_id = ?", (video_id,))
            global_info = dict(cursor.fetchone()) if cursor.rowcount > 0 else {}
            
            # Scenes with Blocks
            cursor = conn.execute("""
                SELECT s.*, kb.title as ai_title, kb.educational_narrative, kb.mermaid_code, kb.svg_code
                FROM scenes s
                LEFT JOIN knowledge_blocks kb ON s.id = kb.scene_id
                WHERE s.video_id = ?
                ORDER BY s.start_time
            """, (video_id,))
            scenes = [dict(r) for r in cursor.fetchall()]
            
            for s in scenes:
                # Facts
                c = conn.execute("SELECT fact, source_quote FROM facts WHERE scene_id = ?", (s['id'],))
                s['facts'] = [dict(r) for r in c.fetchall()]
                # Flashcards
                c = conn.execute("SELECT term, definition FROM flashcards WHERE scene_id = ?", (s['id'],))
                s['flashcards'] = [dict(r) for r in c.fetchall()]
                # Quiz
                c = conn.execute("SELECT * FROM quizzes WHERE scene_id = ?", (s['id'],))
                q = c.fetchone()
                s['quiz'] = dict(q) if q else None
                
            return {"global": global_info, "scenes": scenes}
