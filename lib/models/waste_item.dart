import 'package:flutter/material.dart';

enum WasteCategory {
  cardboard,
  glass,
  metal,
  paper,
  plastic,
  trash,
}

class WasteItem {
  final WasteCategory category;
  final double confidence;
  final String name;
  final String description;
  final String recyclingTip;
  final String icon;

  const WasteItem({
    required this.category,
    required this.confidence,
    required this.name,
    required this.description,
    required this.recyclingTip,
    required this.icon,
  });

  static WasteItem fromCategory(WasteCategory category, double confidence) {
    switch (category) {
      case WasteCategory.cardboard:
        return WasteItem(
          category: category,
          confidence: confidence,
          name: 'Cartón',
          description: 'Material de embalaje reciclable',
          recyclingTip: 'Aplasta las cajas para ahorrar espacio. Asegúrate de que esté limpio y seco antes de reciclar. Separa el cartón del papel y otros materiales.',
          icon: '📦',
        );
      case WasteCategory.glass:
        return WasteItem(
          category: category,
          confidence: confidence,
          name: 'Vidrio',
          description: 'Material transparente y reciclable',
          recyclingTip: 'Limpia el vidrio antes de reciclar. Separa por colores si es posible. El vidrio se puede reciclar infinitamente sin perder calidad.',
          icon: '🍷',
        );
      case WasteCategory.metal:
        return WasteItem(
          category: category,
          confidence: confidence,
          name: 'Metal',
          description: 'Material metálico reciclable',
          recyclingTip: 'Limpia las latas y envases metálicos. El aluminio y acero son altamente reciclables. Aplasta las latas para ahorrar espacio.',
          icon: '🔩',
        );
      case WasteCategory.paper:
        return WasteItem(
          category: category,
          confidence: confidence,
          name: 'Papel',
          description: 'Material fibroso reciclable',
          recyclingTip: 'Separa el papel del cartón. Evita reciclar papel con grasa o tinta de impresora. El papel se puede reciclar hasta 7 veces.',
          icon: '📄',
        );
      case WasteCategory.plastic:
        return WasteItem(
          category: category,
          confidence: confidence,
          name: 'Plástico',
          description: 'Material sintético reciclable',
          recyclingTip: 'Revisa el código de reciclaje (1-7). Limpia los envases antes de reciclar. Reduce el uso de plásticos de un solo uso.',
          icon: '🥤',
        );
      case WasteCategory.trash:
        return WasteItem(
          category: category,
          confidence: confidence,
          name: 'Basura',
          description: 'Material no reciclable',
          recyclingTip: 'Este material no es reciclable. Considera reducir el consumo o buscar alternativas más sostenibles. Deposítalo en el contenedor de basura general.',
          icon: '🗑️',
        );
    }
  }

  Color get color {
    switch (category) {
      case WasteCategory.cardboard:
        return Colors.brown;
      case WasteCategory.glass:
        return Colors.blue;
      case WasteCategory.metal:
        return Colors.grey;
      case WasteCategory.paper:
        return Colors.lightBlue;
      case WasteCategory.plastic:
        return Colors.orange;
      case WasteCategory.trash:
        return Colors.red;
    }
  }

  String get confidencePercentage => '${(confidence * 100).toStringAsFixed(1)}%';
} 