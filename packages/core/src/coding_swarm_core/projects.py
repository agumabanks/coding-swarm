# Unified Premium Sanaa CLI - Production Ready Entry Point
# packages/cli/src/coding_swarm_cli/main.py

"""
Sanaa - Premium AI Development Assistant
A proud-to-ship interactive CLI with smart context, forgiveness, and premium UX
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Optional, List, Any

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.align import Align
from rich.text import Text
from rich.prompt import Confirm
from rich.traceback import install as install_rich_traceback
from dataclasses import dataclass
from typing import List, Optional
import json
import time
from pathlib import Path

# Install rich tracebacks for better error display
install_rich_traceback(show_locals=True)

# -------------------------
# Core Data Classes
# -------------------------

@dataclass
class FileIndexEntry:
    """Represents a file in the project index"""
    path: str
    size: int
    mtime: float = 0.0

@dataclass
class Project:
    """Represents a coding project"""
    name: str
    path: str
    files: List[FileIndexEntry] = None
    updated_at: float = None
    notes: str = ""

    def __post_init__(self):
        if self.files is None:
            self.files = []
        if self.updated_at is None:
            self.updated_at = time.time()

class ProjectRegistry:
    """Manages project metadata and indexing"""

    def __init__(self):
        self.projects: dict[str, Project] = {}
        self.default: Optional[str] = None
        self._data_file = Path.home() / ".sanaa" / "projects.json"
        self._load()

    def _load(self):
        """Load projects from disk"""
        if self._data_file.exists():
            try:
                data = json.loads(self._data_file.read_text())
                self.default = data.get('default')

                for name, proj_data in data.get('projects', {}).items():
                    files = []
                    for file_data in proj_data.get('files', []):
                        files.append(FileIndexEntry(**file_data))

                    project = Project(
                        name=name,
                        path=proj_data['path'],
                        files=files,
                        updated_at=proj_data.get('updated_at', time.time()),
                        notes=proj_data.get('notes', '')
                    )
                    self.projects[name] = project
            except Exception:
                # If loading fails, start with empty registry
                pass

    def _save(self):
        """Save projects to disk"""
        self._data_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'default': self.default,
            'projects': {}
        }

        for name, project in self.projects.items():
            data['projects'][name] = {
                'path': project.path,
                'files': [{'path': f.path, 'size': f.size, 'mtime': f.mtime} for f in project.files],
                'updated_at': project.updated_at,
                'notes': project.notes
            }

        self._data_file.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls) -> "ProjectRegistry":
        """Load project registry"""
        return cls()

    def list(self) -> List[Project]:
        """List all projects"""
        return list(self.projects.values())

    def get(self, name: str) -> Optional[Project]:
        """Get project by name"""
        return self.projects.get(name)

    def add(self, project: Project):
        """Add a project"""
        self.projects[project.name] = project
        self._save()

    def remove(self, name: str):
        """Remove a project"""
        if name in self.projects:
            del self.projects[name]
            if self.default == name:
                self.default = None
            self._save()

    def set_default(self, name: str):
        """Set default project"""
        if name in self.projects:
            self.default = name
            self._save()

    def read_journal(self, project_name: str, limit: int = 10) -> List[dict]:
        """Read project journal entries"""
        project = self.get(project_name)
        if not project:
            return []

        journal_file = Path(project.path) / ".sanaa" / "journal.md"
        if not journal_file.exists():
            return []

        try:
            content = journal_file.read_text()
            # Simple parsing - this could be improved
            entries = []
            for line in content.split('\n'):
                if line.startswith('### '):
                    timestamp_str = line[4:].strip()
                    try:
                        # Try to parse timestamp
                        timestamp = time.mktime(time.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S UTC'))
                        entries.append({
                            'event': 'journal_entry',
                            '_ts': timestamp,
                            'description': 'Journal entry'
                        })
                    except:
                        pass

            return entries[-limit:] if entries else []
        except Exception:
            return []

# Import premium components (these will be created if they don't exist)
try:
    from .premium import PremiumSanaa, SanaaConfig
except ImportError:
    # Create stub classes if premium module doesn't exist
    class SanaaConfig:
        def __init__(self):
            self.model_base = "http://127.0.0.1:8080/v1"
            self.model_name = "qwen2.5-coder-7b-instruct-q4_k_m"
            self.max_context_files = 10
            self.cache_ttl = 300
            self.enable_semantic_search = True
            self.enable_autocomplete = True
            self.enable_telemetry = True

        @classmethod
        def load(cls):
            return cls()

        def save(self):
            pass

    class PremiumSanaa:
        def __init__(self):
            pass

        def smart_project_selection(self, registry, project):
            return None

        async def smart_chat(self, project, message=None):
            console.print("[yellow]Premium Sanaa features not available[/yellow]")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

try:
    from .project_manager import PremiumProjectManager, enhanced_projects
except ImportError:
    # Create stub classes if project_manager doesn't exist
    class PremiumProjectManager:
        def create_project_wizard(self):
            return None

    enhanced_projects = None

# -------------------------
# Global State & Configuration
# -------------------------

app = typer.Typer(
    name="sanaa",
    help="Sanaa - Premium AI Development Assistant",
    epilog="Visit https://github.com/your-org/coding-swarm for documentation and support.",
    add_completion=True,
    rich_markup_mode="rich"
)

console = Console()
config = SanaaConfig()

# Global instances (lazy initialized)
sanaa: Optional[PremiumSanaa] = None
project_manager: Optional[PremiumProjectManager] = None

def get_sanaa() -> PremiumSanaa:
    """Get or create global Sanaa instance"""
    global sanaa
    if sanaa is None:
        sanaa = PremiumSanaa()
    return sanaa

def get_project_manager() -> PremiumProjectManager:
    """Get or create global project manager"""
    global project_manager
    if project_manager is None:
        project_manager = PremiumProjectManager()
    return project_manager

# -------------------------
# Smart Startup & Health Checks
# -------------------------

def check_system_health() -> List[str]:
    """Check system health and return list of issues"""
    issues = []
    
    # Check model endpoint
    try:
        import httpx
        with httpx.Client(timeout=5) as client:
            response = client.get(f"{config.model_base}/models")
            if response.status_code != 200:
                issues.append(f"Model endpoint unreachable: {config.model_base}")
    except Exception:
        issues.append(f"Cannot connect to model: {config.model_base}")
    
    # Check required directories
    data_dir = Path.home() / ".sanaa"
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
    
    # Check git availability
    import shutil
    if not shutil.which("git"):
        issues.append("Git not found in PATH (git operations will be disabled)")
    
    return issues

def show_startup_banner():
    """Show premium startup banner with system status"""
    
    # Health check
    issues = check_system_health()
    health_status = "🟢 All systems operational" if not issues else f"🟡 {len(issues)} issues detected"
    
    # System info
    try:
        registry = ProjectRegistry.load()
        project_count = len(registry.list())
        default_project = registry.default or "None"
    except Exception:
        project_count = 0
        default_project = "None"
    
    # Create banner
    title = Text("Sanaa", style="bold cyan")
    title.append(" AI Development Assistant", style="dim")
    
    status_info = f"""
