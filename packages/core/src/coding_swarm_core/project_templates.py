"""
Project Templates - Framework-specific project templates and workflows
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass
import json

from .projects import Project


@dataclass
class ProjectTemplate:
    """Template for creating new projects"""
    name: str
    description: str
    framework: str
    category: str
    features: List[str]
    structure: Dict[str, Any]
    dependencies: Dict[str, str]
    scripts: Dict[str, str]
    config_files: Dict[str, str]


class ProjectTemplateManager:
    """Manages project templates for different frameworks"""

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, ProjectTemplate]:
        """Load all available project templates"""
        return {
            # React Templates
            "react-basic": ProjectTemplate(
                name="React Basic",
                description="Simple React application with modern tooling",
                framework="react",
                category="frontend",
                features=["React", "TypeScript", "ESLint", "Prettier", "Vite"],
                structure={
                    "src": {
                        "components": {},
                        "hooks": {},
                        "utils": {},
                        "types": {},
                        "App.tsx": "// Main App component",
                        "main.tsx": "// App entry point",
                        "index.css": "/* Global styles */"
                    },
                    "public": {
                        "index.html": "<!-- Main HTML template -->"
                    }
                },
                dependencies={
                    "react": "^18.2.0",
                    "react-dom": "^18.2.0",
                    "@types/react": "^18.2.0",
                    "@types/react-dom": "^18.2.0",
                    "typescript": "^5.0.0",
                    "vite": "^4.4.0"
                },
                scripts={
                    "dev": "vite",
                    "build": "tsc && vite build",
                    "preview": "vite preview",
                    "lint": "eslint src --ext ts,tsx --report-unused-disable-directives --max-warnings 0"
                },
                config_files={
                    "vite.config.ts": """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})""",
                    "tsconfig.json": """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}"""
                }
            ),

            "react-nextjs": ProjectTemplate(
                name="Next.js Full-Stack",
                description="Full-stack Next.js application with API routes",
                framework="react",
                category="fullstack",
                features=["Next.js", "TypeScript", "Tailwind CSS", "API Routes", "SSR"],
                structure={
                    "src": {
                        "app": {
                            "layout.tsx": "// Root layout",
                            "page.tsx": "// Home page",
                            "globals.css": "/* Global styles */"
                        },
                        "components": {},
                        "lib": {},
                        "types": {}
                    },
                    "public": {}
                },
                dependencies={
                    "next": "^14.0.0",
                    "react": "^18.2.0",
                    "react-dom": "^18.2.0",
                    "@types/node": "^20.0.0",
                    "@types/react": "^18.2.0",
                    "@types/react-dom": "^18.2.0",
                    "typescript": "^5.0.0",
                    "tailwindcss": "^3.3.0",
                    "autoprefixer": "^10.4.0",
                    "postcss": "^8.4.0"
                },
                scripts={
                    "dev": "next dev",
                    "build": "next build",
                    "start": "next start",
                    "lint": "next lint"
                },
                config_files={
                    "tailwind.config.js": """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}"""
                }
            ),

            # Laravel Templates
            "laravel-api": ProjectTemplate(
                name="Laravel API",
                description="RESTful API built with Laravel",
                framework="laravel",
                category="backend",
                features=["Laravel", "API", "JWT Auth", "Rate Limiting", "CORS"],
                structure={
                    "app": {
                        "Http": {
                            "Controllers": {
                                "API": {}
                            },
                            "Middleware": {},
                            "Requests": {}
                        },
                        "Models": {},
                        "Services": {},
                        "Repositories": {}
                    },
                    "database": {
                        "migrations": {},
                        "seeders": {},
                        "factories": {}
                    },
                    "routes": {
                        "api.php": "// API routes"
                    },
                    "config": {},
                    "tests": {
                        "Feature": {},
                        "Unit": {}
                    }
                },
                dependencies={
                    "laravel/framework": "^11.0",
                    "laravel/sanctum": "^4.0",
                    "laravel/tinker": "^2.9",
                    "spatie/laravel-permission": "^6.0"
                },
                scripts={
                    "serve": "php artisan serve",
                    "test": "php artisan test",
                    "migrate": "php artisan migrate",
                    "seed": "php artisan db:seed"
                },
                config_files={
                    "composer.json": """{
  "name": "laravel/laravel",
  "type": "project",
  "description": "Laravel API Application",
  "require": {
    "php": "^8.2",
    "laravel/framework": "^11.0"
  }
}""",
                    ".env.example": """APP_NAME=Laravel
