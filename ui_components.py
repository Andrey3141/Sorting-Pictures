from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None, color="#4CAF50"):
        super().__init__(text, parent)
        self.default_color = color
        self.hover_color = self.adjust_brightness(color, 0.8)
        self.setStyleSheet(self.get_style(self.default_color))
        
    def adjust_brightness(self, hex_color, factor):
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def get_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.hover_color};
            }}
            QPushButton:pressed {{
                background-color: {self.adjust_brightness(color, 0.6)};
            }}
        """
    
    def enterEvent(self, event):
        self.setStyleSheet(self.get_style(self.hover_color))
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.setStyleSheet(self.get_style(self.default_color))
        super().leaveEvent(event)

class FaceCard(QFrame):
    def __init__(self, face_data, parent=None):
        super().__init__(parent)
        self.face_data = face_data
        self.setup_ui()
        self.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 15px;
                padding: 15px;
                min-width: 150px;
                max-width: 150px;
            }
            QLabel {
                color: white;
            }
        """)
    
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        pixmap = QPixmap()
        pixmap.loadFromData(self.face_data["thumbnail"])
        face_label = QLabel()
        face_label.setPixmap(pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio))
        face_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(face_label)
        
        self.name_label = QLabel(self.face_data['name'])
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.name_label)
        
        self.confidence_bar = QProgressBar()
        self.confidence_bar.setValue(int(self.face_data['confidence'] * 100))
        self.confidence_bar.setTextVisible(True)
        self.confidence_bar.setFormat("%p%")
        self.confidence_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                text-align: center;
                color: white;
                background-color: #34495e;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.confidence_bar)
        
        self.setLayout(layout)
    
    def update_name(self, new_name):
        self.face_data['name'] = new_name
        self.name_label.setText(new_name)
        self.confidence_bar.setValue(100)
    
    def add_not_face_button(self, callback):
        """Добавить кнопку 'Это не лицо'"""
        fp_btn = QPushButton("❌ ЭТО НЕ ЛИЦО")
        fp_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        fp_btn.clicked.connect(callback)
        self.layout().addWidget(fp_btn)