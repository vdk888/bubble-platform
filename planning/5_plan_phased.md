# 📋 Development Navigation

**📄 Documentation Structure:**
- **[spec.md](./spec.md)** - Original product specification and system requirements
- **[jira.md](./jira.md)** - User stories and acceptance criteria organized by epics
- **[roadmap.md](./roadmap.md)** - Version roadmap (MVP → V1 → V2) with epic distribution
- **[plan_overview.md](./plan_overview.md)** - High-level architecture vision and microservices overview  
- **[plan_phased.md](./plan_phased.md)** *(current)* - Detailed implementation plan with file structure and development phases
- **[plan_detailed.md](./plan_detailed.md)** - Complete technical specification with microservices architecture

---

# 🚀 **BUBBLE PLATFORM - DETAILED IMPLEMENTATION PLAN**

## 🎯 **Architecture Overview & Product Alignment**

**Core Product Flow**: Universe Definition → Indicators & Signals → Portfolio Strategy → Risk Parity Master Portfolio → Broker Execution

**Technical Approach**: Start with monolithic Flask/FastAPI backend + React frontend, evolve to microservices in v2 for scalability.

---

## 📋 **MVP PHASE - Core Automation + Basic Visualization**

### **🏗️ Backend Architecture (MVP)**
**Phase**: MVP  
**Approach**: Monolithic API with clear service separation for future microservice migration

#### **📁 `/backend` - Main Application**
- **Phase**: MVP
- **Tech Stack**: FastAPI + SQLAlchemy + PostgreSQL
- **Structure**:
  ```
  /backend
    /app
      /api/v1
        /universes      # Universe management endpoints
        /indicators     # Signal generation endpoints  
        /strategies     # Portfolio strategy endpoints
        /master         # Master portfolio endpoints
        /execution      # Basic broker integration
        /chat           # AI Agent chatbot endpoints
      /core
        /models         # SQLAlchemy models
        /services       # Business logic services
        /utils          # Shared utilities
      /backtest         # Backtesting engine
    /tests              # Unit and integration tests
    requirements.txt
    Dockerfile
  ```

#### **📊 Core Services (MVP)**

**📁 `/backend/app/services/universe_service.py`**
- **Phase**: MVP → Enhanced in Sprint 2.5
- **Features**: 
  - Manual asset selection (stocks, ETFs, bonds)
  - Basic CRUD operations
  - Asset validation and metadata storage
  - **Temporal universe snapshots with point-in-time composition tracking (Sprint 2.5 core)**
  - **Historical universe evolution timeline for survivorship bias elimination (Sprint 2.5 core)**
- **API Endpoints**: `GET/POST/PUT/DELETE /api/v1/universes`
- **Temporal APIs**: `/universes/{id}/timeline`, `/universes/{id}/snapshots`, `/universes/{id}/composition/{date}` (Sprint 2.5 core)

**📁 `/backend/app/services/indicator_service.py`**
- **Phase**: MVP  
- **Features**:
  - Basic momentum indicators (SMA, RSI, MACD)
  - Simple ROIC filtering
  - Buy/sell signal generation
- **API Endpoints**: `GET/POST /api/v1/indicators`, `/api/v1/signals`

**📁 `/backend/app/services/strategy_service.py`**
- **Phase**: MVP
- **Features**:
  - Portfolio weight calculation
  - Basic backtesting (vectorized approach)
  - Performance metrics (CAGR, Sharpe, max drawdown)
- **API Endpoints**: `GET/POST /api/v1/strategies`, `/api/v1/backtests`

**📁 `/backend/app/services/master_portfolio_service.py`**
- **Phase**: MVP
- **Features**:
  - Risk parity allocation algorithm
  - Strategy aggregation
  - **Daily rebalancing scheduler and triggers**
  - **Rebalancing calculator and order generation**
  - **Drift threshold monitoring**
