# 📋 Development Navigation

**📄 Documentation Structure:**
- **[spec.md](./spec.md)** - Original product specification and system requirements
- **[jira.md](./jira.md)** - User stories and acceptance criteria organized by epics
- **[roadmap.md](./roadmap.md)** - Version roadmap (MVP → V1 → V2) with epic distribution
- **[plan_overview.md](./plan_overview.md)** - High-level architecture vision and microservices overview  
- **[plan_phased.md](./plan_phased.md)** - Detailed implementation plan with file structure and development phases
- **[plan_detailed.md](./plan_detailed.md)** - Complete technical specification with microservices architecture
- **[dev.md](./dev.md)** - Personal skill roadmap and learning path
- **[starting_point.md](./starting_point.md)** *(current)* - Foundation setup and first implementation phases

---

# 🚀 **BUBBLE PLATFORM - STARTING POINT IMPLEMENTATION**

## 🎯 **Strategic Overview**

This document provides the **exact roadmap** to build the Bubble Platform from zero to MVP, following Interface-First Design principles and ensuring bulletproof foundations for enterprise scalability.

### **Core Philosophy**
- **Interface First**: Define contracts before implementation
- **Domain-Driven**: Business logic drives technical decisions
- **AI-Native**: Conversational interface as first-class citizen
- **Production-Ready**: Built for scale from day one

---

## 📅 **PHASE 0: BULLETPROOF FOUNDATIONS** (Week 1)

### **Day 1: Strategic Architecture Decision**

Create the master plan that prevents 3 months of refactoring later:

```bash
mkdir bubble-platform && cd bubble-platform
touch docs/decisions/ADR-001-tech-stack.md
```

**docs/decisions/ADR-001-tech-stack.md**:
```markdown
# ADR-001: Technology Stack and Architecture Decisions

## Status: Accepted
Date: 2025-01-XX

## Context
Building an AI-native investment strategy automation platform requiring:
- Real-time data processing
- Complex financial calculations  
- Conversational AI interface
- Multi-broker execution
- Enterprise scalability path

## Decision
### Backend Stack
- **FastAPI + Python**: Async performance, great AI library ecosystem
- **PostgreSQL**: ACID compliance for financial data
- **Redis**: Caching and real-time features
- **SQLAlchemy + Alembic**: Type-safe ORM with migrations

### Frontend Stack  
- **React + TypeScript**: Component-based with type safety
- **Tailwind CSS**: Rapid UI development
- **Recharts**: Financial data visualization

### Architecture Evolution
- **Phase 1**: Monolithic FastAPI (rapid MVP)
- **Phase 2**: Service extraction to microservices
- **Phase 3**: Kubernetes orchestration

### AI Integration
- **Anthropic Claude**: Conversational interface
- **Tool Calling Architecture**: All platform APIs accessible via chat

## Consequences
- Rapid prototyping with Python/FastAPI
- Clear migration path to microservices
- AI-first design influences all service interfaces
- Production-ready from day one
```

### **Day 2: Project Structure Definition**

```bash
# Create the definitive project structure
mkdir -p backend/app/{core,api/v1,services,models,tests}
mkdir -p backend/app/services/{interfaces,implementations}
mkdir -p frontend/src/{components,pages,services,utils}
mkdir -p docs/{decisions,api,deployment}
mkdir -p infrastructure/{docker,kubernetes,terraform}

# Initialize core files
touch backend/app/main.py
touch backend/app/core/{__init__.py,config.py,database.py,security.py}
touch backend/app/services/interfaces/{__init__.py,base.py}
touch backend/requirements.txt
touch backend/Dockerfile
touch frontend/package.json
touch docker-compose.yml
touch .env.example
touch .gitignore
touch README.md
```

