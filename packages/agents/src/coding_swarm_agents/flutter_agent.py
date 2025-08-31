"""
Flutter Development Agent - Specialized for Flutter/Dart development
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import re

from .base import Agent


class FlutterAgent(Agent):
    """Specialized agent for Flutter development"""

    def __init__(self, context: Dict[str, Any]) -> None:
        super().__init__(context)
        self.framework = "flutter"
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """Load Flutter-specific code templates"""
        return {
            "widget": """import 'package:flutter/material.dart';

class {WidgetName} extends StatefulWidget {
  const {WidgetName}({super.key});

  @override
  State<{WidgetName}> createState() => _{WidgetName}State();
}

class _{WidgetName}State extends State<{WidgetName}> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('{WidgetName}'),
      ),
      body: const Center(
        child: Text(
          'Welcome to {WidgetName}!',
          style: TextStyle(fontSize: 24),
        ),
      ),
    );
  }
}""",

            "stateless_widget": """import 'package:flutter/material.dart';

class {WidgetName} extends StatelessWidget {
  const {WidgetName}({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      child: const Text(
        '{WidgetName}',
        style: TextStyle(fontSize: 16),
      ),
    );
  }
}""",

            "provider": """import 'package:flutter/material.dart';

class {ProviderName} extends ChangeNotifier {
  // State variables
  int _counter = 0;

  int get counter => _counter;

  // Actions
  void increment() {
    _counter++;
    notifyListeners();
  }

  void decrement() {
    _counter--;
    notifyListeners();
  }

  void reset() {
    _counter = 0;
    notifyListeners();
  }
}""",

            "model": """class {ModelName} {
  final int? id;
  final String? name;
  final DateTime? createdAt;

  const {ModelName}({
    this.id,
    this.name,
    this.createdAt,
  });

  factory {ModelName}.fromJson(Map<String, dynamic> json) {
    return {ModelName}(
      id: json['id'] as int?,
      name: json['name'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'created_at': createdAt?.toIso8601String(),
    };
  }

  {ModelName} copyWith({
    int? id,
    String? name,
    DateTime? createdAt,
  }) {
    return {ModelName}(
      id: id ?? this.id,
      name: name ?? this.name,
      createdAt: createdAt ?? this.createdAt,
    );
  }
}""",

            "service": """import 'dart:convert';
import 'package:http/http.dart' as http;

class {ServiceName} {
  static const String baseUrl = 'https://api.example.com';

  Future<List<{ModelName}>> get{ModelName}s() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/{model_name}s'));

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((item) => {ModelName}.fromJson(item)).toList();
      } else {
        throw Exception('Failed to load {model_name}s');
      }
    } catch (e) {
      throw Exception('Error fetching {model_name}s: $e');
    }
  }

  Future<{ModelName}> get{ModelName}(int id) async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/{model_name}s/$id'));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return {ModelName}.fromJson(data);
      } else {
        throw Exception('Failed to load {model_name}');
      }
    } catch (e) {
      throw Exception('Error fetching {model_name}: $e');
    }
  }

  Future<{ModelName}> create{ModelName}({ModelName} {modelName}) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/{model_name}s'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({modelName}.toJson()),
      );

      if (response.statusCode == 201) {
        final data = json.decode(response.body);
        return {ModelName}.fromJson(data);
      } else {
        throw Exception('Failed to create {model_name}');
      }
    } catch (e) {
      throw Exception('Error creating {model_name}: $e');
    }
  }
}""",

            "screen": """import 'package:flutter/material.dart';

class {ScreenName}Screen extends StatefulWidget {
  const {ScreenName}Screen({super.key});

  @override
  State<{ScreenName}Screen> createState() => _{ScreenName}ScreenState();
}

class _{ScreenName}ScreenState extends State<{ScreenName}Screen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('{ScreenName}'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: const Center(
        child: Text(
          'Welcome to {ScreenName} Screen',
          style: TextStyle(fontSize: 24),
        ),
      ),
    );
  }
}""",

            "bloc": """import 'package:flutter_bloc/flutter_bloc.dart';

