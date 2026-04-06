import 'package:flutter/services.dart';

class NativeFaceRecognizer {
  static const MethodChannel _channel = MethodChannel('face_recognizer');
  
  static Future<List<Map<String, dynamic>>> detectFaces(String imagePath) async {
    try {
      final List<dynamic> result = await _channel.invokeMethod('detectFaces', {
        'path': imagePath,
      });
      return result.cast<Map<String, dynamic>>();
    } catch (e) {
      print("Ошибка детекции лиц: $e");
      return [];
    }
  }
  
  static Future<List<double>> getEmbedding(String imagePath, {
    required int x, required int y, required int width, required int height
  }) async {
    try {
      final List<dynamic> result = await _channel.invokeMethod('getEmbedding', {
        'path': imagePath,
        'x': x,
        'y': y,
        'width': width,
        'height': height,
      });
      return result.cast<double>();
    } catch (e) {
      print("Ошибка получения эмбеддинга: $e");
      return [];
    }
  }
  
  static Future<void> close() async {
    await _channel.invokeMethod('close');
  }
}
