import "dart:math";
import 'dart:io';
import 'dart:typed_data';
import 'package:path/path.dart' as path;
import 'package:crypto/crypto.dart';
import 'package:image/image.dart' as img;
import 'native_face_recognizer.dart';
import '../database/face_database.dart';

class FaceRecognizer {
  final FaceDatabase db;
  Map<String, List<double>> knownFaces = {};
  
  FaceRecognizer(this.db) {
    loadKnownFaces();
  }
  
  Future<void> loadKnownFaces() async {
    knownFaces = await db.getAllFaces();
    print("📚 Загружено ${knownFaces.length} лиц");
  }
  
  Future<int> getKnownFacesCount() async {
    return knownFaces.length;
  }
  
  String getFileHash(String filePath) {
    try {
      final bytes = File(filePath).readAsBytesSync();
      return md5.convert(bytes).toString();
    } catch (e) {
      return "";
    }
  }
  
  Future<List<Map<String, dynamic>>> processImage(String imagePath, Function(Map<String, dynamic>) callback) async {
    final results = <Map<String, dynamic>>[];
    
    print("🔍 Анализ: ${path.basename(imagePath)}");
    
    // Вызываем нативный код для детекции лиц
    final faces = await NativeFaceRecognizer.detectFaces(imagePath);
    print("🔍 Найдено ${faces.length} лиц");
    
    final bytes = await File(imagePath).readAsBytes();
    final originalImg = img.decodeImage(bytes);
    
    for (int i = 0; i < faces.length; i++) {
      final face = faces[i];
      final x = face['x'] as int;
      final y = face['y'] as int;
      final w = face['width'] as int;
      final h = face['height'] as int;
      
      if (originalImg == null) continue;
      
      final faceRoi = img.copyCrop(originalImg, x: x, y: y, width: w, height: h);
      
      // Получаем эмбеддинг через нативный код
      final embedding = await NativeFaceRecognizer.getEmbedding(
        imagePath,
        x: x, y: y, width: w, height: h,
      );
      
      final (name, confidence) = recognizeFace(embedding);
      
      final thumbnailImg = img.copyResize(faceRoi, width: 100, height: 100);
      final thumbnail = Uint8List.fromList(img.encodeJpg(thumbnailImg));
      
      final faceData = <String, dynamic>{
        "id": i,
        "position": [x, y, w, h],
        "name": name,
        "confidence": confidence,
        "embedding": embedding,
        "is_known": name != "Неизвестный",
        "thumbnail": thumbnail,
        "face_hash": null,
      };
      
      if (!faceData["is_known"]) {
        await db.saveUnknownFace(imagePath, embedding, thumbnail);
        print("   👤 НЕИЗВЕСТНОЕ лицо #${i+1}");
      } else {
        print("   ✅ $name (${(confidence * 100).toStringAsFixed(1)}%)");
      }
      
      results.add(faceData);
      if (callback != null) callback(faceData);
    }
    
    return results;
  }
  
  (String name, double confidence) recognizeFace(List<double> embedding, {double threshold = 0.6}) {
    if (knownFaces.isEmpty) return ("Неизвестный", 0.0);
    
    String bestMatch = "Неизвестный";
    double bestDistance = 1.0;
    
    for (var entry in knownFaces.entries) {
      final known = entry.value;
      double distance = 0.0;
      
      for (int i = 0; i < embedding.length; i++) {
        distance += pow(embedding[i] - known[i], 2);
      }
      distance = sqrt(distance);
      
      if (distance < bestDistance && distance < threshold) {
        bestDistance = distance;
        bestMatch = entry.key;
      }
    }
    
    final confidence = 1 - (bestDistance / 2);
    return (bestMatch, confidence);
  }
  
  Future<bool> markAsFalsePositive(String imagePath, Map<String, dynamic> faceData) async {
    print("✅ Помечено как НЕ ЛИЦО");
    return true;
  }
  
  void dispose() {
    NativeFaceRecognizer.close();
  }
}
