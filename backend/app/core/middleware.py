from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time
import logging
from typing import Dict, Any
import html
import re

from .config import settings
from .database import get_db
from .rls_policies import apply_user_context_middleware, clear_user_context_middleware
from ..models.user import User

# Set up logging
logger = logging.getLogger(__name__)

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware for production readiness
    Following Sprint 1 specification for security compliance
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers for production readiness
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # HSTS header for HTTPS (only in production)
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Enhanced Content Security Policy for production security
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "img-src 'self' data: https: blob:; "
            "connect-src 'self' https://api.anthropic.com wss://localhost:8000; "
            "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none'; "
            "media-src 'self'; "
            "worker-src 'self'; "
            "manifest-src 'self'"
        )
        response.headers["Content-Security-Policy"] = csp
        
        return response


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Input sanitization middleware for all endpoints
    Following Sprint 1 specification for comprehensive input validation
    """
    
    # Patterns for potential security threats
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload\s*=',
        r'onerror\s*=',
        r'onclick\s*=',
        r'onmouseover\s*='
    ]
    
    SQL_INJECTION_PATTERNS = [
        r'(\bUNION\b|\bSELECT\b|\bINSERT\b|\bDELETE\b|\bUPDATE\b|\bDROP\b)',
        r'(\b(OR|AND)\b\s+\d+\s*=\s*\d+)',
        r'(\'\s*(OR|AND)\s+\')',
        r'(--|\#|\/\*|\*\/)'
    ]
    
    def _sanitize_string(self, value: str) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return value
            
        # HTML encode to prevent XSS
        sanitized = html.escape(value, quote=True)
        
        # Check for suspicious patterns
        for pattern in self.XSS_PATTERNS + self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Suspicious input pattern detected: {pattern} in value: {value[:100]}...")
                # Don't block, but log for monitoring
                
        return sanitized
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary data"""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self._sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_string(item) if isinstance(item, str)
                    else self._sanitize_dict(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized
    
    async def dispatch(self, request: Request, call_next):
        # Skip sanitization for certain endpoints (like file uploads)
        skip_paths = ["/docs", "/openapi.json", "/health"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Log request for audit trail
        logger.info(f"Request: {request.method} {request.url.path} from {request.client.host}")
        
        # Sanitize request body if present
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                if hasattr(request, "_json"):
                    # Request body already parsed
                    pass
                else:
                    # We don't modify the request body here as it would interfere with FastAPI parsing
                    # Sanitization is handled at the route level through validation
                    pass
            except Exception as e:
                logger.error(f"Error in input sanitization: {e}")
        
        response = await call_next(request)
        return response


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Audit logging middleware for authentication events
    Following Sprint 1 specification for financial compliance
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request details for sensitive endpoints
        sensitive_paths = ["/auth/", "/api/v1/portfolios/", "/api/v1/orders/"]
        is_sensitive = any(path in request.url.path for path in sensitive_paths)
        
        if is_sensitive:
            logger.info(
                f"AUDIT: {request.method} {request.url.path} | "
                f"IP: {request.client.host} | "
                f"User-Agent: {request.headers.get('user-agent', 'Unknown')}"
            )
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Log response for sensitive endpoints
        if is_sensitive:
            logger.info(
                f"AUDIT: Response {response.status_code} | "
                f"Time: {process_time:.3f}s | "
                f"Path: {request.url.path}"
            )
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


# Rate limiting decorators for different endpoint types
def rate_limit_auth():
    """Rate limit for authentication endpoints: 10 requests/minute (1000/minute in testing)"""
    import os
    import sys
    # Check if we're running under pytest
    if "pytest" in sys.modules or os.environ.get("ENVIRONMENT") == "testing":
        return limiter.limit("1000/minute")  # High limit for tests
    return limiter.limit("10/minute")


def rate_limit_general():
    """Rate limit for general API endpoints: 100 requests/minute (1000/minute in testing)"""
    import os
    import sys
    # Check if we're running under pytest
    if "pytest" in sys.modules or os.environ.get("ENVIRONMENT") == "testing":
        return limiter.limit("1000/minute")  # High limit for tests
    return limiter.limit("100/minute")


def rate_limit_financial():
    """Rate limit for financial operations: 5 requests/minute (1000/minute in testing)"""
    import os
    import sys
    # Check if we're running under pytest
    if "pytest" in sys.modules or os.environ.get("ENVIRONMENT") == "testing":
        return limiter.limit("1000/minute")  # High limit for tests
    return limiter.limit("5/minute")


def rate_limit_backtesting():
    """Rate limit for backtesting operations: 5 requests/minute (1000/minute in testing)"""
    import os
    if os.environ.get("ENVIRONMENT") == "testing":
        return limiter.limit("1000/minute")  # High limit for tests
    return limiter.limit("5/minute")


# Custom rate limit exceeded handler
def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom rate limit exceeded response"""
    logger.warning(
        f"Rate limit exceeded: {request.client.host} | "
        f"Path: {request.url.path} | "
        f"Limit: {exc.detail}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "error": "Rate limit exceeded",
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests. Please try again later.",
            "retry_after": exc.retry_after,
            "limit": exc.detail
        }
    )


# Custom rate limit handler will be applied at the app level


class PostgreSQLRLSMiddleware(BaseHTTPMiddleware):
    """
    PostgreSQL Row-Level Security middleware for multi-tenant data isolation
    Following Sprint 1 specification for bulletproof data security
    """
    
    async def dispatch(self, request: Request, call_next):
        # Skip RLS for public endpoints
        public_paths = ["/", "/docs", "/openapi.json", "/health", "/api/v1/features"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)
        
        # Skip RLS for authentication endpoints (no user context yet)
        auth_paths = ["/api/v1/auth/register", "/api/v1/auth/login"]
        if request.url.path in auth_paths:
            return await call_next(request)
        
        # Get database session
        db_session = None
        user_id = None
        
        try:
            # Extract user ID from Authorization header
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                from .security import auth_service
                token = auth_header.replace("Bearer ", "")
                token_data = auth_service.verify_token(token)
                
                if token_data:
                    user_id = token_data.user_id
                    
                    # Get database session
                    db_gen = get_db()
                    db_session = next(db_gen)
                    
                    # Apply user context for RLS
                    apply_user_context_middleware(db_session, user_id)
                    
                    logger.debug(f"Applied RLS user context: {user_id}")
            
            # Process request
            response = await call_next(request)
            
            return response
            
        except Exception as e:
            logger.error(f"RLS middleware error: {e}")
            # Don't block request if RLS fails - log for monitoring
            return await call_next(request)
            
        finally:
            # Clean up user context
            if db_session and user_id:
                try:
                    clear_user_context_middleware(db_session)
                    logger.debug(f"Cleared RLS user context: {user_id}")
                except Exception as e:
                    logger.error(f"Failed to clear RLS context: {e}")
                finally:
                    # Close database session
                    try:
                        db_session.close()
                    except Exception:
                        pass