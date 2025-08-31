# Smart Completion & Suggestions System
# packages/cli/src/coding_swarm_cli/completion.py

from __future__ import annotations

import ast
import json
import os
import re
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any, Callable, Generator
from functools import lru_cache

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.prompt import Prompt

from coding_swarm_core.projects import Project, ProjectRegistry

# -------------------------
# Smart Suggestion Models
# -------------------------

@dataclass
class Suggestion:
    """A smart suggestion with context"""
    type: str  # 'command', 'file', 'function', 'variable', 'pattern'
    text: str
    description: str
    confidence: float  # 0.0 - 1.0
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher priority = shown first
    category: Optional[str] = None
    usage_count: int = 0
    last_used: float = 0.0

@dataclass
class CompletionContext:
    """Context for generating completions"""
    current_input: str
    cursor_position: int
    project: Optional[Project] = None
    file_context: Optional[str] = None
    recent_commands: List[str] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)

# -------------------------
# Smart Completion Engine
# -------------------------

class SmartCompletionEngine:
    """Advanced completion engine with learning capabilities"""
    
    def __init__(self):
        self.console = Console()
        self.cache_dir = Path.home() / ".sanaa" / "completion_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Learning data
        self.usage_stats = self._load_usage_stats()
        self.user_patterns = self._load_user_patterns()
        self.command_history = self._load_command_history()
        
        # Built-in completions
        self.builtin_commands = {
            'sanaa': self._get_sanaa_completions(),
            'git': self._get_git_completions(),
            'python': self._get_python_completions(),
            'npm': self._get_npm_completions(),
        }
        
        # Completion providers
        self.providers: List[Callable[[CompletionContext], List[Suggestion]]] = [
            self._command_completions,
            self._file_completions, 
            self._project_completions,
            self._context_aware_completions,
            self._pattern_completions,
            self._ai_suggested_completions
        ]
    
    def get_completions(self, context: CompletionContext) -> List[Suggestion]:
        """Get smart completions for current context"""
        
        all_suggestions = []
        
        # Run all completion providers
        for provider in self.providers:
            try:
                suggestions = provider(context)
                all_suggestions.extend(suggestions)
            except Exception as e:
                # Graceful degradation - log but continue
                pass
        
        # Deduplicate and rank
        suggestions = self._rank_and_filter_suggestions(all_suggestions, context)
        
        # Learn from this interaction
        self._update_learning_data(context, suggestions)
        
        return suggestions[:20]  # Limit to top 20 suggestions
    
    def _command_completions(self, context: CompletionContext) -> List[Suggestion]:
        """Generate command completions"""
        
        suggestions = []
        input_lower = context.current_input.lower()
        
        # Sanaa commands
        sanaa_commands = [
            ('chat', 'Start interactive chat', 0.9),
            ('projects create', 'Create new project', 0.8),
            ('projects list', 'List all projects', 0.7),
            ('debug health', 'Run health check', 0.6),
            ('status', 'Show system status', 0.8),
            ('config', 'Configure settings', 0.5)
        ]
        
        for cmd, desc, base_confidence in sanaa_commands:
            if cmd.startswith(input_lower) or input_lower in cmd:
                # Boost confidence based on usage history
                usage_boost = self.usage_stats.get(cmd, {}).get('count', 0) * 0.1
                confidence = min(1.0, base_confidence + usage_boost)
                
                suggestions.append(Suggestion(
                    type='command',
                    text=cmd,
                    description=desc,
                    confidence=confidence,
                    category='sanaa'
                ))
        
        return suggestions
    
    def _file_completions(self, context: CompletionContext) -> List[Suggestion]:
        """Generate file and path completions"""
        
        suggestions = []
        
        if not context.project:
            return suggestions
        
        project_path = Path(context.project.path)
        input_text = context.current_input
        
        # Extract potential file path from input
        file_pattern = self._extract_file_pattern(input_text)
        if not file_pattern:
            return suggestions
        
        # Find matching files
        try:
            for file_entry in context.project.files:
                file_path = file_entry.path
                
                if file_pattern.lower() in file_path.lower():
                    # Calculate relevance score
                    relevance = self._calculate_file_relevance(
                        file_path, file_pattern, context
                    )
                    
                    suggestions.append(Suggestion(
                        type='file',
                        text=file_path,
                        description=f"Project file ({file_entry.size} bytes)",
                        confidence=relevance,
                        context={'size': file_entry.size, 'mtime': file_entry.mtime},
                        category='files'
                    ))
        
        except Exception:
            pass
        
        return suggestions
    
    def _project_completions(self, context: CompletionContext) -> List[Suggestion]:
        """Generate project-related completions"""
        
        suggestions = []
        
        try:
            registry = ProjectRegistry.load()
            projects = registry.list()
            
            input_lower = context.current_input.lower()
            
            for project in projects:
                if project.name.lower().startswith(input_lower) or input_lower in project.name.lower():
                    # Boost confidence for recently used projects
                    recency_boost = 0.0
                    if project.updated_at:
                        days_ago = (time.time() - project.updated_at) / (24 * 3600)
                        recency_boost = max(0, 0.3 * (1 - days_ago / 30))  # Boost for recent activity
                    
                    confidence = min(1.0, 0.7 + recency_boost)
                    
                    suggestions.append(Suggestion(
                        type='project',
                        text=project.name,
                        description=f"Project ({len(project.files)} files)",
                        confidence=confidence,
                        context={'path': project.path, 'file_count': len(project.files)},
                        category='projects'
                    ))
        
        except Exception:
            pass
        
        return suggestions
    
    def _context_aware_completions(self, context: CompletionContext) -> List[Suggestion]:
        """Generate context-aware completions based on current project"""
        
        suggestions = []
        
        if not context.project:
            return suggestions
        
        # Analyze project type and suggest relevant actions
        project_type = self._detect_project_type(context.project)
        
        type_specific_suggestions = {
            'python': [
                ('pytest', 'Run Python tests', 0.8),
                ('pip install -r requirements.txt', 'Install dependencies', 0.7),
                ('python -m venv .venv', 'Create virtual environment', 0.6),
                ('black .', 'Format code with Black', 0.5),
                ('ruff check .', 'Run linting with Ruff', 0.5)
            ],
            'javascript': [
                ('npm test', 'Run JavaScript tests', 0.8),
                ('npm install', 'Install dependencies', 0.7),
                ('npm run dev', 'Start development server', 0.6),
                ('npm run build', 'Build for production', 0.5)
            ],
            'react': [
                ('npm start', 'Start React development server', 0.8),
                ('npm run build', 'Build React app', 0.7),
                ('npm test', 'Run React tests', 0.6)
            ]
        }
        
        if project_type in type_specific_suggestions:
            for cmd, desc, confidence in type_specific_suggestions[project_type]:
                suggestions.append(Suggestion(
                    type='command',
                    text=cmd,
                    description=desc,
                    confidence=confidence,
                    category=f'{project_type}_tools'
                ))
        
        return suggestions
    
    def _pattern_completions(self, context: CompletionContext) -> List[Suggestion]:
        """Generate completions based on learned user patterns"""
        
        suggestions = []
        
        # Common command sequences
        input_words = context.current_input.split()
        if len(input_words) >= 2:
            pattern_key = ' '.join(input_words[:-1])  # All words except last
            
            if pattern_key in self.user_patterns:
                for next_word, frequency in self.user_patterns[pattern_key].items():
                    confidence = min(0.9, frequency / 10.0)  # Scale frequency to confidence
                    
                    suggestions.append(Suggestion(
                        type='pattern',
                        text=f"{context.current_input} {next_word}",
                        description=f"Common continuation (used {frequency} times)",
                        confidence=confidence,
                        category='patterns'
                    ))
        
        return suggestions
    
    def _ai_suggested_completions(self, context: CompletionContext) -> List[Suggestion]:
        """Generate AI-powered smart suggestions"""
        
        suggestions = []
        
        # Smart suggestions based on project state and common workflows
        if context.project:
            project_path = Path(context.project.path)
            
            # Suggest git operations if it's a git repo
            if (project_path / '.git').exists():
                git_suggestions = self._get_git_workflow_suggestions(project_path)
                suggestions.extend(git_suggestions)
            
            # Suggest development workflow steps
            workflow_suggestions = self._get_workflow_suggestions(context)
            suggestions.extend(workflow_suggestions)
            
            # Suggest based on recent file activity
            recent_suggestions = self._get_recent_activity_suggestions(context)
            suggestions.extend(recent_suggestions)
        
        return suggestions
    
    def _get_git_workflow_suggestions(self, project_path: Path) -> List[Suggestion]:
        """Generate git workflow suggestions"""
        
        suggestions = []
        
        try:
            # Check git status
            import subprocess
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                status_lines = result.stdout.strip().split('\n')
                
                if status_lines and status_lines[0]:
                    # Has uncommitted changes
                    suggestions.append(Suggestion(
                        type='command',
                        text='git add -A && git commit -m "Update"',
                        description='Commit all changes',
                        confidence=0.8,
                        category='git'
                    ))
                    
                    suggestions.append(Suggestion(
                        type='command',
                        text='git diff',
                        description='Review changes before commit',
                        confidence=0.7,
                        category='git'
                    ))
                else:
                    # Clean working directory
                    suggestions.append(Suggestion(
                        type='command',
                        text='git pull',
                        description='Pull latest changes',
                        confidence=0.6,
                        category='git'
                    ))
        
        except Exception:
            pass
        
        return suggestions
    
    def _get_workflow_suggestions(self, context: CompletionContext) -> List[Suggestion]:
        """Generate development workflow suggestions"""
        
        suggestions = []
        
        if not context.project:
            return suggestions
        
        project_path = Path(context.project.path)
        
        # Time-based suggestions
        current_hour = time.localtime().tm_hour
        
        if 9 <= current_hour <= 11:  # Morning
            suggestions.append(Suggestion(
                type='workflow',
                text='sanaa chat',
                description='Start your coding session with AI assistance',
                confidence=0.7,
                category='workflow'
            ))
        elif 14 <= current_hour <= 16:  # Afternoon
            suggestions.append(Suggestion(
                type='workflow', 
                text='debug health',
                description='Run health check on your project',
                confidence=0.6,
                category='workflow'
            ))
        
        # Project state based suggestions
        if len(context.project.files) < 5:
            suggestions.append(Suggestion(
                type='workflow',
                text='projects create',
                description='Project seems small - consider scaffolding',
                confidence=0.5,
                category='workflow'
            ))
        
        return suggestions
    
    def _get_recent_activity_suggestions(self, context: CompletionContext) -> List[Suggestion]:
        """Generate suggestions based on recent activity"""
        
        suggestions = []
        
        # Suggest based on recently modified files
        if context.project:
            project_path = Path(context.project.path)
            
            try:
                # Find recently modified files
                recent_files = []
                for file_entry in context.project.files:
                    file_path = project_path / file_entry.path
                    if file_path.exists():
                        age = time.time() - file_entry.mtime
                        if age < 3600:  # Modified in last hour
                            recent_files.append(file_entry.path)
                
                if recent_files:
                    suggestions.append(Suggestion(
                        type='context',
                        text=f'@{recent_files[0]}',
                        description=f'Recently modified file (reference with @)',
                        confidence=0.6,
                        category='recent'
                    ))
            
            except Exception:
                pass
        
        return suggestions
    
    def _rank_and_filter_suggestions(self, suggestions: List[Suggestion], context: CompletionContext) -> List[Suggestion]:
        """Rank and filter suggestions for optimal user experience"""
        
        # Remove duplicates while preserving highest confidence
        seen = {}
        for suggestion in suggestions:
            key = (suggestion.type, suggestion.text)
            if key not in seen or suggestion.confidence > seen[key].confidence:
                seen[key] = suggestion
        
        unique_suggestions = list(seen.values())
        
        # Apply ranking algorithm
        for suggestion in unique_suggestions:
            # Base score from confidence
            score = suggestion.confidence
            
            # Boost based on usage history
            usage_key = f"{suggestion.type}:{suggestion.text}"
            usage_info = self.usage_stats.get(usage_key, {})
            usage_boost = min(0.3, usage_info.get('count', 0) * 0.05)
            score += usage_boost
            
            # Recency boost
            if usage_info.get('last_used', 0) > time.time() - 3600:  # Used in last hour
                score += 0.2
            
            # Context relevance boost
            if context.project and suggestion.category:
                project_type = self._detect_project_type(context.project)
                if project_type in suggestion.category:
                    score += 0.15
            
            suggestion.priority = int(score * 1000)  # Convert to integer for sorting
        
        # Sort by priority (higher first)
        ranked = sorted(unique_suggestions, key=lambda s: s.priority, reverse=True)
        
        # Filter out low-confidence suggestions unless input is very short
        if len(context.current_input) > 2:
            ranked = [s for s in ranked if s.confidence > 0.2]
        
        return ranked
    
    def record_selection(self, suggestion: Suggestion, context: CompletionContext):
        """Record that user selected a suggestion (for learning)"""
        
        usage_key = f"{suggestion.type}:{suggestion.text}"
        
        if usage_key not in self.usage_stats:
            self.usage_stats[usage_key] = {'count': 0, 'last_used': 0}
        
        self.usage_stats[usage_key]['count'] += 1
        self.usage_stats[usage_key]['last_used'] = time.time()
        
        # Update command history
        self.command_history.append({
            'command': suggestion.text,
            'timestamp': time.time(),
            'context': context.current_input,
            'type': suggestion.type
        })
        
        # Keep only last 1000 commands
        if len(self.command_history) > 1000:
            self.command_history = self.command_history[-1000:]
        
        # Update user patterns
        self._update_user_patterns(context.current_input, suggestion.text)
        
        # Save learning data
        self._save_learning_data()
    
    def _update_user_patterns(self, input_text: str, selected_text: str):
        """Update user pattern learning"""
        
        words = input_text.split()
        if len(words) >= 2:
            pattern_key = ' '.join(words[:-1])
            next_word = selected_text.split()[-1] if selected_text.split() else selected_text
            
            if pattern_key not in self.user_patterns:
                self.user_patterns[pattern_key] = defaultdict(int)
            
            self.user_patterns[pattern_key][next_word] += 1
    
    # Utility methods
    
    def _extract_file_pattern(self, input_text: str) -> Optional[str]:
        """Extract file pattern from input text"""
        
        # Look for file-like patterns
        patterns = [
            r'@([a-zA-Z0-9._/\\-]+)',  # @filename
            r'([a-zA-Z0-9._/\\-]+\.[a-zA-Z0-9]+)',  # filename.ext
            r'([a-zA-Z0-9._/\\-]+/)',  # directory/
        ]
        
        for pattern in patterns:
            match = re.search(pattern, input_text)
            if match:
                return match.group(1)
        
        return None
    
    def _calculate_file_relevance(self, file_path: str, pattern: str, context: CompletionContext) -> float:
        """Calculate relevance score for file completion"""
        
        base_score = 0.5
        
        # Exact name match
        if pattern.lower() == Path(file_path).name.lower():
            base_score += 0.4
        
        # Partial name match
        elif pattern.lower() in Path(file_path).name.lower():
            base_score += 0.2
        
        # Directory match
        elif pattern.lower() in str(Path(file_path).parent).lower():
            base_score += 0.1
        
        # File type relevance
        relevant_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.md'}
        if Path(file_path).suffix.lower() in relevant_extensions:
            base_score += 0.1
        
        # Recent modification boost
        if context.project:
            try:
                file_entry = next(f for f in context.project.files if f.path == file_path)
                age_days = (time.time() - file_entry.mtime) / (24 * 3600)
                if age_days < 1:
                    base_score += 0.2
                elif age_days < 7:
                    base_score += 0.1
            except (StopIteration, AttributeError):
                pass
        
        return min(1.0, base_score)
    
    @lru_cache(maxsize=32)
    def _detect_project_type(self, project: Project) -> str:
        """Detect project type from files"""
        
        file_paths = [f.path for f in project.files]
        
        # Python project
        if any(f.endswith('.py') for f in file_paths):
            if any('requirements.txt' in f or 'pyproject.toml' in f for f in file_paths):
                return 'python'
        
        # JavaScript/Node.js
        if any('package.json' in f for f in file_paths):
            if any('src/App.jsx' in f or 'src/App.tsx' in f for f in file_paths):
                return 'react'
            return 'javascript'
        
        # TypeScript
        if any(f.endswith('.ts') or f.endswith('.tsx') for f in file_paths):
            return 'typescript'
        
        return 'unknown'
    
    # Data persistence methods
    
    def _load_usage_stats(self) -> Dict[str, Dict[str, Any]]:
        """Load usage statistics from cache"""
        
        stats_file = self.cache_dir / 'usage_stats.json'
        if stats_file.exists():
            try:
                with open(stats_file) as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {}
    
    def _load_user_patterns(self) -> Dict[str, Dict[str, int]]:
        """Load user patterns from cache"""
        
        patterns_file = self.cache_dir / 'user_patterns.json'
        if patterns_file.exists():
            try:
                with open(patterns_file) as f:
                    data = json.load(f)
                    # Convert back to defaultdict structure
                    return {k: defaultdict(int, v) for k, v in data.items()}
            except Exception:
                pass
        
        return {}
    
    def _load_command_history(self) -> List[Dict[str, Any]]:
        """Load command history from cache"""
        
        history_file = self.cache_dir / 'command_history.json'
        if history_file.exists():
            try:
                with open(history_file) as f:
                    return json.load(f)
            except Exception:
                pass
        
        return []
    
    def _save_learning_data(self):
        """Save all learning data to cache"""
        
        try:
            # Save usage stats
            with open(self.cache_dir / 'usage_stats.json', 'w') as f:
                json.dump(self.usage_stats, f)
            
            # Save user patterns
            patterns_serializable = {k: dict(v) for k, v in self.user_patterns.items()}
            with open(self.cache_dir / 'user_patterns.json', 'w') as f:
                json.dump(patterns_serializable, f)
            
            # Save command history
            with open(self.cache_dir / 'command_history.json', 'w') as f:
                json.dump(self.command_history, f)
        
        except Exception:
            pass  # Graceful degradation
    
    # Built-in completion data
    
    def _get_sanaa_completions(self) -> List[Tuple[str, str, float]]:
        """Get Sanaa-specific completions"""
        
        return [
            ('sanaa chat', 'Start interactive chat', 0.9),
            ('sanaa projects create', 'Create new project', 0.8),
            ('sanaa projects list', 'List projects', 0.7),
            ('sanaa status', 'Show system status', 0.7),
            ('sanaa config', 'Configure settings', 0.6),
            ('sanaa debug health', 'Run health check', 0.8),
            ('sanaa debug interactive', 'Interactive debugging', 0.7),
            ('sanaa version', 'Show version', 0.5),
            ('sanaa doctor', 'Run diagnostics', 0.6)
        ]
    
    def _get_git_completions(self) -> List[Tuple[str, str, float]]:
        """Get Git command completions"""
        
        return [
            ('git status', 'Show working tree status', 0.9),
            ('git add .', 'Stage all changes', 0.8),
            ('git commit -m', 'Commit with message', 0.9),
            ('git push', 'Push to remote', 0.8),
            ('git pull', 'Pull from remote', 0.8),
            ('git diff', 'Show changes', 0.7),
            ('git log --oneline', 'Show commit history', 0.6),
            ('git checkout -b', 'Create new branch', 0.7),
            ('git merge', 'Merge branches', 0.5),
            ('git reset --hard', 'Reset to last commit', 0.4)
        ]
    
    def _get_python_completions(self) -> List[Tuple[str, str, float]]:
        """Get Python-specific completions"""
        
        return [
            ('python -m pytest', 'Run tests', 0.8),
            ('python -m pip install', 'Install package', 0.8),
            ('python -m venv .venv', 'Create virtual environment', 0.7),
            ('python -m black .', 'Format code', 0.6),
            ('python -m ruff check', 'Run linter', 0.6),
            ('python manage.py runserver', 'Django development server', 0.5),
            ('python -m http.server', 'Start HTTP server', 0.4)
        ]
    
    def _get_npm_completions(self) -> List[Tuple[str, str, float]]:
        """Get npm-specific completions"""
        
        return [
            ('npm install', 'Install dependencies', 0.8),
            ('npm start', 'Start development server', 0.8),
            ('npm run build', 'Build for production', 0.7),
            ('npm test', 'Run tests', 0.7),
            ('npm run dev', 'Development mode', 0.7),
            ('npm audit fix', 'Fix security issues', 0.5),
            ('npm update', 'Update packages', 0.5)
        ]

