"""
Advanced Debugging Tools and Vulnerability Assessment for Sanaa
Provides comprehensive debugging capabilities with security analysis
"""
from __future__ import annotations

import asyncio
import json
import time
import traceback
import inspect
from typing import Dict, List, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import re
import ast
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
import logging


class DebugLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DebugCategory(Enum):
    PERFORMANCE = "performance"
    SECURITY = "security"
    LOGIC = "logic"
    MEMORY = "memory"
    CONCURRENCY = "concurrency"
    NETWORK = "network"


@dataclass
class DebugEvent:
    """Represents a debug event"""
    id: str
    timestamp: datetime
    level: DebugLevel
    category: DebugCategory
    message: str
    source: str
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    thread_id: Optional[int] = None
    process_id: Optional[int] = None
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class PerformanceProfile:
    """Performance profiling data"""
    function_name: str
    call_count: int
    total_time: float
    average_time: float
    max_time: float
    min_time: float
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None


@dataclass
class MemorySnapshot:
    """Memory usage snapshot"""
    timestamp: datetime
    total_memory: float
    available_memory: float
    used_memory: float
    memory_usage_percent: float
    top_consumers: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SecurityIssue:
    """Security vulnerability or issue"""
    id: str
    severity: str
    category: str
    title: str
    description: str
    file_path: str
    line_number: Optional[int]
    cwe_id: Optional[str]
    owasp_id: Optional[str]
    recommendation: str
    evidence: str
    confidence: float
    discovered_at: datetime
    status: str = "open"  # open, fixed, false_positive