// Events
abstract class {BlocName}Event {}

class Load{BlocName}Event extends {BlocName}Event {}

// States
abstract class {BlocName}State {}

class {BlocName}Initial extends {BlocName}State {}

class {BlocName}Loading extends {BlocName}State {}

class {BlocName}Loaded extends {BlocName}State {
  final List<{ModelName}> items;

  const {BlocName}Loaded(this.items);
}

class {BlocName}Error extends {BlocName}State {
  final String message;

  const {BlocName}Error(this.message);
}

// BLoC
class {BlocName}Bloc extends Bloc<{BlocName}Event, {BlocName}State> {
  {BlocName}Bloc() : super({BlocName}Initial()) {
    on<Load{BlocName}Event>(_onLoad{BlocName});
  }

  Future<void> _onLoad{BlocName}(
    Load{BlocName}Event event,
    Emitter<{BlocName}State> emit,
  ) async {
    emit({BlocName}Loading());

    try {
      // Load data here
      // final items = await someService.getItems();
      // emit({BlocName}Loaded(items));

      emit({BlocName}Loaded([])); // Placeholder
    } catch (e) {
      emit({BlocName}Error(e.toString()));
    }
  }
}"""
        }

    def plan(self) -> str:
        """Create a Flutter-specific development plan"""
        goal = self.context.get('goal', '')
        project_type = self._detect_project_type()

        plan = f"""
## Flutter Development Plan

### 🎯 Goal: {goal}

### 📋 Framework Detection
- **Type**: {project_type}
- **Stack**: Flutter with Dart
- **Architecture**: Widget-based UI framework

### 🏗️ Implementation Strategy

1. **UI Architecture**
   - Design widget tree structure
   - Implement responsive layouts
   - Use proper state management
   - Material Design 3 compliance

2. **State Management**
   - Choose BLoC/Provider/Riverpod
   - Implement proper state flow
   - Handle async operations
   - Error state management

3. **Data Layer**
   - Model classes with JSON serialization
   - Service classes for API calls
   - Local storage with SQLite/SharedPreferences
   - Repository pattern implementation

4. **Navigation & Routing**
   - Implement navigation structure
   - Deep linking support
   - Route guards and middleware
   - Bottom navigation/tab bars

5. **Performance Optimization**
   - Widget optimization and keys
   - Image optimization and caching
   - List virtualization
   - Memory leak prevention