APP_ENV=local
APP_KEY=
APP_DEBUG=true
APP_URL=http://localhost

DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=laravel
DB_USERNAME=root
DB_PASSWORD=

CACHE_DRIVER=file
QUEUE_CONNECTION=sync"""
                }
            ),

            "laravel-fullstack": ProjectTemplate(
                name="Laravel Full-Stack",
                description="Full-stack Laravel application with Blade templates",
                framework="laravel",
                category="fullstack",
                features=["Laravel", "Blade", "Livewire", "Alpine.js", "Tailwind CSS"],
                structure={
                    "app": {
                        "Http": {
                            "Controllers": {},
                            "Livewire": {},
                            "Middleware": {}
                        },
                        "Models": {},
                        "View": {
                            "Components": {}
                        }
                    },
                    "resources": {
                        "views": {
                            "layouts": {},
                            "components": {}
                        },
                        "css": {},
                        "js": {}
                    },
                    "routes": {
                        "web.php": "// Web routes",
                        "api.php": "// API routes"
                    }
                },
                dependencies={
                    "laravel/framework": "^11.0",
                    "livewire/livewire": "^3.0",
                    "spatie/laravel-permission": "^6.0",
                    "laravel/breeze": "^2.0"
                },
                scripts={
                    "serve": "php artisan serve",
                    "build": "npm run build",
                    "dev": "npm run dev"
                },
                config_files={
                    "package.json": """{
  "private": true,
  "scripts": {
    "build": "vite build",
    "dev": "vite build --watch"
  },
  "devDependencies": {
    "axios": "^1.6.0",
    "laravel-vite-plugin": "^1.0.0",
    "vite": "^5.0.0"
  }
}""",
                    "vite.config.js": """import { defineConfig } from 'vite';
import laravel from 'laravel-vite-plugin';

export default defineConfig({
    plugins: [
        laravel({
            input: 'resources/css/app.css',
            refresh: true,
        }),
    ],
});"""
                }
            ),

            # Flutter Templates
            "flutter-basic": ProjectTemplate(
                name="Flutter Basic",
                description="Basic Flutter application with Material Design",
                framework="flutter",
                category="mobile",
                features=["Flutter", "Material Design", "Provider", "HTTP", "Shared Preferences"],
                structure={
                    "lib": {
                        "screens": {},
                        "widgets": {},
                        "models": {},
                        "services": {},
                        "providers": {},
                        "utils": {},
                        "main.dart": "// App entry point"
                    },
                    "test": {},
                    "android": {},
                    "ios": {}
                },
                dependencies={
                    "provider": "^6.0.5",
                    "http": "^1.1.0",
                    "shared_preferences": "^2.2.0",
                    "flutter_launcher_icons": "^0.13.1"
                },
                scripts={
                    "run": "flutter run",
                    "build-apk": "flutter build apk",
                    "build-ios": "flutter build ios",
                    "test": "flutter test"
                },
                config_files={
                    "pubspec.yaml": """name: flutter_app
description: A new Flutter project.
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  provider: ^6.0.5
  http: ^1.1.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0

flutter:
  uses-material-design: true""",
                    "analysis_options.yaml": """include: package:flutter_lints/analysis_options.yaml

linter:
  rules:
    - prefer_const_constructors
    - prefer_const_declarations
    - avoid_print
    - unnecessary_brace_in_string_interps""",
                    "README.md": """# Flutter App

A new Flutter project.

## Getting Started

This project is a starting point for a Flutter application.

A few resources to get you started if this is your first Flutter project:

- [Lab: Write your first Flutter app](https://docs.flutter.dev/get-started/codelab)
- [Cookbook: Useful Flutter samples](https://docs.flutter.dev/cookbook)

For help getting started with Flutter development, view the
[online documentation](https://docs.flutter.dev/), which offers tutorials,
samples, guidance on mobile development, and a full API reference."""
                }
            ),

            "flutter-firebase": ProjectTemplate(
                name="Flutter with Firebase",
                description="Flutter app with Firebase integration",
                framework="flutter",
                category="mobile",
                features=["Flutter", "Firebase", "Authentication", "Firestore", "Cloud Functions"],
                structure={
                    "lib": {
                        "screens": {
                            "auth": {},
                            "home": {},
                            "profile": {}
                        },
                        "widgets": {},
                        "models": {},
                        "services": {
                            "auth_service.dart": "// Firebase Auth service",
                            "firestore_service.dart": "// Firestore service"
                        },
                        "providers": {},
                        "utils": {},
                        "main.dart": "// App entry point"
                    },
                    "functions": {
                        "src": {},
                        "package.json": "// Firebase functions package.json"
                    },
                    "test": {},
                    "android": {},
                    "ios": {}
                },
                dependencies={
                    "firebase_core": "^2.24.2",
                    "firebase_auth": "^4.16.0",
                    "cloud_firestore": "^4.14.0",
                    "firebase_storage": "^11.6.0",
                    "provider": "^6.0.5",
                    "http": "^1.1.0"
                },
                scripts={
                    "run": "flutter run",
                    "build-apk": "flutter build apk",
                    "build-ios": "flutter build ios",
                    "test": "flutter test",
                    "deploy-functions": "firebase deploy --only functions"
                },
                config_files={
                    "pubspec.yaml": """name: flutter_firebase_app
description: Flutter app with Firebase
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  firebase_core: ^2.24.2
  firebase_auth: ^4.16.0
  cloud_firestore: ^4.14.0
  provider: ^6.0.5

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0""",
                    "firebase.json": """{
  "functions": {
    "source": "functions"
  },
  "hosting": {
    "public": "build/web",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}"""
                }
            )
        }

    def get_templates_by_framework(self, framework: str) -> List[ProjectTemplate]:
        """Get all templates for a specific framework"""
        return [template for template in self.templates.values() if template.framework == framework]

    def get_template(self, template_name: str) -> Optional[ProjectTemplate]:
        """Get a specific template by name"""
        return self.templates.get(template_name)

    def create_project_from_template(self, template_name: str, project_name: str, project_path: str) -> Project:
        """Create a new project from a template"""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        # Create project directory
        project_dir = Path(project_path) / project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create project structure
        self._create_structure(project_dir, template.structure)

        # Create configuration files
        self._create_config_files(project_dir, template.config_files)

        # Create project instance
        project = Project(
            name=project_name,
            path=str(project_dir),
            notes=f"Created from {template.name} template"
        )

        return project

    def _create_structure(self, base_path: Path, structure: Dict[str, Any], current_path: Path = None):
        """Recursively create project structure"""
        if current_path is None:
            current_path = base_path

        for name, content in structure.items():
            item_path = current_path / name

            if isinstance(content, dict):
                # It's a directory
                item_path.mkdir(exist_ok=True)
                self._create_structure(base_path, content, item_path)
            else:
                # It's a file with default content
                item_path.write_text(content)

    def _create_config_files(self, project_path: Path, config_files: Dict[str, str]):
        """Create configuration files"""
        for filename, content in config_files.items():
            file_path = project_path / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

    def list_available_templates(self) -> Dict[str, List[str]]:
        """List all available templates grouped by framework"""
        templates_by_framework = {}

        for template in self.templates.values():
            if template.framework not in templates_by_framework:
                templates_by_framework[template.framework] = []

            templates_by_framework[template.framework].append(
                f"{template.name}: {template.description}"
            )

        return templates_by_framework


# Global template manager instance
template_manager = ProjectTemplateManager()