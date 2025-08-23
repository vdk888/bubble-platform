from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from enum import Enum
from .base import BaseModel

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    PREMIUM = "premium"

class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro" 
    ENTERPRISE = "enterprise"

class User(BaseModel):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    subscription_tier = Column(SQLEnum(SubscriptionTier), default=SubscriptionTier.FREE, nullable=False)
    
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    universes = relationship("Universe", back_populates="owner", cascade="all, delete-orphan")
    strategies = relationship("Strategy", back_populates="owner", cascade="all, delete-orphan") 
    portfolios = relationship("Portfolio", back_populates="owner", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")