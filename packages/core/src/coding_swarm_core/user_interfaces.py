"""
User-Friendly Interfaces and Documentation for Sanaa
Provides comprehensive documentation, CLI improvements, and web interfaces
"""
from __future__ import annotations

import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum
import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.markdown import Markdown
import typer
import questionary
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style


class InterfaceType(Enum):
    CLI = "cli"
    WEB = "web"
    API = "api"
    DESKTOP = "desktop"


class DocumentationType(Enum):
    USER_GUIDE = "user_guide"
    API_REFERENCE = "api_reference"
    DEVELOPER_GUIDE = "developer_guide"
    TROUBLESHOOTING = "troubleshooting"
    BEST_PRACTICES = "best_practices"


@dataclass
class DocumentationEntry:
    """Represents a documentation entry"""
    id: str
    title: str
    content: str
    type: DocumentationType
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    author: str
    version: str
    related_topics: List[str] = field(default_factory=list)


@dataclass
class UserInterface:
    """Represents a user interface component"""
    id: str
    name: str
    type: InterfaceType
    description: str
    components: Dict[str, Any] = field(default_factory=dict)
    handlers: Dict[str, Callable] = field(default_factory=dict)


class DocumentationSystem:
    """Comprehensive documentation system"""

    def __init__(self):
        self.entries: Dict[str, DocumentationEntry] = {}
        self.categories: Dict[str, List[str]] = {}
        self.search_index: Dict[str, List[str]] = {}
        self.console = Console()

        # Initialize with core documentation
        self._initialize_core_documentation()

    def _initialize_core_documentation(self):
        """Initialize core documentation entries"""
        core_docs = [
            {
                'id': 'getting_started',
                'title': 'Getting Started with Sanaa',
                'content': self._get_getting_started_content(),
                'type': DocumentationType.USER_GUIDE,
                'tags': ['beginner', 'setup', 'installation'],
                'author': 'Sanaa Team',
                'version': '1.0'
            },
            {
                'id': 'api_reference',
                'title': 'API Reference',
                'content': self._get_api_reference_content(),
                'type': DocumentationType.API_REFERENCE,
                'tags': ['api', 'reference', 'endpoints'],
                'author': 'Sanaa Team',
                'version': '1.0'
            },
            {
                'id': 'troubleshooting',
                'title': 'Troubleshooting Guide',
                'content': self._get_troubleshooting_content(),
                'type': DocumentationType.TROUBLESHOOTING,
                'tags': ['debugging', 'issues', 'solutions'],
                'author': 'Sanaa Team',
                'version': '1.0'
            },
            {
                'id': 'best_practices',
                'title': 'Best Practices',
                'content': self._get_best_practices_content(),
                'type': DocumentationType.BEST_PRACTICES,
                'tags': ['optimization', 'security', 'performance'],
                'author': 'Sanaa Team',
                'version': '1.0'
            }
        ]

        for doc_data in core_docs:
            entry = DocumentationEntry(
                id=doc_data['id'],
                title=doc_data['title'],
                content=doc_data['content'],
                type=doc_data['type'],
                tags=doc_data['tags'],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                author=doc_data['author'],
                version=doc_data['version']
            )
            self.entries[doc_data['id']] = entry

            # Update categories
            if doc_data['type'].value not in self.categories:
                self.categories[doc_data['type'].value] = []
            self.categories[doc_data['type'].value].append(doc_data['id'])

            # Update search index
            self._update_search_index(entry)

    def _get_getting_started_content(self) -> str:
        """Get getting started guide content"""
        return """
# Getting Started with Sanaa

## Installation

```bash
# Install Sanaa
pip install sanaa

# Or from source
git clone https://github.com/your-org/sanaa.git
cd sanaa
pip install -e .
```

## Quick Start

```bash
# Initialize Sanaa
sanaa init

# Create your first project
sanaa create my-project --template react

# Start development
cd my-project
sanaa dev
```

## Basic Concepts

### Agents
Sanaa uses specialized AI agents for different tasks:
- **Architect**: Planning and design
- **Coder**: Implementation and coding
- **Debugger**: Testing and debugging
- **Planner**: Project management

### Workflows
Create automated workflows for common tasks:
```bash
# Create a development workflow
sanaa workflow create dev-workflow --steps plan,code,test,deploy
```

## Next Steps
1. Explore the [API Reference](api_reference)
2. Check out [Best Practices](best_practices)
3. Join our community
"""

    def _get_api_reference_content(self) -> str:
        """Get API reference content"""
        return """
# API Reference

## Core Endpoints

### Projects
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create new project
- `GET /api/projects/{id}` - Get project details
- `PUT /api/projects/{id}` - Update project
- `DELETE /api/projects/{id}` - Delete project

### Agents
- `GET /api/agents` - List available agents
- `POST /api/agents/{type}/execute` - Execute agent task
- `GET /api/agents/{id}/status` - Get agent status

### Tasks
- `GET /api/tasks` - List tasks
- `POST /api/tasks` - Create task
- `GET /api/tasks/{id}` - Get task details
- `PUT /api/tasks/{id}/status` - Update task status

## Authentication

All API requests require authentication:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.sanaa.dev/v1/projects
```

## Rate Limits

- 1000 requests per hour for authenticated users
- 100 requests per hour for anonymous users
"""

    def _get_troubleshooting_content(self) -> str:
        """Get troubleshooting guide content"""
        return """
# Troubleshooting Guide

## Common Issues

### Agent Not Responding
**Symptoms**: Agent tasks hang or timeout
**Solutions**:
1. Check agent status: `sanaa agent status`
2. Restart agent: `sanaa agent restart <agent_id>`
3. Check logs: `sanaa logs agent <agent_id>`

### Build Failures
**Symptoms**: Project builds fail
**Solutions**:
1. Clear cache: `sanaa cache clear`
2. Check dependencies: `sanaa deps check`
3. Rebuild from scratch: `sanaa build --clean`

### Performance Issues
**Symptoms**: Slow response times
**Solutions**:
1. Check system resources: `sanaa monitor`
2. Optimize configuration: `sanaa config optimize`
3. Scale resources: `sanaa scale up`

## Debug Mode

Enable debug mode for detailed logging:

```bash
export SANAA_DEBUG=1
sanaa <command>
```

## Getting Help

- Check logs: `sanaa logs`
- Run diagnostics: `sanaa doctor`
- Community support: [Discord](https://discord.gg/sanaa)
"""

    def _get_best_practices_content(self) -> str:
        """Get best practices content"""
        return """
# Best Practices

## Project Structure

```
my-project/
├── src/
│   ├── components/
│   ├── services/
│   └── utils/
├── tests/
├── docs/
└── sanaa.yml
```

## Code Quality

### Naming Conventions
- Use descriptive names
- Follow language-specific conventions
- Be consistent across the project

### Error Handling
```python
# Good
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    handle_error(e)
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise

# Bad
try:
    result = risky_operation()
except:
    pass
```

## Security

### Input Validation
- Validate all user inputs
- Use parameterized queries
- Sanitize data before processing

### Secrets Management
- Never hardcode secrets
- Use environment variables
- Rotate secrets regularly

## Performance

### Caching
- Cache expensive operations
- Use appropriate cache strategies
- Monitor cache hit rates

### Database Optimization
- Use indexes appropriately
- Avoid N+1 queries
- Optimize query patterns

## Testing

### Test Coverage
- Aim for >80% coverage
- Test edge cases
- Use property-based testing

### Test Types
- Unit tests for functions
- Integration tests for components
- End-to-end tests for workflows
"""

    def search_documentation(self, query: str, doc_type: Optional[DocumentationType] = None) -> List[DocumentationEntry]:
        """Search documentation"""
        results = []

        # Search in titles and content
        query_lower = query.lower()
        for entry in self.entries.values():
            if doc_type and entry.type != doc_type:
                continue

            if (query_lower in entry.title.lower() or
                query_lower in entry.content.lower() or
                any(query_lower in tag for tag in entry.tags)):
                results.append(entry)

        return sorted(results, key=lambda x: len(x.title))  # Shorter titles first

    def get_documentation(self, doc_id: str) -> Optional[DocumentationEntry]:
        """Get documentation entry by ID"""
        return self.entries.get(doc_id)

    def list_documentation(self, doc_type: Optional[DocumentationType] = None) -> List[DocumentationEntry]:
        """List documentation entries"""
        if doc_type:
            return [self.entries[doc_id] for doc_id in self.categories.get(doc_type.value, [])]
        return list(self.entries.values())

    def _update_search_index(self, entry: DocumentationEntry):
        """Update search index for an entry"""
        words = set()

        # Extract words from title
        words.update(entry.title.lower().split())

        # Extract words from content (simplified)
        content_words = entry.content.lower().replace('\n', ' ').replace('#', ' ').split()
        words.update(content_words[:100])  # Limit to first 100 words

        # Add tags
        words.update(entry.tags)

        # Update index
        for word in words:
            if word not in self.search_index:
                self.search_index[word] = []
            if entry.id not in self.search_index[word]:
                self.search_index[word].append(entry.id)

    def display_documentation(self, entry: DocumentationEntry):
        """Display documentation entry in console"""
        self.console.print(Panel.fit(
            Markdown(entry.content),
            title=f"[bold blue]{entry.title}[/bold blue]",
            border_style="blue"
        ))

        # Display metadata
        metadata_table = Table(show_header=False)
        metadata_table.add_row("Type", entry.type.value.replace('_', ' ').title())
        metadata_table.add_row("Tags", ', '.join(entry.tags))
        metadata_table.add_row("Author", entry.author)
        metadata_table.add_row("Version", entry.version)
        metadata_table.add_row("Updated", entry.updated_at.strftime("%Y-%m-%d %H:%M"))

        self.console.print(metadata_table)


