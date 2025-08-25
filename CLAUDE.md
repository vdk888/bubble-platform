# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 📚 **CRITICAL: Planning Documentation Reference**

**BEFORE starting ANY task, you MUST consult the relevant planning documents in `planning/` directory.**

### Planning Documentation Map
Use these files to understand requirements, context, and implementation approach for any task:

| File | Purpose | When to Consult |
|------|---------|----------------|
| **`planning/0_dev.md`** | Complete developer roadmap (Junior→Senior), best practices, security patterns, testing frameworks | ALL development tasks, architecture decisions, quality standards |
| **`planning/1_spec.md`** | Original product specification, core components, system requirements | Feature development, API design, system architecture |
| **`planning/2_jira.md`** | User stories, acceptance criteria, epic breakdown | Feature implementation, testing requirements, acceptance criteria |
| **`planning/3_directory_structure.md`** | Complete microservices architecture, file organization | Code organization, service splitting, structure decisions |
| **`planning/4_plan_overview.md`** | High-level architecture vision, microservices overview | Architecture decisions, service design, system overview |
| **`planning/5_plan_phased.md`** | Detailed implementation phases, file structure | Implementation planning, phased development approach |
| **`planning/6_plan_detailed.md`** | Complete technical specification, microservices architecture | Detailed implementation, service specifications |
| **`planning/7_risk_system.md`** | Risk management, security considerations | Security implementation, risk mitigation |
| **`planning/00_sprint_roadmap.md`** | Sprint planning, milestone tracking | Sprint planning, progress tracking |
| **`planning/roadmap.md`** | Version roadmap (MVP → V1 → V2), feature distribution | Version planning, feature prioritization |
| **`planning/Sprint2_progress_tracking.md`** | Current sprint progress, task status | Current sprint context, progress updates |

### **MANDATORY WORKFLOW: Documentation-First Approach**

**For EVERY task, follow this sequence:**

1. **📖 READ FIRST**: Before writing any code, search and read the relevant planning documents
   ```bash
   # Example: For universe screening feature
   # Read: planning/1_spec.md (Universe Definition section)
   # Read: planning/2_jira.md (Epic 1 - Universe Management)
   # Read: planning/0_dev.md (Interface-First Design patterns)
   ```

2. **🎯 UNDERSTAND CONTEXT**: Extract specific requirements, patterns, and constraints
   - What are the exact acceptance criteria?
   - What architectural patterns should be used?
   - What security requirements apply?
   - What performance targets must be met?

3. **🏗️ PLAN IMPLEMENTATION**: Design approach based on documentation
   - Follow Interface-First Design methodology
   - Apply security-by-design principles  
   - Use real data testing patterns
   - Meet performance SLA requirements

4. **💻 IMPLEMENT**: Code according to documented standards and patterns

5. **✅ VALIDATE**: Ensure implementation meets all documented requirements

### **Key Principle**: 
**NEVER assume or guess requirements.** The planning documents contain precise specifications, patterns, and standards. Always consult them first to ensure consistency with the overall architecture and quality standards.

## Development Philosophy & Standards

### Target Level: Senior Developer (Top 1%)
This codebase targets **senior-level engineering standards** with production-grade patterns from Day 1. We're building the MVP as a lightweight version of the full microservices architecture, but with all the foundational quality measures in place.

### Core Principles
1. **Interface-First Design**: Define contracts before implementation (enables parallel development, testing with mocks, implementation flexibility)
2. **Security-By-Design**: Security integrated from Day 1, not added later (password hashing, JWT, RLS, audit trails)
3. **Real Data Testing**: Always test with actual API calls, not mocks (no placeholders, real validation)
4. **Production-Ready from Start**: Include monitoring, logging, error handling from MVP
5. **Clean Architecture**: Business logic in services, not in controllers/views (MVC pattern, SOLID principles)
6. **Test Pyramid**: 60-70% unit, 20-30% integration, 5-10% E2E tests
7. **Documentation as Code**: Living documentation, Architecture Decision Records (ADRs)

