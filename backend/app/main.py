from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from .core.config import settings
from .models.base import Base
from .core.database import engine
from .api.v1 import health, features

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting {settings.app_name}")
    print(f"Environment: {settings.environment}")
    print(f"Debug mode: {settings.debug}")
    
    # Create tables (in production, use alembic migrations)
    if settings.environment == "development":
        Base.metadata.create_all(bind=engine)
        print("Database tables created")
    
    yield
    
    # Shutdown
    print(f"Shutting down {settings.app_name}")

# Enhanced FastAPI app with comprehensive configuration
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="""
    **AI-Native Investment Strategy Automation Platform**
    
    ## Core Features
    * **Universe Management**: Create and manage investment universes
    * **Technical Indicators**: RSI, MACD, Momentum with signal generation  
    * **Strategy Backtesting**: Historical performance validation
    * **Risk Parity Portfolios**: Automated multi-strategy allocation
    * **AI Agent**: Natural language platform control with tool calling
    * **Broker Execution**: Automated rebalancing via multi-broker integration
    
    ## Architecture
    * **Interface-First Design**: Clean service boundaries for future microservice evolution
    * **Production-Ready**: Comprehensive health checks, feature flags, monitoring
    * **AI-Native**: Conversational interface as first-class citizen
    * **Security by Design**: Multi-tenant isolation, input validation, audit trails
    
    ## Authentication
    All endpoints require JWT authentication except /health, /ready, /docs, /features
    
    ## Rate Limits
    * Authentication: 10 requests/minute
    * General APIs: 100 requests/minute  
    * Backtesting: 5 requests/minute
    """,
    contact={
        "name": "Bubble Platform Support",
        "email": "support@bubbleplatform.com"
    },
    license_info={
        "name": "Private License"
    },
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
app.include_router(health.router, prefix="/health", tags=["Health Checks"])
app.include_router(features.router, prefix="/api/v1/features", tags=["Feature Flags"])

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with application information"""
    from .core.feature_flags import FeatureFlags
    
    return {
        "message": "Bubble Platform API",
        "version": "1.0.0",
        "environment": settings.environment,
        "debug": settings.debug,
        "features_enabled": len(FeatureFlags.get_enabled_flags()),
        "docs_url": "/docs",
        "health_url": "/health",
        "ready_url": "/health/ready",
        "metrics_url": "/health/metrics",
        "features_url": "/api/v1/features"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)