class EnhancedCLI:
    """Enhanced Command Line Interface"""

    def __init__(self):
        self.console = Console()
        self.app = typer.Typer()
        self.session: Optional[PromptSession] = None
        self.setup_commands()

    def setup_commands(self):
        """Set up CLI commands"""

        @self.app.command()
        def interactive():
            """Start interactive mode"""
            self.run_interactive_mode()

        @self.app.command()
        def docs(query: str = typer.Argument(None, help="Search query")):
            """Access documentation"""
            if query:
                self.search_docs(query)
            else:
                self.show_docs_menu()

        @self.app.command()
        def status():
            """Show system status"""
            self.show_system_status()

        @self.app.command()
        def monitor():
            """Start monitoring dashboard"""
            self.show_monitoring_dashboard()

    def run_interactive_mode(self):
        """Run interactive CLI mode"""
        self.console.print("[bold green]Welcome to Sanaa Interactive Mode![/bold green]")
        self.console.print("Type 'help' for available commands, 'quit' to exit.\n")

        # Set up prompt session
        commands = ['help', 'docs', 'status', 'monitor', 'projects', 'agents', 'quit']
        completer = WordCompleter(commands, ignore_case=True)
        style = Style.from_dict({
            'completion-menu.completion': 'bg:#008888 #ffffff',
            'completion-menu.completion.current': 'bg:#00aaaa #000000',
        })

        self.session = PromptSession(completer=completer, style=style)

        while True:
            try:
                user_input = self.session.prompt("sanaa> ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', 'q']:
                    break

                self.handle_interactive_command(user_input)

            except KeyboardInterrupt:
                continue
            except EOFError:
                break

        self.console.print("\n[green]Goodbye![/green]")

    def handle_interactive_command(self, command: str):
        """Handle interactive commands"""
        parts = command.split()
        cmd = parts[0].lower()

        if cmd == 'help':
            self.show_help()
        elif cmd == 'docs':
            query = ' '.join(parts[1:]) if len(parts) > 1 else None
            if query:
                self.search_docs(query)
            else:
                self.show_docs_menu()
        elif cmd == 'status':
            self.show_system_status()
        elif cmd == 'monitor':
            self.show_monitoring_dashboard()
        elif cmd == 'projects':
            self.show_projects()
        elif cmd == 'agents':
            self.show_agents()
        else:
            self.console.print(f"[red]Unknown command: {cmd}[/red]")
            self.console.print("Type 'help' for available commands.")

    def show_help(self):
        """Show help information"""
        help_table = Table(title="Available Commands")
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description", style="white")

        commands = [
            ("help", "Show this help message"),
            ("docs [query]", "Search documentation or show docs menu"),
            ("status", "Show system status"),
            ("monitor", "Show monitoring dashboard"),
            ("projects", "List and manage projects"),
            ("agents", "List and manage agents"),
            ("quit", "Exit interactive mode")
        ]

        for cmd, desc in commands:
            help_table.add_row(cmd, desc)

        self.console.print(help_table)

    def search_docs(self, query: str):
        """Search documentation"""
        from .user_interfaces import documentation_system
        results = documentation_system.search_documentation(query)

        if not results:
            self.console.print(f"[yellow]No documentation found for: {query}[/yellow]")
            return

        self.console.print(f"[green]Found {len(results)} documentation entries:[/green]")

        for i, entry in enumerate(results[:5], 1):  # Show top 5
            self.console.print(f"{i}. [cyan]{entry.title}[/cyan] - {entry.type.value}")

        if len(results) > 5:
            self.console.print(f"... and {len(results) - 5} more results")

        # Ask user to select one
        if results:
            choice = questionary.select(
                "Select documentation to view:",
                choices=[entry.title for entry in results[:5]]
            ).ask()

            if choice:
                selected_entry = next(entry for entry in results if entry.title == choice)
                documentation_system.display_documentation(selected_entry)

    def show_docs_menu(self):
        """Show documentation menu"""
        from .user_interfaces import documentation_system

        doc_types = [
            ("User Guides", DocumentationType.USER_GUIDE),
            ("API Reference", DocumentationType.API_REFERENCE),
            ("Developer Guides", DocumentationType.DEVELOPER_GUIDE),
            ("Troubleshooting", DocumentationType.TROUBLESHOOTING),
            ("Best Practices", DocumentationType.BEST_PRACTICES)
        ]

        choices = [f"{name} ({len(documentation_system.list_documentation(doc_type))})"
                  for name, doc_type in doc_types]

        choice = questionary.select("Select documentation category:", choices=choices).ask()

        if choice:
            selected_type = next(doc_type for name, doc_type in doc_types
                               if choice.startswith(name.split()[0]))

            entries = documentation_system.list_documentation(selected_type)

            if entries:
                entry_choice = questionary.select(
                    "Select documentation:",
                    choices=[entry.title for entry in entries]
                ).ask()

                if entry_choice:
                    selected_entry = next(entry for entry in entries if entry.title == entry_choice)
                    documentation_system.display_documentation(selected_entry)
            else:
                self.console.print("[yellow]No documentation available in this category.[/yellow]")

    def show_system_status(self):
        """Show system status"""
        # This would integrate with the performance monitor
        status_table = Table(title="System Status")
        status_table.add_column("Component", style="cyan")
        status_table.add_column("Status", style="green")
        status_table.add_column("Details")

        # Mock status data - in real implementation, get from actual components
        status_data = [
            ("Core Services", "Running", "All systems operational"),
            ("Agent System", "Running", "4 agents active"),
            ("API Server", "Running", "Port 8000"),
            ("Database", "Running", "Connection healthy"),
            ("Cache", "Running", "Redis connected")
        ]

        for component, status, details in status_data:
            status_table.add_row(component, status, details)

        self.console.print(status_table)

    def show_monitoring_dashboard(self):
        """Show monitoring dashboard"""
        with self.console.screen() as screen:
            with Live(screen, refresh_per_second=2) as live:
                for _ in range(50):  # Run for about 25 seconds
                    dashboard = self._create_monitoring_dashboard()
                    live.update(dashboard)
                    time.sleep(0.5)

    def _create_monitoring_dashboard(self) -> Panel:
        """Create monitoring dashboard display"""
        # Mock monitoring data
        cpu_usage = 45.2
        memory_usage = 62.8
        active_tasks = 3
        response_time = 0.234

        dashboard_content = f"""
[bold cyan]System Monitoring Dashboard[/bold cyan]

[green]CPU Usage:[/green] {cpu_usage:.1f}%
[green]Memory Usage:[/green] {memory_usage:.1f}%
[green]Active Tasks:[/green] {active_tasks}
[green]Avg Response Time:[/green] {response_time:.3f}s

[bold yellow]Recent Activity:[/bold yellow]
• Agent 'coder' completed task
• New project created
• API request processed
• Cache hit rate: 94.2%
"""

        return Panel(dashboard_content, title="Live Monitoring", border_style="blue")

    def show_projects(self):
        """Show projects management"""
        # Mock projects data
        projects_table = Table(title="Projects")
        projects_table.add_column("Name", style="cyan")
        projects_table.add_column("Status")
        projects_table.add_column("Last Modified")

        projects = [
            ("my-react-app", "Active", "2 hours ago"),
            ("api-service", "Building", "5 minutes ago"),
            ("mobile-app", "Planning", "1 day ago")
        ]

        for name, status, last_mod in projects:
            projects_table.add_row(name, status, last_mod)

        self.console.print(projects_table)

    def show_agents(self):
        """Show agents management"""
        # Mock agents data
        agents_table = Table(title="Agents")
        agents_table.add_column("Name", style="cyan")
        agents_table.add_column("Type")
        agents_table.add_column("Status")
        agents_table.add_column("Tasks Completed")

        agents = [
            ("architect_1", "Architect", "Idle", "12"),
            ("coder_1", "Coder", "Active", "28"),
            ("debugger_1", "Debugger", "Idle", "8"),
            ("planner_1", "Planner", "Planning", "15")
        ]

        for name, agent_type, status, tasks in agents:
            agents_table.add_row(name, agent_type, status, tasks)

        self.console.print(agents_table)


class WebInterface:
    """Web-based user interface"""

    def __init__(self):
        self.routes: Dict[str, Callable] = {}
        self.templates: Dict[str, str] = {}
        self.static_files: Dict[str, bytes] = {}
        self.setup_routes()

    def setup_routes(self):
        """Set up web routes"""
        self.routes = {
            '/': self.home_page,
            '/dashboard': self.dashboard_page,
            '/projects': self.projects_page,
            '/agents': self.agents_page,
            '/monitoring': self.monitoring_page,
            '/docs': self.documentation_page,
            '/api/status': self.api_status
        }

    async def home_page(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Home page"""
        return {
            'template': 'home.html',
            'data': {
                'title': 'Sanaa - AI Coding Assistant',
                'features': [
                    'Multi-framework support',
                    'Intelligent agent coordination',
                    'Real-time collaboration',
                    'Advanced debugging tools'
                ]
            }
        }

    async def dashboard_page(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Dashboard page"""
        return {
            'template': 'dashboard.html',
            'data': {
                'active_projects': 5,
                'running_agents': 3,
                'system_health': 'Good',
                'recent_activity': [
                    {'time': '2 min ago', 'action': 'Project created'},
                    {'time': '5 min ago', 'action': 'Agent task completed'},
                    {'time': '10 min ago', 'action': 'Deployment successful'}
                ]
            }
        }

    async def projects_page(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Projects page"""
        return {
            'template': 'projects.html',
            'data': {
                'projects': [
                    {'name': 'web-app', 'status': 'active', 'last_update': '1 hour ago'},
                    {'name': 'api-service', 'status': 'building', 'last_update': '5 min ago'},
                    {'name': 'mobile-app', 'status': 'planning', 'last_update': '2 hours ago'}
                ]
            }
        }

    async def agents_page(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Agents page"""
        return {
            'template': 'agents.html',
            'data': {
                'agents': [
                    {'name': 'Architect', 'status': 'idle', 'tasks_completed': 12},
                    {'name': 'Coder', 'status': 'active', 'tasks_completed': 28},
                    {'name': 'Debugger', 'status': 'idle', 'tasks_completed': 8}
                ]
            }
        }

    async def monitoring_page(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Monitoring page"""
        return {
            'template': 'monitoring.html',
            'data': {
                'cpu_usage': 45.2,
                'memory_usage': 62.8,
                'active_tasks': 3,
                'response_time': 0.234
            }
        }

    async def documentation_page(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Documentation page"""
        return {
            'template': 'docs.html',
            'data': {
                'categories': ['Getting Started', 'API Reference', 'Best Practices', 'Troubleshooting']
            }
        }

    async def api_status(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """API status endpoint"""
        return {
            'status': 'healthy',
            'version': '1.0.0',
            'uptime': '2 days, 4 hours',
            'active_connections': 15
        }


# Global instances
documentation_system = DocumentationSystem()
enhanced_cli = EnhancedCLI()
web_interface = WebInterface()


def get_documentation_system() -> DocumentationSystem:
    """Get global documentation system instance"""
    return documentation_system


def get_enhanced_cli() -> EnhancedCLI:
    """Get global enhanced CLI instance"""
    return enhanced_cli


def get_web_interface() -> WebInterface:
    """Get global web interface instance"""
    return web_interface