"""
Comprehensive Performance Monitoring System for Sanaa
Provides real-time monitoring, alerting, and predictive analytics
"""
from __future__ import annotations

import asyncio
import time
import psutil
import threading
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import statistics
import json
from pathlib import Path


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Represents a performance metric"""
    name: str
    type: MetricType
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    description: str = ""


@dataclass
class Alert:
    """Represents a performance alert"""
    id: str
    name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    threshold: float
    current_value: float
    condition: str  # 'above', 'below', 'equals'
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class SystemHealth:
    """Overall system health status"""
    overall_status: str  # 'healthy', 'degraded', 'unhealthy'
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    active_connections: int
    response_time_avg: float
    error_rate: float
    uptime: float
    last_updated: datetime


class MetricsCollector:
    """Collects and aggregates performance metrics"""

    def __init__(self, retention_period: int = 3600):  # 1 hour default
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.aggregates: Dict[str, Dict[str, Any]] = {}
        self.retention_period = retention_period
        self.collection_interval = 10  # seconds
        self._running = False
        self._collection_thread: Optional[threading.Thread] = None

    def start_collection(self):
        """Start metrics collection"""
        self._running = True
        self._collection_thread = threading.Thread(target=self._collection_loop, daemon=True)
        self._collection_thread.start()

    def stop_collection(self):
        """Stop metrics collection"""
        self._running = False
        if self._collection_thread:
            self._collection_thread.join(timeout=5)

    def record_metric(self, name: str, value: float, labels: Dict[str, str] = None, metric_type: MetricType = MetricType.GAUGE):
        """Record a metric value"""
        labels = labels or {}
        metric = Metric(
            name=name,
            type=metric_type,
            value=value,
            labels=labels,
            description=self._get_metric_description(name)
        )

        self.metrics[name].append(metric)

        # Update aggregates
        self._update_aggregates(name)

    def get_metric(self, name: str, time_range: int = 300) -> Optional[Dict[str, Any]]:
        """Get metric data for a time range"""
        if name not in self.metrics:
            return None

        cutoff_time = datetime.utcnow() - timedelta(seconds=time_range)
        recent_metrics = [m for m in self.metrics[name] if m.timestamp > cutoff_time]

        if not recent_metrics:
            return None

        values = [m.value for m in recent_metrics]

        return {
            'name': name,
            'current': values[-1] if values else 0,
            'min': min(values) if values else 0,
            'max': max(values) if values else 0,
            'avg': statistics.mean(values) if values else 0,
            'count': len(values),
            'time_range_seconds': time_range
        }

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all available metrics"""
        result = {}
        for name in self.metrics.keys():
            metric_data = self.get_metric(name)
            if metric_data:
                result[name] = metric_data
        return result

    def _collection_loop(self):
        """Main metrics collection loop"""
        while self._running:
            try:
                self._collect_system_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                print(f"Error in metrics collection: {e}")
                time.sleep(self.collection_interval)

    def _collect_system_metrics(self):
        """Collect system-level metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.record_metric('system.cpu.usage', cpu_percent, {'unit': 'percent'})

        # Memory usage
        memory = psutil.virtual_memory()
        self.record_metric('system.memory.usage', memory.percent, {'unit': 'percent'})
        self.record_metric('system.memory.used', memory.used / 1024 / 1024, {'unit': 'MB'})

        # Disk usage
        disk = psutil.disk_usage('/')
        self.record_metric('system.disk.usage', disk.percent, {'unit': 'percent'})

        # Network I/O
        net_io = psutil.net_io_counters()
        self.record_metric('system.network.bytes_sent', net_io.bytes_sent / 1024 / 1024, {'unit': 'MB'})
        self.record_metric('system.network.bytes_recv', net_io.bytes_recv / 1024 / 1024, {'unit': 'MB'})

        # Process information
        process = psutil.Process()
        self.record_metric('process.cpu.usage', process.cpu_percent(), {'unit': 'percent'})
        self.record_metric('process.memory.rss', process.memory_info().rss / 1024 / 1024, {'unit': 'MB'})

    def _update_aggregates(self, metric_name: str):
        """Update aggregate statistics for a metric"""
        if metric_name not in self.metrics:
            return

        metrics = list(self.metrics[metric_name])
        if not metrics:
            return

        values = [m.value for m in metrics]
        timestamps = [m.timestamp for m in metrics]

        self.aggregates[metric_name] = {
            'count': len(values),
            'sum': sum(values),
            'min': min(values),
            'max': max(values),
            'avg': statistics.mean(values),
            'stddev': statistics.stdev(values) if len(values) > 1 else 0,
            'latest': values[-1],
            'latest_timestamp': timestamps[-1],
            'time_span': (timestamps[-1] - timestamps[0]).total_seconds() if len(timestamps) > 1 else 0
        }

    def _get_metric_description(self, name: str) -> str:
        """Get description for a metric name"""
        descriptions = {
            'system.cpu.usage': 'System CPU usage percentage',
            'system.memory.usage': 'System memory usage percentage',
            'system.disk.usage': 'System disk usage percentage',
            'system.network.bytes_sent': 'Network bytes sent',
            'system.network.bytes_recv': 'Network bytes received',
            'process.cpu.usage': 'Process CPU usage percentage',
            'process.memory.rss': 'Process resident set size memory',
            'api.request.count': 'Total API requests',
            'api.request.duration': 'API request duration',
            'api.error.count': 'API error count',
            'agent.task.count': 'Agent task count',
            'agent.task.duration': 'Agent task duration'
        }
        return descriptions.get(name, f'Metric: {name}')


class AlertSystem:
    """Intelligent alerting system"""

    def __init__(self):
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.alert_callbacks: List[Callable] = []
        self.resolved_alerts: deque = deque(maxlen=1000)

    def add_alert_rule(self, name: str, metric_name: str, threshold: float,
                      condition: str, severity: AlertSeverity, description: str = ""):
        """Add an alert rule"""
        self.alert_rules[name] = {
            'metric_name': metric_name,
            'threshold': threshold,
            'condition': condition,
            'severity': severity,
            'description': description,
            'enabled': True
        }

    def remove_alert_rule(self, name: str):
        """Remove an alert rule"""
        if name in self.alert_rules:
            del self.alert_rules[name]

    def check_alerts(self, metrics_collector: MetricsCollector):
        """Check all alert rules against current metrics"""
        for rule_name, rule in self.alert_rules.items():
            if not rule['enabled']:
                continue

            metric_data = metrics_collector.get_metric(rule['metric_name'])
            if not metric_data:
                continue

            current_value = metric_data['current']
            threshold = rule['threshold']
            condition = rule['condition']

            alert_triggered = self._check_condition(current_value, threshold, condition)

            if alert_triggered:
                self._trigger_alert(rule_name, rule, current_value)
            else:
                self._resolve_alert(rule_name)

    def _check_condition(self, value: float, threshold: float, condition: str) -> bool:
        """Check if alert condition is met"""
        if condition == 'above':
            return value > threshold
        elif condition == 'below':
            return value < threshold
        elif condition == 'equals':
            return abs(value - threshold) < 0.001
        return False

    def _trigger_alert(self, rule_name: str, rule: Dict[str, Any], current_value: float):
        """Trigger an alert"""
        if rule_name in self.alerts and not self.alerts[rule_name].resolved:
            return  # Alert already active

        alert = Alert(
            id=f"{rule_name}_{int(time.time())}",
            name=rule_name,
            severity=rule['severity'],
            message=f"{rule['description']} - Current: {current_value:.2f}, Threshold: {rule['threshold']:.2f}",
            metric_name=rule['metric_name'],
            threshold=rule['threshold'],
            current_value=current_value,
            condition=rule['condition'],
            timestamp=datetime.utcnow()
        )

        self.alerts[rule_name] = alert

        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                asyncio.run(callback(alert))
            except:
                pass  # Ignore callback errors

    def _resolve_alert(self, rule_name: str):
        """Resolve an alert"""
        if rule_name in self.alerts and not self.alerts[rule_name].resolved:
            alert = self.alerts[rule_name]
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            self.resolved_alerts.append(alert)

    def add_alert_callback(self, callback: Callable):
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return [alert for alert in self.alerts.values() if not alert.resolved]

    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        return list(self.resolved_alerts)[-limit:]


class PredictiveAnalyzer:
    """Predictive analytics for performance issues"""

    def __init__(self):
        self.historical_data: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.prediction_models: Dict[str, Dict[str, Any]] = {}
        self.anomaly_threshold = 2.0  # Standard deviations

    def add_data_point(self, metric_name: str, value: float, timestamp: datetime = None):
        """Add data point for analysis"""
        timestamp = timestamp or datetime.utcnow()
        self.historical_data[metric_name].append((timestamp, value))

        # Keep only recent data (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.historical_data[metric_name] = [
            (ts, val) for ts, val in self.historical_data[metric_name] if ts > cutoff
        ]

    def predict_trend(self, metric_name: str, hours_ahead: int = 1) -> Dict[str, Any]:
        """Predict future values for a metric"""
        if metric_name not in self.historical_data:
            return {'error': 'No historical data available'}

        data = self.historical_data[metric_name]
        if len(data) < 10:  # Need minimum data points
            return {'error': 'Insufficient data for prediction'}

        # Simple linear regression for trend prediction
        timestamps = [(ts - data[0][0]).total_seconds() / 3600 for ts, _ in data]  # Hours from start
        values = [val for _, val in data]

        if len(set(values)) <= 1:  # No variation
            return {'predicted_value': values[0], 'confidence': 0.5}

        # Calculate linear regression
        n = len(timestamps)
        sum_x = sum(timestamps)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(timestamps, values))
        sum_xx = sum(x * x for x in timestamps)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n

        # Predict future value
        future_x = timestamps[-1] + hours_ahead
        predicted_value = slope * future_x + intercept

        # Calculate confidence (simplified)
        residuals = [y - (slope * x + intercept) for x, y in zip(timestamps, values)]
        mse = sum(r * r for r in residuals) / len(residuals)
        confidence = max(0, 1 - mse / (max(values) - min(values) + 1))

        return {
            'current_value': values[-1],
            'predicted_value': max(0, predicted_value),  # Ensure non-negative
            'slope': slope,
            'confidence': confidence,
            'trend': 'increasing' if slope > 0.1 else 'decreasing' if slope < -0.1 else 'stable'
        }

    def detect_anomalies(self, metric_name: str) -> List[Dict[str, Any]]:
        """Detect anomalies in metric data"""
        if metric_name not in self.historical_data:
            return []

        data = self.historical_data[metric_name]
        if len(data) < 20:  # Need sufficient data
            return []

        values = [val for _, val in data]

        # Calculate rolling mean and standard deviation
        window_size = min(10, len(values) // 2)
        anomalies = []

        for i in range(window_size, len(values)):
            window = values[i-window_size:i]
            mean = statistics.mean(window)
            stddev = statistics.stdev(window) if len(window) > 1 else 0

            current_value = values[i]
            if stddev > 0:
                z_score = abs(current_value - mean) / stddev
                if z_score > self.anomaly_threshold:
                    anomalies.append({
                        'timestamp': data[i][0],
                        'value': current_value,
                        'expected_range': (mean - stddev, mean + stddev),
                        'z_score': z_score,
                        'severity': 'high' if z_score > 3 else 'medium'
                    })

        return anomalies[-10:]  # Return last 10 anomalies

    def get_recommendations(self, metric_name: str) -> List[str]:
        """Get recommendations based on metric analysis"""
        recommendations = []

        prediction = self.predict_trend(metric_name)
        if 'predicted_value' in prediction:
            if prediction['trend'] == 'increasing' and prediction['predicted_value'] > 80:
                recommendations.append(f"High {metric_name} predicted - consider scaling resources")

        anomalies = self.detect_anomalies(metric_name)
        if anomalies:
            recommendations.append(f"Anomalies detected in {metric_name} - investigate recent changes")

        return recommendations


class PerformanceMonitor:
    """Main performance monitoring system"""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.alert_system = AlertSystem()
        self.predictive_analyzer = PredictiveAnalyzer()
        self.health_checks: Dict[str, Callable] = {}
        self._monitoring_active = False

    async def start_monitoring(self):
        """Start the performance monitoring system"""
        self._monitoring_active = True
        self.metrics_collector.start_collection()

        # Set up default alert rules
        self._setup_default_alerts()

        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self):
        """Stop the performance monitoring system"""
        self._monitoring_active = False
        self.metrics_collector.stop_collection()

    def add_health_check(self, name: str, check_func: Callable):
        """Add a custom health check"""
        self.health_checks[name] = check_func

    def record_api_request(self, endpoint: str, duration: float, status_code: int, method: str = "GET"):
        """Record API request metrics"""
        self.metrics_collector.record_metric(
            'api.request.count',
            1,
            {'endpoint': endpoint, 'method': method, 'status': str(status_code)},
            MetricType.COUNTER
        )

        self.metrics_collector.record_metric(
            'api.request.duration',
            duration,
            {'endpoint': endpoint, 'method': method},
            MetricType.GAUGE
        )

        if status_code >= 400:
            self.metrics_collector.record_metric(
                'api.error.count',
                1,
                {'endpoint': endpoint, 'status': str(status_code)},
                MetricType.COUNTER
            )

    def record_agent_task(self, agent_type: str, task_name: str, duration: float, success: bool):
        """Record agent task metrics"""
        self.metrics_collector.record_metric(
            'agent.task.count',
            1,
            {'agent_type': agent_type, 'task': task_name, 'success': str(success)},
            MetricType.COUNTER
        )

        self.metrics_collector.record_metric(
            'agent.task.duration',
            duration,
            {'agent_type': agent_type, 'task': task_name},
            MetricType.GAUGE
        )

    async def get_system_health(self) -> SystemHealth:
        """Get comprehensive system health status"""
        metrics = self.metrics_collector.get_all_metrics()

        # Calculate overall status
        cpu_usage = metrics.get('system.cpu.usage', {}).get('current', 0)
        memory_usage = metrics.get('system.memory.usage', {}).get('current', 0)
        error_rate = metrics.get('api.error.count', {}).get('current', 0)

        if cpu_usage > 90 or memory_usage > 90 or error_rate > 10:
            overall_status = 'unhealthy'
        elif cpu_usage > 70 or memory_usage > 70 or error_rate > 5:
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'

        # Get network I/O
        network_io = {
            'bytes_sent': metrics.get('system.network.bytes_sent', {}).get('current', 0),
            'bytes_recv': metrics.get('system.network.bytes_recv', {}).get('current', 0)
        }

        # Calculate uptime (simplified)
        uptime = time.time() - psutil.boot_time()

        return SystemHealth(
            overall_status=overall_status,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_usage=metrics.get('system.disk.usage', {}).get('current', 0),
            network_io=network_io,
            active_connections=0,  # Would need to track actual connections
            response_time_avg=metrics.get('api.request.duration', {}).get('avg', 0),
            error_rate=error_rate,
            uptime=uptime,
            last_updated=datetime.utcnow()
        )

    async def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        metrics = self.metrics_collector.get_all_metrics()
        active_alerts = self.alert_system.get_active_alerts()

        # Get predictions for key metrics
        predictions = {}
        for metric_name in ['system.cpu.usage', 'system.memory.usage', 'api.request.duration']:
            pred = self.predictive_analyzer.predict_trend(metric_name)
            if 'predicted_value' in pred:
                predictions[metric_name] = pred

        # Get anomalies
        anomalies = {}
        for metric_name in metrics.keys():
            metric_anomalies = self.predictive_analyzer.detect_anomalies(metric_name)
            if metric_anomalies:
                anomalies[metric_name] = metric_anomalies

        # Get recommendations
        recommendations = []
        for metric_name in metrics.keys():
            recs = self.predictive_analyzer.get_recommendations(metric_name)
            recommendations.extend(recs)

        # Get system health
        system_health = await self.get_system_health()

        return {
            'timestamp': datetime.utcnow(),
            'metrics': metrics,
            'active_alerts': [self._alert_to_dict(alert) for alert in active_alerts],
            'predictions': predictions,
            'anomalies': anomalies,
            'recommendations': list(set(recommendations)),  # Remove duplicates
            'system_health': self._health_to_dict(system_health)
        }

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring_active:
            try:
                # Check alerts
                self.alert_system.check_alerts(self.metrics_collector)

                # Update predictive analyzer with new data
                for metric_name, metric_data in self.metrics_collector.get_all_metrics().items():
                    if 'current' in metric_data:
                        self.predictive_analyzer.add_data_point(
                            metric_name,
                            metric_data['current']
                        )

                # Run health checks
                for check_name, check_func in self.health_checks.items():
                    try:
                        result = await check_func()
                        self.metrics_collector.record_metric(
                            f'health_check.{check_name}',
                            1 if result else 0,
                            {'status': 'pass' if result else 'fail'}
                        )
                    except Exception as e:
                        print(f"Health check {check_name} failed: {e}")

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)

    def _setup_default_alerts(self):
        """Set up default alert rules"""
        self.alert_system.add_alert_rule(
            'high_cpu_usage',
            'system.cpu.usage',
            80.0,
            'above',
            AlertSeverity.WARNING,
            'CPU usage is above 80%'
        )

        self.alert_system.add_alert_rule(
            'high_memory_usage',
            'system.memory.usage',
            85.0,
            'above',
            AlertSeverity.ERROR,
            'Memory usage is above 85%'
        )

        self.alert_system.add_alert_rule(
            'high_error_rate',
            'api.error.count',
            5.0,
            'above',
            AlertSeverity.ERROR,
            'API error rate is above 5%'
        )

    def _alert_to_dict(self, alert: Alert) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            'id': alert.id,
            'name': alert.name,
            'severity': alert.severity.value,
            'message': alert.message,
            'metric_name': alert.metric_name,
            'threshold': alert.threshold,
            'current_value': alert.current_value,
            'condition': alert.condition,
            'timestamp': alert.timestamp.isoformat(),
            'resolved': alert.resolved
        }

    def _health_to_dict(self, health: SystemHealth) -> Dict[str, Any]:
        """Convert health status to dictionary"""
        return {
            'overall_status': health.overall_status,
            'cpu_usage': health.cpu_usage,
            'memory_usage': health.memory_usage,
            'disk_usage': health.disk_usage,
            'network_io': health.network_io,
            'active_connections': health.active_connections,
            'response_time_avg': health.response_time_avg,
            'error_rate': health.error_rate,
            'uptime': health.uptime,
            'last_updated': health.last_updated.isoformat()
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    return performance_monitor