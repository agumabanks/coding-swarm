"""
Advanced Code Generation Engine for Sanaa
Provides AI-powered code generation with quality assurance and performance optimization
"""
from __future__ import annotations

import re
import ast
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import asyncio
from enum import Enum


class CodeQuality(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class GenerationStrategy(Enum):
    TEMPLATE_BASED = "template_based"
    PATTERN_BASED = "pattern_based"
    AI_GENERATED = "ai_generated"
    HYBRID = "hybrid"


@dataclass
class CodeSnippet:
    """Represents a generated code snippet"""
    id: str
    language: str
    framework: str
    content: str
    description: str
    tags: List[str]
    quality_score: float
    generation_strategy: GenerationStrategy
    dependencies: List[str] = field(default_factory=list)
    test_cases: List[str] = field(default_factory=list)
    performance_notes: List[str] = field(default_factory=list)
    security_notes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PatternLibrary:
    """Library of code patterns and templates"""
    patterns: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add_pattern(self, name: str, pattern_data: Dict[str, Any]):
        """Add a code pattern to the library"""
        self.patterns[name] = pattern_data

    def get_pattern(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a pattern by name"""
        return self.patterns.get(name)

    def find_similar_patterns(self, requirements: Dict[str, Any]) -> List[Tuple[str, float]]:
        """Find patterns similar to given requirements"""
        matches = []

        for name, pattern in self.patterns.items():
            similarity = self._calculate_similarity(requirements, pattern)
            if similarity > 0.3:  # Minimum similarity threshold
                matches.append((name, similarity))

        return sorted(matches, key=lambda x: x[1], reverse=True)

    def _calculate_similarity(self, req1: Dict[str, Any], req2: Dict[str, Any]) -> float:
        """Calculate similarity between two requirement sets"""
        common_keys = set(req1.keys()) & set(req2.keys())
        if not common_keys:
            return 0.0

        matches = 0
        for key in common_keys:
            if req1[key] == req2[key]:
                matches += 1

        return matches / len(common_keys)


@dataclass
class CodeQualityChecker:
    """Automated code quality assessment"""

    def __init__(self):
        self.quality_rules = self._load_quality_rules()

    def _load_quality_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load code quality rules"""
        return {
            'python': {
                'max_line_length': 88,
                'max_function_length': 50,
                'required_docstrings': True,
                'naming_conventions': True,
                'error_handling': True
            },
            'javascript': {
                'max_line_length': 100,
                'max_function_length': 30,
                'consistent_spacing': True,
                'semicolon_usage': True,
                'async_await_usage': True
            },
            'typescript': {
                'max_line_length': 100,
                'strict_types': True,
                'interface_usage': True,
                'generic_types': True,
                'error_handling': True
            }
        }

    def assess_quality(self, code: str, language: str) -> Tuple[CodeQuality, Dict[str, Any]]:
        """Assess the quality of generated code"""
        issues = []
        score = 100

        rules = self.quality_rules.get(language, {})

        # Check line length
        max_length = rules.get('max_line_length', 80)
        for i, line in enumerate(code.split('\n'), 1):
            if len(line) > max_length:
                issues.append(f"Line {i} exceeds maximum length ({len(line)} > {max_length})")
                score -= 5

        # Language-specific checks
        if language == 'python':
            score -= self._check_python_quality(code, issues)
        elif language in ['javascript', 'typescript']:
            score -= self._check_js_quality(code, issues, language)

        # General checks
        score -= self._check_general_quality(code, issues)

        # Determine quality level
        if score >= 90:
            quality = CodeQuality.EXCELLENT
        elif score >= 75:
            quality = CodeQuality.GOOD
        elif score >= 60:
            quality = CodeQuality.FAIR
        else:
            quality = CodeQuality.POOR

        return quality, {
            'score': score,
            'issues': issues,
            'suggestions': self._generate_suggestions(issues, language)
        }

    def _check_python_quality(self, code: str, issues: List[str]) -> int:
        """Check Python-specific quality issues"""
        penalty = 0

        # Check for docstrings
        if 'def ' in code and '"""' not in code and "'''" not in code:
            issues.append("Missing docstrings for functions")
            penalty += 10

        # Check naming conventions
        if re.search(r'\b[A-Z][a-zA-Z0-9]*[A-Z]', code):  # camelCase in Python
            issues.append("Using camelCase instead of snake_case")
            penalty += 5

        # Check for bare except clauses
        if 'except:' in code:
            issues.append("Using bare except clause")
            penalty += 15

        return penalty

    def _check_js_quality(self, code: str, issues: List[str], language: str) -> int:
        """Check JavaScript/TypeScript-specific quality issues"""
        penalty = 0

        # Check for var usage (prefer let/const)
        if 'var ' in code:
            issues.append("Using 'var' instead of 'let' or 'const'")
            penalty += 5

        # Check for semicolons
        lines = code.split('\n')
        missing_semicolons = 0
        for line in lines:
            line = line.strip()
            if (line and not line.startswith('//') and not line.startswith('/*') and
                not line.endswith(';') and not line.endswith('{') and not line.endswith('}') and
                not line.endswith(',') and not line.startswith('import') and
                not line.startswith('export') and '=>' not in line):
                missing_semicolons += 1

        if missing_semicolons > 0:
            issues.append(f"Missing semicolons on {missing_semicolons} lines")
            penalty += missing_semicolons * 2

        # TypeScript specific checks
        if language == 'typescript':
            if 'any' in code and 'unknown' not in code:
                issues.append("Using 'any' type instead of specific types")
                penalty += 10

        return penalty

    def _check_general_quality(self, code: str, issues: List[str]) -> int:
        """Check general code quality issues"""
        penalty = 0

        # Check for TODO comments
        if 'TODO' in code.upper():
            issues.append("Contains TODO comments")
            penalty += 5

        # Check for console.log statements
        if 'console.log' in code:
            issues.append("Contains console.log statements")
            penalty += 5

        # Check for hardcoded values
        hardcoded_patterns = [r'\b\d{3,}\b', r'["\'][^"\']*localhost[^"\']*["\']']
        for pattern in hardcoded_patterns:
            if re.search(pattern, code):
                issues.append("Contains potential hardcoded values")
                penalty += 5
                break

        # Check code complexity (simple heuristic)
        lines = len(code.split('\n'))
        if lines > 100:
            issues.append("Code is quite long, consider breaking into smaller functions")
            penalty += 10

        return penalty

    def _generate_suggestions(self, issues: List[str], language: str) -> List[str]:
        """Generate improvement suggestions based on issues"""
        suggestions = []

        for issue in issues:
            if 'line length' in issue:
                suggestions.append("Break long lines into multiple lines for better readability")
            elif 'docstring' in issue:
                suggestions.append("Add comprehensive docstrings to all public functions")
            elif 'naming' in issue:
                suggestions.append(f"Follow {language} naming conventions (snake_case for Python, camelCase for JS)")
            elif 'bare except' in issue:
                suggestions.append("Use specific exception types instead of bare except clauses")
            elif 'var' in issue:
                suggestions.append("Use 'const' for constants and 'let' for variables instead of 'var'")
            elif 'semicolon' in issue:
                suggestions.append("Add semicolons at the end of statements")
            elif 'any type' in issue:
                suggestions.append("Use specific TypeScript types instead of 'any'")
            elif 'TODO' in issue:
                suggestions.append("Address TODO comments or convert them to proper issues")
            elif 'console.log' in issue:
                suggestions.append("Remove debug console.log statements or use proper logging")
            elif 'hardcoded' in issue:
                suggestions.append("Replace hardcoded values with configuration or environment variables")

        return suggestions


@dataclass
class PerformanceOptimizer:
    """Code performance optimization system"""

    def __init__(self):
        self.optimization_patterns = self._load_optimization_patterns()

    def _load_optimization_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load performance optimization patterns"""
        return {
            'python': {
                'list_comprehension': {
                    'pattern': r'(\w+)\s*=\s*\[\s*(\w+)\s+for\s+(\w+)\s+in\s+(.+)\s*\]',
                    'replacement': '\\1 = [\\2 for \\3 in \\4]',
                    'benefit': 'More memory efficient than traditional loops'
                },
                'generator_expression': {
                    'pattern': r'(\w+)\s*=\s*\[(.+?)\]',
                    'replacement': '\\1 = (\\2)',
                    'condition': 'large_dataset',
                    'benefit': 'Uses less memory for large datasets'
                }
            },
            'javascript': {
                'arrow_functions': {
                    'pattern': r'function\s*\(\s*(\w+)\s*\)\s*{\s*return\s+(.+?);\s*}',
                    'replacement': '(\\1) => \\2',
                    'benefit': 'More concise and proper this binding'
                },
                'destructuring': {
                    'pattern': r'const\s+(\w+)\s*=\s*(\w+)\.(\w+);\s*const\s+(\w+)\s*=\s*\w+\.(\w+);',
                    'replacement': 'const {\\3, \\5} = \\2;',
                    'benefit': 'Cleaner code and better performance'
                }
            }
        }

    def optimize_code(self, code: str, language: str, context: Dict[str, Any] = None) -> Tuple[str, List[str]]:
        """Optimize code for better performance"""
        optimized_code = code
        optimizations_applied = []

        patterns = self.optimization_patterns.get(language, {})

        for pattern_name, pattern_data in patterns.items():
            pattern = pattern_data['pattern']
            replacement = pattern_data['replacement']

            # Check conditions if specified
            if 'condition' in pattern_data:
                condition = pattern_data['condition']
                if context and not self._check_condition(condition, context):
                    continue

            # Apply optimization
            if re.search(pattern, optimized_code, re.MULTILINE | re.DOTALL):
                optimized_code = re.sub(pattern, replacement, optimized_code, flags=re.MULTILINE | re.DOTALL)
                optimizations_applied.append(pattern_data['benefit'])

        return optimized_code, optimizations_applied

    def _check_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Check if optimization condition is met"""
        if condition == 'large_dataset':
            return context.get('expected_data_size', 'small') == 'large'
        return True

    def analyze_performance(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code for performance characteristics"""
        analysis = {
            'complexity': 'low',
            'memory_usage': 'low',
            'cpu_usage': 'low',
            'bottlenecks': [],
            'recommendations': []
        }

        # Simple complexity analysis
        lines = len(code.split('\n'))
        if lines > 50:
            analysis['complexity'] = 'medium'
        if lines > 100:
            analysis['complexity'] = 'high'

        # Language-specific analysis
        if language == 'python':
            analysis.update(self._analyze_python_performance(code))
        elif language in ['javascript', 'typescript']:
            analysis.update(self._analyze_js_performance(code))

        return analysis

    def _analyze_python_performance(self, code: str) -> Dict[str, Any]:
        """Analyze Python code performance"""
        issues = []

        # Check for inefficient patterns
        if 'for ' in code and ' in range(' in code and 'list(' not in code:
            issues.append("Consider using list comprehensions for better performance")

        if 'global ' in code:
            issues.append("Global variable usage may impact performance")

        return {'bottlenecks': issues}

    def _analyze_js_performance(self, code: str) -> Dict[str, Any]:
        """Analyze JavaScript code performance"""
        issues = []

        # Check for DOM manipulation in loops
        if 'for' in code and 'getElementById' in code:
            issues.append("DOM manipulation inside loops can cause performance issues")

        # Check for memory leaks
        if 'addEventListener' in code and 'removeEventListener' not in code:
            issues.append("Potential memory leak: event listeners not removed")

        return {'bottlenecks': issues}


class CodeGenerationEngine:
    """Main code generation engine with quality assurance"""

    def __init__(self):
        self.pattern_library = PatternLibrary()
        self.quality_assurance = CodeQualityChecker()
        self.performance_optimizer = PerformanceOptimizer()
        self.generated_snippets: Dict[str, CodeSnippet] = {}

    async def generate_optimized_code(self, requirements: Dict[str, Any]) -> CodeSnippet:
        """Generate optimized code based on requirements"""
        language = requirements.get('language', 'python')
        framework = requirements.get('framework', 'general')
        description = requirements.get('description', 'Generated code')

        # Determine generation strategy
        strategy = self._select_generation_strategy(requirements)

        # Generate code based on strategy
        if strategy == GenerationStrategy.TEMPLATE_BASED:
            code = await self._generate_from_template(requirements)
        elif strategy == GenerationStrategy.PATTERN_BASED:
            code = await self._generate_from_patterns(requirements)
        elif strategy == GenerationStrategy.AI_GENERATED:
            code = await self._generate_with_ai(requirements)
        else:  # HYBRID
            code = await self._generate_hybrid(requirements)

        # Optimize performance
        optimized_code, optimizations = self.performance_optimizer.optimize_code(
            code, language, requirements
        )

        # Assess quality
        quality, quality_report = self.quality_assurance.assess_quality(optimized_code, language)

        # Generate additional metadata
        snippet_id = self._generate_snippet_id()
        dependencies = self._extract_dependencies(optimized_code, language)
        test_cases = self._generate_test_cases(optimized_code, language, requirements)
        security_notes = self._analyze_security(optimized_code, language)
        performance_notes = self._generate_performance_notes(optimized_code, language)

        # Create snippet
        snippet = CodeSnippet(
            id=snippet_id,
            language=language,
            framework=framework,
            content=optimized_code,
            description=description,
            tags=requirements.get('tags', []),
            quality_score=quality_report['score'] / 100.0,
            generation_strategy=strategy,
            dependencies=dependencies,
            test_cases=test_cases,
            performance_notes=performance_notes,
            security_notes=security_notes
        )

        # Store snippet
        self.generated_snippets[snippet_id] = snippet

        return snippet

    def _select_generation_strategy(self, requirements: Dict[str, Any]) -> GenerationStrategy:
        """Select the best generation strategy based on requirements"""
        complexity = requirements.get('complexity', 'simple')
        has_examples = 'examples' in requirements
        has_patterns = bool(self.pattern_library.find_similar_patterns(requirements))

        if complexity == 'simple' and has_patterns:
            return GenerationStrategy.PATTERN_BASED
        elif has_examples:
            return GenerationStrategy.TEMPLATE_BASED
        elif complexity == 'complex':
            return GenerationStrategy.AI_GENERATED
        else:
            return GenerationStrategy.HYBRID

    async def _generate_from_template(self, requirements: Dict[str, Any]) -> str:
        """Generate code from templates"""
        # This would use template engines like Jinja2
        # For now, return a placeholder
        return f"# Generated code for {requirements.get('description', 'task')}\n# Template-based generation\n\nprint('Hello, World!')"

    async def _generate_from_patterns(self, requirements: Dict[str, Any]) -> str:
        """Generate code from patterns"""
        similar_patterns = self.pattern_library.find_similar_patterns(requirements)

        if similar_patterns:
            pattern_name, _ = similar_patterns[0]
            pattern = self.pattern_library.get_pattern(pattern_name)
            return pattern.get('template', '# Pattern-based code')
        else:
            return "# No suitable pattern found"

    async def _generate_with_ai(self, requirements: Dict[str, Any]) -> str:
        """Generate code using AI (placeholder for LLM integration)"""
        # This would integrate with an LLM like GPT
        # For now, return a placeholder
        return f"# AI-generated code for {requirements.get('description', 'task')}\n# Advanced AI generation\n\ndef main():\n    pass"

    async def _generate_hybrid(self, requirements: Dict[str, Any]) -> str:
        """Generate code using hybrid approach"""
        # Combine multiple strategies
        base_code = await self._generate_from_patterns(requirements)
        if base_code == "# No suitable pattern found":
            base_code = await self._generate_with_ai(requirements)

        return base_code

    def _generate_snippet_id(self) -> str:
        """Generate unique snippet ID"""
        import uuid
        return str(uuid.uuid4())

    def _extract_dependencies(self, code: str, language: str) -> List[str]:
        """Extract dependencies from generated code"""
        dependencies = []

        if language == 'python':
            # Look for import statements
            import_pattern = r'^(?:from\s+(\w+)|import\s+(\w+))'
            matches = re.findall(import_pattern, code, re.MULTILINE)
            for match in matches:
                dep = match[0] or match[1]
                if dep and dep not in ['os', 'sys', 'json', 'typing']:  # Skip standard library
                    dependencies.append(dep)

        elif language in ['javascript', 'typescript']:
            # Look for import statements
            import_pattern = r'(?:import\s+.*?\s+from\s+["\']([^"\']+)["\'])|(?:require\s*\(\s*["\']([^"\']+)["\']\s*\))'
            matches = re.findall(import_pattern, code)
            for match in matches:
                dep = match[0] or match[1]
                if dep and not dep.startswith('.'):  # Skip relative imports
                    dependencies.append(dep)

        return list(set(dependencies))  # Remove duplicates

    def _generate_test_cases(self, code: str, language: str, requirements: Dict[str, Any]) -> List[str]:
        """Generate test cases for the code"""
        test_cases = []

        if language == 'python':
            # Generate basic unit test structure
            test_cases.append("""
import unittest
from your_module import YourClass

class TestYourClass(unittest.TestCase):
    def test_basic_functionality(self):
        # Add your test here
        pass

if __name__ == '__main__':
    unittest.main()
""")

        elif language in ['javascript', 'typescript']:
            # Generate Jest test structure
            test_cases.append("""
const { YourClass } = require('./your-module');

describe('YourClass', () => {
    test('basic functionality', () => {
        // Add your test here
        expect(true).toBe(true);
    });
});
""")

        return test_cases

    def _analyze_security(self, code: str, language: str) -> List[str]:
        """Analyze code for security issues"""
        security_notes = []

        # Check for common security issues
        if 'eval(' in code:
            security_notes.append("WARNING: Code contains eval() which can be dangerous")

        if 'innerHTML' in code and language in ['javascript', 'typescript']:
            security_notes.append("WARNING: Direct innerHTML manipulation can lead to XSS attacks")

        if 'password' in code.lower() and 'encrypt' not in code.lower():
            security_notes.append("WARNING: Password handling without encryption detected")

        if 'sql' in code.lower() and 'prepare' not in code.lower():
            security_notes.append("WARNING: Potential SQL injection vulnerability")

        return security_notes

    def _generate_performance_notes(self, code: str, language: str) -> List[str]:
        """Generate performance-related notes"""
        performance_notes = []

        # Analyze code structure
        lines = len(code.split('\n'))
        if lines > 100:
            performance_notes.append("Consider breaking large functions into smaller ones")

        if 'for ' in code and 'for ' in code.replace('for ', '', 1):
            performance_notes.append("Nested loops detected - consider optimization")

        if 'global ' in code and language == 'python':
            performance_notes.append("Global variables can impact performance")

        return performance_notes

    def get_snippet(self, snippet_id: str) -> Optional[CodeSnippet]:
        """Get a generated snippet by ID"""
        return self.generated_snippets.get(snippet_id)

    def list_snippets(self, language: str = None, framework: str = None, tags: List[str] = None) -> List[CodeSnippet]:
        """List generated snippets with optional filtering"""
        snippets = list(self.generated_snippets.values())

        if language:
            snippets = [s for s in snippets if s.language == language]

        if framework:
            snippets = [s for s in snippets if s.framework == framework]

        if tags:
            snippets = [s for s in snippets if any(tag in s.tags for tag in tags)]

        return sorted(snippets, key=lambda s: s.created_at, reverse=True)

    def improve_snippet(self, snippet_id: str, feedback: Dict[str, Any]) -> Optional[CodeSnippet]:
        """Improve a snippet based on feedback"""
        snippet = self.get_snippet(snippet_id)
        if not snippet:
            return None

        # Apply improvements based on feedback
        improved_content = snippet.content

        if feedback.get('add_error_handling'):
            improved_content = self._add_error_handling(improved_content, snippet.language)

        if feedback.get('optimize_performance'):
            improved_content, _ = self.performance_optimizer.optimize_code(
                improved_content, snippet.language
            )

        # Create improved snippet
        improved_snippet = CodeSnippet(
            id=self._generate_snippet_id(),
            language=snippet.language,
            framework=snippet.framework,
            content=improved_content,
            description=f"Improved: {snippet.description}",
            tags=snippet.tags,
            quality_score=min(snippet.quality_score + 0.1, 1.0),  # Slight improvement
            generation_strategy=GenerationStrategy.HYBRID,
            dependencies=snippet.dependencies,
            test_cases=snippet.test_cases,
            performance_notes=snippet.performance_notes,
            security_notes=snippet.security_notes
        )

        self.generated_snippets[improved_snippet.id] = improved_snippet
        return improved_snippet

    def _add_error_handling(self, code: str, language: str) -> str:
        """Add error handling to code"""
        if language == 'python':
            # Simple error handling addition
            if 'def ' in code and 'try:' not in code:
                return code.replace('def ', 'def ', 1).replace(
                    '\n    ', '\n    try:\n        ', 1
                ) + '\n    except Exception as e:\n        print(f"Error: {e}")'
        elif language in ['javascript', 'typescript']:
            # Add try-catch for functions
            if 'function' in code and 'try {' not in code:
                return code.replace('{', '{\n    try {', 1) + '\n    } catch (error) {\n        console.error(error);\n    }'

        return code


# Global code generation engine instance
code_generation_engine = CodeGenerationEngine()


def get_code_generation_engine() -> CodeGenerationEngine:
    """Get global code generation engine instance"""
    return code_generation_engine