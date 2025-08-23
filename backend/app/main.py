from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .core.config import settings
from .models.base import Base
from .core.database import engine
from .core.middleware import SecurityHeadersMiddleware, InputSanitizationMiddleware, AuditLoggingMiddleware, PostgreSQLRLSMiddleware, limiter
from .api.v1 import health, features, auth, rls_admin

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
    
    # Setup PostgreSQL RLS policies for multi-tenant isolation
    if "postgresql" in settings.database_url.lower():
        from .core.rls_policies import setup_postgresql_rls
        from .core.database import SessionLocal
        
        try:
            db_session = SessionLocal()
            rls_success = setup_postgresql_rls(db_session)
            if rls_success:
                print("✅ PostgreSQL RLS policies configured - multi-tenant isolation active")
            else:
                print("⚠️ PostgreSQL RLS setup failed - check logs")
            db_session.close()
        except Exception as e:
            print(f"⚠️ RLS setup error (non-critical): {e}")
    else:
        print("ℹ️ SQLite database - RLS policies not applicable")
    
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

# Add security middleware (order matters - RLS first, then others)
app.add_middleware(PostgreSQLRLSMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(InputSanitizationMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health Checks"])
app.include_router(features.router, prefix="/api/v1/features", tags=["Feature Flags"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(rls_admin.router, prefix="/api/v1/admin/rls", tags=["RLS Administration"])

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