# -------------------------
# Interactive Completion Interface
# -------------------------

class InteractiveCompletion:
    """Interactive completion interface with real-time suggestions"""
    
    def __init__(self):
        self.console = Console()
        self.engine = SmartCompletionEngine()
        self.current_suggestions: List[Suggestion] = []
    
    def show_suggestions(self, context: CompletionContext):
        """Show suggestions for current context"""
        
        suggestions = self.engine.get_completions(context)
        
        if not suggestions:
            return
        
        self.current_suggestions = suggestions
        
        # Group suggestions by category
        categorized = defaultdict(list)
        for suggestion in suggestions[:10]:  # Show top 10
            category = suggestion.category or 'General'
            categorized[category].append(suggestion)
        
        # Display suggestions
        self.console.print("\n[dim]💡 Suggestions:[/dim]")
        
        for category, suggestions_in_category in categorized.items():
            if len(categorized) > 1:
                self.console.print(f"\n[bold]{category}:[/bold]")
            
            for i, suggestion in enumerate(suggestions_in_category, 1):
                confidence_bar = "█" * int(suggestion.confidence * 5)
                confidence_empty = "░" * (5 - int(suggestion.confidence * 5))
                
                # Color based on type
                type_colors = {
                    'command': 'cyan',
                    'file': 'blue',
                    'project': 'green',
                    'pattern': 'yellow',
                    'workflow': 'magenta'
                }
                color = type_colors.get(suggestion.type, 'white')
                
                self.console.print(
                    f"  {i:2d}. [{color}]{suggestion.text}[/{color}] "
                    f"[dim]{confidence_bar}{confidence_empty}[/dim] {suggestion.description}"
                )
        
        self.console.print("\n[dim]Use tab to autocomplete or type number to select[/dim]")
    
    def select_suggestion(self, index: int, context: CompletionContext) -> Optional[str]:
        """Select a suggestion by index"""
        
        if 0 <= index < len(self.current_suggestions):
            suggestion = self.current_suggestions[index]
            self.engine.record_selection(suggestion, context)
            return suggestion.text
        
        return None

