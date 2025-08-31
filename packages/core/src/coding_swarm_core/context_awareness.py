"""
Smart Context Awareness - Intelligent project understanding and assistance
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
import ast
import os


@dataclass
class ProjectContext:
    """Comprehensive project context information"""
    framework: str = "unknown"
    language: str = "unknown"
    project_type: str = "unknown"  # web, mobile, api, desktop, etc.
    architecture: str = "unknown"
    dependencies: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    configuration_files: List[str] = field(default_factory=list)
    test_framework: Optional[str] = None
    build_system: Optional[str] = None
    deployment_target: Optional[str] = None
    development_stage: str = "development"  # development, staging, production
    team_size: int = 1
    complexity_score: float = 0.0
    last_modified: Optional[datetime] = None
    code_quality_score: float = 0.0


@dataclass
class ContextInsight:
    """Contextual insight for better assistance"""
    category: str  # 'optimization', 'security', 'performance', 'best_practice', etc.
    title: str
    description: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    actionable: bool = True
    suggested_actions: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)


class SmartContextAnalyzer:
    """Intelligent context analyzer for projects"""

    def __init__(self):
        self.framework_detectors = self._load_framework_detectors()
        self.insight_generators = self._load_insight_generators()

    def _load_framework_detectors(self) -> Dict[str, callable]:
        """Load framework detection functions"""
        return {
            'react': self._detect_react,
            'nextjs': self._detect_nextjs,
            'laravel': self._detect_laravel,
            'flutter': self._detect_flutter,
            'django': self._detect_django,
            'fastapi': self._detect_fastapi,
            'spring': self._detect_spring,
            'dotnet': self._detect_dotnet,
            'vue': self._detect_vue,
            'angular': self._detect_angular,
        }

    def _load_insight_generators(self) -> Dict[str, callable]:
        """Load insight generation functions"""
        return {
            'security': self._generate_security_insights,
            'performance': self._generate_performance_insights,
            'code_quality': self._generate_code_quality_insights,
            'best_practices': self._generate_best_practice_insights,
            'architecture': self._generate_architecture_insights,
        }

    def analyze_project(self, project_path: str) -> ProjectContext:
        """Analyze project and return comprehensive context"""
        path = Path(project_path)

        if not path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        context = ProjectContext()

        # Detect framework
        context.framework = self._detect_framework(path)

        # Detect language
        context.language = self._detect_language(path)

        # Detect project type
        context.project_type = self._detect_project_type(path, context.framework)

        # Analyze dependencies
        context.dependencies = self._analyze_dependencies(path, context.framework)

        # Find entry points
        context.entry_points = self._find_entry_points(path, context.framework)

        # Find configuration files
        context.configuration_files = self._find_config_files(path, context.framework)

        # Detect build system and test framework
        context.build_system = self._detect_build_system(path, context.framework)
        context.test_framework = self._detect_test_framework(path, context.framework)

        # Calculate complexity
        context.complexity_score = self._calculate_complexity(path, context)

        # Calculate code quality
        context.code_quality_score = self._calculate_code_quality(path, context)

        # Set last modified
        context.last_modified = self._get_last_modified(path)

        return context

    def _detect_framework(self, path: Path) -> str:
        """Detect the project's framework"""
        for framework, detector in self.framework_detectors.items():
            if detector(path):
                return framework
        return "unknown"

    def _detect_react(self, path: Path) -> bool:
        """Detect React projects"""
        if (path / 'package.json').exists():
            try:
                package_data = json.loads((path / 'package.json').read_text())
                deps = package_data.get('dependencies', {})
                dev_deps = package_data.get('devDependencies', {})

                react_deps = {'react', 'react-dom', 'next'}
                if any(dep in deps or dep in dev_deps for dep in react_deps):
                    return True
            except:
                pass
        return False

    def _detect_nextjs(self, path: Path) -> bool:
        """Detect Next.js projects"""
        if (path / 'next.config.js').exists() or (path / 'next.config.mjs').exists():
            return True
        if (path / 'package.json').exists():
            try:
                package_data = json.loads((path / 'package.json').read_text())
                deps = package_data.get('dependencies', {})
                if 'next' in deps:
                    return True
            except:
                pass
        return False

    def _detect_laravel(self, path: Path) -> bool:
        """Detect Laravel projects"""
        return (path / 'artisan').exists() and (path / 'composer.json').exists()

    def _detect_flutter(self, path: Path) -> bool:
        """Detect Flutter projects"""
        return (path / 'pubspec.yaml').exists() and (path / 'lib').exists()

    def _detect_django(self, path: Path) -> bool:
        """Detect Django projects"""
        if (path / 'manage.py').exists():
            # Check for Django in requirements
            for req_file in ['requirements.txt', 'pyproject.toml', 'Pipfile']:
                if (path / req_file).exists():
                    content = (path / req_file).read_text().lower()
                    if 'django' in content:
                        return True
        return False

    def _detect_fastapi(self, path: Path) -> bool:
        """Detect FastAPI projects"""
        for req_file in ['requirements.txt', 'pyproject.toml', 'Pipfile']:
            if (path / req_file).exists():
                content = (path / req_file).read_text().lower()
                if 'fastapi' in content:
                    return True
        return False

    def _detect_spring(self, path: Path) -> bool:
        """Detect Spring Boot projects"""
        return (path / 'pom.xml').exists() or (path / 'build.gradle').exists()

    def _detect_dotnet(self, path: Path) -> bool:
        """Detect .NET projects"""
        return any(path.glob('*.csproj')) or any(path.glob('*.fsproj'))

    def _detect_vue(self, path: Path) -> bool:
        """Detect Vue.js projects"""
        if (path / 'package.json').exists():
            try:
                package_data = json.loads((path / 'package.json').read_text())
                deps = package_data.get('dependencies', {})
                dev_deps = package_data.get('devDependencies', {})
                if 'vue' in deps or 'vue' in dev_deps:
                    return True
            except:
                pass
        return False

    def _detect_angular(self, path: Path) -> bool:
        """Detect Angular projects"""
        return (path / 'angular.json').exists()

    def _detect_language(self, path: Path) -> str:
        """Detect primary programming language"""
        # Count files by extension
        extensions = {}
        for file_path in path.rglob('*'):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                extensions[ext] = extensions.get(ext, 0) + 1

        # Language detection based on file extensions
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.php': 'php',
            '.dart': 'dart',
            '.java': 'java',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.swift': 'swift',
            '.kt': 'kotlin',
        }

        # Find most common language
        max_count = 0
        primary_lang = 'unknown'

        for ext, count in extensions.items():
            if ext in language_map and count > max_count:
                max_count = count
                primary_lang = language_map[ext]

        return primary_lang

    def _detect_project_type(self, path: Path, framework: str) -> str:
        """Detect project type based on structure and framework"""
        if framework in ['react', 'nextjs', 'vue', 'angular']:
            return 'web'
        elif framework == 'flutter':
            return 'mobile'
        elif framework in ['laravel', 'django', 'fastapi', 'spring']:
            # Check if it has frontend components
            if (path / 'resources' / 'js').exists() or (path / 'frontend').exists():
                return 'fullstack'
            else:
                return 'api'
        elif framework == 'dotnet':
            return 'web_api'  # Could be web, desktop, etc.
        else:
            return 'unknown'

    def _analyze_dependencies(self, path: Path, framework: str) -> List[str]:
        """Analyze project dependencies"""
        dependencies = []

        try:
            if framework in ['react', 'nextjs', 'vue', 'angular']:
                if (path / 'package.json').exists():
                    package_data = json.loads((path / 'package.json').read_text())
                    deps = package_data.get('dependencies', {})
                    dev_deps = package_data.get('devDependencies', {})
                    dependencies.extend(list(deps.keys()) + list(dev_deps.keys()))

            elif framework == 'laravel':
                if (path / 'composer.json').exists():
                    composer_data = json.loads((path / 'composer.json').read_text())
                    deps = composer_data.get('require', {})
                    dev_deps = composer_data.get('require-dev', {})
                    dependencies.extend(list(deps.keys()) + list(dev_deps.keys()))

            elif framework == 'flutter':
                if (path / 'pubspec.yaml').exists():
                    # Simple YAML parsing for dependencies
                    content = (path / 'pubspec.yaml').read_text()
                    if 'dependencies:' in content:
                        deps_section = content.split('dependencies:')[1].split('dev_dependencies:')[0]
                        for line in deps_section.split('\n'):
                            if ':' in line and not line.strip().startswith('#'):
                                dep = line.split(':')[0].strip()
                                if dep:
                                    dependencies.append(dep)

            elif framework in ['django', 'fastapi']:
                for req_file in ['requirements.txt', 'pyproject.toml', 'Pipfile']:
                    if (path / req_file).exists():
                        content = (path / req_file).read_text()
                        for line in content.split('\n'):
                            if line.strip() and not line.strip().startswith('#'):
                                if '==' in line:
                                    dep = line.split('==')[0].strip()
                                elif '>=' in line:
                                    dep = line.split('>=')[0].strip()
                                else:
                                    dep = line.strip()
                                dependencies.append(dep)

        except Exception as e:
            print(f"Error analyzing dependencies: {e}")

        return dependencies

    def _find_entry_points(self, path: Path, framework: str) -> List[str]:
        """Find application entry points"""
        entry_points = []

        if framework in ['react', 'nextjs', 'vue', 'angular']:
            # Look for main JS/TS files
            for pattern in ['src/main.*', 'src/index.*', 'src/App.*']:
                for file_path in path.glob(pattern):
                    entry_points.append(str(file_path.relative_to(path)))

        elif framework == 'laravel':
            entry_points = ['public/index.php', 'artisan']

        elif framework == 'flutter':
            entry_points = ['lib/main.dart']

        elif framework in ['django', 'fastapi']:
            # Look for main Python files
            for file_path in path.glob('*.py'):
                if file_path.name in ['main.py', 'app.py', 'wsgi.py', 'asgi.py']:
                    entry_points.append(file_path.name)

        return entry_points

    def _find_config_files(self, path: Path, framework: str) -> List[str]:
        """Find configuration files"""
        config_files = []

        # Common config files
        common_configs = [
            'package.json', 'composer.json', 'pubspec.yaml',
            'requirements.txt', 'pyproject.toml', 'Pipfile',
            'tsconfig.json', 'webpack.config.js', 'vite.config.js',
            '.env', '.env.example', 'docker-compose.yml'
        ]

        for config in common_configs:
            if (path / config).exists():
                config_files.append(config)

        # Framework-specific configs
        if framework == 'laravel':
            laravel_configs = ['config/app.php', 'config/database.php', '.env']
            for config in laravel_configs:
                if (path / config).exists():
                    config_files.append(config)

        elif framework in ['react', 'nextjs']:
            react_configs = ['next.config.js', 'tailwind.config.js', 'postcss.config.js']
            for config in react_configs:
                if (path / config).exists():
                    config_files.append(config)

        return config_files

    def _detect_build_system(self, path: Path, framework: str) -> Optional[str]:
        """Detect build system"""
        if (path / 'package.json').exists():
            return 'npm/yarn'
        elif (path / 'composer.json').exists():
            return 'composer'
        elif (path / 'pubspec.yaml').exists():
            return 'flutter'
        elif (path / 'pom.xml').exists():
            return 'maven'
        elif (path / 'build.gradle').exists():
            return 'gradle'
        elif any(path.glob('*.csproj')):
            return 'msbuild'
        else:
            return None

    def _detect_test_framework(self, path: Path, framework: str) -> Optional[str]:
        """Detect test framework"""
        if framework in ['react', 'nextjs', 'vue', 'angular']:
            return 'jest'
        elif framework == 'laravel':
            return 'phpunit'
        elif framework == 'flutter':
            return 'flutter_test'
        elif framework in ['django', 'fastapi']:
            return 'pytest'
        elif framework == 'spring':
            return 'junit'
        else:
            return None

    def _calculate_complexity(self, path: Path, context: ProjectContext) -> float:
        """Calculate project complexity score"""
        score = 0.0

        # File count factor
        file_count = sum(1 for _ in path.rglob('*') if _.is_file())
        score += min(file_count / 1000, 1.0) * 0.3

        # Dependency count factor
        dep_count = len(context.dependencies)
        score += min(dep_count / 100, 1.0) * 0.3

        # Framework complexity factor
        framework_complexity = {
            'react': 0.6, 'nextjs': 0.7, 'vue': 0.5, 'angular': 0.8,
            'laravel': 0.7, 'django': 0.6, 'fastapi': 0.4, 'spring': 0.9,
            'flutter': 0.8, 'dotnet': 0.8
        }
        score += framework_complexity.get(context.framework, 0.5) * 0.4

        return round(score, 2)

    def _calculate_code_quality(self, path: Path, context: ProjectContext) -> float:
        """Calculate code quality score"""
        score = 0.5  # Base score

        # Check for test files
        test_files = list(path.glob('**/*test*')) + list(path.glob('**/test*'))
        if test_files:
            score += 0.1

        # Check for documentation
        if (path / 'README.md').exists():
            score += 0.1

        # Check for linting configuration
        lint_files = ['.eslintrc', 'eslint.config.js', 'tsconfig.json', '.flake8', 'pylint.rc']
        for lint_file in lint_files:
            if (path / lint_file).exists():
                score += 0.1
                break

        # Check for CI/CD
        ci_files = ['.github/workflows', '.gitlab-ci.yml', 'Jenkinsfile']
        for ci_file in ci_files:
            if (path / ci_file).exists():
                score += 0.1
                break

        return round(min(score, 1.0), 2)

    def _get_last_modified(self, path: Path) -> datetime:
        """Get last modified timestamp"""
        try:
            # Get the most recent modification time
            latest_time = 0
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    latest_time = max(latest_time, file_path.stat().st_mtime)

            return datetime.fromtimestamp(latest_time)
        except:
            return datetime.now()

    def generate_insights(self, context: ProjectContext) -> List[ContextInsight]:
        """Generate contextual insights for the project"""
        insights = []

        # Generate insights from different categories
        for category, generator in self.insight_generators.items():
            try:
                category_insights = generator(context)
                insights.extend(category_insights)
            except Exception as e:
                print(f"Error generating {category} insights: {e}")

        return insights

    def _generate_security_insights(self, context: ProjectContext) -> List[ContextInsight]:
        """Generate security-related insights"""
        insights = []

        # Check for security-related dependencies
        security_deps = ['helmet', 'cors', 'bcrypt', 'jsonwebtoken', 'passport']
        found_security = any(dep in context.dependencies for dep in security_deps)

        if not found_security and context.framework in ['react', 'nextjs', 'laravel']:
            insights.append(ContextInsight(
                category='security',
                title='Security Dependencies Missing',
                description='Consider adding security-related packages for better protection',
                severity='medium',
                suggested_actions=[
                    'Add helmet for security headers',
                    'Implement proper CORS configuration',
                    'Use bcrypt for password hashing'
                ]
            ))

        # Check for environment files
        if not any('.env' in config for config in context.configuration_files):
            insights.append(ContextInsight(
                category='security',
                title='Environment Configuration',
                description='Consider using environment variables for sensitive configuration',
                severity='low',
                suggested_actions=[
                    'Create .env file for environment variables',
                    'Add .env to .gitignore',
                    'Use dotenv package for loading environment variables'
                ]
            ))

        return insights

    def _generate_performance_insights(self, context: ProjectContext) -> List[ContextInsight]:
        """Generate performance-related insights"""
        insights = []

        # Check bundle size for web projects
        if context.project_type == 'web':
            bundle_deps = ['webpack-bundle-analyzer', 'vite-bundle-analyzer']
            has_bundle_analyzer = any(dep in context.dependencies for dep in bundle_deps)

            if not has_bundle_analyzer:
                insights.append(ContextInsight(
                    category='performance',
                    title='Bundle Analysis',
                    description='Consider analyzing bundle size for performance optimization',
                    severity='low',
                    suggested_actions=[
                        'Add webpack-bundle-analyzer or similar',
                        'Monitor bundle size in CI/CD',
                        'Implement code splitting'
                    ]
                ))

        # Check for caching
        cache_deps = ['redis', 'memcached', 'node-cache']
        has_caching = any(dep in context.dependencies for dep in cache_deps)

        if not has_caching and context.complexity_score > 0.7:
            insights.append(ContextInsight(
                category='performance',
                title='Caching Strategy',
                description='High complexity project may benefit from caching',
                severity='medium',
                suggested_actions=[
                    'Implement Redis for session storage',
                    'Add caching for expensive operations',
                    'Consider CDN for static assets'
                ]
            ))

        return insights

    def _generate_code_quality_insights(self, context: ProjectContext) -> List[ContextInsight]:
        """Generate code quality insights"""
        insights = []

        if context.code_quality_score < 0.6:
            insights.append(ContextInsight(
                category='code_quality',
                title='Code Quality Improvements Needed',
                description=f'Code quality score: {context.code_quality_score:.1f}/1.0',
                severity='medium',
                suggested_actions=[
                    'Add ESLint/Prettier configuration',
                    'Implement pre-commit hooks',
                    'Add comprehensive test coverage',
                    'Set up automated code review'
                ]
            ))

        return insights

    def _generate_best_practice_insights(self, context: ProjectContext) -> List[ContextInsight]:
        """Generate best practice insights"""
        insights = []

        # Check for README
        if not any('readme' in config.lower() for config in context.configuration_files):
            insights.append(ContextInsight(
                category='best_practices',
                title='Project Documentation',
                description='Consider adding a README file for project documentation',
                severity='low',
                suggested_actions=[
                    'Create comprehensive README.md',
                    'Add installation instructions',
                    'Document API endpoints',
                    'Include development setup guide'
                ]
            ))

        return insights

    def _generate_architecture_insights(self, context: ProjectContext) -> List[ContextInsight]:
        """Generate architecture insights"""
        insights = []

        # Check for proper project structure
        if context.framework == 'react' and not any('src' in ep for ep in context.entry_points):
            insights.append(ContextInsight(
                category='architecture',
                title='Project Structure',
                description='Consider organizing code in src/ directory',
                severity='low',
                suggested_actions=[
                    'Create src/ directory structure',
                    'Separate components, hooks, and utilities',
                    'Implement feature-based organization'
                ]
            ))

        return insights


# Global context analyzer instance
context_analyzer = SmartContextAnalyzer()