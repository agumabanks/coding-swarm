# 🌐 Web Research Agent Integration Guide

## Overview

This guide provides comprehensive instructions for integrating controlled internet access into the Sanaa Projects system, enabling AI agents to retrieve supplementary information, documentation, and external resources safely and securely.

## 🏗️ Implementation Approaches

### **Approach 1: Direct Agent Integration (Recommended)**

#### **1. Agent Registration**

Update the agent registry to include the web research agent:

```python
# packages/agents/src/coding_swarm_agents/__init__.py
AGENT_REGISTRY: Dict[str, str] = {
    "architect": "agents.architect:Architect",
    "coder": "agents.coder:Coder",
    "tester": "agents.tester:Tester",
    "debugger": "agents.debugger:Debugger",
    "web_research": "agents.web_research_agent:WebResearchAgent",  # Add this
}
```

#### **2. CLI Integration**

Add web research option to the CLI:

```python
# packages/cli/src/coding_swarm_cli/sanaa_projects.py

# Add to main menu options
options = [
    ("1", "📁 Project Management", "Create, select, and manage projects"),
    ("2", "💻 Start Coding Session", "Begin development with AI assistance"),
    ("3", "🔍 Debug & Fix Issues", "Analyze and fix code problems"),
    ("4", "📋 Planning & Architecture", "Design and plan your project"),
    ("5", "❓ Q&A Assistance", "Get help and answers from AI"),
    ("6", "📊 System Status", "View system and project status"),
    ("7", "🧪 LLM Connection Test", "Test AI model connectivity"),
    ("8", "🔧 Auto-Healing", "Fix system issues automatically"),
    ("9", "🌐 Web Research", "Access external documentation"),  # Add this
    ("q", "🚪 Exit", "Quit Sanaa Projects")
]

# Add handler
elif choice == "9":
    self._handle_web_research()
```

#### **3. Web Research Handler**

```python
async def _handle_web_research(self):
    """Handle web research operations"""
    self._clear_screen()
    self.console.print("[bold cyan]🌐 Web Research[/bold cyan]\n")

    # Get research query
    query = Prompt.ask("What would you like to research?")

    # Select framework
    frameworks = ["react", "laravel", "flutter", "general"]
    framework = Prompt.ask("Framework (or 'general')", default="general")

    # Create web research agent
    context = {
        "project": self.current_project.project.path if self.current_project else ".",
        "goal": f"Research: {query}"
    }

    try:
        agent = create_agent("web_research", context)

        with self.console.status(f"[bold green]Researching '{query}'...[/bold green]"):
            # Perform research
            results = await agent.lookup_documentation(query, framework)

        # Display results
        self.console.print(f"\n[bold green]📚 Research Results:[/bold green]\n")
        self.console.print(Markdown(results))

    except Exception as e:
        self.console.print(f"[red]Research failed: {e}[/red]")

    Prompt.ask("\nPress Enter to continue")
```

### **Approach 2: Docker Container Integration**

#### **1. Start Web Research Service**

```bash
# Start the web research container
docker-compose -f docker-compose.web.yml up -d

# Verify it's running
docker ps | grep sanaa-web-research
```

#### **2. Configure Agent to Use Container**

```python
# Update web research agent configuration
web_config = {
    'use_container': True,
    'container_url': 'http://sanaa-web-research:8000',
    'proxy_url': 'http://localhost:8085'
}
```

#### **3. Test Container Integration**

```bash
# Test the web research API
curl -X POST http://localhost:8085/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "React hooks", "framework": "react"}'
```

## 🔧 Configuration

### **1. Security Configuration**

```json
// web_research_config.json
{
  "web_research": {
    "enabled": true,
    "security_level": "high",
    "allowed_domains": [
      "docs.npmjs.com",
      "reactjs.org",
      "laravel.com",
      "flutter.dev",
      "developer.mozilla.org"
    ]
  }
}
```

### **2. Agent Configuration**

```python
# Agent-specific configuration
WEB_RESEARCH_CONFIG = {
    'max_results': 5,
    'timeout': 10,
    'cache_enabled': True,
    'rate_limit': 10,  # requests per minute
    'content_filter': {
        'max_length': 50000,
        'allowed_types': ['text/html', 'application/json']
    }
}
```

## 📚 Usage Examples

### **1. Documentation Lookup**

```python
# Create web research agent
agent = WebResearchAgent({
    'project': './my-react-app',
    'goal': 'Learn about React hooks'
})

# Lookup documentation
result = await agent.lookup_documentation("useEffect hook", "react")
print(result)
```

### **2. Package Information**

```python
# Get package info
info = await agent.get_package_info("react", "npm")
print(f"Latest version: {info['version']}")
print(f"Description: {info['description']}")
```

