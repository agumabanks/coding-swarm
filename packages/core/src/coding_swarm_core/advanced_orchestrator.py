"""
Advanced Agent Orchestrator with Conflict Resolution and Self-Learning
Provides intelligent agent coordination, conflict resolution, and autonomous optimization
"""
from __future__ import annotations

import asyncio
import json
import time
import random
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import heapq
from pathlib import Path


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CONFLICT = "conflict"


class ConflictType(Enum):
    RESOURCE_CONFLICT = "resource_conflict"
    DEPENDENCY_CYCLE = "dependency_cycle"
    AGENT_OVERLOAD = "agent_overload"
    PRIORITY_CONFLICT = "priority_conflict"
    CAPABILITY_MISMATCH = "capability_mismatch"


@dataclass
class SubTask:
    """Enhanced subtask with conflict tracking"""
    id: str
    name: str
    mode: str
    prompt: str
    dependencies: List[str]
    status: TaskStatus
    result: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    priority: int = 1
    estimated_duration: float = 0.0
    actual_duration: float = 0.0
    agent_id: Optional[str] = None
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class Conflict:
    """Represents a conflict between tasks or agents"""
    id: str
    type: ConflictType
    description: str
    involved_tasks: List[str]
    severity: str  # 'low', 'medium', 'high', 'critical'
    resolution_strategy: str
    status: str  # 'detected', 'resolving', 'resolved', 'failed'
    created_at: datetime
    resolved_at: Optional[datetime] = None


@dataclass
class AgentProfile:
    """Profile of an agent's capabilities and performance"""
    agent_id: str
    capabilities: List[str]
    performance_score: float
    current_load: int
    max_concurrent_tasks: int
    specialization_score: Dict[str, float]
    success_rate: float
    average_response_time: float


@dataclass
class ExecutionPattern:
    """Learned execution pattern for optimization"""
    pattern_id: str
    task_sequence: List[str]
    success_rate: float
    average_duration: float
    resource_usage: Dict[str, float]
    last_used: datetime
    usage_count: int


