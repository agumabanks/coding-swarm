"""
Enhanced API Framework for Sanaa
Provides scalable API with real-time processing, caching, and load balancing
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import redis.asyncio as redis
from fastapi import Request, Response, HTTPException, WebSocket
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import aiohttp
from aiohttp import ClientTimeout


@dataclass
class APIRequest:
    """API request representation"""
    id: str
    method: str
    path: str
    headers: Dict[str, str]
    body: Optional[str]
    timestamp: datetime
    client_ip: str
    user_agent: str


@dataclass
class APIMetrics:
    """API performance metrics"""
    request_count: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    throughput: float = 0.0
    active_connections: int = 0


class LoadBalancer:
    """Load balancer for API requests"""

    def __init__(self, backend_urls: List[str]):
        self.backend_urls = backend_urls
        self.current_index = 0
        self.health_checks: Dict[str, bool] = {}
        self.session = aiohttp.ClientSession(timeout=ClientTimeout(total=30))

    async def get_backend_url(self) -> str:
        """Get next healthy backend URL using round-robin"""
        healthy_backends = [url for url in self.backend_urls if self.health_checks.get(url, True)]

        if not healthy_backends:
            raise HTTPException(status_code=503, detail="No healthy backends available")

        # Round-robin selection
        backend_url = healthy_backends[self.current_index % len(healthy_backends)]
        self.current_index += 1

        return backend_url

    async def forward_request(self, request: Request) -> Response:
        """Forward request to backend"""
        backend_url = await self.get_backend_url()

        # Prepare request data
        method = request.method
        url = f"{backend_url}{request.url.path}"
        headers = dict(request.headers)
        body = await request.body()

        # Remove hop-by-hop headers
        hop_by_hop_headers = [
            'connection', 'keep-alive', 'proxy-authenticate',
            'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade'
        ]
        for header in hop_by_hop_headers:
            headers.pop(header, None)

        try:
            async with self.session.request(method, url, headers=headers, data=body) as response:
                response_body = await response.read()
                return Response(
                    content=response_body,
                    status_code=response.status,
                    headers=dict(response.headers)
                )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Backend error: {str(e)}")

    async def health_check(self):
        """Perform health checks on all backends"""
        for url in self.backend_urls:
            try:
                async with self.session.get(f"{url}/health", timeout=ClientTimeout(total=5)) as response:
                    self.health_checks[url] = response.status == 200
            except:
                self.health_checks[url] = False

    async def close(self):
        """Close the session"""
        await self.session.close()


class RedisCache:
    """Redis-based caching layer"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        self.redis = redis.from_url(self.redis_url)

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.redis:
            return None
        return await self.redis.get(key)

    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        """Set value in cache with TTL"""
        if not self.redis:
            return False
        return await self.redis.setex(key, ttl, value)

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if not self.redis:
            return False
        return await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis:
            return False
        return await self.redis.exists(key)

    def generate_cache_key(self, request: Request) -> str:
        """Generate cache key from request"""
        path = request.url.path
        query = str(request.query_params)
        body = ""

        # Include body in cache key for POST/PUT requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            # Note: In production, you'd want to hash the body
            body = "body_included"

        return f"{request.method}:{path}:{query}:{body}"


