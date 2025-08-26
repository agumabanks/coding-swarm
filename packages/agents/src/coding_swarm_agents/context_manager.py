# agents/context_manager.py
import json
import os
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
import hashlib

@dataclass
class MemoryEntry:
    timestamp: float
    goal: str
    context: Dict[str, Any]
    decisions: List[str]
    outcomes: List[str]
    files_modified: List[str]
    
class MemoryBank:
    """KiloCode-inspired persistent context management."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.memory_dir = self.project_root / ".swarm" / "memory-bank"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.brief_file = self.memory_dir / "brief.md"
        self.history_file = self.memory_dir / "history.jsonl"
        self.context_file = self.memory_dir / "context.json"
    
    async def initialize_memory_bank(self, project_description: str):
        """Initialize memory bank for new project."""
        brief_content = f"""# Project Brief

## Overview
{project_description}

## Architecture Decisions
- TBD

## Current Status
- Project initialization complete
- Memory bank activated

## Key Technologies
- Python
- Local LLM (Qwen/Llama)
- FastAPI
- Git

## Next Steps
- Define initial architecture
- Set up development environment
- Implement core features
"""
        self.brief_file.write_text(brief_content)
        
        initial_context = {
            "project_type": "python",
            "ai_provider": "local_llm",
            "development_stage": "initial",
            "key_patterns": []
        }
        self._save_context(initial_context)
    
    async def update_memory(self, goal: str, decisions: List[str], outcomes: List[str], files_modified: List[str]):
        """Add new memory entry."""
        import time
        
        entry = MemoryEntry(
            timestamp=time.time(),
            goal=goal,
            context=self._load_context(),
            decisions=decisions,
            outcomes=outcomes,
            files_modified=files_modified
        )
        
        # Append to history
        with open(self.history_file, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")
        
        # Update context with new learnings
        await self._update_context_from_entry(entry)
    
    def get_relevant_context(self, goal: str, max_entries: int = 5) -> str:
        """Get relevant historical context for current goal."""
        if not self.history_file.exists():
            return ""
        
        # Load recent entries
        entries = []
        with open(self.history_file, "r") as f:
            for line in f:
                entries.append(json.loads(line.strip()))
        
        # Score entries by relevance to current goal
        scored_entries = []
        for entry in entries:
            relevance_score = self._calculate_relevance(goal, entry)
            scored_entries.append((relevance_score, entry))
        
        # Return top N most relevant entries
        scored_entries.sort(reverse=True)
        relevant_entries = [entry for _, entry in scored_entries[:max_entries]]
        
        return self._format_context(relevant_entries)
    
    def _calculate_relevance(self, goal: str, entry: Dict[str, Any]) -> float:
        """Simple relevance scoring based on keyword overlap."""
        goal_words = set(goal.lower().split())
        entry_words = set(entry.get("goal", "").lower().split())
        
        if not goal_words or not entry_words:
            return 0.0
        
        overlap = len(goal_words.intersection(entry_words))
        return overlap / len(goal_words.union(entry_words))