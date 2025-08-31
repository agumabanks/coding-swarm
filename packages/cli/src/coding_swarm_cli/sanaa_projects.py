"""
Sanaa Projects - Comprehensive Project Management & Coding Swarm Interface
A self-contained coding assistant with persistent memory and multi-framework support
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json
import time
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import subprocess

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.align import Align
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.status import Status
from rich.tree import Tree
from rich.layout import Layout
from rich.markdown import Markdown
from rich.syntax import Syntax

from coding_swarm_core import (
    ProjectRegistry, Project, template_manager,
    SmartContextAnalyzer, context_analyzer
)
from coding_swarm_agents import create_agent


@dataclass
class WorkSession:
    """Represents a work session with persistent state"""
    project_name: str
    agent_type: str
    start_time: float
    last_activity: float
    current_task: Optional[str] = None
    completed_tasks: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    stopping_point: Optional[str] = None
    context_state: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Get session duration in minutes"""
        return (self.last_activity - self.start_time) / 60

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'project_name': self.project_name,
            'agent_type': self.agent_type,
            'start_time': self.start_time,
            'last_activity': self.last_activity,
            'current_task': self.current_task,
            'completed_tasks': self.completed_tasks,
            'notes': self.notes,
            'stopping_point': self.stopping_point,
            'context_state': self.context_state
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkSession':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class SanaaProject:
    """Enhanced project with work tracking"""
    project: Project
    work_sessions: List[WorkSession] = field(default_factory=list)
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    context_cache: Dict[str, Any] = field(default_factory=dict)
    last_accessed: float = field(default_factory=time.time)

    @property
    def active_session(self) -> Optional[WorkSession]:
        """Get currently active session"""
        for session in reversed(self.work_sessions):
            if session.stopping_point is None:
                return session
        return None

    def start_session(self, agent_type: str, task: Optional[str] = None) -> WorkSession:
        """Start a new work session"""
        session = WorkSession(
            project_name=self.project.name,
            agent_type=agent_type,
            start_time=time.time(),
            last_activity=time.time(),
            current_task=task
        )
        self.work_sessions.append(session)
        return session

    def end_session(self, stopping_point: Optional[str] = None):
        """End the current active session"""
        session = self.active_session
        if session:
            session.last_activity = time.time()
            session.stopping_point = stopping_point

    def add_note(self, note: str):
        """Add a note to the current session with enhanced context"""
        session = self.active_session
        if session:
            timestamp = datetime.now().isoformat()
            enhanced_note = f"{timestamp}: {note}"

            # Add context information
            if hasattr(self, 'project') and self.project:
                enhanced_note += f" | Project: {self.project.name}"

            session.notes.append(enhanced_note)
            session.last_activity = time.time()

            # Auto-save memory after adding note
            if len(session.notes) % 5 == 0:  # Save every 5 notes
                # This will be handled by the manager
                pass

    def get_session_summary(self, session: WorkSession) -> Dict[str, Any]:
        """Get comprehensive session summary for debugging and analysis"""
        return {
            'session_id': f"{session.project_name}_{int(session.start_time)}",
            'agent_type': session.agent_type,
            'duration_minutes': session.duration,
            'tasks_completed': len(session.completed_tasks),
            'notes_count': len(session.notes),
            'last_activity': datetime.fromtimestamp(session.last_activity).isoformat(),
            'is_active': session.stopping_point is None,
            'current_task': session.current_task,
            'stopping_point': session.stopping_point,
            'efficiency_score': self._calculate_efficiency_score(session)
        }

    def _calculate_efficiency_score(self, session: WorkSession) -> float:
        """Calculate session efficiency score for performance analysis"""
        if session.duration == 0:
            return 0.0

        # Factors: tasks per minute, notes per minute, session completion
        tasks_per_minute = len(session.completed_tasks) / session.duration
        notes_per_minute = len(session.notes) / session.duration
        completion_bonus = 1.0 if session.stopping_point else 0.5

        # Weighted score
        score = (tasks_per_minute * 0.4 + notes_per_minute * 0.3 + completion_bonus * 0.3)
        return min(10.0, max(0.0, score))  # Clamp between 0-10

    def optimize_memory(self):
        """Optimize memory usage for this project"""
        # Remove duplicate notes
        for session in self.work_sessions:
            seen_notes = set()
            unique_notes = []
            for note in session.notes:
                if note not in seen_notes:
                    unique_notes.append(note)
                    seen_notes.add(note)
            session.notes = unique_notes

        # Compress old context cache
        cutoff_time = time.time() - (7 * 24 * 3600)  # 7 days
        self.context_cache = {
            key: value for key, value in self.context_cache.items()
            if isinstance(value, dict) and value.get('timestamp', 0) > cutoff_time
        }

        # Limit milestones
        if len(self.milestones) > 20:
            self.milestones = self.milestones[-20:]  # Keep last 20

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for debugging and optimization"""
        total_sessions = len(self.work_sessions)
        active_sessions = len([s for s in self.work_sessions if s.stopping_point is None])
        completed_sessions = total_sessions - active_sessions

        total_duration = sum(s.duration for s in self.work_sessions)
        avg_session_duration = total_duration / total_sessions if total_sessions > 0 else 0

        total_tasks = sum(len(s.completed_tasks) for s in self.work_sessions)
        total_notes = sum(len(s.notes) for s in self.work_sessions)

        return {
            'project_name': self.project.name if self.project else 'Unknown',
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'completed_sessions': completed_sessions,
            'avg_session_duration': avg_session_duration,
            'total_tasks_completed': total_tasks,
            'total_notes': total_notes,
            'tasks_per_session': total_tasks / total_sessions if total_sessions > 0 else 0,
            'notes_per_session': total_notes / total_sessions if total_sessions > 0 else 0,
            'memory_usage': len(self.work_sessions) + len(self.milestones) + len(self.context_cache),
            'last_accessed': datetime.fromtimestamp(self.last_accessed).isoformat()
        }


class SanaaProjectsManager:
    """Enhanced project management with intelligent memory and auto-healing"""

    def __init__(self):
        self.console = Console()
        self.project_registry = ProjectRegistry.load()
        self.sanaa_projects: Dict[str, SanaaProject] = {}
        self.memory_file = Path.home() / ".sanaa" / "projects_memory.json"
        self.health_file = Path.home() / ".sanaa" / "system_health.json"
        self.cache_file = Path.home() / ".sanaa" / "memory_cache.json"

        # Memory optimization settings
        self.max_memory_age = 30 * 24 * 3600  # 30 days
        self.max_sessions_per_project = 50
        self.compression_threshold = 1000  # Compress after this many entries

        # Auto-healing settings
        self.last_health_check = 0
        self.health_check_interval = 300  # 5 minutes
        self.auto_heal_enabled = True

        # Load existing projects and memory
        self._load_memory()
        self._load_cache()
        self._sync_projects()
        self._perform_health_check()

    def _load_memory(self):
        """Load persistent memory"""
        if self.memory_file.exists():
            try:
                data = json.loads(self.memory_file.read_text())

                for project_name, project_data in data.get('projects', {}).items():
                    # Reconstruct SanaaProject
                    project = self.project_registry.get(project_name)
                    if project:
                        sanaa_project = SanaaProject(
                            project=project,
                            work_sessions=[
                                WorkSession.from_dict(session_data)
                                for session_data in project_data.get('work_sessions', [])
                            ],
                            milestones=project_data.get('milestones', []),
                            context_cache=project_data.get('context_cache', {}),
                            last_accessed=project_data.get('last_accessed', time.time())
                        )
                        self.sanaa_projects[project_name] = sanaa_project

            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load project memory: {e}[/yellow]")

    def _load_cache(self):
        """Load memory cache for performance optimization"""
        if self.cache_file.exists():
            try:
                cache_data = json.loads(self.cache_file.read_text())
                self._restore_from_cache(cache_data)
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load memory cache: {e}[/yellow]")

    def _save_cache(self):
        """Save memory cache for performance"""
        try:
            cache_data = self._prepare_cache_data()
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps(cache_data, indent=2, default=str))
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not save memory cache: {e}[/yellow]")

    def _prepare_cache_data(self) -> Dict[str, Any]:
        """Prepare optimized cache data"""
        cache_data = {
            'projects': {},
            'last_updated': time.time(),
            'stats': self._get_memory_stats()
        }

        for name, sanaa_project in self.sanaa_projects.items():
            # Only cache recent and active sessions
            recent_sessions = [
                session for session in sanaa_project.work_sessions
                if time.time() - session.last_activity < self.max_memory_age
            ][:10]  # Keep only last 10 recent sessions

            cache_data['projects'][name] = {
                'work_sessions': [session.to_dict() for session in recent_sessions],
                'milestones': sanaa_project.milestones[-5:],  # Keep last 5 milestones
                'context_cache': sanaa_project.context_cache,
                'last_accessed': sanaa_project.last_accessed
            }

        return cache_data

    def _restore_from_cache(self, cache_data: Dict[str, Any]):
        """Restore projects from cache"""
        for project_name, project_data in cache_data.get('projects', {}).items():
            if project_name in self.sanaa_projects:
                sanaa_project = self.sanaa_projects[project_name]
                # Merge cached sessions with existing ones
                cached_sessions = [
                    WorkSession.from_dict(session_data)
                    for session_data in project_data.get('work_sessions', [])
                ]
                sanaa_project.work_sessions.extend(cached_sessions)

    def _get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        total_sessions = sum(len(p.work_sessions) for p in self.sanaa_projects.values())
        total_milestones = sum(len(p.milestones) for p in self.sanaa_projects.values())
        active_sessions = sum(1 for p in self.sanaa_projects.values() if p.active_session)

        return {
            'total_projects': len(self.sanaa_projects),
            'total_sessions': total_sessions,
            'total_milestones': total_milestones,
            'active_sessions': active_sessions,
            'memory_file_size': self.memory_file.stat().st_size if self.memory_file.exists() else 0,
            'cache_file_size': self.cache_file.stat().st_size if self.cache_file.exists() else 0
        }

    def _perform_health_check(self):
        """Perform comprehensive system health check"""
        current_time = time.time()

        # Only check health periodically
        if current_time - self.last_health_check < self.health_check_interval:
            return

        self.last_health_check = current_time
        issues = []

        # Check memory file integrity
        if self.memory_file.exists():
            try:
                data = json.loads(self.memory_file.read_text())
                if 'projects' not in data:
                    issues.append("Memory file corrupted - missing projects section")
            except Exception as e:
                issues.append(f"Memory file corrupted: {e}")

        # Check for orphaned sessions
        for project_name, sanaa_project in self.sanaa_projects.items():
            orphaned_sessions = [
                session for session in sanaa_project.work_sessions
                if session.stopping_point is None and
                time.time() - session.last_activity > 24 * 3600  # 24 hours
            ]
            if orphaned_sessions:
                issues.append(f"Project '{project_name}' has {len(orphaned_sessions)} orphaned sessions")

        # Auto-heal if enabled
        if issues and self.auto_heal_enabled:
            self._auto_heal_issues(issues)

        # Save health status
        self._save_health_status(issues)

    def _auto_heal_issues(self, issues: List[str]):
        """Auto-heal detected issues"""
        healed_count = 0

        for issue in issues:
            if "orphaned sessions" in issue:
                # Clean up orphaned sessions
                for sanaa_project in self.sanaa_projects.values():
                    sanaa_project.work_sessions = [
                        session for session in sanaa_project.work_sessions
                        if not (session.stopping_point is None and
                               time.time() - session.last_activity > 24 * 3600)
                    ]
                healed_count += 1
            elif "Memory file corrupted" in issue:
                # Recreate memory file
                self._save_memory()
                healed_count += 1

        if healed_count > 0:
            self.console.print(f"[green]✓ Auto-healed {healed_count} issues[/green]")

    def _save_health_status(self, issues: List[str]):
        """Save health status for monitoring"""
        health_data = {
            'timestamp': time.time(),
            'issues': issues,
            'memory_stats': self._get_memory_stats(),
            'system_info': {
                'python_version': f"{sys.version_info.major}.{sys.version_info.minor}",
                'platform': sys.platform
            }
        }

        try:
            self.health_file.parent.mkdir(parents=True, exist_ok=True)
            self.health_file.write_text(json.dumps(health_data, indent=2, default=str))
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not save health status: {e}[/yellow]")

    def _save_memory(self):
        """Enhanced memory saving with optimization"""
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)

        # Clean up old sessions before saving
        self._cleanup_old_sessions()

        data = {
            'projects': {},
            'last_updated': time.time(),
            'stats': self._get_memory_stats()
        }

        for name, sanaa_project in self.sanaa_projects.items():
            # Limit sessions per project
            recent_sessions = sanaa_project.work_sessions[-self.max_sessions_per_project:]

            data['projects'][name] = {
                'work_sessions': [session.to_dict() for session in recent_sessions],
                'milestones': sanaa_project.milestones,
                'context_cache': sanaa_project.context_cache,
                'last_accessed': sanaa_project.last_accessed
            }

        # Compress if too large
        json_str = json.dumps(data, indent=2, default=str)
        if len(json_str) > self.compression_threshold:
            # For now, just save as-is. Could implement compression later
            pass

        self.memory_file.write_text(json_str)

        # Update cache
        self._save_cache()

    def _cleanup_old_sessions(self):
        """Clean up old and inactive sessions"""
        cutoff_time = time.time() - self.max_memory_age

        for sanaa_project in self.sanaa_projects.values():
            # Keep recent sessions and active ones
            sanaa_project.work_sessions = [
                session for session in sanaa_project.work_sessions
                if session.last_activity > cutoff_time or session.stopping_point is None
            ]

            # Clean up old context cache entries
            sanaa_project.context_cache = {
                key: value for key, value in sanaa_project.context_cache.items()
                if isinstance(value, dict) and value.get('timestamp', 0) > cutoff_time
            }

    def _sync_projects(self):
        """Sync with project registry"""
        for project in self.project_registry.list():
            if project.name not in self.sanaa_projects:
                self.sanaa_projects[project.name] = SanaaProject(project=project)

    def get_sanaa_project(self, project_name: str) -> Optional[SanaaProject]:
        """Get SanaaProject by name"""
        return self.sanaa_projects.get(project_name)

    def create_project(self, name: str, template: str, path: str) -> SanaaProject:
        """Create a new project from template"""
        # Create project using template manager
        project = template_manager.create_project_from_template(template, name, path)

        # Register with project registry
        self.project_registry.add(project)

        # Create SanaaProject
        sanaa_project = SanaaProject(project=project)
        self.sanaa_projects[name] = sanaa_project

        # Save memory
        self._save_memory()

        return sanaa_project

    def list_projects(self) -> List[SanaaProject]:
        """List all SanaaProjects with work status"""
        return list(self.sanaa_projects.values())


class SanaaProjectsInterface:
    """Main interface for Sanaa Projects system"""

    def __init__(self):
        self.console = Console()
        self.manager = SanaaProjectsManager()
        self.current_project: Optional[SanaaProject] = None

    async def show_main_menu(self):
        """Show the main Sanaa Projects interface"""
        while True:
            self._clear_screen()
            self._show_header()

            # Show current project status
            if self.current_project:
                self._show_current_project_status()

            # Show main menu
            self._show_main_menu_options()

            # Get user input
            choice = input().strip()

            if choice == "1":
                self._handle_project_management()
            elif choice == "2":
                self._handle_coding_session()
            elif choice == "3":
                self._handle_debugging()
            elif choice == "4":
                self._handle_planning()
            elif choice == "5":
                await self._handle_qa_assistance()
            elif choice == "6":
                self._show_system_status()
            elif choice == "7":
                self._run_llm_connection_test()
            elif choice == "8":
                self._perform_auto_healing()
            elif choice == "9":
                self._show_help()
            elif choice.lower() in ["q", "quit", "exit"]:
                self._handle_exit()
                break
            else:
                self.console.print("[red]Invalid choice. Please try again.[/red]")
                time.sleep(1)

    def _clear_screen(self):
        """Clear the screen"""
        self.console.clear()

    def _show_header(self):
        """Show the Sanaa Projects header"""
        header_text = Text("🚀 Sanaa Projects", style="bold cyan")
        header_text.append(" • AI-Powered Development Assistant", style="dim")

        header_panel = Panel(
            Align.center(header_text),
            border_style="cyan",
            padding=(1, 2)
        )

        self.console.print(header_panel)
        self.console.print()

    def _show_current_project_status(self):
        """Show current project status"""
        project = self.current_project
        if not project:
            return

        # Project info
        status_table = Table(title=f"📁 Current Project: {project.project.name}")
        status_table.add_column("Metric", style="cyan")
        status_table.add_column("Value", style="green")

        status_table.add_row("Path", project.project.path)
        status_table.add_row("Framework", self._detect_framework(project.project))
        status_table.add_row("Files", str(len(project.project.files)))
        status_table.add_row("Work Sessions", str(len(project.work_sessions)))

        # Active session info
        active_session = project.active_session
        if active_session:
            status_table.add_row("Active Session", f"{active_session.agent_type} ({active_session.duration:.1f}min)")
            if active_session.current_task:
                status_table.add_row("Current Task", active_session.current_task)
        else:
            status_table.add_row("Active Session", "None")

        self.console.print(status_table)
        self.console.print()

    def _show_main_menu_options(self):
        """Show main menu options in Firebase CLI style"""
        self.console.print("\n[bold]What would you like to do?[/bold]\n")

        options = [
            ("1", "📁 Project Management", "Create, select, and manage projects"),
            ("2", "💻 Start Coding Session", "Begin development with AI assistance"),
            ("3", "🔍 Debug & Fix Issues", "Analyze and fix code problems"),
            ("4", "📋 Planning & Architecture", "Design and plan your project"),
            ("5", "❓ Q&A Assistance", "Get help and answers from AI"),
            ("6", "📊 System Status", "View system and project status"),
            ("7", "🧪 LLM Connection Test", "Test AI model connectivity"),
            ("8", "🔧 Auto-Healing", "Automatically fix system issues"),
            ("9", "❓ Help", "Show help and documentation"),
            ("q", "🚪 Exit", "Quit Sanaa Projects")
        ]

        for i, (key, option, desc) in enumerate(options, 1):
            self.console.print(f"  [cyan]{i}.[/cyan] {option}")
            self.console.print(f"     [dim]{desc}[/dim]")

        self.console.print(f"\n[dim]Choose an option (1-{len(options)} or 'q' to exit):[/dim]", end=" ")

    def _handle_project_management(self):
        """Handle project management operations"""
        self._clear_screen()
        self.console.print("[bold cyan]📁 Project Management[/bold cyan]\n")

        projects = self.manager.list_projects()

        if not projects:
            self.console.print("[yellow]No projects found. Let's create your first project![/yellow]\n")

        # Show existing projects
        if projects:
            self._show_projects_table(projects)

        # Project management options
        self.console.print("\n[bold]Project Management Options:[/bold]\n")

        options = [
            ("1", "Create New Project", "Start a new project from template"),
            ("2", "Select Existing Project", "Work on an existing project"),
            ("3", "View Project Details", "See detailed project information"),
            ("4", "Delete Project", "Remove a project"),
            ("b", "Back to Main Menu", "Return to main menu")
        ]

        for i, (key, option, desc) in enumerate(options, 1):
            self.console.print(f"  [cyan]{i}.[/cyan] {option}")
            self.console.print(f"     [dim]{desc}[/dim]")

        self.console.print(f"\n[dim]Choose an option (1-{len(options)} or 'b' to go back):[/dim]", end=" ")
        choice = input().strip()

        if choice == "1":
            self._create_new_project()
        elif choice == "2":
            self._select_project(projects)
        elif choice == "3":
            self._view_project_details(projects)
        elif choice == "4":
            self._delete_project(projects)

    def _show_projects_table(self, projects: List[SanaaProject]):
        """Show projects in a table"""
        table = Table(title="Your Projects")
        table.add_column("Name", style="cyan")
        table.add_column("Framework", style="green")
        table.add_column("Path", style="blue")
        table.add_column("Sessions", justify="right", style="yellow")
        table.add_column("Last Active", style="magenta")

        for sanaa_project in projects:
            project = sanaa_project.project
            framework = self._detect_framework(project)
            sessions_count = len(sanaa_project.work_sessions)

            # Calculate last active time
            if sanaa_project.work_sessions:
                last_session = max(sanaa_project.work_sessions, key=lambda s: s.last_activity)
                last_active = datetime.fromtimestamp(last_session.last_activity).strftime("%Y-%m-%d %H:%M")
            else:
                last_active = "Never"

            table.add_row(
                project.name,
                framework.title(),
                project.path,
                str(sessions_count),
                last_active
            )

        self.console.print(table)
        self.console.print()

    def _create_new_project(self):
        """Create a new project with interactive selection"""
        self.console.print("[bold green]🏗️ Create New Project[/bold green]\n")

        # Get project details
        name = Prompt.ask("Project name")
        path = Prompt.ask("Project path", default=f"./{name}")

        # Show available frameworks with numbers
        frameworks = ["react", "laravel", "flutter"]
        templates = template_manager.list_available_templates()

        self.console.print("\n[bold]Choose a framework:[/bold]")
        for i, framework in enumerate(frameworks, 1):
            template_count = len(templates.get(framework, []))
            self.console.print(f"  [cyan]{i}.[/cyan] {framework.title()} ({template_count} templates)")

        # Framework selection with validation
        while True:
            try:
                framework_choice = IntPrompt.ask(
                    "\nChoose framework",
                    choices=[str(i) for i in range(1, len(frameworks) + 1)]
                )
                selected_framework = frameworks[framework_choice - 1]
                break
            except (ValueError, IndexError):
                self.console.print("[red]Invalid choice. Please select a valid option.[/red]")

        # Show templates for selected framework
        template_list = templates.get(selected_framework, [])
        self.console.print(f"\n[bold]{selected_framework.title()} Templates:[/bold]")

        for i, template in enumerate(template_list, 1):
            template_name = template.split(": ")[0]
            template_desc = template.split(": ")[1] if ": " in template else template
            self.console.print(f"  [cyan]{i}.[/cyan] {template_name}")
            self.console.print(f"     [dim]{template_desc}[/dim]")

        # Template selection
        if len(template_list) == 1:
            template_choice = template_list[0].split(": ")[0]
            self.console.print(f"\n[dim]Using only available template: {template_choice}[/dim]")
        else:
            while True:
                try:
                    template_choice_num = IntPrompt.ask(
                        "\nChoose template",
                        choices=[str(i) for i in range(1, len(template_list) + 1)]
                    )
                    template_choice = template_list[template_choice_num - 1].split(": ")[0]
                    break
                except (ValueError, IndexError):
                    self.console.print("[red]Invalid choice. Please select a valid template.[/red]")

        # Create project
        template_name = f"{selected_framework}-{template_choice.lower().replace(' ', '-').replace('.', '').replace('/', '-')}"
        try:
            sanaa_project = self.manager.create_project(name, template_name, path)
            self.current_project = sanaa_project

            self.console.print(f"\n[green]✓ Project '{name}' created successfully![/green]")
            self.console.print(f"[dim]Location: {path}[/dim]")
            self.console.print(f"[dim]Framework: {selected_framework.title()}[/dim]")
            self.console.print(f"[dim]Template: {template_choice}[/dim]")

        except Exception as e:
            self.console.print(f"\n[red]✗ Failed to create project: {e}[/red]")

        Prompt.ask("\nPress Enter to continue")

    def _select_project(self, projects: List[SanaaProject]):
        """Select an existing project with numeric selection"""
        if not projects:
            self.console.print("[yellow]No projects available to select.[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        self.console.print("[bold]Select a project:[/bold]\n")

        for i, sanaa_project in enumerate(projects, 1):
            project = sanaa_project.project
            framework = self._detect_framework(project)
            session_count = len(sanaa_project.work_sessions)
            self.console.print(f"[cyan]{i}.[/cyan] {project.name}")
            self.console.print(f"   [dim]Framework: {framework} • Sessions: {session_count} • Path: {project.path}[/dim]")

        # Add option to go back
        self.console.print(f"[cyan]{len(projects) + 1}.[/cyan] [yellow]Back to main menu[/yellow]")

        try:
            choice = IntPrompt.ask(
                "\nChoose project number",
                choices=[str(i) for i in range(1, len(projects) + 2)]
            )

            if choice == len(projects) + 1:
                return  # Go back to main menu

            self.current_project = projects[choice - 1]
            self.console.print(f"\n[green]✓ Selected project: {self.current_project.project.name}[/green]")
            self.console.print(f"[dim]Framework: {self._detect_framework(self.current_project.project)}[/dim]")

        except (ValueError, IndexError):
            self.console.print("[red]Invalid choice.[/red]")

        Prompt.ask("\nPress Enter to continue")

    def _detect_framework(self, project: Project) -> str:
        """Detect project framework"""
        project_path = Path(project.path)

        # Check for various framework indicators
        if (project_path / 'package.json').exists():
            try:
                package_data = json.loads((project_path / 'package.json').read_text())
                deps = package_data.get('dependencies', {})
                if 'react' in deps or 'next' in deps:
                    return 'react'
            except:
                pass

        if (project_path / 'artisan').exists():
            return 'laravel'

        if (project_path / 'pubspec.yaml').exists():
            return 'flutter'

        return 'unknown'

    def _handle_coding_session(self):
        """Handle coding session with AI assistance"""
        if not self.current_project:
            self.console.print("[yellow]Please select a project first.[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        self._clear_screen()
        self.console.print(f"[bold cyan]💻 Coding Session - {self.current_project.project.name}[/bold cyan]\n")

        # Detect framework and suggest agent
        framework = self._detect_framework(self.current_project.project)
        suggested_agent = self._get_suggested_agent(framework)

        self.console.print(f"[dim]Detected framework: {framework}[/dim]")
        self.console.print(f"[dim]Suggested agent: {suggested_agent}[/dim]\n")

        # Agent options
        agents = {
            "react": "React development specialist",
            "laravel": "Laravel backend specialist",
            "flutter": "Flutter mobile specialist",
            "coder": "General coding assistant",
            "advanced_debugger": "Advanced debugging specialist"
        }

        self.console.print("[bold]Available Agents:[/bold]")
        for i, (agent, desc) in enumerate(agents.items(), 1):
            marker = " ⭐" if agent == suggested_agent else ""
            self.console.print(f"[cyan]{i}.[/cyan] {agent.title()}{marker} - [dim]{desc}[/dim]")

        try:
            choice = IntPrompt.ask("\nChoose agent", choices=[str(i) for i in range(1, len(agents) + 1)])
            selected_agent = list(agents.keys())[choice - 1]

            # Start work session
            task = Prompt.ask("What would you like to work on?")
            session = self.current_project.start_session(selected_agent, task)

            self.console.print(f"\n[green]✓ Started {selected_agent} session for: {task}[/green]")

            # Launch agent interaction
            self._launch_agent_session(selected_agent, session)

        except (ValueError, IndexError):
            self.console.print("[red]Invalid choice.[/red]")

    def _get_suggested_agent(self, framework: str) -> str:
        """Get suggested agent for framework"""
        agent_map = {
            'react': 'react',
            'laravel': 'laravel',
            'flutter': 'flutter'
        }
        return agent_map.get(framework, 'coder')

    def _launch_agent_session(self, agent_type: str, session: WorkSession):
        """Launch an agent session"""
        self.console.print(f"\n[bold]Starting {agent_type} session...[/bold]")

        # Create agent
        context = {
            "project": self.current_project.project.path,
            "goal": session.current_task or "General development assistance"
        }

        try:
            agent = create_agent(agent_type, context)

            # Interactive session
            self.console.print("\n[dim]Type your requests or 'exit' to end session[/dim]")
            self.console.print("[dim]Type 'help' for available commands[/dim]\n")

            while True:
                user_input = Prompt.ask(f"[bold magenta]{agent_type}[/bold magenta]")

                if user_input.lower() in ['exit', 'quit', 'q']:
                    break
                elif user_input.lower() == 'help':
                    self._show_agent_help(agent_type)
                    continue
                elif user_input.lower() == 'status':
                    self._show_session_status(session)
                    continue

                # Process request
                with self.console.status(f"[bold green]Processing with {agent_type}...[/bold green]"):
                    success = agent.apply_patch(user_input)

                if success:
                    session.completed_tasks.append(user_input)
                    session.last_activity = time.time()
                    self.console.print("[green]✓ Task completed![/green]")
                else:
                    self.console.print("[yellow]⚠ Task encountered issues[/yellow]")

                # Auto-save
                self.manager._save_memory()

        except Exception as e:
            self.console.print(f"[red]Error launching agent: {e}[/red]")

        # End session
        self.current_project.end_session("Session ended by user")
        self.manager._save_memory()

    def _show_agent_help(self, agent_type: str):
        """Show help for specific agent"""
        help_text = {
            "react": """
