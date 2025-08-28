"""
Memory-Based Rate Limiter for Testing
Simple in-memory rate limiter that doesn't require Redis.
Used for testing scenarios where Redis is not available.
"""
import time
from typing import Dict, List
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque

from ..interfaces.security import IRateLimiter, RateLimitInfo


class MemoryRateLimiter(IRateLimiter):
    """
    In-memory rate limiter for testing.
    
    Uses sliding window algorithm with in-memory storage.
    Not suitable for production (no persistence, not distributed).
    """
    
    def __init__(self):
        """Initialize in-memory rate limiter."""
        # Store request timestamps: key -> deque of timestamps
        self.request_history: Dict[str, deque] = defaultdict(deque)
        
        # Rate limits per endpoint pattern
        self.rate_limits = {
            "POST:/api/v1/auth/register": {"limit": 5, "window": 300},  # 5 per 5 minutes
            "POST:/api/v1/auth/login": {"limit": 10, "window": 60},     # 10 per minute
            "GET:/health/": {"limit": 1000, "window": 60},              # 1000 per minute (high)
            "default": {"limit": 100, "window": 60}                     # 100 per minute
        }
    
    def _get_key(self, identifier: str, endpoint: str) -> str:
        """Generate key for rate limit tracking."""
        return f"{endpoint}:{identifier}"
    
    def _get_rate_config(self, endpoint: str) -> dict:
        """Get rate limit configuration for endpoint."""
        if endpoint in self.rate_limits:
            return self.rate_limits[endpoint]
        
        # Pattern matching
        for pattern, config in self.rate_limits.items():
            if pattern in endpoint:
                return config
        
        return self.rate_limits["default"]
    
    def _clean_old_requests(self, key: str, window_seconds: int) -> None:
        """Remove old requests outside the time window."""
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        # Remove old timestamps
        while (self.request_history[key] and 
               self.request_history[key][0] < cutoff_time):
            self.request_history[key].popleft()
    
    async def check_rate_limit(
        self, 
        identifier: str, 
        endpoint: str, 
        limit: int = None, 
        window_seconds: int = 60
    ) -> bool:
        """
        Check if request is within rate limits.
        
        Args:
            identifier: User ID, IP address, or other identifier
            endpoint: API endpoint being accessed
            limit: Maximum requests allowed (uses config if None)
            window_seconds: Time window in seconds (uses config if None)
            
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        config = self._get_rate_config(endpoint)
        
        if limit is None:
            limit = config["limit"]
        if window_seconds is None:
            window_seconds = config["window"]
        
        key = self._get_key(identifier, endpoint)
        
        # Clean old requests
        self._clean_old_requests(key, window_seconds)
        
        # Check if under limit
        current_count = len(self.request_history[key])
        return current_count < limit
    
    async def increment_counter(
        self, 
        identifier: str, 
        endpoint: str
    ) -> None:
        """
        Increment request counter.
        
        Args:
            identifier: User ID, IP address, or other identifier
            endpoint: API endpoint being accessed
        """
        key = self._get_key(identifier, endpoint)
        current_time = time.time()
        
        # Add current request timestamp
        self.request_history[key].append(current_time)
        
        # Keep memory usage reasonable by limiting history size
        config = self._get_rate_config(endpoint)
        max_history = config["limit"] * 2  # Keep 2x limit for safety
        
        if len(self.request_history[key]) > max_history:
            self.request_history[key].popleft()
    
    async def get_rate_limit_info(
        self, 
        identifier: str, 
        endpoint: str
    ) -> RateLimitInfo:
        """
        Get detailed rate limit information.
        
        Args:
            identifier: User ID, IP address, or other identifier
            endpoint: API endpoint being accessed
            
        Returns:
            Detailed rate limit information
        """
        config = self._get_rate_config(endpoint)
        key = self._get_key(identifier, endpoint)
        
        # Clean old requests
        self._clean_old_requests(key, config["window"])
        
        current_count = len(self.request_history[key])
        reset_time = datetime.now(timezone.utc) + timedelta(seconds=config["window"])
        
        return RateLimitInfo(
            identifier=identifier,
            endpoint=endpoint,
            current_count=current_count,
            limit=config["limit"],
            window_seconds=config["window"],
            reset_time=reset_time,
            blocked=current_count >= config["limit"]
        )
    
    async def reset_rate_limit(
        self, 
        identifier: str, 
        endpoint: str
    ) -> bool:
        """
        Reset rate limit counter.
        
        Args:
            identifier: User ID, IP address, or other identifier
            endpoint: API endpoint being accessed
            
        Returns:
            True if reset successful
        """
        key = self._get_key(identifier, endpoint)
        if key in self.request_history:
            self.request_history[key].clear()
        return True