## Project Overview
The Bubble Platform is an AI-native investment strategy automation platform designed to automate the construction, monitoring, and execution of investment strategies. The platform transforms idea → strategy → portfolio → orders → notifications in an automated workflow.

### Core Components
1. **Universe Definition** (What do I buy?) - Define investment universes with dynamic screening
2. **Indicators & Signals** (When do I buy?) - Technical indicators (RSI, MACD, Momentum) with signal generation
3. **Portfolio Strategy** (How much do I buy?) - Allocation rules and backtesting
4. **Master Portfolio** - Risk parity aggregation of multiple strategies ("pockets")
5. **Broker Execution** - Automated multi-broker order routing and execution

### Architecture Evolution
- **MVP**: Monolithic FastAPI backend with React frontend
- **V1**: Microservices architecture with 6 core services
- **V2**: Full enterprise features with AI agent, alternative data, and advanced risk management

### Key Technical Features
- Multi-tenant architecture with PostgreSQL Row-Level Security (RLS)
- Dynamic universe screening with ROIC-based filters and sector analysis
- Background processing with Celery/Redis for async operations
- Real-time data validation with Alpha Vantage, Yahoo Finance, and alternative data sources
- React TypeScript frontend with traditional UI and conversational AI interface
- Interface-First Design methodology for clean service boundaries

## Development Commands

### Backend Development
```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Run backend server (development mode with SQLite)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Run tests with real data validation
python run_tests.py

# Run specific test categories
pytest -m unit              # Unit tests only
pytest -m integration        # Integration tests
pytest -m business_logic     # Business logic validation
pytest -m security          # Security tests
pytest -m api_endpoints     # API endpoint tests

# Run tests with coverage
pytest --cov=app

# Database migrations
alembic revision --autogenerate -m "Description"  # Generate migration
alembic upgrade head                              # Apply migrations
alembic downgrade -1                              # Rollback last migration
```

### Frontend Development
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm start

# Run tests
npm test

# Build for production
npm build
```

### Docker Development
```bash
# Start all services (backend, frontend, database, redis, celery)
docker-compose up --build

# Run tests in Docker
docker-compose --profile test run test

# View logs
docker-compose logs backend -f
docker-compose logs celery_worker -f