- **API Endpoints**: `GET/POST /api/v1/master-portfolio`, `/api/v1/allocations`, `/api/v1/rebalance`

**📁 `/backend/app/services/execution_service.py`**
- **Phase**: MVP
- **Features**:
  - Basic Alpaca integration
  - Order generation and submission
  - Execution status tracking
- **API Endpoints**: `POST /api/v1/orders`, `GET /api/v1/executions`

**📁 `/backend/app/services/ai_agent_service.py`**
- **Phase**: MVP 
- **Features**:
  - Claude API integration with tool calling
  - Natural language to API translation
  - Custom tool definitions for all platform APIs
  - Conversation history and context management
  - Chart generation and visualization commands
  - Safety layer for critical actions (rebalancing, order execution)
- **API Endpoints**: `POST /api/v1/chat`, `GET /api/v1/chat/history`, `WebSocket /ws/chat`

#### **📁 `/backend/app/core/models.py`**
- **Phase**: MVP
- **Models**:
  ```python
  User, Universe, Asset, Indicator, Strategy, 
  MasterPortfolio, Order, Execution, PerformanceSnapshot,
  Conversation, ChatMessage, ToolCall
  ```

### **🌐 Frontend Application (MVP)**
**Phase**: MVP
**Tech Stack**: React + TypeScript + Tailwind CSS

#### **📁 `/frontend` - React Application**
```
/frontend
  /src
    /components
      /common           # Shared UI components
      /universe         # Universe management UI
      /indicators       # Indicator configuration UI
      /strategy         # Strategy builder UI  
      /master           # Master portfolio dashboard
      /charts           # Basic chart components
      /chat             # AI Agent chat interface
    /pages              # Main application pages
    /services           # API integration
    /utils              # Frontend utilities
  /public
  package.json
  Dockerfile
```

**📁 `/frontend/src/pages/UniversePage.tsx`**
- **Phase**: MVP → Enhanced in Sprint 2.5
- **Features**: Manual asset selection, universe CRUD, basic asset table
- **🚀 NEW: Universe timeline table showing composition evolution by date/period**
- **🚀 NEW: Turnover analysis visualization with asset flow tracking**
- **🚀 NEW: Point-in-time universe composition viewer with historical drill-down**

**📁 `/frontend/src/pages/IndicatorsPage.tsx`**
- **Phase**: MVP  
- **Features**: Indicator parameter setting, basic signal visualization

**📁 `/frontend/src/pages/StrategyPage.tsx`**
- **Phase**: MVP
- **Features**: Weight configuration, backtest results display, basic equity curve

**📁 `/frontend/src/pages/MasterPortfolioPage.tsx`**
- **Phase**: MVP
- **Features**: 
  - Allocation overview and current weights
  - Basic performance tracking and metrics
  - **Rebalancing controls and triggers**
  - **Order preview and execution status**
  - **Rebalancing history and timeline**

**📁 `/frontend/src/components/charts/BasicChart.tsx`**
- **Phase**: MVP
- **Features**: Simple line charts for equity curves, basic overlays for signals

**📁 `/frontend/src/components/chat/ChatInterface.tsx`**
- **Phase**: MVP
- **Features**: 
  - Natural language conversation interface
  - Interface mode toggle (Traditional UI ↔ Chat)
  - Real-time chart generation and display
  - Action confirmation dialogs for critical operations
  - Conversation history and context
  - Multi-modal responses (text, charts, tables)

**📁 `/frontend/src/pages/ChatPage.tsx`**
- **Phase**: MVP
- **Features**: Full-screen conversational interface as alternative to traditional UI

#### **📁 `/backend/app/core/scheduler.py`**
- **Phase**: MVP
- **Features**: 
  - **Daily rebalancing automation (cron job)**
  - **Portfolio drift monitoring**
  - **Automated order generation and submission**
  - **Rebalancing execution status tracking**
  - **Basic notification system (email)**