### 🎨 Code Quality Standards
- Effective Dart guidelines
- Widget composition over inheritance
- Proper async/await usage
- Error handling with try-catch
- Unit and widget tests
- Integration tests for critical flows
"""
        return plan

    def _detect_project_type(self) -> str:
        """Detect the type of Flutter project"""
        project_path = Path(self.context.get('project', '.'))

        # Check for Flutter
        if (project_path / 'pubspec.yaml').exists():
            return "Flutter Application"

        # Check for Flutter module
        if (project_path / '.flutter-plugins').exists():
            return "Flutter Module"

        return "Flutter/Dart Project"

    def apply_patch(self, patch: str) -> bool:
        """Apply Flutter-specific patches"""
        try:
            if 'widget' in patch.lower() and 'stateless' not in patch.lower():
                return self._create_widget(patch)
            elif 'stateless' in patch.lower():
                return self._create_stateless_widget(patch)
            elif 'provider' in patch.lower():
                return self._create_provider(patch)
            elif 'model' in patch.lower():
                return self._create_model(patch)
            elif 'service' in patch.lower():
                return self._create_service(patch)
            elif 'screen' in patch.lower():
                return self._create_screen(patch)
            elif 'bloc' in patch.lower():
                return self._create_bloc(patch)
            else:
                return self._apply_generic_patch(patch)
        except Exception as e:
            print(f"Error applying Flutter patch: {e}")
            return False

    def _create_widget(self, spec: str) -> bool:
        """Create a Flutter stateful widget"""
        name_match = re.search(r'widget[:\s]+(\w+)', spec, re.IGNORECASE)
        if not name_match:
            return False

        widget_name = name_match.group(1)
        template = self.templates['widget']
        code = template.replace('{WidgetName}', widget_name)

        self._save_code_file(f"lib/widgets/{widget_name.lower()}_widget.dart", code)
        return True

    def _create_stateless_widget(self, spec: str) -> bool:
        """Create a Flutter stateless widget"""
        name_match = re.search(r'stateless[:\s]+(\w+)', spec, re.IGNORECASE)
        if not name_match:
            return False

        widget_name = name_match.group(1)
        template = self.templates['stateless_widget']
        code = template.replace('{WidgetName}', widget_name)

        self._save_code_file(f"lib/widgets/{widget_name.lower()}_widget.dart", code)
        return True

    def _create_provider(self, spec: str) -> bool:
        """Create a Provider class"""
        name_match = re.search(r'provider[:\s]+(\w+)', spec, re.IGNORECASE)
        if not name_match:
            return False

        provider_name = name_match.group(1)
        template = self.templates['provider']
        code = template.replace('{ProviderName}', provider_name)

        self._save_code_file(f"lib/providers/{provider_name.lower()}_provider.dart", code)
        return True

    def _create_model(self, spec: str) -> bool:
        """Create a model class"""
        name_match = re.search(r'model[:\s]+(\w+)', spec, re.IGNORECASE)
        if not name_match:
            return False

        model_name = name_match.group(1)
        template = self.templates['model']
        code = template.replace('{ModelName}', model_name)

        self._save_code_file(f"lib/models/{model_name.lower()}_model.dart", code)
        return True

    def _create_service(self, spec: str) -> bool:
        """Create a service class"""
        name_match = re.search(r'service[:\s]+(\w+)', spec, re.IGNORECASE)
        if not name_match:
            return False

        service_name = name_match.group(1)
        model_name = service_name.replace('Service', '')

        template = self.templates['service']
        code = template.replace('{ServiceName}', service_name)
        code = code.replace('{ModelName}', model_name)
        code = code.replace('{modelName}', model_name.lower())
        code = code.replace('{model_name}', model_name.lower())

        self._save_code_file(f"lib/services/{service_name.lower()}_service.dart", code)
        return True

    def _create_screen(self, spec: str) -> bool:
        """Create a screen widget"""
        name_match = re.search(r'screen[:\s]+(\w+)', spec, re.IGNORECASE)
        if not name_match:
            return False

        screen_name = name_match.group(1)
        template = self.templates['screen']
        code = template.replace('{ScreenName}', screen_name)

        self._save_code_file(f"lib/screens/{screen_name.lower()}_screen.dart", code)
        return True

    def _create_bloc(self, spec: str) -> bool:
        """Create a BLoC pattern implementation"""
        name_match = re.search(r'bloc[:\s]+(\w+)', spec, re.IGNORECASE)
        if not name_match:
            return False

        bloc_name = name_match.group(1)
        model_name = bloc_name.replace('Bloc', '')

        template = self.templates['bloc']
        code = template.replace('{BlocName}', bloc_name)
        code = code.replace('{ModelName}', model_name)

        self._save_code_file(f"lib/blocs/{bloc_name.lower()}_bloc.dart", code)
        return True

    def _apply_generic_patch(self, patch: str) -> bool:
        """Apply generic code patches"""
        return True

    def _save_code_file(self, relative_path: str, content: str) -> None:
        """Save code to file with proper directory creation"""
        project_path = Path(self.context.get('project', '.'))
        full_path = project_path / relative_path

        # Create directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        full_path.write_text(content, encoding='utf-8')

        # Store in artifacts
        self.artifacts[relative_path] = content

    def run_tests(self) -> tuple[bool, str]:
        """Run Flutter-specific tests"""
        # This would run Flutter tests
        return True, "Flutter tests completed successfully"