# Clean rebuild
docker-compose down
docker-compose up --build --force-recreate
```

## Architecture & Patterns

### Backend Structure
- **Interface-First Design**: Define contracts (interfaces) BEFORE implementation in `app/services/interfaces/`
  - Enables parallel development, better testing with mocks, and flexibility to swap implementations
  - Example: `IScreener` interface with `FundamentalScreener`, `TechnicalScreener` implementations
- **Multi-tenant isolation**: PostgreSQL RLS policies automatically filter data by tenant_id
- **Background processing**: Celery workers handle async tasks with dedicated queues:
  - `validation` queue: Asset validation and enrichment
  - `bulk_validation` queue: Bulk universe operations
  - `maintenance` queue: Periodic maintenance tasks
- **Service layer pattern**: Business logic in services, not in API endpoints
- **Feature flags**: Dynamic feature control via `/api/v1/features/` endpoint

### Key Service Interfaces
- `IDataProvider`: Abstract interface for market data (Yahoo, Alpha Vantage, mock implementations)
- `IScreener`: Interface for universe screening (fundamental, technical, composite screeners)
- `IAssetValidation`: Interface for validating and enriching asset data
- `IAIAgent`: Interface for conversational AI with tool calling capabilities
- `IBacktestEngine`: Interface for backtesting engines (basic, VectorBT, QuantConnect)

### Authentication & Security
- JWT-based authentication with tenant isolation
- All API endpoints require authentication except: `/health`, `/ready`, `/docs`, `/features`
- Rate limiting configured per endpoint type (auth: 10/min, general: 100/min, backtesting: 5/min)
- Input sanitization and audit logging middleware

### Testing Philosophy
- **Real data testing**: Tests use actual API calls to validate integrations
- **Comprehensive coverage**: Unit, integration, security, and business logic tests
- **Test markers**: Use pytest markers to categorize and run specific test suites
- **Isolated test environment**: Separate test database and Redis instances

## API Endpoints

### Health & Monitoring
- `GET /health/` - Basic health check
- `GET /health/ready` - Database connectivity check
- `GET /health/metrics` - System metrics and performance data
- `GET /health/worker` - Celery worker status

### Core Features
- `/api/v1/auth/` - Authentication (register, login, token refresh)
- `/api/v1/universes/` - Universe management with dynamic screening capabilities
- `/api/v1/assets/` - Asset validation and enrichment with real-time data
- `/api/v1/features/` - Feature flag management
- `/api/v1/indicators/` - Technical indicator calculations (RSI, MACD, Momentum)
- `/api/v1/signals/` - Signal generation with weighted composite signals
- `/api/v1/portfolios/` - Portfolio management and risk parity allocation
- `/api/v1/backtests/` - Strategy backtesting with multiple engines

## Database Schema

### Multi-tenant Design
All tables include `tenant_id` for isolation:
- Users table: Authentication and tenant association
- Universes table: Investment universe definitions
- Assets table: Global asset registry
- UniverseAssets table: Universe-specific asset tracking

### Migrations
Database changes tracked through Alembic migrations in `backend/alembic/versions/`

## Environment Variables

### Required for Development
```bash
SECRET_KEY=your-development-secret-key
DATABASE_URL=sqlite:///./bubble_dev.db  # Or PostgreSQL for production-like
REDIS_URL=redis://localhost:6379
CLAUDE_API_KEY=your-claude-api-key      # For AI agent functionality
ALPHA_VANTAGE_API_KEY=your-av-key       # For market data
```

### Testing Environment
```bash
DATABASE_TEST_URL=sqlite:///./bubble_test.db
ENVIRONMENT=testing
DEBUG=false
```

## Technical Indicators Specification

### Supported Indicators
1. **RSI (Relative Strength Index)**
   - 14-period default, configurable
   - Signals: Overbought (>70), Oversold (<30)
   - Output: -1 (sell), 0 (hold), 1 (buy)

2. **MACD (Moving Average Convergence Divergence)**
   - Parameters: 12,26,9 (fast, slow, signal)
   - Signals: Crossover detection
   - Priority: Highest in conflict resolution

3. **Momentum**
   - Configurable lookback periods
   - Signal thresholds: ±2%
   - Simple rate of change calculation

### Signal Generation Rules
- **Output Format**: Standardized pandas Series with -1, 0, 1 values
- **Composite Signals**: Weighted combination with configurable weights
- **Conflict Resolution**: MACD > RSI > Momentum hierarchy
- **Data Validation**: Reject market data older than 15 minutes
- **Performance**: <2 seconds for 1000 assets calculation

## Microservices Roadmap

### MVP Phase (Current Implementation)
- Monolithic FastAPI backend with all features
- SQLite for development, PostgreSQL for production
- Basic authentication and universe management
- Simple backtesting capabilities

### V1 Architecture (Future)
Planned microservices split:
1. **Auth Service**: User management, JWT, multi-tenancy
2. **Billing Service**: Stripe integration, subscription management
3. **Pocket Factory Service**: Strategy creation, screening, backtesting
4. **Master Portfolio Service**: Risk parity allocation, rebalancing
5. **Execution Service**: Multi-broker order routing
6. **Data Service**: Market data aggregation and caching
7. **Notification Service**: Multi-channel alerts
8. **AI Agent Service**: Conversational interface with tool calling

### V2 Features (Enterprise)
- Alternative data integration (Reddit, Twitter sentiment)
- Advanced risk management with VaR, correlation monitoring
- Machine learning-based allocation strategies
- Real-time streaming data with WebSocket

## Common Development Tasks

### Adding New API Endpoint
1. Define interface in `backend/app/services/interfaces/`
2. Implement service in `backend/app/services/`
3. Create API router in `backend/app/api/v1/`
4. Include router in `backend/app/main.py`
5. Add comprehensive tests in `backend/app/tests/`

### Adding New Model
1. Create model in `backend/app/models/`
2. Import in `backend/app/models/__init__.py`
3. Generate migration: `alembic revision --autogenerate -m "Add ModelName"`
4. Apply migration: `alembic upgrade head`

### Implementing Background Task
1. Define task in `backend/app/workers/`
2. Configure queue in Celery worker command
3. Add task invocation in relevant service
4. Test with real worker running

### Interface-First Design Workflow
When adding new functionality, ALWAYS follow this pattern:

```python
# 1. Define the interface FIRST
from abc import ABC, abstractmethod

