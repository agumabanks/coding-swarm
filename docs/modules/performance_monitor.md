# Performance Monitor Module Documentation

## Overview

The Performance Monitor Module (`packages/core/src/coding_swarm_core/performance_monitor.py`) provides comprehensive system and application performance monitoring for the Sanaa platform, including real-time metrics, alerting, and predictive analytics.

## Features

### 1. Metrics Collector
- **Real-time system metrics** collection (CPU, memory, disk, network)
- **Application performance metrics** (response times, throughput, error rates)
- **Custom metric registration** for application-specific monitoring
- **Time-series data storage** with configurable retention

### 2. Alert System
- **Configurable alert rules** with multiple condition types
- **Multi-severity alerting** (info, warning, error, critical)
- **Alert callbacks** for custom notification handling
- **Alert history and resolution tracking**

### 3. Predictive Analytics
- **Trend analysis** for performance metrics
- **Anomaly detection** using statistical methods
- **Predictive modeling** for resource usage forecasting
- **Automated recommendations** based on analysis

### 4. System Health Monitoring
- **Comprehensive health checks** for all system components
- **Service availability monitoring** with automatic recovery
- **Resource utilization tracking** with capacity planning
- **Performance baseline establishment** and deviation detection

## API Reference

### MetricsCollector

```python
from coding_swarm_core.performance_monitor import MetricsCollector

# Initialize metrics collector
collector = MetricsCollector(retention_period=3600)  # 1 hour retention

# Start collection
collector.start_collection()

# Record custom metrics
collector.record_metric('api.request.count', 1, {'endpoint': '/api/users', 'method': 'GET'})
collector.record_metric('api.request.duration', 0.234, {'endpoint': '/api/users'})

# Get metric data
metric_data = collector.get_metric('api.request.duration', time_range=300)
# Returns: {'current': 0.234, 'min': 0.123, 'max': 0.456, 'avg': 0.234, 'count': 10}

# Get all metrics
all_metrics = collector.get_all_metrics()

# Stop collection
collector.stop_collection()
```

### AlertSystem

```python
from coding_swarm_core.performance_monitor import AlertSystem

# Initialize alert system
alert_system = AlertSystem()

# Add alert rule
alert_system.add_alert_rule(
    name='high_cpu_usage',
    metric_name='system.cpu.usage',
    threshold=80.0,
    condition='above',
    severity='warning',
    description='CPU usage is above 80%'
)

# Add alert callback
async def send_notification(alert):
    print(f"Alert: {alert.name} - {alert.message}")

alert_system.add_alert_callback(send_notification)

# Check alerts (typically called by monitoring loop)
alert_system.check_alerts(metrics_collector)

# Get active alerts
active_alerts = alert_system.get_active_alerts()

# Get alert history
alert_history = alert_system.get_alert_history(limit=50)
```

### PredictiveAnalyzer

```python
from coding_swarm_core.performance_monitor import PredictiveAnalyzer

# Initialize predictive analyzer
analyzer = PredictiveAnalyzer()

# Add data points
analyzer.add_data_point('system.cpu.usage', 45.2)
analyzer.add_data_point('system.memory.usage', 62.8)

# Predict future values
prediction = analyzer.predict_trend('system.cpu.usage', hours_ahead=1)
# Returns: {
#     'predicted_value': 47.8,
#     'confidence': 0.85,
#     'trend': 'increasing'
# }

# Detect anomalies
anomalies = analyzer.detect_anomalies('system.cpu.usage')
# Returns: [
#     {
#         'timestamp': datetime,
#         'value': 95.2,
#         'expected_range': (40.0, 60.0),
#         'z_score': 3.2,
#         'severity': 'high'
#     }
# ]

# Get recommendations
recommendations = analyzer.get_recommendations('system.cpu.usage')
# Returns: ['High CPU usage predicted - consider scaling resources']
```

### PerformanceMonitor

```python
from coding_swarm_core.performance_monitor import PerformanceMonitor

# Initialize performance monitor
monitor = PerformanceMonitor()

# Start monitoring
await monitor.start_monitoring()

# Record API request metrics
monitor.record_api_request(
    endpoint='/api/users',
    duration=0.234,
    status_code=200,
    method='GET'
)

# Record agent task metrics
monitor.record_agent_task(
    agent_type='coder',
    task_name='implement_feature',
    duration=45.6,
    success=True
)

# Get system health
health = await monitor.get_system_health()
# Returns: {
#     'overall_status': 'healthy',
#     'cpu_usage': 45.2,
#     'memory_usage': 62.8,
#     'response_time_avg': 0.234,
#     'error_rate': 0.02
# }

# Get comprehensive performance report
report = await monitor.get_performance_report()
# Returns: {
#     'metrics': {...},
#     'active_alerts': [...],
#     'predictions': {...},
#     'anomalies': {...},
#     'recommendations': [...]
# }

# Stop monitoring
await monitor.stop_monitoring()
```