**File Structure**:
```
bubble-platform/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application entry
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic settings
│   │   │   ├── database.py            # PostgreSQL connection
│   │   │   ├── security.py            # JWT auth setup
│   │   │   └── events.py              # Application lifecycle
│   │   ├── api/v1/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                # Authentication endpoints
│   │   │   ├── universes.py           # Universe management
│   │   │   ├── strategies.py          # Strategy operations
│   │   │   ├── portfolios.py          # Portfolio management
│   │   │   ├── chat.py                # AI Agent interface
│   │   │   └── health.py              # Health checks
│   │   ├── services/
│   │   │   ├── interfaces/            # Abstract interfaces (contracts)
│   │   │   │   ├── auth.py
│   │   │   │   ├── data_provider.py
│   │   │   │   ├── universe.py
│   │   │   │   ├── screener.py
│   │   │   │   ├── strategy.py
│   │   │   │   ├── portfolio.py
│   │   │   │   ├── execution.py
│   │   │   │   └── ai_agent.py
│   │   │   └── implementations/       # Concrete implementations
│   │   ├── models/                    # SQLAlchemy domain models
│   │   │   ├── base.py               # Base model with common fields
│   │   │   ├── user.py               # User and authentication
│   │   │   ├── universe.py           # Asset universe management
│   │   │   ├── strategy.py           # Investment strategies
│   │   │   ├── portfolio.py          # Portfolio and allocations
│   │   │   ├── execution.py          # Orders and executions
│   │   │   └── chat.py               # AI conversation history
│   │   └── tests/
│   │       ├── unit/                 # Service unit tests
│   │       ├── integration/          # API integration tests
│   │       └── fixtures/             # Test data and mocks
│   ├── alembic/                      # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/               # Reusable UI components
│   │   │   ├── universe/             # Universe management UI
│   │   │   ├── strategy/             # Strategy builder
│   │   │   ├── portfolio/            # Portfolio dashboard
│   │   │   ├── chat/                 # AI Agent interface
│   │   │   └── charts/               # Financial visualizations
│   │   ├── pages/                    # Main application routes
│   │   ├── services/                 # API integration
│   │   ├── utils/                    # Utility functions
│   │   └── types/                    # TypeScript definitions
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── docs/
│   ├── decisions/                    # Architecture Decision Records
│   ├── api/                         # API documentation
│   └── deployment/                  # Deployment guides
├── infrastructure/
│   ├── docker/                      # Docker configurations
│   ├── kubernetes/                  # K8s manifests (future)
│   └── terraform/                   # Infrastructure as code (future)
├── docker-compose.yml               # Development environment
├── .env.example                     # Environment template
├── .gitignore
└── README.md
```

### **Day 3: Configuration & Environment Setup**

**backend/app/core/config.py**:
```python
from typing import Optional
from pydantic import BaseSettings, validator
import os

class Settings(BaseSettings):
    # Application
    app_name: str = "Bubble Platform"
    debug: bool = False
    environment: str = "development"
    secret_key: str
    
    # Database
    database_url: str
    database_test_url: Optional[str] = None
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # External APIs
    claude_api_key: str
    alpaca_api_key: str
    alpaca_secret_key: str
    yahoo_finance_api_key: Optional[str] = None
    
    # Authentication
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Business Logic
    rebalancing_threshold: float = 0.05
    max_single_allocation: float = 0.4
    paper_trading_enabled: bool = True
    
    # AI Agent
    max_conversation_history: int = 50
    ai_response_timeout: int = 30
    
    @validator('database_url')
    def validate_database_url(cls, v):
        if 'sqlite' in v and os.getenv('ENVIRONMENT') == 'production':
            raise ValueError('SQLite not allowed in production')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

**.env.example**:
```bash
# Application
SECRET_KEY=your-super-secret-key-change-in-production
ENVIRONMENT=development
DEBUG=true

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/bubble_dev
DATABASE_TEST_URL=postgresql://user:password@localhost:5432/bubble_test

# Redis
REDIS_URL=redis://localhost:6379

# External APIs
CLAUDE_API_KEY=your-claude-api-key
ALPACA_API_KEY=your-alpaca-key
ALPACA_SECRET_KEY=your-alpaca-secret
YAHOO_FINANCE_API_KEY=your-yahoo-key