class IScreener(ABC):
    @abstractmethod
    async def screen_universe(
        self, 
        criteria: ScreeningCriteria, 
        date: datetime
    ) -> List[ScreeningResult]:
        pass

# 2. Update existing code to accept interface
class SignalEngine:
    def __init__(self, screener: IScreener):  # Interface, not implementation
        self.screener = screener

# 3. Implement the interface
class FundamentalScreener(IScreener):
    async def screen_universe(self, criteria, date):
        # Actual implementation
        pass

# 4. Use dependency injection
screener = FundamentalScreener(data_provider)
signal_engine = SignalEngine(screener=screener)
```

This approach enables:
- Parallel development by multiple team members
- Easy testing with mock implementations
- Flexibility to swap implementations without refactoring
- Clear contracts between components

## Testing Best Practices

### Always Test with Real Data
- Use actual API responses, not mocks
- Validate external service integrations
- Test rate limiting and error handling
- Verify multi-tenant isolation

### Run Comprehensive Tests Before Changes
```bash
cd backend
python run_tests.py  # Runs all tests with clean output
```

## Performance Considerations

### Caching Strategy
- Redis caching for frequently accessed data
- Asset validation results cached for 24 hours
- Universe compositions cached with invalidation on update

### Background Processing
- Asset validation runs asynchronously via Celery
- Bulk operations processed in dedicated queues
- Worker health monitoring via `/health/worker` endpoint

## Security Requirements

### Security-First Development
Security is integrated from Day 1, not added later. Follow these principles:

### Authentication & Authorization
- **Password Requirements**: Minimum 12 characters, uppercase, lowercase, numbers, special characters
- **JWT Configuration**: 30-minute expiration, HS256 algorithm, automatic refresh
- **Rate Limiting**: 10 req/min for auth, 100 req/min for general APIs, 5 req/min for backtesting
- **2FA Support**: Optional two-factor authentication for enhanced security

### Multi-tenant Isolation
- PostgreSQL RLS policies enforce data separation at database level
- Every query automatically filtered by tenant_id
- Cross-tenant access attempts logged and blocked
- Audit trail for all financial operations

### Input Validation & Sanitization
- Pydantic models validate all API inputs with strict type checking
- SQL injection prevention through SQLAlchemy ORM with parameterized queries
- XSS protection via input sanitization middleware
- File upload validation for type and size constraints

### Security Headers & Middleware
```python
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000"
}
```

### Financial Data Protection
- All financial operations require audit logging
- Trade confirmations require explicit user approval
- Encryption at rest for sensitive data
- No logging of sensitive information (API keys, passwords)

## Project Status & Priorities

### Current Implementation Status
The project is in MVP phase with:
- ✅ Basic authentication and user management
- ✅ Universe creation and asset validation
- ✅ Health monitoring endpoints
- ✅ Multi-tenant database structure with RLS
- ✅ Comprehensive test coverage (unit, integration, security)
- ✅ Docker containerization
- ✅ Redis/Celery background processing setup

### Immediate Development Priorities
1. **Complete Indicator Implementation** - RSI, MACD, Momentum with signal generation
2. **Dynamic Universe Screening** - ROIC-based filters with sector analysis  
3. **Backtesting Engine** - Basic implementation with performance metrics
4. **Portfolio Risk Parity** - Allocation algorithm for master portfolio
5. **AI Agent Integration** - Conversational interface with tool calling

### Performance Targets
- API Response: <200ms (95th percentile)
- Indicator Calculation: <2s for 1000 assets
- Backtest Execution: <30s for 2-year daily data
- System Uptime: 99.9% availability

### Business Model Implementation
- **Free Tier**: 3 strategies, limited backtesting
- **Pro Tier**: 50 strategies, advanced features
- **Enterprise**: Unlimited, custom features, SLA

## Senior-Level Development Standards

### Feature Development Framework (RICE Prioritization)
Use **RICE Matrix** (Reach × Impact × Confidence ÷ Effort) for feature prioritization:

| Feature | Reach | Impact | Confidence | Effort | RICE Score | Priority |
|---------|-------|--------|------------|--------|------------|----------|
| User Authentication | High (1000) | High (3) | High (100%) | Low (2) | 150 | P0 |
| Basic Portfolio | Med (500) | High (3) | High (80%) | Med (4) | 100 | P1 |
| AI Agent Interface | Low (100) | High (3) | Med (60%) | High (8) | 22.5 | P3 |

### Weekly Feature Development Template
```markdown
# Feature: [Name]

