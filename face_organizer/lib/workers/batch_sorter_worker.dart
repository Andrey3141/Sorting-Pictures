import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';

class BatchSorterWorker {
  final Function(int, int, String) onProgress;
  final Function(List<Map<String, dynamic>>) onFinished;
  
  BatchSorterWorker({
    required this.onProgress,
    required this.onFinished,
  });
  
  static Future<List<Map<String, dynamic>>> sortFolder(dynamic sorter, String folderPath, Function(int, int, String) progressCallback) async {
    // TODO: Реализовать логику сортировки папки
    // Это заглушка, которая эмулирует работу
    
    List<Map<String, dynamic>> results = [];
    
    Directory folder = Directory(folderPath);
    List<FileSystemEntity> files = await folder.list().toList();
    
    Set<String> imageExtensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'};
    List<File> photoFiles = [];
    
    for (var entity in files) {
      if (entity is File) {
        String ext = entity.path.split('.').last.toLowerCase();
        if (imageExtensions.contains('.$ext')) {
          photoFiles.add(entity);
        }
      }
    }
    
    int total = photoFiles.length;
    int current = 0;
    
    for (File photo in photoFiles) {
      current++;
      String fileName = photo.path.split('/').last;
      
      // Отправляем прогресс
      progressCallback(current, total, fileName);
      
      // Имитация обработки
      await Future.delayed(const Duration(milliseconds: 50));
      
      // Добавляем результат
      results.add({
        'file': photo.path,
        'result': {
          'status': 'sorted',
          'message': 'Фото отсортировано',
        }
      });
    }
    
    return results;
  }
  
  void run(dynamic sorter, String folderPath) {
    // Эмуляция потока как в Python QThread
    Timer.run(() async {
      List<Map<String, dynamic>> results = await BatchSorterWorker.sortFolder(sorter, folderPath, onProgress);
      onFinished(results);
    });
  }
  
  // Статический метод для использования с Stream (альтернативный подход)
  static Stream<Map<String, dynamic>> runStream(dynamic sorter, String folderPath) async* {
    Directory folder = Directory(folderPath);
    List<FileSystemEntity> files = await folder.list().toList();
    
    Set<String> imageExtensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'};
    List<File> photoFiles = [];
    
    for (var entity in files) {
      if (entity is File) {
        String ext = entity.path.split('.').last.toLowerCase();
        if (imageExtensions.contains('.$ext')) {
          photoFiles.add(entity);
        }
      }
    }
    
    int total = photoFiles.length;
    int current = 0;
    List<Map<String, dynamic>> allResults = [];
    
    for (File photo in photoFiles) {
      current++;
      String fileName = photo.path.split('/').last;
      
      yield {
        'type': 'progress',
        'current': current,
        'total': total,
        'filename': fileName,
      };
      
      await Future.delayed(const Duration(milliseconds: 50));
      
      allResults.add({
        'file': photo.path,
        'result': {
          'status': 'sorted',
        }
      });
    }
    
    yield {
      'type': 'finished',
      'results': allResults,
    };
  }
}
