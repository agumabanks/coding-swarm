# 🚀 Sanaa - Comprehensive AI Development Assistant

**Sanaa** is a self-contained, enterprise-grade AI coding assistant that provides everything you need for modern software development. Inspired by the best features of AI coding tools, Sanaa combines multiple specialized agents with persistent memory, comprehensive project management, and seamless integration with your existing Docker infrastructure.

## ✨ What Makes Sanaa Special

- **🤖 Specialized Framework Agents**: React, Laravel, Flutter, and planning experts
- **🧠 Persistent Memory**: Tracks work sessions, progress, and stopping points
- **📁 Project Management**: Complete project lifecycle with templates and workflows
- **🔍 Advanced Debugging**: Framework-specific issue detection and auto-fixing
- **📋 Comprehensive Planning**: Multi-framework development strategies
- **🐳 Infrastructure Integration**: Seamless Docker container management
- **🎨 Modern UI**: Steve Jobs-inspired interface design
- **⚡ Self-Healing**: Automatic container health monitoring and recovery

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Sanaa Projects Interface                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🤖 Agent Registry                                   │   │
│  │ • React Agent     • Laravel Agent    • Flutter Agent│   │
│  │ • Planning Agent  • Debug Agent      • Coder Agent  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🧠 Context Awareness                                │   │
│  │ • Framework Detection • Dependency Analysis         │   │
│  │ • Code Quality     • Security Insights              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📁 Project Management                               │   │
│  │ • Template System  • Work Sessions   • Memory       │   │
│  │ • Milestones      • Progress Tracking               │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Docker Infrastructure                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🤖 AI Models (Llama.cpp)                             │   │
│  │ • API Model (8080) • Web Model (8081)                │   │
│  │ • Mobile (8082)    • Testing (8083)                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🗄️ Databases & Services                             │   │
│  │ • MySQL (3306)    • PostgreSQL (5432) • Redis (6379)│   │
│  │ • Meilisearch     • Mailpit         • Selenium       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Bootstrap the Environment
```bash
# Create virtual environment and install dependencies
python3 tools/bootstrap.py
source .venv/bin/activate
```

### 2. Launch Sanaa Projects
```bash
# Main interface - comprehensive project management
sanaa
# or
python3 -m sanaa_projects
# or
sanaa projects

# Direct CLI commands
sanaa react component MyComponent
sanaa laravel model User
sanaa flutter widget HomeScreen
sanaa debug --project my-app
sanaa plan "Build an e-commerce platform"
```

### 3. Health Check & Auto-Healing
```bash
# Check system health and fix issues
sanaa health

# Test LLM connection and system components
python3 test_llm_connection.py

# Interactive system monitoring
sanaa projects
# Choose option 6: System Status
# Choose option 7: LLM Connection Test
# Choose option 8: Auto-Healing
```

---

## 🎯 Core Features

### 🤖 Specialized Agents

#### React Agent
```bash
sanaa react component ProductCard
sanaa react hook useAuth
sanaa react page Dashboard
sanaa react api userApi
```
- **Component Generation**: React components with TypeScript
- **Custom Hooks**: Reusable logic with proper patterns
- **API Integration**: RESTful API clients
- **State Management**: Context, Redux, Zustand patterns

#### Laravel Agent
```bash
sanaa laravel model Product
sanaa laravel controller ProductController
sanaa laravel migration create_products_table
sanaa laravel request StoreProductRequest
sanaa laravel resource ProductResource
```
- **Eloquent Models**: With relationships and validation
- **Controllers**: RESTful API and web controllers
- **Database Migrations**: Schema management
- **Form Requests**: Validation and authorization

#### Flutter Agent
```bash
sanaa flutter widget ProductCard
sanaa flutter provider AuthProvider
sanaa flutter model UserModel
sanaa flutter service ApiService
sanaa flutter screen ProductList
sanaa flutter bloc AuthBloc
```
- **Widget Generation**: Stateful/stateless widgets
- **State Management**: Provider, Riverpod, BLoC patterns
- **Data Models**: JSON serialization
- **Services**: API clients and business logic

