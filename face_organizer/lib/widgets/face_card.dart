import 'package:flutter/material.dart';

class FaceCard extends StatelessWidget {
  final Map<String, dynamic> faceData;
  final VoidCallback onAddName;
  final VoidCallback onMarkAsNotFace;
  
  const FaceCard({
    super.key,
    required this.faceData,
    required this.onAddName,
    required this.onMarkAsNotFace,
  });
  
  @override
  Widget build(BuildContext context) {
    final isKnown = faceData['is_known'] ?? false;
    final name = faceData['name'] ?? 'Неизвестный';
    final confidence = faceData['confidence'] ?? 0.0;
    final thumbnail = faceData['thumbnail'];
    
    return Container(
      width: 160,
      margin: const EdgeInsets.symmetric(horizontal: 5),
      decoration: BoxDecoration(
        color: const Color(0xFF2c3e50),
        borderRadius: BorderRadius.circular(15),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const SizedBox(height: 15),
          Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              color: Colors.grey[800],
            ),
            child: thumbnail != null
                ? ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: Image.memory(
                      thumbnail,
                      width: 120,
                      height: 120,
                      fit: BoxFit.cover,
                    ),
                  )
                : const Icon(Icons.face, size: 60, color: Colors.grey),
          ),
          const SizedBox(height: 10),
          Text(
            name,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 14,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          LinearProgressIndicator(
            value: confidence,
            backgroundColor: const Color(0xFF34495e),
            color: Colors.green,
            borderRadius: BorderRadius.circular(5),
            minHeight: 20,
          ),
          const SizedBox(height: 5),
          Text(
            "${(confidence * 100).toStringAsFixed(0)}%",
            style: const TextStyle(color: Colors.white, fontSize: 12),
          ),
          const SizedBox(height: 10),
          if (!isKnown)
            ElevatedButton(
              onPressed: onAddName,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.orange,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
              ),
              child: const Text("🏷️ ДОБАВИТЬ ИМЯ", style: TextStyle(fontSize: 11)),
            ),
          const SizedBox(height: 5),
          ElevatedButton(
            onPressed: onMarkAsNotFace,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF9C27B0),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
            ),
            child: const Text("❌ НЕ ЛИЦО", style: TextStyle(fontSize: 11)),
          ),
          const SizedBox(height: 15),
        ],
      ),
    );
  }
}