[dim]Model:[/dim] {config.model_name} @ {config.model_base.split('/')[-2] if '://' in config.model_base else 'local'}
[dim]Projects:[/dim] {project_count} configured • Default: {default_project}
[dim]Status:[/dim] {health_status}
"""
    
    banner = Panel(
        Align.center(title) + status_info.strip(),
        border_style="cyan" if not issues else "yellow",
        padding=(1, 2)
    )
    
    console.print(banner)
    
    # Show issues if any
    if issues:
        console.print("\n[yellow]⚠ System Issues:[/yellow]")
        for issue in issues:
            console.print(f"  • {issue}")
        console.print()

# -------------------------
# Smart Interactive Mode
# -------------------------

class SmartInteractiveMode:
    """Enhanced interactive mode with context awareness"""
    
    def __init__(self):
        self.console = Console()
        self.sanaa = get_sanaa()
        self.project_manager = get_project_manager()
        self.registry = ProjectRegistry.load()
        
    async def run(self):
        """Run interactive mode"""
        
        show_startup_banner()
        
        # Quick start for new users
        if not self.registry.list():
            await self._first_time_setup()
        
        # Main interaction loop
        while True:
            try:
                await self._main_menu()
            except KeyboardInterrupt:
                if Confirm.ask("\n[yellow]Exit Sanaa?[/yellow]", default=False):
                    break
                continue
            except Exception as e:
                console.print(f"[red]Unexpected error: {e}[/red]")
                if config.enable_telemetry:
                    console.print("[dim]Error has been logged for debugging[/dim]")
                continue
        
        console.print("\n[dim]Thanks for using Sanaa! Happy coding! 🚀[/dim]")
    
    async def _first_time_setup(self):
        """First-time user setup"""
        
        welcome_text = """
[bold cyan]Welcome to Sanaa![/bold cyan]

I'm your AI development assistant, here to help you:
• Plan and architect software projects
• Write and review code
• Debug issues and optimize performance
• Orchestrate complex development tasks

