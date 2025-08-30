"""
Input Validation Middleware - Sprint 2.5 Part D Implementation

Enterprise-grade input validation middleware with XSS protection,
SQL injection prevention, and business rule validation.

Following Interface-First Design methodology from planning/0_dev.md
"""
import json
from typing import Callable, Dict, Any
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from ...services.interfaces.security import IInputValidator
from ...services.implementations.input_validator import EnterpriseInputValidator


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Input validation middleware for FastAPI applications.
    
    Features:
    - Automatic input sanitization for all requests
    - XSS protection via HTML sanitization
    - SQL injection pattern detection
    - Business rule validation for specific endpoints
    - Configurable validation rules per endpoint
    """
    
    def __init__(
        self, 
        app, 
        input_validator: IInputValidator = None,
        enable_validation: bool = True,
        exempt_paths: list = None
    ):
        """
        Initialize input validation middleware.
        
        Args:
            app: FastAPI application instance
            input_validator: Input validator implementation
            enable_validation: Whether to enable validation
            exempt_paths: Paths to exempt from validation
        """
        super().__init__(app)
        
        self.input_validator = input_validator or EnterpriseInputValidator()
        self.enable_validation = enable_validation
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc"
        ]
        
        # Validation configuration per endpoint
        self.validation_config = {
            "/api/v1/universes/timeline": {
                "schema": "temporal_universe_request",
                "context": "html",
                "business_rules": "universe_timeline"
            },
            "/api/v1/universes/backfill": {
                "schema": "backfill_request", 
                "context": "html",
                "business_rules": "backfill_universe"
            },
            "/snapshots": {
                "schema": "snapshot_request",
                "context": "html", 
                "business_rules": "create_snapshot"
            },
            "default": {
                "schema": None,
                "context": "general",
                "business_rules": None
            }
        }
    
    def _is_exempt_path(self, path: str) -> bool:
        """
        Check if path is exempt from input validation.
        
        Args:
            path: Request path
            
        Returns:
            True if path is exempt
        """
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False
    
    def _get_validation_config(self, path: str, method: str) -> Dict[str, Any]:
        """
        Get validation configuration for specific path and method.
        
        Args:
            path: Request path
            method: HTTP method
            
        Returns:
            Validation configuration dictionary
        """
        # Exact match first
        if path in self.validation_config:
            return self.validation_config[path]
        
        # Pattern matching for dynamic paths
        for pattern, config in self.validation_config.items():
            if pattern != "default" and pattern in path:
                return config
        
        # Use default configuration
        return self.validation_config["default"]
    
    async def _get_request_data(self, request: Request) -> Dict[str, Any]:
        """
        Extract data from request for validation.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Dictionary containing request data
        """
        data = {}
        
        # Get query parameters
        if request.query_params:
            data.update(dict(request.query_params))
        
        # Get path parameters
        if hasattr(request, 'path_params') and request.path_params:
            data.update(request.path_params)
        
        # Get JSON body for POST/PUT requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            
            if "application/json" in content_type:
                try:
                    # Check if body was already read and stored
                    if hasattr(request.state, 'original_body'):
                        body = request.state.original_body
                    else:
                        # Read and store original body
                        body = await request.body()
                        request.state.original_body = body
                    
                    if body:
                        json_data = json.loads(body.decode())
                        if isinstance(json_data, dict):
                            data.update(json_data)
                        else:
                            data["body"] = json_data
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Invalid JSON - will be caught by validation
                    data["body"] = body.decode() if body else ""
        
        return data
    
    def _get_user_context(self, request: Request) -> Dict[str, Any]:
        """
        Get user context for business rule validation.
        
        Args:
            request: FastAPI request object
            
        Returns:
            User context dictionary
        """
        context = {
            "subscription_tier": "free",  # Default
            "user_id": None,
            "ip_address": request.client.host if request.client else "unknown"
        }
        
        # Get user info from request state (set by auth middleware)
        if hasattr(request.state, 'user'):
            user = request.state.user
            context["user_id"] = getattr(user, 'id', None)
            context["subscription_tier"] = getattr(user, 'subscription_tier', 'free')
        
        return context
    
    async def _create_validation_error_response(
        self, 
        validation_result, 
        message: str = "Input validation failed"
    ) -> Response:
        """
        Create standardized validation error response.
        
        Args:
            validation_result: Validation result object
            message: Error message
            
        Returns:
            HTTP 400 response with validation details
        """
        error_response = {
            "error": "Validation Error",
            "message": message,
            "details": validation_result.errors,
            "risk_score": validation_result.risk_score
        }
        
        # Include sanitized data for debugging in non-production
        # In production, this should be logged but not returned
        if validation_result.risk_score < 0.7:  # Only for low-risk cases
            error_response["sanitized_data"] = validation_result.sanitized_data
        
        return Response(
            content=json.dumps(error_response),
            status_code=status.HTTP_400_BAD_REQUEST,
            media_type="application/json"
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request through input validation middleware.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response with input validation applied
        """
        # Skip validation if disabled
        if not self.enable_validation:
            return await call_next(request)
        
        path = request.url.path
        method = request.method
        
        # Skip exempt paths
        if self._is_exempt_path(path):
            return await call_next(request)
        
        try:
            # Get validation configuration
            config = self._get_validation_config(path, method)
            
            # Extract request data
            request_data = await self._get_request_data(request)
            
            if not request_data:
                # No data to validate - proceed
                return await call_next(request)
            
            # Perform input sanitization
            sanitized_data = await self.input_validator.sanitize_user_input(
                request_data,
                context=config["context"]
            )
            
            # Perform schema validation if configured
            if config["schema"]:
                validation_result = await self.input_validator.validate_temporal_input(
                    request_data,
                    schema=config["schema"]
                )
                
                if not validation_result.is_valid:
                    return await self._create_validation_error_response(
                        validation_result,
                        f"Schema validation failed for {config['schema']}"
                    )
                
                # Check risk score
                if validation_result.risk_score > 0.8:
                    return await self._create_validation_error_response(
                        validation_result,
                        "Input rejected due to high security risk score"
                    )
            
            # Perform business rule validation if configured
            if config["business_rules"]:
                user_context = self._get_user_context(request)
                
                business_validation = await self.input_validator.validate_business_rules(
                    request_data,
                    operation=config["business_rules"],
                    user_context=user_context
                )
                
                if not business_validation.is_valid:
                    return await self._create_validation_error_response(
                        business_validation,
                        "Business rule validation failed"
                    )
            
            # Store sanitized data in request state for use by handlers
            request.state.sanitized_input = sanitized_data
            
            # Process request
            response = await call_next(request)
            
            return response
            
        except Exception as e:
            # Log validation error but don't block request
            print(f"Input validation error: {e}")
            
            # For high-severity errors, block the request
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['injection', 'script', 'malicious']):
                error_response = {
                    "error": "Security Error",
                    "message": "Request blocked due to security policy violation",
                    "timestamp": request.state.get('timestamp', 'unknown')
                }
                
                return Response(
                    content=json.dumps(error_response),
                    status_code=status.HTTP_403_FORBIDDEN,
                    media_type="application/json"
                )
            
            # For other errors, allow request to proceed
            return await call_next(request)