# Business Settings
REBALANCING_THRESHOLD=0.05
MAX_SINGLE_ALLOCATION=0.4
PAPER_TRADING_ENABLED=true
```

### **Day 4: Database Foundation**

**backend/app/core/database.py**:
```python
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from .config import settings
import logging

# Create engine with proper configuration
if "sqlite" in settings.database_url:
    # Development with SQLite
    engine = create_engine(
        settings.database_url,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=settings.debug
    )
else:
    # Production with PostgreSQL
    engine = create_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=settings.debug
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Connection health check
async def check_database_connection() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        return True
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        return False
```

**backend/app/models/base.py**:
```python
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime, timezone
import uuid
from ..core.database import Base

class BaseModel(Base):
    __abstract__ = True
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, 
                       default=lambda: datetime.now(timezone.utc), 
                       onupdate=lambda: datetime.now(timezone.utc), 
                       nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower() + 's'
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
```

### **Day 5: Docker Development Environment**

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://bubble_user:bubble_pass@db:5432/bubble_dev
      - REDIS_URL=redis://redis:6379
      - ENVIRONMENT=development
      - DEBUG=true
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./backend:/app
      - /app/__pycache__
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: bubble_dev
      POSTGRES_USER: bubble_user
      POSTGRES_PASSWORD: bubble_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bubble_user -d bubble_dev"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

**backend/Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### **Day 6-7: Core Domain Models**

This is where we define the **business domain** that drives everything else.

**backend/app/models/user.py**:
```python
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
```

**backend/app/models/universe.py**:
```python
from sqlalchemy import Column, String, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from .base import BaseModel

class Universe(BaseModel):
    __tablename__ = "universes"
    
    name = Column(String(100), nullable=False)
    description = Column(Text)
    symbols = Column(JSON, nullable=False)  # List of asset symbols
    
    # Dynamic screening criteria
    screening_criteria = Column(JSON)  # Flexible screening rules
    last_screening_date = Column(DateTime(timezone=True))
    turnover_rate = Column(Float)  # Track universe evolution
    
    # Ownership
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="universes")
    
    # Relationships
    strategies = relationship("Strategy", back_populates="universe", cascade="all, delete-orphan")
    
    def get_symbols(self) -> List[str]:
        """Get current universe symbols"""
        return self.symbols if isinstance(self.symbols, list) else []
    
    def update_symbols(self, new_symbols: List[str]):
        """Update universe with turnover tracking"""
        if self.symbols:
            old_set = set(self.get_symbols())
            new_set = set(new_symbols)
            self.turnover_rate = len(old_set.symmetric_difference(new_set)) / len(old_set.union(new_set))
        self.symbols = new_symbols
        self.last_screening_date = datetime.now(timezone.utc)
```

**backend/app/models/strategy.py**:
```python
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
```

### **IndicatorService - Technical Indicators & Signal Generation**

```python
# ===== INDICATOR SERVICE IMPLEMENTATION =====

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class SignalType(Enum):
    SELL = -1
    HOLD = 0
    BUY = 1

@dataclass
class IndicatorConfig:
    """Configuration for technical indicators"""
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    momentum_period: int = 10

