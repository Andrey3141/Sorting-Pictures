import os
import cv2
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from ui_components import AnimatedButton

class TrainingDialog(QDialog):
    def __init__(self, db, recognizer, parent=None):
        super().__init__(parent)
        self.db = db
        self.recognizer = recognizer
        self.parent = parent
        self.setWindowTitle("Обучение модели - Face Organizer AI")
        self.setGeometry(200, 200, 1000, 700)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
            }
            QLabel {
                color: white;
            }
            QListWidget {
                background-color: #16213e;
                border: none;
                border-radius: 10px;
                padding: 10px;
            }
            QListWidget::item {
                background-color: #0f3460;
                border-radius: 8px;
                margin: 5px;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
            }
            QLineEdit {
                background-color: #16213e;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                padding: 10px;
                color: white;
                font-size: 14px;
            }
            QTextEdit {
                background-color: #16213e;
                border: 1px solid #4CAF50;
                border-radius: 8px;
                color: #00ff00;
                font-family: monospace;
            }
        """)
        self.setup_ui()
        self.load_pending_faces()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Заголовок
        title = QLabel("🎓 ОБУЧЕНИЕ РАСПОЗНАВАНИЮ ЛИЦ")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Информация
        info_label = QLabel("Здесь показаны НЕИЗВЕСТНЫЕ лица, которые нейросеть обнаружила.\n"
                           "Вы можете:\n"
                           "• Присвоить имя - добавить человека в базу\n"
                           "• Отметить как НЕ ЛИЦО - если это ошибка (текстура, тень, узор)\n"
                           "• Пропустить - оставить как неизвестное")
        info_label.setStyleSheet("color: #aaa; font-size: 12px; margin: 10px;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        # Список неизвестных лиц
        self.faces_list = QListWidget()
        self.faces_list.setIconSize(QSize(120, 120))
        self.faces_list.setGridSize(QSize(150, 180))
        self.faces_list.setViewMode(QListView.ViewMode.IconMode)
        self.faces_list.setMovement(QListView.Movement.Static)
        self.faces_list.itemClicked.connect(self.on_item_selected)
        layout.addWidget(self.faces_list)
        
        # Панель ввода
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setSpacing(10)
        
        # Выбранное лицо
        self.selected_label = QLabel("Выберите лицо для обучения")
        self.selected_label.setStyleSheet("color: #FF9800; font-size: 12px;")
        input_layout.addWidget(self.selected_label)
        
        # Поле для имени
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Имя:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введите имя человека...")
        self.name_input.returnPressed.connect(self.label_face)
        name_layout.addWidget(self.name_input)
        input_layout.addLayout(name_layout)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        
        self.label_btn = AnimatedButton("✅ Присвоить имя", color="#4CAF50")
        self.label_btn.clicked.connect(self.label_face)
        
        self.not_face_btn = AnimatedButton("❌ ЭТО НЕ ЛИЦО", color="#9C27B0")
        self.not_face_btn.clicked.connect(self.mark_as_not_face)
        
        self.skip_btn = AnimatedButton("⏭️ Пропустить", color="#f44336")
        self.skip_btn.clicked.connect(self.skip_face)
        
        buttons_layout.addWidget(self.label_btn)
        buttons_layout.addWidget(self.not_face_btn)
        buttons_layout.addWidget(self.skip_btn)
        input_layout.addLayout(buttons_layout)
        
        layout.addWidget(input_widget)
        
        # Статистика
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #4CAF50; font-size: 12px; margin: 5px;")
        layout.addWidget(self.stats_label)
        
        # Лог действий
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("Лог действий...")
        layout.addWidget(self.log_text)
        
        # Кнопка закрытия
        close_btn = AnimatedButton("Закрыть", color="#2196F3")
        close_btn.clicked.connect(self.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # Автоскролл
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def load_pending_faces(self):
        pending_faces = self.db.get_pending_faces(limit=50)
        
        for face_id, thumbnail, image_path in pending_faces:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, face_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, image_path)
            
            pixmap = QPixmap()
            pixmap.loadFromData(thumbnail)
            icon = QIcon(pixmap)
            item.setIcon(icon)
            
            item.setText(f"ID: {face_id}")
            item.setSizeHint(QSize(140, 160))
            item.setToolTip(f"Файл: {os.path.basename(image_path)}")
            
            self.faces_list.addItem(item)
        
        count = len(pending_faces)
        self.stats_label.setText(f"📸 Найдено {count} неизвестных лиц для обучения")
        
        if count == 0:
            self.selected_label.setText("✅ Нет неизвестных лиц! Все лица распознаны.")
            self.label_btn.setEnabled(False)
            self.not_face_btn.setEnabled(False)
            self.skip_btn.setEnabled(False)
    
    def on_item_selected(self, item):
        face_id = item.data(Qt.ItemDataRole.UserRole)
        self.selected_label.setText(f"✅ Выбрано лицо ID: {face_id}")
        self.name_input.setFocus()
    
    def label_face(self):
        current = self.faces_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Ошибка", "Выберите лицо для разметки")
            return
        
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя")
            return
        
        face_id = current.data(Qt.ItemDataRole.UserRole)
        
        if self.db.label_unknown_face(face_id, name):
            self.recognizer.load_known_faces()
            self.faces_list.takeItem(self.faces_list.row(current))
            self.name_input.clear()
            self.selected_label.setText("Выберите лицо для обучения")
            
            self.log_message(f"✅ Лицо ID {face_id} добавлено как '{name}'")
            QMessageBox.information(self, "Успех", f"✅ Лицо добавлено как '{name}'")
            
            if self.faces_list.count() == 0:
                self.log_message("🎉 Все лица размечены! Обучение завершено.")
                QMessageBox.information(self, "Обучение завершено", "Все лица размечены!")
                self.accept()
        else:
            self.log_message(f"❌ Ошибка: не удалось добавить лицо ID {face_id}")
            QMessageBox.critical(self, "Ошибка", "Не удалось добавить лицо")
    
    def mark_as_not_face(self):
        """Пометить выбранную область как НЕ ЛИЦО (ложное срабатывание)"""
        current = self.faces_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Ошибка", "Выберите область для маркировки")
            return
        
        face_id = current.data(Qt.ItemDataRole.UserRole)
        image_path = current.data(Qt.ItemDataRole.UserRole + 1)
        
        reply = QMessageBox.question(
            self,
            "Маркировка НЕ ЛИЦО",
            f"Вы уверены, что эта область НЕ является лицом?\n\n"
            f"Это поможет нейросети не ошибаться в будущем.\n\n"
            f"Область будет удалена из списка неизвестных лиц.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Просто удаляем из unknown_faces (без сложной логики с cv2)
                self.db.delete_unknown_face(face_id)
                
                # Удаляем из списка
                self.faces_list.takeItem(self.faces_list.row(current))
                
                self.log_message(f"❌ Область ID {face_id} помечена как НЕ ЛИЦО и удалена")
                
                QMessageBox.information(
                    self, 
                    "Маркировка выполнена", 
                    "✅ Область помечена как НЕ ЛИЦО\n\n"
                    "При следующем анализе нейросеть будет игнорировать подобные области."
                )
                
            except Exception as e:
                self.log_message(f"❌ Ошибка: {e}")
                QMessageBox.critical(self, "Ошибка", f"Не удалось пометить: {e}")
        
        if self.faces_list.count() == 0:
            self.selected_label.setText("✅ Нет неизвестных лиц!")
    
    def skip_face(self):
        current = self.faces_list.currentItem()
        if current:
            face_id = current.data(Qt.ItemDataRole.UserRole)
            self.db.delete_unknown_face(face_id)
            self.faces_list.takeItem(self.faces_list.row(current))
            self.log_message(f"⏭️ Пропущено лицо ID {face_id}")
            
            if self.faces_list.count() == 0:
                self.selected_label.setText("✅ Нет неизвестных лиц!")