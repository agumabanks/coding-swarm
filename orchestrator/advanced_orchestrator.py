# orchestrator/advanced_orchestrator.py
from typing import Dict, List, Any, Optional
import asyncio
from dataclasses import dataclass
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"

@dataclass
class SubTask:
    id: str
    name: str
    mode: str  # architect, coder, debugger
    prompt: str
    dependencies: List[str]
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None

class AdvancedOrchestrator:
    """KiloCode-inspired orchestrator with task delegation and mode specialization."""
    
    def __init__(self):
        self.active_tasks: Dict[str, SubTask] = {}
        self.task_graph: Dict[str, List[str]] = {}
        self.results_cache: Dict[str, Any] = {}
    
    async def orchestrate(self, goal: str, project: str = ".") -> Dict[str, Any]:
        """Break down complex goal into specialized subtasks."""
        
        # 1. Initial planning with Architect
        main_plan = await self._delegate_to_architect(goal, project)
        
        # 2. Create task graph from plan
        subtasks = self._create_subtasks_from_plan(main_plan)
        
        # 3. Execute tasks with dependency resolution
        final_results = await self._execute_task_graph(subtasks)
        
        # 4. Validate and test results
        validation_result = await self._validate_results(final_results, goal)
        
        return {
            "success": validation_result["success"],
            "results": final_results,
            "validation": validation_result,
            "task_history": self.active_tasks
        }
    
    async def _delegate_to_architect(self, goal: str, project: str) -> Dict[str, Any]:
        """Delegate initial planning to Architect agent."""
        from agents import create_agent
        
        context = {"goal": goal, "project": project, "mode": "planning"}
        architect = create_agent("architect", context)
        return await architect.plan()
    
    def _create_subtasks_from_plan(self, plan: Dict[str, Any]) -> List[SubTask]:
        """Convert architect's plan into executable subtasks."""
        subtasks = []
        
        for i, step in enumerate(plan.get("steps", [])):
            # Determine optimal mode for this step
            mode = self._determine_optimal_mode(step)
            
            subtask = SubTask(
                id=f"task_{i}",
                name=step["name"],
                mode=mode,
                prompt=self._create_mode_specific_prompt(step, mode),
                dependencies=step.get("dependencies", []),
                status=TaskStatus.PENDING,
                context={"step_details": step}
            )
            subtasks.append(subtask)
        
        return subtasks
    
    def _determine_optimal_mode(self, step: Dict[str, Any]) -> str:
        """Choose the best agent mode for this step type."""
        step_type = step.get("type", "").lower()
        files_to_modify = step.get("files_to_modify", [])
        
        if "test" in step["name"].lower() or "debug" in step["name"].lower():
            return "debugger"
        elif files_to_modify or "implement" in step["name"].lower():
            return "coder" 
        elif "design" in step["name"].lower() or "plan" in step["name"].lower():
            return "architect"
        else:
            return "coder"  # default
    
    async def _execute_task_graph(self, subtasks: List[SubTask]) -> Dict[str, Any]:
        """Execute subtasks respecting dependencies."""
        results = {}
        
        # Build dependency graph
        self.task_graph = self._build_dependency_graph(subtasks)
        
        # Execute tasks in dependency order
        while subtasks:
            # Find ready tasks (no unmet dependencies)
            ready_tasks = [t for t in subtasks if self._dependencies_met(t)]
            
            if not ready_tasks:
                # Check for circular dependencies or blocking issues
                break
            
            # Execute ready tasks concurrently
            task_futures = [
                self._execute_single_task(task) 
                for task in ready_tasks
            ]
            
            completed_results = await asyncio.gather(*task_futures, return_exceptions=True)
            
            # Process results and update task states
            for task, result in zip(ready_tasks, completed_results):
                if isinstance(result, Exception):
                    task.status = TaskStatus.FAILED
                    # Attempt recovery or fail gracefully
                    result = await self._handle_task_failure(task, result)
                
                task.result = result
                task.status = TaskStatus.COMPLETED
                results[task.id] = result
                subtasks.remove(task)
        
        return results
    
    async def _execute_single_task(self, task: SubTask) -> Dict[str, Any]:
        """Execute a single subtask using the appropriate agent mode."""
        from agents import create_agent
        
        # Build context with results from dependencies
        context = {
            "goal": task.prompt,
            "mode": task.mode,
            "dependencies_results": self._get_dependency_results(task),
            **task.context
        }
        
        # Create and run appropriate agent
        agent = create_agent(task.mode, context)
        
        if task.mode == "architect":
            return await agent.plan()
        elif task.mode == "coder":
            return await agent.generate_code()
        elif task.mode == "debugger":
            return await agent.debug_and_fix()
        else:
            raise ValueError(f"Unknown task mode: {task.mode}")