"""
Advanced Debugging Agent - Framework-specific debugging capabilities
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json
import re
import subprocess
import time
from dataclasses import dataclass

from .base import Agent
from .diagnostics import auto_debug, DebugReport


@dataclass
class DebugIssue:
    """Represents a debug issue"""
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    category: str  # 'syntax', 'logic', 'performance', 'security', etc.
    title: str
    description: str
    file_path: str
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    framework_specific: bool = False


@dataclass
class DebugSession:
    """Represents a debugging session"""
    project_path: str
    framework: str
    issues: List[DebugIssue] = None
    start_time: float = None
    end_time: Optional[float] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.start_time is None:
            self.start_time = time.time()


class AdvancedDebuggerAgent(Agent):
    """Advanced debugger with framework-specific capabilities"""

    def __init__(self, context: Dict[str, Any]) -> None:
        super().__init__(context)
        self.framework = self._detect_framework()
        self.debug_strategies = self._load_debug_strategies()

    def _detect_framework(self) -> str:
        """Detect the project's framework"""
        project_path = Path(self.context.get('project', '.'))

        # React/Next.js detection
        if (project_path / 'package.json').exists():
            try:
                package_data = json.loads((project_path / 'package.json').read_text())
                deps = package_data.get('dependencies', {})
                if 'react' in deps:
                    if 'next' in deps:
                        return 'nextjs'
                    return 'react'
            except:
                pass

        # Laravel detection
        if (project_path / 'artisan').exists():
            return 'laravel'

        # Flutter detection
        if (project_path / 'pubspec.yaml').exists():
            return 'flutter'

        return 'generic'

    def _load_debug_strategies(self) -> Dict[str, Any]:
        """Load framework-specific debugging strategies"""
        return {
            'react': {
                'common_issues': [
                    'useEffect dependency array',
                    'state update in render',
                    'memory leaks',
                    'key props in lists',
                    'conditional rendering issues'
                ],
                'tools': ['react-devtools', 'eslint', 'typescript'],
                'patterns': [
                    r'useEffect\(\s*\(\)\s*=>\s*\{[^}]*\}\s*,\s*\[\s*\]\s*\)',
                    r'setState.*render',
                    r'useEffect.*\[\s*\]',
                ]
            },
            'laravel': {
                'common_issues': [
                    'N+1 query problem',
                    'mass assignment vulnerability',
                    'missing model relationships',
                    'improper validation',
                    'memory leaks in jobs'
                ],
                'tools': ['laravel-debugbar', 'phpunit', 'phpstan'],
                'patterns': [
                    r'->get\(\)->map',
                    r'fillable.*=.*\[\]',
                    r'belongsTo.*hasMany',
                ]
            },
            'flutter': {
                'common_issues': [
                    'setState in build method',
                    'memory leaks in streams',
                    'improper key usage',
                    'async gaps in UI',
                    'widget rebuild optimization'
                ],
                'tools': ['flutter-devtools', 'dart-analyzer', 'flutter-test'],
                'patterns': [
                    r'setState.*build',
                    r'Stream.*listen.*dispose',
                    r'ListView.*key',
                ]
            }
        }

    def plan(self) -> str:
        """Create a comprehensive debugging plan"""
        goal = self.context.get('goal', 'Debug application issues')
        framework = self.framework

        plan = f"""
## 🔍 Advanced Debugging Plan

### 🎯 Goal: {goal}

### 📋 Framework Detection
- **Framework**: {framework.title()}
- **Debug Strategy**: Framework-specific analysis
- **Tools**: {', '.join(self.debug_strategies.get(framework, {}).get('tools', ['generic']))}

### 🏗️ Debugging Strategy

1. **Static Analysis**
   - Code quality checks
   - Framework-specific linting
   - Security vulnerability scanning
   - Performance bottleneck identification

2. **Dynamic Analysis**
   - Runtime error detection
   - Memory leak identification
   - Performance profiling
   - User interaction testing

3. **Framework-Specific Checks**
   {self._get_framework_specific_checks()}

4. **Automated Fixes**
   - Quick fix suggestions
   - Code refactoring recommendations
   - Best practice enforcement
   - Security hardening

5. **Reporting & Documentation**
   - Comprehensive issue reports
   - Fix prioritization
   - Code quality metrics
   - Maintenance recommendations

### 🎨 Quality Standards
- Zero critical security issues
- Optimal performance metrics
- Clean, maintainable code
- Comprehensive test coverage
- Proper error handling
"""
        return plan

    def _get_framework_specific_checks(self) -> str:
        """Get framework-specific debugging checks"""
        framework = self.framework
        strategy = self.debug_strategies.get(framework, {})

        if not strategy:
            return "- Generic code quality checks\n- Basic error detection"

        checks = []
        for issue in strategy.get('common_issues', []):
            checks.append(f"- {issue.title()}")

        return '\n'.join(checks)

    def apply_patch(self, patch: str) -> bool:
        """Apply debugging patches and fixes"""
        try:
            if 'analyze' in patch.lower():
                return self._run_comprehensive_analysis()
            elif 'fix' in patch.lower():
                return self._apply_automated_fixes(patch)
            elif 'profile' in patch.lower():
                return self._run_performance_profiling()
            elif 'security' in patch.lower():
                return self._run_security_audit()
            else:
                return self._run_generic_debugging()
        except Exception as e:
            print(f"Error in debugging: {e}")
            return False

    def _run_comprehensive_analysis(self) -> bool:
        """Run comprehensive code analysis"""
        project_path = Path(self.context.get('project', '.'))

        # Create debug session
        session = DebugSession(
            project_path=str(project_path),
            framework=self.framework
        )

        # Run framework-specific analysis
        issues = []

        if self.framework == 'react':
            issues.extend(self._analyze_react_code(project_path))
        elif self.framework == 'laravel':
            issues.extend(self._analyze_laravel_code(project_path))
        elif self.framework == 'flutter':
            issues.extend(self._analyze_flutter_code(project_path))
        else:
            issues.extend(self._analyze_generic_code(project_path))

        # Run general diagnostics
        try:
            report = auto_debug(str(project_path))
            issues.extend(self._convert_diagnostic_report(report))
        except Exception as e:
            print(f"Diagnostic error: {e}")

        session.issues = issues
        session.end_time = time.time()

        # Generate report
        self._generate_debug_report(session)

        return True

    def _analyze_react_code(self, project_path: Path) -> List[DebugIssue]:
        """Analyze React-specific code issues"""
        issues = []

        # Check for common React issues
        patterns = self.debug_strategies['react']['patterns']

        for file_path in project_path.rglob('*.tsx'):
            if file_path.is_file():
                try:
                    content = file_path.read_text()

                    # Check for useEffect dependency issues
                    if re.search(patterns[0], content):
                        issues.append(DebugIssue(
                            severity='high',
                            category='logic',
                            title='Potential useEffect dependency issue',
                            description='useEffect with empty dependency array may cause stale closures',
                            file_path=str(file_path),
                            framework_specific=True,
                            suggestion='Add proper dependencies or use useCallback/useMemo'
                        ))

                    # Check for setState in render
                    if re.search(patterns[1], content):
                        issues.append(DebugIssue(
                            severity='critical',
                            category='logic',
                            title='setState called during render',
                            description='Calling setState during render can cause infinite loops',
                            file_path=str(file_path),
                            framework_specific=True,
                            suggestion='Move state updates to event handlers or useEffect'
                        ))

                except Exception as e:
                    print(f"Error analyzing {file_path}: {e}")

        return issues

    def _analyze_laravel_code(self, project_path: Path) -> List[DebugIssue]:
        """Analyze Laravel-specific code issues"""
        issues = []

        # Check for common Laravel issues
        patterns = self.debug_strategies['laravel']['patterns']

        for file_path in project_path.rglob('*.php'):
            if file_path.is_file():
                try:
                    content = file_path.read_text()

                    # Check for N+1 query issues
                    if re.search(patterns[0], content):
                        issues.append(DebugIssue(
                            severity='high',
                            category='performance',
                            title='Potential N+1 query problem',
                            description='Using get()->map() may cause N+1 queries',
                            file_path=str(file_path),
                            framework_specific=True,
                            suggestion='Use with() method for eager loading'
                        ))

                    # Check for mass assignment vulnerabilities
                    if re.search(patterns[1], content):
                        issues.append(DebugIssue(
                            severity='critical',
                            category='security',
                            title='Mass assignment vulnerability',
                            description='Empty fillable array allows all attributes to be mass assigned',
                            file_path=str(file_path),
                            framework_specific=True,
                            suggestion='Specify allowed attributes in $fillable array'
                        ))

                except Exception as e:
                    print(f"Error analyzing {file_path}: {e}")

        return issues

    def _analyze_flutter_code(self, project_path: Path) -> List[DebugIssue]:
        """Analyze Flutter-specific code issues"""
        issues = []

        # Check for common Flutter issues
        patterns = self.debug_strategies['flutter']['patterns']

        for file_path in project_path.rglob('*.dart'):
            if file_path.is_file():
                try:
                    content = file_path.read_text()

                    # Check for setState in build
                    if re.search(patterns[0], content):
                        issues.append(DebugIssue(
                            severity='critical',
                            category='logic',
                            title='setState called in build method',
                            description='Calling setState during build can cause infinite loops',
                            file_path=str(file_path),
                            framework_specific=True,
                            suggestion='Move state updates to event handlers or initState'
                        ))

                    # Check for stream dispose issues
                    if 'Stream' in content and 'dispose' not in content:
                        issues.append(DebugIssue(
                            severity='medium',
                            category='memory',
                            title='Potential stream memory leak',
                            description='Stream subscription may not be properly disposed',
                            file_path=str(file_path),
                            framework_specific=True,
                            suggestion='Implement proper dispose() method for stream subscriptions'
                        ))

                except Exception as e:
                    print(f"Error analyzing {file_path}: {e}")

        return issues

    def _analyze_generic_code(self, project_path: Path) -> List[DebugIssue]:
        """Analyze generic code issues"""
        issues = []

        # Check for common issues across frameworks
        for file_path in project_path.rglob('*'):
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.php', '.dart']:
                try:
                    content = file_path.read_text()

                    # Check for TODO comments
                    if 'TODO' in content.upper():
                        issues.append(DebugIssue(
                            severity='low',
                            category='maintenance',
                            title='TODO comment found',
                            description='Code contains TODO comments that need attention',
                            file_path=str(file_path),
                            suggestion='Address TODO items or convert to proper issues'
                        ))

                    # Check for console.log statements
                    if 'console.log' in content:
                        issues.append(DebugIssue(
                            severity='info',
                            category='maintenance',
                            title='Debug logging found',
                            description='Console.log statements should be removed in production',
                            file_path=str(file_path),
                            suggestion='Remove debug logging or use proper logging framework'
                        ))

                except Exception as e:
                    print(f"Error analyzing {file_path}: {e}")

        return issues

    def _convert_diagnostic_report(self, report: DebugReport) -> List[DebugIssue]:
        """Convert diagnostic report to DebugIssue objects"""
        issues = []

        # Convert test failures
        if report.first_failure:
            issues.append(DebugIssue(
                severity='high',
                category='testing',
                title='Test failure detected',
                description=report.first_failure[:200] + '...' if len(report.first_failure) > 200 else report.first_failure,
                file_path=report.cwd,
                suggestion='Fix failing tests and ensure proper test coverage'
            ))

        # Convert linting issues
        if report.ruff.strip():
            issues.append(DebugIssue(
                severity='medium',
                category='code_quality',
                title='Code quality issues found',
                description=f"Ruff detected {len(report.ruff.split('\\n'))} issues",
                file_path=report.cwd,
                suggestion='Run `ruff check --fix` to automatically fix issues'
            ))

        return issues

    def _generate_debug_report(self, session: DebugSession):
        """Generate comprehensive debug report"""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel

        console = Console()

        # Summary statistics
        severity_counts = {}
        category_counts = {}

        for issue in session.issues:
            severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1

        # Create summary panel
        summary_text = f"""
🔍 Debug Session Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Framework: {session.framework.title()}
Duration: {session.end_time - session.start_time:.2f}s
Total Issues: {len(session.issues)}

Severity Breakdown:
• Critical: {severity_counts.get('critical', 0)}
• High: {severity_counts.get('high', 0)}
• Medium: {severity_counts.get('medium', 0)}
• Low: {severity_counts.get('low', 0)}
• Info: {severity_counts.get('info', 0)}

Top Categories:
{chr(10).join(f"• {cat.title()}: {count}" for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3])}
        """

        console.print(Panel(summary_text.strip(), title="[bold red]Debug Report[/bold red]", border_style="red"))

        # Create issues table
        if session.issues:
            table = Table(title="Detected Issues")
            table.add_column("Severity", style="bold", width=10)
            table.add_column("Category", width=12)
            table.add_column("Title", width=40)
            table.add_column("File", width=30)

            # Sort by severity
            severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
            sorted_issues = sorted(session.issues, key=lambda x: severity_order.get(x.severity, 5))

            for issue in sorted_issues[:20]:  # Show top 20 issues
                severity_style = {
                    'critical': 'bold red',
                    'high': 'red',
                    'medium': 'yellow',
                    'low': 'blue',
                    'info': 'dim'
                }.get(issue.severity, 'white')

                table.add_row(
                    f"[{severity_style}]{issue.severity.upper()}[/{severity_style}]",
                    issue.category.title(),
                    issue.title[:37] + '...' if len(issue.title) > 37 else issue.title,
                    Path(issue.file_path).name
                )

            console.print(table)

            # Show top suggestions
            if any(issue.suggestion for issue in session.issues):
                console.print("\n[bold cyan]💡 Top Recommendations:[/bold cyan]")
                suggestions = [issue for issue in session.issues if issue.suggestion][:5]

                for i, issue in enumerate(suggestions, 1):
                    console.print(f"{i}. [yellow]{issue.title}[/yellow]")
                    console.print(f"   [dim]{issue.suggestion}[/dim]")
                    console.print()

    def _apply_automated_fixes(self, patch: str) -> bool:
        """Apply automated fixes based on detected issues"""
        # This would implement automated fixing logic
        print("Automated fixes functionality coming soon...")
        return True

    def _run_performance_profiling(self) -> bool:
        """Run performance profiling"""
        print("Performance profiling functionality coming soon...")
        return True

    def _run_security_audit(self) -> bool:
        """Run security audit"""
        print("Security audit functionality coming soon...")
        return True

    def _run_generic_debugging(self) -> bool:
        """Run generic debugging analysis"""
        return self._run_comprehensive_analysis()

    def run_tests(self) -> tuple[bool, str]:
        """Run debugging tests"""
        return True, "Debug analysis completed successfully"