## Monday: Analysis & Planning
- [ ] User story definition with acceptance criteria
- [ ] API contract design (Interface-First)
- [ ] Database schema impact analysis
- [ ] Risk assessment and mitigation
- [ ] Performance requirements (SLA targets)

## Tuesday: Interface Definition
- [ ] Define service interfaces before implementation
- [ ] Mock implementations for testing
- [ ] Error handling strategy
- [ ] Security considerations

## Wednesday-Thursday: Implementation
- [ ] Service layer implementation
- [ ] API endpoints with comprehensive validation
- [ ] Database migrations (tested rollback)
- [ ] Real data testing (no mocks/placeholders)

## Friday: Quality Assurance
- [ ] Integration testing with real APIs
- [ ] Security testing (input validation, auth)
- [ ] Performance validation against targets
- [ ] Code review and documentation update
```

### Quality Gates (Must Pass Before Deployment)

#### Code Quality Standards
- **Test Coverage**: Minimum 80% overall, 90% for critical paths
- **Real Data Testing**: All external API integrations tested with actual calls
- **Performance**: API responses <200ms (95th percentile)
- **Security**: All inputs validated, SQL injection prevention, audit trails

#### Pre-Deployment Checklist
```bash
# 1. Run comprehensive test suite
cd backend && python run_tests.py

# 2. Security validation
pytest -m security

# 3. Performance benchmarks
pytest -m performance --benchmark-only

# 4. Integration tests with real data
pytest -m integration --no-mock

# 5. Database migration testing (up/down)
alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```

### Production-Grade Monitoring & Observability

#### Health Check Implementation
```python
# Comprehensive health checks (not just "OK")
@app.get("/health/comprehensive")
async def comprehensive_health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": app.version,
        "database": {
            "status": await check_db_connection(),
            "query_time_ms": await measure_db_query_time(),
            "migrations": await get_current_migration()
        },
        "redis": {
            "status": await check_redis_connection(),
            "latency_ms": await measure_redis_latency()
        },
        "external_apis": {
            "alpha_vantage": await check_alpha_vantage_status(),
            "yahoo_finance": await check_yahoo_finance_status()
        },
        "celery_workers": await get_worker_status(),
        "performance_metrics": {
            "avg_response_time": get_avg_response_time(),
            "requests_per_second": get_current_rps()
        }
    }
```

#### Smoke Testing (Post-Deployment)
```python
async def smoke_tests():
    """Critical path validation after deployment"""
    
    # 1. Core functionality works
    assert await test_user_registration()
    assert await test_user_login()
    assert await test_universe_creation()
    assert await test_basic_backtest()
    
    # 2. External integrations working
    assert await test_market_data_fetch()
    assert await test_asset_validation()
    
    # 3. Background processing operational
    assert await test_celery_worker_health()
    
    print("✅ Smoke tests passed - Critical paths operational")
