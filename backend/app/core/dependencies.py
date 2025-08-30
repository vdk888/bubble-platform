"""
FastAPI dependencies for rate limiting and authentication.
Following Interface-First Design with proper ordering to ensure rate limiting runs first.
"""

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import time

from .database import get_db
from .middleware.rate_limiting import RateLimitMiddleware
from ..models.user import User
from .security import auth_service

# Security scheme with auto_error=False to allow rate limiting first
security = HTTPBearer(auto_error=False)


async def check_rate_limit(request: Request) -> None:
    """
    Rate limiting dependency that runs before authentication.
    This ensures rate limits are checked before auth dependencies.
    """
    # Import here to avoid circular imports
    from ..main import app
    
    # Get the rate limiting middleware instance from the app
    rate_limit_middleware = None
    for middleware in app.user_middleware:
        if hasattr(middleware, 'cls') and middleware.cls.__name__ == 'RateLimitMiddleware':
            rate_limit_middleware = middleware.cls
            break
    
    if rate_limit_middleware is None:
        # No rate limiting middleware found, skip check
        return
    
    # Create a temporary middleware instance to check rate limits
    # Note: This is a workaround for FastAPI's dependency ordering
    import os
    from ..core.config import settings
    from ..services.implementations.memory_rate_limiter import MemoryRateLimiter
    from ..services.implementations.redis_rate_limiter import RedisRateLimiter
    
    environment = os.environ.get("ENVIRONMENT", settings.environment)
    
    # Only apply rate limiting in specific environments
    is_rate_limiting_enabled = (
        environment == "testing_with_rate_limits" or
        environment == "production"
    )
    
    if not is_rate_limiting_enabled:
        return
    
    # Initialize rate limiter
    if environment == "testing_with_rate_limits":
        rate_limiter = MemoryRateLimiter()
    else:
        rate_limiter = RedisRateLimiter()
    
    path = request.url.path
    method = request.method
    
    # Skip exempt paths
    exempt_paths = ["/health", "/health/ready", "/docs", "/openapi.json", "/redoc"]
    if any(path.startswith(exempt_path) for exempt_path in exempt_paths):
        return
    
    # Rate limiting configuration (same as middleware)
    rate_limit_config = {
        "/api/v1/auth/login": {"limit": 10, "window": 60, "identifier": "ip"},
        "/api/v1/auth/register": {"limit": 5, "window": 300, "identifier": "ip"},
        "/api/v1/auth/me": {"limit": 30, "window": 60, "identifier": "ip"},
        "/api/v1/auth/refresh": {"limit": 20, "window": 60, "identifier": "ip"},
        "/api/v1/auth/logout": {"limit": 10, "window": 60, "identifier": "ip"},
        "default": {"limit": 100, "window": 60, "identifier": "user"}
    }
    
    # Get configuration for this endpoint
    config = rate_limit_config.get(path, rate_limit_config["default"])
    limit = config["limit"]
    window = config["window"]
    identifier_type = config["identifier"]
    
    # Get identifier
    if identifier_type == "ip":
        # Get client IP
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            identifier = f"ip:{forwarded_for.split(',')[0].strip()}"
        else:
            real_ip = request.headers.get("x-real-ip")
            if real_ip:
                identifier = f"ip:{real_ip}"
            else:
                identifier = f"ip:{request.client.host if request.client else 'unknown'}"
    else:
        # Default to IP for dependencies (user not available yet)
        identifier = f"ip:{request.client.host if request.client else 'unknown'}"
    
    endpoint_key = f"{method}:{path}"
    
    try:
        # Check rate limit
        is_allowed = await rate_limiter.check_rate_limit(
            identifier=identifier,
            endpoint=endpoint_key,
            limit=limit,
            window_seconds=window
        )
        
        if not is_allowed:
            # Rate limit exceeded
            rate_info = await rate_limiter.get_rate_limit_info(identifier, endpoint_key)
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {rate_info.limit} per {rate_info.window_seconds} seconds",
                    "retry_after": rate_info.window_seconds,
                    "current_count": rate_info.current_count,
                    "limit": rate_info.limit,
                    "reset_time": rate_info.reset_time.isoformat()
                }
            )
        
        # Increment counter for successful rate limit check
        await rate_limiter.increment_counter(identifier, endpoint_key)
        
    except HTTPException:
        raise  # Re-raise rate limit exceptions
    except Exception as e:
        # Rate limiter error - allow request to proceed (fail open)
        print(f"Rate limiting dependency error: {e}")
        pass


async def get_current_user(
    _: None = Depends(check_rate_limit),  # Rate limiting runs first
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user.
    Rate limiting is checked first via check_rate_limit dependency.
    """
    # Check if credentials are provided (auto_error=False allows None)
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    token_data = auth_service.verify_token(token)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account",
        )
    
    return user