#### **📁 `/backend/app/core/rebalancing/`**
- **Phase**: MVP
- **Structure**:
  ```
  /rebalancing
    scheduler.py        # Daily rebalancing schedule
    calculator.py       # Order calculation logic  
    trigger.py          # Drift-based triggers
    executor.py         # Order execution orchestration
  ```

---

## 📈 **V1 PHASE - Advanced Universe Filtering + Live Monitoring**

### **🔍 Enhanced Universe Management (V1)**

**📁 `/backend/app/services/screener_service.py`**
- **Phase**: V1
- **Features**:
  - Multi-metric screening (P/E, ROIC, market cap, sector)
  - Dynamic universe updates
  - Screening result caching
- **New API Endpoints**: `/api/v1/screener`, `/api/v1/screener/results`

**📁 `/frontend/src/components/universe/AdvancedScreener.tsx`**
- **Phase**: V1
- **Features**: Multi-filter interface, real-time screening results, drag-and-drop asset management

### **📊 Enhanced Indicators & Visualization (V1)**

**📁 `/backend/app/services/market_data_service.py`**
- **Phase**: V1
- **Features**: Real-time data integration, triple-provider sources (OpenBB, Yahoo Finance, Alpha Vantage), professional-grade fundamental data, economic indicators

**📁 `/frontend/src/components/charts/InteractiveChart.tsx`**
- **Phase**: V1
- **Features**: Advanced charting with overlays, zoom, signal markers, multiple timeframes

### **📈 Live Performance Tracking (V1)**

**📁 `/backend/app/services/performance_service.py`**
- **Phase**: V1
- **Features**: 
  - Live portfolio tracking
  - Performance attribution
  - Risk metrics calculation

**📁 `/frontend/src/pages/LivePerformancePage.tsx`**
- **Phase**: V1
- **Features**: Real-time dashboards, performance comparison charts, rolling Sharpe visualization

### **🔔 Enhanced Notifications (V1)**

**📁 `/backend/app/services/notification_service.py`**
- **Phase**: V1
- **Features**: Multi-channel notifications (Email, Telegram), custom alert rules

### **🤖 Advanced AI Agent Features (V1)**

**📁 `/backend/app/services/ai_agent_service.py` - V1 Enhancements**
- **Phase**: V1
- **Features**:
  - Advanced workflow orchestration (multi-step strategy creation)
  - Proactive insights and recommendations
  - Advanced context management and user preference learning
  - Integration with alternative data sources (OpenBB economic data, news sentiment, analyst estimates)
  - Enhanced visualization generation capabilities

**📁 `/frontend/src/components/chat/` - V1 Enhancements**
- **Phase**: V1
- **Features**: 
  - Advanced interface modes (sidebar, overlay, fullscreen)
  - Quick action suggestions based on user patterns
  - Enhanced conversation search and history management
  - Smart template messages and command shortcuts

---

## 🏢 **V2 PHASE - Full Product Polish + Payments & Scalability**

### **💳 Payment Integration (V2)**

**📁 `/backend/app/services/billing_service.py`**
- **Phase**: V2
- **Features**: Stripe integration, subscription management, usage quotas

**📁 `/frontend/src/pages/BillingPage.tsx`**
- **Phase**: V2
- **Features**: Subscription management, payment forms, usage tracking

### **🔧 API Modularization (V2)**
**Phase**: V2 - Microservice Migration

**📁 `/services/universe-service`**
- **Phase**: V2
- **Migration**: Extract universe management to dedicated service

**📁 `/services/strategy-service`**
- **Phase**: V2
- **Migration**: Extract strategy logic to dedicated service

**📁 `/services/execution-service`**
- **Phase**: V2
- **Migration**: Extract broker integration to dedicated service

**📁 `/services/data-service`**
- **Phase**: V2
- **Migration**: Extract market data management to dedicated service

### **☸️ Infrastructure & Deployment (V2)**

