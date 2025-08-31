"""
Continuous Improvement and Deployment Automation for Sanaa
Provides automated deployment, rollback, and continuous improvement capabilities
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import time
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import docker
import git
import yaml


class DeploymentStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentStrategy(Enum):
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    IMMEDIATE = "immediate"


@dataclass
class Deployment:
    """Represents a deployment"""
    id: str
    version: str
    environment: str
    strategy: DeploymentStrategy
    status: DeploymentStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    rollback_version: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)


@dataclass
class RollbackPlan:
    """Represents a rollback plan"""
    deployment_id: str
    target_version: str
    strategy: str
    steps: List[Dict[str, Any]]
    estimated_duration: int  # seconds
    risk_level: str


@dataclass
class ImprovementSuggestion:
    """Represents a system improvement suggestion"""
    id: str
    category: str
    title: str
    description: str
    impact: str
    effort: str
    priority: int
    suggested_by: str
    created_at: datetime
    implemented: bool = False
    implemented_at: Optional[datetime] = None


class DeploymentAutomator:
    """Automated deployment system"""

    def __init__(self, config_path: Path = None):
        self.config_path = config_path or Path.home() / ".sanaa" / "deployment_config.yaml"
        self.deployments: Dict[str, Deployment] = {}
        self.environments: Dict[str, Dict[str, Any]] = {}
        self.docker_client = docker.from_env()

        self._load_config()

    def _load_config(self):
        """Load deployment configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.environments = config.get('environments', {})

    def create_deployment(self, version: str, environment: str,
                         strategy: DeploymentStrategy = DeploymentStrategy.ROLLING) -> Deployment:
        """Create a new deployment"""
        deployment_id = f"deploy_{int(time.time())}_{version}"

        deployment = Deployment(
            id=deployment_id,
            version=version,
            environment=environment,
            strategy=strategy,
            status=DeploymentStatus.PENDING,
            created_at=datetime.utcnow()
        )

        self.deployments[deployment_id] = deployment
        return deployment

    async def execute_deployment(self, deployment_id: str) -> bool:
        """Execute a deployment"""
        if deployment_id not in self.deployments:
            raise ValueError(f"Deployment {deployment_id} not found")

        deployment = self.deployments[deployment_id]
        deployment.status = DeploymentStatus.IN_PROGRESS
        deployment.started_at = datetime.utcnow()

        try:
            # Pre-deployment checks
            await self._run_pre_deployment_checks(deployment)

            # Execute deployment based on strategy
            if deployment.strategy == DeploymentStrategy.BLUE_GREEN:
                success = await self._execute_blue_green_deployment(deployment)
            elif deployment.strategy == DeploymentStrategy.CANARY:
                success = await self._execute_canary_deployment(deployment)
            elif deployment.strategy == DeploymentStrategy.ROLLING:
                success = await self._execute_rolling_deployment(deployment)
            else:
                success = await self._execute_immediate_deployment(deployment)

            if success:
                deployment.status = DeploymentStatus.SUCCESS
                deployment.completed_at = datetime.utcnow()

                # Post-deployment validation
                await self._run_post_deployment_validation(deployment)
            else:
                deployment.status = DeploymentStatus.FAILED
                # Automatic rollback
                await self.rollback_deployment(deployment_id)

            return success

        except Exception as e:
            deployment.status = DeploymentStatus.FAILED
            deployment.logs.append(f"Deployment failed: {str(e)}")
            await self.rollback_deployment(deployment_id)
            return False

    async def rollback_deployment(self, deployment_id: str) -> bool:
        """Rollback a deployment"""
        if deployment_id not in self.deployments:
            raise ValueError(f"Deployment {deployment_id} not found")

        deployment = self.deployments[deployment_id]

        # Create rollback plan
        rollback_plan = self._create_rollback_plan(deployment)

        try:
            # Execute rollback
            success = await self._execute_rollback(rollback_plan)

            if success:
                deployment.status = DeploymentStatus.ROLLED_BACK
                deployment.rollback_version = rollback_plan.target_version
                deployment.completed_at = datetime.utcnow()

            return success

        except Exception as e:
            deployment.logs.append(f"Rollback failed: {str(e)}")
            return False

    async def _run_pre_deployment_checks(self, deployment: Deployment) -> bool:
        """Run pre-deployment health checks"""
        deployment.logs.append("Running pre-deployment checks...")

        # Health checks
        checks = [
            self._check_system_resources,
            self._check_database_connectivity,
            self._check_service_dependencies,
            self._validate_deployment_package
        ]

        for check in checks:
            try:
                result = await check(deployment)
                if not result:
                    deployment.logs.append(f"Pre-deployment check failed: {check.__name__}")
                    return False
            except Exception as e:
                deployment.logs.append(f"Check {check.__name__} error: {str(e)}")
                return False

        deployment.logs.append("All pre-deployment checks passed")
        return True

    async def _run_post_deployment_validation(self, deployment: Deployment):
        """Run post-deployment validation"""
        deployment.logs.append("Running post-deployment validation...")

        # Wait for services to be ready
        await asyncio.sleep(30)

        # Validation checks
        validations = [
            self._validate_service_health,
            self._validate_api_endpoints,
            self._validate_database_migrations,
            self._run_smoke_tests
        ]

        for validation in validations:
            try:
                result = await validation(deployment)
                deployment.logs.append(f"Validation {validation.__name__}: {'PASS' if result else 'FAIL'}")
            except Exception as e:
                deployment.logs.append(f"Validation {validation.__name__} error: {str(e)}")

    async def _execute_blue_green_deployment(self, deployment: Deployment) -> bool:
        """Execute blue-green deployment"""
        deployment.logs.append("Starting blue-green deployment...")

        # Create green environment
        green_env = f"{deployment.environment}_green"

        # Deploy to green environment
        success = await self._deploy_to_environment(deployment, green_env)
        if not success:
            return False

        # Run tests on green environment
        test_success = await self._run_deployment_tests(deployment, green_env)
        if not test_success:
            deployment.logs.append("Tests failed on green environment")
            return False

        # Switch traffic to green environment
        await self._switch_traffic(deployment.environment, green_env)

        # Keep blue environment as backup
        deployment.logs.append("Blue-green deployment completed successfully")
        return True

    async def _execute_canary_deployment(self, deployment: Deployment) -> bool:
        """Execute canary deployment"""
        deployment.logs.append("Starting canary deployment...")

        # Deploy to small subset of instances
        canary_instances = await self._get_canary_instances(deployment.environment)

        for instance in canary_instances:
            success = await self._deploy_to_instance(deployment, instance)
            if not success:
                return False

        # Monitor canary instances
        monitoring_success = await self._monitor_canary_performance(deployment, canary_instances)
        if not monitoring_success:
            deployment.logs.append("Canary monitoring failed")
            return False

        # Gradually roll out to all instances
        await self._gradual_rollout(deployment)

        deployment.logs.append("Canary deployment completed successfully")
        return True

    async def _execute_rolling_deployment(self, deployment: Deployment) -> bool:
        """Execute rolling deployment"""
        deployment.logs.append("Starting rolling deployment...")

        instances = await self._get_environment_instances(deployment.environment)

        # Deploy to instances in batches
        batch_size = max(1, len(instances) // 4)  # 25% at a time

        for i in range(0, len(instances), batch_size):
            batch = instances[i:i + batch_size]

            # Deploy batch
            batch_tasks = [self._deploy_to_instance(deployment, instance) for instance in batch]
            results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Check for failures
            for j, result in enumerate(results):
                if isinstance(result, Exception) or not result:
                    deployment.logs.append(f"Failed to deploy to instance {batch[j]}")
                    return False

            # Wait for batch to stabilize
            await asyncio.sleep(60)

            # Health check
            health_ok = await self._check_batch_health(batch)
            if not health_ok:
                deployment.logs.append(f"Health check failed for batch {i//batch_size + 1}")
                return False

        deployment.logs.append("Rolling deployment completed successfully")
        return True

    async def _execute_immediate_deployment(self, deployment: Deployment) -> bool:
        """Execute immediate deployment (all at once)"""
        deployment.logs.append("Starting immediate deployment...")

        instances = await self._get_environment_instances(deployment.environment)

        # Deploy to all instances simultaneously
        tasks = [self._deploy_to_instance(deployment, instance) for instance in instances]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check results
        for i, result in enumerate(results):
            if isinstance(result, Exception) or not result:
                deployment.logs.append(f"Failed to deploy to instance {instances[i]}")
                return False

        deployment.logs.append("Immediate deployment completed successfully")
        return True

    def _create_rollback_plan(self, deployment: Deployment) -> RollbackPlan:
        """Create a rollback plan"""
        # Determine target version (previous version)
        target_version = self._get_previous_version(deployment.environment)

        steps = [
            {
                'action': 'stop_new_version',
                'description': 'Stop the newly deployed version'
            },
            {
                'action': 'restore_previous',
                'description': f'Restore version {target_version}'
            },
            {
                'action': 'switch_traffic',
                'description': 'Switch traffic back to previous version'
            },
            {
                'action': 'validate_rollback',
                'description': 'Validate rollback success'
            }
        ]

        return RollbackPlan(
            deployment_id=deployment.id,
            target_version=target_version,
            strategy='immediate',
            steps=steps,
            estimated_duration=300,  # 5 minutes
            risk_level='medium'
        )

    async def _execute_rollback(self, rollback_plan: RollbackPlan) -> bool:
        """Execute rollback plan"""
        for step in rollback_plan.steps:
            try:
                success = await self._execute_rollback_step(step)
                if not success:
                    return False
            except Exception as e:
                print(f"Rollback step failed: {step['action']} - {str(e)}")
                return False

        return True

    async def _execute_rollback_step(self, step: Dict[str, Any]) -> bool:
        """Execute a single rollback step"""
        action = step['action']

        if action == 'stop_new_version':
            # Implementation would stop new containers/services
            await asyncio.sleep(10)  # Simulate
        elif action == 'restore_previous':
            # Implementation would start previous version
            await asyncio.sleep(30)  # Simulate
        elif action == 'switch_traffic':
            # Implementation would switch load balancer
            await asyncio.sleep(5)  # Simulate
        elif action == 'validate_rollback':
            # Implementation would run validation checks
            await asyncio.sleep(15)  # Simulate

        return True

    # Placeholder methods for deployment operations
    async def _deploy_to_environment(self, deployment: Deployment, environment: str) -> bool:
        """Deploy to environment (placeholder)"""
        await asyncio.sleep(30)  # Simulate deployment time
        return True

    async def _deploy_to_instance(self, deployment: Deployment, instance: str) -> bool:
        """Deploy to instance (placeholder)"""
        await asyncio.sleep(15)  # Simulate deployment time
        return True

    async def _get_environment_instances(self, environment: str) -> List[str]:
        """Get instances for environment (placeholder)"""
        return [f"{environment}-instance-{i}" for i in range(1, 5)]

    async def _get_canary_instances(self, environment: str) -> List[str]:
        """Get canary instances (placeholder)"""
        instances = await self._get_environment_instances(environment)
        return instances[:2]  # First 2 instances

    async def _switch_traffic(self, from_env: str, to_env: str):
        """Switch traffic between environments (placeholder)"""
        await asyncio.sleep(10)  # Simulate traffic switch

    async def _gradual_rollout(self, deployment: Deployment):
        """Gradual rollout (placeholder)"""
        await asyncio.sleep(60)  # Simulate gradual rollout

    async def _monitor_canary_performance(self, deployment: Deployment, instances: List[str]) -> bool:
        """Monitor canary performance (placeholder)"""
        await asyncio.sleep(120)  # Simulate monitoring
        return True

    async def _check_batch_health(self, instances: List[str]) -> bool:
        """Check batch health (placeholder)"""
        await asyncio.sleep(30)  # Simulate health check
        return True

    def _get_previous_version(self, environment: str) -> str:
        """Get previous version (placeholder)"""
        return "v1.0.0"

    # Health check methods
    async def _check_system_resources(self, deployment: Deployment) -> bool:
        """Check system resources (placeholder)"""
        return True

    async def _check_database_connectivity(self, deployment: Deployment) -> bool:
        """Check database connectivity (placeholder)"""
        return True

    async def _check_service_dependencies(self, deployment: Deployment) -> bool:
        """Check service dependencies (placeholder)"""
        return True

    async def _validate_deployment_package(self, deployment: Deployment) -> bool:
        """Validate deployment package (placeholder)"""
        return True

    async def _validate_service_health(self, deployment: Deployment) -> bool:
        """Validate service health (placeholder)"""
        return True

    async def _validate_api_endpoints(self, deployment: Deployment) -> bool:
        """Validate API endpoints (placeholder)"""
        return True

    async def _validate_database_migrations(self, deployment: Deployment) -> bool:
        """Validate database migrations (placeholder)"""
        return True

    async def _run_smoke_tests(self, deployment: Deployment) -> bool:
        """Run smoke tests (placeholder)"""
        return True

    async def _run_deployment_tests(self, deployment: Deployment, environment: str) -> bool:
        """Run deployment tests (placeholder)"""
        return True


class ContinuousImprovementEngine:
    """Continuous improvement system"""

    def __init__(self):
        self.suggestions: Dict[str, ImprovementSuggestion] = {}
        self.improvement_categories = [
            'performance', 'security', 'usability', 'reliability',
            'maintainability', 'scalability', 'monitoring'
        ]

    def analyze_system_metrics(self, metrics: Dict[str, Any]) -> List[ImprovementSuggestion]:
        """Analyze system metrics and generate improvement suggestions"""
        suggestions = []

        # Performance analysis
        if metrics.get('cpu_usage', 0) > 80:
            suggestions.append(self._create_suggestion(
                'performance',
                'High CPU Usage Detected',
                'System CPU usage is consistently above 80%. Consider optimizing resource-intensive operations.',
                'high',
                'medium'
            ))

        if metrics.get('memory_usage', 0) > 85:
            suggestions.append(self._create_suggestion(
                'performance',
                'High Memory Usage Detected',
                'System memory usage is above 85%. Consider implementing memory optimization techniques.',
                'high',
                'medium'
            ))

        # Error rate analysis
        error_rate = metrics.get('error_rate', 0)
        if error_rate > 5:
            suggestions.append(self._create_suggestion(
                'reliability',
                'High Error Rate Detected',
                f'Error rate is {error_rate}%. Review error handling and implement better exception management.',
                'critical',
                'high'
            ))

        # Response time analysis
        avg_response_time = metrics.get('avg_response_time', 0)
        if avg_response_time > 2.0:
            suggestions.append(self._create_suggestion(
                'performance',
                'Slow Response Times',
                f'Average response time is {avg_response_time}s. Consider implementing caching or optimization.',
                'medium',
                'medium'
            ))

        return suggestions

    def analyze_code_quality(self, quality_report: Dict[str, Any]) -> List[ImprovementSuggestion]:
        """Analyze code quality and generate suggestions"""
        suggestions = []

        quality_score = quality_report.get('score', 100)
        if quality_score < 70:
            suggestions.append(self._create_suggestion(
                'maintainability',
                'Low Code Quality Score',
                f'Code quality score is {quality_score}%. Focus on code reviews and refactoring.',
                'medium',
                'high'
            ))

        issues = quality_report.get('issues', [])
        if len(issues) > 10:
            suggestions.append(self._create_suggestion(
                'maintainability',
                'High Number of Code Issues',
                f'Found {len(issues)} code quality issues. Prioritize fixing critical issues.',
                'medium',
                'medium'
            ))

        return suggestions

    def analyze_security_issues(self, security_issues: List[Dict[str, Any]]) -> List[ImprovementSuggestion]:
        """Analyze security issues and generate suggestions"""
        suggestions = []

        high_severity = [issue for issue in security_issues if issue.get('severity') == 'high']
        if high_severity:
            suggestions.append(self._create_suggestion(
                'security',
                'High-Severity Security Issues Found',
                f'Detected {len(high_severity)} high-severity security vulnerabilities. Immediate attention required.',
                'critical',
                'high'
            ))

        critical_issues = [issue for issue in security_issues if issue.get('severity') == 'critical']
        if critical_issues:
            suggestions.append(self._create_suggestion(
                'security',
                'Critical Security Vulnerabilities',
                f'Found {len(critical_issues)} critical security issues. Immediate remediation required.',
                'critical',
                'urgent'
            ))

        return suggestions

    def _create_suggestion(self, category: str, title: str, description: str,
                          impact: str, effort: str) -> ImprovementSuggestion:
        """Create an improvement suggestion"""
        suggestion_id = f"sugg_{int(time.time())}_{hash(title) % 10000}"

        # Calculate priority based on impact and effort
        priority_map = {
            'critical': 5,
            'high': 4,
            'medium': 3,
            'low': 2,
            'info': 1
        }

        effort_penalty = {'urgent': 2, 'high': 1, 'medium': 0, 'low': -1}
        priority = priority_map.get(impact, 3) + effort_penalty.get(effort, 0)
        priority = max(1, min(5, priority))

        suggestion = ImprovementSuggestion(
            id=suggestion_id,
            category=category,
            title=title,
            description=description,
            impact=impact,
            effort=effort,
            priority=priority,
            suggested_by='system',
            created_at=datetime.utcnow()
        )

        self.suggestions[suggestion_id] = suggestion
        return suggestion

    def get_suggestions(self, category: str = None, priority_min: int = None,
                       implemented: bool = None) -> List[ImprovementSuggestion]:
        """Get improvement suggestions with filtering"""
        suggestions = list(self.suggestions.values())

        if category:
            suggestions = [s for s in suggestions if s.category == category]

        if priority_min is not None:
            suggestions = [s for s in suggestions if s.priority >= priority_min]

        if implemented is not None:
            suggestions = [s for s in suggestions if s.implemented == implemented]

        return sorted(suggestions, key=lambda s: s.priority, reverse=True)

    def mark_implemented(self, suggestion_id: str):
        """Mark a suggestion as implemented"""
        if suggestion_id in self.suggestions:
            self.suggestions[suggestion_id].implemented = True
            self.suggestions[suggestion_id].implemented_at = datetime.utcnow()

    def generate_improvement_report(self) -> Dict[str, Any]:
        """Generate comprehensive improvement report"""
        all_suggestions = list(self.suggestions.values())

        implemented = [s for s in all_suggestions if s.implemented]
        pending = [s for s in all_suggestions if not s.implemented]

        category_stats = {}
        for suggestion in all_suggestions:
            category_stats[suggestion.category] = category_stats.get(suggestion.category, 0) + 1

        priority_stats = {}
        for suggestion in pending:
            priority_stats[suggestion.priority] = priority_stats.get(suggestion.priority, 0) + 1

        return {
            'total_suggestions': len(all_suggestions),
            'implemented': len(implemented),
            'pending': len(pending),
            'category_breakdown': category_stats,
            'priority_breakdown': priority_stats,
            'top_pending_suggestions': [
                {
                    'id': s.id,
                    'title': s.title,
                    'category': s.category,
                    'priority': s.priority,
                    'created_at': s.created_at.isoformat()
                }
                for s in pending[:10]
            ],
            'recent_improvements': [
                {
                    'id': s.id,
                    'title': s.title,
                    'implemented_at': s.implemented_at.isoformat()
                }
                for s in implemented[-5:]
            ]
        }


# Global instances
deployment_automator = DeploymentAutomator()
continuous_improvement_engine = ContinuousImprovementEngine()


def get_deployment_automator() -> DeploymentAutomator:
    """Get global deployment automator instance"""
    return deployment_automator


def get_continuous_improvement_engine() -> ContinuousImprovementEngine:
    """Get global continuous improvement engine instance"""
    return continuous_improvement_engine