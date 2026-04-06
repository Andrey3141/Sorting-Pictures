package com.example.face_organizer

import android.os.Bundle
import androidx.annotation.NonNull
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import kotlinx.coroutines.*
import java.util.concurrent.Executors

class MainActivity : FlutterActivity() {
    private val CHANNEL = "face_recognizer"
    private lateinit var faceRecognizer: FaceRecognizerNative
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        faceRecognizer = FaceRecognizerNative(this)
    }
    
    override fun configureFlutterEngine(@NonNull flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "detectFaces" -> {
                    val path = call.argument<String>("path")
                    if (path != null) {
                        scope.launch {
                            try {
                                val faces = faceRecognizer.detectFaces(path)
                                val json = faces.map { face ->
                                    mapOf(
                                        "id" to face.id,
                                        "x" to face.x,
                                        "y" to face.y,
                                        "width" to face.width,
                                        "height" to face.height,
                                        "leftEyeOpenProbability" to (face.leftEyeOpenProbability ?: 0f),
                                        "rightEyeOpenProbability" to (face.rightEyeOpenProbability ?: 0f),
                                        "smilingProbability" to (face.smilingProbability ?: 0f),
                                        "trackingId" to (face.trackingId ?: -1)
                                    )
                                }
                                withContext(Dispatchers.Main) {
                                    result.success(json)
                                }
                            } catch (e: Exception) {
                                withContext(Dispatchers.Main) {
                                    result.error("DETECT_ERROR", e.message, null)
                                }
                            }
                        }
                    } else {
                        result.error("INVALID_ARGUMENT", "Path is null", null)
                    }
                }
                "getEmbedding" -> {
                    val path = call.argument<String>("path")
                    val x = call.argument<Int>("x") ?: 0
                    val y = call.argument<Int>("y") ?: 0
                    val w = call.argument<Int>("width") ?: 0
                    val h = call.argument<Int>("height") ?: 0
                    
                    if (path != null) {
                        scope.launch {
                            try {
                                val embedding = faceRecognizer.getFaceEmbedding(path, x, y, w, h)
                                withContext(Dispatchers.Main) {
                                    result.success(embedding.toList())
                                }
                            } catch (e: Exception) {
                                withContext(Dispatchers.Main) {
                                    result.error("EMBEDDING_ERROR", e.message, null)
                                }
                            }
                        }
                    } else {
                        result.error("INVALID_ARGUMENT", "Path is null", null)
                    }
                }
                "close" -> {
                    faceRecognizer.close()
                    result.success(null)
                }
                else -> result.notImplemented()
            }
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
        faceRecognizer.close()
    }
}