## Configuration

### Environment Variables

- `PERFORMANCE_MONITOR_RETENTION_PERIOD`: Metrics retention in seconds (default: 3600)
- `PERFORMANCE_MONITOR_COLLECTION_INTERVAL`: Collection interval in seconds (default: 10)
- `ALERT_SYSTEM_MAX_HISTORY`: Maximum alert history size (default: 1000)
- `PREDICTIVE_ANALYZER_ANOMALY_THRESHOLD`: Z-score threshold for anomalies (default: 2.0)

### Alert Rules Configuration

```python
# Configure default alert rules
alert_rules = {
    'high_cpu': {
        'metric': 'system.cpu.usage',
        'threshold': 80.0,
        'severity': 'warning'
    },
    'high_memory': {
        'metric': 'system.memory.usage',
        'threshold': 85.0,
        'severity': 'error'
    },
    'high_error_rate': {
        'metric': 'api.error.count',
        'threshold': 5.0,
        'severity': 'error'
    }
}
```

## Dependencies

- `psutil>=5.9.0`: For system resource monitoring
- `statistics`: Built-in Python statistics module

## Integration Points

### With Other Modules
- **Enhanced API**: API request metrics and performance monitoring
- **Advanced Orchestrator**: Agent task performance tracking
- **Memory Optimization**: Memory usage metrics integration
- **Security Module**: Security event monitoring and alerting

### External Systems
- **Prometheus/Grafana**: Metrics export and visualization
- **ELK Stack**: Log aggregation and analysis
- **PagerDuty/OpsGenie**: Alert notification systems
- **AWS CloudWatch**: Cloud monitoring integration

## Metrics Types

### System Metrics
- **CPU Usage**: Overall and per-core CPU utilization
- **Memory Usage**: RAM and swap usage statistics
- **Disk I/O**: Read/write operations and throughput
- **Network I/O**: Bandwidth usage and connection counts
- **Process Metrics**: CPU, memory, and I/O for Sanaa processes

### Application Metrics
- **API Metrics**: Request count, response times, error rates
- **Agent Metrics**: Task completion times, success rates, queue lengths
- **Cache Metrics**: Hit/miss ratios, eviction rates, memory usage
- **Database Metrics**: Query times, connection counts, error rates

### Custom Metrics
- **Business Metrics**: User activity, feature usage, conversion rates
- **Performance Metrics**: Custom timing measurements, throughput rates
- **Quality Metrics**: Test coverage, code quality scores, deployment frequency

## Alert Management

### Alert Severities
- **Info**: Informational alerts for awareness
- **Warning**: Potential issues requiring attention
- **Error**: Active problems requiring action
- **Critical**: System-threatening issues requiring immediate action

### Alert Conditions
- **Above**: Metric value exceeds threshold
- **Below**: Metric value falls below threshold
- **Equals**: Metric value equals threshold
- **Not Equals**: Metric value differs from threshold

### Alert Lifecycle
1. **Detection**: Alert condition is met
2. **Notification**: Alert callbacks are triggered
3. **Escalation**: Automatic escalation for unresolved alerts
4. **Resolution**: Manual or automatic alert resolution
5. **Analysis**: Post-mortem analysis for prevention

## Predictive Analytics

### Trend Analysis
- **Linear Regression**: Simple trend prediction for metrics
- **Moving Averages**: Smoothed trend analysis
- **Seasonal Analysis**: Pattern recognition for periodic behavior
- **Confidence Intervals**: Uncertainty quantification for predictions

### Anomaly Detection
- **Statistical Methods**: Z-score and standard deviation analysis
- **Machine Learning**: Advanced anomaly detection algorithms
- **Threshold-Based**: Configurable threshold violation detection
- **Contextual Analysis**: Environment-aware anomaly detection

### Forecasting Models
- **Time Series Forecasting**: ARIMA and exponential smoothing
- **Regression Models**: Linear and polynomial regression
- **Machine Learning**: Random forest and neural network models
- **Ensemble Methods**: Combined forecasting approaches

