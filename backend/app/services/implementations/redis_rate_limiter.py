"""
Redis-Based Rate Limiter Implementation - Sprint 2.5 Part D

Enterprise-grade rate limiting with Redis backend using sliding window algorithm.
Implements IRateLimiter interface with high-performance concurrent support.

Following Interface-First Design methodology from planning/0_dev.md
"""
import time
import json
from typing import Dict, Optional
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.exceptions import RedisError

from ..interfaces.security import IRateLimiter, RateLimitInfo
from ..interfaces.base import ServiceResult


class RedisRateLimiter(IRateLimiter):
    """
    Redis-based rate limiter using sliding window algorithm.
    
    Features:
    - Sliding window rate limiting for accurate request counting
    - Per-endpoint rate limit configuration
    - Redis cluster support for high availability
    - Memory-efficient with automatic cleanup
    - Detailed monitoring and metrics
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None, key_prefix: str = "rate_limit"):
        """
        Initialize Redis rate limiter.
        
        Args:
            redis_client: Redis client instance (defaults to localhost)
            key_prefix: Key prefix for Redis keys
        """
        if redis_client is None:
            # Default Redis connection for development
            redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        
        self.redis = redis_client
        self.key_prefix = key_prefix
        
        # Default rate limits per endpoint (requests per minute)
        self.default_limits = {
            "/api/v1/universes": 100,
            "/api/v1/universes/timeline": 60,
            "/api/v1/universes/backfill": 10,
            "/api/v1/universes/snapshots": 50,
            "/api/v1/auth/login": 10,
            "/api/v1/auth/register": 5,
            "default": 100
        }
    
    def _get_key(self, identifier: str, endpoint: str) -> str:
        """Generate Redis key for rate limit tracking."""
        return f"{self.key_prefix}:{endpoint}:{identifier}"
    
    def _get_limit_for_endpoint(self, endpoint: str) -> int:
        """Get rate limit for specific endpoint."""
        # Exact match first
        if endpoint in self.default_limits:
            return self.default_limits[endpoint]
        
        # Pattern matching for dynamic endpoints
        for pattern, limit in self.default_limits.items():
            if pattern in endpoint:
                return limit
        
        return self.default_limits["default"]
    
    async def check_rate_limit(
        self, 
        identifier: str, 
        endpoint: str, 
        limit: int = None, 
        window_seconds: int = 60
    ) -> bool:
        """
        Check if request is within rate limits using sliding window algorithm.
        
        Args:
            identifier: User ID, IP address, or other identifier
            endpoint: API endpoint being accessed
            limit: Maximum requests allowed (uses default if None)
            window_seconds: Time window in seconds (default: 60)
            
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        try:
            if limit is None:
                limit = self._get_limit_for_endpoint(endpoint)
            
            key = self._get_key(identifier, endpoint)
            current_time = time.time()
            window_start = current_time - window_seconds
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Remove old entries outside window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]
            
            # Check if under limit
            return current_count < limit
            
        except RedisError as e:
            # Fail open - allow request if Redis is unavailable
            # Log the error for monitoring
            print(f"Redis rate limiter error: {e}")
            return True
        except Exception as e:
            print(f"Rate limiter unexpected error: {e}")
            return True
    
    async def increment_counter(
        self, 
        identifier: str, 
        endpoint: str
    ) -> int:
        """
        Increment request counter and return current count.
        
        Args:
            identifier: User ID, IP address, or other identifier
            endpoint: API endpoint being accessed
            
        Returns:
            Current request count in the window
        """
        try:
            key = self._get_key(identifier, endpoint)
            current_time = time.time()
            
            # Use Redis pipeline for atomic operations
            pipe = self.redis.pipeline()
            
            # Add current request with timestamp as score and value
            request_id = f"{current_time}:{identifier}"
            pipe.zadd(key, {request_id: current_time})
            
            # Set expiration for automatic cleanup
            pipe.expire(key, 3600)  # Auto-expire after 1 hour
            
            # Get current count
            pipe.zcard(key)
            
            # Execute pipeline
            results = await pipe.execute()
            return results[2]  # Result from zcard
            
        except RedisError as e:
            print(f"Redis increment error: {e}")
            return 0
        except Exception as e:
            print(f"Increment counter unexpected error: {e}")
            return 0
    
    async def get_rate_limit_info(
        self,
        identifier: str,
        endpoint: str
    ) -> RateLimitInfo:
        """
        Get detailed rate limit information for monitoring.
        
        Args:
            identifier: User ID, IP address, or other identifier
            endpoint: API endpoint being accessed
            
        Returns:
            Detailed rate limit information
        """
        try:
            key = self._get_key(identifier, endpoint)
            limit = self._get_limit_for_endpoint(endpoint)
            window_seconds = 60  # Default window
            
            current_time = time.time()
            window_start = current_time - window_seconds
            
            # Clean up old entries and get current count
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            
            results = await pipe.execute()
            current_count = results[1]
            
            # Calculate reset time (next window)
            reset_time = datetime.fromtimestamp(current_time + window_seconds)
            
            return RateLimitInfo(
                identifier=identifier,
                endpoint=endpoint,
                current_count=current_count,
                limit=limit,
                window_seconds=window_seconds,
                reset_time=reset_time,
                blocked=current_count >= limit
            )
            
        except Exception as e:
            print(f"Get rate limit info error: {e}")
            # Return safe defaults
            return RateLimitInfo(
                identifier=identifier,
                endpoint=endpoint,
                current_count=0,
                limit=self._get_limit_for_endpoint(endpoint),
                window_seconds=60,
                reset_time=datetime.now() + timedelta(seconds=60),
                blocked=False
            )
    
    async def reset_rate_limit(
        self,
        identifier: str,
        endpoint: str
    ) -> bool:
        """
        Reset rate limit counter (admin function).
        
        Args:
            identifier: User ID, IP address, or other identifier
            endpoint: API endpoint being accessed
            
        Returns:
            True if reset successful
        """
        try:
            key = self._get_key(identifier, endpoint)
            result = await self.redis.delete(key)
            return result > 0
            
        except Exception as e:
            print(f"Reset rate limit error: {e}")
            return False
    
    async def get_global_stats(self) -> Dict[str, int]:
        """
        Get global rate limiting statistics.
        
        Returns:
            Dictionary with global statistics
        """
        try:
            pattern = f"{self.key_prefix}:*"
            keys = await self.redis.keys(pattern)
            
            stats = {
                "total_tracked_endpoints": len(keys),
                "active_rate_limits": 0,
                "total_requests_tracked": 0
            }
            
            # Get detailed stats for each key
            for key in keys:
                count = await self.redis.zcard(key)
                stats["total_requests_tracked"] += count
                if count > 0:
                    stats["active_rate_limits"] += 1
            
            return stats
            
        except Exception as e:
            print(f"Get global stats error: {e}")
            return {
                "total_tracked_endpoints": 0,
                "active_rate_limits": 0,
                "total_requests_tracked": 0
            }
    
    async def cleanup_expired_entries(self) -> int:
        """
        Manual cleanup of expired entries (usually handled automatically).
        
        Returns:
            Number of entries cleaned up
        """
        try:
            pattern = f"{self.key_prefix}:*"
            keys = await self.redis.keys(pattern)
            
            current_time = time.time()
            window_start = current_time - 3600  # Clean entries older than 1 hour
            
            total_cleaned = 0
            for key in keys:
                cleaned = await self.redis.zremrangebyscore(key, 0, window_start)
                total_cleaned += cleaned
            
            return total_cleaned
            
        except Exception as e:
            print(f"Cleanup expired entries error: {e}")
            return 0
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of rate limiter components.
        
        Returns:
            Health check results
        """
        health = {
            "redis_connection": False,
            "redis_operations": False
        }
        
        try:
            # Test Redis connection
            await self.redis.ping()
            health["redis_connection"] = True
            
            # Test Redis operations
            test_key = f"{self.key_prefix}:health_check"
            await self.redis.set(test_key, "test", ex=10)
            result = await self.redis.get(test_key)
            await self.redis.delete(test_key)
            
            health["redis_operations"] = result == "test"
            
        except Exception as e:
            print(f"Rate limiter health check error: {e}")
        
        return health
    
    async def configure_endpoint_limits(self, limits: Dict[str, int]) -> bool:
        """
        Configure custom rate limits for endpoints.
        
        Args:
            limits: Dictionary mapping endpoints to rate limits
            
        Returns:
            True if configuration successful
        """
        try:
            # Store configuration in Redis for persistence
            config_key = f"{self.key_prefix}:config:limits"
            await self.redis.hset(config_key, mapping=limits)
            
            # Update local configuration
            self.default_limits.update(limits)
            
            return True
            
        except Exception as e:
            print(f"Configure endpoint limits error: {e}")
            return False
    
    async def load_endpoint_limits(self) -> bool:
        """
        Load endpoint limits from Redis configuration.
        
        Returns:
            True if loading successful
        """
        try:
            config_key = f"{self.key_prefix}:config:limits"
            limits = await self.redis.hgetall(config_key)
            
            if limits:
                # Convert string values to integers
                int_limits = {k: int(v) for k, v in limits.items()}
                self.default_limits.update(int_limits)
                return True
            
            return False
            
        except Exception as e:
            print(f"Load endpoint limits error: {e}")
            return False