class ConflictResolutionEngine:
    """Intelligent conflict resolution system"""

    def __init__(self):
        self.conflicts: Dict[str, Conflict] = {}
        self.resolution_strategies = self._load_resolution_strategies()

    def _load_resolution_strategies(self) -> Dict[str, Callable]:
        """Load conflict resolution strategies"""
        return {
            'resource_conflict': self._resolve_resource_conflict,
            'dependency_cycle': self._resolve_dependency_cycle,
            'agent_overload': self._resolve_agent_overload,
            'priority_conflict': self._resolve_priority_conflict,
            'capability_mismatch': self._resolve_capability_mismatch
        }

    async def detect_conflicts(self, subtasks: List[SubTask], agent_profiles: Dict[str, AgentProfile]) -> List[Conflict]:
        """Detect various types of conflicts in the task graph"""
        conflicts = []

        # Check for resource conflicts
        conflicts.extend(self._detect_resource_conflicts(subtasks, agent_profiles))

        # Check for dependency cycles
        conflicts.extend(self._detect_dependency_cycles(subtasks))

        # Check for agent overload
        conflicts.extend(self._detect_agent_overload(subtasks, agent_profiles))

        # Check for priority conflicts
        conflicts.extend(self._detect_priority_conflicts(subtasks))

        # Check for capability mismatches
        conflicts.extend(self._detect_capability_mismatches(subtasks, agent_profiles))

        return conflicts

    async def resolve_conflict(self, conflict: Conflict, subtasks: List[SubTask], agent_profiles: Dict[str, AgentProfile]) -> bool:
        """Resolve a specific conflict"""
        if conflict.type.value not in self.resolution_strategies:
            return False

        strategy = self.resolution_strategies[conflict.type.value]
        success = await strategy(conflict, subtasks, agent_profiles)

        if success:
            conflict.status = 'resolved'
            conflict.resolved_at = datetime.utcnow()
        else:
            conflict.status = 'failed'

        return success

    def _detect_resource_conflicts(self, subtasks: List[SubTask], agent_profiles: Dict[str, AgentProfile]) -> List[Conflict]:
        """Detect resource conflicts between tasks"""
        conflicts = []
        resource_usage = defaultdict(list)

        for task in subtasks:
            if task.agent_id:
                resource_usage[task.agent_id].append(task)

        for agent_id, tasks in resource_usage.items():
            if agent_id in agent_profiles:
                profile = agent_profiles[agent_id]
                if len(tasks) > profile.max_concurrent_tasks:
                    conflict = Conflict(
                        id=f"resource_{agent_id}_{len(tasks)}",
                        type=ConflictType.RESOURCE_CONFLICT,
                        description=f"Agent {agent_id} overloaded with {len(tasks)} tasks",
                        involved_tasks=[t.id for t in tasks],
                        severity='high',
                        resolution_strategy='redistribute_tasks',
                        status='detected',
                        created_at=datetime.utcnow()
                    )
                    conflicts.append(conflict)

        return conflicts

    def _detect_dependency_cycles(self, subtasks: List[SubTask]) -> List[Conflict]:
        """Detect circular dependencies in task graph"""
        conflicts = []

        # Build dependency graph
        graph = defaultdict(list)
        for task in subtasks:
            graph[task.id] = task.dependencies

        # Check for cycles using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for dependency in graph[node]:
                if dependency not in visited:
                    if has_cycle(dependency):
                        return True
                elif dependency in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for task in subtasks:
            if task.id not in visited:
                if has_cycle(task.id):
                    conflict = Conflict(
                        id=f"cycle_{task.id}",
                        type=ConflictType.DEPENDENCY_CYCLE,
                        description=f"Dependency cycle detected involving task {task.id}",
                        involved_tasks=[task.id],
                        severity='critical',
                        resolution_strategy='break_cycle',
                        status='detected',
                        created_at=datetime.utcnow()
                    )
                    conflicts.append(conflict)

        return conflicts

    def _detect_agent_overload(self, subtasks: List[SubTask], agent_profiles: Dict[str, AgentProfile]) -> List[Conflict]:
        """Detect agent overload situations"""
        conflicts = []
        agent_load = defaultdict(int)

        for task in subtasks:
            if task.status == TaskStatus.IN_PROGRESS and task.agent_id:
                agent_load[task.agent_id] += 1

        for agent_id, load in agent_load.items():
            if agent_id in agent_profiles:
                profile = agent_profiles[agent_id]
                if load > profile.max_concurrent_tasks:
                    conflict = Conflict(
                        id=f"overload_{agent_id}",
                        type=ConflictType.AGENT_OVERLOAD,
                        description=f"Agent {agent_id} overloaded with {load} concurrent tasks",
                        involved_tasks=[],  # All tasks assigned to this agent
                        severity='medium',
                        resolution_strategy='reassign_tasks',
                        status='detected',
                        created_at=datetime.utcnow()
                    )
                    conflicts.append(conflict)

        return conflicts

    def _detect_priority_conflicts(self, subtasks: List[SubTask]) -> List[Conflict]:
        """Detect priority conflicts between dependent tasks"""
        conflicts = []

        for task in subtasks:
            for dep_id in task.dependencies:
                dep_task = next((t for t in subtasks if t.id == dep_id), None)
                if dep_task and dep_task.priority < task.priority:
                    conflict = Conflict(
                        id=f"priority_{task.id}_{dep_id}",
                        type=ConflictType.PRIORITY_CONFLICT,
                        description=f"Task {task.id} (priority {task.priority}) depends on lower priority task {dep_id} (priority {dep_task.priority})",
                        involved_tasks=[task.id, dep_id],
                        severity='low',
                        resolution_strategy='adjust_priorities',
                        status='detected',
                        created_at=datetime.utcnow()
                    )
                    conflicts.append(conflict)

        return conflicts

    def _detect_capability_mismatches(self, subtasks: List[SubTask], agent_profiles: Dict[str, AgentProfile]) -> List[Conflict]:
        """Detect capability mismatches between tasks and assigned agents"""
        conflicts = []

        for task in subtasks:
            if task.agent_id and task.agent_id in agent_profiles:
                profile = agent_profiles[task.agent_id]
                required_capability = task.mode

                if required_capability not in profile.capabilities:
                    conflict = Conflict(
                        id=f"capability_{task.id}_{task.agent_id}",
                        type=ConflictType.CAPABILITY_MISMATCH,
                        description=f"Task {task.id} requires {required_capability} capability not available in agent {task.agent_id}",
                        involved_tasks=[task.id],
                        severity='high',
                        resolution_strategy='reassign_task',
                        status='detected',
                        created_at=datetime.utcnow()
                    )
                    conflicts.append(conflict)

        return conflicts

    async def _resolve_resource_conflict(self, conflict: Conflict, subtasks: List[SubTask], agent_profiles: Dict[str, AgentProfile]) -> bool:
        """Resolve resource conflict by redistributing tasks"""
        # Find overloaded agent
        overloaded_agent = None
        for task_id in conflict.involved_tasks:
            task = next((t for t in subtasks if t.id == task_id), None)
            if task and task.agent_id:
                overloaded_agent = task.agent_id
                break

        if not overloaded_agent:
            return False

        # Find available agents with similar capabilities
        available_agents = []
        for agent_id, profile in agent_profiles.items():
            if agent_id != overloaded_agent and profile.current_load < profile.max_concurrent_tasks:
                available_agents.append((agent_id, profile))

        if not available_agents:
            return False

        # Redistribute tasks to available agents
        tasks_to_reassign = [t for t in subtasks if t.agent_id == overloaded_agent and t.status == TaskStatus.PENDING]

        for i, task in enumerate(tasks_to_reassign):
            if i < len(available_agents):
                new_agent = available_agents[i][0]
                task.agent_id = new_agent
                agent_profiles[new_agent].current_load += 1

        return True

    async def _resolve_dependency_cycle(self, conflict: Conflict, subtasks: List[SubTask], agent_profiles: Dict[str, AgentProfile]) -> bool:
        """Resolve dependency cycle by breaking it"""
        # Simple strategy: remove one dependency to break the cycle
        # In production, this would be more sophisticated
        for task in subtasks:
            if task.dependencies:
                # Remove the last dependency (arbitrary choice)
                removed_dep = task.dependencies.pop()
                print(f"Removed dependency {removed_dep} from task {task.id} to break cycle")
                return True

        return False

    async def _resolve_agent_overload(self, conflict: Conflict, subtasks: List[SubTask], agent_profiles: Dict[str, AgentProfile]) -> bool:
        """Resolve agent overload by reassigning tasks"""
        return await self._resolve_resource_conflict(conflict, subtasks, agent_profiles)

    async def _resolve_priority_conflict(self, conflict: Conflict, subtasks: List[SubTask], agent_profiles: Dict[str, AgentProfile]) -> bool:
        """Resolve priority conflict by adjusting priorities"""
        if len(conflict.involved_tasks) == 2:
            task_id, dep_id = conflict.involved_tasks
            task = next((t for t in subtasks if t.id == task_id), None)
            dep_task = next((t for t in subtasks if t.id == dep_id), None)

            if task and dep_task:
                # Increase dependency priority to match or exceed task priority
                dep_task.priority = max(dep_task.priority, task.priority)
                return True

        return False

    async def _resolve_capability_mismatch(self, conflict: Conflict, subtasks: List[SubTask], agent_profiles: Dict[str, AgentProfile]) -> bool:
        """Resolve capability mismatch by reassigning task"""
        if not conflict.involved_tasks:
            return False

        task_id = conflict.involved_tasks[0]
        task = next((t for t in subtasks if t.id == task_id), None)

        if not task:
            return False

        required_capability = task.mode

        # Find agent with required capability
        for agent_id, profile in agent_profiles.items():
            if (required_capability in profile.capabilities and
                profile.current_load < profile.max_concurrent_tasks):
                task.agent_id = agent_id
                profile.current_load += 1
                return True

        return False