class AdvancedDebugger:
    """Advanced debugging system with multiple analysis tools"""

    def __init__(self):
        self.debug_events: List[DebugEvent] = []
        self.performance_profiles: Dict[str, PerformanceProfile] = {}
        self.memory_snapshots: List[MemorySnapshot] = []
        self.security_issues: List[SecurityIssue] = []
        self.breakpoints: Dict[str, List[int]] = {}
        self.watch_variables: Dict[str, Any] = {}
        self.active_traces: Set[str] = set()

        # Initialize analysis tools
        self.performance_analyzer = PerformanceAnalyzer()
        self.memory_analyzer = MemoryAnalyzer()
        self.security_scanner = SecurityScanner()
        self.concurrency_analyzer = ConcurrencyAnalyzer()

        # Set up logging
        self.logger = logging.getLogger('sanaa_debugger')
        self.logger.setLevel(logging.DEBUG)

    def start_debugging(self, target_module: str = None):
        """Start comprehensive debugging session"""
        self._setup_debug_hooks()
        self._start_performance_monitoring()
        self._start_memory_monitoring()

        if target_module:
            self._instrument_module(target_module)

    def stop_debugging(self):
        """Stop debugging session and generate report"""
        self._remove_debug_hooks()
        self._stop_performance_monitoring()
        self._stop_memory_monitoring()

        return self.generate_debug_report()

    def add_breakpoint(self, file_path: str, line_number: int, condition: str = None):
        """Add a breakpoint"""
        if file_path not in self.breakpoints:
            self.breakpoints[file_path] = []

        self.breakpoints[file_path].append({
            'line': line_number,
            'condition': condition,
            'enabled': True
        })

    def remove_breakpoint(self, file_path: str, line_number: int):
        """Remove a breakpoint"""
        if file_path in self.breakpoints:
            self.breakpoints[file_path] = [
                bp for bp in self.breakpoints[file_path]
                if bp['line'] != line_number
            ]

    def watch_variable(self, variable_name: str, scope: str = 'global'):
        """Watch a variable for changes"""
        self.watch_variables[variable_name] = {
            'scope': scope,
            'last_value': None,
            'change_count': 0,
            'changes': []
        }

    def log_event(self, level: DebugLevel, category: DebugCategory, message: str,
                  source: str = None, context: Dict[str, Any] = None):
        """Log a debug event"""
        event = DebugEvent(
            id=f"evt_{int(time.time() * 1000000)}",
            timestamp=datetime.utcnow(),
            level=level,
            category=category,
            message=message,
            source=source or "unknown",
            context=context or {},
            thread_id=threading.get_ident()
        )

        self.debug_events.append(event)

        # Keep only recent events
        if len(self.debug_events) > 10000:
            self.debug_events = self.debug_events[-5000:]

    def analyze_performance(self, function_name: str = None) -> Dict[str, Any]:
        """Analyze performance bottlenecks"""
        return self.performance_analyzer.analyze(function_name)

    def analyze_memory(self) -> Dict[str, Any]:
        """Analyze memory usage patterns"""
        return self.memory_analyzer.analyze()

    def scan_security(self, codebase_path: str) -> List[SecurityIssue]:
        """Scan codebase for security vulnerabilities"""
        return self.security_scanner.scan(codebase_path)

    def analyze_concurrency(self) -> Dict[str, Any]:
        """Analyze concurrency issues"""
        return self.concurrency_analyzer.analyze()

    def generate_debug_report(self) -> Dict[str, Any]:
        """Generate comprehensive debug report"""
        return {
            'timestamp': datetime.utcnow(),
            'summary': self._generate_summary(),
            'performance_analysis': self.analyze_performance(),
            'memory_analysis': self.analyze_memory(),
            'security_issues': [self._security_issue_to_dict(issue) for issue in self.security_issues],
            'concurrency_analysis': self.analyze_concurrency(),
            'recent_events': [self._event_to_dict(event) for event in self.debug_events[-100:]],
            'recommendations': self._generate_recommendations()
        }

    def _setup_debug_hooks(self):
        """Set up debugging hooks"""
        # Set up system-wide exception hook
        sys.excepthook = self._exception_hook

        # Set up thread exception hook
        threading.excepthook = self._thread_exception_hook

    def _remove_debug_hooks(self):
        """Remove debugging hooks"""
        sys.excepthook = sys.__excepthook__
        threading.excepthook = threading.__excepthook__

    def _exception_hook(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions"""
        stack_trace = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))

        self.log_event(
            DebugLevel.CRITICAL,
            DebugCategory.LOGIC,
            f"Uncaught exception: {exc_value}",
            context={
                'exception_type': exc_type.__name__,
                'exception_value': str(exc_value),
                'stack_trace': stack_trace
            }
        )

        # Call original exception hook
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    def _thread_exception_hook(self, args):
        """Handle thread exceptions"""
        self.log_event(
            DebugLevel.ERROR,
            DebugCategory.CONCURRENCY,
            f"Thread exception: {args.exc_value}",
            context={
                'thread_id': args.thread.ident,
                'exception_type': args.exc_type.__name__,
                'exception_value': str(args.exc_value)
            }
        )

        # Call original thread exception hook
        threading.__excepthook__(args)

    def _start_performance_monitoring(self):
        """Start performance monitoring"""
        self.performance_analyzer.start_monitoring()

    def _stop_performance_monitoring(self):
        """Stop performance monitoring"""
        self.performance_analyzer.stop_monitoring()

    def _start_memory_monitoring(self):
        """Start memory monitoring"""
        self.memory_analyzer.start_monitoring()

    def _stop_memory_monitoring(self):
        """Stop memory monitoring"""
        self.memory_analyzer.stop_monitoring()

    def _instrument_module(self, module_name: str):
        """Instrument a module for detailed debugging"""
        try:
            module = __import__(module_name)

            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) or inspect.ismethod(obj):
                    self._instrument_function(obj)

        except ImportError:
            self.log_event(
                DebugLevel.WARNING,
                DebugCategory.LOGIC,
                f"Could not instrument module {module_name}",
                context={'module': module_name}
            )

    def _instrument_function(self, func):
        """Instrument a function for performance monitoring"""
        self.performance_analyzer.instrument_function(func)

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate debug session summary"""
        total_events = len(self.debug_events)
        events_by_level = {}
        events_by_category = {}

        for event in self.debug_events:
            level = event.level.value
            category = event.category.value

            events_by_level[level] = events_by_level.get(level, 0) + 1
            events_by_category[category] = events_by_category.get(category, 0) + 1

        return {
            'total_events': total_events,
            'events_by_level': events_by_level,
            'events_by_category': events_by_category,
            'security_issues_count': len(self.security_issues),
            'performance_profiles_count': len(self.performance_profiles),
            'memory_snapshots_count': len(self.memory_snapshots),
            'session_duration': self._calculate_session_duration()
        }

    def _calculate_session_duration(self) -> float:
        """Calculate debugging session duration"""
        if not self.debug_events:
            return 0.0

        start_time = min(event.timestamp for event in self.debug_events)
        end_time = max(event.timestamp for event in self.debug_events)

        return (end_time - start_time).total_seconds()

    def _generate_recommendations(self) -> List[str]:
        """Generate debugging recommendations"""
        recommendations = []

        # Analyze event patterns
        error_count = sum(1 for event in self.debug_events if event.level == DebugLevel.ERROR)
        if error_count > 10:
            recommendations.append("High error rate detected - consider reviewing error handling")

        # Analyze performance
        perf_analysis = self.analyze_performance()
        if perf_analysis.get('bottlenecks'):
            recommendations.append("Performance bottlenecks identified - review optimization opportunities")

        # Analyze security
        if self.security_issues:
            high_severity = [issue for issue in self.security_issues if issue.severity == 'high']
            if high_severity:
                recommendations.append(f"{len(high_severity)} high-severity security issues found - prioritize fixes")

        # Analyze memory
        memory_analysis = self.analyze_memory()
        if memory_analysis.get('memory_leaks_detected', False):
            recommendations.append("Potential memory leaks detected - review memory management")

        return recommendations

    def _event_to_dict(self, event: DebugEvent) -> Dict[str, Any]:
        """Convert debug event to dictionary"""
        return {
            'id': event.id,
            'timestamp': event.timestamp.isoformat(),
            'level': event.level.value,
            'category': event.category.value,
            'message': event.message,
            'source': event.source,
            'line_number': event.line_number,
            'function_name': event.function_name,
            'thread_id': event.thread_id,
            'context': event.context,
            'tags': event.tags
        }

    def _security_issue_to_dict(self, issue: SecurityIssue) -> Dict[str, Any]:
        """Convert security issue to dictionary"""
        return {
            'id': issue.id,
            'severity': issue.severity,
            'category': issue.category,
            'title': issue.title,
            'description': issue.description,
            'file_path': issue.file_path,
            'line_number': issue.line_number,
            'cwe_id': issue.cwe_id,
            'recommendation': issue.recommendation,
            'confidence': issue.confidence,
            'status': issue.status
        }


class PerformanceAnalyzer:
    """Performance analysis and profiling"""

    def __init__(self):
        self.function_calls: Dict[str, List[float]] = {}
        self.instrumented_functions: Dict[str, Callable] = {}
        self.monitoring_active = False

    def start_monitoring(self):
        """Start performance monitoring"""
        self.monitoring_active = True

    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False

    def instrument_function(self, func: Callable):
        """Instrument a function for performance monitoring"""
        func_name = f"{func.__module__}.{func.__name__}"

        def wrapper(*args, **kwargs):
            if not self.monitoring_active:
                return func(*args, **kwargs)

            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                duration = end_time - start_time
                self._record_call(func_name, duration)

        self.instrumented_functions[func_name] = wrapper
        # Replace the original function
        # Note: This is a simplified version - in practice, you'd need more sophisticated instrumentation

    def _record_call(self, func_name: str, duration: float):
        """Record function call duration"""
        if func_name not in self.function_calls:
            self.function_calls[func_name] = []

        self.function_calls[func_name].append(duration)

        # Keep only recent calls
        if len(self.function_calls[func_name]) > 1000:
            self.function_calls[func_name] = self.function_calls[func_name][-500:]

    def analyze(self, function_name: str = None) -> Dict[str, Any]:
        """Analyze performance data"""
        if function_name:
            return self._analyze_function(function_name)

        # Analyze all functions
        analysis = {}
        for func_name in self.function_calls:
            analysis[func_name] = self._analyze_function(func_name)

        # Find bottlenecks
        bottlenecks = []
        for func_name, func_analysis in analysis.items():
            if func_analysis['average_time'] > 1.0:  # More than 1 second
                bottlenecks.append({
                    'function': func_name,
                    'average_time': func_analysis['average_time'],
                    'call_count': func_analysis['call_count']
                })

        return {
            'function_analysis': analysis,
            'bottlenecks': sorted(bottlenecks, key=lambda x: x['average_time'], reverse=True)[:10],
            'total_functions': len(analysis)
        }

    def _analyze_function(self, func_name: str) -> Dict[str, Any]:
        """Analyze a specific function"""
        if func_name not in self.function_calls:
            return {'error': 'Function not found'}

        calls = self.function_calls[func_name]
        if not calls:
            return {'error': 'No call data'}

        return {
            'call_count': len(calls),
            'total_time': sum(calls),
            'average_time': statistics.mean(calls),
            'max_time': max(calls),
            'min_time': min(calls),
            'percentiles': {
                '95': sorted(calls)[int(len(calls) * 0.95)],
                '99': sorted(calls)[int(len(calls) * 0.99)]
            }
        }


class MemoryAnalyzer:
    """Memory usage analysis and leak detection"""

    def __init__(self):
        self.snapshots: List[MemorySnapshot] = []
        self.monitoring_active = False
        self.snapshot_interval = 60  # seconds

    def start_monitoring(self):
        """Start memory monitoring"""
        self.monitoring_active = True
        # In a real implementation, you'd set up periodic snapshots

    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.monitoring_active = False

    def take_snapshot(self):
        """Take a memory usage snapshot"""
        try:
            import psutil
            process = psutil.Process()

            snapshot = MemorySnapshot(
                timestamp=datetime.utcnow(),
                total_memory=psutil.virtual_memory().total / 1024 / 1024,  # MB
                available_memory=psutil.virtual_memory().available / 1024 / 1024,  # MB
                used_memory=psutil.virtual_memory().used / 1024 / 1024,  # MB
                memory_usage_percent=psutil.virtual_memory().percent,
                top_consumers=[]  # Would need more sophisticated tracking
            )

            self.snapshots.append(snapshot)

            # Keep only recent snapshots
            if len(self.snapshots) > 100:
                self.snapshots = self.snapshots[-50:]

        except ImportError:
            # psutil not available
            pass

    def analyze(self) -> Dict[str, Any]:
        """Analyze memory usage patterns"""
        if not self.snapshots:
            return {'error': 'No memory snapshots available'}

        # Analyze memory trends
        memory_usage = [s.memory_usage_percent for s in self.snapshots]
        timestamps = [s.timestamp for s in self.snapshots]

        analysis = {
            'current_memory_usage': memory_usage[-1] if memory_usage else 0,
            'average_memory_usage': statistics.mean(memory_usage) if memory_usage else 0,
            'max_memory_usage': max(memory_usage) if memory_usage else 0,
            'memory_trend': self._calculate_trend(memory_usage),
            'snapshot_count': len(self.snapshots),
            'memory_leaks_detected': self._detect_memory_leaks()
        }

        return analysis

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate memory usage trend"""
        if len(values) < 2:
            return 'stable'

        # Simple linear regression
        n = len(values)
        x = list(range(n))
        slope = statistics.linear_regression(x, values)[0]

        if slope > 0.1:
            return 'increasing'
        elif slope < -0.1:
            return 'decreasing'
        else:
            return 'stable'

    def _detect_memory_leaks(self) -> bool:
        """Detect potential memory leaks"""
        if len(self.snapshots) < 10:
            return False

        # Check if memory usage is consistently increasing
        recent_snapshots = self.snapshots[-10:]
        memory_values = [s.memory_usage_percent for s in recent_snapshots]

        # Simple heuristic: if memory is increasing in 7 out of 10 recent snapshots
        increasing_count = sum(1 for i in range(1, len(memory_values))
                              if memory_values[i] > memory_values[i-1])

        return increasing_count >= 7


class SecurityScanner:
    """Advanced security vulnerability scanner"""

    def __init__(self):
        self.vulnerability_patterns = self._load_patterns()
        self.cwe_database = self._load_cwe_database()

    def _load_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load security vulnerability patterns"""
        return {
            'sql_injection': {
                'pattern': r'(?i)(select|insert|update|delete).*\$\{.*\}|.*\+.*\.sql',
                'severity': 'high',
                'category': 'injection',
                'cwe_id': 'CWE-89',
                'description': 'Potential SQL injection vulnerability'
            },
            'xss_vulnerable': {
                'pattern': r'innerHTML\s*[=]\s*.*\+.*|document\.write\s*\(.*\+.*\)',
                'severity': 'high',
                'category': 'xss',
                'cwe_id': 'CWE-79',
                'description': 'Potential Cross-Site Scripting (XSS) vulnerability'
            },
            'hardcoded_secrets': {
                'pattern': r'(?i)(password|secret|key|token)\s*[=:]\s*["\'][^"\']+["\']',
                'severity': 'medium',
                'category': 'credentials',
                'cwe_id': 'CWE-798',
                'description': 'Hardcoded credentials detected'
            },
            'command_injection': {
                'pattern': r'(?i)(exec|eval|system|shell_exec)\s*\(\s*.*\+.*\)',
                'severity': 'critical',
                'category': 'injection',
                'cwe_id': 'CWE-78',
                'description': 'Potential command injection vulnerability'
            },
            'path_traversal': {
                'pattern': r'\.\./|\.\.\\',
                'severity': 'high',
                'category': 'path_traversal',
                'cwe_id': 'CWE-22',
                'description': 'Potential path traversal vulnerability'
            }
        }

    def _load_cwe_database(self) -> Dict[str, Dict[str, Any]]:
        """Load CWE database (simplified)"""
        return {
            'CWE-79': {'name': 'Cross-site Scripting', 'impact': 'high'},
            'CWE-89': {'name': 'SQL Injection', 'impact': 'critical'},
            'CWE-78': {'name': 'OS Command Injection', 'impact': 'critical'},
            'CWE-22': {'name': 'Path Traversal', 'impact': 'high'},
            'CWE-798': {'name': 'Use of Hard-coded Credentials', 'impact': 'medium'}
        }

    def scan(self, codebase_path: str) -> List[SecurityIssue]:
        """Scan codebase for security vulnerabilities"""
        issues = []
        codebase_path = Path(codebase_path)

        # Scan all relevant files
        for file_path in codebase_path.rglob('*'):
            if file_path.is_file() and self._is_relevant_file(file_path):
                try:
                    content = file_path.read_text()
                    file_issues = self._scan_file(content, str(file_path))
                    issues.extend(file_issues)
                except Exception as e:
                    print(f"Error scanning {file_path}: {e}")

        return issues

    def _is_relevant_file(self, file_path: Path) -> bool:
        """Check if file should be scanned"""
        relevant_extensions = ['.py', '.js', '.ts', '.php', '.java', '.cpp', '.c', '.go', '.rs', '.html']
        return file_path.suffix in relevant_extensions

    def _scan_file(self, content: str, file_path: str) -> List[SecurityIssue]:
        """Scan individual file for security issues"""
        issues = []
        lines = content.split('\n')

        for pattern_name, pattern_config in self.vulnerability_patterns.items():
            matches = re.finditer(pattern_config['pattern'], content)

            for match in matches:
                line_number = content[:match.start()].count('\n') + 1

                # Calculate confidence based on context
                confidence = self._calculate_confidence(match.group(), pattern_config, lines[line_number-1] if line_number <= len(lines) else "")

                issue = SecurityIssue(
                    id=f"sec_{pattern_name}_{file_path}_{line_number}_{int(time.time())}",
                    severity=pattern_config['severity'],
                    category=pattern_config['category'],
                    title=pattern_config['description'],
                    description=f"Found {pattern_name} pattern at line {line_number}",
                    file_path=file_path,
                    line_number=line_number,
                    cwe_id=pattern_config['cwe_id'],
                    recommendation=self._get_recommendation(pattern_name),
                    evidence=match.group(),
                    confidence=confidence,
                    discovered_at=datetime.utcnow()
                )

                issues.append(issue)

        return issues

    def _calculate_confidence(self, match: str, pattern_config: Dict[str, Any], line_context: str) -> float:
        """Calculate confidence score for vulnerability detection"""
        confidence = 0.7  # Base confidence

        # Increase confidence based on context
        if 'password' in line_context.lower() or 'secret' in line_context.lower():
            confidence += 0.2

        # Decrease confidence for false positives
        if 'example' in line_context.lower() or 'test' in line_context.lower():
            confidence -= 0.3

        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))

    def _get_recommendation(self, pattern_name: str) -> str:
        """Get security recommendation for vulnerability type"""
        recommendations = {
            'sql_injection': 'Use parameterized queries or prepared statements. Validate and sanitize all user inputs.',
            'xss_vulnerable': 'Use textContent instead of innerHTML. Sanitize user inputs and use Content Security Policy (CSP).',
            'hardcoded_secrets': 'Move credentials to environment variables or secure key management systems.',
            'command_injection': 'Avoid executing user-controlled commands. Use safe APIs and validate inputs.',
            'path_traversal': 'Validate and sanitize file paths. Use allowlists for permitted paths.'
        }

        return recommendations.get(pattern_name, 'Review and fix the security issue')