**📁 `/infrastructure`**
- **Phase**: V2
- **Structure**:
  ```
  /infrastructure
    /terraform          # Infrastructure as code
    /kubernetes         # K8s manifests
    /docker-compose     # Local development
    /monitoring         # Prometheus, Grafana configs
  ```

**📁 `/infrastructure/kubernetes`**
- **Phase**: V2
- **Features**: Production-ready K8s deployment, auto-scaling, service mesh

**📁 `/infrastructure/terraform`**
- **Phase**: V2
- **Features**: AWS/GCP infrastructure provisioning, RDS, ElastiCache setup

### **🔒 Enterprise Features (V2)**

**📁 `/backend/app/core/auth.py`**
- **Phase**: V2 Enhancement
- **Features**: OAuth integration, 2FA, RBAC, multi-tenancy

**📁 `/backend/app/core/cache.py`**
- **Phase**: V2
- **Features**: Redis caching, intelligent invalidation, performance optimization

---

## 📁 **Shared Infrastructure & Configuration**

### **Database (All Phases)**

**📁 `/database`**
- **Phase**: MVP (basic), V1 (enhanced), V2 (optimized)
- **Structure**:
  ```
  /database
    /migrations         # Alembic migrations
    /seeds             # Development data
    init_db.sql        # Initial schema
  ```

### **Development & Testing**

**📁 `/tests`**
- **Phase**: MVP
- **Structure**:
  ```
  /tests
    /unit              # Unit tests for services
    /integration       # API integration tests  
    /e2e              # End-to-end tests
  ```

**📁 `/docs`**
- **Phase**: V1
- **Features**: API documentation, architecture docs, deployment guides

### **Configuration & Deployment**

**📁 `/docker-compose.yml`**
- **Phase**: MVP
- **Features**: Local development environment

**📁 `/.github/workflows`**
- **Phase**: V1
- **Features**: CI/CD pipeline, automated testing, deployment

**📁 `/scripts`**
- **Phase**: MVP
- **Features**: Setup scripts, data migration utilities

---

## 🎯 **Implementation Priority Matrix**

### **MVP Critical Path**
1. **Backend API Foundation** → Universe, Indicators, Strategy, Master Portfolio services
2. **AI Agent Service** → Claude integration with tool calling for all platform APIs
3. **Basic Frontend** → Core pages with simple charts + Chat interface
4. **Database Schema** → Core models and relationships (including chat models)
5. **Basic Execution** → Alpaca integration for order submission
6. **Daily Automation** → **Complete rebalancing workflow (scheduler → drift detection → order calculation → execution → notifications)**
7. **AI Safety Layer** → Critical action confirmations and audit logging

### **V1 Enhancement Path**
1. **Advanced Screener** → Multi-metric filtering
2. **Live Data Integration** → Real-time market data
3. **Enhanced Charts** → Interactive visualization
4. **Performance Tracking** → Live monitoring dashboard
5. **Advanced AI Features** → Workflow orchestration, proactive insights, enhanced visualizations

### **V2 Scale Path**
1. **Microservice Migration** → Service separation
2. **Payment Integration** → Stripe billing
3. **Infrastructure** → Kubernetes deployment
4. **Enterprise Features** → Multi-tenancy, advanced security

---

## 🔄 **Migration Strategy**

**MVP → V1**: Enhance existing monolith with new features while maintaining API compatibility

**V1 → V2**: Gradual microservice extraction using strangler fig pattern, maintaining backward compatibility

This plan ensures rapid MVP delivery while providing a clear evolution path toward a scalable SaaS platform.

---

## 🎯 **MIGRATION PATH TO FULL ENTERPRISE SAAS**

Your original `plan_detailed.md` is the **ultimate target architecture** - a comprehensive enterprise SaaS platform with:

### **🏗️ Full Microservices Architecture** (Target State)
- **7 Core Services**: Auth, Billing, Pocket Factory, Master Portfolio, Execution, Data, Notification, **AI Agent**
- **Advanced Universe Screening**: Dynamic ROIC-based filtering, sector analysis, turnover tracking
- **AI-First Interface**: Conversational platform management with comprehensive tool calling
- **Alternative Data Integration**: Reddit sentiment, Twitter buzz, custom datasets  
- **Enterprise Features**: Multi-tenancy, advanced security, RBAC, 2FA
- **Full Infrastructure**: Kubernetes, Terraform, monitoring stack, CI/CD

### **📈 Migration Strategy Validation**

**MVP → V1 → V2 → Full Enterprise** provides a **proven evolution path**:

#### **Phase Alignment Check:**
- ✅ **MVP Components** → All map to simplified versions of enterprise services
- ✅ **Database Schema** → Designed to support full enterprise models
- ✅ **API Design** → RESTful structure prepares for microservice extraction  
- ✅ **Frontend Architecture** → Component-based design scales to full feature set

#### **Technical Debt Management:**
- **Service Boundaries**: MVP services are designed as **future microservice boundaries**
- **Event Architecture**: MVP includes event hooks for future event-driven scaling
- **Database Design**: Schema supports multi-tenancy and enterprise features
- **API Contracts**: Designed for backward compatibility during microservice migration

#### **Key Validation Points:**

1. **Daily Rebalancing Workflow** ✅
   - MVP: Complete automated workflow 
   - Enterprise: Advanced rebalancing with multiple allocators and optimizers

2. **Universe Management** ✅  
   - MVP: Manual asset selection
   - Enterprise: Dynamic screening with ROIC > sector median, alternative data

3. **Execution Architecture** ✅
   - MVP: Basic Alpaca integration  
   - Enterprise: Multi-broker routing, smart order routing, risk controls

4. **Data Architecture** ✅
   - MVP: Simple market data fetching
   - Enterprise: Multi-provider data aggregation, caching, streaming

5. **User Management** ✅
   - MVP: Basic authentication
   - Enterprise: Multi-tenant, RBAC, OAuth, 2FA

6. **AI Agent Interface** ✅
   - MVP: Basic Claude integration with tool calling
   - Enterprise: Advanced conversational workflows, proactive insights, comprehensive platform control

### **🚀 Confidence Level: HIGH**

The revised plan provides a **rock-solid foundation** that:
- ✅ Delivers immediate user value (MVP)
- ✅ Maintains clean upgrade path 
- ✅ Prevents architectural lock-in
- ✅ Scales to full enterprise SaaS (your original plan_detailed.md)

**Result**: You can start building the MVP immediately while knowing exactly how it evolves into the comprehensive platform described in your original architecture.

---

## 💡 **Additional Production-Ready Recommendations**

### **📚 Documentation & API Design (Day 1)**
- **API Documentation**: Swagger/OpenAPI integration from the start
- **Interactive API Explorer**: Auto-generated docs with live testing capabilities
- **Versioning Strategy**: Clear API versioning scheme (`/api/v1/`)

**Implementation:**
```python
# Add to MVP backend setup
from flask_restx import Api, Resource
from flask_restx import fields

api = Api(app, doc='/docs/', 
         title='Bubble Platform API',
         description='Investment Strategy Automation Platform')

# Auto-documented models
universe_model = api.model('Universe', {
    'id': fields.String(required=True),
    'name': fields.String(required=True),
    'symbols': fields.List(fields.String, required=True)
})
```

### **🔍 Monitoring & Observability (MVP)**
- **Health Check Endpoints**: `/health`, `/ready`, `/metrics`
- **Basic Metrics Collection**: Request count, response times, error rates
- **Structured Logging**: JSON format with correlation IDs
- **Application Performance Monitoring**: Basic APM integration

**Implementation:**
```python
# Health check endpoints
@app.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}

@app.route('/ready')
def readiness_check():
    # Check DB connectivity, external services
    db_status = check_database_connection()
    return {'ready': db_status, 'services': {'database': db_status}}

@app.route('/metrics')
def metrics():
    return {
        'requests_total': request_counter,
        'active_users': get_active_user_count(),
        'portfolio_value_total': get_total_portfolio_value()
    }
```

