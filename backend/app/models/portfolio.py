from sqlalchemy import Column, String, Text, ForeignKey, JSON, Float, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime, timezone
from .base import BaseModel

class AllocationMethod(str, Enum):
    RISK_PARITY = "risk_parity"
    EQUAL_WEIGHT = "equal_weight"
    CUSTOM = "custom"
    MOMENTUM = "momentum"

class Portfolio(BaseModel):
    __tablename__ = "portfolios"
    
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Portfolio configuration
    allocation_method = Column(SQLEnum(AllocationMethod), default=AllocationMethod.RISK_PARITY)
    target_allocations = Column(JSON)  # Target allocation weights
    current_allocations = Column(JSON)  # Current actual allocations
    
    # Risk management
    rebalancing_threshold = Column(Float, default=0.05)  # 5% drift threshold
    max_single_allocation = Column(Float, default=0.4)   # 40% max allocation
    
    # Performance tracking
    total_value = Column(Float)
    daily_returns = Column(JSON)  # Daily return history
    performance_metrics = Column(JSON)  # Sharpe, volatility, etc.
    
    # Portfolio state
    cash_balance = Column(Float, default=0.0)
    last_rebalance_date = Column(DateTime(timezone=True))
    
    # Relationships
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="portfolios")
    
    allocations = relationship("PortfolioAllocation", back_populates="portfolio", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="portfolio")

class PortfolioAllocation(BaseModel):
    __tablename__ = "portfolio_allocations"
    
    # Portfolio and Strategy references
    portfolio_id = Column(String(36), ForeignKey("portfolios.id"), nullable=False)
    strategy_id = Column(String(36), ForeignKey("strategies.id"), nullable=False)
    
    # Allocation details
    target_weight = Column(Float, nullable=False)  # Target allocation weight
    current_weight = Column(Float, nullable=False)  # Current actual weight
    
    # Performance tracking for this allocation
    contribution_to_return = Column(Float)  # Performance attribution
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="allocations")
    strategy = relationship("Strategy", back_populates="portfolio_allocations")