import 'package:flutter/material.dart';

class ProgressDialog extends StatelessWidget {
  final int current;
  final int total;
  final String currentFile;
  
  const ProgressDialog({
    super.key,
    required this.current,
    required this.total,
    required this.currentFile,
  });
  
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF1a1a2e),
      title: const Text(
        "Пакетная обработка",
        style: TextStyle(color: Colors.white),
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          LinearProgressIndicator(
            value: current / total,
            backgroundColor: const Color(0xFF34495e),
            color: Colors.green,
          ),
          const SizedBox(height: 20),
          Text(
            "$current из $total",
            style: const TextStyle(color: Colors.white),
          ),
          const SizedBox(height: 10),
          Text(
            currentFile,
            style: const TextStyle(color: Colors.grey, fontSize: 12),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
