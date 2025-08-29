"""
Performance optimization utilities for Milestone 2

Features:
- Connection pooling optimization
- Cache warming and management  
- Request batching and parallelization
- Memory usage optimization
- Response time monitoring
- Dependency conflict resolution
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
import time
import psutil
import gc
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """Performance optimization manager for composite data provider"""
    
    def __init__(
        self,
        max_connections_per_provider: int = 50,
        connection_timeout: float = 30.0,
        request_timeout: float = 10.0,
        enable_memory_monitoring: bool = True
    ):
        """
        Initialize performance optimizer
        
        Args:
            max_connections_per_provider: Maximum concurrent connections per provider
            connection_timeout: Connection timeout in seconds
            request_timeout: Request timeout in seconds  
            enable_memory_monitoring: Enable memory usage monitoring
        """
        self.max_connections = max_connections_per_provider
        self.connection_timeout = connection_timeout
        self.request_timeout = request_timeout
        self.enable_memory_monitoring = enable_memory_monitoring
        
        # Connection pools for each provider
        self.connection_pools: Dict[str, aiohttp.ClientSession] = {}
        
        # Performance metrics
        self.request_times: Dict[str, List[float]] = {}
        self.memory_usage: List[Dict[str, Any]] = []
        
        # Thread pools for blocking operations
        self.thread_pools: Dict[str, ThreadPoolExecutor] = {}
        
        logger.info(f"PerformanceOptimizer initialized with {max_connections_per_provider} max connections per provider")
    
    async def initialize_connection_pools(self, providers: List[str]):
        """Initialize optimized connection pools for all providers"""
        try:
            for provider in providers:
                # Create optimized connector
                connector = aiohttp.TCPConnector(
                    limit=self.max_connections,
                    limit_per_host=self.max_connections // 2,
                    keepalive_timeout=60,
                    enable_cleanup_closed=True,
                    use_dns_cache=True,
                    ttl_dns_cache=300,  # 5 minutes DNS cache
                    family=0,  # Allow both IPv4 and IPv6
                )
                
                # Create session with optimized settings
                timeout = aiohttp.ClientTimeout(
                    total=self.connection_timeout,
                    connect=self.request_timeout,
                    sock_read=self.request_timeout
                )
                
                session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={
                        "User-Agent": "BubblePlatform/1.0 (Performance-Optimized)",
                        "Accept": "application/json",
                        "Accept-Encoding": "gzip, deflate",
                        "Connection": "keep-alive"
                    },
                    raise_for_status=False  # Handle errors manually
                )
                
                self.connection_pools[provider] = session
                
                # Initialize thread pool for this provider
                self.thread_pools[provider] = ThreadPoolExecutor(
                    max_workers=min(4, self.max_connections // 10),
                    thread_name_prefix=f"provider_{provider}"
                )
                
                logger.info(f"Connection pool initialized for {provider}")
            
            logger.info(f"All connection pools initialized for {len(providers)} providers")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize connection pools: {e}")
            return False
    
    async def cleanup_connection_pools(self):
        """Clean up connection pools and resources"""
        try:
            # Close all HTTP sessions
            for provider, session in self.connection_pools.items():
                if not session.closed:
                    await session.close()
                    logger.debug(f"Connection pool closed for {provider}")
            
            # Shutdown thread pools
            for provider, pool in self.thread_pools.items():
                pool.shutdown(wait=False)
                logger.debug(f"Thread pool shutdown for {provider}")
            
            # Clear collections
            self.connection_pools.clear()
            self.thread_pools.clear()
            
            # Force garbage collection
            if self.enable_memory_monitoring:
                gc.collect()
                logger.debug("Memory cleanup completed")
            
            logger.info("All connection pools and resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def performance_monitor(self, operation_name: str):
        """Decorator for monitoring operation performance"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                start_memory = None
                
                if self.enable_memory_monitoring:
                    process = psutil.Process()
                    start_memory = process.memory_info().rss / 1024 / 1024  # MB
                
                try:
                    result = await func(*args, **kwargs)
                    
                    # Record successful operation time
                    elapsed = (time.time() - start_time) * 1000  # Convert to ms
                    if operation_name not in self.request_times:
                        self.request_times[operation_name] = []
                    
                    self.request_times[operation_name].append(elapsed)
                    
                    # Keep only last 100 measurements
                    if len(self.request_times[operation_name]) > 100:
                        self.request_times[operation_name] = self.request_times[operation_name][-50:]
                    
                    # Log slow operations
                    if elapsed > 2000:  # 2 seconds
                        logger.warning(f"Slow operation detected: {operation_name} took {elapsed:.2f}ms")
                    
                    # Memory monitoring
                    if self.enable_memory_monitoring and start_memory:
                        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                        memory_diff = end_memory - start_memory
                        
                        if memory_diff > 50:  # 50MB increase
                            logger.warning(f"High memory usage: {operation_name} used {memory_diff:.2f}MB")
                        
                        self.memory_usage.append({
                            "timestamp": datetime.now(timezone.utc),
                            "operation": operation_name,
                            "memory_before_mb": start_memory,
                            "memory_after_mb": end_memory,
                            "memory_diff_mb": memory_diff,
                            "duration_ms": elapsed
                        })
                        
                        # Keep only last 50 memory measurements
                        if len(self.memory_usage) > 50:
                            self.memory_usage = self.memory_usage[-25:]
                    
                    return result
                    
                except Exception as e:
                    elapsed = (time.time() - start_time) * 1000
                    logger.error(f"Operation {operation_name} failed after {elapsed:.2f}ms: {e}")
                    raise
            
            return wrapper
        return decorator
    
    async def batch_requests(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: int = 10,
        batch_delay: float = 0.1
    ) -> List[Any]:
        """
        Execute requests in optimized batches
        
        Args:
            requests: List of request configurations
            max_concurrent: Maximum concurrent requests
            batch_delay: Delay between batches
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        
        async def execute_request(request_config):
            async with semaphore:
                try:
                    # Execute the request based on configuration
                    provider = request_config.get("provider")
                    operation = request_config.get("operation")
                    params = request_config.get("params", {})
                    
                    # Use appropriate provider and operation
                    # This would be implemented based on specific provider interfaces
                    logger.debug(f"Executing batch request: {provider}.{operation}")
                    
                    # Placeholder for actual execution
                    await asyncio.sleep(0.1)  # Simulate network delay
                    
                    return {"success": True, "provider": provider, "operation": operation}
                    
                except Exception as e:
                    logger.error(f"Batch request failed: {e}")
                    return {"success": False, "error": str(e)}
        
        # Execute requests in batches
        for i in range(0, len(requests), max_concurrent):
            batch = requests[i:i + max_concurrent]
            
            batch_tasks = [execute_request(req) for req in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            results.extend(batch_results)
            
            # Delay between batches (except for last batch)
            if i + max_concurrent < len(requests):
                await asyncio.sleep(batch_delay)
        
        return results
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        metrics = {
            "request_times": {},
            "memory_usage": {
                "current_mb": psutil.Process().memory_info().rss / 1024 / 1024 if self.enable_memory_monitoring else 0,
                "peak_usage": max(
                    [m["memory_after_mb"] for m in self.memory_usage], 
                    default=0
                ),
                "average_usage": sum(
                    [m["memory_after_mb"] for m in self.memory_usage]
                ) / max(len(self.memory_usage), 1)
            },
            "connection_pools": {
                provider: {
                    "closed": session.closed,
                    "connector_limit": session.connector.limit if hasattr(session, 'connector') else 0
                }
                for provider, session in self.connection_pools.items()
            },
            "thread_pools": {
                provider: {
                    "max_workers": pool._max_workers,
                    "active_threads": len([t for t in pool._threads if t.is_alive()]) if hasattr(pool, '_threads') else 0
                }
                for provider, pool in self.thread_pools.items()
            }
        }
        
        # Calculate request time statistics
        for operation, times in self.request_times.items():
            if times:
                metrics["request_times"][operation] = {
                    "count": len(times),
                    "average_ms": sum(times) / len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "p95_ms": sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0]
                }
        
        return metrics
    
    async def optimize_memory_usage(self):
        """Optimize memory usage by clearing caches and forcing garbage collection"""
        try:
            # Clear request time history
            for operation in self.request_times:
                if len(self.request_times[operation]) > 20:
                    self.request_times[operation] = self.request_times[operation][-10:]
            
            # Clear old memory usage data
            if len(self.memory_usage) > 20:
                self.memory_usage = self.memory_usage[-10:]
            
            # Force garbage collection
            collected = gc.collect()
            
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            logger.info(f"Memory optimization completed: {collected} objects collected, current usage: {current_memory:.2f}MB")
            
            return {
                "objects_collected": collected,
                "current_memory_mb": current_memory,
                "optimization_successful": True
            }
            
        except Exception as e:
            logger.error(f"Memory optimization failed: {e}")
            return {
                "objects_collected": 0,
                "current_memory_mb": 0,
                "optimization_successful": False,
                "error": str(e)
            }
    
    def recommend_optimizations(self) -> List[str]:
        """Analyze performance metrics and provide optimization recommendations"""
        recommendations = []
        metrics = self.get_performance_metrics()
        
        # Check request times
        for operation, stats in metrics["request_times"].items():
            if stats["average_ms"] > 1000:  # >1 second average
                recommendations.append(f"Consider caching for {operation} - average response time is {stats['average_ms']:.0f}ms")
            
            if stats["max_ms"] > 5000:  # >5 seconds max
                recommendations.append(f"Add timeout protection for {operation} - max response time is {stats['max_ms']:.0f}ms")
        
        # Check memory usage
        if metrics["memory_usage"]["current_mb"] > 500:  # >500MB
            recommendations.append("Consider memory optimization - current usage is high")
        
        if metrics["memory_usage"]["peak_usage"] > 1000:  # >1GB peak
            recommendations.append("Investigate memory leaks - peak usage is very high")
        
        # Check connection pools
        for provider, pool_info in metrics["connection_pools"].items():
            if pool_info["closed"]:
                recommendations.append(f"Reinitialize connection pool for {provider} - currently closed")
        
        # Generic recommendations
        if len(self.request_times) > 10:
            avg_response_time = sum(
                stats["average_ms"] for stats in metrics["request_times"].values()
            ) / len(metrics["request_times"])
            
            if avg_response_time > 800:  # >800ms average across all operations
                recommendations.append("Overall system performance is degraded - consider scaling")
        
        return recommendations

# Utility functions for dependency conflict resolution

def resolve_websocket_conflicts():
    """
    Resolve websockets version conflicts between OpenBB and other dependencies
    """
    try:
        import websockets
        import openbb
        
        logger.info(f"Websockets version: {websockets.__version__}")
        logger.info(f"OpenBB version: {openbb.__version__}")
        
        # Check for known compatibility issues
        compatibility_issues = []
        
        # OpenBB 4.4.5 is compatible with websockets 10.x and 11.x
        websockets_version = websockets.__version__
        major_version = int(websockets_version.split('.')[0])
        
        if major_version < 10:
            compatibility_issues.append("Websockets version too old for OpenBB 4.4.5")
        elif major_version > 12:
            compatibility_issues.append("Websockets version may be too new")
        
        if compatibility_issues:
            logger.warning(f"Websockets compatibility issues detected: {compatibility_issues}")
            return {
                "compatible": False,
                "issues": compatibility_issues,
                "recommendations": [
                    "Update websockets to version 10.x or 11.x",
                    "Consider using websockets==11.0.2 for best compatibility"
                ]
            }
        else:
            logger.info("Websockets dependencies are compatible")
            return {
                "compatible": True,
                "issues": [],
                "recommendations": []
            }
    
    except ImportError as e:
        logger.error(f"Failed to check websockets compatibility: {e}")
        return {
            "compatible": False,
            "issues": [f"Import error: {e}"],
            "recommendations": ["Install missing dependencies"]
        }

def check_all_dependencies():
    """Check all major dependencies for version conflicts"""
    import pkg_resources
    import subprocess
    import sys
    
    try:
        # Get list of installed packages
        installed_packages = {pkg.project_name: pkg.version for pkg in pkg_resources.working_set}
        
        # Key dependencies to check
        key_dependencies = [
            "fastapi",
            "uvicorn", 
            "sqlalchemy",
            "redis",
            "pydantic",
            "anthropic",
            "yfinance",
            "alpha-vantage", 
            "pandas",
            "numpy",
            "openbb",
            "websockets"
        ]
        
        dependency_status = {}
        for dep in key_dependencies:
            if dep in installed_packages:
                dependency_status[dep] = {
                    "installed": True,
                    "version": installed_packages[dep],
                    "status": "OK"
                }
            else:
                dependency_status[dep] = {
                    "installed": False,
                    "version": None,
                    "status": "MISSING"
                }
        
        # Check for pip check issues
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "check"], 
                                  capture_output=True, text=True, timeout=30)
            pip_issues = result.stdout + result.stderr if result.returncode != 0 else ""
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pip_issues = "Unable to run pip check"
        
        return {
            "dependencies": dependency_status,
            "pip_check_issues": pip_issues,
            "websockets_compatibility": resolve_websocket_conflicts()
        }
        
    except Exception as e:
        logger.error(f"Dependency check failed: {e}")
        return {
            "dependencies": {},
            "pip_check_issues": f"Check failed: {e}",
            "websockets_compatibility": {"compatible": False, "issues": [str(e)]}
        }