### **3. API Reference**

```python
# Get API reference
api_docs = await agent.get_api_reference("useState", "react")
print(api_docs)
```

### **4. Best Practices**

```python
# Get best practices
practices = await agent.get_best_practices("state management", "react")
print(practices)
```

### **5. Troubleshooting**

```python
# Get troubleshooting info
solutions = await agent.get_troubleshooting_info("TypeError: Cannot read property", "react")
print(solutions)
```

## 🔒 Security Implementation

### **1. Domain Whitelisting**

```python
class SafeWebClient:
    def __init__(self, config):
        self.allowed_domains = config.get('allowed_domains', [])
        self.blocked_patterns = config.get('blocked_patterns', [])

    def is_domain_allowed(self, url: str) -> bool:
        """Check if domain is in whitelist"""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc

        # Check allowed domains
        for allowed in self.allowed_domains:
            if domain == allowed or domain.endswith('.' + allowed):
                return True
        return False
```

### **2. Rate Limiting**

```python
class RateLimiter:
    def __init__(self, requests_per_minute: int = 10):
        self.requests_per_minute = requests_per_minute
        self.requests = []

    def is_allowed(self) -> bool:
        """Check if request is within rate limits"""
        now = time.time()

        # Remove old requests
        self.requests = [t for t in self.requests if now - t < 60]

        if len(self.requests) >= self.requests_per_minute:
            return False

        self.requests.append(now)
        return True
```

### **3. Content Filtering**

```python
class ContentFilter:
    def __init__(self, config):
        self.max_length = config.get('max_content_length', 50000)
        self.allowed_types = config.get('allowed_content_types', [])

    def filter_content(self, content: str, content_type: str) -> str:
        """Filter and sanitize content"""
        # Check content type
        if content_type not in self.allowed_types:
            raise ValueError(f"Content type {content_type} not allowed")

        # Check length
        if len(content) > self.max_length:
            content = content[:self.max_length] + "...[truncated]"

        # Sanitize HTML if needed
        if content_type == 'text/html':
            content = self.sanitize_html(content)

        return content
```

## 🐳 Docker Integration

### **1. Container Setup**

```yaml
# docker-compose.web.yml
services:
  sanaa-web-research:
    image: python:3.11-slim
    environment:
      - REQUEST_TIMEOUT=10
      - MAX_CONTENT_LENGTH=50000
      - ALLOWED_DOMAINS=docs.npmjs.com,reactjs.org
    volumes:
      - ./web_cache:/app/web_cache
    networks:
      - sanaa-network
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
```

### **2. Network Configuration**

```yaml
networks:
  sanaa-network:
    driver: bridge
    internal: true  # Isolated network
```

### **3. Nginx Proxy**

```nginx
# nginx.conf
server {
    listen 8085;
    location /api/research {
        limit_req zone=research burst=5 nodelay;
        proxy_pass http://sanaa-web-research:8000;
    }
}
```

## 📊 Monitoring & Analytics

### **1. Request Logging**

```python
class RequestLogger:
    def __init__(self, log_file: str):
        self.log_file = log_file

    def log_request(self, url: str, response_time: float, status: str):
        """Log web research requests"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"{timestamp} | {url} | {response_time:.2f}s | {status}\n"

        with open(self.log_file, 'a') as f:
            f.write(log_entry)
```

### **2. Performance Metrics**

```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'average_response_time': 0,
            'cache_hit_rate': 0
        }

    def record_request(self, success: bool, response_time: float, cached: bool):
        """Record request metrics"""
        self.metrics['total_requests'] += 1

        if success:
            self.metrics['successful_requests'] += 1
        else:
            self.metrics['failed_requests'] += 1

        # Update average response time
        total_time = self.metrics['average_response_time'] * (self.metrics['total_requests'] - 1)
        self.metrics['average_response_time'] = (total_time + response_time) / self.metrics['total_requests']
```

## 🧪 Testing

### **1. Unit Tests**

```python
# tests/test_web_research.py
import pytest
from coding_swarm_agents.web_research_agent import WebResearchAgent, SafeWebClient

def test_domain_whitelisting():
    config = {'allowed_domains': ['docs.npmjs.com', 'reactjs.org']}
    client = SafeWebClient(config)

    assert client.is_domain_allowed('https://docs.npmjs.com/package/react')
    assert not client.is_domain_allowed('https://malicious-site.com')

def test_content_filtering():
    config = {'max_content_length': 100, 'allowed_content_types': ['text/html']}
    filter = ContentFilter(config)

    # Test content length limiting
    long_content = 'x' * 200
    filtered = filter.filter_content(long_content, 'text/html')
    assert len(filtered) <= 100 + len('...[truncated]')
```

