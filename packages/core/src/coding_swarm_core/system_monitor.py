"""
System Monitor - Comprehensive monitoring and auto-healing for Sanaa infrastructure
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import time
import subprocess
import threading
import json
from pathlib import Path
from datetime import datetime, timedelta

import httpx


@dataclass
class ServiceStatus:
    """Status of a service"""
    name: str
    type: str  # 'docker', 'http', 'system'
    endpoint: Optional[str] = None
    container_name: Optional[str] = None
    status: str = "unknown"  # 'healthy', 'unhealthy', 'down', 'unknown'
    last_check: float = field(default_factory=time.time)
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    response_time: Optional[float] = None
    auto_heal_attempts: int = 0
    last_heal_attempt: Optional[float] = None


@dataclass
class SystemHealth:
    """Overall system health status"""
    overall_status: str = "unknown"  # 'healthy', 'degraded', 'critical', 'down'
    services: Dict[str, ServiceStatus] = field(default_factory=dict)
    last_update: float = field(default_factory=time.time)
    uptime: float = 0.0
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class SystemMonitor:
    """Comprehensive system monitoring and auto-healing"""

    def __init__(self):
        self.services = self._initialize_services()
        self.health_history: List[SystemHealth] = []
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.check_interval = 30  # seconds
        self.max_heal_attempts = 3
        self.heal_cooldown = 300  # 5 minutes between heal attempts

    def _initialize_services(self) -> Dict[str, ServiceStatus]:
        """Initialize all services to monitor"""
        return {
            # LLM Services
            'qwen-api': ServiceStatus(
                name='Qwen API Model',
                type='docker',
                container_name='coding-swarm-qwen-api-1',
                endpoint='http://127.0.0.1:8080/v1/models'
            ),
            'qwen-web': ServiceStatus(
                name='Qwen Web Model',
                type='docker',
                container_name='coding-swarm-qwen-web-1',
                endpoint='http://127.0.0.1:8081/v1/models'
            ),
            'qwen-mobile': ServiceStatus(
                name='Qwen Mobile Model',
                type='docker',
                container_name='coding-swarm-qwen-mobile-1',
                endpoint='http://127.0.0.1:8082/v1/models'
            ),
            'qwen-test': ServiceStatus(
                name='Qwen Test Model',
                type='docker',
                container_name='coding-swarm-qwen-test-1',
                endpoint='http://127.0.0.1:8083/v1/models'
            ),

            # Database Services
            'mysql': ServiceStatus(
                name='MySQL Database',
                type='docker',
                container_name='backend-mysql-1',
                endpoint='mysql://127.0.0.1:3306'
            ),
            'postgres': ServiceStatus(
                name='PostgreSQL Database',
                type='docker',
                container_name='coding-swarm-postgres-1',
                endpoint='postgresql://127.0.0.1:5432'
            ),
            'redis': ServiceStatus(
                name='Redis Cache',
                type='docker',
                container_name='coding-swarm-redis-1',
                endpoint='redis://127.0.0.1:6379'
            ),

            # Search and Communication
            'meilisearch': ServiceStatus(
                name='Meilisearch',
                type='docker',
                container_name='backend-meilisearch-1',
                endpoint='http://127.0.0.1:7700/health'
            ),
            'mailpit': ServiceStatus(
                name='Mailpit',
                type='docker',
                container_name='backend-mailpit-1',
                endpoint='http://127.0.0.1:8025'
            ),

            # Testing
            'selenium': ServiceStatus(
                name='Selenium',
                type='docker',
                container_name='backend-selenium-1',
                endpoint='http://127.0.0.1:4444/wd/hub/status'
            )
        }

    def start_monitoring(self):
        """Start the monitoring system"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()

        # Initial health check
        self.check_system_health()

    def stop_monitoring(self):
        """Stop the monitoring system"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                self.check_system_health()
                self._perform_auto_healing()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(self.check_interval)

    def check_system_health(self) -> SystemHealth:
        """Check overall system health"""
        health = SystemHealth()

        # Check each service
        for service_name, service in self.services.items():
            self._check_service_status(service)
            health.services[service_name] = service

        # Determine overall status
        statuses = [s.status for s in health.services.values()]

        if all(s == 'healthy' for s in statuses):
            health.overall_status = 'healthy'
        elif any(s == 'critical' for s in statuses):
            health.overall_status = 'critical'
        elif any(s == 'unhealthy' for s in statuses):
            health.overall_status = 'degraded'
        else:
            health.overall_status = 'degraded'

        # Generate issues and recommendations
        health.issues = self._analyze_issues(health.services)
        health.recommendations = self._generate_recommendations(health.services)

        # Update uptime
        if self.health_history:
            health.uptime = time.time() - self.health_history[0].last_update
        else:
            health.uptime = 0.0

        # Store in history
        self.health_history.append(health)

        # Keep only last 100 health checks
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-100:]

        return health

    def _check_service_status(self, service: ServiceStatus):
        """Check the status of a specific service"""
        service.last_check = time.time()

        try:
            if service.type == 'docker':
                self._check_docker_service(service)
            elif service.type == 'http':
                self._check_http_service(service)
            elif service.type == 'system':
                self._check_system_service(service)

        except Exception as e:
            service.status = 'unknown'
            service.last_error = str(e)
            service.consecutive_failures += 1

    def _check_docker_service(self, service: ServiceStatus):
        """Check Docker container status"""
        if not service.container_name:
            return

        try:
            # Check container status
            result = subprocess.run(
                ['docker', 'ps', '--filter', f'name={service.container_name}', '--format', '{{.Status}}'],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                status_text = result.stdout.strip().lower()

                if 'healthy' in status_text:
                    service.status = 'healthy'
                    service.consecutive_failures = 0
                    service.last_error = None
                elif 'unhealthy' in status_text:
                    service.status = 'unhealthy'
                    service.consecutive_failures += 1
                elif 'up' in status_text:
                    service.status = 'healthy'  # Assume healthy if up but no health check
                    service.consecutive_failures = 0
                    service.last_error = None
                else:
                    service.status = 'down'
                    service.consecutive_failures += 1
            else:
                service.status = 'down'
                service.consecutive_failures += 1
                service.last_error = "Container not found or not running"

            # Check HTTP endpoint if available
            if service.endpoint and service.endpoint.startswith('http'):
                self._check_http_endpoint(service)

        except subprocess.TimeoutExpired:
            service.status = 'unknown'
            service.last_error = "Timeout checking container status"
        except Exception as e:
            service.status = 'unknown'
            service.last_error = str(e)

    def _check_http_service(self, service: ServiceStatus):
        """Check HTTP service status"""
        if not service.endpoint:
            return

        try:
            start_time = time.time()
            with httpx.Client(timeout=10) as client:
                response = client.get(service.endpoint)
                response_time = time.time() - start_time

                service.response_time = response_time

                if response.status_code in [200, 201, 202]:
                    service.status = 'healthy'
                    service.consecutive_failures = 0
                    service.last_error = None
                else:
                    service.status = 'unhealthy'
                    service.consecutive_failures += 1
                    service.last_error = f"HTTP {response.status_code}"

        except httpx.TimeoutException:
            service.status = 'unhealthy'
            service.last_error = "Request timeout"
            service.consecutive_failures += 1
        except Exception as e:
            service.status = 'down'
            service.last_error = str(e)
            service.consecutive_failures += 1

    def _check_http_endpoint(self, service: ServiceStatus):
        """Check HTTP endpoint for a service"""
        if not service.endpoint or not service.endpoint.startswith('http'):
            return

        try:
            start_time = time.time()
            with httpx.Client(timeout=5) as client:
                response = client.get(service.endpoint)
                response_time = time.time() - start_time

                if service.response_time is None:
                    service.response_time = response_time
                else:
                    # Average response time
                    service.response_time = (service.response_time + response_time) / 2

                if response.status_code not in [200, 201, 202]:
                    if service.status == 'healthy':
                        service.status = 'degraded'
                        service.last_error = f"HTTP {response.status_code}"

        except Exception:
            # Don't override container status, just note HTTP issue
            if service.status == 'healthy':
                service.status = 'degraded'
                service.last_error = "HTTP endpoint unreachable"

    def _check_system_service(self, service: ServiceStatus):
        """Check system service status"""
        # Placeholder for system service checks
        service.status = 'healthy'

    def _perform_auto_healing(self):
        """Perform automatic healing of unhealthy services"""
        for service_name, service in self.services.items():
            if service.status in ['unhealthy', 'down']:
                self._attempt_service_healing(service)

    def _attempt_service_healing(self, service: ServiceStatus):
        """Attempt to heal a specific service"""
        # Check cooldown
        if (service.last_heal_attempt and
            time.time() - service.last_heal_attempt < self.heal_cooldown):
            return

        # Check max attempts
        if service.auto_heal_attempts >= self.max_heal_attempts:
            return

        service.last_heal_attempt = time.time()
        service.auto_heal_attempts += 1

        try:
            if service.type == 'docker' and service.container_name:
                self._heal_docker_service(service)
            elif service.type == 'http':
                self._heal_http_service(service)

        except Exception as e:
            service.last_error = f"Healing failed: {e}"

    def _heal_docker_service(self, service: ServiceStatus):
        """Attempt to heal a Docker service"""
        container_name = service.container_name

        # Try restarting the container
        try:
            result = subprocess.run(
                ['docker', 'restart', container_name],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                service.last_error = "Container restarted successfully"
                # Wait a moment for container to start
                time.sleep(5)
                # Re-check status
                self._check_service_status(service)
            else:
                service.last_error = f"Restart failed: {result.stderr}"

        except subprocess.TimeoutExpired:
            service.last_error = "Restart timeout"
        except Exception as e:
            service.last_error = f"Restart error: {e}"

    def _heal_http_service(self, service: ServiceStatus):
        """Attempt to heal an HTTP service"""
        # For HTTP services, we might need to restart related containers
        # This is a placeholder for more sophisticated healing logic
        service.last_error = "HTTP service healing not implemented"

    def _analyze_issues(self, services: Dict[str, ServiceStatus]) -> List[str]:
        """Analyze system issues"""
        issues = []

        for service_name, service in services.items():
            if service.status == 'down':
                issues.append(f"{service.name} is completely down")
            elif service.status == 'unhealthy':
                issues.append(f"{service.name} is unhealthy ({service.last_error or 'Unknown error'})")
            elif service.status == 'degraded':
                issues.append(f"{service.name} is degraded ({service.last_error or 'Performance issue'})")

            # Check response times
            if service.response_time and service.response_time > 5.0:
                issues.append(f"{service.name} has slow response time ({service.response_time:.2f}s)")

            # Check consecutive failures
            if service.consecutive_failures > 5:
                issues.append(f"{service.name} has {service.consecutive_failures} consecutive failures")

        return issues

    def _generate_recommendations(self, services: Dict[str, ServiceStatus]) -> List[str]:
        """Generate recommendations based on service status"""
        recommendations = []

        # Count unhealthy services
        unhealthy_count = sum(1 for s in services.values() if s.status in ['unhealthy', 'down'])

        if unhealthy_count > 0:
            recommendations.append(f"Address {unhealthy_count} unhealthy services")

        # Check for pattern issues
        llm_services = ['qwen-api', 'qwen-web', 'qwen-mobile', 'qwen-test']
        unhealthy_llm = sum(1 for s in llm_services if services.get(s, ServiceStatus('')).status != 'healthy')

        if unhealthy_llm > 0:
            recommendations.append("Multiple LLM services are unhealthy - check model files and container logs")

        # Check database services
        db_services = ['mysql', 'postgres', 'redis']
        unhealthy_db = sum(1 for s in db_services if services.get(s, ServiceStatus('')).status != 'healthy')

        if unhealthy_db > 0:
            recommendations.append("Database services have issues - check connectivity and data integrity")

        # Performance recommendations
        slow_services = [s.name for s in services.values() if s.response_time and s.response_time > 2.0]
        if slow_services:
            recommendations.append(f"Optimize performance for: {', '.join(slow_services[:3])}")

        return recommendations

    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        if not self.health_history:
            return {"status": "no_data", "message": "No health data available"}

        latest_health = self.health_history[-1]

        # Calculate trends
        healthy_trend = []
        if len(self.health_history) > 1:
            for i in range(1, min(6, len(self.health_history))):  # Last 5 checks
                prev_health = self.health_history[-i-1]
                curr_health = self.health_history[-i]

                prev_healthy = sum(1 for s in prev_health.services.values() if s.status == 'healthy')
                curr_healthy = sum(1 for s in curr_health.services.values() if s.status == 'healthy')

                healthy_trend.append(curr_healthy - prev_healthy)

        return {
            "overall_status": latest_health.overall_status,
            "services_count": len(latest_health.services),
            "healthy_services": sum(1 for s in latest_health.services.values() if s.status == 'healthy'),
            "unhealthy_services": sum(1 for s in latest_health.services.values() if s.status in ['unhealthy', 'down']),
            "issues": latest_health.issues,
            "recommendations": latest_health.recommendations,
            "uptime": latest_health.uptime,
            "last_update": datetime.fromtimestamp(latest_health.last_update).isoformat(),
            "trend": "improving" if healthy_trend and sum(healthy_trend) > 0 else "stable" if not healthy_trend else "degrading",
            "services_detail": {
                name: {
                    "status": service.status,
                    "last_check": datetime.fromtimestamp(service.last_check).isoformat(),
                    "response_time": service.response_time,
                    "consecutive_failures": service.consecutive_failures,
                    "last_error": service.last_error
                }
                for name, service in latest_health.services.items()
            }
        }

    def export_health_data(self, filepath: str):
        """Export health data to file"""
        data = {
            "export_time": datetime.now().isoformat(),
            "monitoring_active": self.monitoring_active,
            "services": {
                name: {
                    "name": service.name,
                    "type": service.type,
                    "endpoint": service.endpoint,
                    "container_name": service.container_name,
                    "status": service.status,
                    "last_check": service.last_check,
                    "consecutive_failures": service.consecutive_failures,
                    "last_error": service.last_error,
                    "response_time": service.response_time,
                    "auto_heal_attempts": service.auto_heal_attempts,
                    "last_heal_attempt": service.last_heal_attempt
                }
                for name, service in self.services.items()
            },
            "health_history": [
                {
                    "overall_status": health.overall_status,
                    "last_update": health.last_update,
                    "uptime": health.uptime,
                    "issues": health.issues,
                    "recommendations": health.recommendations,
                    "services_status": {
                        name: service.status
                        for name, service in health.services.items()
                    }
                }
                for health in self.health_history[-10:]  # Last 10 health checks
            ]
        }

        Path(filepath).write_text(json.dumps(data, indent=2, default=str))


# Global system monitor instance
system_monitor = SystemMonitor()