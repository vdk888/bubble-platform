from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
import secrets
import re
from enum import Enum

from .config import settings


# Password strength levels
class PasswordStrength(str, Enum):
    WEAK = "weak"
    FAIR = "fair" 
    GOOD = "good"
    STRONG = "strong"


class TokenData(BaseModel):
    """JWT token data structure"""
    user_id: str
    email: str
    role: str
    subscription_tier: str
    exp: datetime
    iat: datetime
    jti: str  # JWT ID for token tracking


class TokenResponse(BaseModel):
    """AI-friendly authentication response"""
    success: bool
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]
    message: str
    next_actions: list[str] = []


class AuthService:
    """
    Advanced JWT authentication service with multi-tenant claims and Redis backing
    Following Sprint 1 specifications for financial compliance
    """
    
    def __init__(self):
        # Use bcrypt directly for better performance and no deprecation warnings
        self.bcrypt_rounds = 12  # Secure default for 2025
        self.algorithm = settings.jwt_algorithm
        self.secret_key = settings.secret_key
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.refresh_token_expire_days = settings.refresh_token_expire_days
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash using bcrypt directly"""
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'), 
                hashed_password.encode('utf-8')
            )
        except (ValueError, TypeError):
            return False
    
    def get_password_hash(self, password: str) -> str:
        """Hash password for storage using bcrypt directly"""
        salt = bcrypt.gensalt(rounds=self.bcrypt_rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def validate_password_strength(self, password: str) -> tuple[bool, PasswordStrength, list[str]]:
        """
        Enhanced password validation following Sprint 1 requirements
        Returns: (is_valid, strength_level, feedback_messages)
        """
        feedback = []
        score = 0
        
        # Minimum length check (12+ chars per financial compliance)
        if len(password) < 12:
            feedback.append("Password must be at least 12 characters long")
            return False, PasswordStrength.WEAK, feedback
        elif len(password) >= 16:
            score += 2
        else:
            score += 1
            
        # Complexity checks
        if re.search(r"[a-z]", password):
            score += 1
        else:
            feedback.append("Password must contain lowercase letters")
            
        if re.search(r"[A-Z]", password):
            score += 1
        else:
            feedback.append("Password must contain uppercase letters")
            
        if re.search(r"\d", password):
            score += 1
        else:
            feedback.append("Password must contain numbers")
            
        if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            score += 2
        else:
            feedback.append("Password should contain special characters")
            
        # Common password patterns check
        common_patterns = ["password", "123456", "qwerty", "admin", "bubble"]
        if any(pattern in password.lower() for pattern in common_patterns):
            feedback.append("Password contains common patterns")
            score -= 2
            
        # Determine strength
        if score < 4:
            strength = PasswordStrength.WEAK
        elif score < 6:
            strength = PasswordStrength.FAIR
        elif score < 8:
            strength = PasswordStrength.GOOD
        else:
            strength = PasswordStrength.STRONG
            
        is_valid = len(feedback) == 0 and strength in [PasswordStrength.GOOD, PasswordStrength.STRONG]
        
        if is_valid:
            feedback.append(f"Password strength: {strength.value}")
            
        return is_valid, strength, feedback
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """
        Create JWT access token with multi-tenant claims
        Following Sprint 1 specification for AI-friendly format
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        
        # Multi-tenant JWT claims for secure data isolation
        token_data = {
            "sub": user_data["id"],  # Subject (user ID)
            "email": user_data["email"],
            "role": user_data.get("role", "user"),
            "subscription_tier": user_data.get("subscription_tier", "free"),
            "iat": now,
            "exp": expire,
            "jti": secrets.token_urlsafe(32),  # JWT ID for tracking
            "type": "access_token"
        }
        
        return jwt.encode(token_data, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """Create refresh token with longer expiry"""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)
        
        token_data = {
            "sub": user_data["id"],
            "email": user_data["email"],
            "iat": now,
            "exp": expire,
            "jti": secrets.token_urlsafe(32),
            "type": "refresh_token"
        }
        
        return jwt.encode(token_data, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """
        Verify JWT token and return token data
        Supports both access and refresh tokens
        """
        try:
            # Handle None or empty token
            if not token:
                return None
                
            # JWT decode will automatically verify expiration if validate is True (default)
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            user_id: str = payload.get("sub")
            email: str = payload.get("email")
            
            if user_id is None or email is None:
                return None
            
            # Double-check expiration manually for security
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                exp_time = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                if datetime.now(timezone.utc) > exp_time:
                    return None
                
            token_data = TokenData(
                user_id=user_id,
                email=email,
                role=payload.get("role", "user"),
                subscription_tier=payload.get("subscription_tier", "free"),
                exp=datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc),
                iat=datetime.fromtimestamp(payload.get("iat"), tz=timezone.utc),
                jti=payload.get("jti", "")
            )
            
            return token_data
            
        except JWTError:
            return None
    
    def create_token_response(
        self, 
        user_data: Dict[str, Any], 
        message: str = "Authentication successful"
    ) -> TokenResponse:
        """
        Create AI-friendly authentication response
        Following Sprint 1 specification for structured responses
        """
        access_token = self.create_access_token(user_data)
        refresh_token = self.create_refresh_token(user_data)
        
        # Generate next actions based on user state
        next_actions = []
        if not user_data.get("is_verified"):
            next_actions.append("verify_email")
        # All users should explore premium features (free users to upgrade, premium users to discover more)
        next_actions.append("explore_premium_features")
        if not user_data.get("has_created_universe"):
            next_actions.append("create_first_universe")
            
        return TokenResponse(
            success=True,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60,
            user={
                "id": user_data["id"],
                "email": user_data["email"],
                "full_name": user_data.get("full_name"),
                "role": user_data.get("role", "user"),
                "subscription_tier": user_data.get("subscription_tier", "free"),
                "is_verified": user_data.get("is_verified", False),
                "last_login": user_data.get("last_login")
            },
            message=message,
            next_actions=next_actions
        )


# Global auth service instance
auth_service = AuthService()