# PROJECT_STRUCTURE.md

face_organizer/
│
├── main.py                 # Главный файл приложения (GUI на PyQt6)
├── database.py             # Работа с SQLite базой данных
├── face_recognizer.py      # Распознавание лиц (FaceNet + Haar Cascade)
├── photo_sorter.py         # Логика сортировки фото по папкам
├── ui_components.py        # UI компоненты (анимированные кнопки, карточки лиц)
├── dialogs.py              # Диалоговые окна (обучение, ошибки)
├── workers.py              # Фоновые потоки для обработки фото
├── requirements.txt        # Зависимости проекта
├── CHANGELOG.md            # История изменений
├── README.md               # Документация проекта
├── PROJECT_STRUCTURE.md    # Структура проекта
│
├── models/                 # Директория с моделями ИИ
│   ├── haarcascade_frontalface_default.xml  # Детектор лиц OpenCV
│   ├── facenet.tflite                       # FaceNet модель для эмбеддингов
│   └── face_landmarker_v2_with_blendshapes.task  # Модель для эмоций (опционально)
│
├── sorted_photos/          # Папка с отсортированными фото (создается автоматически)
│   ├── Имя_человека/       # Папки с именами распознанных людей
│   ├── unknown/            # Неизвестные лица
│   └── no_faces/           # Фото без лиц
│
├── training_photos/        # Сохраненные фото лиц для обучения
│   └── Имя_человека/       # Фото конкретного человека
│
└── faces.db                # SQLite база данных с эмбеддингами лиц
