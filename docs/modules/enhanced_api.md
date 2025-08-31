# Enhanced API Module Documentation

## Overview

The Enhanced API Module (`packages/core/src/coding_swarm_core/enhanced_api.py`) provides advanced API capabilities for the Sanaa system, including load balancing, caching, rate limiting, and real-time streaming.

## Features

### 1. Load Balancer
- **Intelligent backend distribution** using round-robin and health checks
- **Automatic failover** to healthy backends
- **Dynamic backend management** with configuration support
- **Health monitoring** with configurable intervals

### 2. Redis Cache
- **High-performance caching** with TTL support
- **Cache key generation** from request parameters
- **Cache invalidation** strategies
- **Connection pooling** for Redis efficiency

### 3. Rate Limiter
- **Configurable rate limits** per endpoint and user
- **Sliding window algorithm** for accurate rate limiting
- **Redis-backed storage** for distributed rate limiting
- **Burst handling** with configurable burst allowances

### 4. Real-time Stream Processor
- **WebSocket connection management** with automatic cleanup
- **Group-based messaging** for targeted broadcasts
- **Message queuing** with async processing
- **Connection pooling** for scalability

### 5. Metrics Collector
- **Comprehensive API metrics** collection
- **Performance monitoring** with latency tracking
- **Error rate analysis** and success rate tracking
- **Throughput measurement** and capacity planning

## API Reference

### LoadBalancer

```python
from coding_swarm_core.enhanced_api import LoadBalancer

# Initialize load balancer
backends = ["http://api1.sanaa.dev", "http://api2.sanaa.dev", "http://api3.sanaa.dev"]
lb = LoadBalancer(backends)

# Get healthy backend
backend_url = await lb.get_backend_url()

# Forward request
response = await lb.forward_request(request)

# Check health
await lb.health_check()

# Close connections
await lb.close()
```

### RedisCache

```python
from coding_swarm_core.enhanced_api import RedisCache

# Initialize cache
cache = RedisCache(redis_url="redis://localhost:6379")

# Connect to Redis
await cache.connect()

# Cache operations
await cache.set("key", "value", ttl=300)
value = await cache.get("key")
exists = await cache.exists("key")
await cache.delete("key")

# Generate cache key from request
cache_key = cache.generate_cache_key(request)

# Disconnect
await cache.disconnect()
```

### RateLimiter

```python
from coding_swarm_core.enhanced_api import RateLimiter

# Initialize rate limiter
limiter = RateLimiter(redis_url="redis://localhost:6379")

# Connect to Redis
await limiter.connect()

# Check rate limit
client_id = "user123"
allowed = await limiter.is_allowed(client_id, endpoint_type="api")

# Get remaining requests
remaining = await limiter.get_remaining_requests(client_id, endpoint_type="api")

# Disconnect
await limiter.disconnect()
```

### RealTimeStreamProcessor

```python
from coding_swarm_core.enhanced_api import RealTimeStreamProcessor

# Initialize stream processor
processor = RealTimeStreamProcessor()

# Add WebSocket connection
await processor.add_connection(client_id, websocket, groups=["project:123"])

# Send message to client
await processor.send_to_client(client_id, {"type": "update", "data": {...}})

# Broadcast to group
await processor.broadcast_to_group("project:123", {"type": "notification", "message": "..."})

# Broadcast to all
await processor.broadcast_all({"type": "system", "message": "System update"})

# Register message processor
async def handle_update(data):
    # Process update message
    pass

processor.register_processor("update", handle_update)

# Remove connection
await processor.remove_connection(client_id)
```

### EnhancedAPI

```python
from coding_swarm_core.enhanced_api import EnhancedAPI

# Initialize enhanced API
api = EnhancedAPI(redis_url="redis://localhost:6379")

# Initialize components
await api.initialize(backend_urls=["http://api1.sanaa.dev", "http://api2.sanaa.dev"])

# Handle request with all enhancements
response = await api.handle_request(request)

# Add WebSocket connection
await api.add_websocket_connection(client_id, websocket, groups=["project:123"])

# Broadcast event
await api.broadcast_event("task_completed", {"task_id": "123", "status": "success"})

# Get metrics
metrics = api.get_metrics()

# Shutdown
await api.shutdown()
```

## Configuration

### Environment Variables

