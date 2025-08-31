"""
Advanced Memory Handling and Optimization for Sanaa
Provides efficient resource management, garbage collection improvements, and memory profiling tools
"""
from __future__ import annotations

import gc
import weakref
import threading
import time
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import tracemalloc
import psutil
import os
import sys
from contextlib import contextmanager


@dataclass
class MemorySnapshot:
    """Memory usage snapshot"""
    timestamp: datetime
    process_memory: int  # bytes
    system_memory: int   # bytes
    memory_percent: float
    top_allocations: List[Dict[str, Any]] = field(default_factory=list)
    gc_stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryPool:
    """Memory pool for efficient object reuse"""
    pool: Dict[str, deque] = field(default_factory=lambda: defaultdict(deque))
    max_size: int = 1000
    stats: Dict[str, int] = field(default_factory=dict)

    def get(self, obj_type: str) -> Optional[Any]:
        """Get object from pool"""
        if obj_type in self.pool and self.pool[obj_type]:
            self.stats[obj_type] = self.stats.get(obj_type, 0) + 1
            return self.pool[obj_type].popleft()
        return None

    def put(self, obj_type: str, obj: Any):
        """Return object to pool"""
        if len(self.pool[obj_type]) < self.max_size:
            self.pool[obj_type].append(obj)

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            'total_objects': sum(len(pool) for pool in self.pool.values()),
            'pool_sizes': {k: len(v) for k, v in self.pool.items()},
            'usage_stats': self.stats.copy()
        }