#### Advanced Debugger
```bash
sanaa debug --project my-app
sanaa debug --deep  # Comprehensive analysis
```
- **Framework-Specific Issues**: React, Laravel, Flutter bugs
- **Performance Analysis**: Bottleneck identification
- **Security Scanning**: Vulnerability detection
- **Auto-Fixing**: Automated code improvements

#### Planning Agent
```bash
sanaa plan "Build a social media platform"
```
- **Architecture Design**: System design and patterns
- **Timeline Planning**: Realistic development schedules
- **Risk Assessment**: Technical and business risks
- **Resource Allocation**: Team and technology recommendations

### 📁 Project Management

#### Create New Projects
```bash
# Launch Sanaa Projects interface
sanaa
# or
sanaa projects

# Then follow the interactive wizard:
# 1. Choose "Create New Project"
# 2. Select framework (React, Laravel, Flutter)
# 3. Pick template (Basic, Full-Stack, API-Only, etc.)
# 4. Configure options
```

#### Available Templates

**React Templates:**
- `react-basic`: Simple React app with Vite
- `react-nextjs`: Full-stack Next.js application
- `react-typescript`: TypeScript-first React setup

**Laravel Templates:**
- `laravel-api`: RESTful API with Sanctum auth
- `laravel-fullstack`: Complete web application
- `laravel-admin`: Admin panel with user management

**Flutter Templates:**
- `flutter-basic`: Simple Flutter app
- `flutter-firebase`: Firebase integration
- `flutter-bloc`: BLoC pattern implementation

#### Work Session Tracking
- **Persistent Memory**: All sessions automatically saved
- **Progress Tracking**: Task completion and milestones
- **Stopping Points**: Resume exactly where you left off
- **Context Preservation**: Maintain conversation history

### 🔍 Advanced Features

#### Smart Context Awareness
- **Framework Detection**: Automatic technology identification
- **Dependency Analysis**: Package and library mapping
- **Code Quality Scoring**: Automated quality assessment
- **Security Insights**: Vulnerability detection
- **Performance Recommendations**: Optimization suggestions

#### System Monitoring & Auto-Healing
```bash
sanaa health  # Check all services
```
- **Container Health**: Docker container monitoring
- **Service Availability**: HTTP endpoint checking
- **Auto-Restart**: Failed container recovery
- **Performance Metrics**: Response time tracking
- **Trend Analysis**: Health status trends

#### Multi-Modal Development
- **Web Development**: React, Next.js, Vue.js
- **Backend Development**: Laravel, Django, FastAPI
- **Mobile Development**: Flutter, React Native
- **API Development**: REST, GraphQL, WebSocket
- **Database Design**: MySQL, PostgreSQL, MongoDB

---

## 🐳 Infrastructure Integration

### Docker Services
```bash
# Check all containers
docker ps

# Expected services:
✓ coding-swarm-qwen-api-1     (8080) - API Model
✓ coding-swarm-qwen-web-1     (8081) - Web Model
✓ coding-swarm-qwen-mobile-1  (8082) - Mobile Model
✓ coding-swarm-qwen-test-1    (8083) - Testing Model
✓ backend-mysql-1             (3306) - MySQL Database
✓ coding-swarm-postgres-1     (5432) - PostgreSQL
✓ coding-swarm-redis-1        (6379) - Redis Cache
✓ backend-meilisearch-1       (7700) - Search Engine
✓ backend-mailpit-1           (1025/8025) - Email Testing
✓ backend-selenium-1          (4444) - E2E Testing
```

### Model Configuration
```bash
# Environment variables
export OPENAI_BASE_URL="http://127.0.0.1:8080/v1"
export OPENAI_MODEL="qwen2.5-coder-7b-instruct-q4_k_m"
export OPENAI_API_KEY="sk-local"
```

### Health Monitoring
```bash
# Continuous monitoring
sanaa health

# Auto-healing (attempts to fix unhealthy containers)
# Built-in monitoring with automatic recovery
```

---