### **🚀 Safe Deployment Strategy (MVP)**
- **Feature Flags**: Environment-based feature toggles
- **Blue-Green Deployments**: Zero-downtime deployment capability
- **Rollback Strategy**: Quick rollback mechanism for failed deployments
- **Database Migration Safety**: Backwards-compatible migrations

**Implementation:**
```python
# Feature flags configuration
class FeatureFlags:
    ADVANCED_SCREENER = os.getenv('FEATURE_ADVANCED_SCREENER', 'false').lower() == 'true'
    REAL_TIME_DATA = os.getenv('FEATURE_REAL_TIME_DATA', 'false').lower() == 'true'
    MULTI_BROKER = os.getenv('FEATURE_MULTI_BROKER', 'false').lower() == 'true'

# Usage in code
@app.route('/api/v1/screener')
def advanced_screener():
    if not FeatureFlags.ADVANCED_SCREENER:
        return {'error': 'Feature not available'}, 404
    # Implementation...
```

### **💾 Database Optimization (Day 1)**
- **Connection Pooling**: PostgreSQL connection pool configuration
- **Query Optimization**: EXPLAIN plan analysis setup
- **Database Monitoring**: Slow query logging and analysis
- **Index Strategy**: Essential indexes for core queries

**Implementation:**
```python
# Connection pooling with SQLAlchemy
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300
)

# Essential indexes in models
class Universe(db.Model):
    __tablename__ = 'universes'
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        db.Index('idx_user_created', 'user_id', 'created_at'),
    )
```

### **🔒 Security Fundamentals (MVP)**
- **Input Validation**: Comprehensive request validation
- **Rate Limiting**: API endpoint protection
- **CORS Configuration**: Proper cross-origin setup
- **Security Headers**: Essential HTTP security headers

**Implementation:**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/v1/universes', methods=['POST'])
@limiter.limit("10 per minute")
def create_universe():
    # Implementation with rate limiting
    pass

# Security headers
@app.after_request
def after_request(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response
```

### **📊 Business Intelligence (MVP)**
- **Usage Analytics**: Track key business metrics
- **Error Tracking**: Automated error reporting and alerting
- **Performance Dashboards**: Real-time system performance visibility
- **User Behavior Tracking**: Core user journey metrics

### **🔄 Development Workflow Enhancements**
- **Pre-commit Hooks**: Code quality checks before commits
- **Automated Testing**: Unit, integration, and API tests
- **Code Coverage**: Minimum coverage thresholds
- **Linting & Formatting**: Consistent code style enforcement

These recommendations ensure your MVP is **production-ready from day one** while maintaining the clean evolution path to your enterprise architecture.

---

## 🤖 **AI Agent Integration Summary**

The AI Agent Service is now **properly integrated** throughout the development phases:

### **MVP Phase Integration**
- **Core AI Agent Service** with Claude API integration and tool calling
- **Basic Chat Interface** with multi-modal responses and safety confirmations
- **Platform Tool Integration** for all core services (Universe, Strategy, Portfolio, Execution)
- **Safety Layer** for critical financial actions requiring user confirmation

### **V1 Phase Enhancements**
- **Advanced Workflow Orchestration** for complex multi-step operations
- **Proactive Insights** and recommendation engine
- **Enhanced Interface Modes** (sidebar, overlay, fullscreen)
- **Smart Context Management** with user preference learning

### **V2+ Enterprise Features**
- **Dedicated AI Agent Microservice** extraction
- **Advanced Analytics Integration** with alternative data sources
- **Enterprise Security** with comprehensive audit trails
- **Multi-tenant AI Context** isolation and customization

This integration ensures the AI Agent evolves naturally with the platform, providing immediate value in MVP while scaling to enterprise-grade conversational capabilities.