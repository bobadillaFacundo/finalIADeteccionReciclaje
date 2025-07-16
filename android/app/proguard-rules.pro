# ====== TFLite GPU - Evitar que R8 elimine clases necesarias ======
-keep class org.tensorflow.lite.** { *; }
-dontwarn org.tensorflow.lite.**
