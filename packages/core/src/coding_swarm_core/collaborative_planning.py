"""
Collaborative Planning Interface for Sanaa
Enables real-time collaborative planning with version control and feedback collection
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import difflib


class CollaborationEvent(Enum):
    PLAN_CREATED = "plan_created"
    PLAN_UPDATED = "plan_updated"
    TASK_ADDED = "task_added"
    TASK_MODIFIED = "task_modified"
    TASK_DELETED = "task_deleted"
    COMMENT_ADDED = "comment_added"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    VOTE_CAST = "vote_cast"


class PlanStatus(Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    IMPLEMENTING = "implementing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class PlanVersion:
    """Represents a version of a planning document"""
    version_id: str
    plan_id: str
    content: Dict[str, Any]
    author: str
    timestamp: datetime
    change_summary: str
    parent_version: Optional[str] = None
    diff: Optional[Dict[str, Any]] = None


@dataclass
class CollaborativePlan:
    """Main collaborative planning document"""
    plan_id: str
    title: str
    description: str
    goal: str
    status: PlanStatus
    created_by: str
    created_at: datetime
    updated_at: datetime
    stakeholders: Set[str]
    current_version: str
    versions: Dict[str, PlanVersion] = field(default_factory=dict)
    tasks: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    comments: List[Dict[str, Any]] = field(default_factory=list)
    votes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    active_users: Set[str] = field(default_factory=set)


@dataclass
class Comment:
    """Represents a comment on a plan or task"""
    comment_id: str
    plan_id: str
    task_id: Optional[str]
    author: str
    content: str
    timestamp: datetime
    parent_comment: Optional[str] = None
    replies: List[str] = field(default_factory=list)
    reactions: Dict[str, int] = field(default_factory=dict)


@dataclass
class Vote:
    """Represents a vote on a plan or task"""
    vote_id: str
    plan_id: str
    task_id: Optional[str]
    voter: str
    vote_type: str  # 'approve', 'reject', 'block'
    reason: Optional[str]
    timestamp: datetime


class RealTimeCollaboration:
    """Real-time collaboration system using WebSocket connections"""

    def __init__(self):
        self.connections: Dict[str, Dict[str, Any]] = {}  # user_id -> connection info
        self.plan_sessions: Dict[str, Set[str]] = defaultdict(set)  # plan_id -> active users
        self.user_sessions: Dict[str, str] = {}  # user_id -> plan_id
        self.message_queues: Dict[str, asyncio.Queue] = {}

    async def join_plan_session(self, user_id: str, plan_id: str, websocket: Any):
        """Join a collaborative planning session"""
        # Leave previous session if any
        if user_id in self.user_sessions:
            await self.leave_plan_session(user_id)

        # Join new session
        self.connections[user_id] = {
            'plan_id': plan_id,
            'websocket': websocket,
            'joined_at': datetime.utcnow()
        }

        self.plan_sessions[plan_id].add(user_id)
        self.user_sessions[user_id] = plan_id
        self.message_queues[user_id] = asyncio.Queue()

        # Notify other participants
        await self.broadcast_to_plan(plan_id, {
            'event': CollaborationEvent.USER_JOINED.value,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        }, exclude_user=user_id)

        # Start message processing for this user
        asyncio.create_task(self._process_user_messages(user_id))

    async def leave_plan_session(self, user_id: str):
        """Leave current planning session"""
        if user_id not in self.user_sessions:
            return

        plan_id = self.user_sessions[user_id]

        # Remove from session
        if plan_id in self.plan_sessions:
            self.plan_sessions[plan_id].discard(user_id)

        # Clean up
        if user_id in self.connections:
            del self.connections[user_id]
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        if user_id in self.message_queues:
            del self.message_queues[user_id]

        # Notify other participants
        await self.broadcast_to_plan(plan_id, {
            'event': CollaborationEvent.USER_LEFT.value,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })

    async def broadcast_to_plan(self, plan_id: str, message: Dict[str, Any], exclude_user: Optional[str] = None):
        """Broadcast message to all users in a plan session"""
        if plan_id not in self.plan_sessions:
            return

        for user_id in self.plan_sessions[plan_id]:
            if user_id != exclude_user and user_id in self.message_queues:
                await self.message_queues[user_id].put(message)

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to specific user"""
        if user_id in self.message_queues:
            await self.message_queues[user_id].put(message)

    async def _process_user_messages(self, user_id: str):
        """Process messages for a specific user"""
        try:
            while user_id in self.connections:
                websocket = self.connections[user_id]['websocket']
                queue = self.message_queues[user_id]

                # Wait for message with timeout
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=1.0)
                    await websocket.send_json(message)
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    if user_id in self.connections:
                        await websocket.send_json({"type": "ping", "timestamp": datetime.utcnow().isoformat()})

        except Exception as e:
            print(f"Error processing messages for {user_id}: {e}")
        finally:
            await self.leave_plan_session(user_id)

    def get_active_users(self, plan_id: str) -> List[str]:
        """Get list of active users in a plan session"""
        return list(self.plan_sessions.get(plan_id, set()))

    def is_user_active(self, user_id: str) -> bool:
        """Check if user is currently active in any session"""
        return user_id in self.connections