class IndicatorService:
    """Service for calculating technical indicators and generating signals"""
    
    def __init__(self, config: Optional[IndicatorConfig] = None):
        self.config = config or IndicatorConfig()
    
    def calculate_rsi(self, data: pd.DataFrame, period: int = None) -> pd.Series:
        """
        Calculate RSI indicator returning signals (-1, 0, 1)
        
        Args:
            data: DataFrame with OHLCV data
            period: RSI calculation period (default from config)
            
        Returns:
            Series with RSI signals: -1 (sell), 0 (hold), 1 (buy)
        """
        period = period or self.config.rsi_period
        
        # Calculate RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # Generate signals
        signals = pd.Series(SignalType.HOLD.value, index=data.index)
        signals[rsi < self.config.rsi_oversold] = SignalType.BUY.value
        signals[rsi > self.config.rsi_overbought] = SignalType.SELL.value
        
        return signals
    
    def calculate_macd(self, data: pd.DataFrame, fast: int = None, slow: int = None, signal: int = None) -> pd.Series:
        """
        Calculate MACD indicator returning signals (-1, 0, 1)
        
        Args:
            data: DataFrame with OHLCV data
            fast: Fast EMA period (default from config)
            slow: Slow EMA period (default from config)
            signal: Signal line EMA period (default from config)
            
        Returns:
            Series with MACD signals: -1 (sell), 0 (hold), 1 (buy)
        """
        fast = fast or self.config.macd_fast
        slow = slow or self.config.macd_slow
        signal_period = signal or self.config.macd_signal
        
        # Calculate MACD
        ema_fast = data['close'].ewm(span=fast).mean()
        ema_slow = data['close'].ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period).mean()
        
        # Generate signals on crossover
        signals = pd.Series(SignalType.HOLD.value, index=data.index)
        crossover = macd_line > signal_line
        signals[crossover & ~crossover.shift(1)] = SignalType.BUY.value  # Bullish crossover
        signals[~crossover & crossover.shift(1)] = SignalType.SELL.value  # Bearish crossover
        
        return signals
    
    def calculate_momentum(self, data: pd.DataFrame, period: int = None) -> pd.Series:
        """
        Calculate momentum indicator returning signals (-1, 0, 1)
        
        Args:
            data: DataFrame with OHLCV data
            period: Momentum calculation period (default from config)
            
        Returns:
            Series with momentum signals: -1 (sell), 0 (hold), 1 (buy)
        """
        period = period or self.config.momentum_period
        
        # Calculate momentum (rate of change)
        momentum = data['close'].pct_change(period)
        
        # Generate signals based on momentum thresholds
        signals = pd.Series(SignalType.HOLD.value, index=data.index)
        signals[momentum > 0.02] = SignalType.BUY.value  # 2% positive momentum
        signals[momentum < -0.02] = SignalType.SELL.value  # 2% negative momentum
        
        return signals
    
    def generate_composite_signals(self, data: pd.DataFrame, indicators: List[str], weights: Dict[str, float]) -> pd.Series:
        """
        Generate composite signals from multiple indicators
        
        Args:
            data: DataFrame with OHLCV data
            indicators: List of indicator names to combine
            weights: Dict of indicator weights (must sum to 1.0)
            
        Returns:
            Series with composite signals: -1 (sell), 0 (hold), 1 (buy)
        """
        if abs(sum(weights.values()) - 1.0) > 0.001:
            raise ValueError("Indicator weights must sum to 1.0")
        
        composite_score = pd.Series(0.0, index=data.index)
        
        for indicator in indicators:
            if indicator == 'rsi':
                signals = self.calculate_rsi(data)
            elif indicator == 'macd':
                signals = self.calculate_macd(data)
            elif indicator == 'momentum':
                signals = self.calculate_momentum(data)
            else:
                raise ValueError(f"Unknown indicator: {indicator}")
            
            composite_score += signals * weights[indicator]
        
        # Convert composite score to discrete signals
        final_signals = pd.Series(SignalType.HOLD.value, index=data.index)
        final_signals[composite_score > 0.5] = SignalType.BUY.value
        final_signals[composite_score < -0.5] = SignalType.SELL.value
        
        return final_signals
    
    def validate_data_freshness(self, data: pd.DataFrame, max_age_minutes: int = 15) -> bool:
        """
        Validate that market data is fresh enough for signal generation
        
        Args:
            data: DataFrame with timestamp index
            max_age_minutes: Maximum age in minutes
            
        Returns:
            True if data is fresh enough, False otherwise
        """
        if data.empty:
            return False
        
        latest_timestamp = data.index[-1]
        current_time = pd.Timestamp.now()
        age_minutes = (current_time - latest_timestamp).total_seconds() / 60
        
        return age_minutes <= max_age_minutes

# ===== INDICATOR API ENDPOINTS =====

