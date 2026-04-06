import 'dart:io';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'package:path/path.dart' as path;
import 'package:crypto/crypto.dart';
import '../database/face_database.dart';
import 'face_recognizer.dart';

class PhotoSorter {
  final FaceRecognizer recognizer;
  final FaceDatabase db;
  final String baseOutputDir;
  late String unknownDir;
  late String noFacesDir;
  
  PhotoSorter(this.recognizer, this.db, this.baseOutputDir) {
    _createDirectories();
  }
  
  void _createDirectories() {
    Directory(baseOutputDir).createSync(recursive: true);
    
    unknownDir = path.join(baseOutputDir, "unknown");
    noFacesDir = path.join(baseOutputDir, "no_faces");
    
    Directory(unknownDir).createSync(recursive: true);
    Directory(noFacesDir).createSync(recursive: true);
  }
  
  Future<String> getFileHash(String filePath) async {
    try {
      final file = File(filePath);
      final bytes = await file.readAsBytes();
      final hash = md5.convert(bytes);
      return hash.toString();
    } catch (e) {
      print("Ошибка вычисления хеша: $e");
      return "";
    }
  }
  
  Future<(bool, String?)> isDuplicate(String filePath, String targetDir) async {
    final targetDirectory = Directory(targetDir);
    if (!await targetDirectory.exists()) {
      return (false, null);
    }
    
    final fileHash = await getFileHash(filePath);
    if (fileHash.isEmpty) return (false, null);
    
    final files = await targetDirectory.list().where((entity) => entity is File).toList();
    
    for (var entity in files) {
      final existingFile = entity as File;
      try {
        final existingHash = await getFileHash(existingFile.path);
        if (existingHash == fileHash) {
          return (true, existingFile.path);
        }
      } catch (e) {
        continue;
      }
    }
    
    return (false, null);
  }
  
  Future<String> copyFile(String srcPath, String destDir) async {
    final fileHash = await getFileHash(srcPath);
    final ext = path.extension(srcPath);
    
    final destPath = path.join(destDir, "$fileHash$ext");
    final destFile = File(destPath);
    
    if (!await destFile.exists()) {
      await File(srcPath).copy(destPath);
    }
    
    return destPath;
  }
  
  Future<Map<String, dynamic>> sortPhoto(String imagePath) async {
    print("\n📁 Обработка: ${path.basename(imagePath)}");
    
    final imageFile = File(imagePath);
    if (!await imageFile.exists()) {
      return {"status": "error", "message": "Файл не найден"};
    }
    
    // Анализируем фото
    final results = await recognizer.processImage(imagePath, (faceData) {});
    
    if (results.isEmpty) {
      // Нет лиц
      final (isDup, existing) = await isDuplicate(imagePath, noFacesDir);
      if (isDup) {
        print("   ⏭️ Дубликат (уже есть в no_faces)");
        return {"status": "duplicate", "dest_path": existing};
      }
      
      final destPath = await copyFile(imagePath, noFacesDir);
      return {"status": "no_faces", "dest_path": destPath};
    }
    
    // Сортируем по лицам
    final sortedInfo = <Map<String, dynamic>>[];
    
    for (var faceData in results) {
      final personName = faceData["name"] as String;
      final confidence = faceData["confidence"] as double;
      
      String personDir;
      if (personName == "Неизвестный") {
        personDir = unknownDir;
      } else {
        personDir = path.join(baseOutputDir, personName);
        await Directory(personDir).create(recursive: true);
      }
      
      // Проверяем дубликат
      final (isDup, existing) = await isDuplicate(imagePath, personDir);
      if (isDup) {
        print("   ⏭️ Дубликат $personName (уже есть)");
        sortedInfo.add({
          "person": personName,
          "confidence": confidence,
          "dest_path": existing,
          "action": "duplicate"
        });
        continue;
      }
      
      // Копируем файл
      final destPath = await copyFile(imagePath, personDir);
      print("   ✅ $personName -> ${path.basename(destPath)}");
      
      // Сохраняем в БД
      await db.saveSortedPhoto(imagePath, destPath, personName, confidence);
      
      sortedInfo.add({
        "person": personName,
        "confidence": confidence,
        "dest_path": destPath,
        "action": "copied"
      });
    }
    
    return {"status": "sorted", "sorted_info": sortedInfo};
  }
  