```

### Risk Management & Audit Framework

#### Risk Register (Financial Platform Requirements)
| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| Market Data API Outage | Medium | High | Multiple providers + circuit breakers | Backend |
| Database Scaling | High | Medium | Read replicas + connection pooling | DevOps |
| Security Breach | Low | Critical | Penetration testing + monitoring | Security |
| Claude API Rate Limits | Medium | High | Fallback modes + caching | AI Team |

#### Rollback Strategy (Zero-Downtime)
```markdown
## Emergency Rollback Procedures

### Database Migrations
- All migrations must have tested rollback scripts
- Backup created automatically before major schema changes
- Rollback tested in staging environment first

### Service Deployments
- Blue-green deployment with health checks
- Feature flags for instant disable
- Container rollback to previous stable version

### Critical Feature Failures
- AI Agent → Fallback to traditional UI
- Live Trading → Automatic paper mode
- Market Data → Switch to backup provider
```

### Frontend Testing Strategy (Production-Grade)

#### Test Pyramid Implementation
```javascript
// Unit Tests (60-70%) - Fast, isolated
describe('PortfolioCalculator', () => {
  it('calculates risk parity allocation correctly', () => {
    const assets = [/* test data */];
    const result = calculateRiskParity(assets);
    expect(result.totalWeight).toBeCloseTo(1.0);
  });
});

// Integration Tests (20-30%) - Component + API
describe('UniverseCreation', () => {
  it('creates universe with real asset validation', async () => {
    render(<UniverseEditor />);
    await userEvent.type(screen.getByRole('textbox'), 'AAPL');
    await userEvent.click(screen.getByText('Add Asset'));
    
    // Tests actual API integration
    await waitFor(() => {
      expect(screen.getByText('Asset validated')).toBeInTheDocument();
    });
  });
});

// E2E Tests (5-10%) - Full user journeys
describe('Complete Strategy Creation', () => {
  it('creates strategy from universe to backtest', () => {
    cy.visit('/universes');
    cy.createUniverse(['AAPL', 'GOOGL']);
    cy.addIndicators(['RSI', 'MACD']);
    cy.runBacktest();
    cy.get('[data-testid="backtest-results"]').should('contain', 'Sharpe Ratio');
  });
});
```

### Audit & Compliance Framework

#### Security Audit Checklist
- [ ] **Multi-tenant Isolation**: PostgreSQL RLS policies tested
- [ ] **Financial Data Protection**: All trades logged immutably  
- [ ] **Input Validation**: Pydantic models prevent injection attacks
- [ ] **Authentication**: JWT with proper expiration, 2FA support
- [ ] **Rate Limiting**: API protection against abuse
- [ ] **Audit Trails**: All financial operations logged with checksum

#### Performance Budget (SLA Requirements)
```markdown
## Performance SLA Targets

### API Response Times (95th percentile)
- Authentication: <200ms
- Universe Creation: <500ms
- Indicator Calculation: <2s (1000 assets)
- Backtest Execution: <30s (2-year daily data)

### System Availability
- Overall Uptime: 99.9% (8.76 hours downtime/year)
- Database: 99.95%
- Critical APIs: 99.9%

### Scalability Targets
- Concurrent Users: 1,000 (MVP) → 10,000 (V1)
- API Requests: 10,000/minute
- Background Jobs: 100/second
```

### Architecture Evolution Strategy

#### Current (MVP): Bulletproof Monolith
- Single FastAPI application with all features
- PostgreSQL with RLS for multi-tenancy
- Redis/Celery for background processing
- Interface-First Design preparing for microservices split

#### V1: Microservices with Service Mesh
- 8 specialized services (Auth, Billing, Pocket Factory, etc.)
- Event-driven communication via Redis streams
- Kubernetes orchestration with Istio service mesh
- Distributed tracing and monitoring

#### V2: Enterprise Scale
- Alternative data integration (social sentiment)
- ML-based allocation strategies
- Real-time streaming with WebSocket
- Advanced risk management (VaR, correlation monitoring)