class ConcurrencyAnalyzer:
    """Concurrency and threading analysis"""

    def __init__(self):
        self.thread_events: List[Dict[str, Any]] = []
        self.lock_usage: Dict[str, List[Dict[str, Any]]] = {}
        self.race_conditions: List[Dict[str, Any]] = []

    def analyze(self) -> Dict[str, Any]:
        """Analyze concurrency patterns and issues"""
        return {
            'thread_count': threading.active_count(),
            'active_threads': [t.name for t in threading.enumerate()],
            'potential_race_conditions': len(self.race_conditions),
            'lock_usage_analysis': self._analyze_lock_usage(),
            'deadlock_detection': self._detect_deadlocks(),
            'recommendations': self._generate_concurrency_recommendations()
        }

    def _analyze_lock_usage(self) -> Dict[str, Any]:
        """Analyze lock usage patterns"""
        return {
            'total_locks': len(self.lock_usage),
            'lock_contention': 'low',  # Would need actual lock monitoring
            'recommendations': []
        }

    def _detect_deadlocks(self) -> bool:
        """Detect potential deadlocks"""
        # Simplified deadlock detection
        # In practice, this would be much more sophisticated
        return False

    def _generate_concurrency_recommendations(self) -> List[str]:
        """Generate concurrency-related recommendations"""
        recommendations = []

        if threading.active_count() > 10:
            recommendations.append("High thread count detected - consider using thread pools")

        if self.race_conditions:
            recommendations.append("Potential race conditions detected - review shared state access")

        return recommendations


# Global advanced debugger instance
advanced_debugger = AdvancedDebugger()


def get_advanced_debugger() -> AdvancedDebugger:
    """Get global advanced debugger instance"""
    return advanced_debugger