@dataclass
class WeakReferenceCache:
    """Cache with weak references to prevent memory leaks"""
    cache: weakref.WeakValueDictionary = field(default_factory=weakref.WeakValueDictionary)
    access_times: Dict[str, datetime] = field(default_factory=dict)
    max_age: timedelta = timedelta(hours=1)

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        if key in self.cache:
            self.access_times[key] = datetime.utcnow()
            return self.cache[key]
        return None

    def put(self, key: str, value: Any):
        """Put item in cache"""
        self.cache[key] = value
        self.access_times[key] = datetime.utcnow()

    def cleanup_expired(self):
        """Remove expired entries"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, access_time in self.access_times.items()
            if now - access_time > self.max_age
        ]
        for key in expired_keys:
            self.cache.pop(key, None)
            self.access_times.pop(key, None)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'size': len(self.cache),
            'oldest_access': min(self.access_times.values()) if self.access_times else None,
            'newest_access': max(self.access_times.values()) if self.access_times else None
        }


class MemoryProfiler:
    """Advanced memory profiling and analysis"""

    def __init__(self):
        self.snapshots: List[MemorySnapshot] = []
        self.tracemalloc_started = False
        self.monitoring_active = False
        self.snapshot_interval = 60  # seconds
        self.max_snapshots = 100

    def start_profiling(self):
        """Start memory profiling"""
        if not tracemalloc.is_tracing():
            tracemalloc.start()
            self.tracemalloc_started = True

        self.monitoring_active = True

    def stop_profiling(self):
        """Stop memory profiling"""
        self.monitoring_active = False
        if self.tracemalloc_started:
            tracemalloc.stop()
            self.tracemalloc_started = False

    def take_snapshot(self) -> MemorySnapshot:
        """Take a memory usage snapshot"""
        process = psutil.Process()
        memory_info = process.memory_info()

        snapshot = MemorySnapshot(
            timestamp=datetime.utcnow(),
            process_memory=memory_info.rss,
            system_memory=psutil.virtual_memory().used,
            memory_percent=process.memory_percent(),
            gc_stats=self._get_gc_stats()
        )

        # Get top memory allocations if tracemalloc is active
        if self.tracemalloc_started:
            snapshot.top_allocations = self._get_top_allocations()

        self.snapshots.append(snapshot)

        # Keep only recent snapshots
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots:]

        return snapshot

    def _get_top_allocations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top memory allocations"""
        try:
            stats = tracemalloc.take_snapshot()
            top_stats = stats.statistics('lineno')[:limit]

            return [
                {
                    'size': stat.size,
                    'count': stat.count,
                    'average': stat.size / stat.count if stat.count > 0 else 0,
                    'traceback': stat.traceback.format()[:3]  # First 3 frames
                }
                for stat in top_stats
            ]
        except Exception:
            return []

    def _get_gc_stats(self) -> Dict[str, Any]:
        """Get garbage collection statistics"""
        return {
            'collections': gc.get_count(),
            'objects': gc.get_stats(),
            'threshold': gc.get_threshold()
        }

    def analyze_memory_trends(self) -> Dict[str, Any]:
        """Analyze memory usage trends"""
        if len(self.snapshots) < 2:
            return {'error': 'Insufficient data for trend analysis'}

        memory_values = [s.process_memory for s in self.snapshots]
        timestamps = [s.timestamp for s in self.snapshots]

        # Calculate trends
        if len(memory_values) >= 2:
            memory_increase = memory_values[-1] - memory_values[0]
            time_span = (timestamps[-1] - timestamps[0]).total_seconds()
            memory_rate = memory_increase / time_span if time_span > 0 else 0

            # Detect memory leaks (sustained increase)
            recent_trend = self._calculate_recent_trend(memory_values, 10)

            return {
                'total_memory_increase': memory_increase,
                'memory_increase_rate': memory_rate,  # bytes per second
                'current_memory_usage': memory_values[-1],
                'peak_memory_usage': max(memory_values),
                'average_memory_usage': sum(memory_values) / len(memory_values),
                'memory_leak_detected': recent_trend > 1000,  # 1KB/s increase
                'trend_direction': 'increasing' if recent_trend > 0 else 'decreasing',
                'snapshot_count': len(self.snapshots)
            }

        return {'error': 'Unable to calculate trends'}

    def _calculate_recent_trend(self, values: List[int], window: int = 10) -> float:
        """Calculate recent trend in values"""
        if len(values) < window:
            window = len(values)

        recent = values[-window:]
        if len(recent) < 2:
            return 0

        # Simple linear regression slope
        n = len(recent)
        x = list(range(n))
        y = recent

        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_xx = sum(xi * xi for xi in x)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x) if (n * sum_xx - sum_x * sum_x) != 0 else 0

        return slope

    def get_memory_report(self) -> Dict[str, Any]:
        """Generate comprehensive memory report"""
        if not self.snapshots:
            return {'error': 'No memory snapshots available'}

        latest = self.snapshots[-1]
        trends = self.analyze_memory_trends()

        return {
            'current_memory': {
                'process_mb': latest.process_memory / 1024 / 1024,
                'system_mb': latest.system_memory / 1024 / 1024,
                'percentage': latest.memory_percent
            },
            'trends': trends,
            'gc_stats': latest.gc_stats,
            'top_allocations': latest.top_allocations,
            'snapshot_count': len(self.snapshots),
            'monitoring_active': self.monitoring_active,
            'recommendations': self._generate_memory_recommendations(trends)
        }

    def _generate_memory_recommendations(self, trends: Dict[str, Any]) -> List[str]:
        """Generate memory optimization recommendations"""
        recommendations = []

        if trends.get('memory_leak_detected', False):
            recommendations.append("Memory leak detected - review object lifecycle management")
            recommendations.append("Consider implementing weak references for cached objects")
            recommendations.append("Review circular references that may prevent garbage collection")

        memory_rate = trends.get('memory_increase_rate', 0)
        if memory_rate > 50000:  # 50KB/s
            recommendations.append("High memory allocation rate - consider object pooling")
            recommendations.append("Review frequent object creation patterns")

        current_mb = trends.get('current_memory_usage', 0) / 1024 / 1024
        if current_mb > 500:  # 500MB
            recommendations.append("High memory usage - consider memory optimization techniques")
            recommendations.append("Review large data structures and caching strategies")

        return recommendations


class GarbageCollectionOptimizer:
    """Advanced garbage collection optimization"""

    def __init__(self):
        self.gc_disabled = False
        self.custom_cleanup_callbacks: List[Callable] = []
        self.object_registry: weakref.WeakSet = weakref.WeakSet()

    def optimize_gc_settings(self):
        """Optimize garbage collection settings"""
        # Set more aggressive GC thresholds for better memory management
        gc.set_threshold(700, 10, 10)  # More frequent collections

        # Disable automatic GC if needed for performance-critical sections
        self.gc_disabled = False

    @contextmanager
    def disable_gc_temporarily(self):
        """Context manager to temporarily disable GC"""
        was_enabled = gc.isenabled()
        if was_enabled:
            gc.disable()
        try:
            yield
        finally:
            if was_enabled:
                gc.enable()
                # Force a collection after re-enabling
                gc.collect()

    def register_cleanup_callback(self, callback: Callable):
        """Register a cleanup callback"""
        self.custom_cleanup_callbacks.append(callback)

    def perform_optimized_collection(self, generation: int = 2) -> Dict[str, Any]:
        """Perform optimized garbage collection"""
        before = gc.get_count()
        before_stats = gc.get_stats()

        # Collect specific generation
        collected = gc.collect(generation)

        after = gc.get_count()
        after_stats = gc.get_stats()

        return {
            'collected_objects': collected,
            'collections_before': before,
            'collections_after': after,
            'stats_before': before_stats,
            'stats_after': after_stats,
            'efficiency': collected / max(before[generation], 1)
        }

    def cleanup_weak_references(self):
        """Clean up weak references"""
        # Force cleanup of weak references
        gc.collect()

        # Call custom cleanup callbacks
        for callback in self.custom_cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"Error in cleanup callback: {e}")

    def monitor_object_lifecycle(self, obj: Any, name: str = None):
        """Monitor object lifecycle using weak references"""
        def cleanup_callback(ref):
            print(f"Object {name or 'unknown'} was garbage collected")

        weak_ref = weakref.ref(obj, cleanup_callback)
        self.object_registry.add(weak_ref)

        return weak_ref


