# Premium Sanaa CLI - Production Ready
# packages/cli/src/coding_swarm_cli/premium.py

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import shutil
import time
import difflib
import hashlib
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Set, Union, AsyncGenerator, Callable
from functools import lru_cache
from contextlib import contextmanager

import httpx
import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.align import Align
from rich.columns import Columns
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.rule import Rule
from rich.status import Status
from rich.tree import Tree
from rich.layout import Layout
from rich.padding import Padding

from coding_swarm_core.projects import ProjectRegistry, Project, FileIndexEntry
from coding_swarm_agents.tools import FileReader
from coding_swarm_agents.diagnostics import auto_debug, summarize_fail_report

# -------------------------
# Enhanced Configuration & State Management
# -------------------------

@dataclass
class SanaaConfig:
    """Smart configuration with auto-detection and caching"""
    model_base: str = "http://127.0.0.1:8080/v1"
    model_name: str = "qwen2.5"
    max_context_files: int = 10
    auto_save_frequency: int = 30  # seconds
    enable_semantic_search: bool = True
    enable_autocomplete: bool = True
    cache_ttl: int = 300  # 5 minutes
    max_file_size: int = 1024 * 1024  # 1MB
    preferred_editor: str = "code"
    theme: str = "dark"
    enable_telemetry: bool = True
    workspace_templates: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def load(cls) -> "SanaaConfig":
        """Load config with smart defaults and environment overrides"""
        config_path = Path.home() / ".sanaa" / "config.json"
        config = cls()
        
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text())
                for key, value in data.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
            except Exception:
                pass  # Use defaults on any error
        
        # Environment overrides
        config.model_base = os.getenv("SANAA_MODEL_BASE", config.model_base)
        config.model_name = os.getenv("SANAA_MODEL", config.model_name)
        
        return config
    
    def save(self) -> None:
        """Save configuration atomically"""
        config_path = Path.home() / ".sanaa" / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=config_path.parent) as tmp:
            json.dump(self.__dict__, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
        
        os.replace(tmp.name, config_path)

@dataclass
class SmartCache:
    """Intelligent caching system for file contents and analysis"""
    _cache: Dict[str, Tuple[Any, float]] = field(default_factory=dict)
    _file_hashes: Dict[str, str] = field(default_factory=dict)
    ttl: int = 300
    
    def _hash_file(self, path: Path) -> str:
        """Fast file hash for change detection"""
        stat = path.stat()
        return f"{stat.st_mtime}:{stat.st_size}"
    
    def get(self, key: str, file_path: Optional[Path] = None) -> Optional[Any]:
        """Get cached value with file change detection"""
        if key not in self._cache:
            return None
        
        value, timestamp = self._cache[key]
        
        # Check TTL
        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            return None
        
        # Check file changes
        if file_path and file_path.exists():
            current_hash = self._hash_file(file_path)
            if self._file_hashes.get(key) != current_hash:
                del self._cache[key]
                return None
        
        return value
    
    def set(self, key: str, value: Any, file_path: Optional[Path] = None) -> None:
        """Cache value with optional file tracking"""
        self._cache[key] = (value, time.time())
        if file_path and file_path.exists():
            self._file_hashes[key] = self._hash_file(file_path)
    
    def clear_expired(self) -> None:
        """Remove expired entries"""
        now = time.time()
        expired = [k for k, (_, ts) in self._cache.items() if now - ts > self.ttl]
        for key in expired:
            del self._cache[key]
            self._file_hashes.pop(key, None)

# -------------------------
# Smart Context Management
# -------------------------

class ContextManager:
    """Intelligent context selection and management"""
    
    def __init__(self, config: SanaaConfig):
        self.config = config
        self.cache = SmartCache(ttl=config.cache_ttl)
        self._file_reader = FileReader()
    
    def _calculate_relevance(self, file_path: str, query: str, project_root: Path) -> float:
        """Calculate relevance score for a file given a query"""
        path = Path(file_path)
        score = 0.0
        
        # File name relevance
        query_terms = set(query.lower().split())
        file_terms = set(path.stem.lower().split('_') + path.stem.lower().split('-'))
        common_terms = query_terms.intersection(file_terms)
        score += len(common_terms) * 0.3
        
        # Extension relevance
        relevant_extensions = {'.py': 0.2, '.js': 0.2, '.ts': 0.2, '.html': 0.1, '.css': 0.1}
        score += relevant_extensions.get(path.suffix.lower(), 0)
        
        # Directory depth penalty
        try:
            relative_path = path.relative_to(project_root)
            depth = len(relative_path.parts)
            score -= depth * 0.05
        except ValueError:
            pass
        
        # Recent files bonus
        try:
            mtime = path.stat().st_mtime
            age_days = (time.time() - mtime) / (24 * 3600)
            if age_days < 1:
                score += 0.2
            elif age_days < 7:
                score += 0.1
        except OSError:
            pass
        
        return max(0, score)
    
    def _search_file_content(self, content: str, query: str) -> Tuple[float, List[str]]:
        """Search within file content and return relevance score + snippets"""
        lines = content.split('\n')
        query_terms = query.lower().split()
        
        relevant_lines = []
        total_score = 0.0
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            line_score = 0.0
            
            # Exact phrase matching
            if query.lower() in line_lower:
                line_score += 1.0
            
            # Term matching
            term_matches = sum(1 for term in query_terms if term in line_lower)
            line_score += term_matches * 0.3
            
            # Code relevance (functions, classes, etc.)
            if any(keyword in line_lower for keyword in ['def ', 'class ', 'function ', 'const ']):
                line_score += 0.5
            
            if line_score > 0.3:
                # Include context lines
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                snippet = '\n'.join(f"{j+1:4d}: {lines[j]}" for j in range(start, end))
                relevant_lines.append(snippet)
                total_score += line_score
        
        return total_score, relevant_lines[:5]  # Limit snippets
    
    async def get_smart_context(self, query: str, project: Project) -> Dict[str, Any]:
        """Get intelligently selected context for a query"""
        project_path = Path(project.path)
        context = {
            "query": query,
            "project": project.name,
            "files": [],
            "total_files": len(project.files),
            "context_strategy": "smart_selection"
        }
        
        # Score all files
        file_scores = []
        for file_entry in project.files:
            file_path = project_path / file_entry.path
            if not file_path.exists() or file_entry.size > self.config.max_file_size:
                continue
            
            relevance = self._calculate_relevance(file_entry.path, query, project_path)
            if relevance > 0.1:  # Minimum threshold
                file_scores.append((relevance, file_entry))
        
        # Sort by relevance and take top N
        file_scores.sort(reverse=True)
        selected_files = file_scores[:self.config.max_context_files]
        
        # Read and analyze selected files
        for relevance, file_entry in selected_files:
            file_path = project_path / file_entry.path
            cache_key = f"content:{file_path}"
            
            content = self.cache.get(cache_key, file_path)
            if content is None:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    self.cache.set(cache_key, content, file_path)
                except Exception:
                    continue
            
            # Search within content
            content_score, snippets = self._search_file_content(content, query)
            final_score = relevance + content_score * 0.5
            
            context["files"].append({
                "path": file_entry.path,
                "relevance_score": final_score,
                "size": file_entry.size,
                "snippets": snippets if self.config.enable_semantic_search else [],
                "full_content": content if final_score > 1.0 else None  # Only include full content for highly relevant files
            })
        
        # Sort by final score
        context["files"].sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return context

# -------------------------
# Fuzzy Matching & Forgiveness
# -------------------------

class FuzzyMatcher:
    """Smart fuzzy matching for commands, projects, and files"""
    
    @staticmethod
    def find_best_match(query: str, candidates: List[str], threshold: float = 0.6) -> Optional[str]:
        """Find the best fuzzy match with confidence threshold"""
        if not candidates:
            return None
        
        matches = difflib.get_close_matches(query, candidates, n=1, cutoff=threshold)
        return matches[0] if matches else None
    
    @staticmethod
    def suggest_corrections(query: str, candidates: List[str], max_suggestions: int = 3) -> List[Tuple[str, float]]:
        """Get multiple suggestions with confidence scores"""
        suggestions = []
        for candidate in candidates:
            ratio = difflib.SequenceMatcher(None, query.lower(), candidate.lower()).ratio()
            if ratio > 0.4:  # Lower threshold for suggestions
                suggestions.append((candidate, ratio))
        
        return sorted(suggestions, key=lambda x: x[1], reverse=True)[:max_suggestions]

class ForgivingPrompt:
    """Enhanced prompting with auto-correction and smart defaults"""
    
    def __init__(self, fuzzy_matcher: FuzzyMatcher):
        self.fuzzy = fuzzy_matcher
    
    def ask_with_suggestions(self, 
                           prompt: str, 
                           candidates: List[str], 
                           default: Optional[str] = None,
                           allow_new: bool = True) -> str:
        """Prompt with fuzzy matching and suggestions"""
        
        while True:
            try:
                response = Prompt.ask(prompt, default=default).strip()
                
                if not response and default:
                    return default
                
                # Exact match
                if response in candidates:
                    return response
                
                # Fuzzy match
                best_match = self.fuzzy.find_best_match(response, candidates)
                if best_match:
                    if Confirm.ask(f"Did you mean '{best_match}'?", default=True):
                        return best_match
                
                # Show suggestions
                suggestions = self.fuzzy.suggest_corrections(response, candidates)
                if suggestions and not allow_new:
                    console.print("[yellow]Available options:[/yellow]")
                    for i, (suggestion, score) in enumerate(suggestions, 1):
                        console.print(f"  {i}. {suggestion} (confidence: {score:.1%})")
                    
                    choice = Prompt.ask("Choose number or type again", default="").strip()
                    if choice.isdigit():
                        idx = int(choice) - 1
                        if 0 <= idx < len(suggestions):
                            return suggestions[idx][0]
                elif allow_new:
                    return response
                    
            except KeyboardInterrupt:
                raise typer.Exit(0)

# -------------------------
# Enhanced Progress & Status
# -------------------------

class SmartProgress:
    """Intelligent progress tracking with context awareness"""
    
    def __init__(self):
        self.console = Console()
    
    @contextmanager
    def task_progress(self, description: str, total: Optional[int] = None):
        """Context manager for task progress"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn() if total else TextColumn(""),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%") if total else TextColumn(""),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(description, total=total)
            yield progress, task
    
    @contextmanager
    def status_context(self, status: str):
        """Simple status context for quick operations"""
        with Status(status, console=self.console):
            yield

# -------------------------
# Premium CLI Application
# -------------------------

class PremiumSanaa:
    """Premium Sanaa CLI with advanced features"""
    
    def __init__(self):
        self.config = SanaaConfig.load()
        self.console = Console()
        self.fuzzy = FuzzyMatcher()
        self.prompt = ForgivingPrompt(self.fuzzy)
        self.progress = SmartProgress()
        self.context_manager = ContextManager(self.config)
        self._client_cache: Optional[httpx.AsyncClient] = None
        
        # Auto-save timer
        self._last_save = time.time()
    
    async def __aenter__(self):
        self._client_cache = httpx.AsyncClient(
            base_url=self.config.model_base,
            timeout=60,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client_cache:
            await self._client_cache.aclose()
    
    def show_welcome_banner(self):
        """Premium welcome banner with system info"""
        
        # System status
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            system_info = f"""
[dim]System: CPU {cpu_percent:.1f}% • RAM {memory.percent:.1f}% • Disk {disk.percent:.1f}%[/dim]
[dim]Model: {self.config.model_name} @ {self.config.model_base}[/dim]
"""
        except ImportError:
            system_info = f"[dim]Model: {self.config.model_name}[/dim]"
        
        banner_text = Text()
        banner_text.append("Sanaa", style="bold cyan")
        banner_text.append(" • AI-Powered Development Assistant", style="dim")
        
        panel = Panel(
            Align.center(banner_text) + system_info,
            border_style="cyan",
            padding=(1, 2)
        )
        
        self.console.print(panel)
        self.console.print()
    
    def smart_project_selection(self, registry: ProjectRegistry, hint: Optional[str] = None) -> Optional[Project]:
        """Smart project selection with fuzzy matching"""
        
        projects = registry.list()
        if not projects:
            self.console.print("[yellow]No projects yet. Let's create one![/yellow]")
            return None
        
        project_names = [p.name for p in projects]
        
        # If hint provided, try fuzzy matching
        if hint:
            match = self.fuzzy.find_best_match(hint, project_names)
            if match:
                return registry.get(match)
            
            # Show suggestions
            suggestions = self.fuzzy.suggest_corrections(hint, project_names)
            if suggestions:
                self.console.print(f"[yellow]Project '{hint}' not found. Did you mean:[/yellow]")
                for suggestion, score in suggestions:
                    self.console.print(f"  • {suggestion} (confidence: {score:.1%})")
        
        # Interactive selection with rich display
        self._display_projects_table(registry, projects)
        
        selected = self.prompt.ask_with_suggestions(
            "Select project",
            project_names,
            default=registry.default,
            allow_new=False
        )
        
        return registry.get(selected)
    
    def _display_projects_table(self, registry: ProjectRegistry, projects: List[Project]):
        """Display projects in a rich table"""
        
        table = Table(title="Available Projects", show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Path", style="blue")
        table.add_column("Files", justify="right", style="green")
        table.add_column("Updated", style="yellow")
        table.add_column("Default", justify="center", style="red")
        
        for project in projects:
            updated = time.strftime("%Y-%m-%d", time.localtime(project.updated_at))
            is_default = "★" if registry.default == project.name else ""
            
            table.add_row(
                project.name,
                project.path,
                str(len(project.files)),
                updated,
                is_default
            )
        
        self.console.print(table)
        self.console.print()
    
    async def smart_chat(self, project: Optional[Project], initial_message: Optional[str] = None):
        """Enhanced chat with smart context and streaming"""
        
        messages = [{"role": "system", "content": "You are Sanaa, an expert AI coding assistant. You're helpful, direct, and provide practical solutions."}]
        
        if project:
            messages.append({
                "role": "system",
                "content": f"Working on project '{project.name}' at {project.path}. {project.notes}"
            })
        
        self.console.print("[green]Smart Chat Mode[/green] • Type '/exit' to leave, '/help' for commands")
        self.console.print("[dim]Context-aware • Auto-suggestions • File mentions with @[/dim]")
        self.console.print()
        
        if initial_message:
            await self._process_message(initial_message, messages, project)
        
        while True:
            try:
                # Smart prompting with auto-complete hints
                user_input = Prompt.ask(
                    "[bold magenta]you[/bold magenta]",
                    default=""
                ).strip()
                
                if user_input.lower() in ['/exit', '/quit', 'exit', 'quit']:
                    break
                
                if user_input.lower() == '/help':
                    self._show_chat_help()
                    continue
                
                if user_input.lower() == '/context' and project:
                    await self._show_project_context(project)
                    continue
                
                if user_input.lower().startswith('/files') and project:
                    await self._show_relevant_files(user_input[6:].strip(), project)
                    continue
                
                if not user_input:
                    continue
                
                await self._process_message(user_input, messages, project)
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use /exit to quit gracefully[/yellow]")
                continue
            except EOFError:
                break
    
    async def _process_message(self, user_input: str, messages: List[Dict], project: Optional[Project]):
        """Process a chat message with smart context injection"""
        
        # Handle file mentions (@filename)
        if project and '@' in user_input:
            user_input = await self._resolve_file_mentions(user_input, project)
        
        messages.append({"role": "user", "content": user_input})
        
        # Get smart context if project is available
        context_info = ""
        if project:
            with self.progress.status_context("Analyzing project context..."):
                context = await self.context_manager.get_smart_context(user_input, project)
                
                if context["files"]:
                    context_info = "\n\n--- Relevant Project Context ---\n"
                    for file_info in context["files"][:3]:  # Top 3 most relevant
                        context_info += f"\n**{file_info['path']}** (relevance: {file_info['relevance_score']:.2f})\n"
                        if file_info.get("snippets"):
                            context_info += "Relevant sections:\n"
                            for snippet in file_info["snippets"][:2]:  # Top 2 snippets
                                context_info += f"```\n{snippet}\n```\n"
        
        # Call LLM with enhanced context
        enhanced_message = user_input + context_info
        messages[-1]["content"] = enhanced_message
        
        try:
            with self.progress.status_context("Thinking..."):
                response = await self._call_llm_async(messages)
            
            # Display response with syntax highlighting if it contains code
            if '```' in response:
                self._display_code_response(response)
            else:
                self.console.print(f"[cyan]sanaa[/cyan]: {response}")
            
            messages.append({"role": "assistant", "content": response})
            
            # Auto-save conversation
            if time.time() - self._last_save > self.config.auto_save_frequency:
                await self._auto_save_conversation(messages, project)
        
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
    
    async def _resolve_file_mentions(self, text: str, project: Project) -> str:
        """Resolve @file mentions to actual file content"""
        
        import re
        project_path = Path(project.path)
        
        # Find all @mentions
        mentions = re.findall(r'@(\S+)', text)
        
        for mention in mentions:
            # Find matching files
            matching_files = []
            for file_entry in project.files:
                if mention.lower() in file_entry.path.lower():
                    matching_files.append(file_entry)
            
            if matching_files:
                # Use most relevant file
                best_file = max(matching_files, key=lambda f: mention.lower() in f.path.lower().split('/')[-1])
                file_path = project_path / best_file.path
                
                try:
                    if file_path.exists() and best_file.size < self.config.max_file_size:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        replacement = f"\n\n--- Content of {best_file.path} ---\n```\n{content}\n```\n"
                        text = text.replace(f"@{mention}", replacement)
                except Exception:
                    text = text.replace(f"@{mention}", f"[File {mention} not accessible]")
        
        return text
    
    def _display_code_response(self, response: str):
        """Display response with syntax highlighting for code blocks"""
        
        parts = response.split('```')
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Regular text
                if part.strip():
                    self.console.print(f"[cyan]sanaa[/cyan]: {part}")
            else:  # Code block
                lines = part.split('\n')
                language = lines[0].strip() if lines else "text"
                code = '\n'.join(lines[1:]) if len(lines) > 1 else part
                
                try:
                    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
                    self.console.print(syntax)
                except Exception:
                    self.console.print(f"```{language}\n{code}\n```")
    
    async def _call_llm_async(self, messages: List[Dict]) -> str:
        """Async LLM call with error handling"""
        
        if not self._client_cache:
            raise RuntimeError("HTTP client not initialized")
        
        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        response = await self._client_cache.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        
        return data["choices"][0]["message"]["content"]
    
    def _show_chat_help(self):
        """Show chat help commands"""
        
        help_text = """[bold]Chat Commands:[/bold]
        
/exit, /quit    Exit chat
/help          Show this help
/context       Show project context summary
/files <query> Show files relevant to query
@filename      Include file content in message

[bold]Tips:[/bold]
• Be specific about what you want to accomplish
• Mention file names with @ to include their content
• Ask for explanations, code reviews, or implementations
• Use natural language - I understand context!
"""
        
        self.console.print(Panel(help_text, title="Help", border_style="blue"))
    
    async def _show_project_context(self, project: Project):
        """Show comprehensive project context"""
        
        # File type distribution
        extensions = {}
        total_size = 0
        
        for file_entry in project.files:
            ext = Path(file_entry.path).suffix.lower() or 'no extension'
            extensions[ext] = extensions.get(ext, 0) + 1
            total_size += file_entry.size
        
        # Create visualization
        table = Table(title=f"Project Context: {project.name}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Files", str(len(project.files)))
        table.add_row("Total Size", f"{total_size / 1024 / 1024:.1f} MB")
        table.add_row("Last Updated", time.strftime("%Y-%m-%d %H:%M", time.localtime(project.updated_at)))
        
        self.console.print(table)
        
        # File types
        if extensions:
            type_table = Table(title="File Types")
            type_table.add_column("Extension", style="blue")
            type_table.add_column("Count", justify="right", style="green")
            
            for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:10]:
                type_table.add_row(ext, str(count))
            
            self.console.print(type_table)
    
    async def _show_relevant_files(self, query: str, project: Project):
        """Show files relevant to a query"""
        
        if not query.strip():
            self.console.print("[yellow]Please provide a search query after /files[/yellow]")
            return
        
        with self.progress.status_context(f"Searching for files related to '{query}'..."):
            context = await self.context_manager.get_smart_context(query, project)
        
        if not context["files"]:
            self.console.print(f"[yellow]No files found relevant to '{query}'[/yellow]")
            return
        
        table = Table(title=f"Files relevant to: {query}")
        table.add_column("File", style="cyan")
        table.add_column("Relevance", justify="right", style="green")
        table.add_column("Size", justify="right", style="blue")
        
        for file_info in context["files"][:10]:
            size_str = f"{file_info['size'] / 1024:.1f}K" if file_info['size'] > 1024 else f"{file_info['size']}B"
            table.add_row(
                file_info["path"],
                f"{file_info['relevance_score']:.2f}",
                size_str
            )
        
        self.console.print(table)
    
    async def _auto_save_conversation(self, messages: List[Dict], project: Optional[Project]):
        """Auto-save conversation for recovery"""
        
        if not project:
            return
        
        conversations_dir = Path.home() / ".sanaa" / "conversations"
        conversations_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{project.name}_{timestamp}.json"
        
        conversation_data = {
            "project": project.name,
            "timestamp": time.time(),
            "messages": messages
        }
        
        with open(conversations_dir / filename, 'w') as f:
            json.dump(conversation_data, f, indent=2)
        
        self._last_save = time.time()

# -------------------------
# Enhanced CLI Commands
# -------------------------

app = typer.Typer(add_completion=False, help="Sanaa - Premium AI Development Assistant")
console = Console()

# Global instance
sanaa = None

@app.callback()
def initialize():
    """Initialize premium Sanaa"""
    global sanaa
    if sanaa is None:
        sanaa = PremiumSanaa()

@app.command()
def welcome():
    """Show welcome screen and system status"""
    sanaa.show_welcome_banner()

@app.command() 
def chat(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name or pattern"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Initial message")
):
    """Smart chat with context awareness"""
    
    async def run_chat():
        async with sanaa:
            registry = ProjectRegistry.load()
            proj = sanaa.smart_project_selection(registry, project) if project else None
            await sanaa.smart_chat(proj, message)
    
    asyncio.run(run_chat())

@app.command()
def status():
    """Show detailed system and project status"""

    registry = ProjectRegistry.load()
    projects = registry.list()

    # System status
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )

    # Header
    header_text = Text("Sanaa System Status", style="bold cyan", justify="center")
    layout["header"].update(Panel(header_text))

    # Body - split into projects and configuration
    layout["body"].split_row(
        Layout(name="projects"),
        Layout(name="config")
    )

    # Projects table
    if projects:
        projects_table = Table(title="Projects", show_header=True)
        projects_table.add_column("Name", style="cyan")
        projects_table.add_column("Files", justify="right", style="green")
        projects_table.add_column("Status", style="yellow")

        for project in projects[:5]:  # Show top 5
            status_icon = "★" if registry.default == project.name else "○"
            projects_table.add_row(project.name, str(len(project.files)), status_icon)

        layout["projects"].update(Panel(projects_table))
    else:
        layout["projects"].update(Panel("No projects configured", title="Projects"))

    # Configuration
    config_text = f"""Model: {sanaa.config.model_name}
Endpoint: {sanaa.config.model_base}
Cache TTL: {sanaa.config.cache_ttl}s
Max Context: {sanaa.config.max_context_files} files
Semantic Search: {'✓' if sanaa.config.enable_semantic_search else '✗'}"""

    layout["config"].update(Panel(config_text, title="Configuration"))

    # Footer
    footer_text = f"Ready • {len(projects)} projects • Config: ~/.sanaa/config.json"
    layout["footer"].update(Panel(footer_text, style="dim"))

    console.print(layout)

@app.command()
def react(
    action: str = typer.Argument(..., help="Action to perform (component, hook, page, api)"),
    name: str = typer.Argument(..., help="Name of the item to create"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name")
):
    """React development assistant - Create components, hooks, pages, and APIs"""
    from coding_swarm_agents import create_agent

    try:
        # Create React agent
        context = {"project": project or "."}
        agent = create_agent("react", context)

        # Execute action
        if action == "component":
            success = agent.apply_patch(f"component {name}")
        elif action == "hook":
            success = agent.apply_patch(f"hook {name}")
        elif action == "page":
            success = agent.apply_patch(f"page {name}")
        elif action == "api":
            success = agent.apply_patch(f"api {name}")
        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            console.print("[yellow]Available actions: component, hook, page, api[/yellow]")
            return

        if success:
            console.print(f"[green]✓ {action.title()} '{name}' created successfully![/green]")
        else:
            console.print(f"[red]✗ Failed to create {action} '{name}'[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@app.command()
def laravel(
    action: str = typer.Argument(..., help="Action to perform (model, controller, migration, request, resource)"),
    name: str = typer.Argument(..., help="Name of the item to create"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name")
):
    """Laravel development assistant - Create models, controllers, migrations, and more"""
    from coding_swarm_agents import create_agent

    try:
        # Create Laravel agent
        context = {"project": project or "."}
        agent = create_agent("laravel", context)

        # Execute action
        if action in ["model", "controller", "migration", "request", "resource"]:
            success = agent.apply_patch(f"{action} {name}")
        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            console.print("[yellow]Available actions: model, controller, migration, request, resource[/yellow]")
            return

        if success:
            console.print(f"[green]✓ {action.title()} '{name}' created successfully![/green]")
        else:
            console.print(f"[red]✗ Failed to create {action} '{name}'[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@app.command()
def flutter(
    action: str = typer.Argument(..., help="Action to perform (widget, provider, model, service, screen, bloc)"),
    name: str = typer.Argument(..., help="Name of the item to create"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name")
):
    """Flutter development assistant - Create widgets, providers, models, and more"""
    from coding_swarm_agents import create_agent

    try:
        # Create Flutter agent
        context = {"project": project or "."}
        agent = create_agent("flutter", context)

        # Execute action
        if action in ["widget", "provider", "model", "service", "screen", "bloc"]:
            success = agent.apply_patch(f"{action} {name}")
        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            console.print("[yellow]Available actions: widget, provider, model, service, screen, bloc[/yellow]")
            return

        if success:
            console.print(f"[green]✓ {action.title()} '{name}' created successfully![/green]")
        else:
            console.print(f"[red]✗ Failed to create {action} '{name}'[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@app.command()
def debug(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
    deep: bool = typer.Option(False, "--deep", help="Run deep analysis")
):
    """Advanced debugging assistant - Analyze and fix code issues"""
    from coding_swarm_agents import create_agent

    try:
        # Create advanced debugger agent
        context = {"project": project or "."}
        agent = create_agent("advanced_debugger", context)

        # Run analysis
        if deep:
            success = agent.apply_patch("analyze deep")
        else:
            success = agent.apply_patch("analyze")

        if success:
            console.print("[green]✓ Debug analysis completed![/green]")
        else:
            console.print("[red]✗ Debug analysis failed[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@app.command()
def plan(
    goal: str = typer.Argument(..., help="Project goal or description"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name")
):
    """Planning assistant - Create comprehensive development plans"""
    from coding_swarm_agents import create_agent

    try:
        # Create planning agent
        context = {"project": project or ".", "goal": goal}
        agent = create_agent("planner", context)

        # Generate plan
        plan_text = agent.plan()

        # Display plan with rich formatting
        from rich.markdown import Markdown
        console.print(Markdown(plan_text))

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@app.command()
def projects():
    """Launch Sanaa Projects - Comprehensive project management interface"""
    from .sanaa_projects import run_sanaa_projects

    try:
        asyncio.run(run_sanaa_projects())
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye![/dim]")
    except Exception as e:
        console.print(f"[red]Error launching Sanaa Projects: {e}[/red]")

@app.command()
def health():
    """Check system health and fix unhealthy containers"""
    console.print("[bold cyan]🔍 System Health Check[/bold cyan]\n")

    # Check Docker containers
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--format", "table {{.Names}}\\t{{.Status}}\\t{{.Image}}"],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # Has header + containers
                console.print("[bold]Docker Containers Status:[/bold]")

                unhealthy_containers = []
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 3:
                            name = parts[0]
                            status = ' '.join(parts[1:-1])
                            image = parts[-1]

                            # Check for unhealthy status
                            if 'unhealthy' in status.lower():
                                unhealthy_containers.append((name, status, image))
                                console.print(f"[red]✗ {name}: {status}[/red]")
                            elif 'healthy' in status.lower():
                                console.print(f"[green]✓ {name}: {status}[/green]")
                            else:
                                console.print(f"[yellow]⚠ {name}: {status}[/yellow]")

                # Fix unhealthy containers
                if unhealthy_containers:
                    console.print(f"\n[bold red]Found {len(unhealthy_containers)} unhealthy containers[/bold red]")
                    if Confirm.ask("Attempt to fix unhealthy containers?", default=True):
                        for name, status, image in unhealthy_containers:
                            console.print(f"\n[bold]Fixing {name}...[/bold]")

                            # Try restarting the container
                            restart_result = subprocess.run(
                                ["docker", "restart", name],
                                capture_output=True, text=True, timeout=30
                            )

                            if restart_result.returncode == 0:
                                console.print(f"[green]✓ Successfully restarted {name}[/green]")

                                # Wait a moment and check status
                                import time
                                time.sleep(3)

                                status_result = subprocess.run(
                                    ["docker", "ps", "--filter", f"name={name}", "--format", "{{.Status}}"],
                                    capture_output=True, text=True
                                )

                                if status_result.returncode == 0 and 'healthy' in status_result.stdout.lower():
                                    console.print(f"[green]✓ {name} is now healthy[/green]")
                                else:
                                    console.print(f"[yellow]⚠ {name} restarted but status unclear[/yellow]")
                            else:
                                console.print(f"[red]✗ Failed to restart {name}: {restart_result.stderr}[/red]")
                    else:
                        console.print("[dim]Skipping container fixes[/dim]")
                else:
                    console.print("\n[green]✓ All containers are healthy![/green]")
            else:
                console.print("[yellow]No running containers found[/yellow]")
        else:
            console.print(f"[red]Error checking Docker: {result.stderr}[/red]")

    except Exception as e:
        console.print(f"[red]Error during health check: {e}[/red]")

    # Check model endpoints
    console.print("\n[bold]Model Endpoints Check:[/bold]")
    endpoints = [
        ("http://127.0.0.1:8080/v1/models", "API Model (Port 8080)"),
        ("http://127.0.0.1:8081/v1/models", "Web Model (Port 8081)"),
        ("http://127.0.0.1:8082/v1/models", "Mobile Model (Port 8082)"),
        ("http://127.0.0.1:8083/v1/models", "Test Model (Port 8083)"),
    ]

    for url, name in endpoints:
        try:
            import httpx
            with httpx.Client(timeout=5) as client:
                response = client.get(url)
                if response.status_code == 200:
                    console.print(f"[green]✓ {name}: Available[/green]")
                else:
                    console.print(f"[yellow]⚠ {name}: Status {response.status_code}[/yellow]")
        except Exception:
            console.print(f"[red]✗ {name}: Unavailable[/red]")

    # Check other services
    console.print("\n[bold]Service Health Check:[/bold]")
    services = [
        ("http://127.0.0.1:7700/health", "Meilisearch (Port 7700)"),
        ("http://127.0.0.1:1025", "Mailpit SMTP (Port 1025)"),
        ("http://127.0.0.1:8025", "Mailpit Web (Port 8025)"),
    ]

    for url, name in services:
        try:
            import httpx
            with httpx.Client(timeout=5) as client:
                response = client.get(url)
                if response.status_code in [200, 404]:  # 404 is OK for some services
                    console.print(f"[green]✓ {name}: Available[/green]")
                else:
                    console.print(f"[yellow]⚠ {name}: Status {response.status_code}[/yellow]")
        except Exception:
            console.print(f"[red]✗ {name}: Unavailable[/red]")

    console.print("\n[dim]Health check completed. Use 'sanaa projects' for full project management.[/dim]")

if __name__ == "__main__":
    app()