## 📚 Usage Examples

### Complete Development Workflow

```bash
# 1. Start Sanaa Projects
sanaa projects

# 2. Create new Laravel API project
# - Select "Create New Project"
# - Choose "Laravel" framework
# - Select "API" template
# - Configure database settings

# 3. Generate initial models
sanaa laravel model User
sanaa laravel model Product
sanaa laravel model Order

# 4. Create controllers
sanaa laravel controller UserController
sanaa laravel controller ProductController

# 5. Set up authentication
sanaa laravel migration create_users_table
sanaa laravel request LoginRequest

# 6. Debug and optimize
sanaa debug --project my-api --deep

# 7. Plan next phase
sanaa plan "Add payment integration and admin panel"
```

### React Development Example

```bash
# Create React component library
sanaa react component Button
sanaa react component Input
sanaa react component Modal

# Add custom hooks
sanaa react hook useApi
sanaa react hook useLocalStorage

# Create pages
sanaa react page Home
sanaa react page About
sanaa react page Contact

# Set up API integration
sanaa react api userApi
sanaa react api productApi
```

### Flutter Mobile App

```bash
# Create core widgets
sanaa flutter widget AppBar
sanaa flutter widget BottomNav
sanaa flutter widget ProductCard

# Set up state management
sanaa flutter provider AuthProvider
sanaa flutter bloc ProductBloc

# Create screens
sanaa flutter screen HomeScreen
sanaa flutter screen ProductScreen
sanaa flutter screen ProfileScreen

# Add services
sanaa flutter service ApiService
sanaa flutter service AuthService
```

---

## 🔧 Configuration

### Environment Variables
```bash
# Model Configuration
SANAA_MODEL_BASE=http://127.0.0.1:8080/v1
SANAA_MODEL=qwen2.5-coder-7b-instruct-q4_k_m

# Project Settings
SANAA_DEFAULT_PROJECT=~/projects
SANAA_AUTO_SAVE=true
SANAA_CACHE_TTL=300

# UI Preferences
SANAA_THEME=dark
SANAA_PREFERRED_EDITOR=code
```

### Configuration File
```bash
# ~/.sanaa/config.json
{
  "model_base": "http://127.0.0.1:8080/v1",
  "model_name": "qwen2.5-coder-7b-instruct-q4_k_m",
  "max_context_files": 10,
  "enable_semantic_search": true,
  "preferred_editor": "code",
  "theme": "dark"
}
```

---

## 🎨 Interface Features

### Modern CLI Design
- **Rich Terminal UI**: Beautiful tables, panels, and progress bars
- **Interactive Menus**: Easy navigation with keyboard shortcuts
- **Smart Suggestions**: Context-aware recommendations
- **Real-time Feedback**: Live progress for long operations

### Project Dashboard
```
🚀 Sanaa Projects • AI-Powered Development Assistant

📁 Current Project: my-laravel-api
├── Framework: Laravel
├── Files: 247
├── Sessions: 12
├── Active Session: Laravel Agent (2.3h)
└── Current Task: Implement user authentication

┌─ Main Menu ──────────────────────────┐
│ 1. 📁 Project Management            │
│ 2. 💻 Start Coding Session          │
│ 3. 🔍 Debug & Fix Issues           │
│ 4. 📋 Planning & Architecture      │
│ 5. ❓ Q&A Assistance               │
│ 6. 📊 System Status               │
│ 7. ❓ Help                         │
│ q. 🚪 Exit                        │
└─────────────────────────────────────┘
```

---

## 🛠️ Advanced Capabilities

### Intelligent Code Generation
- **Framework-Specific Patterns**: Follows each framework's best practices
- **Type Safety**: Full TypeScript support where applicable
- **Testing Integration**: Generates tests alongside code
- **Documentation**: Automatic code documentation

### Persistent Work Sessions
- **Session Recovery**: Resume exactly where you left off
- **Progress Tracking**: Visual progress indicators
- **Task Management**: Break down complex tasks
- **Context Preservation**: Maintain conversation history

