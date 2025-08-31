"""
Modern CLI UI - Steve Jobs Standards Implementation
Clean, intuitive, and beautiful command-line interface
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import time
import os
from pathlib import Path

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
from rich.padding import Padding
from rich.rule import Rule
from rich.markdown import Markdown
from rich.syntax import Syntax

from coding_swarm_core import ProjectRegistry, template_manager
from coding_swarm_core.projects import Project


@dataclass
class UITheme:
    """UI Theme configuration"""
    primary: str = "bold cyan"
    secondary: str = "dim cyan"
    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    accent: str = "magenta"
    background: str = "blue"
    border: str = "cyan"


class ModernCLI:
    """Modern CLI with Steve Jobs standards - Simple, Beautiful, Intuitive"""

    def __init__(self):
        self.console = Console()
        self.theme = UITheme()
        self.project_registry = ProjectRegistry.load()

    def show_welcome(self):
        """Show beautiful welcome screen"""
        # Clear screen
        self.console.clear()

        # Create welcome layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=8),
            Layout(name="content"),
            Layout(name="footer", size=3)
        )

        # Header with logo
        header_text = Text()
        header_text.append("🚀 ", style=self.theme.primary)
        header_text.append("Sanaa", style="bold white")
        header_text.append(" AI Development Assistant", style=self.theme.secondary)

        welcome_panel = Panel(
            Align.center(header_text),
            border_style=self.theme.border,
            padding=(2, 4),
            title="[dim]Welcome[/dim]"
        )
        layout["header"].update(welcome_panel)

        # Main content
        content_layout = Layout()
        content_layout.split_row(
            Layout(name="left"),
            Layout(name="right")
        )

        # Quick actions
        quick_actions = self._create_quick_actions()
        content_layout["left"].update(quick_actions)

        # System status
        system_status = self._create_system_status()
        content_layout["right"].update(system_status)

        layout["content"].update(content_layout)

        # Footer
        footer_text = Align.center(
            Text("Press Enter to continue or 'h' for help", style="dim")
        )
        layout["footer"].update(footer_text)

        self.console.print(layout)

    def _create_quick_actions(self) -> Panel:
        """Create quick actions panel"""
        actions_table = Table(show_header=False, box=None)
        actions_table.add_column("Action", style=self.theme.primary)
        actions_table.add_column("Description", style="dim")

        actions = [
            ("🏗️  New Project", "Create from template"),
            ("📥  Clone Repository", "Clone Git repository"),
            ("💻  Code", "Start coding session"),
            ("🔍  Debug", "Debug existing code"),
            ("📊  Status", "System overview"),
            ("⚙️  Settings", "Configure Sanaa"),
        ]

        for action, desc in actions:
            actions_table.add_row(action, desc)

        return Panel(
            actions_table,
            title="[bold]Quick Actions[/bold]",
            border_style=self.theme.border,
            padding=(1, 2)
        )

    def _create_system_status(self) -> Panel:
        """Create system status panel"""
        status_info = []

        # Project count
        projects = self.project_registry.list()
        status_info.append(f"📁 Projects: {len(projects)}")

        # Default project
        default = self.project_registry.default or "None"
        status_info.append(f"🎯 Default: {default}")

        # Recent activity
        recent_activity = self._get_recent_activity()
        if recent_activity:
            status_info.append(f"⚡ Recent: {recent_activity}")

        status_text = "\n".join(status_info)

        return Panel(
            status_text,
            title="[bold]System Status[/bold]",
            border_style=self.theme.success,
            padding=(1, 2)
        )

    def _get_recent_activity(self) -> str:
        """Get recent activity summary"""
        projects = self.project_registry.list()
        if not projects:
            return "No recent activity"

        # Get most recently updated project
        recent = max(projects, key=lambda p: p.updated_at)
        hours_ago = int((time.time() - recent.updated_at) / 3600)

        if hours_ago < 1:
            return f"Updated {recent.name} recently"
        elif hours_ago < 24:
            return f"Updated {recent.name} {hours_ago}h ago"
        else:
            days_ago = hours_ago // 24
            return f"Updated {recent.name} {days_ago}d ago"

    def show_main_menu(self):
        """Show main interactive menu"""
        while True:
            self.show_welcome()

            # Get user input
            choice = Prompt.ask(
                "\n[dim]What would you like to do?[/dim]",
                choices=["1", "2", "3", "4", "5", "6", "h", "q"],
                default="1",
                show_choices=False
            ).lower()

            if choice in ["q", "quit", "exit"]:
                self._show_goodbye()
                break
            elif choice == "h":
                self._show_help()
            elif choice == "1":
                self._handle_new_project()
            elif choice == "2":
                self._handle_code_session()
            elif choice == "3":
                self._handle_debug()
            elif choice == "4":
                self._show_detailed_status()
            elif choice == "5":
                self._show_settings()
            elif choice == "6":
                self._handle_clone_repository()
            else:
                self.console.print("[red]Invalid choice. Press 'h' for help.[/red]")
                time.sleep(1)

    def _handle_new_project(self):
        """Handle new project creation"""
        self.console.clear()

        # Show project templates
        templates = template_manager.list_available_templates()

        self.console.print("\n[bold cyan]🏗️  Create New Project[/bold cyan]\n")

        # Framework selection
        frameworks = list(templates.keys())
        framework_table = Table(title="Available Frameworks")
        framework_table.add_column("Framework", style=self.theme.primary)
        framework_table.add_column("Templates", style="dim")

        for framework in frameworks:
            template_list = templates[framework]
            framework_table.add_row(
                framework.title(),
                f"{len(template_list)} templates"
            )

        self.console.print(framework_table)
        self.console.print()

        # Get framework choice
        framework_choice = Prompt.ask(
            "Choose framework",
            choices=frameworks,
            default=frameworks[0] if frameworks else None
        )

        if framework_choice in templates:
            self._show_framework_templates(framework_choice, templates[framework_choice])

    def _handle_clone_repository(self):
        """Handle Git repository cloning"""
        self.console.clear()
        self.console.print("\n[bold cyan]📥  Clone Git Repository[/bold cyan]\n")

        # Get repository details
        repo_url = Prompt.ask("Repository URL")
        project_name = Prompt.ask("Project name", default=self._extract_project_name_from_url(repo_url))
        project_path = Prompt.ask("Project path", default=f"./{project_name}")

        # Clone repository
        with self.console.status(f"[bold green]Cloning {repo_url}...[/bold green]"):
            try:
                import subprocess
                import os

                # Ensure project directory exists
                os.makedirs(project_path, exist_ok=True)

                # Clone the repository
                result = subprocess.run(
                    ["git", "clone", repo_url, project_name],
                    cwd=project_path,
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    raise Exception(f"Git clone failed: {result.stderr}")

                # Create project instance
                full_project_path = os.path.join(project_path, project_name)
                project = Project(
                    name=project_name,
                    path=full_project_path,
                    notes=f"Cloned from {repo_url}"
                )

                # Register project
                self.project_registry.add(project)
                if not self.project_registry.default:
                    self.project_registry.set_default(project.name)

                self.console.print(f"\n[green]✓[/green] Repository cloned successfully!")
                self.console.print(f"[dim]Location: {full_project_path}[/dim]")

                # Ask to start coding session
                if Confirm.ask("\nStart coding session now?", default=True):
                    self._start_code_session(project)

            except Exception as e:
                self.console.print(f"\n[red]✗[/red] Failed to clone repository: {e}")

        Prompt.ask("\nPress Enter to continue")

    def _extract_project_name_from_url(self, url: str) -> str:
        """Extract project name from Git URL"""
        # Remove .git suffix and get last part of path
        url = url.rstrip('.git')
        parts = url.split('/')
        if parts:
            return parts[-1]
        return "cloned-project"

    def _show_framework_templates(self, framework: str, templates: List[str]):
        """Show templates for selected framework"""
        self.console.print(f"\n[bold]{framework.title()} Templates:[/bold]\n")

        template_table = Table()
        template_table.add_column("#", style=self.theme.accent, width=3)
        template_table.add_column("Template", style=self.theme.primary)
        template_table.add_column("Description", style="dim")

        for i, template_desc in enumerate(templates, 1):
            name, desc = template_desc.split(": ", 1)
            template_table.add_row(str(i), name, desc)

        self.console.print(template_table)
        self.console.print()

        # Template selection
        template_choice = IntPrompt.ask(
            "Choose template number",
            choices=[str(i) for i in range(1, len(templates) + 1)]
        )

        if 1 <= template_choice <= len(templates):
            selected_template = templates[template_choice - 1].split(": ")[0]
            self._create_project_from_template(framework, selected_template)

    def _create_project_from_template(self, framework: str, template_name: str):
        """Create project from selected template"""
        # Get project details
        project_name = Prompt.ask("Project name")
        project_path = Prompt.ask("Project path", default=f"./{project_name}")

        # Find the template key by matching name and framework
        template_key = None
        for key, template in template_manager.templates.items():
            if template.name == template_name and template.framework == framework:
                template_key = key
                break

        if not template_key:
            # Debug: show available templates for this framework
            available_templates = []
            for key, template in template_manager.templates.items():
                if template.framework == framework:
                    available_templates.append(f"'{template.name}' (key: {key})")
            available_str = ", ".join(available_templates) if available_templates else "none"
            raise ValueError(f"Template '{template_name}' not found for framework '{framework}'. Available templates: {available_str}")

        # Create project
        with self.console.status(f"[bold green]Creating {project_name}...[/bold green]"):
            try:
                project = template_manager.create_project_from_template(
                    template_key,
                    project_name,
                    project_path
                )

                # Register project
                self.project_registry.add(project)
                if not self.project_registry.default:
                    self.project_registry.set_default(project.name)

                self.console.print(f"\n[green]✓[/green] Project '{project_name}' created successfully!")
                self.console.print(f"[dim]Location: {project.path}[/dim]")

                # Ask to start coding
                if Confirm.ask("\nStart coding session now?", default=True):
                    self._start_code_session(project)

            except Exception as e:
                self.console.print(f"\n[red]✗[/red] Failed to create project: {e}")

        Prompt.ask("\nPress Enter to continue")

    def _start_code_session(self, project):
        """Start a coding session for the project"""
        self.console.print(f"\n[bold cyan]💻 Starting coding session for {project.name}[/bold cyan]")

        # Detect framework and suggest agent
        framework = self._detect_project_framework(project)
        suggested_agent = self._get_suggested_agent(framework)

        self.console.print(f"[dim]Detected framework: {framework}[/dim]")
        self.console.print(f"[dim]Suggested agent: {suggested_agent}[/dim]")

        # This would integrate with the agent system
        self.console.print("[yellow]Agent integration coming soon...[/yellow]")

    def _detect_project_framework(self, project) -> str:
        """Detect project framework"""
        project_path = Path(project.path)

        # React detection
        if (project_path / 'package.json').exists():
            package_json = project_path / 'package.json'
            try:
                import json
                data = json.loads(package_json.read_text())
                deps = data.get('dependencies', {})

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

        return 'unknown'

    def _get_suggested_agent(self, framework: str) -> str:
        """Get suggested agent for framework"""
        agent_map = {
            'react': 'react',
            'nextjs': 'react',
            'laravel': 'laravel',
            'flutter': 'flutter'
        }
        return agent_map.get(framework, 'coder')

    def _handle_code_session(self):
        """Handle code session"""
        self.console.clear()
        self.console.print("\n[bold cyan]💻 Code Session[/bold cyan]\n")

        projects = self.project_registry.list()
        if not projects:
            self.console.print("[yellow]No projects found. Create a project first.[/yellow]")
            Prompt.ask("\nPress Enter to continue")
            return

        # Show projects
        project_table = Table(title="Available Projects")
        project_table.add_column("#", style=self.theme.accent, width=3)
        project_table.add_column("Name", style=self.theme.primary)
        project_table.add_column("Path", style="dim")
        project_table.add_column("Framework", style=self.theme.secondary)

        for i, project in enumerate(projects, 1):
            framework = self._detect_project_framework(project)
            project_table.add_row(
                str(i),
                project.name,
                project.path,
                framework.title()
            )

        self.console.print(project_table)
        self.console.print()

        # Project selection
        if len(projects) == 1:
            choice = 1
        else:
            choice = IntPrompt.ask(
                "Choose project number",
                choices=[str(i) for i in range(1, len(projects) + 1)]
            )

        if 1 <= choice <= len(projects):
            project = projects[choice - 1]
            self._start_code_session(project)

    def _handle_debug(self):
        """Handle debug functionality"""
        self.console.clear()
        self.console.print("\n[bold cyan]🔍 Debug Mode[/bold cyan]\n")
        self.console.print("[yellow]Debug functionality coming soon...[/yellow]")
        Prompt.ask("\nPress Enter to continue")

    def _show_detailed_status(self):
        """Show detailed system status"""
        self.console.clear()

        # Create status layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="content"),
            Layout(name="footer", size=3)
        )

        # Header
        header = Panel(
            Align.center("[bold cyan]📊 System Status[/bold cyan]"),
            border_style=self.theme.border
        )
        layout["header"].update(header)

        # Content
        content_layout = Layout()
        content_layout.split_row(
            Layout(name="projects"),
            Layout(name="system")
        )

        # Projects panel
        projects_panel = self._create_projects_panel()
        content_layout["projects"].update(projects_panel)

        # System panel
        system_panel = self._create_system_info_panel()
        content_layout["system"].update(system_panel)

        layout["content"].update(content_layout)

        # Footer
        footer = Align.center(Text("Press Enter to return", style="dim"))
        layout["footer"].update(footer)

        self.console.print(layout)
        Prompt.ask("")

    def _create_projects_panel(self) -> Panel:
        """Create projects status panel"""
        projects = self.project_registry.list()

        if not projects:
            content = "[dim]No projects configured[/dim]"
        else:
            table = Table(show_header=False, box=None)
            table.add_column("Project", style=self.theme.primary)
            table.add_column("Framework", style=self.theme.secondary)
            table.add_column("Updated", style="dim", justify="right")

            for project in projects[:5]:  # Show top 5
                framework = self._detect_project_framework(project)
                updated = time.strftime("%Y-%m-%d", time.localtime(project.updated_at))
                table.add_row(project.name, framework.title(), updated)

            content = table

        return Panel(
            content,
            title="[bold]Projects[/bold]",
            border_style=self.theme.success,
            padding=(1, 2)
        )

    def _create_system_info_panel(self) -> Panel:
        """Create system information panel"""
        import platform

        system_info = [
            f"🖥️  OS: {platform.system()} {platform.release()}",
            f"🐍 Python: {platform.python_version()}",
            f"📁 Projects: {len(self.project_registry.list())}",
            f"🎯 Default: {self.project_registry.default or 'None'}",
            f"⚡ Memory: {self._get_memory_usage()}",
        ]

        content = "\n".join(system_info)

        return Panel(
            content,
            title="[bold]System Info[/bold]",
            border_style=self.theme.accent,
            padding=(1, 2)
        )

    def _get_memory_usage(self) -> str:
        """Get memory usage info"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return f"{memory.percent:.1f}%"
        except ImportError:
            return "N/A"

    def _show_settings(self):
        """Show settings menu"""
        self.console.clear()
        self.console.print("\n[bold cyan]⚙️  Settings[/bold cyan]\n")
        self.console.print("[yellow]Settings functionality coming soon...[/yellow]")
        Prompt.ask("\nPress Enter to continue")

    def _show_help(self):
        """Show help information"""
        self.console.clear()

        help_text = """
[bold cyan]🚀 Sanaa AI Development Assistant[/bold cyan]

Sanaa is your intelligent coding companion that helps you:
• Create projects from professional templates
• Write code with AI assistance
• Debug and optimize your applications
• Manage complex development workflows

[bold]Quick Start:[/bold]
1. Create a new project from template
2. Start a coding session
3. Use AI assistance for development
4. Debug and optimize your code

[bold]Available Frameworks:[/bold]
• React/Next.js for web development
• Laravel for PHP backend development
• Flutter for mobile app development

[bold]Commands:[/bold]
• '1' - Create new project
• '2' - Start coding session
• '3' - Debug mode
• '4' - System status
• '5' - Settings
• '6' - Clone Git repository
• 'h' - Show this help
• 'q' - Quit

[dim]Press Enter to return to main menu[/dim]
        """

        self.console.print(Panel(help_text, border_style=self.theme.border, padding=(1, 2)))
        Prompt.ask("")

    def _show_goodbye(self):
        """Show goodbye message"""
        self.console.clear()

        goodbye_text = Text()
        goodbye_text.append("👋 ", style=self.theme.primary)
        goodbye_text.append("Thanks for using Sanaa!", style="bold white")
        goodbye_text.append("\n[dim]Happy coding! 🚀[/dim]")

        panel = Panel(
            Align.center(goodbye_text),
            border_style=self.theme.success,
            padding=(2, 4)
        )

        self.console.print(panel)
        time.sleep(1)


# Global CLI instance
modern_cli = ModernCLI()