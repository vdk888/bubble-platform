"""
Tests for database models.
"""
import pytest
from sqlalchemy.orm import Session
from app.models.user import User, UserRole, SubscriptionTier
from app.models.universe import Universe
from app.models.strategy import Strategy, StrategyStatus
from app.models.portfolio import Portfolio
from app.models.chat import Conversation, ChatMessage

def test_create_user(db_session: Session):
    """Test creating a user model."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password_123",
        full_name="Test User"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.role == UserRole.USER
    assert user.subscription_tier == SubscriptionTier.FREE
    assert user.is_active is True
    assert user.created_at is not None
    assert user.updated_at is not None

def test_create_universe(db_session: Session):
    """Test creating a universe with owner relationship."""
    # Create user first
    user = User(
        email="test@example.com",
        hashed_password="hashed_password_123"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Create universe
    universe = Universe(
        name="Tech Stocks",
        description="Technology companies",
        symbols=["AAPL", "GOOGL", "MSFT"],
        owner_id=user.id
    )
    db_session.add(universe)
    db_session.commit()
    db_session.refresh(universe)
    
    assert universe.id is not None
    assert universe.name == "Tech Stocks"
    assert universe.symbols == ["AAPL", "GOOGL", "MSFT"]
    assert universe.owner_id == user.id
    assert universe.owner.email == "test@example.com"

def test_create_strategy(db_session: Session):
    """Test creating a strategy with relationships."""
    # Create user and universe first
    user = User(email="test@example.com", hashed_password="hash123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    universe = Universe(
        name="Test Universe",
        symbols=["AAPL", "GOOGL"],
        owner_id=user.id
    )
    db_session.add(universe)
    db_session.commit()
    db_session.refresh(universe)
    
    # Create strategy
    strategy = Strategy(
        name="RSI Strategy",
        description="RSI-based momentum strategy",
        indicator_config={"rsi_period": 14, "overbought": 70, "oversold": 30},
        allocation_rules={"method": "equal_weight"},
        universe_id=universe.id,
        owner_id=user.id
    )
    db_session.add(strategy)
    db_session.commit()
    db_session.refresh(strategy)
    
    assert strategy.id is not None
    assert strategy.name == "RSI Strategy"
    assert strategy.status == StrategyStatus.DRAFT
    assert strategy.universe_id == universe.id
    assert strategy.owner_id == user.id
    assert strategy.universe.name == "Test Universe"
    assert strategy.owner.email == "test@example.com"

def test_create_portfolio(db_session: Session):
    """Test creating a portfolio model."""
    # Create user first
    user = User(email="test@example.com", hashed_password="hash123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Create portfolio
    portfolio = Portfolio(
        name="Risk Parity Portfolio",
        description="Equal risk contribution portfolio",
        allocation_method="risk_parity",
        target_allocations={"AAPL": 0.25, "GOOGL": 0.25, "MSFT": 0.25, "AMZN": 0.25},
        total_value=100000.0,
        cash_balance=5000.0,
        owner_id=user.id
    )
    db_session.add(portfolio)
    db_session.commit()
    db_session.refresh(portfolio)
    
    assert portfolio.id is not None
    assert portfolio.name == "Risk Parity Portfolio"
    assert portfolio.total_value == 100000.0
    assert portfolio.cash_balance == 5000.0
    assert portfolio.owner_id == user.id

def test_create_conversation(db_session: Session):
    """Test creating a conversation with messages."""
    # Create user first
    user = User(email="test@example.com", hashed_password="hash123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Create conversation
    conversation = Conversation(
        title="Portfolio Discussion",
        user_id=user.id
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)
    
    # Create chat message
    message = ChatMessage(
        role="user",
        content="Show me my portfolio performance",
        conversation_id=conversation.id
    )
    db_session.add(message)
    db_session.commit()
    db_session.refresh(message)
    
    assert conversation.id is not None
    assert conversation.title == "Portfolio Discussion"
    assert conversation.user_id == user.id
    assert len(conversation.messages) == 1
    assert message.content == "Show me my portfolio performance"
    assert message.conversation_id == conversation.id