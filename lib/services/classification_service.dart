import 'dart:io';
import 'dart:typed_data';                       // para UnmodifiableUint8ListView
import 'package:tflite_flutter/tflite_flutter.dart';
import 'package:image/image.dart' as img;        // único import de `image`
import '../models/waste_item.dart';

class ClassificationService {
  static const List<String> _labels = [
    'cardboard', 'glass', 'metal',
    'paper', 'plastic', 'trash',
  ];

  Interpreter? _interpreter;
  bool _isInitialized = false;

  Future<void> initialize() async {
    if (_isInitialized) return;
    try {
      _interpreter = await Interpreter.fromAsset(
          'assets/models/waste_classifier.tflite'
      );
      _isInitialized = true;
      print('✅ Modelo TFLite cargado');
    } catch (e) {
      print('⚠️ Error al cargar TFLite: $e');
      _isInitialized = true; // para que no lo intente siempre
    }
  }

  Future<WasteItem> classifyImage(File file) async {
    await initialize();
    if (_interpreter == null) return _simulateClassification();

    try {
      // 1) Decodificar y redimensionar
      final raw = await file.readAsBytes();
      final src = img.decodeImage(raw);
      if (src == null) throw Exception('Imagen no decodificable');
      final image = img.copyResize(src, width: 224, height: 224);

      // 2) Construir el tensor [1,224,224,3]
      final input = List.generate(224, (y) => List.generate(224, (x) {
          final px = image.getPixel(x, y);
          return <double>[
            px.r.toDouble() / 255.0, // Normalizar R
            px.g.toDouble() / 255.0, // Normalizar G  
            px.b.toDouble() / 255.0, // Normalizar B  
          ];
        }));
      final inputTensor = [input];

      // 3) Preparar salida
      final output = List.filled(_labels.length, 0.0).reshape([1, _labels.length]);

      // 4) Ejecutar inferencia
      _interpreter!.run(inputTensor, output);

      // 5) Post‑procesado
      final preds = output[0];
      final maxI = preds.indexWhere((v) => v == preds.reduce((a, b) => a > b ? a : b));
      return WasteItem.fromCategory(
        WasteCategory.values[maxI],
        preds[maxI],
      );
    } catch (e) {
      print('⚠️ Error en inferencia: $e');
      return _simulateClassification();
    }
  }

  WasteItem _simulateClassification() {
    final idx = DateTime.now().millisecondsSinceEpoch % _labels.length;
    final conf = 0.7 + (DateTime.now().millisecondsSinceEpoch % 30) / 100.0;
    return WasteItem.fromCategory(WasteCategory.values[idx], conf);
  }

  void dispose() {
    _interpreter?.close();
    _interpreter = null;
    _isInitialized = false;
  }
}
