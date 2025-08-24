"""
COMPREHENSIVE AUTHENTICATION SECURITY TESTS
Following best practices from 0_dev.md and business logic from 00_sprint_roadmap.md

Tests real bcrypt password hashing, JWT validation, multi-tenant isolation,
and Sprint 1 authentication requirements with NO artificial bypasses.
"""

import pytest
import bcrypt
import time
from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.security import AuthService, PasswordStrength
from app.core.config import settings
from app.models.user import User, UserRole, SubscriptionTier


class TestPasswordHashingSecurity:
    """Test REAL password hashing - no fake hashed_password strings"""
    
    def test_password_hashing_with_bcrypt(self):
        """Test that passwords are properly hashed using bcrypt - CRITICAL SECURITY TEST"""
        auth_service = AuthService()
        
        # Test real password hashing
        password = "TestFinance2025!@#"
        hashed = auth_service.get_password_hash(password)
        
        # CRITICAL: Verify actual bcrypt hashing occurred
        assert hashed != password, "Password was not hashed!"
        assert hashed.startswith("$2b$"), "Not using bcrypt algorithm"
        assert len(hashed) > 50, "Hash too short - likely fake"
        
        # Test password verification works
        assert auth_service.verify_password(password, hashed) is True
        assert auth_service.verify_password("wrong_password", hashed) is False
        
        # Test different passwords create different hashes
        hash2 = auth_service.get_password_hash(password)
        assert hashed != hash2, "Hashes should be different (salt)"
        
        # Both should verify correctly
        assert auth_service.verify_password(password, hash2) is True
    
    def test_password_strength_validation_financial_compliance(self):
        """Test password validation meets Sprint 1 financial compliance requirements"""
        auth_service = AuthService()
        
        # Test minimum 12 characters (financial compliance requirement)
        valid, strength, feedback = auth_service.validate_password_strength("Short123!")
        assert valid is False
        assert "at least 12 characters" in str(feedback)
        
        # Test weak password rejected
        valid, strength, feedback = auth_service.validate_password_strength("password123456")
        assert valid is False
        assert strength == PasswordStrength.WEAK
        
        # Test strong password accepted
        valid, strength, feedback = auth_service.validate_password_strength("SecureFinance2025!@#")
        assert valid is True
        assert strength in [PasswordStrength.GOOD, PasswordStrength.STRONG]
        
        # Test common pattern detection
        valid, strength, feedback = auth_service.validate_password_strength("bubble123456789!")
        assert valid is False  # Contains "bubble" common pattern
        assert "common patterns" in str(feedback)
    
    def test_timing_attack_resistance(self):
        """Test password verification is resistant to timing attacks"""
        auth_service = AuthService()
        password = "TestFinance2025!@#"
        hashed = auth_service.get_password_hash(password)
        
        # Measure verification time for correct password
        start_time = time.perf_counter()
        auth_service.verify_password(password, hashed)
        correct_time = time.perf_counter() - start_time
        
        # Measure verification time for wrong password
        start_time = time.perf_counter()
        auth_service.verify_password("wrong_password", hashed)
        wrong_time = time.perf_counter() - start_time
        
        # Times should be relatively similar (within 10x)
        # This is not perfect but catches obvious timing issues
        ratio = max(correct_time, wrong_time) / min(correct_time, wrong_time)
        assert ratio < 10, f"Timing difference too large: {ratio}x"


class TestJWTSecurityValidation:
    """Test JWT token security - no fake tokens or bypasses"""
    
    def test_jwt_token_creation_and_validation(self):
        """Test JWT tokens are properly created and validated"""
        auth_service = AuthService()
        
        user_data = {
            "id": "test-user-123",
            "email": "test@bubble.com",
            "role": "user",
            "subscription_tier": "pro"
        }
        
        # Create access token
        token = auth_service.create_access_token(user_data)
        
        # Verify it's a real JWT (3 parts separated by dots)
        assert len(token.split('.')) == 3, "Invalid JWT format"
        
        # Verify token data
        token_data = auth_service.verify_token(token)
        assert token_data is not None
        assert token_data.user_id == "test-user-123"
        assert token_data.email == "test@bubble.com"
        assert token_data.role == "user"
        assert token_data.subscription_tier == "pro"
        
        # Verify expiration is set correctly
        expected_exp = datetime.now(timezone.utc) + timedelta(minutes=30)
        assert abs((token_data.exp - expected_exp).total_seconds()) < 60  # Within 1 minute
    
    def test_jwt_multi_tenant_claims(self):
        """Test JWT contains multi-tenant claims for data isolation"""
        auth_service = AuthService()
        
        user_data = {
            "id": "tenant-user-456",
            "email": "tenant@bubble.com",
            "role": "admin",
            "subscription_tier": "enterprise"
        }
        
        token = auth_service.create_access_token(user_data)
        
        # Decode token manually to verify all claims present
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        
        # Verify multi-tenant claims (critical for data isolation)
        assert payload["sub"] == "tenant-user-456"
        assert payload["email"] == "tenant@bubble.com"
        assert payload["role"] == "admin"
        assert payload["subscription_tier"] == "enterprise"
        assert payload["type"] == "access_token"
        assert "jti" in payload  # JWT ID for token tracking
        assert "iat" in payload  # Issued at
        assert "exp" in payload  # Expires at
    
    def test_jwt_token_expiration(self):
        """Test JWT tokens properly expire"""
        auth_service = AuthService()
        
        user_data = {"id": "test-user", "email": "test@bubble.com"}
        
        # Create token with very short expiry
        old_expire_minutes = auth_service.access_token_expire_minutes
        auth_service.access_token_expire_minutes = 0.02  # ~1.2 seconds for reliable testing
        
        try:
            token = auth_service.create_access_token(user_data)
            
            # Should be valid immediately
            assert auth_service.verify_token(token) is not None
            
            # Wait for expiration
            time.sleep(1.5)  # Wait longer than token expiry
            
            # Should be invalid after expiration
            assert auth_service.verify_token(token) is None
            
        finally:
            auth_service.access_token_expire_minutes = old_expire_minutes
    
    def test_jwt_invalid_token_handling(self):
        """Test handling of invalid JWT tokens"""
        auth_service = AuthService()
        
        # Test malformed token
        assert auth_service.verify_token("invalid.token") is None
        
        # Test token with wrong signature
        user_data = {"id": "test-user", "email": "test@bubble.com"}
        token = auth_service.create_access_token(user_data)
        tampered_token = token[:-10] + "tampered123"
        assert auth_service.verify_token(tampered_token) is None
        
        # Test empty token
        assert auth_service.verify_token("") is None
        assert auth_service.verify_token(None) is None