@app.route('/api/v1/indicators/default', methods=['GET'])
@auth_required
def get_default_indicators():
    """Get default indicator configurations"""
    config = IndicatorConfig()
    return jsonify({
        "rsi": {
            "period": config.rsi_period,
            "overbought": config.rsi_overbought,
            "oversold": config.rsi_oversold
        },
        "macd": {
            "fast": config.macd_fast,
            "slow": config.macd_slow,
            "signal": config.macd_signal
        },
        "momentum": {
            "period": config.momentum_period
        }
    })

@app.route('/api/v1/indicators/calculate', methods=['POST'])
@auth_required
def calculate_indicators():
    """Calculate indicators for given market data"""
    data = request.get_json()
    
    # Validate required fields
    if 'market_data' not in data or 'indicators' not in data:
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        # Convert market data to DataFrame
        df = pd.DataFrame(data['market_data'])
        df.index = pd.to_datetime(df['timestamp'])
        
        # Initialize service
        indicator_service = IndicatorService()
        
        # Validate data freshness
        if not indicator_service.validate_data_freshness(df):
            return jsonify({"error": "Market data too old for reliable signals"}), 400
        
        results = {}
        
        # Calculate requested indicators
        for indicator_name in data['indicators']:
            if indicator_name == 'rsi':
                results['rsi'] = indicator_service.calculate_rsi(df).to_list()
            elif indicator_name == 'macd':
                results['macd'] = indicator_service.calculate_macd(df).to_list()
            elif indicator_name == 'momentum':
                results['momentum'] = indicator_service.calculate_momentum(df).to_list()
            else:
                return jsonify({"error": f"Unknown indicator: {indicator_name}"}), 400
        
        return jsonify({
            "success": True,
            "indicators": results,
            "timestamp": pd.Timestamp.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/signals/generate', methods=['POST'])
@auth_required
def generate_signals():
    """Generate composite signals from multiple indicators"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['market_data', 'indicators', 'weights']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        # Convert market data to DataFrame
        df = pd.DataFrame(data['market_data'])
        df.index = pd.to_datetime(df['timestamp'])
        
        # Initialize service
        indicator_service = IndicatorService()
        
        # Generate composite signals
        signals = indicator_service.generate_composite_signals(
            df, 
            data['indicators'], 
            data['weights']
        )
        
        return jsonify({
            "success": True,
            "signals": signals.to_list(),
            "signal_mapping": {
                "-1": "SELL",
                "0": "HOLD", 
                "1": "BUY"
            },
            "timestamp": pd.Timestamp.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

### **Day 8: Service Interfaces Definition**

This is the **most critical step** - defining contracts before any implementation.

**backend/app/services/interfaces/base.py**:
```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from datetime import datetime
from pydantic import BaseModel

T = TypeVar('T')

class ServiceResult(Generic[T], BaseModel):
    """Standard service response wrapper"""
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}

class BaseService(ABC):
    """Base service interface with common patterns"""
    
    @abstractmethod
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Service health status"""
        pass
```

**backend/app/services/interfaces/data_provider.py**:
```python
from abc import abstractmethod
from typing import List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel
from .base import BaseService, ServiceResult

class MarketData(BaseModel):
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float  
    close: float
    volume: int
    adjusted_close: Optional[float] = None

class AssetInfo(BaseModel):
    symbol: str
    name: str
    sector: str
    industry: str
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None

class IDataProvider(BaseService):
    """Interface for market data providers (Yahoo Finance, Alpha Vantage, etc.)"""
    
    @abstractmethod
    async def fetch_historical_data(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        interval: str = "1d"
    ) -> ServiceResult[Dict[str, List[MarketData]]]:
        """Fetch historical price data"""
        pass
    
    @abstractmethod
    async def fetch_real_time_data(
        self, 
        symbols: List[str]
    ) -> ServiceResult[Dict[str, MarketData]]:
        """Fetch current market data"""
        pass
    
    @abstractmethod  
    async def fetch_asset_info(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, AssetInfo]]:
        """Fetch fundamental asset information"""
        pass
    
    @abstractmethod
    async def search_assets(
        self,
        query: str,
        limit: int = 10
    ) -> ServiceResult[List[AssetInfo]]:
        """Search for assets by name or symbol"""
        pass
```

**backend/app/services/interfaces/ai_agent.py**:
```python
from abc import abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum
from .base import BaseService, ServiceResult

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}