## Performance Baselines

### Baseline Establishment
1. **Data Collection**: Gather performance data under normal conditions
2. **Statistical Analysis**: Calculate mean, standard deviation, percentiles
3. **Seasonal Adjustment**: Account for time-based patterns
4. **Outlier Removal**: Filter anomalous data points

### Baseline Monitoring
1. **Deviation Detection**: Compare current performance to baseline
2. **Threshold Calculation**: Dynamic threshold based on baseline statistics
3. **Trend Analysis**: Monitor baseline changes over time
4. **Alert Generation**: Notify when performance deviates from baseline

## Best Practices

### Monitoring Setup
1. **Define Key Metrics**: Focus on business-critical performance indicators
2. **Set Appropriate Thresholds**: Balance sensitivity with false positive rates
3. **Implement Alert Escalation**: Ensure critical alerts reach the right people
4. **Regular Review**: Periodically review and update monitoring configuration

### Alert Management
1. **Alert Fatigue Prevention**: Minimize unnecessary notifications
2. **Clear Alert Messages**: Provide actionable information in alerts
3. **Escalation Policies**: Define clear escalation paths for different severities
4. **Post-Mortem Analysis**: Learn from alerts to prevent future occurrences

### Predictive Analytics
1. **Data Quality**: Ensure accurate and consistent metric collection
2. **Model Validation**: Regularly validate prediction accuracy
3. **Feedback Loop**: Use prediction results to improve models
4. **Actionable Insights**: Focus on predictions that enable preventive action

## Troubleshooting

### Common Issues

1. **Missing Metrics**
   - Solution: Check metric collection configuration and permissions
   - Solution: Verify system resource monitoring access

2. **False Positive Alerts**
   - Solution: Adjust alert thresholds based on baseline analysis
   - Solution: Implement alert suppression for known issues

3. **Performance Impact**
   - Solution: Adjust collection intervals to balance monitoring with performance
   - Solution: Use sampling for high-frequency metrics

4. **Data Retention Issues**
   - Solution: Configure appropriate retention periods
   - Solution: Implement data archiving for long-term storage

### Debug Mode

Enable detailed performance logging:
```python
import logging
logging.getLogger('sanaa.performance').setLevel(logging.DEBUG)
```

## Examples

### Complete Monitoring Setup

```python
from coding_swarm_core.performance_monitor import PerformanceMonitor
import asyncio

async def main():
    # Initialize performance monitor
    monitor = PerformanceMonitor()

    # Start monitoring
    await monitor.start_monitoring()

    # Add custom alert rules
    monitor.alert_system.add_alert_rule(
        'api_latency',
        'api.request.duration',
        2.0,
        'above',
        'warning',
        'API response time is too high'
    )

    # Simulate application activity
    for i in range(100):
        # Record API request
        monitor.record_api_request(
            endpoint='/api/data',
            duration=0.1 + (i * 0.01),  # Increasing latency
            status_code=200,
            method='GET'
        )

        # Record agent task
        monitor.record_agent_task(
            agent_type='analyzer',
            task_name='process_data',
            duration=1.5,
            success=True
        )

        await asyncio.sleep(0.1)

    # Get performance report
    report = await monitor.get_performance_report()

    print("Performance Report:")
    print(f"Active Alerts: {len(report['active_alerts'])}")
    print(f"Predictions: {len(report['predictions'])}")
    print(f"Anomalies: {len(report['anomalies'])}")
    print(f"Recommendations: {report['recommendations']}")

    # Stop monitoring
    await monitor.stop_monitoring()

if __name__ == "__main__":
    asyncio.run(main())
```

### Custom Health Checks

```python
from coding_swarm_core.performance_monitor import PerformanceMonitor

# Initialize monitor
monitor = PerformanceMonitor()

# Add custom health check
async def database_health_check():
    """Check database connectivity and performance"""
    try:
        # Simulate database check
        await asyncio.sleep(0.1)  # Simulate query time
        return True
    except Exception:
        return False

monitor.add_health_check('database', database_health_check)

# Add API endpoint health check
async def api_health_check():
    """Check API endpoint availability"""
    try:
        # Simulate API call
        await asyncio.sleep(0.05)
        return True
    except Exception:
        return False

monitor.add_health_check('api_endpoint', api_health_check)
```

This module provides enterprise-grade performance monitoring capabilities with advanced analytics, alerting, and predictive features, enabling proactive system management and optimization.