class SelfLearningAlgorithm:
    """Self-learning system for workflow optimization"""

    def __init__(self):
        self.execution_patterns: Dict[str, ExecutionPattern] = {}
        self.performance_history: List[Dict[str, Any]] = []
        self.learning_rate = 0.1

    async def learn_from_execution(self, execution_data: Dict[str, Any]):
        """Learn from task execution results"""
        # Extract pattern from execution
        pattern = self._extract_pattern(execution_data)

        if pattern:
            pattern_key = self._generate_pattern_key(pattern)

            if pattern_key in self.execution_patterns:
                # Update existing pattern
                existing = self.execution_patterns[pattern_key]
                existing.success_rate = self._update_moving_average(
                    existing.success_rate, execution_data['success'], existing.usage_count
                )
                existing.average_duration = self._update_moving_average(
                    existing.average_duration, execution_data['duration'], existing.usage_count
                )
                existing.usage_count += 1
                existing.last_used = datetime.utcnow()
            else:
                # Create new pattern
                self.execution_patterns[pattern_key] = ExecutionPattern(
                    pattern_id=pattern_key,
                    task_sequence=pattern['sequence'],
                    success_rate=execution_data['success'],
                    average_duration=execution_data['duration'],
                    resource_usage=execution_data.get('resource_usage', {}),
                    last_used=datetime.utcnow(),
                    usage_count=1
                )

        # Store execution data for future learning
        self.performance_history.append(execution_data)

        # Keep only recent history
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]

    def _extract_pattern(self, execution_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract execution pattern from data"""
        if 'tasks' not in execution_data:
            return None

        tasks = execution_data['tasks']
        sequence = [task['mode'] for task in tasks]

        return {
            'sequence': sequence,
            'success': execution_data.get('success', False),
            'duration': execution_data.get('duration', 0.0)
        }

    def _generate_pattern_key(self, pattern: Dict[str, Any]) -> str:
        """Generate unique key for pattern"""
        return '_'.join(pattern['sequence'])

    def _update_moving_average(self, current_avg: float, new_value: float, count: int) -> float:
        """Update moving average with new value"""
        return current_avg + (new_value - current_avg) / (count + 1)

    def predict_execution_time(self, task_sequence: List[str]) -> float:
        """Predict execution time for task sequence"""
        pattern_key = '_'.join(task_sequence)

        if pattern_key in self.execution_patterns:
            pattern = self.execution_patterns[pattern_key]
            return pattern.average_duration

        # Fallback: estimate based on individual task times
        return len(task_sequence) * 30.0  # 30 seconds per task average

    def suggest_optimization(self, current_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest optimizations based on learned patterns"""
        suggestions = {
            'task_reordering': [],
            'parallelization_opportunities': [],
            'resource_optimization': []
        }

        # Analyze task dependencies and suggest reordering
        if 'tasks' in current_plan:
            task_modes = [task.get('mode', 'unknown') for task in current_plan['tasks']]

            # Look for known efficient patterns
            for pattern_key, pattern in self.execution_patterns.items():
                if (pattern.success_rate > 0.8 and
                    self._sequence_similarity(task_modes, pattern.task_sequence) > 0.7):
                    suggestions['task_reordering'].append({
                        'pattern': pattern.task_sequence,
                        'expected_improvement': pattern.average_duration
                    })

        return suggestions

    def _sequence_similarity(self, seq1: List[str], seq2: List[str]) -> float:
        """Calculate similarity between two sequences"""
        if len(seq1) != len(seq2):
            return 0.0

        matches = sum(1 for a, b in zip(seq1, seq2) if a == b)
        return matches / len(seq1)


class IntelligentScheduler:
    """Intelligent task scheduling with optimization"""

    def __init__(self):
        self.task_queue: List[Tuple[int, SubTask]] = []
        self.agent_assignments: Dict[str, List[SubTask]] = defaultdict(list)

    def schedule_task(self, task: SubTask, priority_boost: int = 0):
        """Schedule task with priority"""
        # Calculate effective priority (higher number = higher priority)
        effective_priority = task.priority + priority_boost

        # Use negative priority for min-heap (Python's heapq is min-heap)
        heapq.heappush(self.task_queue, (-effective_priority, task))

    def get_next_task(self, agent_id: str, agent_capabilities: List[str]) -> Optional[SubTask]:
        """Get next suitable task for agent"""
        # Look for tasks this agent can handle
        temp_queue = []

        while self.task_queue:
            neg_priority, task = heapq.heappop(self.task_queue)

            if task.mode in agent_capabilities and task.status == TaskStatus.PENDING:
                # Check if dependencies are met
                if self._dependencies_met(task):
                    return task

            # Put back tasks we can't handle yet
            temp_queue.append((neg_priority, task))

        # Restore queue
        for item in temp_queue:
            heapq.heappush(self.task_queue, item)

        return None

    def assign_task_to_agent(self, task: SubTask, agent_id: str):
        """Assign task to specific agent"""
        task.agent_id = agent_id
        task.status = TaskStatus.IN_PROGRESS
        self.agent_assignments[agent_id].append(task)

    def _dependencies_met(self, task: SubTask) -> bool:
        """Check if task dependencies are satisfied"""
        # This would need access to the full task list
        # For now, assume dependencies are met
        return True

    def get_agent_workload(self, agent_id: str) -> int:
        """Get current workload for agent"""
        return len([t for t in self.agent_assignments[agent_id] if t.status == TaskStatus.IN_PROGRESS])


class AdvancedOrchestrator:
    """Advanced orchestrator with conflict resolution and self-learning"""

    def __init__(self):
        self.active_tasks: Dict[str, SubTask] = {}
        self.task_graph: Dict[str, List[str]] = {}
        self.results_cache: Dict[str, Any] = {}

        # Advanced components
        self.conflict_resolver = ConflictResolutionEngine()
        self.learning_engine = SelfLearningAlgorithm()
        self.task_scheduler = IntelligentScheduler()
        self.agent_profiles: Dict[str, AgentProfile] = {}

    async def orchestrate(self, goal: str, project: str = ".") -> Dict[str, Any]:
        """Execute complex goal with advanced coordination"""
        start_time = time.time()

        # 1. Initial planning with Architect
        main_plan = await self._delegate_to_architect(goal, project)

        # 2. Create enhanced task graph
        subtasks = self._create_subtasks_from_plan(main_plan)

        # 3. Initialize agent profiles
        await self._initialize_agent_profiles()

        # 4. Assign tasks to agents
        await self._assign_tasks_to_agents(subtasks)

        # 5. Detect and resolve conflicts
        conflicts = await self.conflict_resolver.detect_conflicts(subtasks, self.agent_profiles)
        resolved_conflicts = await self._resolve_conflicts(conflicts, subtasks)

        # 6. Execute tasks with intelligent scheduling
        final_results = await self._execute_task_graph(subtasks)

        # 7. Learn from execution
        execution_data = {
            'goal': goal,
            'tasks': [{'id': t.id, 'mode': t.mode, 'duration': t.actual_duration} for t in subtasks],
            'success': all(r.get('success', False) for r in final_results.values()),
            'duration': time.time() - start_time,
            'conflicts_resolved': len(resolved_conflicts)
        }
        await self.learning_engine.learn_from_execution(execution_data)

        # 8. Generate optimization suggestions
        optimization_suggestions = self.learning_engine.suggest_optimization(main_plan)

        return {
            "success": execution_data['success'],
            "results": final_results,
            "conflicts_detected": len(conflicts),
            "conflicts_resolved": len(resolved_conflicts),
            "execution_time": execution_data['duration'],
            "optimization_suggestions": optimization_suggestions,
            "task_history": self.active_tasks
        }

    async def _delegate_to_architect(self, goal: str, project: str) -> Dict[str, Any]:
        """Delegate initial planning to Architect agent"""
        from coding_swarm_agents import create_agent

        context = {"goal": goal, "project": project, "mode": "planning"}
        architect = create_agent("architect", context)
        return await architect.plan()

    def _create_subtasks_from_plan(self, plan: Dict[str, Any]) -> List[SubTask]:
        """Convert architect's plan into enhanced subtasks"""
        subtasks = []

        for i, step in enumerate(plan.get("steps", [])):
            # Determine optimal mode for this step
            mode = self._determine_optimal_mode(step)

            # Estimate duration based on learned patterns
            estimated_duration = self.learning_engine.predict_execution_time([mode])

            subtask = SubTask(
                id=f"task_{i}",
                name=step["name"],
                mode=mode,
                prompt=self._create_mode_specific_prompt(step, mode),
                dependencies=step.get("dependencies", []),
                status=TaskStatus.PENDING,
                context={"step_details": step},
                priority=step.get("priority", 1),
                estimated_duration=estimated_duration
            )
            subtasks.append(subtask)

        return subtasks

    def _determine_optimal_mode(self, step: Dict[str, Any]) -> str:
        """Choose the best agent mode for this step"""
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

    def _create_mode_specific_prompt(self, step: Dict[str, Any], mode: str) -> str:
        """Create mode-specific prompt for task"""
        base_prompt = f"Task: {step['name']}\nDescription: {step.get('description', '')}"

        if mode == "architect":
            return f"As an architect, {base_prompt}\nFocus on design and planning aspects."
        elif mode == "coder":
            return f"As a coder, {base_prompt}\nFocus on implementation and code quality."
        elif mode == "debugger":
            return f"As a debugger, {base_prompt}\nFocus on testing and issue resolution."
        else:
            return base_prompt

    async def _initialize_agent_profiles(self):
        """Initialize agent capability profiles"""
        # This would load from a configuration file or database
        # For now, create sample profiles
        self.agent_profiles = {
            "architect_agent": AgentProfile(
                agent_id="architect_agent",
                capabilities=["architect", "planning"],
                performance_score=0.9,
                current_load=0,
                max_concurrent_tasks=2,
                specialization_score={"architect": 0.95, "planning": 0.9},
                success_rate=0.92,
                average_response_time=45.0
            ),
            "coder_agent": AgentProfile(
                agent_id="coder_agent",
                capabilities=["coder", "implementation"],
                performance_score=0.85,
                current_load=0,
                max_concurrent_tasks=3,
                specialization_score={"coder": 0.9, "implementation": 0.85},
                success_rate=0.88,
                average_response_time=60.0
            ),
            "debugger_agent": AgentProfile(
                agent_id="debugger_agent",
                capabilities=["debugger", "testing"],
                performance_score=0.8,
                current_load=0,
                max_concurrent_tasks=2,
                specialization_score={"debugger": 0.85, "testing": 0.8},
                success_rate=0.85,
                average_response_time=30.0
            )
        }

    async def _assign_tasks_to_agents(self, subtasks: List[SubTask]):
        """Assign tasks to agents based on capabilities and load"""
        for task in subtasks:
            # Find best agent for this task
            best_agent = self._find_best_agent(task)

            if best_agent:
                task.agent_id = best_agent
                self.agent_profiles[best_agent].current_load += 1
                self.task_scheduler.assign_task_to_agent(task, best_agent)

    def _find_best_agent(self, task: SubTask) -> Optional[str]:
        """Find best agent for task based on capabilities and load"""
        best_agent = None
        best_score = -1

        for agent_id, profile in self.agent_profiles.items():
            if (task.mode in profile.capabilities and
                profile.current_load < profile.max_concurrent_tasks):

                # Calculate suitability score
                capability_score = profile.specialization_score.get(task.mode, 0.5)
                load_factor = 1.0 - (profile.current_load / profile.max_concurrent_tasks)
                performance_factor = profile.performance_score

                total_score = (capability_score * 0.4 + load_factor * 0.3 + performance_factor * 0.3)

                if total_score > best_score:
                    best_score = total_score
                    best_agent = agent_id

        return best_agent

    async def _resolve_conflicts(self, conflicts: List[Conflict], subtasks: List[SubTask]) -> List[Conflict]:
        """Resolve detected conflicts"""
        resolved = []

        for conflict in conflicts:
            success = await self.conflict_resolver.resolve_conflict(conflict, subtasks, self.agent_profiles)
            if success:
                resolved.append(conflict)

        return resolved

    async def _execute_task_graph(self, subtasks: List[SubTask]) -> Dict[str, Any]:
        """Execute subtasks with intelligent scheduling"""
        results = {}

        # Schedule all tasks
        for task in subtasks:
            self.task_scheduler.schedule_task(task)

        # Execute tasks concurrently with agent coordination
        pending_tasks = subtasks.copy()
        active_tasks = set()

        while pending_tasks or active_tasks:
            # Get completed tasks
            completed_tasks = []
            for task in list(active_tasks):
                if task.status == TaskStatus.COMPLETED:
                    active_tasks.remove(task)
                    completed_tasks.append(task)
                    results[task.id] = task.result

            # Process completed tasks
            for task in completed_tasks:
                if task.agent_id:
                    self.agent_profiles[task.agent_id].current_load -= 1

            # Schedule new tasks
            for agent_id, profile in self.agent_profiles.items():
                if profile.current_load < profile.max_concurrent_tasks:
                    next_task = self.task_scheduler.get_next_task(agent_id, profile.capabilities)
                    if next_task:
                        active_tasks.add(next_task)
                        profile.current_load += 1
                        asyncio.create_task(self._execute_single_task(next_task))

            # Small delay to prevent busy waiting
            await asyncio.sleep(0.1)

        return results

    async def _execute_single_task(self, task: SubTask) -> Dict[str, Any]:
        """Execute a single subtask using the appropriate agent mode"""
        start_time = time.time()

        try:
            from coding_swarm_agents import create_agent

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
                result = await agent.plan()
            elif task.mode == "coder":
                result = await agent.generate_code()
            elif task.mode == "debugger":
                result = await agent.debug_and_fix()
            else:
                result = {"error": f"Unknown task mode: {task.mode}"}

            task.result = result
            task.status = TaskStatus.COMPLETED

        except Exception as e:
            task.result = {"error": str(e)}
            task.status = TaskStatus.FAILED

            # Handle retries
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                # Re-schedule task
                self.task_scheduler.schedule_task(task, priority_boost=1)

        task.actual_duration = time.time() - start_time

        return task.result

    def _get_dependency_results(self, task: SubTask) -> Dict[str, Any]:
        """Get results from dependency tasks"""
        results = {}
        for dep_id in task.dependencies:
            if dep_id in self.active_tasks:
                dep_task = self.active_tasks[dep_id]
                results[dep_id] = dep_task.result
        return results


# Global advanced orchestrator instance
advanced_orchestrator = AdvancedOrchestrator()


def get_advanced_orchestrator() -> AdvancedOrchestrator:
    """Get global advanced orchestrator instance"""
    return advanced_orchestrator