def create_input_validation_middleware(
    input_validator: IInputValidator = None,
    enable_validation: bool = True,
    custom_config: Dict[str, Any] = None
) -> type:
    """
    Factory function to create input validation middleware with custom configuration.
    
    Args:
        input_validator: Custom input validator implementation
        enable_validation: Whether to enable validation
        custom_config: Custom validation configuration
        
    Returns:
        Configured middleware class
    """
    class CustomInputValidationMiddleware(InputValidationMiddleware):
        def __init__(self, app):
            super().__init__(
                app=app,
                input_validator=input_validator,
                enable_validation=enable_validation
            )
            
            if custom_config:
                self.validation_config.update(custom_config)
    
    return CustomInputValidationMiddleware


# Predefined configurations for different environments
DEVELOPMENT_CONFIG = {
    "enable_validation": True,
    "custom_config": {
        # Lenient validation for development
        "default": {
            "schema": None,
            "context": "general",
            "business_rules": None
        }
    }
}

PRODUCTION_CONFIG = {
    "enable_validation": True,
    "custom_config": {
        # Strict validation for production
        "/api/v1/universes/timeline": {
            "schema": "temporal_universe_request",
            "context": "html",
            "business_rules": "universe_timeline"
        },
        "/api/v1/universes/backfill": {
            "schema": "backfill_request",
            "context": "html", 
            "business_rules": "backfill_universe"
        },
        "default": {
            "schema": None,
            "context": "html",  # Always sanitize HTML in production
            "business_rules": None
        }
    }
}

TESTING_CONFIG = {
    "enable_validation": False,  # Disabled for testing
    "custom_config": {}
}