### Multi-Framework Orchestration
- **Cross-Framework Communication**: Agents can work together
- **Dependency Management**: Handle inter-framework dependencies
- **Unified Architecture**: Consistent patterns across frameworks
- **Deployment Coordination**: Multi-service deployment planning

### Quality Assurance
- **Automated Testing**: Generate and run tests
- **Code Quality Checks**: Linting and formatting
- **Security Scanning**: Vulnerability detection
- **Performance Monitoring**: Optimization recommendations

---

## 🚀 Getting Started (Detailed)

### Prerequisites
- **Python 3.11+** with virtual environments
- **Docker** with running containers
- **Git** for version control
- **4GB+ RAM** for model inference

### Installation
```bash
# 1. Clone and setup
git clone <repository>
cd sanaa
python3 tools/bootstrap.py

# 2. Activate environment
source .venv/bin/activate

# 3. Verify installation
sanaa --help
```

### First Project
```bash
# Launch Sanaa Projects
sanaa

# Follow the setup wizard:
# 1. Create new project
# 2. Choose framework
# 3. Select template
# 4. Start coding!
```

---

## 📈 Performance & Monitoring

### System Health Dashboard
```bash
sanaa health
```
Shows real-time status of:
- Docker containers
- Model endpoints
- Database connections
- External services
- Performance metrics

### Auto-Healing Features
- **Container Restart**: Automatic recovery of failed containers
- **Service Monitoring**: Continuous health checking
- **Performance Alerts**: Response time monitoring
- **Resource Optimization**: Memory and CPU usage tracking

### Analytics & Insights
- **Usage Statistics**: Track coding patterns
- **Productivity Metrics**: Measure development efficiency
- **Quality Trends**: Code quality over time
- **Performance History**: System performance trends

---

## 🔒 Security & Best Practices

### Code Security
- **Input Validation**: Automatic validation generation
- **Authentication**: Secure auth pattern implementation
- **Authorization**: Role-based access control
- **Data Sanitization**: XSS and injection prevention

### Development Security
- **Dependency Scanning**: Vulnerable package detection
- **Code Review**: Automated security checks
- **Secret Management**: Environment variable handling
- **Access Control**: API security best practices

---

## 🎯 Comparison with Other Tools

| Feature | Sanaa | Kilo Code | GitHub Copilot | Other AI Assistants |
|---------|-------|-----------|----------------|-------------------|
| **Local Models** | ✅ | ❌ | ❌ | ❌ |
| **Framework Specialists** | ✅ | ❌ | ❌ | ❌ |
| **Persistent Memory** | ✅ | ❌ | ❌ | ❌ |
| **Project Management** | ✅ | ❌ | ❌ | ❌ |
| **Auto-Healing** | ✅ | ❌ | ❌ | ❌ |
| **Multi-Framework** | ✅ | ❌ | ❌ | ❌ |
| **Self-Contained** | ✅ | ❌ | ❌ | ❌ |
| **Docker Integration** | ✅ | ❌ | ❌ | ❌ |

---

## 🚨 Troubleshooting

### Common Issues

**Containers Unhealthy**
```bash
# Check container logs
docker logs coding-swarm-qwen-web-1

# Restart unhealthy containers
sanaa health  # Auto-healing
```

**Model Not Responding**
```bash
# Check model endpoint
curl http://127.0.0.1:8080/v1/models

# Verify model file exists
ls -la /opt/models/
```

**Import Errors**
```bash
# Reinstall packages
python3 tools/bootstrap.py
source .venv/bin/activate
```

### Support Resources
- **Documentation**: Comprehensive in-project docs
- **Health Monitoring**: Built-in system diagnostics
- **Auto-Recovery**: Automatic issue resolution
- **Community**: Open-source project

---

## 🔧 Troubleshooting LLM Connection

### Q&A Not Working?
If the Q&A assistance shows generic responses instead of AI answers:

1. **Check Model Status**:
   ```bash
   # Test all model endpoints
   python3 test_llm_connection.py

   # Check Docker containers
   docker ps | grep coding-swarm
   ```