  Future<List<Map<String, dynamic>>> resortAllPhotos() async {
    print("\n" + "=" * 60);
    print("🔄 ПЕРЕСОРТИРОВКА ВСЕХ ФОТО (новые знания)");
    print("=" * 60);
    
    final unknownDirectory = Directory(unknownDir);
    if (!await unknownDirectory.exists()) {
      print("📁 Папка unknown не найдена");
      return [];
    }
    
    // Находим все фото в unknown
    final unknownPhotos = <String>[];
    final files = await unknownDirectory.list().where((entity) => entity is File).toList();
    
    for (var file in files) {
      final fileName = path.basename(file.path).toLowerCase();
      if (fileName.endsWith('.jpg') || fileName.endsWith('.jpeg') || 
          fileName.endsWith('.png') || fileName.endsWith('.bmp')) {
        unknownPhotos.add(file.path);
      }
    }
    
    print("📸 Найдено ${unknownPhotos.length} фото в папке unknown");
    
    final results = <Map<String, dynamic>>[];
    
    for (var photoPath in unknownPhotos) {
      print("\n🔍 Проверяем: ${path.basename(photoPath)}");
      
      // Анализируем заново
      final analysis = await recognizer.processImage(photoPath, (faceData) {});
      
      if (analysis.isNotEmpty) {
        bool recognized = false;
        for (var faceData in analysis) {
          final personName = faceData["name"] as String;
          final confidence = faceData["confidence"] as double;
          
          if (personName != "Неизвестный" && confidence > 0.5) {
            print("   ✅ РАСПОЗНАН: $personName (уверенность: ${(confidence * 100).toStringAsFixed(1)}%)");
            
            // Создаем папку для человека
            final personDir = path.join(baseOutputDir, personName);
            await Directory(personDir).create(recursive: true);
            
            // Проверяем дубликат
            final (isDup, existing) = await isDuplicate(photoPath, personDir);
            if (isDup) {
              print("   ⏭️ Фото уже есть в папке $personName");
              // Удаляем из unknown
              await File(photoPath).delete();
              results.add({
                "file": path.basename(photoPath),
                "action": "removed_duplicate",
                "person": personName
              });
            } else {
              // Копируем в папку человека
              final destPath = await copyFile(photoPath, personDir);
              print("   📁 ПЕРЕМЕЩЕНО: $destPath");
              
              // Сохраняем в БД
              await db.saveSortedPhoto(photoPath, destPath, personName, confidence);
              
              // Удаляем из unknown
              await File(photoPath).delete();
              results.add({
                "file": path.basename(photoPath),
                "action": "moved_to_known",
                "person": personName,
                "dest_path": destPath
              });
            }
            recognized = true;
            break;
          } else {
            print("   ⚠️ Остается неизвестным (уверенность: ${(confidence * 100).toStringAsFixed(1)}%)");
          }
        }
        if (!recognized) {
          // Остается неизвестным - ничего не делаем
        }
      } else {
        // Нет лиц - перемещаем в no_faces
        final noFacesPath = path.join(noFacesDir, path.basename(photoPath));
        final noFacesFile = File(noFacesPath);
        if (!await noFacesFile.exists()) {
          await File(photoPath).rename(noFacesPath);
          print("   📁 Перемещено в no_faces");
          results.add({
            "file": path.basename(photoPath),
            "action": "moved_to_no_faces"
          });
        }
      }
    }
    
    print("\n" + "=" * 60);
    print("✅ ПЕРЕСОРТИРОВКА ЗАВЕРШЕНА!");
    final movedCount = results.where((r) => r['action'] == 'moved_to_known').length;
    print("📊 Распознано новых лиц: $movedCount");
    print("=" * 60 + "\n");
    
    return results;
  }
  
  Future<List<Map<String, dynamic>>> sortFolder(String folderPath, Function(int, int, String)? progressCallback) async {
    final imageExtensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'};
    final photos = <String>[];
    
    final folder = Directory(folderPath);
    final files = await folder.list().where((entity) => entity is File).toList();
    
    for (var file in files) {
      final ext = path.extension(file.path).toLowerCase();
      if (imageExtensions.contains(ext)) {
        photos.add(file.path);
      }
    }
    
    final total = photos.length;
    print("\n📸 Найдено $total новых фото");
    
    final results = <Map<String, dynamic>>[];
    
    for (int i = 0; i < total; i++) {
      final photoPath = photos[i];
      if (progressCallback != null) {
        progressCallback(i + 1, total, path.basename(photoPath));
      }
      
      final result = await sortPhoto(photoPath);
      results.add({
        "file": path.basename(photoPath),
        "result": result
      });
    }
    
    return results;
  }
}
