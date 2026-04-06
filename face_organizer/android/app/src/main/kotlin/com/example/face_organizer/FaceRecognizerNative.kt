package com.example.face_organizer

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import androidx.camera.core.ImageProxy
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.face.FaceDetection
import com.google.mlkit.vision.face.FaceDetectorOptions
import java.io.File
import java.nio.ByteBuffer

class FaceRecognizerNative(private val context: Context) {
    
    private val faceDetector by lazy {
        val options = FaceDetectorOptions.Builder()
            .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_ACCURATE)
            .setClassificationMode(FaceDetectorOptions.CLASSIFICATION_MODE_ALL)
            .setContourMode(FaceDetectorOptions.CONTOUR_MODE_ALL)
            .setMinFaceSize(0.15f)
            .build()
        FaceDetection.getClient(options)
    }
    
    data class FaceData(
        val id: Int,
        val x: Int,
        val y: Int,
        val width: Int,
        val height: Int,
        val leftEyeOpenProbability: Float? = null,
        val rightEyeOpenProbability: Float? = null,
        val smilingProbability: Float? = null,
        val trackingId: Int? = null
    )
    
    suspend fun detectFaces(imagePath: String): List<FaceData> {
        return try {
            val inputImage = InputImage.fromFilePath(context, imagePath)
            val faces = faceDetector.process(inputImage)
                .onFailure { throw it }
                .await()
            
            faces.mapIndexed { index, face ->
                val bounds = face.boundingBox
                FaceData(
                    id = index,
                    x = bounds.left,
                    y = bounds.top,
                    width = bounds.width(),
                    height = bounds.height(),
                    leftEyeOpenProbability = face.leftEyeOpenProbability,
                    rightEyeOpenProbability = face.rightEyeOpenProbability,
                    smilingProbability = face.smilingProbability,
                    trackingId = face.trackingId
                )
            }
        } catch (e: Exception) {
            e.printStackTrace()
            emptyList()
        }
    }
    
    suspend fun getFaceEmbedding(imagePath: String, x: Int, y: Int, width: Int, height: Int): FloatArray {
        // Здесь будет вызов твоей FaceNet модели через TFLite
        // Пока возвращаем заглушку
        return FloatArray(128) { 0f }
    }
    
    fun close() {
        faceDetector.close()
    }
}
