#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from database import FaceDatabase
from face_recognizer import FaceRecognizer
from photo_sorter import PhotoSorter
from ui_components import AnimatedButton, FaceCard
from dialogs import TrainingDialog
from workers import ImageProcessor, BatchSorterWorker

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Face Organizer AI - Сортировка фото по лицам")
        self.setGeometry(100, 100, 1400, 900)
        
        # Инициализация БД и компонентов
        self.db = FaceDatabase()
        self.recognizer = FaceRecognizer(self.db)
        self.sorter = PhotoSorter(self.recognizer, self.db, "sorted_photos")
        
        self.setup_ui()
        self.apply_styles()
        self.current_image_path = None
        self.current_face_data = None
        
        self.setAcceptDrops(True)
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Верхняя панель с кнопками
        top_bar = QHBoxLayout()
        top_bar.setSpacing(15)
        
        # Кнопки действий
        self.upload_btn = AnimatedButton("📤 Загрузить фото", color="#4CAF50")
        self.upload_btn.clicked.connect(self.upload_image)
        
        self.sort_btn = AnimatedButton("📁 Сортировать это фото", color="#2196F3")
        self.sort_btn.clicked.connect(self.sort_current_image)
        
        self.batch_btn = AnimatedButton("📂 Сортировать всю папку", color="#9C27B0")
        self.batch_btn.clicked.connect(self.batch_sort_folder)
        
        self.train_btn = AnimatedButton("🎓 Обучить модель", color="#FF9800")
        self.train_btn.clicked.connect(self.open_training_panel)
        
        self.open_folder_btn = AnimatedButton("📂 Открыть папку с результатами", color="#00BCD4")
        self.open_folder_btn.clicked.connect(self.open_sorted_folder)
        
        self.clear_btn = AnimatedButton("🗑️ Очистить всё", color="#f44336")
        self.clear_btn.clicked.connect(self.clear_all)
        
        top_bar.addWidget(self.upload_btn)
        top_bar.addWidget(self.sort_btn)
        top_bar.addWidget(self.batch_btn)
        top_bar.addWidget(self.train_btn)
        top_bar.addWidget(self.open_folder_btn)
        top_bar.addWidget(self.clear_btn)
        top_bar.addStretch()
        
        # Статистика
        self.stats_label = QLabel("Готов к работе")
        self.stats_label.setStyleSheet("color: #4CAF50; font-size: 12px; font-weight: bold;")
        top_bar.addWidget(self.stats_label)
        
        main_layout.addLayout(top_bar)
        
        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #4CAF50; max-height: 2px;")
        main_layout.addWidget(line)
        
        # Область изображения
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setStyleSheet("""
            QScrollArea {
                border: 2px dashed #4CAF50;
                border-radius: 15px;
                background-color: #0f0f1a;
            }
        """)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(450)
        self.image_label.setText("📸 ПЕРЕТАЩИТЕ ИЗОБРАЖЕНИЕ СЮДА\n\nили нажмите 'Загрузить фото'")
        self.image_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 18px;
                padding: 50px;
            }
        """)
        
        self.image_scroll.setWidget(self.image_label)
        main_layout.addWidget(self.image_scroll)
        
        # Область результатов (распознанные лица)
        results_label = QLabel("🔍 РАСПОЗНАННЫЕ ЛИЦА:")
        results_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px; color: #4CAF50;")
        main_layout.addWidget(results_label)
        
        self.faces_scroll = QScrollArea()
        self.faces_scroll.setWidgetResizable(True)
        self.faces_scroll.setMaximumHeight(280)
        self.faces_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        self.faces_container = QWidget()
        self.faces_layout = QHBoxLayout(self.faces_container)
        self.faces_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.faces_layout.setSpacing(15)
        self.faces_scroll.setWidget(self.faces_container)
        main_layout.addWidget(self.faces_scroll)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                text-align: center;
                color: white;
                background-color: #34495e;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 5px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Лог сообщений
        log_label = QLabel("📋 ЛОГ ОПЕРАЦИЙ:")
        log_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px; color: #4CAF50;")
        main_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(180)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a2e;
                color: #00ff00;
                border: 1px solid #4CAF50;
                border-radius: 10px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                padding: 10px;
            }
        """)
        main_layout.addWidget(self.log_text)
        
        # Статус-бар
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #1a1a2e;
                color: white;
                padding: 5px;
            }
        """)
        
        self.update_stats()
        self.log_message("✅ Программа запущена. Готова к работе!")
    
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f0f1a, stop:1 #1a1a2e);
            }
            QScrollBar:vertical {
                border: none;
                background: #1a1a2e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #4CAF50;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #45a049;
            }
            QScrollBar:horizontal {
                border: none;
                background: #1a1a2e;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #4CAF50;
                border-radius: 6px;
            }
        """)
    
    def update_stats(self):
        known_count = len(self.recognizer.known_faces)
        self.stats_label.setText(f"📚 БАЗА ДАННЫХ: {known_count} человек")
    
    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # Автоскролл вниз
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def open_sorted_folder(self):
        """Открыть папку с отсортированными фото"""
        folder_path = os.path.abspath("sorted_photos")
        if os.path.exists(folder_path):
            os.system(f'xdg-open "{folder_path}"' if sys.platform != "win32" else f'start "" "{folder_path}"')
            self.log_message(f"📂 Открыта папка: {folder_path}")
        else:
            QMessageBox.warning(self, "Ошибка", "Папка sorted_photos еще не создана.\nСначала отсортируйте хотя бы одно фото.")
    
    def upload_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите изображение", "", 
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        
        if file_path:
            self.current_image_path = file_path
            self.process_image(file_path)
    
    def sort_current_image(self):
        """Сортировка текущего изображения"""
        if not self.current_image_path:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите фото!")
            return
        
        if not os.path.exists(self.current_image_path):
            QMessageBox.warning(self, "Ошибка", "Файл не найден!")
            return
        
        self.log_message(f"🚀 Начинаем сортировку: {os.path.basename(self.current_image_path)}")
        self.sort_image(self.current_image_path)
    
    def sort_image(self, image_path):
        """Сортировка одного изображения"""
        self.current_image_path = image_path
        
        # Показываем прогресс
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.statusBar().showMessage("📁 Сортировка изображения...")
        
        # Запускаем сортировку в потоке
        self.sort_thread = QThread()
        self.sort_worker = SortWorker(self.sorter, image_path)
        self.sort_worker.moveToThread(self.sort_thread)
        
        self.sort_thread.started.connect(self.sort_worker.run)
        self.sort_worker.finished.connect(self.on_sort_finished)
        self.sort_worker.finished.connect(self.sort_thread.quit)
        self.sort_worker.finished.connect(self.sort_worker.deleteLater)
        self.sort_thread.finished.connect(self.sort_thread.deleteLater)
        
        self.sort_thread.start()
    
    def on_sort_finished(self, result):
        self.progress_bar.setVisible(False)
        
        if result["status"] == "sorted":
            self.statusBar().showMessage("✅ Сортировка завершена!", 3000)
            self.log_message(f"✅ Фото отсортировано!")
            for info in result.get("sorted_info", []):
                self.log_message(f"   👤 {info['person']} (уверенность: {info['confidence']:.2%})")
                self.log_message(f"   📁 Сохранено: {info['dest_path']}")
            
            QMessageBox.information(
                self, 
                "Сортировка завершена", 
                f"✅ Фото успешно отсортировано!\n\n"
                f"👤 {result['sorted_info'][0]['person']}\n"
                f"📊 Уверенность: {result['sorted_info'][0]['confidence']:.2%}\n"
                f"📁 Сохранено в: sorted_photos/"
            )
        elif result["status"] == "no_faces":
            self.statusBar().showMessage("⚠️ Лица не обнаружены", 3000)
            self.log_message(f"⚠️ Лица не обнаружены на фото")
            QMessageBox.warning(self, "Результат", "На фото не обнаружены лица!")
        else:
            self.statusBar().showMessage("❌ Ошибка сортировки", 3000)
            self.log_message(f"❌ Ошибка: {result.get('message', 'Неизвестная ошибка')}")
    
    def batch_sort_folder(self):
        """Сортировка всей папки"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Выберите папку с фото", os.path.expanduser("~/Pictures")
        )
        
        if not folder_path:
            return
        
        # Подсчитываем количество фото
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        photo_count = 0
        for file in os.listdir(folder_path):
            if os.path.splitext(file)[1].lower() in image_extensions:
                photo_count += 1
        
        if photo_count == 0:
            QMessageBox.warning(self, "Ошибка", "В выбранной папке нет фото!")
            return
        
        reply = QMessageBox.question(
            self, 
            "Пакетная сортировка",
            f"📁 Папка: {folder_path}\n"
            f"📸 Найдено фото: {photo_count}\n\n"
            f"Фото будут скопированы в папку 'sorted_photos'\n"
            f"Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.log_message("")
            self.log_message("=" * 60)
            self.log_message(f"🚀 НАЧАЛО ПАКЕТНОЙ СОРТИРОВКИ")
            self.log_message(f"📁 Папка: {folder_path}")
            self.log_message(f"📸 Всего фото: {photo_count}")
            self.log_message("=" * 60)
            
            # Запускаем сортировку
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, photo_count)
            self.statusBar().showMessage("📁 Сортировка папки...")
            
            self.batch_thread = BatchSorterWorker(self.sorter, folder_path)
            self.batch_thread.progress.connect(self.on_batch_progress)
            self.batch_thread.finished.connect(self.on_batch_finished)
            self.batch_thread.start()
    
    def on_batch_progress(self, current, total, filename):
        """Прогресс сортировки папки"""
        self.progress_bar.setValue(current)
        self.statusBar().showMessage(f"📁 Сортировка: {current}/{total} - {filename}")
        self.log_message(f"[{current}/{total}] {filename}")
    
    def on_batch_finished(self, results):
        """Завершение сортировки папки"""
        self.progress_bar.setVisible(False)
        
        # Подсчет статистики
        total = len(results)
        sorted_count = 0
        no_faces_count = 0
        error_count = 0
        
        for r in results:
            if r["result"]["status"] == "sorted":
                sorted_count += 1
            elif r["result"]["status"] == "no_faces":
                no_faces_count += 1
            else:
                error_count += 1
        
        self.log_message("")
        self.log_message("=" * 60)
        self.log_message(f"✅ ПАКЕТНАЯ СОРТИРОВКА ЗАВЕРШЕНА!")
        self.log_message(f"📸 Всего фото: {total}")
        self.log_message(f"✅ С лицами: {sorted_count}")
        self.log_message(f"👤 Без лиц: {no_faces_count}")
        self.log_message(f"❌ Ошибок: {error_count}")
        self.log_message(f"📁 Результаты: {os.path.abspath('sorted_photos')}")
        self.log_message("=" * 60)
        
        self.statusBar().showMessage(f"✅ Сортировка завершена! Обработано: {total} фото", 5000)
        
        QMessageBox.information(
            self, 
            "Сортировка завершена", 
            f"📊 РЕЗУЛЬТАТЫ:\n\n"
            f"📸 Всего фото: {total}\n"
            f"✅ С лицами: {sorted_count}\n"
            f"👤 Без лиц: {no_faces_count}\n"
            f"❌ Ошибок: {error_count}\n\n"
            f"📁 Результаты сохранены в:\n{os.path.abspath('sorted_photos')}"
        )
    
    def process_image(self, image_path):
        """Анализ изображения без сортировки"""
        self.current_image_path = image_path
        
        # Отображаем фото
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(
            self.image_scroll.width() - 40, 
            450, 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        
        # Очищаем старые карточки
        self.clear_faces_layout()
        
        # Показываем прогресс
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.statusBar().showMessage("🔍 Анализ изображения...")
        self.log_message(f"🔍 Анализ: {os.path.basename(image_path)}")
        
        # Запускаем анализ в потоке
        self.processor_thread = ImageProcessor(self.recognizer, image_path)
        self.processor_thread.face_detected.connect(self.add_face_card)
        self.processor_thread.finished.connect(self.on_processing_finished)
        self.processor_thread.progress.connect(self.update_progress)
        self.processor_thread.start()
    
    def update_progress(self, value):
        if value == 100:
            self.progress_bar.setVisible(False)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(value)
    
    def on_processing_finished(self, results):
        self.progress_bar.setVisible(False)
        
        if not results:
            self.statusBar().showMessage("⚠️ Лица не обнаружены", 5000)
            self.log_message("⚠️ Лица не обнаружены на фото")
            return
        
        unknown_count = len([f for f in results if not f["is_known"]])
        
        if unknown_count > 0:
            self.statusBar().showMessage(f"⚠️ Обнаружено {unknown_count} неизвестных лиц", 5000)
            self.log_message(f"⚠️ Обнаружено {unknown_count} неизвестных лиц")
            self.log_message("💡 Нажмите 'Обучить модель' чтобы добавить новые лица")
        else:
            self.statusBar().showMessage(f"✅ Анализ завершен! Распознано {len(results)} лиц", 5000)
            self.log_message(f"✅ Анализ завершен! Распознано {len(results)} лиц")
        
        self.update_stats()
    
    def add_face_card(self, face_data):
        card = FaceCard(face_data)
        
        # Кнопка "Это НЕ лицо" (для любых обнаруженных областей)
        card.add_not_face_button(lambda: self.mark_as_false_positive(face_data, card))
        
        if not face_data["is_known"]:
            quick_train_btn = QPushButton("🏷️ ДОБАВИТЬ ИМЯ")
            quick_train_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
            """)
            quick_train_btn.clicked.connect(lambda: self.quick_label_face(face_data, card))
            card.layout().addWidget(quick_train_btn)
        
        self.faces_layout.addWidget(card)
    
    def quick_label_face(self, face_data, card):
        name, ok = QInputDialog.getText(
            self, 
            "Добавить человека", 
            "Введите имя для этого лица:",
            QLineEdit.EchoMode.Normal
        )
        
        if ok and name.strip():
            name = name.strip()
            self.db.add_face(name, face_data["embedding"])
            self.recognizer.load_known_faces()
            card.update_name(name)
            self.update_stats()
            self.statusBar().showMessage(f"✅ Человек '{name}' добавлен в базу!", 3000)
            self.log_message(f"✅ Добавлен новый человек: {name}")
            
            # Спрашиваем, отсортировать ли текущее фото
            reply = QMessageBox.question(
                self, 
                "Сортировка", 
                f"Отсортировать текущее фото с новыми данными?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes and self.current_image_path:
                self.sort_image(self.current_image_path)
    
    def clear_faces_layout(self):
        while self.faces_layout.count():
            child = self.faces_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def clear_all(self):
        self.clear_faces_layout()
        self.image_label.clear()
        self.image_label.setText("📸 ПЕРЕТАЩИТЕ ИЗОБРАЖЕНИЕ СЮДА\n\nили нажмите 'Загрузить фото'")
        self.current_image_path = None
        self.statusBar().showMessage("Очищено", 2000)
        self.log_message("🗑️ Интерфейс очищен")
    
    def open_training_panel(self):
        dialog = TrainingDialog(self.db, self.recognizer, self)
        if dialog.exec():
            self.recognizer.load_known_faces()
            self.update_stats()
            self.statusBar().showMessage("✅ Модель успешно обучена!", 3000)
            self.log_message("✅ Модель успешно обучена новым лицам")
            
            if self.current_image_path:
                reply = QMessageBox.question(
                    self, 
                    "Обновить результат", 
                    "Переобработать текущее изображение с новыми данными?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.process_image(self.current_image_path)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                self.current_image_path = file
                self.process_image(file)
                break

    def mark_as_false_positive(self, face_data, card):
        """Пометить область как НЕ лицо"""
        reply = QMessageBox.question(
            self,
            "Маркировка НЕ лицо",
            f"Вы уверены, что эта область НЕ является лицом?\n\n"
            f"Это поможет нейросети не ошибаться в будущем.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success = self.recognizer.mark_as_false_positive(self.current_image_path, face_data)
            
            if success:
                self.log_message(f"❌ Область помечена как НЕ ЛИЦО")
                self.statusBar().showMessage("✅ Область помечена как не лицо", 3000)
                
                # Удаляем карточку из UI
                card.deleteLater()
                
                # Спрашиваем, переобработать ли фото
                reply2 = QMessageBox.question(
                    self,
                    "Переобработать?",
                    "Переобработать фото с новыми знаниями?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply2 == QMessageBox.StandardButton.Yes:
                    self.process_image(self.current_image_path)
            else:
                self.log_message(f"❌ Ошибка при маркировке")
                self.statusBar().showMessage("❌ Ошибка при маркировке", 3000)

class SortWorker(QObject):
    finished = pyqtSignal(dict)
    
    def __init__(self, sorter, image_path):
        super().__init__()
        self.sorter = sorter
        self.image_path = image_path
    
    def run(self):
        result = self.sorter.sort_photo(self.image_path)
        self.finished.emit(result)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    window.raise_()
    window.activateWindow()
    
    print("✅ GUI окно открыто!")
    print("Если окна не видно, проверьте другие рабочие столы")
    
    sys.exit(app.exec())
