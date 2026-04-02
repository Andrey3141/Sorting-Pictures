from PyQt6.QtCore import QThread, QObject, pyqtSignal

class ImageProcessor(QThread):
    finished = pyqtSignal(object)
    face_detected = pyqtSignal(dict)
    progress = pyqtSignal(int)
    
    def __init__(self, recognizer, image_path):
        super().__init__()
        self.recognizer = recognizer
        self.image_path = image_path
    
    def run(self):
        self.progress.emit(0)
        results = self.recognizer.process_image(self.image_path, self.face_detected.emit)
        self.progress.emit(100)
        self.finished.emit(results)

class BatchSorterWorker(QThread):
    finished = pyqtSignal(list)
    progress = pyqtSignal(int, int, str)
    
    def __init__(self, sorter, folder_path):
        super().__init__()
        self.sorter = sorter
        self.folder_path = folder_path
    
    def run(self):
        results = self.sorter.sort_folder(self.folder_path, self.progress.emit)
        self.finished.emit(results)
