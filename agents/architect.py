# Enhanced Architect Agent (agents/architect.py)
from __future__ import annotations
import asyncio
from typing import Dict, List, Any
from dataclasses import dataclass
from .base import Agent
from .tools import FileReader, ProjectAnalyzer, LLMClient

@dataclass
class PlanStep:
    name: str
    description: str
    dependencies: List[str]
    estimated_effort: str
    files_to_modify: List[str]
    tests_required: List[str]

class Architect(Agent):
    """Advanced planning agent with context awareness and tool integration."""
    
    def __init__(self, context: Dict[str, Any]):
        super().__init__(context)
        self.file_reader = FileReader()
        self.project_analyzer = ProjectAnalyzer()
        self.llm_client = LLMClient()
        self.memory_bank = self._load_memory_bank()
    
    async def plan(self) -> Dict[str, Any]:
        """Generate comprehensive project plan with dependencies and context."""
        goal = self.context.get("goal", "")
        project_root = self.context.get("project", ".")
        
        # 1. Analyze current project state
        project_context = await self.project_analyzer.analyze(project_root)
        
        # 2. Read relevant files for context
        relevant_files = await self._identify_relevant_files(goal, project_context)
        file_contents = await self.file_reader.read_multiple(relevant_files)
        
        # 3. Generate plan using LLM with rich context
        system_prompt = self._build_architect_system_prompt()
        user_prompt = self._build_planning_prompt(goal, project_context, file_contents)
        
        raw_plan = await self.llm_client.chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        # 4. Parse and structure the plan
        structured_plan = await self._parse_plan(raw_plan)
        
        # 5. Store in artifacts and memory
        self.artifacts["plan"] = structured_plan
        self.artifacts["context"] = project_context
        await self._update_memory_bank(goal, structured_plan)
        
        return structured_plan
    
    def _build_architect_system_prompt(self) -> str:
        return """You are a Senior Software Architect AI agent specializing in:
- System design and architecture planning
- Breaking complex goals into executable steps
- Dependency analysis and risk assessment
- Code quality and maintainability

RESPONSE FORMAT: Return a JSON structure with:
{
  "overview": "High-level approach summary",
  "steps": [
    {
      "name": "Step name",
      "description": "Detailed description",
      "dependencies": ["dependency1", "dependency2"],
      "files_to_modify": ["file1.py", "file2.py"],
      "tests_required": ["test1.py::test_function"],
      "estimated_effort": "small|medium|large"
    }
  ],
  "risks": ["risk1", "risk2"],
  "success_criteria": ["criteria1", "criteria2"]
}"""

    async def _identify_relevant_files(self, goal: str, project_context: Dict) -> List[str]:
        # Use semantic search on project files
        return await self.project_analyzer.find_relevant_files(goal, project_context)
    
    async def _update_memory_bank(self, goal: str, plan: Dict[str, Any]):
        # Implement memory persistence like KiloCode's Memory Bank
        memory_entry = {
            "timestamp": asyncio.get_event_loop().time(),
            "goal": goal,
            "plan_summary": plan.get("overview", ""),
            "key_decisions": plan.get("risks", [])
        }
        # Persist to .swarm/memory-bank/