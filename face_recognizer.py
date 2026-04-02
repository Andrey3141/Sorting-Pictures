import os
import cv2
import hashlib
import json
import numpy as np
import tensorflow as tf
from datetime import datetime
from pathlib import Path

class FaceRecognizer:
    def __init__(self, db):
        self.db = db
        
        # Создаем папку для моделей если её нет
        Path("models").mkdir(exist_ok=True)
        
        # Проверяем наличие файлов моделей
        cascade_path = 'models/haarcascade_frontalface_default.xml'
        facenet_path = 'models/facenet.tflite'
        
        if not os.path.exists(cascade_path):
            print(f"⚠️ Ошибка: {cascade_path} не найден!")
            print("Пожалуйста, поместите haarcascade_frontalface_default.xml в папку models/")
            
        if not os.path.exists(facenet_path):
            print(f"⚠️ Ошибка: {facenet_path} не найден!")
            print("Пожалуйста, поместите facenet.tflite в папку models/")
        
        # Загружаем Haar Cascade для детекции лиц
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Загружаем FaceNet для получения эмбеддингов
        try:
            self.facenet = tf.lite.Interpreter(model_path=facenet_path)
            self.facenet.allocate_tensors()
            print("✅ FaceNet загружен успешно")
        except Exception as e:
            print(f"❌ Ошибка загрузки FaceNet: {e}")
            self.facenet = None
        
        # Папка для сохранения фото при обучении
        self.training_photos_dir = "training_photos"
        Path(self.training_photos_dir).mkdir(exist_ok=True)
        
        # Загружаем известные лица из БД
        self.load_known_faces()
    
    def load_known_faces(self):
        """Загрузить известные лица из базы данных"""
        self.known_faces = self.db.get_all_faces()
        print(f"📚 Загружено {len(self.known_faces)} известных лиц")
        for name in self.known_faces.keys():
            print(f"   - {name}")
    
    def get_file_hash(self, file_path):
        """Вычисление MD5 хеша файла для проверки дубликатов"""
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                buf = f.read(65536)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
            return hasher.hexdigest()
        except Exception as e:
            print(f"Ошибка вычисления хеша: {e}")
            return None
    
    def get_face_hash(self, face_img):
        """Получить хеш области лица для сравнения"""
        if face_img is None or face_img.size == 0:
            return None
        
        try:
            # Уменьшаем до 32x32 для хеша
            resized = cv2.resize(face_img, (32, 32))
            # Преобразуем в оттенки серого
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            # Бинаризуем
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            # Хеш как строка
            hash_str = ''.join(str(int(pixel/255)) for pixel in binary.flatten())
            return hash_str
        except Exception as e:
            print(f"Ошибка получения хеша лица: {e}")
            return None
    
    def get_face_embedding(self, face_img):
        """Получить эмбеддинг лица через FaceNet"""
        if self.facenet is None:
            return np.random.randn(128)
        
        try:
            # Подготавливаем изображение для FaceNet (160x160)
            face_resized = cv2.resize(face_img, (160, 160))
            face_normalized = (face_resized.astype(np.float32) - 127.5) / 127.5
            input_tensor = np.expand_dims(face_normalized, axis=0)
            
            # Выполняем инференс
            input_details = self.facenet.get_input_details()
            output_details = self.facenet.get_output_details()
            self.facenet.set_tensor(input_details[0]['index'], input_tensor)
            self.facenet.invoke()
            embedding = self.facenet.get_tensor(output_details[0]['index'])[0]
            
            # Нормализуем эмбеддинг
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding
        except Exception as e:
            print(f"Ошибка получения эмбеддинга: {e}")
            return np.random.randn(128)
    
    def recognize_face(self, embedding, threshold=0.6):
        """Распознать лицо по эмбеддингу"""
        if not self.known_faces or self.facenet is None:
            return "Неизвестный", 0.0
        
        best_match = "Неизвестный"
        best_distance = 1.0
        best_confidence = 0.0
        
        for name, known_embedding in self.known_faces.items():
            try:
                # Вычисляем косинусное расстояние
                distance = 1 - np.dot(embedding, known_embedding)
                confidence = 1 - distance
                
                if distance < best_distance and distance < threshold:
                    best_distance = distance
                    best_confidence = confidence
                    best_match = name
            except Exception as e:
                print(f"Ошибка сравнения с {name}: {e}")
                continue
        
        return best_match, best_confidence
    
    def save_face_photo(self, face_img, person_name, original_image_path, face_id):
        """Сохраняет фото лица при обучении"""
        try:
            person_dir = os.path.join(self.training_photos_dir, person_name)
            Path(person_dir).mkdir(exist_ok=True, parents=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = os.path.splitext(os.path.basename(original_image_path))[0]
            filename = f"{person_name}_{timestamp}_{original_name}_face_{face_id}.jpg"
            filepath = os.path.join(person_dir, filename)
            
            cv2.imwrite(filepath, face_img)
            print(f"📸 Сохранено фото лица: {filepath}")
            return filepath
        except Exception as e:
            print(f"Ошибка сохранения фото: {e}")
            return None
    
    def process_image(self, image_path, callback=None):
        """Обработать изображение и найти все лица"""
        
        # Загружаем изображение
        img = cv2.imread(image_path)
        if img is None:
            print(f"❌ Не удалось загрузить изображение: {image_path}")
            return []
        
        # Конвертируем в оттенки серого для детекции
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Детекция лиц
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(50, 50))
        print(f"🔍 Обнаружено {len(faces)} кандидатов на {os.path.basename(image_path)}")
        
        results = []
        false_positives_count = 0
        
        for i, (x, y, w, h) in enumerate(faces):
            face_roi = img[y:y+h, x:x+w]
            
            # Получаем хеш области для проверки
            face_hash = self.get_face_hash(face_roi)
            
            # Проверяем, не является ли это ложным срабатыванием
            if face_hash and self.db.is_false_positive(face_hash):
                print(f"   ⚠️ Область #{i+1} - ЛОЖНОЕ СРАБАТЫВАНИЕ (пропускаем)")
                false_positives_count += 1
                continue
            
            try:
                # Получаем эмбеддинг
                embedding = self.get_face_embedding(face_roi)
                
                # Распознаем
                name, confidence = self.recognize_face(embedding)
                
                face_data = {
                    "id": i,
                    "position": (x, y, w, h),
                    "name": name,
                    "confidence": confidence,
                    "embedding": embedding,
                    "is_known": name != "Неизвестный",
                    "thumbnail": self.get_thumbnail(face_roi),
                    "face_hash": face_hash
                }
                
                # Сохраняем неизвестные лица в БД для последующего обучения
                if not face_data["is_known"] and self.facenet is not None:
                    self.db.save_unknown_face(image_path, embedding, face_data["thumbnail"])
                    print(f"   👤 НЕИЗВЕСТНОЕ лицо #{i+1}")
                else:
                    print(f"   ✅ {name} (уверенность: {confidence:.2%})")
                
                results.append(face_data)
                
                if callback:
                    callback(face_data)
                    
            except Exception as e:
                print(f"❌ Ошибка обработки области {i}: {e}")
        
        if false_positives_count > 0:
            print(f"📊 Итого: {len(results)} лиц, {false_positives_count} ложных срабатываний")
        
        return results
    
    def get_thumbnail(self, face_img, size=(100, 100)):
        """Создать миниатюру лица для отображения в UI"""
        try:
            thumbnail = cv2.resize(face_img, size)
            _, buffer = cv2.imencode('.jpg', thumbnail)
            return buffer.tobytes()
        except Exception as e:
            print(f"Ошибка создания миниатюры: {e}")
            return b''
    
    def mark_as_false_positive(self, image_path, face_data):
        """Пометить область как ложное срабатывание (НЕ лицо)"""
        try:
            # Загружаем изображение
            img = cv2.imread(image_path)
            if img is None:
                return False
            
            # Получаем позицию и конвертируем в обычные int
            x, y, w, h = face_data["position"]
            position = (int(x), int(y), int(w), int(h))
            
            face_roi = img[y:y+h, x:x+w]
            face_hash = self.get_face_hash(face_roi)
            thumbnail = self.get_thumbnail(face_roi)
            
            # Сохраняем в БД
            self.db.add_false_positive(image_path, position, face_hash, thumbnail)
            print(f"✅ Область помечена как НЕ ЛИЦО (false positive)")
            return True
        except Exception as e:
            print(f"❌ Ошибка при маркировке: {e}")
            return False
    
    def retrain_from_training_photos(self):
        """Переобучить модель на основе сохраненных тренировочных фото"""
        if not os.path.exists(self.training_photos_dir):
            print("Папка с тренировочными фото не найдена")
            return
        
        print("🔄 Переобучение модели на основе сохраненных фото...")
        
        for person_name in os.listdir(self.training_photos_dir):
            person_dir = os.path.join(self.training_photos_dir, person_name)
            if not os.path.isdir(person_dir):
                continue
            
            print(f"   Обработка: {person_name}")
            
            for photo_file in os.listdir(person_dir):
                if photo_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    photo_path = os.path.join(person_dir, photo_file)
                    
                    # Загружаем фото и получаем эмбеддинг
                    img = cv2.imread(photo_path)
                    if img is not None:
                        embedding = self.get_face_embedding(img)
                        self.db.add_face(person_name, embedding)
                        print(f"      ✅ Добавлен {photo_file}")
        
        self.load_known_faces()
        print("✅ Переобучение завершено!")