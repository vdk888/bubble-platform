from sqlalchemy import Column, String, Text, ForeignKey, JSON, Float, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
from enum import Enum
from datetime import datetime, timezone
from .base import BaseModel

class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class Order(BaseModel):
    __tablename__ = "orders"
    
    # Order identification
    broker_order_id = Column(String(100), index=True)  # ID from broker
    symbol = Column(String(20), nullable=False)
    
    # Order details
    order_type = Column(SQLEnum(OrderType), default=OrderType.MARKET, nullable=False)
    side = Column(SQLEnum(OrderSide), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float)  # For limit orders
    stop_price = Column(Float)  # For stop orders
    
    # Order status
    status = Column(SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False)
    filled_quantity = Column(Float, default=0.0)
    filled_price = Column(Float)
    
    # Timestamps
    submitted_at = Column(DateTime(timezone=True))
    filled_at = Column(DateTime(timezone=True))
    
    # Portfolio context
    portfolio_id = Column(String(36), ForeignKey("portfolios.id"), nullable=False)
    rebalancing_id = Column(String(36))  # Groups orders from same rebalancing
    
    # Additional data
    broker_data = Column(JSON)  # Raw broker response
    error_message = Column(Text)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="orders")
    executions = relationship("Execution", back_populates="order", cascade="all, delete-orphan")

class Execution(BaseModel):
    __tablename__ = "executions"
    
    # Execution identification
    broker_execution_id = Column(String(100), index=True)
    
    # Execution details
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    value = Column(Float, nullable=False)  # quantity * price
    commission = Column(Float, default=0.0)
    
    # Timestamps
    executed_at = Column(DateTime(timezone=True), nullable=False)
    
    # Order reference
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    
    # Additional data
    broker_data = Column(JSON)  # Raw execution data from broker
    
    # Relationships
    order = relationship("Order", back_populates="executions")