class RateLimiter:
    """Rate limiting implementation"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.limits: Dict[str, Dict[str, Any]] = {
            'default': {'requests': 100, 'window': 60},  # 100 requests per minute
            'api': {'requests': 1000, 'window': 60},     # 1000 requests per minute
            'agent': {'requests': 50, 'window': 60},     # 50 requests per minute
        }

    async def connect(self):
        """Connect to Redis"""
        self.redis = redis.from_url(self.redis_url)

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()

    async def is_allowed(self, client_id: str, endpoint_type: str = 'default') -> bool:
        """Check if request is allowed under rate limit"""
        if not self.redis:
            return True  # Allow if Redis is not available

        limit = self.limits.get(endpoint_type, self.limits['default'])
        key = f"ratelimit:{client_id}:{endpoint_type}"

        # Use Redis sorted set to track requests
        now = time.time()
        window_start = now - limit['window']

        # Remove old requests outside the window
        await self.redis.zremrangebyscore(key, '-inf', window_start)

        # Count current requests in window
        current_count = await self.redis.zcount(key, window_start, '+inf')

        if current_count >= limit['requests']:
            return False

        # Add current request
        await self.redis.zadd(key, {str(now): now})

        # Set expiration on the key
        await self.redis.expire(key, limit['window'])

        return True

    async def get_remaining_requests(self, client_id: str, endpoint_type: str = 'default') -> int:
        """Get remaining requests for client"""
        if not self.redis:
            return 999

        limit = self.limits.get(endpoint_type, self.limits['default'])
        key = f"ratelimit:{client_id}:{endpoint_type}"

        now = time.time()
        window_start = now - limit['window']

        current_count = await self.redis.zcount(key, window_start, '+inf')
        return max(0, limit['requests'] - current_count)


class RealTimeStreamProcessor:
    """Real-time stream processing for WebSocket connections"""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.connection_groups: Dict[str, List[str]] = defaultdict(list)
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self.processors: Dict[str, Callable] = {}

    async def add_connection(self, client_id: str, websocket: WebSocket, groups: List[str] = None):
        """Add WebSocket connection"""
        self.connections[client_id] = websocket
        self.message_queues[client_id] = asyncio.Queue()

        if groups:
            for group in groups:
                self.connection_groups[group].append(client_id)

        # Start message processing for this connection
        asyncio.create_task(self._process_messages(client_id))

    async def remove_connection(self, client_id: str):
        """Remove WebSocket connection"""
        if client_id in self.connections:
            del self.connections[client_id]

        if client_id in self.message_queues:
            del self.message_queues[client_id]

        # Remove from groups
        for group, clients in self.connection_groups.items():
            if client_id in clients:
                clients.remove(client_id)

    async def send_to_client(self, client_id: str, message: Dict[str, Any]):
        """Send message to specific client"""
        if client_id in self.message_queues:
            await self.message_queues[client_id].put(message)

    async def broadcast_to_group(self, group: str, message: Dict[str, Any]):
        """Broadcast message to all clients in a group"""
        if group in self.connection_groups:
            for client_id in self.connection_groups[group]:
                await self.send_to_client(client_id, message)

    async def broadcast_all(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        for client_id in self.message_queues:
            await self.send_to_client(client_id, message)

    async def _process_messages(self, client_id: str):
        """Process messages for a specific client"""
        try:
            while client_id in self.connections:
                websocket = self.connections[client_id]
                queue = self.message_queues[client_id]

                # Wait for message with timeout
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=1.0)
                    await websocket.send_json(message)
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    if client_id in self.connections:
                        await websocket.send_json({"type": "ping", "timestamp": time.time()})

        except Exception as e:
            print(f"Error processing messages for {client_id}: {e}")
        finally:
            await self.remove_connection(client_id)

    def register_processor(self, event_type: str, processor: Callable):
        """Register message processor for specific event type"""
        self.processors[event_type] = processor

    async def process_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process event using registered processor"""
        if event_type in self.processors:
            return await self.processors[event_type](data)
        return data


class MetricsCollector:
    """API metrics collection and analysis"""

    def __init__(self):
        self.metrics: Dict[str, APIMetrics] = defaultdict(APIMetrics)
        self.request_times: Dict[str, List[float]] = defaultdict(list)
        self.endpoint_metrics: Dict[str, Dict[str, Any]] = {}

    def record_request(self, endpoint: str, response_time: float, status_code: int):
        """Record API request metrics"""
        metrics = self.metrics[endpoint]
        metrics.request_count += 1

        if status_code >= 400:
            metrics.error_count += 1

        # Update response times
        self.request_times[endpoint].append(response_time)
        if len(self.request_times[endpoint]) > 1000:  # Keep last 1000 requests
            self.request_times[endpoint] = self.request_times[endpoint][-1000:]

        # Calculate averages
        times = self.request_times[endpoint]
        if times:
            metrics.avg_response_time = sum(times) / len(times)
            sorted_times = sorted(times)
            metrics.p95_response_time = sorted_times[int(len(sorted_times) * 0.95)]
            metrics.p99_response_time = sorted_times[int(len(sorted_times) * 0.99)]

    def get_endpoint_metrics(self, endpoint: str) -> APIMetrics:
        """Get metrics for specific endpoint"""
        return self.metrics[endpoint]

    def get_all_metrics(self) -> Dict[str, APIMetrics]:
        """Get all endpoint metrics"""
        return dict(self.metrics)

    def calculate_throughput(self, endpoint: str, time_window: int = 60) -> float:
        """Calculate requests per second for endpoint"""
        if endpoint not in self.request_times:
            return 0.0

        # Count requests in the last time_window seconds
        now = time.time()
        recent_requests = [t for t in self.request_times[endpoint] if now - t <= time_window]

        return len(recent_requests) / time_window if time_window > 0 else 0.0