React Agent Commands:
• component <name> - Create a React component
• hook <name> - Create a custom hook
• page <name> - Create a page component
• api <name> - Create API integration
• state <description> - Add state management
• style <description> - Add styling
• test <component> - Create tests
""",
            "laravel": """
Laravel Agent Commands:
• model <name> - Create an Eloquent model
• controller <name> - Create a controller
• migration <name> - Create a database migration
• request <name> - Create a form request
• resource <name> - Create an API resource
• policy <name> - Create an authorization policy
• seeder <name> - Create a database seeder
""",
            "flutter": """
Flutter Agent Commands:
• widget <name> - Create a widget
• provider <name> - Create a state provider
• model <name> - Create a data model
• service <name> - Create a service class
• screen <name> - Create a screen/page
• bloc <name> - Create a BLoC pattern
• test <widget> - Create widget tests
"""
        }

        help_content = help_text.get(agent_type, "General coding assistance available.")
        self.console.print(Panel(help_content, title=f"{agent_type.title()} Agent Help", border_style="blue"))

    def _show_session_status(self, session: WorkSession):
        """Show current session status"""
        status_table = Table(title="Session Status")
        status_table.add_column("Metric", style="cyan")
        status_table.add_column("Value", style="green")

        status_table.add_row("Agent", session.agent_type.title())
        status_table.add_row("Duration", f"{session.duration:.1f} minutes")
        status_table.add_row("Tasks Completed", str(len(session.completed_tasks)))
        status_table.add_row("Current Task", session.current_task or "None")

        if session.completed_tasks:
            status_table.add_row("Last Completed", session.completed_tasks[-1])

        self.console.print(status_table)

    def _handle_debugging(self):
        """Handle debugging operations"""
        if not self.current_project:
            self.console.print("[yellow]Please select a project first.[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        self.console.print(f"[bold cyan]🔍 Debugging - {self.current_project.project.name}[/bold cyan]\n")

        # Start debugging session
        session = self.current_project.start_session("debugger", "Debug and fix issues")

        try:
            agent = create_agent("advanced_debugger", {"project": self.current_project.project.path})

            with self.console.status("[bold green]Running comprehensive analysis...[/bold green]"):
                success = agent.apply_patch("analyze")

            if success:
                self.console.print("[green]✓ Debug analysis completed![/green]")
                session.completed_tasks.append("Debug analysis completed")
            else:
                self.console.print("[red]✗ Debug analysis failed[/red]")

        except Exception as e:
            self.console.print(f"[red]Error during debugging: {e}[/red]")

        # End session
        self.current_project.end_session("Debugging session completed")
        self.manager._save_memory()

        Prompt.ask("\nPress Enter to continue")

    def _handle_planning(self):
        """Handle planning and architecture"""
        if not self.current_project:
            self.console.print("[yellow]Please select a project first.[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        self.console.print(f"[bold cyan]📋 Planning - {self.current_project.project.name}[/bold cyan]\n")

        goal = Prompt.ask("What would you like to plan?")

        # Start planning session
        session = self.current_project.start_session("planner", f"Planning: {goal}")

        try:
            agent = create_agent("planner", {
                "project": self.current_project.project.path,
                "goal": goal
            })

            with self.console.status("[bold green]Creating comprehensive plan...[/bold green]"):
                plan_text = agent.plan()

            # Display plan
            self.console.print("\n[bold green]📋 Development Plan Generated:[/bold green]\n")
            self.console.print(Markdown(plan_text))

            session.completed_tasks.append(f"Planning completed: {goal}")

        except Exception as e:
            self.console.print(f"[red]Error during planning: {e}[/red]")

        # End session
        self.current_project.end_session("Planning session completed")
        self.manager._save_memory()

        Prompt.ask("\nPress Enter to continue")

    async def _handle_qa_assistance(self):
        """Handle Q&A assistance"""
        self.console.print("[bold cyan]❓ Q&A Assistance[/bold cyan]\n")

        question = Prompt.ask("What would you like to know?")

        # Use general coding agent for Q&A
        context = {"project": self.current_project.project.path if self.current_project else "."}

        try:
            agent = create_agent("coder", context)

            async with agent:
                with self.console.status("[bold green]Getting answer from AI...[/bold green]"):
                    answer = await agent._generate_response(
                        f"Please answer this question helpfully and directly: {question}",
                        "You are an expert coding assistant with deep knowledge of software development, best practices, and multiple programming frameworks."
                    )

                if answer and not answer.startswith("LLM"):
                    self.console.print(f"\n[cyan]AI Answer:[/cyan]")
                    self.console.print(Markdown(answer))
                else:
                    # Fallback response
                    fallback_answer = f"""Based on your question: '{question}'

