import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

class PhotoSorter:
    def __init__(self, recognizer, db, base_output_dir="sorted_photos"):
        self.recognizer = recognizer
        self.db = db
        self.base_output_dir = base_output_dir
        
        Path(base_output_dir).mkdir(exist_ok=True)
        
        # Создаем папки для разных категорий
        self.unknown_dir = os.path.join(base_output_dir, "unknown")
        self.no_faces_dir = os.path.join(base_output_dir, "no_faces")
        Path(self.unknown_dir).mkdir(exist_ok=True)
        Path(self.no_faces_dir).mkdir(exist_ok=True)
    
    def get_file_hash(self, file_path):
        """Вычисление MD5 хеша файла"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def is_duplicate(self, file_path, target_dir):
        """Проверка, есть ли уже такой файл в целевой папке"""
        file_hash = self.get_file_hash(file_path)
        
        if not os.path.exists(target_dir):
            return False, None
        
        for existing_file in os.listdir(target_dir):
            existing_path = os.path.join(target_dir, existing_file)
            if os.path.isfile(existing_path):
                try:
                    existing_hash = self.get_file_hash(existing_path)
                    if existing_hash == file_hash:
                        return True, existing_path
                except:
                    continue
        return False, None
    
    def sort_photo(self, image_path):
        """
        Умная сортировка одного фото
        """
        print(f"\n📁 Обработка: {os.path.basename(image_path)}")
        
        if not os.path.exists(image_path):
            return {"status": "error", "message": "Файл не найден"}
        
        # Анализируем фото
        results = self.recognizer.process_image(image_path)
        
        if not results:
            # Нет лиц
            is_dup, existing = self.is_duplicate(image_path, self.no_faces_dir)
            if is_dup:
                print(f"   ⏭️ Дубликат (уже есть в no_faces)")
                return {"status": "duplicate", "dest_path": existing}
            
            dest_path = self._copy_file(image_path, self.no_faces_dir)
            return {"status": "no_faces", "dest_path": dest_path}
        
        # Сортируем по лицам
        sorted_info = []
        for face_data in results:
            person_name = face_data["name"]
            confidence = face_data["confidence"]
            
            if person_name == "Неизвестный":
                person_dir = self.unknown_dir
            else:
                person_dir = os.path.join(self.base_output_dir, person_name)
                Path(person_dir).mkdir(exist_ok=True, parents=True)
            
            # Проверяем дубликат
            is_dup, existing = self.is_duplicate(image_path, person_dir)
            if is_dup:
                print(f"   ⏭️ Дубликат {person_name} (уже есть)")
                sorted_info.append({
                    "person": person_name,
                    "confidence": confidence,
                    "dest_path": existing,
                    "action": "duplicate"
                })
                continue
            
            # Копируем файл
            dest_path = self._copy_file(image_path, person_dir)
            print(f"   ✅ {person_name} -> {os.path.basename(dest_path)}")
            
            # Сохраняем в БД
            self.db.save_sorted_photo(image_path, dest_path, person_name, confidence)
            
            sorted_info.append({
                "person": person_name,
                "confidence": confidence,
                "dest_path": dest_path,
                "action": "copied"
            })
        
        return {"status": "sorted", "sorted_info": sorted_info}
    
    def _copy_file(self, src_path, dest_dir):
        """Копирует файл с уникальным именем на основе хеша"""
        file_hash = self.get_file_hash(src_path)
        ext = os.path.splitext(src_path)[1]
        
        # Используем хеш как имя файла для избежания дубликатов
        dest_path = os.path.join(dest_dir, f"{file_hash}{ext}")
        
        if not os.path.exists(dest_path):
            shutil.copy2(src_path, dest_path)
        
        return dest_path
    
    def resort_all_photos(self):
        """Пересортировать ВСЕ фото из unknown на основе новых знаний"""
        print("\n" + "="*60)
        print("🔄 ПЕРЕСОРТИРОВКА ВСЕХ ФОТО (новые знания)")
        print("="*60)
        
        if not os.path.exists(self.unknown_dir):
            print("📁 Папка unknown не найдена")
            return []
        
        # Находим все фото в unknown
        unknown_photos = []
        for file in os.listdir(self.unknown_dir):
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                unknown_photos.append(os.path.join(self.unknown_dir, file))
        
        print(f"📸 Найдено {len(unknown_photos)} фото в папке unknown")
        
        results = []
        for photo_path in unknown_photos:
            print(f"\n🔍 Проверяем: {os.path.basename(photo_path)}")
            
            # Анализируем заново
            analysis = self.recognizer.process_image(photo_path)
            
            if analysis:
                for face_data in analysis:
                    person_name = face_data["name"]
                    confidence = face_data["confidence"]
                    
                    if person_name != "Неизвестный" and confidence > 0.5:
                        # О! Теперь мы знаем кто это!
                        print(f"   ✅ РАСПОЗНАН: {person_name} (уверенность: {confidence:.2%})")
                        
                        # Создаем папку для человека
                        person_dir = os.path.join(self.base_output_dir, person_name)
                        Path(person_dir).mkdir(exist_ok=True, parents=True)
                        
                        # Проверяем дубликат
                        is_dup, existing = self.is_duplicate(photo_path, person_dir)
                        if is_dup:
                            print(f"   ⏭️ Фото уже есть в папке {person_name}")
                            # Удаляем из unknown
                            os.remove(photo_path)
                            results.append({
                                "file": os.path.basename(photo_path),
                                "action": "removed_duplicate",
                                "person": person_name
                            })
                        else:
                            # Копируем в папку человека
                            dest_path = self._copy_file(photo_path, person_dir)
                            print(f"   📁 ПЕРЕМЕЩЕНО: {dest_path}")
                            
                            # Сохраняем в БД
                            self.db.save_sorted_photo(photo_path, dest_path, person_name, confidence)
                            
                            # Удаляем из unknown
                            os.remove(photo_path)
                            results.append({
                                "file": os.path.basename(photo_path),
                                "action": "moved_to_known",
                                "person": person_name,
                                "dest_path": dest_path
                            })
                        break
                    else:
                        print(f"   ⚠️ Остается неизвестным (уверенность: {confidence:.2%})")
            else:
                # Нет лиц - перемещаем в no_faces
                no_faces_path = os.path.join(self.no_faces_dir, os.path.basename(photo_path))
                if not os.path.exists(no_faces_path):
                    shutil.move(photo_path, no_faces_path)
                    print(f"   📁 Перемещено в no_faces")
                    results.append({
                        "file": os.path.basename(photo_path),
                        "action": "moved_to_no_faces"
                    })
        
        print("\n" + "="*60)
        print(f"✅ ПЕРЕСОРТИРОВКА ЗАВЕРШЕНА!")
        print(f"📊 Распознано новых лиц: {len([r for r in results if r['action'] == 'moved_to_known'])}")
        print("="*60 + "\n")
        
        return results
    
    def sort_folder(self, folder_path, progress_callback=None):
        """Сортировка новой папки (без дубликатов)"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        results = []
        
        # Находим все фото
        photos = []
        for file in os.listdir(folder_path):
            if os.path.splitext(file)[1].lower() in image_extensions:
                photos.append(os.path.join(folder_path, file))
        
        total = len(photos)
        print(f"\n📸 Найдено {total} новых фото")
        
        for i, photo_path in enumerate(photos):
            if progress_callback:
                progress_callback(i + 1, total, os.path.basename(photo_path))
            
            result = self.sort_photo(photo_path)
            results.append({
                "file": os.path.basename(photo_path),
                "result": result
            })
        
        return results