class ToolCall(BaseModel):
    name: str
    parameters: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    tool_calls: List[ToolCall] = []
    charts: List[Dict[str, Any]] = []
    tables: List[Dict[str, Any]] = []
    requires_confirmation: bool = False
    confirmation_data: Optional[Dict[str, Any]] = None

class UserContext(BaseModel):
    user_id: str
    conversation_id: str
    universes: List[Dict[str, Any]] = []
    strategies: List[Dict[str, Any]] = []
    portfolios: List[Dict[str, Any]] = []
    preferences: Dict[str, Any] = {}

class IAIAgentService(BaseService):
    """Interface for AI Agent conversational capabilities"""
    
    @abstractmethod
    async def process_message(
        self,
        message: str,
        user_context: UserContext,
        conversation_history: List[ChatMessage]
    ) -> ServiceResult[ChatResponse]:
        """Process user message and generate response with tool calls"""
        pass
    
    @abstractmethod
    async def execute_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        user_context: UserContext
    ) -> ServiceResult[Dict[str, Any]]:
        """Execute a specific tool call"""
        pass
    
    @abstractmethod
    async def get_available_tools(
        self,
        user_context: UserContext
    ) -> ServiceResult[List[Dict[str, str]]]:
        """Get list of available tools for user"""
        pass
    
    @abstractmethod
    async def confirm_critical_action(
        self,
        action_type: str,
        action_data: Dict[str, Any],
        user_context: UserContext
    ) -> ServiceResult[bool]:
        """Handle user confirmation for critical actions"""
        pass
```

---

## 📅 **PHASE 1: CORE SERVICES IMPLEMENTATION** (Weeks 2-4)

### **Week 2: Authentication & Health Foundation**

**Implementation Order (Critical Dependencies First)**:

1. **Health Check System** - Debug infrastructure early
2. **Authentication Service** - Everything depends on user context
3. **Database Models** - Domain foundation
4. **Basic API Endpoints** - Test the stack

**backend/app/main.py**:
```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import settings
from .core.database import engine, Base
from .api.v1 import auth, health, universes, strategies, portfolios, chat

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting {settings.app_name}")
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    print(f"Shutting down {settings.app_name}")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AI-Native Investment Strategy Automation Platform",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(universes.router, prefix="/api/v1/universes", tags=["universes"])
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["strategies"])
app.include_router(portfolios.router, prefix="/api/v1/portfolios", tags=["portfolios"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["ai-agent"])

@app.get("/")
async def root():
    return {
        "message": "Bubble Platform API",
        "version": "1.0.0",
        "environment": settings.environment
    }
```

**backend/app/api/v1/health.py**:
```python
from fastapi import APIRouter, status
from datetime import datetime, timezone
from ...core.database import check_database_connection
import redis
from ...core.config import settings

router = APIRouter()

@router.get("/")
async def health_check():
    """Comprehensive health check"""
    health_data = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "environment": settings.environment
    }
    
    # Check database
    db_healthy = await check_database_connection()
    health_data["database"] = "healthy" if db_healthy else "unhealthy"
    
    # Check Redis
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        health_data["redis"] = "healthy"
    except Exception:
        health_data["redis"] = "unhealthy"
    
    # Overall status
    overall_healthy = db_healthy and health_data["redis"] == "healthy"
    health_data["status"] = "healthy" if overall_healthy else "unhealthy"
    
    status_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return health_data
```

### **Week 3: Data Pipeline & Universe Service**

Implement the **data foundation** that everything else depends on:

**backend/app/services/implementations/yahoo_data_provider.py**:
```python
import yfinance as yf
from typing import List, Dict
from datetime import date
from ..interfaces.data_provider import IDataProvider, MarketData, AssetInfo, ServiceResult