I'm a comprehensive coding assistant system with support for React, Laravel, and Flutter development. I can help you with:

• Code generation and refactoring
• Debugging and issue resolution
• Project planning and architecture
• Best practices and recommendations
• Framework-specific guidance

For specific coding tasks, try starting a coding session with the appropriate agent!

**Note:** I'm currently connecting to your local AI models. Make sure your Llama.cpp servers are running on ports 8080-8083."""

                    self.console.print(f"\n[cyan]Answer:[/cyan] {fallback_answer}")

        except Exception as e:
            self.console.print(f"[red]Error getting answer: {e}[/red]")
            self.console.print("[yellow]Make sure your local AI models are running and accessible.[/yellow]")

        Prompt.ask("\nPress Enter to continue")

    def _show_system_status(self):
        """Show comprehensive system status with health checks"""
        self._clear_screen()
        self.console.print("[bold cyan]📊 System Status[/bold cyan]\n")

        # Perform health check
        health_issues = self._perform_system_health_check()

        # Show health status
        if not health_issues:
            self.console.print("[green]✅ System Health: All systems operational[/green]")
        else:
            self.console.print(f"[yellow]⚠️ System Health: {len(health_issues)} issues detected[/yellow]")
            for issue in health_issues:
                self.console.print(f"  [red]•[/red] {issue}")

        self.console.print()

        # Docker containers status
        self._show_docker_status()

        # Projects summary
        self._show_projects_summary()

        # Memory and sessions
        self._show_memory_stats()

        # LLM Connection status
        self._show_llm_status()

        # Performance metrics
        self._show_performance_metrics()

        Prompt.ask("\nPress Enter to continue")

    def _perform_system_health_check(self) -> List[str]:
        """Perform comprehensive system health check"""
        issues = []

        # Check Docker containers
        try:
            import subprocess
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                containers = result.stdout.strip().split('\n') if result.stdout.strip() else []
                sanaa_containers = [c for c in containers if 'coding-swarm' in c]

                if len(sanaa_containers) < 4:  # Expect 4 Sanaa containers
                    issues.append(f"Missing containers: expected 4, found {len(sanaa_containers)}")

                # Check for unhealthy containers
                for container in sanaa_containers:
                    health_result = subprocess.run(
                        ["docker", "inspect", "--format", "{{.State.Health.Status}}", container],
                        capture_output=True, text=True
                    )
                    if health_result.returncode == 0 and 'unhealthy' in health_result.stdout.lower():
                        issues.append(f"Container {container} is unhealthy")
            else:
                issues.append("Cannot access Docker daemon")

        except Exception as e:
            issues.append(f"Docker check failed: {e}")

        # Check LLM endpoints
        llm_issues = self._check_llm_endpoints()
        issues.extend(llm_issues)

        # Check memory system
        memory_issues = self._check_memory_system()
        issues.extend(memory_issues)

        # Check project integrity
        project_issues = self._check_project_integrity()
        issues.extend(project_issues)

        return issues

    def _check_llm_endpoints(self) -> List[str]:
        """Check LLM endpoint connectivity"""
        issues = []
        endpoints = [
            ("http://127.0.0.1:8080/v1/models", "API Model"),
            ("http://127.0.0.1:8081/v1/models", "Web Model"),
            ("http://127.0.0.1:8082/v1/models", "Mobile Model"),
            ("http://127.0.0.1:8083/v1/models", "Test Model")
        ]

        try:
            import httpx
            for url, name in endpoints:
                try:
                    with httpx.Client(timeout=5) as client:
                        response = client.get(url)
                        if response.status_code != 200:
                            issues.append(f"{name} endpoint returned status {response.status_code}")
                except Exception as e:
                    issues.append(f"{name} endpoint unreachable: {str(e)[:50]}")
        except ImportError:
            issues.append("httpx not available for LLM endpoint checks")

        return issues

    def _check_memory_system(self) -> List[str]:
        """Check memory system integrity"""
        issues = []

        # Check memory file
        memory_file = Path.home() / ".sanaa" / "projects_memory.json"
        if memory_file.exists():
            try:
                data = json.loads(memory_file.read_text())
                if 'projects' not in data:
                    issues.append("Memory file corrupted - missing projects section")
            except Exception as e:
                issues.append(f"Memory file corrupted: {e}")
        else:
            issues.append("Memory file does not exist")

        # Check for orphaned sessions
        for sanaa_project in self.manager.sanaa_projects.values():
            orphaned_sessions = [
                session for session in sanaa_project.work_sessions
                if session.stopping_point is None and
                time.time() - session.last_activity > 24 * 3600  # 24 hours
            ]
            if orphaned_sessions:
                issues.append(f"Project '{sanaa_project.project.name}' has {len(orphaned_sessions)} orphaned sessions")

        return issues

    def _check_project_integrity(self) -> List[str]:
        """Check project integrity"""
        issues = []

        for sanaa_project in self.manager.sanaa_projects.values():
            # Check if project still exists in registry
            if sanaa_project.project.name not in [p.name for p in self.manager.project_registry.list()]:
                issues.append(f"Project '{sanaa_project.project.name}' missing from registry")

            # Check for invalid paths
            if not Path(sanaa_project.project.path).exists():
                issues.append(f"Project path does not exist: {sanaa_project.project.path}")

        return issues

    def _show_llm_status(self):
        """Show LLM connection status"""
        self.console.print("[bold]🤖 LLM Status[/bold]")

        endpoints = [
            ("http://127.0.0.1:8080/v1/models", "API Model (Port 8080)"),
            ("http://127.0.0.1:8081/v1/models", "Web Model (Port 8081)"),
            ("http://127.0.0.1:8082/v1/models", "Mobile Model (Port 8082)"),
            ("http://127.0.0.1:8083/v1/models", "Test Model (Port 8083)")
        ]

        try:
            import httpx
            for url, name in endpoints:
                try:
                    with httpx.Client(timeout=3) as client:
                        response = client.get(url)
                        if response.status_code == 200:
                            self.console.print(f"  [green]✅[/green] {name}")
                        else:
                            self.console.print(f"  [yellow]⚠️[/yellow] {name} (Status: {response.status_code})")
                except Exception:
                    self.console.print(f"  [red]❌[/red] {name}")
        except ImportError:
            self.console.print("  [red]❌[/red] httpx not available for checks")

        self.console.print()

    def _show_performance_metrics(self):
        """Show system performance metrics"""
        self.console.print("[bold]⚡ Performance Metrics[/bold]")

        # Memory stats
        memory_stats = self.manager._get_memory_stats()
        self.console.print(f"  Projects: {memory_stats['total_projects']}")
        self.console.print(f"  Total Sessions: {memory_stats['total_sessions']}")
        self.console.print(f"  Active Sessions: {memory_stats['active_sessions']}")
        self.console.print(f"  Memory File Size: {memory_stats['memory_file_size'] / 1024:.1f} KB")

        # Project performance
        if self.manager.sanaa_projects:
            total_tasks = sum(
                len(session.completed_tasks)
                for sanaa_project in self.manager.sanaa_projects.values()
                for session in sanaa_project.work_sessions
            )
            self.console.print(f"  Total Tasks Completed: {total_tasks}")

        self.console.print()

    def _show_docker_status(self):
        """Show Docker containers status"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                self.console.print(Panel(
                    result.stdout,
                    title="[bold]Docker Containers[/bold]",
                    border_style="green"
                ))
            else:
                self.console.print("[red]Could not retrieve Docker status[/red]")

        except Exception as e:
            self.console.print(f"[red]Error checking Docker: {e}[/red]")

    def _show_projects_summary(self):
        """Show projects summary"""
        projects = self.manager.list_projects()

        summary_table = Table(title="Projects Summary")
        summary_table.add_column("Total Projects", style="cyan")
        summary_table.add_column("Active Sessions", style="green")
        summary_table.add_column("Total Sessions", style="yellow")
        summary_table.add_column("Completed Tasks", style="magenta")

        total_sessions = sum(len(p.work_sessions) for p in projects)
        active_sessions = sum(1 for p in projects if p.active_session)
        completed_tasks = sum(
            len(session.completed_tasks)
            for p in projects
            for session in p.work_sessions
        )

        summary_table.add_row(
            str(len(projects)),
            str(active_sessions),
            str(total_sessions),
            str(completed_tasks)
        )

        self.console.print(summary_table)

    def _show_memory_stats(self):
        """Show memory and persistence stats"""
        memory_stats = {
            "Memory File": str(self.manager.memory_file),
            "Memory Size": f"{self.manager.memory_file.stat().st_size if self.manager.memory_file.exists() else 0} bytes",
            "Last Saved": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        stats_table = Table(title="Memory & Persistence")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")

        for metric, value in memory_stats.items():
            stats_table.add_row(metric, value)

        self.console.print(stats_table)

    def _show_help(self):
        """Show comprehensive help"""
        help_content = """