class ResourceManager:
    """Efficient resource management system"""

    def __init__(self):
        self.resources: Dict[str, Any] = {}
        self.resource_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self.resource_usage: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.cleanup_callbacks: Dict[str, List[Callable]] = defaultdict(list)

    @contextmanager
    def acquire_resource(self, resource_id: str, resource_type: str = 'generic'):
        """Context manager for resource acquisition"""
        lock = self.resource_locks[resource_id]

        with lock:
            start_time = time.time()
            try:
                resource = self._get_or_create_resource(resource_id, resource_type)
                self._record_usage(resource_id, 'acquire', start_time)

                yield resource

            finally:
                end_time = time.time()
                self._record_usage(resource_id, 'release', end_time)

                # Check if resource should be cleaned up
                if self._should_cleanup_resource(resource_id):
                    self._cleanup_resource(resource_id)

    def register_resource(self, resource_id: str, resource: Any, cleanup_callback: Optional[Callable] = None):
        """Register a resource for management"""
        self.resources[resource_id] = resource

        if cleanup_callback:
            self.cleanup_callbacks[resource_id].append(cleanup_callback)

    def unregister_resource(self, resource_id: str):
        """Unregister a resource"""
        if resource_id in self.resources:
            self._cleanup_resource(resource_id)
            del self.resources[resource_id]

    def get_resource_stats(self, resource_id: str = None) -> Dict[str, Any]:
        """Get resource usage statistics"""
        if resource_id:
            return self.resource_usage.get(resource_id, {})

        return dict(self.resource_usage)

    def _get_or_create_resource(self, resource_id: str, resource_type: str) -> Any:
        """Get existing resource or create new one"""
        if resource_id in self.resources:
            return self.resources[resource_id]

        # Create resource based on type (placeholder logic)
        if resource_type == 'database_connection':
            # Create DB connection
            resource = f"DB_Connection_{resource_id}"
        elif resource_type == 'file_handle':
            # Create file handle
            resource = f"File_Handle_{resource_id}"
        else:
            resource = f"Generic_Resource_{resource_id}"

        self.resources[resource_id] = resource
        return resource

    def _record_usage(self, resource_id: str, action: str, timestamp: float):
        """Record resource usage"""
        if resource_id not in self.resource_usage:
            self.resource_usage[resource_id] = {
                'acquire_count': 0,
                'release_count': 0,
                'total_acquire_time': 0,
                'total_release_time': 0,
                'last_acquired': None,
                'last_released': None
            }

        usage = self.resource_usage[resource_id]

        if action == 'acquire':
            usage['acquire_count'] += 1
            usage['last_acquired'] = timestamp
        elif action == 'release':
            usage['release_count'] += 1
            usage['last_released'] = timestamp

    def _should_cleanup_resource(self, resource_id: str) -> bool:
        """Determine if resource should be cleaned up"""
        usage = self.resource_usage.get(resource_id, {})
        acquire_count = usage.get('acquire_count', 0)
        release_count = usage.get('release_count', 0)

        # Cleanup if resource has been released more than acquired (indicates overuse)
        return release_count > acquire_count + 5

    def _cleanup_resource(self, resource_id: str):
        """Clean up a resource"""
        # Call cleanup callbacks
        for callback in self.cleanup_callbacks.get(resource_id, []):
            try:
                callback(self.resources[resource_id])
            except Exception as e:
                print(f"Error in cleanup callback for {resource_id}: {e}")

        # Remove from tracking
        if resource_id in self.resources:
            del self.resources[resource_id]


