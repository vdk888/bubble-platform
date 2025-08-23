from sqlalchemy import Column, String, Text, ForeignKey, JSON, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum
from .base import BaseModel

class StrategyStatus(str, Enum):
    DRAFT = "draft"
    BACKTESTING = "backtesting"
    VALIDATED = "validated"
    ACTIVE = "active"
    PAUSED = "paused"

class Strategy(BaseModel):
    __tablename__ = "strategies"
    
    name = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(SQLEnum(StrategyStatus), default=StrategyStatus.DRAFT)
    
    # Strategy configuration
    indicator_config = Column(JSON, nullable=False)  # Indicator parameters
    allocation_rules = Column(JSON, nullable=False)  # How to weight assets
    
    # Performance tracking
    backtest_results = Column(JSON)  # Historical performance metrics
    live_performance = Column(JSON)  # Real-time performance data
    
    # Risk metrics
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float)
    volatility = Column(Float)
    
    # Relationships
    universe_id = Column(String(36), ForeignKey("universes.id"), nullable=False)
    universe = relationship("Universe", back_populates="strategies")
    
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="strategies")
    
    portfolio_allocations = relationship("PortfolioAllocation", back_populates="strategy")