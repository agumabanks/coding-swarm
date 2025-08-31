# packages/core/src/coding_swarm_core/enhanced_modes.py
"""Enhanced Multi-Mode System similar to KiloCode's modes with custom mode support"""

import json
import yaml
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum

class ToolPermission(Enum):
    READ = "read"
    WRITE = "write" 
    EXECUTE = "execute"
    BROWSE = "browse"
    MCP = "mcp"

@dataclass
class ModeConfig:
    """Configuration for a mode similar to KiloCode's custom modes"""
    name: str
    description: str
    system_prompt: str
    tool_permissions: List[ToolPermission] = field(default_factory=list)
    file_permissions: Dict[str, List[str]] = field(default_factory=dict)  # pattern -> permissions
    auto_switch_conditions: List[str] = field(default_factory=list)
    context_size_limit: Optional[int] = None
    model_preference: Optional[str] = None
    temperature: float = 0.7
    max_iterations: int = 10
    requires_approval: bool = True

class BaseModeHandler(ABC):
    """Base class for mode handlers"""
    
    def __init__(self, config: ModeConfig, mcp_client=None):
        self.config = config
        self.mcp_client = mcp_client
        self.conversation_history = []
    
    @abstractmethod
    async def process_request(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request in this mode"""
        pass
    
    @abstractmethod
    def can_handle_request(self, request: str, context: Dict[str, Any]) -> bool:
        """Check if this mode can handle the request"""
        pass
    
    def should_switch_mode(self, request: str, context: Dict[str, Any]) -> Optional[str]:
        """Check if should switch to another mode"""
        for condition in self.config.auto_switch_conditions:
            # Simple keyword-based switching (can be enhanced with ML)
            if condition.lower() in request.lower():
                # Extract target mode from condition
                if "->architect" in condition:
                    return "architect"
                elif "->coder" in condition:
                    return "coder"  
                elif "->debugger" in condition:
                    return "debugger"
        return None

class ArchitectMode(BaseModeHandler):
    """Architect mode for planning and design"""
    
    def __init__(self, mcp_client=None):
        config = ModeConfig(
            name="architect",
            description="Technical leadership and system design",
            system_prompt="""You are a senior software architect. Focus on:
- High-level system design and architecture decisions
- Breaking down complex requirements into manageable components
- Identifying design patterns and best practices
- Planning implementation phases with clear milestones
- Considering scalability, maintainability, and performance
- Creating technical specifications and documentation

Always provide structured plans with clear acceptance criteria.""",
            tool_permissions=[ToolPermission.READ, ToolPermission.MCP],
            file_permissions={
                "**/*.md": ["read", "write"],  # Can read/write docs
                "**/*.py": ["read"],           # Can read code
                "**/*.json": ["read"],         # Can read configs
            },
            auto_switch_conditions=[
                "implement->coder", 
                "code this->coder",
                "debug->debugger",
                "error->debugger"
            ]
        )
        super().__init__(config, mcp_client)
    
    async def process_request(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process architect request"""
        # Enhanced with project analysis
        project_context = await self._analyze_project_structure(context.get("project_path"))
        
        enhanced_prompt = f"""
Project Context: {json.dumps(project_context, indent=2)}

Request: {request}

Please provide a detailed architectural plan including:
1. System overview and key components
2. Implementation phases with milestones
3. Technical decisions and rationale
4. Acceptance criteria for each phase
5. Risk assessment and mitigation strategies
"""
        
        # Your LLM call here with enhanced context
        response = await self._call_llm(enhanced_prompt, context)
        
        return {
            "mode": "architect",
            "response": response,
            "project_analysis": project_context,
            "suggested_next_mode": self._suggest_next_mode(response)
        }
    
    def can_handle_request(self, request: str, context: Dict[str, Any]) -> bool:
        architect_keywords = [
            "design", "architecture", "plan", "structure", "organize",
            "strategy", "approach", "system", "high-level", "overview"
        ]
        return any(keyword in request.lower() for keyword in architect_keywords)
    
    async def _analyze_project_structure(self, project_path: str) -> Dict[str, Any]:
        """Analyze project structure for architectural context"""
        if not project_path:
            return {}
        
        path = Path(project_path)
        analysis = {
            "structure": {},
            "technologies": [],
            "dependencies": {},
            "test_setup": {},
            "documentation": []
        }
        
        # Analyze structure
        for item in path.rglob("*"):
            if item.is_file():
                ext = item.suffix.lower()
                if ext not in analysis["structure"]:
                    analysis["structure"][ext] = 0
                analysis["structure"][ext] += 1
        
        # Detect technologies
        if (path / "package.json").exists():
            analysis["technologies"].append("Node.js")
        if (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
            analysis["technologies"].append("Python")
        if (path / "Dockerfile").exists():
            analysis["technologies"].append("Docker")
        
        return analysis
    
    def _suggest_next_mode(self, response: str) -> Optional[str]:
        """Suggest next mode based on response content"""
        if "implement" in response.lower() or "code" in response.lower():
            return "coder"
        elif "test" in response.lower():
            return "debugger"
        return None

class CoderMode(BaseModeHandler):
    """Coder mode for implementation"""
    
    def __init__(self, mcp_client=None):
        config = ModeConfig(
            name="coder",
            description="Code implementation and modification",
            system_prompt="""You are a senior software engineer focused on implementation. You:
- Write clean, maintainable, and well-documented code
- Follow established patterns and conventions
- Provide complete, working implementations
- Include appropriate error handling and validation
- Write unit tests when appropriate
- Generate clear diffs showing changes

Always provide complete file contents or clear diffs.""",
            tool_permissions=[ToolPermission.READ, ToolPermission.WRITE, ToolPermission.MCP],
            file_permissions={
                "**/*.py": ["read", "write"],
                "**/*.js": ["read", "write"], 
                "**/*.ts": ["read", "write"],
                "**/*.html": ["read", "write"],
                "**/*.css": ["read", "write"],
                "test_*": ["read", "write"],
                "*_test.py": ["read", "write"]
            },
            auto_switch_conditions=[
                "design->architect",
                "plan->architect", 
                "debug->debugger",
                "test failed->debugger"
            ]
        )
        super().__init__(config, mcp_client)
    
    async def process_request(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process coding request"""
        # Enhanced with code analysis
        current_code = await self._get_relevant_code(request, context)
        
        enhanced_prompt = f"""
Current Code Context:
{current_code}

Implementation Request: {request}

Please provide:
1. Complete implementation or clear diffs
2. Explanation of changes and approach
3. Any new dependencies or setup required
4. Suggested tests for the implementation
"""
        
        response = await self._call_llm(enhanced_prompt, context)
        
        # Extract code blocks and file changes
        changes = self._extract_code_changes(response)
        
        return {
            "mode": "coder",
            "response": response,
            "code_changes": changes,
            "files_modified": list(changes.keys()) if changes else [],
            "suggested_next_mode": self._suggest_next_mode(response)
        }
    
    def can_handle_request(self, request: str, context: Dict[str, Any]) -> bool:
        coder_keywords = [
            "implement", "code", "write", "create", "build", "add",
            "modify", "update", "fix", "function", "class", "method"
        ]
        return any(keyword in request.lower() for keyword in coder_keywords)
    
    async def _get_relevant_code(self, request: str, context: Dict[str, Any]) -> str:
        """Get relevant existing code for context"""
        # This would integrate with your file reading capabilities
        # and potentially use semantic search to find relevant code
        return ""
    
    def _extract_code_changes(self, response: str) -> Dict[str, str]:
        """Extract code changes from LLM response"""
        # Parse code blocks and file markers from response
        # Return dict of filename -> code content
        return {}

class DebuggerMode(BaseModeHandler):
    """Debugger mode for problem diagnosis and fixing"""
    
    def __init__(self, mcp_client=None):
        config = ModeConfig(
            name="debugger", 
            description="Bug diagnosis and systematic debugging",
            system_prompt="""You are a debugging expert. You systematically:
- Analyze error messages and stack traces
- Identify root causes of issues
- Suggest step-by-step debugging approaches
- Provide fixes with explanations
- Run tests to verify solutions
- Document fixes for future reference

Always be methodical and thorough in your debugging approach.""",
            tool_permissions=[ToolPermission.READ, ToolPermission.WRITE, ToolPermission.EXECUTE, ToolPermission.MCP],
            file_permissions={
                "**/*.py": ["read", "write"],
                "**/*.log": ["read"], 
                "test_*": ["read", "write", "execute"],
                "*_test.py": ["read", "write", "execute"]
            },
            auto_switch_conditions=[
                "implement fix->coder",
                "refactor->coder",
                "redesign->architect"
            ]
        )
        super().__init__(config, mcp_client)
    
    async def process_request(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process debug request"""
        # Enhanced with automated debugging
        debug_info = await self._gather_debug_info(context)
        
        enhanced_prompt = f"""
Debug Information:
{json.dumps(debug_info, indent=2)}

Problem Description: {request}

Please provide:
1. Root cause analysis
2. Step-by-step debugging plan
3. Proposed fixes with explanations
4. Tests to verify the fix
5. Prevention strategies for similar issues
"""
        
        response = await self._call_llm(enhanced_prompt, context)
        
        return {
            "mode": "debugger",
            "response": response,
            "debug_info": debug_info,
            "suggested_tests": self._extract_test_suggestions(response),
            "suggested_next_mode": self._suggest_next_mode(response)
        }
    
    def can_handle_request(self, request: str, context: Dict[str, Any]) -> bool:
        debug_keywords = [
            "debug", "error", "bug", "issue", "problem", "broken",
            "fails", "exception", "crash", "not working", "fix"
        ]
        return any(keyword in request.lower() for keyword in debug_keywords)
    
    async def _gather_debug_info(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Gather debugging information"""
        debug_info = {
            "recent_changes": [],
            "test_results": {},
            "logs": [],
            "system_info": {}
        }
        
        project_path = context.get("project_path")
        if project_path:
            # Run tests if available
            test_results = await self._run_tests(project_path)
            debug_info["test_results"] = test_results
            
            # Check recent git changes
            changes = await self._get_recent_changes(project_path)
            debug_info["recent_changes"] = changes
        
        return debug_info
    
    async def _run_tests(self, project_path: str) -> Dict[str, Any]:
        """Run project tests and capture results"""
        # Implementation would run pytest, npm test, etc.
        return {}
    
    def _extract_test_suggestions(self, response: str) -> List[str]:
        """Extract test suggestions from response"""
        # Parse test suggestions from response
        return []

class CustomModeManager:
    """Manager for custom modes similar to KiloCode's custom modes"""
    
    def __init__(self, modes_dir: Path = None):
        self.modes_dir = modes_dir or Path.home() / ".coding-swarm" / "modes"
        self.custom_modes: Dict[str, ModeConfig] = {}
        self.mode_handlers: Dict[str, BaseModeHandler] = {}
        
        # Initialize built-in modes
        self._initialize_builtin_modes()
        
        # Load custom modes
        self._load_custom_modes()
    
    def _initialize_builtin_modes(self):
        """Initialize built-in mode handlers"""
        self.mode_handlers["architect"] = ArchitectMode()
        self.mode_handlers["coder"] = CoderMode()
        self.mode_handlers["debugger"] = DebuggerMode()
    
    def _load_custom_modes(self):
        """Load custom modes from configuration files"""
        if not self.modes_dir.exists():
            return
        
        for mode_file in self.modes_dir.glob("*.yaml"):
            try:
                with open(mode_file) as f:
                    mode_data = yaml.safe_load(f)
                
                config = ModeConfig(**mode_data)
                self.custom_modes[config.name] = config
                
                # Create generic handler for custom mode
                self.mode_handlers[config.name] = GenericModeHandler(config)
                
            except Exception as e:
                print(f"Failed to load custom mode {mode_file}: {e}")
    
    def create_custom_mode(self, config: ModeConfig):
        """Create a new custom mode"""
        self.custom_modes[config.name] = config
        self.mode_handlers[config.name] = GenericModeHandler(config)
        
        # Save to file
        mode_file = self.modes_dir / f"{config.name}.yaml"
        self.modes_dir.mkdir(parents=True, exist_ok=True)
        
        with open(mode_file, 'w') as f:
            yaml.dump(config.__dict__, f)
    
    def get_mode_handler(self, mode_name: str) -> Optional[BaseModeHandler]:
        """Get mode handler by name"""
        return self.mode_handlers.get(mode_name)
    
    def suggest_mode(self, request: str, context: Dict[str, Any]) -> str:
        """Suggest the best mode for a request"""
        scores = {}
        
        for mode_name, handler in self.mode_handlers.items():
            if handler.can_handle_request(request, context):
                # Simple scoring - could be enhanced with ML
                scores[mode_name] = 1.0
        
        if not scores:
            return "coder"  # Default mode
        
        return max(scores, key=scores.get)

class GenericModeHandler(BaseModeHandler):
    """Generic handler for custom modes"""
    
    async def process_request(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request using custom mode configuration"""
        enhanced_prompt = f"""
{self.config.system_prompt}

Request: {request}
Context: {json.dumps(context, indent=2)}
"""
        
        response = await self._call_llm(enhanced_prompt, context)
        
        return {
            "mode": self.config.name,
            "response": response,
            "suggested_next_mode": self.should_switch_mode(request, context)
        }
    
    def can_handle_request(self, request: str, context: Dict[str, Any]) -> bool:
        """Basic keyword matching for custom modes"""
        # Could be enhanced with more sophisticated matching
        return self.config.name.lower() in request.lower()

# Example of creating a custom mode
EXAMPLE_CUSTOM_MODES = {
    "refactor": ModeConfig(
        name="refactor",
        description="Code refactoring and optimization specialist",
        system_prompt="""You are a refactoring expert focused on improving code quality.
You systematically improve code by:
- Identifying code smells and antipatterns
- Applying design patterns appropriately
- Improving performance and readability
- Maintaining backward compatibility
- Providing clear explanations of changes""",
        tool_permissions=[ToolPermission.READ, ToolPermission.WRITE],
        auto_switch_conditions=["test->debugger", "implement->coder"],
        temperature=0.3  # More conservative for refactoring
    ),
    
    "security": ModeConfig(
        name="security", 
        description="Security analysis and hardening specialist",
        system_prompt="""You are a security expert focused on identifying and fixing vulnerabilities.
You analyze code for:
- Common security vulnerabilities (OWASP Top 10)
- Input validation and sanitization
- Authentication and authorization issues
- Secure coding practices
- Dependency vulnerabilities""",
        tool_permissions=[ToolPermission.READ, ToolPermission.MCP],
        requires_approval=True,
        temperature=0.2  # Very conservative for security
    )
}