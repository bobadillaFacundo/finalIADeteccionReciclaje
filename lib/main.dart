import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'widgets/home_screen.dart';

void main() {
  runApp(const WasteClassifierApp());
}

class WasteClassifierApp extends StatelessWidget {
  const WasteClassifierApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Waste Classifier',
      theme: ThemeData(
        primarySwatch: Colors.green,
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.green,
          brightness: Brightness.light,
        ),
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    _requestPermissions();
  }

  Future<void> _requestPermissions() async {
    await Permission.camera.request();
    await Permission.storage.request();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Clasificador de Residuos',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: Colors.green,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Colors.green, Colors.lightGreen],
          ),
        ),
        child: const Center(
          child: HomeContent(),
        ),
      ),
    );
  }
} 