### **2. Integration Tests**

```python
# tests/test_web_research_integration.py
import pytest
import httpx
from coding_swarm_agents.web_research_agent import WebResearchAgent

@pytest.mark.asyncio
async def test_documentation_lookup():
    agent = WebResearchAgent({'project': '.', 'goal': 'test'})

    result = await agent.lookup_documentation('React hooks', 'react')

    assert isinstance(result, str)
    assert len(result) > 0
    assert 'hook' in result.lower() or 'react' in result.lower()

@pytest.mark.asyncio
async def test_package_info():
    agent = WebResearchAgent({'project': '.', 'goal': 'test'})

    info = await agent.get_package_info('react', 'npm')

    assert 'name' in info or 'version' in info
```

### **3. Security Tests**

```python
# tests/test_web_research_security.py
def test_rate_limiting():
    limiter = RateLimiter(requests_per_minute=5)

    # Should allow initial requests
    for _ in range(5):
        assert limiter.is_allowed()

    # Should deny additional requests
    assert not limiter.is_allowed()

def test_content_sanitization():
    filter = ContentFilter({'max_content_length': 1000})

    malicious_html = '<script>alert("xss")</script><p>Safe content</p>'
    sanitized = filter.filter_content(malicious_html, 'text/html')

    assert '<script>' not in sanitized
    assert 'Safe content' in sanitized
```

## 🚀 Deployment

### **1. Development Setup**

```bash
# Clone and setup
git clone https://github.com/your-org/coding-swarm.git
cd coding-swarm

# Install dependencies
pip install -e packages/agents/
pip install httpx aiohttp

# Start web research service
docker-compose -f docker-compose.web.yml up -d

# Test integration
python3 -c "
from coding_swarm_agents import create_agent
agent = create_agent('web_research', {'project': '.'})
print('Web research agent created successfully')
"
```

### **2. Production Deployment**

```bash
# Build production images
docker build -t sanaa-web-research:latest -f Dockerfile.web .

# Deploy with orchestration
docker-compose -f docker-compose.prod.yml up -d

# Configure reverse proxy
nginx -c /etc/nginx/sites-enabled/sanaa.conf

# Set up monitoring
docker run -d --name sanaa-monitor \
  -v /var/log/sanaa:/logs \
  monitoring-tool:latest
```

### **3. Configuration Management**

```bash
# Environment variables
export WEB_RESEARCH_ENABLED=true
export ALLOWED_DOMAINS="docs.npmjs.com,reactjs.org,laravel.com"
export REQUESTS_PER_MINUTE=10
export MAX_CONTENT_LENGTH=50000

# Configuration file
cp web_research_config.json ~/.sanaa/
# Edit as needed for your environment
```

## 📈 Performance Optimization

### **1. Caching Strategy**

```python
class DocumentationCache:
    def __init__(self, cache_dir: str, ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Optional[str]:
        """Get cached content with TTL check"""
        cache_file = self.cache_dir / f"{hash(key)}.json"

        if not cache_file.exists():
            return None

        data = json.loads(cache_file.read_text())
        if time.time() - data['timestamp'] > self.ttl:
            cache_file.unlink()
            return None

        return data['content']

    def set(self, key: str, content: str):
        """Cache content with timestamp"""
        cache_file = self.cache_dir / f"{hash(key)}.json"

        data = {
            'timestamp': time.time(),
            'content': content,
            'key': key
        }

        cache_file.write_text(json.dumps(data))
```

### **2. Connection Pooling**

```python
class ConnectionPool:
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.clients = []

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if len(self.clients) < self.max_connections:
            client = httpx.AsyncClient(
                timeout=10,
                limits=httpx.Limits(max_connections=5)
            )
            self.clients.append(client)
            return client

        # Reuse existing client
        return self.clients[0]
```

### **3. Background Processing**

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class BackgroundProcessor:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.loop = asyncio.get_event_loop()

    async def process_research_request(self, query: str, framework: str):
        """Process research request in background"""
        return await self.loop.run_in_executor(
            self.executor,
            self._sync_research,
            query,
            framework
        )

    def _sync_research(self, query: str, framework: str) -> str:
        """Synchronous research processing"""
        # Perform research operations
        return f"Research results for {query} in {framework}"
```

## 🎯 Use Cases & Examples

### **1. Real-time Documentation**

```python
# During coding session
user: "How do I use React's useEffect hook?"
agent: "Let me look that up for you..."

# Agent performs web research
result = await agent.lookup_documentation("useEffect hook", "react")

