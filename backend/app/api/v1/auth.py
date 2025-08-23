from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime, timezone
import logging
import html
import re

from ...core.database import get_db
from ...core.security import auth_service, TokenResponse, PasswordStrength
from ...core.middleware import rate_limit_auth, limiter
from ...models.user import User, UserRole, SubscriptionTier

# Set up logging for audit trail
logging.basicConfig(level=logging.INFO)
audit_logger = logging.getLogger("auth_audit")

# Security scheme
security = HTTPBearer()

router = APIRouter()


# Request/Response models
class UserRegistration(BaseModel):
    """User registration request model"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    subscription_tier: Optional[SubscriptionTier] = SubscriptionTier.FREE
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        is_valid, strength, feedback = auth_service.validate_password_strength(v)
        if not is_valid:
            raise ValueError(f"Password validation failed: {'; '.join(feedback)}")
        return v
    
    @field_validator('full_name')
    @classmethod
    def sanitize_full_name(cls, v):
        if v is None:
            return v
        # Sanitize HTML and dangerous characters
        sanitized = html.escape(v, quote=True)
        # Check for script tags and other dangerous patterns
        dangerous_patterns = [r'<script', r'javascript:', r'vbscript:', r'on\w+\s*=']
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Full name contains invalid characters")
        return sanitized


class UserLogin(BaseModel):
    """User login request model"""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""
    refresh_token: str


class UserResponse(BaseModel):
    """AI-friendly user response model"""
    success: bool
    user: dict
    message: str
    next_actions: list[str] = []


class ErrorResponse(BaseModel):
    """Standardized error response"""
    success: bool = False
    error: str
    error_code: str
    message: str


# Dependency for getting current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user
    Validates JWT token and returns user object
    """
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


# Authentication endpoints
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register_user(
    user_data: UserRegistration,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    User registration with subscription tier support
    Following Sprint 1 specification for AI-friendly responses
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            audit_logger.warning(f"Registration attempt with existing email: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = auth_service.get_password_hash(user_data.password)
        
        db_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            subscription_tier=user_data.subscription_tier,
            role=UserRole.USER,
            is_verified=False  # Email verification required
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Audit logging
        audit_logger.info(
            f"User registered: {db_user.email} | "
            f"ID: {db_user.id} | "
            f"Tier: {db_user.subscription_tier.value} | "
            f"IP: {request.client.host}"
        )
        
        # Create token response
        user_dict = {
            "id": db_user.id,
            "email": db_user.email,
            "full_name": db_user.full_name,
            "role": db_user.role.value,
            "subscription_tier": db_user.subscription_tier.value,
            "is_verified": db_user.is_verified,
            "created_at": db_user.created_at.isoformat(),
            "has_created_universe": False  # New user hasn't created anything yet
        }
        
        return auth_service.create_token_response(
            user_dict,
            "Registration successful! Please verify your email to access all features."
        )
        
    except HTTPException:
        # Re-raise HTTPException without catching
        raise
    except IntegrityError:
        db.rollback()
        audit_logger.warning(f"Registration attempt with duplicate email (IntegrityError): {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    except Exception as e:
        db.rollback()
        audit_logger.error(f"Registration error for {user_data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login_user(
    login_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    User authentication with AI-friendly response format
    Following Sprint 1 specification with multi-tenant JWT claims
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == login_data.email).first()
        
        if not user or not auth_service.verify_password(login_data.password, user.hashed_password):
            audit_logger.warning(
                f"Failed login attempt: {login_data.email} | "
                f"IP: {request.client.host}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        if not user.is_active:
            audit_logger.warning(f"Login attempt on inactive account: {login_data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive"
            )
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        
        # Audit logging
        audit_logger.info(
            f"Successful login: {user.email} | "
            f"ID: {user.id} | "
            f"Role: {user.role.value} | "
            f"IP: {request.client.host}"
        )
        
        # Check if user has created content (for next_actions)
        has_universes = db.query(User).filter(User.id == user.id).first().universes != []
        
        user_dict = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "subscription_tier": user.subscription_tier.value,
            "is_verified": user.is_verified,
            "last_login": user.last_login.isoformat(),
            "has_created_universe": has_universes
        }
        
        return auth_service.create_token_response(
            user_dict,
            "Login successful! Welcome back to Bubble Platform."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        audit_logger.error(f"Login error for {login_data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Token refresh with rotation for security
    Following Sprint 1 specification for enhanced security
    """
    try:
        # Verify refresh token
        token_data = auth_service.verify_token(refresh_request.refresh_token)
        
        if token_data is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user data
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Audit logging
        audit_logger.info(
            f"Token refresh: {user.email} | "
            f"ID: {user.id} | "
            f"IP: {request.client.host}"
        )
        
        # Create new tokens (token rotation for security)
        user_dict = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "subscription_tier": user.subscription_tier.value,
            "is_verified": user.is_verified,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
        
        return auth_service.create_token_response(
            user_dict,
            "Token refreshed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        audit_logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user profile with AI-friendly format
    Following Sprint 1 specification for structured responses
    """
    next_actions = []
    
    # Generate contextual next actions
    if not current_user.is_verified:
        next_actions.append("verify_email")
    
    if current_user.subscription_tier == SubscriptionTier.FREE:
        next_actions.append("explore_premium_features")
    
    if not current_user.universes:
        next_actions.append("create_first_universe")
    elif not current_user.strategies:
        next_actions.append("build_first_strategy")
    elif not current_user.portfolios:
        next_actions.append("create_master_portfolio")
    
    return UserResponse(
        success=True,
        user={
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role.value,
            "subscription_tier": current_user.subscription_tier.value,
            "is_verified": current_user.is_verified,
            "created_at": current_user.created_at.isoformat(),
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
            "universe_count": len(current_user.universes),
            "strategy_count": len(current_user.strategies),
            "portfolio_count": len(current_user.portfolios)
        },
        message="User profile retrieved successfully",
        next_actions=next_actions
    )


@router.post("/logout")
async def logout_user(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    User logout with session cleanup
    Following Sprint 1 specification with Redis cleanup (when implemented)
    """
    # Audit logging
    audit_logger.info(
        f"User logout: {current_user.email} | "
        f"ID: {current_user.id} | "
        f"IP: {request.client.host}"
    )
    
    # TODO: Add Redis session cleanup when Redis is integrated
    # For now, we rely on client-side token removal
    
    return {
        "success": True,
        "message": "Logout successful",
        "next_actions": ["login"]
    }