# 🚀 Sanaa Projects - Complete Development Assistant

## Overview
Sanaa Projects is a comprehensive, self-contained coding assistant that provides:
- **Multi-framework support** (React, Laravel, Flutter)
- **Persistent memory** for tracking work progress
- **AI-powered coding assistance** with specialized agents
- **Project management** with templates and workflows
- **Debugging and issue resolution**
- **Planning and architecture guidance**

## Key Features

### 🤖 Specialized Agents
- **React Agent**: Component generation, hooks, state management
- **Laravel Agent**: Models, controllers, migrations, API resources
- **Flutter Agent**: Widgets, providers, BLoC pattern, services
- **Advanced Debugger**: Framework-specific issue detection and fixes
- **Planning Agent**: Comprehensive project planning and architecture

### 📁 Project Management
- Create projects from professional templates
- Persistent work session tracking
- Progress monitoring and milestone tracking
- Context-aware assistance

### 🔧 Development Workflow
- Interactive coding sessions with AI assistance
- Real-time debugging and issue resolution
- Code generation and refactoring
- Best practices enforcement

### 🐳 Infrastructure Integration
- Docker container management
- Database integration (MySQL, PostgreSQL)
- Search functionality (Meilisearch)
- Email testing (Mailpit)
- Selenium for testing

