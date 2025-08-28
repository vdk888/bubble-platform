"""
Rate Limiting Middleware - Sprint 2.5 Part D Implementation

Enterprise-grade rate limiting middleware with Redis backend.
Integrates with FastAPI for automatic rate limiting enforcement.

Following Interface-First Design methodology from planning/0_dev.md
"""
import time
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ...services.interfaces.security import IRateLimiter
from ...services.implementations.redis_rate_limiter import RedisRateLimiter
from ...services.implementations.memory_rate_limiter import MemoryRateLimiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI applications.
    
    Features:
    - Automatic rate limiting for all API endpoints
    - Configurable rate limits per endpoint pattern
    - User-based and IP-based rate limiting
    - Graceful degradation when rate limiter is unavailable
    - Detailed rate limit headers in responses
    """
    
    def __init__(
        self, 
        app, 
        rate_limiter: Optional[IRateLimiter] = None,
        enable_rate_limiting: bool = True,
        exempt_paths: list = None
    ):
        """
        Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application instance
            rate_limiter: Rate limiter implementation
            enable_rate_limiting: Whether to enable rate limiting
            exempt_paths: Paths to exempt from rate limiting
        """
        super().__init__(app)
        
        if rate_limiter is None:
            # Use memory rate limiter for testing, Redis for production
            import os
            environment = os.environ.get("ENVIRONMENT", "development")
            if environment == "testing_with_rate_limits":
                self.rate_limiter = MemoryRateLimiter()
            else:
                self.rate_limiter = RedisRateLimiter()
        else:
            self.rate_limiter = rate_limiter
        self.enable_rate_limiting = enable_rate_limiting
        self.exempt_paths = exempt_paths or [
            "/health",
            "/health/ready", 
            "/docs",
            "/openapi.json",
            "/redoc"
        ]
        
        # Rate limiting configuration per endpoint pattern
        self.rate_limit_config = {
            "/api/v1/auth/login": {"limit": 10, "window": 60, "identifier": "ip"},
            "/api/v1/auth/register": {"limit": 5, "window": 300, "identifier": "ip"},
            "/api/v1/universes/timeline": {"limit": 60, "window": 60, "identifier": "user"},
            "/api/v1/universes/backfill": {"limit": 10, "window": 60, "identifier": "user"},
            "/api/v1/universes/snapshots": {"limit": 50, "window": 60, "identifier": "user"},
            "/api/v1/universes": {"limit": 100, "window": 60, "identifier": "user"},
            "/api/v1/assets": {"limit": 200, "window": 60, "identifier": "user"},
            "default": {"limit": 100, "window": 60, "identifier": "user"}
        }
    
    def _get_identifier(self, request: Request, identifier_type: str) -> str:
        """
        Get rate limiting identifier based on type.
        
        Args:
            request: FastAPI request object
            identifier_type: Type of identifier ('user', 'ip', 'session')
            
        Returns:
            Identifier string for rate limiting
        """
        if identifier_type == "user":
            # Get user ID from request state (set by auth middleware)
            user_id = getattr(request.state, 'user_id', None)
            if user_id:
                return f"user:{user_id}"
            # Fall back to IP if no user ID
            return f"ip:{self._get_client_ip(request)}"
        
        elif identifier_type == "ip":
            return f"ip:{self._get_client_ip(request)}"
        
        elif identifier_type == "session":
            # Get session ID from cookies or headers
            session_id = request.cookies.get("session_id") or request.headers.get("x-session-id")
            if session_id:
                return f"session:{session_id}"
            # Fall back to IP if no session
            return f"ip:{self._get_client_ip(request)}"
        
        else:
            # Default to IP-based limiting
            return f"ip:{self._get_client_ip(request)}"
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request headers.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address
        """
        # Check for forwarded headers (behind proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection IP
        return request.client.host if request.client else "unknown"
    
    def _get_rate_limit_config(self, path: str) -> dict:
        """
        Get rate limit configuration for specific path.
        
        Args:
            path: Request path
            
        Returns:
            Rate limit configuration dictionary
        """
        # Exact match first
        if path in self.rate_limit_config:
            return self.rate_limit_config[path]
        
        # Pattern matching for dynamic paths
        for pattern, config in self.rate_limit_config.items():
            if pattern != "default" and pattern in path:
                return config
        
        # Use default configuration
        return self.rate_limit_config["default"]
    
    def _is_exempt_path(self, path: str) -> bool:
        """
        Check if path is exempt from rate limiting.
        
        Args:
            path: Request path
            
        Returns:
            True if path is exempt
        """
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False
    
    async def _add_rate_limit_headers(
        self, 
        response: Response, 
        identifier: str, 
        endpoint: str
    ) -> None:
        """
        Add rate limit headers to response.
        
        Args:
            response: Response object
            identifier: Rate limit identifier
            endpoint: API endpoint
        """
        try:
            rate_info = await self.rate_limiter.get_rate_limit_info(identifier, endpoint)
            
            # Add standard rate limiting headers
            response.headers["X-RateLimit-Limit"] = str(rate_info.limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, rate_info.limit - rate_info.current_count))
            response.headers["X-RateLimit-Reset"] = str(int(rate_info.reset_time.timestamp()))
            response.headers["X-RateLimit-Window"] = str(rate_info.window_seconds)
            
        except Exception as e:
            # Don't fail the request if headers can't be added
            print(f"Failed to add rate limit headers: {e}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through rate limiting middleware.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response with rate limiting applied
        """
        # Check environment dynamically for testing scenarios
        import os
        from ...core.config import settings
        environment = os.environ.get("ENVIRONMENT", settings.environment)
        
        # Enable rate limiting for specific environments
        is_rate_limiting_enabled = (
            self.enable_rate_limiting or 
            environment == "testing_with_rate_limits" or
            environment == "production"
        )
        
        # Skip rate limiting if disabled
        if not is_rate_limiting_enabled:
            return await call_next(request)
        
        path = request.url.path
        method = request.method
        
        # Skip exempt paths
        if self._is_exempt_path(path):
            return await call_next(request)
        
        # Get rate limit configuration
        config = self._get_rate_limit_config(path)
        limit = config["limit"]
        window = config["window"]
        identifier_type = config["identifier"]
        
        # Get identifier for rate limiting
        identifier = self._get_identifier(request, identifier_type)
        endpoint_key = f"{method}:{path}"
        
        try:
            # Check rate limit
            is_allowed = await self.rate_limiter.check_rate_limit(
                identifier=identifier,
                endpoint=endpoint_key,
                limit=limit,
                window_seconds=window
            )
            
            if not is_allowed:
                # Rate limit exceeded - return 429 Too Many Requests
                rate_info = await self.rate_limiter.get_rate_limit_info(identifier, endpoint_key)
                
                error_response = {
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {rate_info.limit} per {rate_info.window_seconds} seconds",
                    "retry_after": rate_info.window_seconds,
                    "current_count": rate_info.current_count,
                    "limit": rate_info.limit,
                    "reset_time": rate_info.reset_time.isoformat()
                }
                
                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content=error_response
                )
                
                # Add rate limiting headers
                await self._add_rate_limit_headers(response, identifier, endpoint_key)
                response.headers["Retry-After"] = str(rate_info.window_seconds)
                
                return response
            
            # Increment counter for successful requests
            await self.rate_limiter.increment_counter(identifier, endpoint_key)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limiting headers to successful responses
            await self._add_rate_limit_headers(response, identifier, endpoint_key)
            
            return response
            
        except Exception as e:
            # Rate limiter error - allow request to proceed (fail open)
            print(f"Rate limiting error: {e}")
            response = await call_next(request)
            
            # Add error header for debugging
            response.headers["X-RateLimit-Error"] = "Rate limiter temporarily unavailable"
            
            return response


def create_rate_limit_middleware(
    rate_limiter: Optional[IRateLimiter] = None,
    enable_rate_limiting: bool = True,
    custom_config: Optional[dict] = None
) -> type:
    """
    Factory function to create rate limiting middleware with custom configuration.
    
    Args:
        rate_limiter: Custom rate limiter implementation
        enable_rate_limiting: Whether to enable rate limiting
        custom_config: Custom rate limiting configuration
        
    Returns:
        Configured middleware class
    """
    class CustomRateLimitMiddleware(RateLimitMiddleware):
        def __init__(self, app):
            super().__init__(
                app=app,
                rate_limiter=rate_limiter,
                enable_rate_limiting=enable_rate_limiting
            )
            
            if custom_config:
                self.rate_limit_config.update(custom_config)
    
    return CustomRateLimitMiddleware


# Predefined configurations for different deployment environments
DEVELOPMENT_CONFIG = {
    "enable_rate_limiting": True,
    "custom_config": {
        # Relaxed limits for development
        "/api/v1/universes/timeline": {"limit": 1000, "window": 60, "identifier": "user"},
        "/api/v1/universes/backfill": {"limit": 100, "window": 60, "identifier": "user"},
        "default": {"limit": 1000, "window": 60, "identifier": "user"}
    }
}

PRODUCTION_CONFIG = {
    "enable_rate_limiting": True,
    "custom_config": {
        # Strict limits for production
        "/api/v1/auth/login": {"limit": 5, "window": 60, "identifier": "ip"},
        "/api/v1/auth/register": {"limit": 3, "window": 300, "identifier": "ip"},
        "/api/v1/universes/timeline": {"limit": 30, "window": 60, "identifier": "user"},
        "/api/v1/universes/backfill": {"limit": 5, "window": 60, "identifier": "user"},
        "default": {"limit": 60, "window": 60, "identifier": "user"}
    }
}

TESTING_CONFIG = {
    "enable_rate_limiting": False,  # Disabled for testing
    "custom_config": {}
}