class YahooDataProvider(IDataProvider):
    """Yahoo Finance implementation of data provider"""
    
    async def fetch_historical_data(
        self,
        symbols: List[str], 
        start_date: date,
        end_date: date,
        interval: str = "1d"
    ) -> ServiceResult[Dict[str, List[MarketData]]]:
        try:
            result = {}
            for symbol in symbols:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(start=start_date, end=end_date, interval=interval)
                
                market_data = []
                for date_idx, row in hist.iterrows():
                    market_data.append(MarketData(
                        symbol=symbol,
                        timestamp=date_idx,
                        open=row['Open'],
                        high=row['High'],
                        low=row['Low'],
                        close=row['Close'],
                        volume=int(row['Volume']),
                        adjusted_close=row.get('Adj Close')
                    ))
                
                result[symbol] = market_data
            
            return ServiceResult(success=True, data=result)
            
        except Exception as e:
            return ServiceResult(success=False, error=str(e))
    
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        try:
            # Test with a simple query
            ticker = yf.Ticker("AAPL")
            info = ticker.info
            return ServiceResult(success=True, data={"provider": "yahoo_finance", "test_symbol": "AAPL"})
        except Exception as e:
            return ServiceResult(success=False, error=str(e))
```

### **Week 4: Strategy Service & AI Agent Integration**

**backend/app/services/implementations/claude_ai_agent.py**:
```python
import anthropic
from typing import List, Dict, Any
from ..interfaces.ai_agent import IAIAgentService, ChatResponse, UserContext, ChatMessage, ToolCall, ServiceResult
from ...core.config import settings

class ClaudeAIAgent(IAIAgentService):
    """Claude-powered AI agent implementation"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.claude_api_key)
        self.tools = self._define_tools()
    
    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define available tools for Claude"""
        return [
            {
                "name": "create_universe",
                "description": "Create a new investment universe with specified symbols",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "symbols": {"type": "array", "items": {"type": "string"}},
                        "description": {"type": "string"}
                    },
                    "required": ["name", "symbols"]
                }
            },
            {
                "name": "run_backtest", 
                "description": "Run a backtest for a strategy",
                "input_schema": {
                    "type": "object", 
                    "properties": {
                        "strategy_id": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"}
                    },
                    "required": ["strategy_id", "start_date", "end_date"]
                }
            },
            {
                "name": "rebalance_portfolio",
                "description": "Trigger portfolio rebalancing - REQUIRES CONFIRMATION",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "portfolio_id": {"type": "string"},
                        "allocation_method": {"type": "string", "enum": ["risk_parity", "equal_weight", "custom"]}
                    },
                    "required": ["portfolio_id"]
                }
            }
        ]
    
    async def process_message(
        self,
        message: str,
        user_context: UserContext,
        conversation_history: List[ChatMessage]
    ) -> ServiceResult[ChatResponse]:
        try:
            # Build conversation context for Claude
            messages = []
            for msg in conversation_history[-10:]:  # Last 10 messages
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            messages.append({"role": "user", "content": message})
            
            # System prompt with user context
            system_prompt = f"""You are an AI assistant for the Bubble Platform investment management system.
            
User Context:
- User ID: {user_context.user_id}
- Available Universes: {len(user_context.universes)}
- Active Strategies: {len(user_context.strategies)}
- Portfolios: {len(user_context.portfolios)}

You have access to tools for:
- Creating and managing investment universes
- Running backtests and analyzing performance
- Portfolio management and rebalancing
- Data visualization and reporting

CRITICAL SAFETY RULES:
- ALWAYS require explicit confirmation for financial actions (rebalancing, order placement)
- Provide clear summaries of what actions will be taken
- Show estimated costs and impacts before execution
- Be transparent about risks and limitations

Available tools: {[tool['name'] for tool in self.tools]}
"""

            response = await self.client.messages.create(
                model="claude-3-sonnet-20241022",
                max_tokens=2000,
                system=system_prompt,
                messages=messages,
                tools=self.tools
            )
            
            # Process response and tool calls
            chat_response = ChatResponse(
                message=response.content[0].text if response.content else "",
                tool_calls=[],
                requires_confirmation=self._requires_confirmation(response)
            )
            
            # Handle tool calls if present
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_result = await self.execute_tool_call(
                        tool_call.name,
                        tool_call.input,
                        user_context
                    )
                    
                    chat_response.tool_calls.append(ToolCall(
                        name=tool_call.name,
                        parameters=tool_call.input,
                        result=tool_result.data if tool_result.success else None,
                        error=tool_result.error if not tool_result.success else None
                    ))
            
            return ServiceResult(success=True, data=chat_response)
            
        except Exception as e:
            return ServiceResult(success=False, error=str(e))
    
    def _requires_confirmation(self, response) -> bool:
        """Check if response contains critical financial actions"""
        critical_actions = ["rebalance_portfolio", "place_order", "modify_allocation"]
        if hasattr(response, 'tool_calls'):
            return any(tool.name in critical_actions for tool in response.tool_calls)
        return False