## Getting Started

1. **Launch Sanaa Projects**:
   ```bash
   sanaa projects
   ```

2. **Create or select a project** from the main menu

3. **Start a coding session** with your preferred agent

4. **Work with AI assistance** for code generation, debugging, and planning

## Available Commands

### Project Management
- Create new projects from templates
- Select and manage existing projects
- View detailed project information
- Track work sessions and progress

### Development
- Start coding sessions with specialized agents
- Debug and fix code issues
- Plan project architecture
- Get Q&A assistance

### System
- View comprehensive system status
- Monitor Docker containers
- Check project statistics
- Access help and documentation

## Framework Support

### React/Next.js
- Component generation with TypeScript
- Custom hooks and context providers
- API integration and data fetching
- State management solutions
- Testing setup and utilities

### Laravel
- Eloquent models with relationships
- Controllers and API resources
- Database migrations and seeders
- Authentication and authorization
- Job queues and background processing

### Flutter
- Stateful and stateless widgets
- Provider pattern for state management
- BLoC pattern implementation
- Service classes and API integration
- Material Design 3 compliance

## Best Practices

- **Persistent Memory**: All work sessions are automatically saved
- **Context Awareness**: AI understands your project structure and framework
- **Framework-Specific**: Specialized agents for each supported framework
- **Quality Assurance**: Built-in linting, testing, and code quality checks
- **Scalable Architecture**: Clean, maintainable code generation