class TestAuthenticationEndpointsReal:
    """Test authentication endpoints with REAL password hashing and validation"""
    
    def test_user_registration_with_real_password_hashing(self, client: TestClient, db_session: Session):
        """Test user registration creates real bcrypt hashes"""
        import uuid
        registration_data = {
            "email": f"security.test.{uuid.uuid4().hex[:8]}@bubble.com",
            "password": "SecureFinance2025!@#",
            "full_name": "Security Test User"
        }
        
        response = client.post("/api/v1/auth/register", json=registration_data)
        assert response.status_code == 201
        
        # Verify user was created with real bcrypt hash
        user = db_session.query(User).filter(User.email == registration_data["email"]).first()
        assert user is not None
        
        # CRITICAL: Verify real bcrypt hashing was used
        assert user.hashed_password != registration_data["password"]
        assert user.hashed_password.startswith("$2b$")
        assert len(user.hashed_password) > 50
        
        # Verify password can be verified with bcrypt
        auth_service = AuthService()
        assert auth_service.verify_password(registration_data["password"], user.hashed_password)
    
    def test_login_with_real_password_verification(self, client: TestClient, db_session: Session):
        """Test login uses real password verification"""
        # Create user with real hashed password
        auth_service = AuthService()
        password = "SecureFinance2025!@#"
        hashed_password = auth_service.get_password_hash(password)
        
        user = User(
            email="login.test@bubble.com",
            hashed_password=hashed_password,  # Real bcrypt hash
            full_name="Login Test User",
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()
        
        # Test successful login with correct password
        login_data = {"email": "login.test@bubble.com", "password": password}
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data
        assert data["user"]["email"] == "login.test@bubble.com"
        
        # Test failed login with wrong password
        login_data["password"] = "wrong_password"
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
    
    def test_ai_friendly_response_format(self, client: TestClient):
        """Test authentication responses follow Sprint 1 AI-friendly format"""
        import uuid
        registration_data = {
            "email": f"ai.test.{uuid.uuid4().hex[:8]}@bubble.com",
            "password": "SecureFinance2025!@#",
            "full_name": "AI Test User"
        }
        
        response = client.post("/api/v1/auth/register", json=registration_data)
        assert response.status_code == 201
        
        data = response.json()
        
        # Verify AI-friendly structure
        required_fields = ["success", "access_token", "refresh_token", 
                         "token_type", "expires_in", "user", "message", "next_actions"]
        for field in required_fields:
            assert field in data, f"Missing AI-friendly field: {field}"
        
        # Verify next_actions for AI agent guidance
        assert isinstance(data["next_actions"], list)
        assert "verify_email" in data["next_actions"]
        assert "create_first_universe" in data["next_actions"]
        
        # Verify user data structure
        user_data = data["user"]
        assert "id" in user_data
        assert user_data["email"] == registration_data["email"]
        assert user_data["role"] == "user"
        assert user_data["subscription_tier"] == "free"


class TestPasswordValidationBehavior:
    """Test password validation behavior matches Sprint 1 requirements"""
    
    def test_weak_passwords_rejected_by_api(self, client: TestClient):
        """Test API rejects weak passwords according to business rules"""
        weak_passwords = [
            "short123",  # Too short
            "password123456789",  # Common pattern
            "alllowercase123!",  # No uppercase
            "ALLUPPERCASE123!",  # No lowercase
            "NoNumbers!@#$",  # No numbers
            "NoSpecialChars123",  # No special characters
        ]
        
        for weak_password in weak_passwords:
            registration_data = {
                "email": f"weak.{weak_password[:5]}@bubble.com",
                "password": weak_password,
                "full_name": "Weak Password Test"
            }
            
            response = client.post("/api/v1/auth/register", json=registration_data)
            assert response.status_code == 422, f"Weak password '{weak_password}' was accepted!"
            
            # Verify error message is informative
            error_data = response.json()
            assert "detail" in error_data
    
    def test_strong_passwords_accepted_by_api(self, client: TestClient):
        """Test API accepts strong passwords meeting all requirements"""
        strong_passwords = [
            "SecureFinance2025!@#",
            "MyStrongP@ssw0rd123",
            "Capital$Invest#2025!",
        ]
        
        import uuid
        for i, strong_password in enumerate(strong_passwords):
            registration_data = {
                "email": f"strong{i}.{uuid.uuid4().hex[:8]}@bubble.com",
                "password": strong_password,
                "full_name": f"Strong Password Test {i}"
            }
            
            response = client.post("/api/v1/auth/register", json=registration_data)
            assert response.status_code == 201, f"Strong password '{strong_password}' was rejected!"