class PlanningVersionControl:
    """Version control system for planning documents"""

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path.home() / ".sanaa" / "plans"
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def create_version(self, plan: CollaborativePlan, author: str, change_summary: str) -> PlanVersion:
        """Create a new version of a plan"""
        version_id = str(uuid.uuid4())

        # Get current content
        current_content = self._plan_to_dict(plan)

        # Create version
        version = PlanVersion(
            version_id=version_id,
            plan_id=plan.plan_id,
            content=current_content,
            author=author,
            timestamp=datetime.utcnow(),
            change_summary=change_summary,
            parent_version=plan.current_version
        )

        # Calculate diff if there's a parent version
        if plan.current_version and plan.current_version in plan.versions:
            parent_content = plan.versions[plan.current_version].content
            version.diff = self._calculate_diff(parent_content, current_content)

        # Add to plan
        plan.versions[version_id] = version
        plan.current_version = version_id
        plan.updated_at = datetime.utcnow()

        # Save to disk
        self._save_plan(plan)

        return version

    def get_version(self, plan_id: str, version_id: str) -> Optional[PlanVersion]:
        """Get a specific version of a plan"""
        plan = self._load_plan(plan_id)
        if plan and version_id in plan.versions:
            return plan.versions[version_id]
        return None

    def list_versions(self, plan_id: str) -> List[PlanVersion]:
        """List all versions of a plan"""
        plan = self._load_plan(plan_id)
        if not plan:
            return []

        return sorted(plan.versions.values(), key=lambda v: v.timestamp, reverse=True)

    def revert_to_version(self, plan_id: str, version_id: str, author: str) -> Optional[CollaborativePlan]:
        """Revert plan to a specific version"""
        plan = self._load_plan(plan_id)
        if not plan or version_id not in plan.versions:
            return None

        target_version = plan.versions[version_id]

        # Create new version with reverted content
        self._dict_to_plan(target_version.content, plan)
        plan.updated_at = datetime.utcnow()

        # Create version record for the revert
        revert_version = self.create_version(plan, author, f"Reverted to version {version_id}")

        return plan

    def compare_versions(self, plan_id: str, version1_id: str, version2_id: str) -> Dict[str, Any]:
        """Compare two versions of a plan"""
        plan = self._load_plan(plan_id)
        if not plan:
            return {}

        version1 = plan.versions.get(version1_id)
        version2 = plan.versions.get(version2_id)

        if not version1 or not version2:
            return {}

        return {
            'version1': version1.version_id,
            'version2': version2.version_id,
            'diff': self._calculate_diff(version1.content, version2.content),
            'summary': {
                'author1': version1.author,
                'author2': version2.author,
                'time1': version1.timestamp.isoformat(),
                'time2': version2.timestamp.isoformat()
            }
        }

    def _calculate_diff(self, old_content: Dict[str, Any], new_content: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate diff between two plan contents"""
        diff = {}

        # Compare tasks
        old_tasks = old_content.get('tasks', {})
        new_tasks = new_content.get('tasks', {})

        added_tasks = set(new_tasks.keys()) - set(old_tasks.keys())
        removed_tasks = set(old_tasks.keys()) - set(new_tasks.keys())
        modified_tasks = set()

        for task_id in set(old_tasks.keys()) & set(new_tasks.keys()):
            if old_tasks[task_id] != new_tasks[task_id]:
                modified_tasks.add(task_id)

        diff['tasks'] = {
            'added': list(added_tasks),
            'removed': list(removed_tasks),
            'modified': list(modified_tasks)
        }

        # Compare other fields
        for field in ['title', 'description', 'goal', 'status']:
            if old_content.get(field) != new_content.get(field):
                diff[field] = {
                    'old': old_content.get(field),
                    'new': new_content.get(field)
                }

        return diff

    def _plan_to_dict(self, plan: CollaborativePlan) -> Dict[str, Any]:
        """Convert plan object to dictionary"""
        return {
            'plan_id': plan.plan_id,
            'title': plan.title,
            'description': plan.description,
            'goal': plan.goal,
            'status': plan.status.value,
            'created_by': plan.created_by,
            'created_at': plan.created_at.isoformat(),
            'updated_at': plan.updated_at.isoformat(),
            'stakeholders': list(plan.stakeholders),
            'current_version': plan.current_version,
            'tasks': plan.tasks.copy(),
            'comments': plan.comments.copy(),
            'votes': plan.votes.copy()
        }

    def _dict_to_plan(self, data: Dict[str, Any], plan: CollaborativePlan):
        """Update plan object from dictionary"""
        plan.title = data['title']
        plan.description = data['description']
        plan.goal = data['goal']
        plan.status = PlanStatus(data['status'])
        plan.stakeholders = set(data['stakeholders'])
        plan.tasks = data['tasks'].copy()
        plan.comments = data['comments'].copy()
        plan.votes = data['votes'].copy()

    def _save_plan(self, plan: CollaborativePlan):
        """Save plan to disk"""
        plan_file = self.storage_path / f"{plan.plan_id}.json"
        data = self._plan_to_dict(plan)
        with open(plan_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def _load_plan(self, plan_id: str) -> Optional[CollaborativePlan]:
        """Load plan from disk"""
        plan_file = self.storage_path / f"{plan_id}.json"
        if not plan_file.exists():
            return None

        try:
            with open(plan_file, 'r') as f:
                data = json.load(f)

            plan = CollaborativePlan(
                plan_id=data['plan_id'],
                title=data['title'],
                description=data['description'],
                goal=data['goal'],
                status=PlanStatus(data['status']),
                created_by=data['created_by'],
                created_at=datetime.fromisoformat(data['created_at']),
                updated_at=datetime.fromisoformat(data['updated_at']),
                stakeholders=set(data['stakeholders']),
                current_version=data['current_version']
            )

            plan.tasks = data['tasks']
            plan.comments = data['comments']
            plan.votes = data['votes']

            # Load versions
            versions_file = self.storage_path / f"{plan_id}_versions.json"
            if versions_file.exists():
                with open(versions_file, 'r') as f:
                    versions_data = json.load(f)
                    for v_data in versions_data.values():
                        version = PlanVersion(
                            version_id=v_data['version_id'],
                            plan_id=v_data['plan_id'],
                            content=v_data['content'],
                            author=v_data['author'],
                            timestamp=datetime.fromisoformat(v_data['timestamp']),
                            change_summary=v_data['change_summary'],
                            parent_version=v_data.get('parent_version'),
                            diff=v_data.get('diff')
                        )
                        plan.versions[version.version_id] = version

            return plan

        except Exception as e:
            print(f"Error loading plan {plan_id}: {e}")
            return None


class FeedbackCollection:
    """System for collecting and analyzing feedback on plans"""

    def __init__(self):
        self.feedback_store: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    async def collect_feedback(self, plan_id: str, user_id: str, feedback_type: str, content: Dict[str, Any]):
        """Collect feedback on a plan"""
        feedback_entry = {
            'plan_id': plan_id,
            'user_id': user_id,
            'type': feedback_type,
            'content': content,
            'timestamp': datetime.utcnow(),
            'processed': False
        }

        self.feedback_store[plan_id].append(feedback_entry)

    def get_feedback_summary(self, plan_id: str) -> Dict[str, Any]:
        """Get summary of feedback for a plan"""
        feedback_list = self.feedback_store.get(plan_id, [])

        if not feedback_list:
            return {'total_feedback': 0, 'types': {}, 'average_rating': 0}

        type_counts = {}
        ratings = []

        for feedback in feedback_list:
            fb_type = feedback['type']
            type_counts[fb_type] = type_counts.get(fb_type, 0) + 1

            # Extract rating if present
            if 'rating' in feedback['content']:
                ratings.append(feedback['content']['rating'])

        return {
            'total_feedback': len(feedback_list),
            'types': type_counts,
            'average_rating': sum(ratings) / len(ratings) if ratings else 0,
            'recent_feedback': feedback_list[-5:]  # Last 5 feedback items
        }

    def analyze_feedback_trends(self, plan_id: str) -> Dict[str, Any]:
        """Analyze feedback trends over time"""
        feedback_list = sorted(self.feedback_store.get(plan_id, []),
                              key=lambda x: x['timestamp'])

        if not feedback_list:
            return {}

        # Group by day
        daily_feedback = defaultdict(list)
        for feedback in feedback_list:
            day = feedback['timestamp'].date()
            daily_feedback[day].append(feedback)

        trends = {}
        for day, feedbacks in daily_feedback.items():
            trends[str(day)] = {
                'count': len(feedbacks),
                'types': {fb['type']: sum(1 for f in feedbacks if f['type'] == fb['type'])
                         for fb in feedbacks}
            }

        return trends


class CollaborativePlanner:
    """Main collaborative planning system"""

    def __init__(self):
        self.plans: Dict[str, CollaborativePlan] = {}
        self.real_time_collaboration = RealTimeCollaboration()
        self.version_control = PlanningVersionControl()
        self.feedback_system = FeedbackCollection()

    async def create_shared_plan(self, title: str, description: str, goal: str, creator: str) -> CollaborativePlan:
        """Create a new collaborative planning document"""
        plan_id = str(uuid.uuid4())

        plan = CollaborativePlan(
            plan_id=plan_id,
            title=title,
            description=description,
            goal=goal,
            status=PlanStatus.DRAFT,
            created_by=creator,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            stakeholders={creator},
            current_version=""
        )

        # Create initial version
        initial_version = self.version_control.create_version(plan, creator, "Initial plan creation")

        self.plans[plan_id] = plan

        return plan

    async def update_plan(self, plan_id: str, updates: Dict[str, Any], user_id: str) -> bool:
        """Update a collaborative plan"""
        if plan_id not in self.plans:
            return False

        plan = self.plans[plan_id]

        # Apply updates
        for key, value in updates.items():
            if hasattr(plan, key):
                setattr(plan, key, value)

        plan.updated_at = datetime.utcnow()

        # Create new version
        change_summary = f"Updated by {user_id}: {', '.join(updates.keys())}"
        self.version_control.create_version(plan, user_id, change_summary)

        # Notify collaborators
        await self.real_time_collaboration.broadcast_to_plan(plan_id, {
            'event': CollaborationEvent.PLAN_UPDATED.value,
            'user_id': user_id,
            'updates': updates,
            'timestamp': datetime.utcnow().isoformat()
        })

        return True

    async def add_task(self, plan_id: str, task_data: Dict[str, Any], user_id: str) -> bool:
        """Add a task to a plan"""
        if plan_id not in self.plans:
            return False

        plan = self.plans[plan_id]
        task_id = str(uuid.uuid4())

        task_data['created_by'] = user_id
        task_data['created_at'] = datetime.utcnow().isoformat()
        task_data['status'] = 'pending'

        plan.tasks[task_id] = task_data
        plan.updated_at = datetime.utcnow()

        # Create version
        self.version_control.create_version(plan, user_id, f"Added task: {task_data.get('title', 'Untitled')}")

        # Notify collaborators
        await self.real_time_collaboration.broadcast_to_plan(plan_id, {
            'event': CollaborationEvent.TASK_ADDED.value,
            'task_id': task_id,
            'task_data': task_data,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })

        return True

    async def add_comment(self, plan_id: str, content: str, user_id: str, task_id: Optional[str] = None) -> bool:
        """Add a comment to a plan or task"""
        if plan_id not in self.plans:
            return False

        plan = self.plans[plan_id]

        comment = {
            'comment_id': str(uuid.uuid4()),
            'plan_id': plan_id,
            'task_id': task_id,
            'author': user_id,
            'content': content,
            'timestamp': datetime.utcnow().isoformat(),
            'reactions': {}
        }

        plan.comments.append(comment)
        plan.updated_at = datetime.utcnow()

        # Create version
        target = f"task {task_id}" if task_id else "plan"
        self.version_control.create_version(plan, user_id, f"Added comment to {target}")

        # Notify collaborators
        await self.real_time_collaboration.broadcast_to_plan(plan_id, {
            'event': CollaborationEvent.COMMENT_ADDED.value,
            'comment': comment,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })

        return True

    async def cast_vote(self, plan_id: str, vote_type: str, user_id: str, reason: Optional[str] = None, task_id: Optional[str] = None) -> bool:
        """Cast a vote on a plan or task"""
        if plan_id not in self.plans:
            return False

        plan = self.plans[plan_id]

        vote = {
            'vote_id': str(uuid.uuid4()),
            'plan_id': plan_id,
            'task_id': task_id,
            'voter': user_id,
            'vote_type': vote_type,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat()
        }

        target_key = task_id or 'plan'
        if target_key not in plan.votes:
            plan.votes[target_key] = []

        plan.votes[target_key].append(vote)
        plan.updated_at = datetime.utcnow()

        # Create version
        target = f"task {task_id}" if task_id else "plan"
        self.version_control.create_version(plan, user_id, f"Cast {vote_type} vote on {target}")

        # Notify collaborators
        await self.real_time_collaboration.broadcast_to_plan(plan_id, {
            'event': CollaborationEvent.VOTE_CAST.value,
            'vote': vote,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })

        return True

    def get_plan(self, plan_id: str) -> Optional[CollaborativePlan]:
        """Get a collaborative plan"""
        return self.plans.get(plan_id)

    def list_plans(self, user_id: Optional[str] = None) -> List[CollaborativePlan]:
        """List all plans or plans for a specific user"""
        if user_id:
            return [plan for plan in self.plans.values() if user_id in plan.stakeholders]
        return list(self.plans.values())

    async def collect_feedback(self, plan_id: str, user_id: str, feedback_type: str, content: Dict[str, Any]):
        """Collect feedback on a plan"""
        await self.feedback_system.collect_feedback(plan_id, user_id, feedback_type, content)

    def get_feedback_summary(self, plan_id: str) -> Dict[str, Any]:
        """Get feedback summary for a plan"""
        return self.feedback_system.get_feedback_summary(plan_id)

    def get_active_users(self, plan_id: str) -> List[str]:
        """Get list of active users in a plan session"""
        return self.real_time_collaboration.get_active_users(plan_id)


# Global collaborative planner instance
collaborative_planner = CollaborativePlanner()


def get_collaborative_planner() -> CollaborativePlanner:
    """Get global collaborative planner instance"""
    return collaborative_planner