class MemoryOptimizer:
    """Main memory optimization coordinator"""

    def __init__(self):
        self.profiler = MemoryProfiler()
        self.gc_optimizer = GarbageCollectionOptimizer()
        self.resource_manager = ResourceManager()
        self.object_pool = MemoryPool()
        self.cache = WeakReferenceCache()
        self.monitoring_active = False

    def start_optimization(self):
        """Start memory optimization"""
        self.profiler.start_profiling()
        self.gc_optimizer.optimize_gc_settings()
        self.monitoring_active = True

        # Start background monitoring
        threading.Thread(target=self._background_monitoring, daemon=True).start()

    def stop_optimization(self):
        """Stop memory optimization"""
        self.monitoring_active = False
        self.profiler.stop_profiling()

    def optimize_memory_usage(self) -> Dict[str, Any]:
        """Perform comprehensive memory optimization"""
        results = {
            'gc_collection': self.gc_optimizer.perform_optimized_collection(),
            'memory_snapshot': self.profiler.take_snapshot(),
            'cache_cleanup': self._cleanup_cache(),
            'pool_stats': self.object_pool.get_stats(),
            'resource_stats': self.resource_manager.get_resource_stats()
        }

        # Force garbage collection
        gc.collect()

        return results

    def _cleanup_cache(self) -> Dict[str, Any]:
        """Clean up cache and return statistics"""
        before_size = len(self.cache.cache)
        self.cache.cleanup_expired()
        after_size = len(self.cache.cache)

        return {
            'cleaned_entries': before_size - after_size,
            'remaining_entries': after_size,
            'cache_stats': self.cache.get_stats()
        }

    def _background_monitoring(self):
        """Background memory monitoring"""
        while self.monitoring_active:
            try:
                # Take memory snapshot
                self.profiler.take_snapshot()

                # Periodic cleanup
                if time.time() % 300 < 1:  # Every 5 minutes
                    self.optimize_memory_usage()

                time.sleep(self.profiler.snapshot_interval)

            except Exception as e:
                print(f"Error in background monitoring: {e}")
                time.sleep(60)

    def get_memory_status(self) -> Dict[str, Any]:
        """Get comprehensive memory status"""
        return {
            'profiler_report': self.profiler.get_memory_report(),
            'gc_optimizer_status': {
                'gc_disabled': self.gc_optimizer.gc_disabled,
                'cleanup_callbacks': len(self.gc_optimizer.custom_cleanup_callbacks),
                'object_registry_size': len(self.gc_optimizer.object_registry)
            },
            'resource_manager_status': {
                'active_resources': len(self.resource_manager.resources),
                'resource_types': list(set(
                    usage.get('type', 'unknown')
                    for usage in self.resource_manager.resource_usage.values()
                ))
            },
            'object_pool_status': self.object_pool.get_stats(),
            'cache_status': self.cache.get_stats(),
            'system_memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'used': psutil.virtual_memory().used,
                'percentage': psutil.virtual_memory().percent
            }
        }


# Global memory optimizer instance
memory_optimizer = MemoryOptimizer()


def get_memory_optimizer() -> MemoryOptimizer:
    """Get global memory optimizer instance"""
    return memory_optimizer


# Utility functions for memory-efficient operations
def create_large_object_pool(obj_type: str, factory_func: Callable, pool_size: int = 100):
    """Create a pool for large objects to reduce allocation overhead"""
    pool = MemoryPool(max_size=pool_size)

    # Pre-populate pool
    for _ in range(pool_size // 2):
        obj = factory_func()
        pool.put(obj_type, obj)

    return pool


def monitor_function_memory(func: Callable):
    """Decorator to monitor memory usage of a function"""
    def wrapper(*args, **kwargs):
        process = psutil.Process()
        before_memory = process.memory_info().rss

        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()

        after_memory = process.memory_info().rss
        memory_delta = after_memory - before_memory

        print(f"Function {func.__name__}:")
        print(f"  Execution time: {end_time - start_time:.4f}s")
        print(f"  Memory delta: {memory_delta / 1024:.1f} KB")

        return result

    return wrapper


@contextmanager
def memory_efficient_context():
    """Context manager for memory-efficient operations"""
    # Disable GC temporarily
    gc_disabled = gc.isenabled()
    if gc_disabled:
        gc.disable()

    try:
        yield
    finally:
        if gc_disabled:
            gc.enable()
            # Force collection after re-enabling
            gc.collect()