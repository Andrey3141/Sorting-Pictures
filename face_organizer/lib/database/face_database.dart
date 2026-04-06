import 'dart:io';
import 'dart:convert';
import 'dart:typed_data';
import 'package:sqflite/sqflite.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';

class FaceDatabase {
  static Database? _database;
  static const String dbName = 'faces.db';
  static bool _initialized = false;
  
  static void initDesktop() {
    if (!_initialized && !Platform.isAndroid && !Platform.isIOS) {
      sqfliteFfiInit();
      databaseFactory = databaseFactoryFfi;
      _initialized = true;
    }
  }
  
  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }
  
  Future<Database> _initDatabase() async {
    // Инициализация для десктопа
    initDesktop();
    
    String dbPath;
    if (Platform.isAndroid || Platform.isIOS) {
      dbPath = join(await getDatabasesPath(), dbName);
    } else {
      // Для десктопа (Linux, Windows, MacOS)
      final appDir = await getApplicationDocumentsDirectory();
      dbPath = join(appDir.path, dbName);
    }
    
    return await openDatabase(
      dbPath,
      version: 1,
      onCreate: (db, version) async {
        await _createTables(db);
      },
    );
  }
  
  Future<void> _createTables(Database db) async {
    await db.execute('''
      CREATE TABLE IF NOT EXISTS known_faces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        embedding TEXT NOT NULL,
        created_at TEXT,
        last_seen TEXT,
        times_seen INTEGER DEFAULT 1
      )
    ''');
    
    await db.execute('''
      CREATE TABLE IF NOT EXISTS unknown_faces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_path TEXT,
        embedding TEXT,
        thumbnail BLOB,
        detected_at TEXT,
        status TEXT DEFAULT 'pending'
      )
    ''');
    
    await db.execute('''
      CREATE TABLE IF NOT EXISTS processed_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_hash TEXT UNIQUE,
        file_path TEXT,
        processed_at TEXT,
        faces_count INTEGER
      )
    ''');
    
    await db.execute('''
      CREATE TABLE IF NOT EXISTS sorted_photos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        original_path TEXT,
        sorted_path TEXT,
        person_name TEXT,
        confidence REAL,
        sorted_at TEXT
      )
    ''');
    
    await db.execute('''
      CREATE TABLE IF NOT EXISTS false_positives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_path TEXT,
        face_position TEXT,
        face_hash TEXT,
        thumbnail BLOB,
        created_at TEXT
      )
    ''');
  }
  
  Future<int> addFace(String name, List<double> embedding) async {
    final db = await database;
    String embeddingJson = jsonEncode(embedding);
    String now = DateTime.now().toIso8601String();
    
    List<Map<String, dynamic>> existing = await db.query(
      'known_faces',
      where: 'name = ?',
      whereArgs: [name],
    );
    
    if (existing.isNotEmpty) {
      List<double> oldEmbedding = List<double>.from(jsonDecode(existing.first['embedding'] as String));
      List<double> newEmbedding = List<double>.generate(oldEmbedding.length, (i) => (oldEmbedding[i] + embedding[i]) / 2);
      String newEmbeddingJson = jsonEncode(newEmbedding);
      int timesSeen = (existing.first['times_seen'] as int) + 1;
      
      return await db.update(
        'known_faces',
        {
          'embedding': newEmbeddingJson,
          'times_seen': timesSeen,
          'last_seen': now,
        },
        where: 'name = ?',
        whereArgs: [name],
      );
    } else {
      return await db.insert('known_faces', {
        'name': name,
        'embedding': embeddingJson,
        'created_at': now,
        'last_seen': now,
        'times_seen': 1,
      });
    }
  }
  
  Future<Map<String, List<double>>> getAllFaces() async {
    final db = await database;
    List<Map<String, dynamic>> results = await db.query('known_faces');
    
    Map<String, List<double>> faces = {};
    for (var row in results) {
      String name = row['name'] as String;
      List<double> embedding = List<double>.from(jsonDecode(row['embedding'] as String));
      faces[name] = embedding;
    }
    return faces;
  }
  
  Future<int> saveUnknownFace(String imagePath, List<double> embedding, Uint8List? thumbnail) async {
    final db = await database;
    String embeddingJson = jsonEncode(embedding);
    String now = DateTime.now().toIso8601String();
    
    return await db.insert('unknown_faces', {
      'image_path': imagePath,
      'embedding': embeddingJson,
      'thumbnail': thumbnail,
      'detected_at': now,
      'status': 'pending',
    });
  }
  
  Future<List<Map<String, dynamic>>> getPendingFaces({int limit = 50}) async {
    final db = await database;
    return await db.query(
      'unknown_faces',
      where: 'status = ?',
      whereArgs: ['pending'],
      orderBy: 'detected_at DESC',
      limit: limit,
    );
  }
  
  Future<bool> labelUnknownFace(int faceId, String name) async {
    final db = await database;
    
    List<Map<String, dynamic>> result = await db.query(
      'unknown_faces',
      where: 'id = ?',
      whereArgs: [faceId],
    );
    
    if (result.isEmpty) return false;
    
    List<double> embedding = List<double>.from(jsonDecode(result.first['embedding'] as String));
    await addFace(name, embedding);
    
    await db.update(
      'unknown_faces',
      {'status': 'labeled'},
      where: 'id = ?',
      whereArgs: [faceId],
    );
    
    return true;
  }
  
  Future<int> deleteUnknownFace(int faceId) async {
    final db = await database;
    return await db.delete(
      'unknown_faces',
      where: 'id = ?',
      whereArgs: [faceId],
    );
  }
  
  Future<bool> isImageProcessed(String fileHash) async {
    final db = await database;
    List<Map<String, dynamic>> result = await db.query(
      'processed_images',
      where: 'file_hash = ?',
      whereArgs: [fileHash],
    );
    return result.isNotEmpty;
  }
  
  Future<void> markImageProcessed(String fileHash, String filePath, int facesCount) async {
    final db = await database;
    String now = DateTime.now().toIso8601String();
    
    await db.insert(
      'processed_images',
      {
        'file_hash': fileHash,
        'file_path': filePath,
        'processed_at': now,
        'faces_count': facesCount,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }
  
  Future<int> saveSortedPhoto(String originalPath, String sortedPath, String personName, double confidence) async {
    final db = await database;
    String now = DateTime.now().toIso8601String();
    
    return await db.insert('sorted_photos', {
      'original_path': originalPath,
      'sorted_path': sortedPath,
      'person_name': personName,
      'confidence': confidence,
      'sorted_at': now,
    });
  }
  
  Future<int> addFalsePositive(String imagePath, List<int> facePosition, String faceHash, Uint8List? thumbnail) async {
    final db = await database;
    String now = DateTime.now().toIso8601String();
    String positionJson = jsonEncode(facePosition);
    
    return await db.insert('false_positives', {
      'image_path': imagePath,
      'face_position': positionJson,
      'face_hash': faceHash,
      'thumbnail': thumbnail,
      'created_at': now,
    });
  }
  
  Future<List<Map<String, dynamic>>> getFalsePositives() async {
    final db = await database;
    List<Map<String, dynamic>> results = await db.query('false_positives');
    
    for (var row in results) {
      String positionJson = row['face_position'] as String;
      row['face_position_parsed'] = List<int>.from(jsonDecode(positionJson));
    }
    
    return results;
  }
  
  Future<int> deleteFalsePositive(int fpId) async {
    final db = await database;
    return await db.delete(
      'false_positives',
      where: 'id = ?',
      whereArgs: [fpId],
    );
  }
  
  Future<bool> isFalsePositive(String faceHash, {double threshold = 0.95}) async {
    if (faceHash.isEmpty) return false;
    
    final db = await database;
    List<Map<String, dynamic>> results = await db.query('false_positives');
    
    for (var row in results) {
      String? storedHash = row['face_hash'] as String?;
      if (storedHash != null && storedHash.isNotEmpty && storedHash == faceHash) {
        return true;
      }
    }
    return false;
  }
  
  Future<int> clearFalsePositives() async {
    final db = await database;
    return await db.delete('false_positives');
  }
  
  Future<void> close() async {
    if (_database != null) {
      await _database!.close();
      _database = null;
    }
  }
}