class EnhancedAPIMiddleware(BaseHTTPMiddleware):
    """Enhanced API middleware for monitoring and processing"""

    def __init__(self, app, metrics_collector: MetricsCollector):
        super().__init__(app)
        self.metrics_collector = metrics_collector

    async def dispatch(self, request: Request, call_next):
        """Process request and collect metrics"""
        start_time = time.time()

        # Extract request info
        endpoint = f"{request.method} {request.url.path}"
        client_ip = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Handle exceptions
            status_code = 500
            response = JSONResponse(
                status_code=500,
                content={"error": "Internal server error"}
            )

        # Record metrics
        response_time = time.time() - start_time
        self.metrics_collector.record_request(endpoint, response_time, status_code)

        # Add custom headers
        response.headers["X-Response-Time"] = f"{response_time:.3f}s"
        response.headers["X-API-Version"] = "2.0"

        return response


class EnhancedAPI:
    """Enhanced API with all scalability features"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.load_balancer = None
        self.cache = RedisCache(redis_url)
        self.rate_limiter = RateLimiter(redis_url)
        self.stream_processor = RealTimeStreamProcessor()
        self.metrics_collector = MetricsCollector()
        self.middleware = EnhancedAPIMiddleware(None, self.metrics_collector)

    async def initialize(self, backend_urls: List[str] = None):
        """Initialize all components"""
        await self.cache.connect()
        await self.rate_limiter.connect()

        if backend_urls:
            self.load_balancer = LoadBalancer(backend_urls)
            # Start health check loop
            asyncio.create_task(self._health_check_loop())

    async def shutdown(self):
        """Shutdown all components"""
        await self.cache.disconnect()
        await self.rate_limiter.disconnect()

        if self.load_balancer:
            await self.load_balancer.close()

    async def handle_request(self, request: Request) -> Response:
        """Handle API request with all enhancements"""
        client_id = self._get_client_id(request)
        endpoint_type = self._classify_endpoint(request.url.path)

        # Rate limiting check
        if not await self.rate_limiter.is_allowed(client_id, endpoint_type):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"}
            )

        # Cache check for GET requests
        if request.method == "GET":
            cache_key = self.cache.generate_cache_key(request)
            cached_response = await self.cache.get(cache_key)
            if cached_response:
                return Response(content=cached_response, media_type="application/json")

        # Forward to load balancer or handle locally
        if self.load_balancer:
            response = await self.load_balancer.forward_request(request)
        else:
            # Local handling would go here
            response = JSONResponse(content={"message": "Request processed"})

        # Cache successful GET responses
        if request.method == "GET" and response.status_code == 200:
            cache_key = self.cache.generate_cache_key(request)
            await self.cache.set(cache_key, response.body.decode())

        return response

    async def add_websocket_connection(self, client_id: str, websocket: WebSocket, groups: List[str] = None):
        """Add WebSocket connection for real-time communication"""
        await self.stream_processor.add_connection(client_id, websocket, groups)

    async def broadcast_event(self, event_type: str, data: Dict[str, Any], group: str = None):
        """Broadcast event to clients"""
        event_data = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }

        if group:
            await self.stream_processor.broadcast_to_group(group, event_data)
        else:
            await self.stream_processor.broadcast_all(event_data)

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive API metrics"""
        return {
            "endpoints": self.metrics_collector.get_all_metrics(),
            "connections": len(self.stream_processor.connections),
            "cache_stats": {},  # Would implement cache statistics
            "rate_limits": {}   # Would implement rate limit statistics
        }

    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request"""
        # Use IP address as client ID (in production, use API key or JWT)
        return request.client.host if request.client else "anonymous"

    def _classify_endpoint(self, path: str) -> str:
        """Classify endpoint type for rate limiting"""
        if path.startswith("/api/agent"):
            return "agent"
        elif path.startswith("/api"):
            return "api"
        else:
            return "default"

    async def _health_check_loop(self):
        """Periodic health check loop"""
        while True:
            if self.load_balancer:
                await self.load_balancer.health_check()
            await asyncio.sleep(30)  # Check every 30 seconds


# Global enhanced API instance
enhanced_api = EnhancedAPI()


def get_enhanced_api() -> EnhancedAPI:
    """Get global enhanced API instance"""
    return enhanced_api