- `REDIS_URL`: Redis connection URL (default: redis://localhost:6379)
- `API_LOAD_BALANCER_BACKENDS`: Comma-separated backend URLs
- `API_RATE_LIMIT_DEFAULT`: Default requests per window (default: 100)
- `API_RATE_LIMIT_WINDOW`: Rate limit window in seconds (default: 60)
- `API_CACHE_TTL`: Default cache TTL in seconds (default: 300)

### Rate Limit Configuration

```python
# Configure rate limits
limiter.limits = {
    'default': {'requests': 100, 'window': 60},
    'api': {'requests': 1000, 'window': 60},
    'agent': {'requests': 50, 'window': 60}
}
```

### Cache Configuration

```python
# Configure cache settings
cache.ttl = 300  # 5 minutes default TTL
cache.max_connections = 10  # Redis connection pool size
```

## Dependencies

- `aiohttp>=3.8.0`: For HTTP client operations and load balancing
- `redis>=4.2.0`: For caching and rate limiting (async version)
- `fastapi`: For API framework integration
- `uvicorn`: For ASGI server support

## Integration Points

### With Other Modules
- **Security Module**: Authentication and authorization integration
- **Performance Monitor**: API metrics and health monitoring
- **User Interfaces**: WebSocket real-time updates
- **Advanced Debugging**: API request tracing and debugging

### External Systems
- **Redis Cluster**: For distributed caching and rate limiting
- **Load Balancers**: Nginx, HAProxy, AWS ALB integration
- **Monitoring Systems**: Prometheus metrics export
- **CDN**: Cache integration with CDN providers

## Performance Optimization

### Caching Strategies
1. **HTTP Response Caching**: Cache GET responses based on URL and parameters
2. **Database Query Caching**: Cache expensive database queries
3. **Computed Result Caching**: Cache results of expensive computations
4. **Session Data Caching**: Cache user session and authentication data

### Rate Limiting Strategies
1. **User-Based Limiting**: Per-user rate limits for fairness
2. **Endpoint-Based Limiting**: Different limits for different API endpoints
3. **IP-Based Limiting**: Rate limiting by client IP address
4. **Burst Handling**: Allow short bursts above normal limits

### Load Balancing Strategies
1. **Round-Robin**: Simple distribution across backends
2. **Least Connections**: Route to backend with fewest active connections
3. **IP Hashing**: Consistent routing based on client IP
4. **Health-Based**: Only route to healthy backends

## Error Handling

The enhanced API module provides comprehensive error handling:

- **BackendError**: Backend service failures
- **CacheError**: Redis/cache operation failures
- **RateLimitError**: Rate limit exceeded
- **WebSocketError**: WebSocket connection errors
- **LoadBalancerError**: Load balancing failures

## Monitoring and Metrics

### API Metrics
- Request count and rate
- Response time percentiles (P50, P95, P99)
- Error rates by endpoint
- Cache hit/miss ratios
- Rate limit violations
- WebSocket connection counts

### Health Checks
- Backend health status
- Redis connectivity
- Memory usage
- CPU utilization
- Network connectivity

## Security Considerations

### Authentication
- JWT token validation
- API key authentication
- OAuth2 integration support
- Session management

### Authorization
- Role-based access control
- Endpoint-level permissions
- Request rate limiting
- IP whitelisting/blacklisting

### Data Protection
- HTTPS enforcement
- Request/response encryption
- Sensitive data masking in logs
- CORS configuration

## Best Practices

### API Design
1. **RESTful Design**: Follow REST principles for API endpoints
2. **Versioning**: Use API versioning for backward compatibility
3. **Documentation**: Maintain up-to-date API documentation
4. **Error Handling**: Provide consistent error responses

### Performance
1. **Caching**: Implement appropriate caching strategies
2. **Rate Limiting**: Protect against abuse and ensure fairness
3. **Load Balancing**: Distribute load across multiple backends
4. **Monitoring**: Monitor API performance and health

### Scalability
1. **Horizontal Scaling**: Design for multiple backend instances
2. **Connection Pooling**: Use connection pools for efficiency
3. **Async Processing**: Use async/await for non-blocking operations
4. **Resource Limits**: Implement resource limits and quotas

## Troubleshooting

### Common Issues

1. **High Latency**
   - Solution: Check cache hit rates and backend performance
   - Solution: Review load balancer distribution

2. **Rate Limit Errors**
   - Solution: Adjust rate limit configurations
   - Solution: Implement request queuing or backoff

3. **WebSocket Disconnections**
   - Solution: Check network connectivity and firewall settings
   - Solution: Implement reconnection logic

4. **Cache Invalidation Issues**
   - Solution: Review cache key generation logic
   - Solution: Implement cache warming strategies

### Debug Mode

Enable detailed API logging:
```python
import logging
logging.getLogger('sanaa.api').setLevel(logging.DEBUG)
```

## Examples

### Complete API Setup

```python
from coding_swarm_core.enhanced_api import EnhancedAPI
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

# Initialize FastAPI app
app = FastAPI()

# Initialize enhanced API
enhanced_api = EnhancedAPI(redis_url="redis://localhost:6379")
await enhanced_api.initialize([
    "http://api1.sanaa.dev:8000",
    "http://api2.sanaa.dev:8000"
])

# Add middleware
app.add_middleware(EnhancedAPIMiddleware, metrics_collector=enhanced_api.metrics_collector)

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def api_proxy(request: Request, path: str):
    """Proxy all requests through enhanced API"""
    return await enhanced_api.handle_request(request)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket, client_id: str):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    await enhanced_api.add_websocket_connection(client_id, websocket)

# Start server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

### Real-time Collaboration Example

```python
from coding_swarm_core.enhanced_api import EnhancedAPI

# Initialize API
api = EnhancedAPI()
await api.initialize()

# Broadcast real-time updates
async def on_task_completion(task_id: str, result: dict):
    await api.broadcast_event(
        "task_completed",
        {
            "task_id": task_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        },
        group=f"project:{result.get('project_id')}"
    )

# Handle incoming messages
async def handle_collaboration_message(data: dict):
    message_type = data.get("type")

    if message_type == "cursor_update":
        # Broadcast cursor position to other users
        await api.broadcast_event(
            "cursor_moved",
            {
                "user_id": data["user_id"],
                "position": data["position"],
                "file": data["file"]
            },
            group=f"file:{data['file']}"
        )

    elif message_type == "text_change":
        # Broadcast text changes for collaborative editing
        await api.broadcast_event(
            "text_changed",
            {
                "user_id": data["user_id"],
                "changes": data["changes"],
                "file": data["file"]
            },
            group=f"file:{data['file']}"
        )

# Register message handlers
api.stream_processor.register_processor("collaboration", handle_collaboration_message)
```

This module provides enterprise-grade API capabilities with advanced features for scalability, performance, and real-time communication, making it suitable for high-traffic applications and collaborative environments.