# Sanaa Core Modules Documentation

This directory contains comprehensive documentation for all core modules in the Sanaa system.

## Module Index

### Core Infrastructure
- **[Security Module](security.md)** - Encryption, access control, and vulnerability assessment
- **[Enhanced API Module](enhanced_api.md)** - Load balancing, caching, and real-time streaming
- **[Performance Monitor Module](performance_monitor.md)** - System monitoring and predictive analytics
- **[Memory Optimization Module](memory_optimization.md)** - Advanced memory management and profiling

### Agent & Orchestration
- **[Advanced Orchestrator](advanced_orchestrator.md)** - Intelligent agent coordination and conflict resolution
- **[Code Generation Engine](code_generation.md)** - AI-powered code generation with quality assurance
- **[Collaborative Planning](collaborative_planning.md)** - Real-time collaborative planning interfaces

### User Experience
- **[User Interfaces](user_interfaces.md)** - CLI and web interface components
- **[Advanced Debugging](advanced_debugging.md)** - Comprehensive debugging and vulnerability scanning
- **[Deployment Automation](deployment_automation.md)** - Continuous improvement and automated deployment

### Supporting Modules
- **[Context Awareness](context_awareness.md)** - Project and environment context analysis
- **[System Monitor](system_monitor.md)** - System health monitoring and auto-healing
- **[Project Templates](project_templates.md)** - Project scaffolding and templates
- **[MCP Integration](mcp_integration.md)** - Model Context Protocol integration

## Quick Start

### Installation
```bash
pip install sanaa
```

### Basic Usage
```python
from coding_swarm_core import get_security_manager, get_performance_monitor

# Initialize core components
security = get_security_manager()
monitor = get_performance_monitor()

# Start monitoring
await monitor.start_monitoring()
```

### Configuration
```python
# Environment variables
export SANAA_REDIS_URL="redis://localhost:6379"
export SANAA_JWT_SECRET="your-secret-key"
export SANAA_API_PORT=8080
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interfaces                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  CLI  │  Web UI  │  API  │  VS Code Integration     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                 Core Services                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Security │ API │ Performance │ Memory Optimization  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│              Agent & Orchestration                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Orchestrator │ Code Gen │ Planning │ Debugging      │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│               Supporting Services                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Context │ System │ Templates │ MCP Integration      │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 🔒 Security First
- End-to-end encryption
- Role-based access control
- Automated vulnerability scanning
- Security audit logging

### ⚡ High Performance
- Intelligent caching and load balancing
- Real-time performance monitoring
- Memory optimization and leak detection
- Predictive analytics and alerting

### 🤖 Intelligent Automation
- Self-learning agent coordination
- AI-powered code generation
- Automated deployment and rollback
- Continuous improvement algorithms

### 🎯 Developer Experience
- Interactive CLI with rich formatting
- VS Code-inspired web interface
- Real-time collaboration tools
- Comprehensive debugging capabilities

## Integration Examples

### Full System Setup
```python
from coding_swarm_core import (
    get_security_manager,
    get_enhanced_api,
    get_performance_monitor,
    get_advanced_orchestrator
)

# Initialize all core components
security = get_security_manager()
api = get_enhanced_api()
monitor = get_performance_monitor()
orchestrator = get_advanced_orchestrator()

# Configure and start
await api.initialize(["http://localhost:8000"])
await monitor.start_monitoring()

# System is ready for use
```

### Custom Integration
```python
# Custom security integration
class CustomAuthenticator:
    def authenticate(self, credentials):
        user = security.validate_token(credentials.token)
        return user and security.validate_access(
            user.id, "custom:resource", "read"
        )

# Custom monitoring
monitor.add_health_check("custom_service", check_custom_service)

# Custom API endpoints
@app.post("/custom/endpoint")
async def custom_endpoint(request: Request):
    # Use enhanced API features
    response = await api.handle_request(request)
    return response
```

## Best Practices

### Security
1. Always validate user input
2. Use HTTPS in production
3. Rotate encryption keys regularly
4. Implement proper logging and monitoring

### Performance
1. Enable caching for expensive operations
2. Monitor memory usage regularly
3. Use connection pooling
4. Implement proper error handling

### Development
1. Follow the modular architecture
2. Write comprehensive tests
3. Document all public APIs
4. Use type hints for better code quality

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure all dependencies are installed
   - Check Python path configuration

2. **Connection Issues**
   - Verify Redis/database connectivity
   - Check network configuration

3. **Performance Issues**
   - Review monitoring dashboards
   - Check resource utilization

4. **Security Alerts**
   - Review vulnerability reports
   - Update dependencies regularly

### Getting Help

- **Documentation**: Check module-specific documentation
- **Logs**: Enable debug logging for detailed information
- **Community**: Join our Discord community
- **Support**: Contact enterprise support for priority issues

## Contributing

We welcome contributions to the Sanaa project! Please see our [Contributing Guide](../CONTRIBUTING.md) for details.

### Development Setup
```bash
git clone https://github.com/your-org/sanaa.git
cd sanaa
pip install -e .[dev]
```

### Testing
```bash
# Run all tests
pytest

# Run specific module tests
pytest tests/test_security.py

# Run with coverage
pytest --cov=coding_swarm_core
```

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## Changelog

### Version 2.0.0 (Latest)
- Complete system redesign with modular architecture
- Advanced security and performance monitoring
- Real-time collaboration and AI-powered features
- Comprehensive web interface with VS Code integration

### Version 1.5.0
- Enhanced API with load balancing and caching
- Advanced debugging and memory optimization
- Deployment automation and continuous improvement

### Version 1.0.0
- Initial release with core agent functionality
- Basic CLI and API interfaces
- Fundamental security and monitoring features

---

For more detailed information about specific modules, please refer to their individual documentation files.