import sqlite3
import json
import numpy as np
from datetime import datetime

class FaceDatabase:
    def __init__(self, db_path="faces.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS known_faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                embedding TEXT NOT NULL,
                created_at TIMESTAMP,
                last_seen TIMESTAMP,
                times_seen INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS unknown_faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT,
                embedding TEXT,
                thumbnail BLOB,
                detected_at TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT UNIQUE,
                file_path TEXT,
                processed_at TIMESTAMP,
                faces_count INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sorted_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT,
                sorted_path TEXT,
                person_name TEXT,
                confidence REAL,
                sorted_at TIMESTAMP
            )
        ''')
        
        # Таблица для ложных срабатываний
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS false_positives (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT,
                face_position TEXT,
                face_hash TEXT,
                thumbnail BLOB,
                created_at TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def add_face(self, name, embedding):
        cursor = self.conn.cursor()
        embedding_json = json.dumps(embedding.tolist())
        
        cursor.execute("SELECT id, embedding FROM known_faces WHERE name = ?", (name,))
        existing = cursor.fetchone()
        
        if existing:
            old_embedding = np.array(json.loads(existing[1]))
            new_embedding = (old_embedding + embedding) / 2
            cursor.execute('''
                UPDATE known_faces 
                SET embedding = ?, times_seen = times_seen + 1, last_seen = ?
                WHERE name = ?
            ''', (json.dumps(new_embedding.tolist()), datetime.now(), name))
        else:
            cursor.execute('''
                INSERT INTO known_faces (name, embedding, created_at, last_seen)
                VALUES (?, ?, ?, ?)
            ''', (name, embedding_json, datetime.now(), datetime.now()))
        
        self.conn.commit()
    
    def get_all_faces(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name, embedding FROM known_faces")
        results = cursor.fetchall()
        faces = {}
        for name, emb_json in results:
            faces[name] = np.array(json.loads(emb_json))
        return faces
    
    def save_unknown_face(self, image_path, embedding, thumbnail):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO unknown_faces (image_path, embedding, thumbnail, detected_at)
            VALUES (?, ?, ?, ?)
        ''', (image_path, json.dumps(embedding.tolist()), thumbnail, datetime.now()))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_pending_faces(self, limit=50):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, thumbnail, image_path FROM unknown_faces 
            WHERE status = 'pending' 
            ORDER BY detected_at DESC LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def label_unknown_face(self, face_id, name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT embedding FROM unknown_faces WHERE id = ?", (face_id,))
        result = cursor.fetchone()
        
        if result:
            embedding = np.array(json.loads(result[0]))
            self.add_face(name, embedding)
            cursor.execute('''
                UPDATE unknown_faces SET status = 'labeled' WHERE id = ?
            ''', (face_id,))
            self.conn.commit()
            return True
        return False
    
    def delete_unknown_face(self, face_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM unknown_faces WHERE id = ?", (face_id,))
        self.conn.commit()
    
    def is_image_processed(self, file_hash):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM processed_images WHERE file_hash = ?", (file_hash,))
        return cursor.fetchone() is not None
    
    def mark_image_processed(self, file_hash, file_path, faces_count):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO processed_images (file_hash, file_path, processed_at, faces_count)
            VALUES (?, ?, ?, ?)
        ''', (file_hash, file_path, datetime.now(), faces_count))
        self.conn.commit()
    
    def save_sorted_photo(self, original_path, sorted_path, person_name, confidence):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO sorted_photos (original_path, sorted_path, person_name, confidence, sorted_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (original_path, sorted_path, person_name, confidence, datetime.now()))
        self.conn.commit()
    
    # ============ МЕТОДЫ ДЛЯ ЛОЖНЫХ СРАБАТЫВАНИЙ ============
    
    def add_false_positive(self, image_path, face_position, face_hash, thumbnail):
        """Сохранить область, которая НЕ является лицом"""
        cursor = self.conn.cursor()
        
        # Конвертируем позицию в JSON с обычными int (не int32)
        position_list = [int(face_position[0]), int(face_position[1]), int(face_position[2]), int(face_position[3])]
        position_json = json.dumps(position_list)
        
        cursor.execute('''
            INSERT INTO false_positives (image_path, face_position, face_hash, thumbnail, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (image_path, position_json, face_hash, thumbnail, datetime.now()))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_false_positives(self):
        """Получить все ложные срабатывания"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, face_hash, face_position, thumbnail FROM false_positives")
        results = cursor.fetchall()
        
        # Конвертируем JSON обратно в tuple
        converted = []
        for row in results:
            fp_id, face_hash, face_position_json, thumbnail = row
            face_position = tuple(json.loads(face_position_json))
            converted.append((fp_id, face_hash, face_position, thumbnail))
        return converted
    
    def delete_false_positive(self, fp_id):
        """Удалить ложное срабатывание"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM false_positives WHERE id = ?", (fp_id,))
        self.conn.commit()
    
    def is_false_positive(self, face_hash, threshold=0.95):
        """Проверить, является ли область ложным срабатыванием"""
        if not face_hash:
            return False
        
        cursor = self.conn.cursor()
        cursor.execute("SELECT face_hash FROM false_positives")
        results = cursor.fetchall()
        
        for (stored_hash,) in results:
            if stored_hash and face_hash and stored_hash == face_hash:
                return True
        return False
    
    def clear_false_positives(self):
        """Очистить все ложные срабатывания"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM false_positives")
        self.conn.commit()