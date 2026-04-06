import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../database/face_database.dart';
import '../services/face_recognizer.dart';
import '../widgets/animated_button.dart';

class TrainingDialog extends StatefulWidget {
  final FaceDatabase db;
  final FaceRecognizer recognizer;
  
  const TrainingDialog({
    super.key,
    required this.db,
    required this.recognizer,
  });

  @override
  State<TrainingDialog> createState() => _TrainingDialogState();
}

class _TrainingDialogState extends State<TrainingDialog> {
  List<Map<String, dynamic>> pendingFaces = [];
  int? selectedFaceId;
  final TextEditingController nameController = TextEditingController();
  final List<String> logMessages = [];
  final ScrollController logScrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    loadPendingFaces();
  }

  @override
  void dispose() {
    nameController.dispose();
    logScrollController.dispose();
    super.dispose();
  }

  void logMessage(String message) {
    String timestamp = DateTime.now().toString().substring(11, 19);
    setState(() {
      logMessages.insert(0, "[$timestamp] $message");
      if (logMessages.length > 50) logMessages.removeLast();
    });
  }

  Future<void> loadPendingFaces() async {
    List<Map<String, dynamic>> faces = await widget.db.getPendingFaces(limit: 50);
    setState(() {
      pendingFaces = List.from(faces); // Создаем копию
    });
    
    if (pendingFaces.isEmpty) {
      logMessage("✅ Нет неизвестных лиц!");
    } else {
      logMessage("📸 Загружено ${pendingFaces.length} неизвестных лиц");
    }
  }

  Future<void> labelFace() async {
    if (selectedFaceId == null) {
      _showWarningDialog("Ошибка", "Выберите лицо");
      return;
    }

    String name = nameController.text.trim();
    if (name.isEmpty) {
      _showWarningDialog("Ошибка", "Введите имя");
      return;
    }

    bool success = await widget.db.labelUnknownFace(selectedFaceId!, name);
    
    if (success) {
      await widget.recognizer.loadKnownFaces();
      
      // Создаем новый список вместо удаления из read-only
      final newList = List<Map<String, dynamic>>.from(pendingFaces);
      newList.removeWhere((face) => face['id'] == selectedFaceId);
      
      setState(() {
        pendingFaces = newList;
        selectedFaceId = null;
      });
      
      nameController.clear();
      logMessage("✅ Лицо ID $selectedFaceId добавлено как '$name'");
      _showInfoDialog("Успех", "✅ Лицо добавлено как '$name'");
      
      if (pendingFaces.isEmpty) {
        logMessage("🎉 Все лица размечены!");
        _showInfoDialog("Обучение завершено", "Все лица размечены!");
        Navigator.pop(context, true);
      }
    } else {
      logMessage("❌ Ошибка: не удалось добавить лицо");
      _showWarningDialog("Ошибка", "Не удалось добавить лицо");
    }
  }

  Future<void> markAsNotFace() async {
    if (selectedFaceId == null) {
      _showWarningDialog("Ошибка", "Выберите область");
      return;
    }

    bool? confirm = await _showConfirmDialog(
      "Маркировка НЕ ЛИЦО",
      "Вы уверены, что это НЕ лицо?"
    );

    if (confirm == true) {
      try {
        await widget.db.deleteUnknownFace(selectedFaceId!);
        
        final newList = List<Map<String, dynamic>>.from(pendingFaces);
        newList.removeWhere((face) => face['id'] == selectedFaceId);
        
        setState(() {
          pendingFaces = newList;
          selectedFaceId = null;
        });
        
        logMessage("❌ Область ID $selectedFaceId помечена как НЕ ЛИЦО");
        _showInfoDialog("Маркировка выполнена", "✅ Область помечена как НЕ ЛИЦО");
      } catch (e) {
        logMessage("❌ Ошибка: $e");
        _showWarningDialog("Ошибка", "Не удалось пометить: $e");
      }
    }
  }

  Future<void> skipFace() async {
    if (selectedFaceId == null) return;
    
    await widget.db.deleteUnknownFace(selectedFaceId!);
    
    final newList = List<Map<String, dynamic>>.from(pendingFaces);
    newList.removeWhere((face) => face['id'] == selectedFaceId);
    
    setState(() {
      pendingFaces = newList;
      selectedFaceId = null;
    });
    
    logMessage("⏭️ Пропущено лицо ID $selectedFaceId");
  }

  Uint8List? getThumbnailData(Map<String, dynamic> face) {
    final thumbnail = face['thumbnail'];
    if (thumbnail is Uint8List) return thumbnail;
    if (thumbnail is List<int>) return Uint8List.fromList(thumbnail);
    return null;
  }

  void _showWarningDialog(String title, String message) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("OK"),
          ),
        ],
      ),
    );
  }

  void _showInfoDialog(String title, String message) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text("OK"),
          ),
        ],
      ),
    );
  }

  Future<bool?> _showConfirmDialog(String title, String message) async {
    return await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text("Нет"),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text("Да"),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      child: Container(
        width: MediaQuery.of(context).size.width * 0.9,
        height: MediaQuery.of(context).size.height * 0.85,
        decoration: BoxDecoration(
          color: const Color(0xFF1a1a2e),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              child: const Text(
                "🎓 ОБУЧЕНИЕ",
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
            Expanded(
              flex: 2,
              child: pendingFaces.isEmpty
                  ? const Center(child: Text("✅ Нет неизвестных лиц!", style: TextStyle(color: Colors.green)))
                  : GridView.builder(
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 4,
                        childAspectRatio: 0.8,
                        crossAxisSpacing: 10,
                        mainAxisSpacing: 10,
                      ),
                      itemCount: pendingFaces.length,
                      itemBuilder: (context, index) {
                        final face = pendingFaces[index];
                        final faceId = face['id'] as int;
                        final thumbnail = getThumbnailData(face);
                        final isSelected = selectedFaceId == faceId;
                        
                        return GestureDetector(
                          onTap: () => setState(() => selectedFaceId = faceId),
                          child: Container(
                            decoration: BoxDecoration(
                              color: isSelected ? Colors.green : const Color(0xFF0f3460),
                              borderRadius: BorderRadius.circular(10),
                              border: isSelected ? Border.all(color: Colors.white, width: 2) : null,
                            ),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                thumbnail != null
                                    ? ClipRRect(
                                        borderRadius: BorderRadius.circular(8),
                                        child: Image.memory(thumbnail, width: 100, height: 100, fit: BoxFit.cover),
                                      )
                                    : Container(width: 100, height: 100, color: Colors.grey[800], child: const Icon(Icons.face, size: 50)),
                                const SizedBox(height: 8),
                                Text("ID: $faceId", style: const TextStyle(color: Colors.white)),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
            ),
            Container(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  Text(selectedFaceId != null ? "✅ Выбрано лицо ID: $selectedFaceId" : "Выберите лицо"),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      const Text("Имя:", style: TextStyle(color: Colors.white)),
                      const SizedBox(width: 10),
                      Expanded(
                        child: TextField(
                          controller: nameController,
                          style: const TextStyle(color: Colors.white),
                          decoration: const InputDecoration(
                            hintText: "Введите имя...",
                            border: OutlineInputBorder(),
                            enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: Colors.green)),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 15),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      AnimatedButton(text: "✅ Присвоить", color: Colors.green, onPressed: labelFace),
                      const SizedBox(width: 15),
                      AnimatedButton(text: "❌ НЕ ЛИЦО", color: Colors.purple, onPressed: markAsNotFace),
                      const SizedBox(width: 15),
                      AnimatedButton(text: "⏭️ Пропустить", color: Colors.red, onPressed: skipFace),
                    ],
                  ),
                ],
              ),
            ),
            Container(
              height: 100,
              margin: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFF1a1a2e),
                border: Border.all(color: Colors.green),
                borderRadius: BorderRadius.circular(10),
              ),
              child: ListView.builder(
                controller: logScrollController,
                reverse: true,
                itemCount: logMessages.length,
                itemBuilder: (_, i) => Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  child: Text(logMessages[i], style: const TextStyle(color: Colors.green, fontSize: 10)),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(20),
              child: AnimatedButton(text: "Закрыть", color: Colors.blue, onPressed: () => Navigator.pop(context, true)),
            ),
          ],
        ),
      ),
    );
  }
}