2. **Verify Model Files**:
   ```bash
   # Check if model files exist
   ls -la /opt/models/

   # Expected: Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf
   ```

3. **Check Model Ports**:
   ```bash
   # Test individual endpoints
   curl http://127.0.0.1:8080/v1/models
   curl http://127.0.0.1:8081/v1/models
   curl http://127.0.0.1:8082/v1/models
   curl http://127.0.0.1:8083/v1/models
   ```

4. **Restart Containers**:
   ```bash
   # Restart all Sanaa containers
   docker restart coding-swarm-qwen-api-1
   docker restart coding-swarm-qwen-web-1
   docker restart coding-swarm-qwen-mobile-1
   docker restart coding-swarm-qwen-test-1
   ```

5. **Check Logs**:
   ```bash
   # View container logs
   docker logs coding-swarm-qwen-api-1
   ```

### Environment Variables
Make sure these are set correctly:
```bash
export OPENAI_BASE_URL="http://127.0.0.1:8080/v1"
export OPENAI_MODEL="qwen2.5-coder-7b-instruct-q4_k_m"
export OPENAI_API_KEY="sk-local"
```

---

## 🧠 **Enhanced Memory System**

Sanaa Projects includes a sophisticated memory system designed for optimal performance and reliability:

### **Persistent Memory Features**
- **Session Tracking**: All work sessions are automatically saved and restored
- **Context Preservation**: Project context and conversation history maintained
- **Performance Optimization**: Intelligent caching and memory cleanup
- **Cross-Session Continuity**: Seamless experience across multiple sessions

### **Memory Management**
```bash
# View memory statistics
sanaa projects
# Choose option 6: System Status
# Shows memory usage, session counts, and performance metrics
```

### **Automatic Optimization**
- **Smart Cleanup**: Removes old sessions and duplicate data
- **Cache Management**: Optimizes frequently accessed data
- **Memory Limits**: Prevents memory bloat with configurable limits
- **Background Processing**: Non-intrusive optimization during idle time

### **Memory Configuration**
```bash
# Memory settings in ~/.sanaa/config.json
{
  "max_memory_age": 2592000,        # 30 days in seconds
  "max_sessions_per_project": 50,   # Limit sessions per project
  "compression_threshold": 1000,    # Compress after size threshold
  "auto_heal_enabled": true         # Enable automatic issue fixing
}
```

---

## 🔧 **Advanced Health Monitoring**

### **Comprehensive System Checks**
Sanaa includes built-in health monitoring for all system components:

#### **Real-time Health Status**
```bash
sanaa projects
# Choose option 6: System Status
# Shows:
# - Docker container health
# - LLM endpoint connectivity
# - Memory system integrity
# - Project data consistency
# - Performance metrics
```

#### **Automated Health Checks**
- **Periodic Monitoring**: Automatic health checks every 5 minutes
- **Issue Detection**: Identifies orphaned sessions, corrupted files, unreachable endpoints
- **Performance Tracking**: Monitors response times and resource usage
- **Proactive Alerts**: Early warning system for potential issues

### **Auto-Healing System**
```bash
sanaa projects
# Choose option 8: Auto-Healing
# Automatically fixes:
# - Orphaned work sessions
# - Corrupted memory files
# - Unhealthy Docker containers
# - File system inconsistencies
```

#### **Health Monitoring Features**
- **Container Health**: Monitors all Sanaa Docker containers
- **Endpoint Testing**: Verifies LLM model connectivity
- **Memory Integrity**: Checks data consistency and corruption
- **Project Validation**: Ensures project files and paths are valid
- **Performance Metrics**: Tracks system performance over time

### **Health Data Storage**
```bash
# Health status stored in ~/.sanaa/system_health.json
{
  "timestamp": 1642857600,
  "issues": ["Container coding-swarm-qwen-api-1 unhealthy"],
  "memory_stats": {
    "total_projects": 3,
    "total_sessions": 15,
    "active_sessions": 2
  },
  "system_info": {
    "python_version": "3.11",
    "platform": "linux"
  }
}
```

