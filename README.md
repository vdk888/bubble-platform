# 🚀 Bubble Platform - AI-Native Investment Strategy Automation

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://docker.com)
[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**An AI-native investment platform that enables users to create, backtest, and automatically execute investment strategies through natural language conversations.**

## 🎯 Project Status: Sprint 0 Complete ✅

**Foundation Components Implemented:**
- ✅ **Backend API**: FastAPI with comprehensive health monitoring
- ✅ **Database Layer**: 8 production-ready models with SQLAlchemy + Alembic
- ✅ **Production Monitoring**: Health checks, metrics, readiness endpoints
- ✅ **Feature Flags**: Environment-based feature management
- ✅ **Development Environment**: Docker + VS Code ready
- ✅ **API Documentation**: Interactive Swagger UI at `/docs`

## 🏗️ Architecture Overview

### **Interface-First Design**
Built for future microservices evolution with clean service boundaries:

```
bubble-platform/
├── backend/app/
│   ├── api/v1/          # REST API endpoints
│   ├── core/            # Configuration, database, security
│   ├── models/          # Domain models (User, Universe, Strategy, etc.)
│   ├── services/        # Business logic interfaces
│   └── main.py          # FastAPI application
├── frontend/src/        # React app (Sprint 1+)
├── docs/               # Architecture decisions & planning
└── docker-compose.yml  # Development environment
```

### **Database Schema**
**Multi-tenant SaaS ready** with user isolation:
- **User Management**: Authentication, subscription tiers
- **Investment Universe**: Asset lists with screening criteria  
- **Strategy Engine**: Technical indicators, backtesting results
- **Portfolio Management**: Risk parity allocation, rebalancing
- **Execution System**: Order tracking, broker integration
- **AI Agent**: Conversation history, tool calling support

## 🚀 Quick Start

### **Development Setup (Recommended)**
```bash
# Clone repository
git clone https://github.com/vdk888/bubble-platform.git
cd bubble-platform

# Start backend server (uses SQLite)
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### **Docker Development**
```bash
# Full environment with PostgreSQL + Redis
docker-compose up --build

# Or just backend for testing
docker-compose up backend db redis
```

### **Test Your Setup**
```bash
# Health checks
curl http://localhost:8000/health/
curl http://localhost:8000/health/ready
curl http://localhost:8000/health/metrics

# Feature flags
curl http://localhost:8000/api/v1/features/

# Interactive API docs
# Open: http://localhost:8000/docs
```

## 🛠️ VS Code Development

**Optimized for VS Code development:**

1. **Open project**: `code .`
2. **Install extensions**: Python, Docker, SQLite Viewer
3. **Use integrated terminal** for backend development
4. **Debug setup**: F5 to start with breakpoint support

See [DEVELOPMENT.md](DEVELOPMENT.md) for complete VS Code guide.

## 📊 API Endpoints (Sprint 0)

### **Health & Monitoring**
```http
GET /health/              # Basic health status
GET /health/ready         # Database connectivity check
GET /health/metrics       # System metrics (CPU, memory, disk)
GET /docs                 # Interactive API documentation
```

### **Feature Management**
```http
GET /api/v1/features/     # Feature flags status
```

### **Application Info**
```http
GET /                     # Application metadata
```

## 🗄️ Database Models

**Production-ready models with full relationships:**

```python
# Core Models (all implemented)
├── User              # Authentication, subscription management
├── Universe          # Asset lists, screening criteria
├── Strategy          # Technical indicators, backtesting
├── Portfolio         # Risk parity allocation, performance
├── PortfolioAllocation # Strategy-portfolio relationships
├── Order             # Trade execution tracking
├── Execution         # Broker integration, fills
├── Conversation      # AI chat history
└── ChatMessage       # Tool calling, confirmations
```

## 🎛️ Configuration

**Environment-based configuration with validation:**

```bash
# Core settings (.env file)
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///./bubble_dev.db
CLAUDE_API_KEY=your-claude-key
ALPACA_API_KEY=your-alpaca-key
DEBUG=true
ENVIRONMENT=development

# Feature flags
FEATURE_PAPER_TRADING=true
FEATURE_AI_AGENT_ADVANCED=false
FEATURE_REAL_TIME_DATA=false
```

## 🚦 Development Workflow

### **Database Migrations**
```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# View history
alembic history
```

### **Testing**
```bash
# Backend tests (coming in Sprint 1)
cd backend
pytest

# Specific test files
pytest app/tests/test_health.py -v
```

## 🗓️ Roadmap

### **Sprint 1 (Week 2): Authentication & User Management**
- JWT authentication with refresh tokens
- User registration/login endpoints
- Row-level security for multi-tenancy
- Frontend login/register forms

### **Sprint 2 (Week 3): Universe Management**
- Asset search and validation
- Universe CRUD operations
- Frontend universe builder

### **Sprint 3-11: Core Platform Features**
- Market data integration (Yahoo Finance)
- Technical indicators (RSI, MACD, Momentum)  
- Strategy backtesting engine
- AI agent with Claude integration
- Risk parity portfolio optimization
- Broker integration (Alpaca API)
- Daily rebalancing automation

**MVP Target**: 12 weeks to full platform with AI capabilities

## 🔧 Technology Stack

**Backend:**
- **FastAPI** - High-performance async API framework
- **SQLAlchemy** - Database ORM with Alembic migrations
- **Pydantic** - Data validation and settings management
- **PostgreSQL** - Production database (SQLite for development)
- **Redis** - Caching and real-time features

**AI Integration:**
- **Anthropic Claude** - AI agent with tool calling
- **Natural Language Interface** - Conversational platform control

**Infrastructure:**
- **Docker & Docker Compose** - Containerized development
- **GitHub Actions** - CI/CD pipeline (coming Sprint 10)
- **Production deployment** - Cloud-ready architecture

## 🤝 Contributing

**Development Process:**
1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Follow the development guide in [DEVELOPMENT.md](DEVELOPMENT.md)
4. Submit pull request with tests

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎯 Sprint 0 Achievements

**✅ Bulletproof Foundation Complete:**
- **8 production-ready database models** with proper relationships
- **Comprehensive health monitoring** with system metrics
- **Feature flags infrastructure** for production deployments
- **Interactive API documentation** with Swagger UI
- **Development environment** optimized for VS Code
- **Docker configuration** for production-like testing
- **Alembic migrations** ready for database evolution

**Ready for Sprint 1 development!** 🚀

---

**Built with ❤️ for automated investment management**