## Support

For issues or questions:
- Check system status for container health
- Review project memory for work session history
- Use Q&A assistance for development questions
- Access comprehensive help documentation

---

**Happy coding with Sanaa Projects! 🚀✨**
"""

        self.console.print(Markdown(help_content))
        Prompt.ask("\nPress Enter to continue")

    def _handle_exit(self):
        """Handle application exit with comprehensive cleanup"""
        # Perform final health check and optimization
        self.console.print("[dim]Performing final system optimization...[/dim]")

        # Optimize memory for all projects
        for sanaa_project in self.manager.sanaa_projects.values():
            sanaa_project.optimize_memory()

        # Save all memory with optimization
        self.manager._save_memory()

        # Perform final health check
        final_issues = self._perform_system_health_check()
        if final_issues:
            self.console.print(f"[yellow]Note: {len(final_issues)} system issues detected[/yellow]")
            self.console.print("[dim]Run 'sanaa projects' → 'System Status' for details[/dim]")

        # Show goodbye message with session summary
        goodbye_text = Text("👋 Thanks for using Sanaa Projects!", style="bold cyan")
        goodbye_text.append("\n[dim]Your work sessions have been saved and optimized.[/dim]")

        if self.current_project:
            goodbye_text.append(f"\n[dim]Current project: {self.current_project.project.name}[/dim]")

        panel = Panel(
            Align.center(goodbye_text),
            border_style="cyan",
            padding=(2, 4)
        )

        self.console.print(panel)
        time.sleep(1)

    def _run_llm_connection_test(self):
        """Run comprehensive LLM connection test"""
        self._clear_screen()
        self.console.print("[bold cyan]🧪 LLM Connection Test[/bold cyan]\n")

        # Test script execution
        test_script = Path("test_llm_connection.py")
        if not test_script.exists():
            self.console.print("[red]❌ Test script not found. Please run 'python3 test_llm_connection.py' manually.[/red]")
            Prompt.ask("\nPress Enter to continue")
            return

        try:
            self.console.print("Running comprehensive LLM test...")
            result = subprocess.run(
                [sys.executable, str(test_script)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                self.console.print("[green]✅ LLM Connection Test PASSED[/green]")
                self.console.print(result.stdout)
            else:
                self.console.print("[red]❌ LLM Connection Test FAILED[/red]")
                self.console.print("STDOUT:", result.stdout)
                self.console.print("STDERR:", result.stderr)

        except subprocess.TimeoutExpired:
            self.console.print("[red]❌ Test timed out after 60 seconds[/red]")
        except Exception as e:
            self.console.print(f"[red]❌ Test execution failed: {e}[/red]")

        Prompt.ask("\nPress Enter to continue")

    def _perform_auto_healing(self):
        """Perform comprehensive auto-healing"""
        self._clear_screen()
        self.console.print("[bold cyan]🔧 Auto-Healing System[/bold cyan]\n")

        self.console.print("Scanning system for issues...")
        issues = self._perform_system_health_check()

        if not issues:
            self.console.print("[green]✅ No issues detected. System is healthy![/green]")
        else:
            self.console.print(f"[yellow]Found {len(issues)} issues. Attempting auto-healing...[/yellow]\n")

            healed_count = 0
            failed_count = 0

            for i, issue in enumerate(issues, 1):
                self.console.print(f"{i}. {issue}")

                # Attempt to heal each issue
                if self._heal_specific_issue(issue):
                    self.console.print("   [green]✓ Healed[/green]")
                    healed_count += 1
                else:
                    self.console.print("   [red]✗ Could not heal[/red]")
                    failed_count += 1

            self.console.print(f"\n[green]Healed: {healed_count}[/green] | [red]Failed: {failed_count}[/red]")

            if healed_count > 0:
                self.console.print("\n[dim]Re-running health check to verify fixes...[/dim]")
                remaining_issues = self._perform_system_health_check()
                if len(remaining_issues) < len(issues):
                    self.console.print(f"[green]✅ Successfully reduced issues from {len(issues)} to {len(remaining_issues)}[/green]")
                else:
                    self.console.print("[yellow]⚠️ Some issues persist[/yellow]")

        Prompt.ask("\nPress Enter to continue")

    def _heal_specific_issue(self, issue: str) -> bool:
        """Attempt to heal a specific issue"""
        try:
            if "orphaned sessions" in issue:
                # Clean up orphaned sessions
                for sanaa_project in self.manager.sanaa_projects.values():
                    sanaa_project.work_sessions = [
                        session for session in sanaa_project.work_sessions
                        if not (session.stopping_point is None and
                               time.time() - session.last_activity > 24 * 3600)
                    ]
                return True

            elif "Memory file corrupted" in issue:
                # Recreate memory file
                self.manager._save_memory()
                return True

            elif "Container" in issue and "unhealthy" in issue:
                # Try to restart unhealthy containers
                container_name = issue.split("Container ")[1].split(" is")[0]
                result = subprocess.run(
                    ["docker", "restart", container_name],
                    capture_output=True, text=True
                )
                return result.returncode == 0

            elif "endpoint unreachable" in issue:
                # Check if containers are running
                result = subprocess.run(
                    ["docker", "ps", "--format", "{{.Names}}"],
                    capture_output=True, text=True
                )
                if "coding-swarm" in result.stdout:
                    return True  # Containers are running, might be temporary issue
                return False

            else:
                return False  # Unknown issue type

        except Exception as e:
            self.console.print(f"   [red]Healing failed: {e}[/red]")
            return False

    def _view_project_details(self, projects: List[SanaaProject]):
        """View detailed project information"""
        if not projects:
            self.console.print("[yellow]No projects available.[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        self.console.print("[bold]Select project to view details:[/bold]\n")

        for i, sanaa_project in enumerate(projects, 1):
            self.console.print(f"[cyan]{i}.[/cyan] {sanaa_project.project.name}")

        try:
            choice = IntPrompt.ask("\nChoose project number", choices=[str(i) for i in range(1, len(projects) + 1)])
            project = projects[choice - 1]

            self._show_detailed_project_info(project)

        except (ValueError, IndexError):
            self.console.print("[red]Invalid choice.[/red]")

        Prompt.ask("\nPress Enter to continue")

    def _show_detailed_project_info(self, sanaa_project: SanaaProject):
        """Show detailed project information"""
        project = sanaa_project.project

        # Project overview
        overview_table = Table(title=f"📁 Project: {project.name}")
        overview_table.add_column("Property", style="cyan")
        overview_table.add_column("Value", style="green")

        overview_table.add_row("Name", project.name)
        overview_table.add_row("Path", project.path)
        overview_table.add_row("Framework", self._detect_framework(project))
        overview_table.add_row("Files", str(len(project.files)))
        overview_table.add_row("Created", datetime.fromtimestamp(project.created_at).strftime("%Y-%m-%d %H:%M"))
        overview_table.add_row("Updated", datetime.fromtimestamp(project.updated_at).strftime("%Y-%m-%d %H:%M"))

        self.console.print(overview_table)
        self.console.print()

        # Work sessions
        if sanaa_project.work_sessions:
            sessions_table = Table(title="Work Sessions")
            sessions_table.add_column("Agent", style="cyan")
            sessions_table.add_column("Duration", style="green", justify="right")
            sessions_table.add_column("Tasks", style="yellow", justify="right")
            sessions_table.add_column("Last Activity", style="magenta")

            for session in sanaa_project.work_sessions[-10:]:  # Show last 10
                duration = f"{session.duration:.1f}m"
                tasks = str(len(session.completed_tasks))
                last_activity = datetime.fromtimestamp(session.last_activity).strftime("%Y-%m-%d %H:%M")

                sessions_table.add_row(
                    session.agent_type.title(),
                    duration,
                    tasks,
                    last_activity
                )

            self.console.print(sessions_table)
        else:
            self.console.print("[dim]No work sessions recorded yet.[/dim]")

    def _delete_project(self, projects: List[SanaaProject]):
        """Delete a project"""
        if not projects:
            self.console.print("[yellow]No projects available to delete.[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        self.console.print("[bold red]⚠️ Delete Project[/bold red]\n")
        self.console.print("[yellow]This action cannot be undone![/yellow]\n")

        for i, sanaa_project in enumerate(projects, 1):
            self.console.print(f"[cyan]{i}.[/cyan] {sanaa_project.project.name}")

        try:
            choice = IntPrompt.ask("\nChoose project to delete (0 to cancel)",
                                 choices=["0"] + [str(i) for i in range(1, len(projects) + 1)])

            if choice == "0":
                return

            project = projects[int(choice) - 1]

            # Confirm deletion
            if Confirm.ask(f"Are you sure you want to delete '{project.project.name}'?", default=False):
                # Remove from registry and memory
                self.project_registry.remove(project.project.name)
                if project.project.name in self.sanaa_projects:
                    del self.sanaa_projects[project.project.name]

                # Remove from current project if selected
                if self.current_project and self.current_project.project.name == project.project.name:
                    self.current_project = None

                # Save memory
                self.manager._save_memory()

                self.console.print(f"[green]✓ Project '{project.project.name}' deleted.[/green]")
            else:
                self.console.print("[dim]Deletion cancelled.[/dim]")

        except (ValueError, IndexError):
            self.console.print("[red]Invalid choice.[/red]")

        Prompt.ask("\nPress Enter to continue")


# Global interface instance
sanaa_projects = SanaaProjectsInterface()

# Async wrapper for the main menu
async def run_sanaa_projects():
    """Run Sanaa Projects with async support"""
    await sanaa_projects.show_main_menu()