```

---

## 🎯 **SUCCESS METRICS & VALIDATION**

### **Week 1 Success Criteria**
- ✅ Complete project structure created
- ✅ Docker environment running smoothly  
- ✅ Database connection established
- ✅ Health check endpoints responding
- ✅ All configuration properly externalized

### **Week 2-4 Success Criteria**
- ✅ User registration and JWT authentication working
- ✅ Basic universe creation and management
- ✅ Market data fetching from Yahoo Finance
- ✅ Simple AI chat interface responding
- ✅ Database models and migrations working
- ✅ API documentation auto-generated

### **MVP Readiness Checklist**
- ✅ Full user authentication flow
- ✅ Universe creation with manual asset selection
- ✅ Basic strategy configuration
- ✅ Simple backtesting capability
- ✅ AI agent responding to basic queries
- ✅ Docker deployment working
- ✅ Basic monitoring and health checks

---

## 🚀 **IMMEDIATE NEXT STEPS**

### **Tomorrow Morning - Start Here**:

```bash
# 1. Create the foundation
mkdir bubble-platform && cd bubble-platform
mkdir -p backend/app/{core,api/v1,services/{interfaces,implementations},models,tests}
mkdir -p frontend/src/{components,pages,services}
mkdir -p docs/decisions

# 2. Create key files
touch backend/app/main.py
touch backend/app/core/{config.py,database.py}
touch backend/app/services/interfaces/{base.py,data_provider.py,ai_agent.py}
touch backend/requirements.txt
touch docker-compose.yml
touch .env.example

# 3. Initialize git
git init
echo "node_modules/\n__pycache__/\n*.pyc\n.env\n.venv/\n*.db" > .gitignore
git add .
git commit -m "🚀 Initial Bubble Platform structure with Interface-First architecture"

# 4. Start development environment
cp .env.example .env
# Edit .env with your API keys
docker-compose up -d
```

### **This Week's Focus**
1. **Monday-Tuesday**: Complete Phase 0 foundation setup
2. **Wednesday-Thursday**: Implement health checks and basic FastAPI structure  
3. **Friday**: Test full development environment and fix any issues
4. **Weekend**: Plan Week 2 authentication implementation

### **Key Success Principles**
- **Interface First**: Define contracts before implementation
- **Test Early**: Health checks and basic functionality first
- **Iterate Fast**: Get something working quickly, then enhance
- **Production Mindset**: Build with scalability and maintainability from day one

This foundation will support the entire Bubble Platform evolution from MVP through enterprise microservices architecture. The Interface-First approach ensures clean service boundaries and easy testing, while the AI-native design makes conversational interaction a first-class citizen from day one.

**Start building tomorrow - you have a bulletproof plan! 🚀**

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create starting_point.md with detailed foundation and first phase plan", "status": "completed"}]