# -------------------------
# CLI Integration
# -------------------------

def create_completion_commands():
    """Create completion-related commands"""
    
    completion_app = typer.Typer(help="Smart completion and suggestions")
    engine = SmartCompletionEngine()
    
    @completion_app.command("analyze")
    def analyze_patterns(
        project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name")
    ):
        """Analyze usage patterns and show insights"""
        
        from coding_swarm_core.projects import ProjectRegistry
        
        registry = ProjectRegistry.load()
        
        if project:
            proj = registry.get(project)
        else:
            # Show global patterns
            proj = None
        
        _show_pattern_analysis(engine, proj)
    
    @completion_app.command("suggestions")
    def show_suggestions(
        text: str = typer.Argument(..., help="Text to get suggestions for"),
        project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name")
    ):
        """Get suggestions for given text"""
        
        from coding_swarm_core.projects import ProjectRegistry
        
        registry = ProjectRegistry.load()
        proj = registry.get(project) if project else None
        
        context = CompletionContext(
            current_input=text,
            cursor_position=len(text),
            project=proj
        )
        
        suggestions = engine.get_completions(context)
        
        if not suggestions:
            rprint("[yellow]No suggestions found[/yellow]")
            return
        
        table = Table(title=f"Suggestions for: {text}")
        table.add_column("Type", style="cyan")
        table.add_column("Suggestion", style="green")
        table.add_column("Confidence", justify="right", style="yellow")
        table.add_column("Description", style="dim")
        
        for suggestion in suggestions[:10]:
            confidence_pct = f"{suggestion.confidence * 100:.0f}%"
            table.add_row(
                suggestion.type.title(),
                suggestion.text,
                confidence_pct,
                suggestion.description
            )
        
        rprint(table)
    
    @completion_app.command("clear-cache")
    def clear_completion_cache():
        """Clear completion learning cache"""
        
        cache_dir = Path.home() / ".sanaa" / "completion_cache"
        
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True)
            rprint("[green]✓ Completion cache cleared[/green]")
        else:
            rprint("[yellow]No cache to clear[/yellow]")
    
    return completion_app