# Returns formatted documentation
"""
## useEffect Hook

The `useEffect` hook lets you perform side effects in function components.

### Basic Usage
```javascript
useEffect(() => {
  // Side effect code here
  return () => {
    // Cleanup function
  };
}, [dependencies]);
```

### When to Use
- Data fetching
- DOM manipulation
- Setting up subscriptions
- Timer management
"""
```

### **2. Package Research**

```python
# Package compatibility check
user: "Is react-router-dom compatible with React 18?"
agent: "Checking package compatibility..."

info = await agent.get_package_info("react-router-dom", "npm")
compatibility = await agent.lookup_documentation("react 18 compatibility", "react")
```

### **3. Troubleshooting**

```python
# Error resolution
user: "Getting 'Cannot read property 'map' of undefined' in React"
agent: "Searching for solutions..."

solutions = await agent.get_troubleshooting_info(
    "Cannot read property 'map' of undefined",
    "react"
)
```

### **4. Best Practices**

```python
# Code improvement suggestions
user: "How should I structure my React components?"
agent: "Looking up React best practices..."

practices = await agent.get_best_practices("component structure", "react")
```

## 🔄 Integration with Existing Systems

### **1. LLM Integration**

```python
# Enhanced LLM responses with web research
async def enhanced_llm_response(user_query: str, context: Dict) -> str:
    """Generate LLM response with web research augmentation"""

    # First, try to answer from existing knowledge
    base_response = await generate_llm_response(user_query, context)

    # If confidence is low, perform web research
    if needs_research(base_response):
        research_results = await web_research_agent.lookup_documentation(
            user_query,
            context.get('framework', 'general')
        )

        # Combine responses
        enhanced_response = await combine_responses(base_response, research_results)

        return enhanced_response

    return base_response
```

### **2. Project Context Enhancement**

```python
# Enhance project context with external information
async def enhance_project_context(project: Project) -> Dict:
    """Enhance project context with web research"""

    framework = detect_framework(project)

    # Get latest framework updates
    updates = await web_research_agent.lookup_documentation(
        f"{framework} latest updates",
        framework
    )

    # Get relevant best practices
    practices = await web_research_agent.get_best_practices(
        "project structure",
        framework
    )

    return {
        'framework_updates': updates,
        'best_practices': practices,
        'external_resources': await get_relevant_resources(project, framework)
    }
```

## 📊 Metrics & Analytics

### **1. Usage Tracking**

```python
class UsageAnalytics:
    def __init__(self):
        self.metrics = {
            'total_queries': 0,
            'successful_researches': 0,
            'failed_researches': 0,
            'average_response_time': 0,
            'popular_frameworks': {},
            'popular_queries': {}
        }

    def track_research(self, query: str, framework: str, success: bool, response_time: float):
        """Track research usage"""
        self.metrics['total_queries'] += 1

        if success:
            self.metrics['successful_researches'] += 1
        else:
            self.metrics['failed_researches'] += 1

        # Update averages
        total_time = self.metrics['average_response_time'] * (self.metrics['total_queries'] - 1)
        self.metrics['average_response_time'] = (total_time + response_time) / self.metrics['total_queries']

        # Track popular items
        self.metrics['popular_frameworks'][framework] = self.metrics['popular_frameworks'].get(framework, 0) + 1
        self.metrics['popular_queries'][query] = self.metrics['popular_queries'].get(query, 0) + 1
```

### **2. Performance Dashboard**

```python
def generate_performance_report(analytics: UsageAnalytics) -> str:
    """Generate performance report"""

    success_rate = (analytics.metrics['successful_researches'] /
                   analytics.metrics['total_queries']) * 100

    report = f"""
Web Research Performance Report
===============================

Total Queries: {analytics.metrics['total_queries']}
Success Rate: {success_rate:.1f}%
Average Response Time: {analytics.metrics['average_response_time']:.2f}s

Popular Frameworks:
{chr(10).join(f"- {fw}: {count}" for fw, count in analytics.metrics['popular_frameworks'].items())}

Popular Queries:
{chr(10).join(f"- {query}: {count}" for query, count in list(analytics.metrics['popular_queries'].items())[:10])}
"""

    return report
```

## 🎉 Conclusion

The Web Research Agent integration provides Sanaa Projects with powerful capabilities to access external resources safely and securely. The implementation includes:

- ✅ **Secure web access** with domain whitelisting and content filtering
- ✅ **Rate limiting and DDoS protection** to prevent abuse
- ✅ **Caching system** for performance optimization
- ✅ **Docker containerization** for isolation and security
- ✅ **Comprehensive monitoring** and analytics
- ✅ **Easy integration** with existing Sanaa Projects architecture

This enhancement significantly improves the AI agents' ability to provide accurate, up-to-date information while maintaining enterprise-grade security and performance standards.

**Ready to enhance your Sanaa Projects with web research capabilities! 🚀**