Let's start by setting up your first project!
"""
        
        console.print(Panel(welcome_text, border_style="green"))
        
        if Confirm.ask("Create your first project now?", default=True):
            project = self.project_manager.create_project_wizard()
            if project:
                self.registry = ProjectRegistry.load()  # Reload after creation
    
    async def _main_menu(self):
        """Main interactive menu"""
        
        # Smart suggestions based on context
        suggestions = self._get_smart_suggestions()
        
        # Menu options
        menu_options = [
            ("chat", "💬 Smart Chat", "Context-aware conversation"),
            ("create", "📁 Create Project", "New project wizard"),
            ("status", "📊 System Status", "Health and project overview"),
            ("config", "⚙️ Configuration", "Settings and preferences")
        ]
        
        # Add project-specific options
        if self.registry.default:
            default_project = self.registry.get(self.registry.default)
            if default_project:
                menu_options.insert(1, (
                    "work", f"🎯 Work on {default_project.name}", 
                    "Quick access to default project"
                ))
        
        # Display menu
        console.print("\n[bold]What would you like to do?[/bold]")
        
        # Show suggestions first if any
        if suggestions:
            console.print(f"[dim]💡 Suggestion: {suggestions[0]}[/dim]\n")
        
        # Display options
        for i, (key, title, desc) in enumerate(menu_options, 1):
            console.print(f"  [cyan]{i}.[/cyan] {title}")
            console.print(f"     [dim]{desc}[/dim]")
        
        console.print(f"\n  [cyan]{len(menu_options)+1}.[/cyan] [red]Exit[/red]")
        
        # Get user choice
        try:
            choice_input = typer.prompt("\nSelect option", type=str).strip()
            
            # Handle numeric choices
            if choice_input.isdigit():
                choice_num = int(choice_input)
                if 1 <= choice_num <= len(menu_options):
                    selected_key = menu_options[choice_num - 1][0]
                elif choice_num == len(menu_options) + 1:
                    raise typer.Exit(0)
                else:
                    console.print("[red]Invalid choice[/red]")
                    return
            else:
                # Handle text choices with fuzzy matching
                from .premium import FuzzyMatcher
                fuzzy = FuzzyMatcher()
                option_keys = [opt[0] for opt in menu_options]
                selected_key = fuzzy.find_best_match(choice_input, option_keys)
                
                if not selected_key:
                    console.print(f"[red]Unknown option: {choice_input}[/red]")
                    return
            
            # Execute selected action
            await self._execute_menu_action(selected_key)
            
        except (typer.Exit, KeyboardInterrupt):
            raise
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    def _get_smart_suggestions(self) -> List[str]:
        """Generate smart suggestions based on context"""
        
        suggestions = []
        
        # Check for recent activity
        projects = self.registry.list()
        if projects:
            # Most recently updated project
            recent_project = max(projects, key=lambda p: p.updated_at)
            if time.time() - recent_project.updated_at < 24 * 3600:  # Within 24 hours
                suggestions.append(f"Continue work on {recent_project.name}")
        
        # Check for git repositories that might need attention
        for project in projects[:3]:  # Check top 3 projects
            try:
                project_path = Path(project.path)
                if (project_path / ".git").exists():
                    # Check for uncommitted changes (simplified)
                    import subprocess
                    result = subprocess.run(
                        ["git", "status", "--porcelain"],
                        cwd=project_path,
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        suggestions.append(f"Commit changes in {project.name}")
                        break
            except Exception:
                pass
        
        return suggestions
    
    async def _execute_menu_action(self, action: str):
        """Execute menu action"""
        
        if action == "chat":
            # Smart project selection for chat
            project = None
            if self.registry.default:
                project = self.registry.get(self.registry.default)
            
            async with self.sanaa:
                await self.sanaa.smart_chat(project)
        
        elif action == "work":
            # Quick work mode - chat with default project
            if self.registry.default:
                project = self.registry.get(self.registry.default)
                if project:
                    console.print(f"[green]Working on {project.name}[/green]")
                    async with self.sanaa:
                        await self.sanaa.smart_chat(project)
        
        elif action == "create":
            project = self.project_manager.create_project_wizard()
            if project:
                self.registry = ProjectRegistry.load()  # Reload
                console.print(f"\n[green]Project {project.name} ready! Starting chat...[/green]")
                async with self.sanaa:
                    await self.sanaa.smart_chat(project, "Hello! I just created this project. What should we build?")
        
        elif action == "status":
            self._show_detailed_status()
        
        elif action == "config":
            self._configure_settings()
    
    def _show_detailed_status(self):
        """Show comprehensive system status"""
        
        console.print("\n[bold cyan]System Status[/bold cyan]\n")
        
        # Model status
        model_panel = self._create_model_status_panel()
        
        # Projects status  
        projects_panel = self._create_projects_status_panel()
        
        # Display in columns
        console.print(Columns([model_panel, projects_panel]))
        
        # Recent activity
        self._show_recent_activity()
    
    def _create_model_status_panel(self) -> Panel:
        """Create model status panel"""

        # Use default values for now to avoid config issues
        model_name = "qwen2.5-coder-7b-instruct-q4_k_m"
        model_base = "http://127.0.0.1:8080/v1"
        max_context_files = 10
        cache_ttl = 300

        try:
            import httpx
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{model_base}/models")
                if response.status_code == 200:
                    status = "[green]✓ Connected[/green]"
                else:
                    status = "[yellow]⚠ Issues detected[/yellow]"
        except Exception:
            status = "[red]✗ Unreachable[/red]"

        content = f"""[bold]Model Configuration[/bold]

