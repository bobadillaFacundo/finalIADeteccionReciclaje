import 'dart:io';
import 'package:tflite_flutter/tflite_flutter.dart';
import 'package:image/image.dart' as img;
import '../models/waste_item.dart';

class ClassificationService {
  static const _inputSize = 128;
  static const _normFactor = 127.5;
  static const List<String> _labels = [
    'cardboard', 'glass', 'metal',
    'paper', 'plastic', 'trash',
  ];

  Interpreter? _interpreter;
  bool _isInitialized = false;

  Future<void> initialize() async {
    if (_isInitialized) return;
    try {
      _interpreter = await Interpreter.fromAsset('assets/models/waste_classifier.tflite');
      print('✅ Modelo TFLite cargado');
    } catch (e) {
      print('⚠️ Error al cargar TFLite: $e');
    }
    _isInitialized = true;
  }

  Future<WasteItem> classifyImage(File file) async {
    await initialize();
    if (_interpreter == null) return _simulateClassification();

    // 1) Decodificar y redimensionar a 128×128
    final bytes = await file.readAsBytes();
    final src = img.decodeImage(bytes);
    if (src == null) {
      throw Exception('Imagen no decodificable');
    }
    final image = img.copyResize(src, width: _inputSize, height: _inputSize);

    // 2) Crear tensor de entrada [1,128,128,3] con rango [0,255]
    final input = List.generate(_inputSize, (y) =>
      List.generate(_inputSize, (x) {
        final p = image.getPixel(x, y);
        return <double>[
          p.r.toDouble(),
          p.g.toDouble(),
          p.b.toDouble(),
        ];
      })
    );
    final inputTensor = [input];

    // 3) Preparar salida [1, numLabels]
    final output = List.generate(1, (_) => List.filled(_labels.length, 0.0));

    // 4) Inferencia
    _interpreter!.run(inputTensor, output);

    // 5) Post‑procesado
    final preds = output[0];
    final maxIdx = preds.indexWhere((v) => v == preds.reduce((a, b) => a > b ? a : b));
    return WasteItem.fromCategory(
      WasteCategory.values[maxIdx],
      preds[maxIdx],
    );
  }

  WasteItem _simulateClassification() {
    final idx  = DateTime.now().millisecondsSinceEpoch % _labels.length;
    final conf = 0.7 + (DateTime.now().millisecondsSinceEpoch % 30) / 100.0;
    return WasteItem.fromCategory(WasteCategory.values[idx], conf);
  }

  void dispose() {
    _interpreter?.close();
    _interpreter = null;
    _isInitialized = false;
  }
}