---

## 🧪 **Comprehensive Testing Suite**

### **Enhanced Test Script**
```bash
# Run complete system test
python3 test_llm_connection.py

# Tests include:
# ✅ Model Endpoints (Ports 8080-8083)
# ✅ Agent Creation (React, Laravel, Flutter, etc.)
# ✅ Memory System Integrity
# ✅ Project Management Features
# ✅ Auto-Healing Mechanisms
# ✅ LLM Connection & Responses
```

### **Interactive Testing**
```bash
# Test all features interactively
sanaa projects

# Available test options:
# 7. 🧪 LLM Connection Test - Test AI connectivity
# 8. 🔧 Auto-Healing - Fix system issues automatically
# 6. 📊 System Status - View comprehensive health report
```

### **Performance Benchmarking**
The test suite includes performance benchmarks:
- **CLI Responsiveness**: < 3 seconds startup time
- **LLM Response**: < 10 seconds for AI queries
- **Memory Operations**: < 1 second for save/load
- **Project Creation**: < 5 seconds for new projects

---

## 🚀 **Production-Ready Features**

### **Enterprise-Grade Reliability**
- **Fault Tolerance**: Graceful handling of failures
- **Data Integrity**: Automatic corruption detection and repair
- **Performance Monitoring**: Real-time system performance tracking
- **Automatic Recovery**: Self-healing capabilities for common issues

### **Scalability Features**
- **Memory Optimization**: Efficient handling of large project sets
- **Session Management**: Intelligent cleanup of old sessions
- **Cache Management**: Smart caching for improved performance
- **Resource Monitoring**: Automatic resource usage optimization

### **Security & Privacy**
- **Local AI Models**: All processing happens locally
- **No Data Transmission**: Project data never leaves your system
- **Secure Storage**: Encrypted memory files and configurations
- **Access Control**: Local-only access with no external dependencies

### Common Issues
- **"LLM Connection Error"**: Model server not running
- **"LLM Error: 500"**: Model file not found or corrupted
- **Timeout errors**: Model overloaded or slow hardware
- **Generic responses**: Fallback when AI is unavailable

---

## 🎉 What's Next

### Planned Features
- **Real-time Collaboration**: Multi-user development sessions
- **Advanced Error Detection**: Machine learning-based issue detection
- **Custom Agent Creation**: User-defined specialized agents
- **Cloud Integration**: AWS, GCP, Azure deployment support
- **Mobile App Generation**: Native iOS/Android app creation
- **API Marketplace**: Pre-built API integrations

### Contributing
Sanaa is open-source and welcomes contributions:
- **Agent Development**: Create new specialized agents
- **Template Creation**: Add new project templates
- **Feature Requests**: Suggest new capabilities
- **Bug Reports**: Help improve stability

---

## 📞 Contact & Support

- **Documentation**: [Project Wiki]
- **Issues**: [GitHub Issues]
- **Discussions**: [GitHub Discussions]
- **Email**: [Contact Information]

---

**🎯 Sanaa - Your Complete AI Development Companion**

*Built with ❤️ for developers who demand excellence*

---

## 📋 Complete Command Reference

```bash
# Main Interface
sanaa                       # Launch Sanaa Projects interface
# or
sanaa projects              # Alternative way to launch

# Framework Agents
sanaa react <action> <name> [--project PATH]
sanaa laravel <action> <name> [--project PATH]
sanaa flutter <action> <name> [--project PATH]

# Development Tools
sanaa debug [--project PATH] [--deep]
sanaa plan <goal> [--project PATH]

# System Management
sanaa health                # System health check
sanaa status               # Project status overview
sanaa chat [--project PATH] [--message TEXT]

# Legacy Commands
sanaa welcome              # Welcome screen
python3 bin/sanaa_orchestrator.py  # Direct CLI
./bin/swarm                # Swarm wrapper
```

---

*Last updated: 2025-01-29*
*Version: 2.0.0*
*Sanaa - The Future of AI-Assisted Development* 🚀✨