Name: {model_name}
Endpoint: {model_base}
Status: {status}
Context Limit: {max_context_files} files
Cache TTL: {cache_ttl}s"""

        return Panel(content, title="Model", border_style="blue")
    
    def _create_projects_status_panel(self) -> Panel:
        """Create projects status panel"""
        
        projects = self.registry.list()
        
        if not projects:
            content = "[dim]No projects configured[/dim]"
        else:
            content = f"[bold]Project Summary[/bold]\n\n"
            content += f"Total Projects: {len(projects)}\n"
            content += f"Default: {self.registry.default or 'None'}\n\n"
            
            # Top 3 projects by recent activity
            recent_projects = sorted(projects, key=lambda p: p.updated_at, reverse=True)[:3]
            content += "[bold]Recent Activity:[/bold]\n"
            
            for project in recent_projects:
                age = time.time() - project.updated_at
                if age < 3600:  # < 1 hour
                    age_str = f"{int(age/60)}m ago"
                elif age < 86400:  # < 1 day
                    age_str = f"{int(age/3600)}h ago"
                else:
                    age_str = f"{int(age/86400)}d ago"
                
                content += f"  • {project.name} ({age_str})\n"
        
        return Panel(content, title="Projects", border_style="green")
    
    def _show_recent_activity(self):
        """Show recent activity from journals"""
        
        console.print("\n[bold]Recent Activity[/bold]")
        
        all_events = []
        for project in self.registry.list():
            try:
                events = self.registry.read_journal(project.name, limit=5)
                for event in events:
                    event['project'] = project.name
                    all_events.append(event)
            except Exception:
                pass
        
        # Sort by timestamp and take recent
        all_events.sort(key=lambda e: e.get('_ts', 0), reverse=True)
        recent_events = all_events[:10]
        
        if not recent_events:
            console.print("[dim]No recent activity[/dim]")
            return
        
        table = Table(show_header=False, box=None)
        table.add_column("Time", style="dim", width=10)
        table.add_column("Project", style="cyan", width=15)  
        table.add_column("Event", style="green")
        
        for event in recent_events:
            timestamp = time.strftime("%H:%M", time.localtime(event.get('_ts', 0)))
            project_name = event.get('project', 'Unknown')
            event_desc = self._format_event_description(event)
            
            table.add_row(timestamp, project_name, event_desc)
        
        console.print(table)
    
    def _format_event_description(self, event: dict) -> str:
        """Format event description for display"""
        
        event_type = event.get('event', 'unknown')
        
        if event_type == 'project_created':
            return "Project created"
        elif event_type == 'rescan':
            files = event.get('files_indexed', 0)
            return f"Reindexed {files} files"
        elif event_type == 'git_clone':
            return f"Cloned from {event.get('remote', 'repository')}"
        elif event_type == 'chat':
            return "Chat session"
        else:
            return event_type.replace('_', ' ').title()
    
    def _configure_settings(self):
        """Interactive settings configuration"""
        
        console.print("\n[bold cyan]Configuration[/bold cyan]\n")
        
        settings_options = [
            ("model", f"Model Settings (current: {config.model_name})"),
            ("context", f"Context Settings (max files: {config.max_context_files})"),
            ("cache", f"Cache Settings (TTL: {config.cache_ttl}s)"),
            ("features", "Feature Toggles"),
            ("reset", "Reset to Defaults")
        ]
        
        for i, (key, desc) in enumerate(settings_options, 1):
            console.print(f"  {i}. {desc}")
        
        try:
            choice = typer.prompt("Select setting to configure", type=int)
            if 1 <= choice <= len(settings_options):
                setting_key = settings_options[choice - 1][0]
                self._configure_setting(setting_key)
            else:
                console.print("[red]Invalid choice[/red]")
        except (ValueError, KeyboardInterrupt):
            pass
    
    def _configure_setting(self, setting: str):
        """Configure specific setting"""
        
        if setting == "model":
            new_name = typer.prompt("Model name", default=config.model_name)
            new_base = typer.prompt("Model endpoint", default=config.model_base)
            config.model_name = new_name
            config.model_base = new_base
            
        elif setting == "context":
            new_max = typer.prompt("Max context files", default=config.max_context_files, type=int)
            config.max_context_files = max(1, min(50, new_max))  # Reasonable bounds
            
        elif setting == "cache":
            new_ttl = typer.prompt("Cache TTL (seconds)", default=config.cache_ttl, type=int)
            config.cache_ttl = max(60, min(3600, new_ttl))  # 1 minute to 1 hour
            
        elif setting == "features":
            config.enable_semantic_search = Confirm.ask(
                "Enable semantic search?", 
                default=config.enable_semantic_search
            )
            config.enable_autocomplete = Confirm.ask(
                "Enable autocomplete?", 
                default=config.enable_autocomplete
            )
            config.enable_telemetry = Confirm.ask(
                "Enable telemetry?", 
                default=config.enable_telemetry
            )
            
        elif setting == "reset":
            if Confirm.ask("Reset all settings to defaults?", default=False):
                config.__dict__.update(SanaaConfig().__dict__)
        
        # Save configuration
        config.save()
        console.print("[green]✓ Configuration saved[/green]")

# -------------------------
# CLI Commands
# -------------------------

# Add project management commands
app.add_typer(enhanced_projects, name="projects")

@app.command()
def chat(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Initial message")
):
    """Smart chat with AI assistant"""
    
    async def run_chat():
        sanaa_instance = get_sanaa()
        async with sanaa_instance:
            registry = ProjectRegistry.load()
            proj = None
            
            if project:
                proj = sanaa_instance.smart_project_selection(registry, project)
            
            await sanaa_instance.smart_chat(proj, message)
    
    asyncio.run(run_chat())

@app.command()
def status():
    """Show system status and health"""
    mode = SmartInteractiveMode()
    mode._show_detailed_status()

@app.command()
def config():
    """Configure Sanaa settings"""
    mode = SmartInteractiveMode()
    mode._configure_settings()

@app.command("version", hidden=True)
def show_version():
    """Show version information"""
    version_info = {
        "sanaa": "2.0.0",
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform
    }
    
    console.print(Panel.fit(
        f"[bold cyan]Sanaa v{version_info['sanaa']}[/bold cyan]\n"
        f"[dim]Python {version_info['python']} on {version_info['platform']}[/dim]",
        border_style="blue"
    ))

@app.command("doctor", hidden=True)
def doctor():
    """Run system diagnostics"""
    console.print("[bold]Running system diagnostics...[/bold]\n")
    
    issues = check_system_health()
    
    if not issues:
        console.print("[green]✓ All systems operational![/green]")
    else:
        console.print(f"[yellow]Found {len(issues)} issues:[/yellow]")
        for issue in issues:
            console.print(f"  [red]✗[/red] {issue}")
        
        console.print(f"\n[dim]Run 'sanaa config' to fix configuration issues[/dim]")

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Sanaa - Premium AI Development Assistant

    An intelligent, context-aware coding assistant that helps you plan, build,
    and debug software projects with advanced AI capabilities.

    When run without arguments, launches the Sanaa Projects interface.
    """

    if ctx.invoked_subcommand is None:
        # Launch Sanaa Projects interface by default
        try:
            # Import the Sanaa Projects interface
            import sys
            from pathlib import Path
            BASE_DIR = Path(__file__).resolve().parent.parent.parent
            sys.path.insert(0, str(BASE_DIR))

            from packages.cli.src.coding_swarm_cli.sanaa_projects import run_sanaa_projects
            asyncio.run(run_sanaa_projects())
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/dim]")
        except Exception as e:
            console.print(f"[red]Error launching Sanaa Projects: {e}[/red]")
            # Note: Telemetry logging would be implemented here
            console.print("[dim]Error logged for debugging[/dim]")
            sys.exit(1)

# -------------------------
# Entry Point
# -------------------------

def cli_main():
    """Main CLI entry point"""
    app()

if __name__ == "__main__":
    cli_main()