def _show_pattern_analysis(engine: SmartCompletionEngine, project: Optional[Project]):
    """Show pattern analysis for user"""
    
    console = Console()
    
    # Usage statistics
    if engine.usage_stats:
        console.print("[bold]Most Used Commands:[/bold]")
        
        sorted_usage = sorted(
            engine.usage_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        table = Table()
        table.add_column("Command", style="cyan")
        table.add_column("Usage", justify="right", style="green")
        table.add_column("Last Used", style="dim")
        
        for (cmd, stats) in sorted_usage[:10]:
            last_used = time.strftime(
                "%Y-%m-%d", 
                time.localtime(stats['last_used'])
            ) if stats['last_used'] else "Never"
            
            table.add_row(
                cmd.split(':', 1)[-1],  # Remove type prefix
                str(stats['count']),
                last_used
            )
        
        console.print(table)
    
    # Command patterns
    if engine.user_patterns:
        console.print("\n[bold]Common Command Patterns:[/bold]")
        
        for pattern, continuations in list(engine.user_patterns.items())[:5]:
            console.print(f"\n[cyan]{pattern}[/cyan] →")
            
            sorted_continuations = sorted(
                continuations.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            for continuation, count in sorted_continuations[:3]:
                console.print(f"  • {continuation} ({count} times)")
    
    # Recent activity
    if engine.command_history:
        console.print("\n[bold]Recent Activity:[/bold]")
        
        recent_commands = engine.command_history[-10:]
        
        for cmd_info in reversed(recent_commands):
            timestamp = time.strftime(
                "%H:%M",
                time.localtime(cmd_info['timestamp'])
            )
            console.print(f"[dim]{timestamp}[/dim] {cmd_info['command']}")

# Make completion commands available
enhanced_completion = create_completion_commands()