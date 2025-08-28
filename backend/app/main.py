from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
# Rate limiting now handled by enterprise middleware

from .core.config import settings
from .models.base import Base
from .core.database import engine
# Enterprise middleware imports (conditionally enabled)
from .core.middleware.rate_limiting import RateLimitMiddleware, TESTING_CONFIG
from .api.v1 import health, features, auth, rls_admin, universes, assets

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
                print("SUCCESS: PostgreSQL RLS policies configured - multi-tenant isolation active")
            else:
                print("WARNING: PostgreSQL RLS setup failed - check logs")
            db_session.close()
        except Exception as e:
            print(f"WARNING: RLS setup error (non-critical): {e}")
    else:
        print("INFO: SQLite database - RLS policies not applicable")
    
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

# Add security middleware - Enterprise security features
# Always add rate limiting middleware but enable/disable it dynamically
app.add_middleware(
    RateLimitMiddleware, 
    rate_limiter=None,  # Use default Redis rate limiter
    enable_rate_limiting=False,  # Will be enabled dynamically based on environment
    exempt_paths=["/health", "/health/ready", "/docs", "/openapi.json", "/redoc"]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting now handled by RateLimitMiddleware

# Include routers
app.include_router(health.router, prefix="/health", tags=["Health Checks"])
app.include_router(features.router, prefix="/api/v1/features", tags=["Feature Flags"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(rls_admin.router, prefix="/api/v1/admin/rls", tags=["RLS Administration"])
app.include_router(universes.router, prefix="/api/v1/universes", tags=["Universe Management"])
app.include_router(assets.router, prefix="/api/v1/assets", tags=["Asset Management"])

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with application information and standardized response format"""
    from .core.feature_flags import FeatureFlags
    
    return {
        "success": True,
        "data": {
            "name": "Bubble Platform API",
            "version": "1.0.0",
            "environment": settings.environment,
            "debug": settings.debug,
            "features_enabled": len(FeatureFlags.get_enabled_flags()),
            "docs_url": "/docs",
            "health_url": "/health",
            "ready_url": "/health/ready",
            "metrics_url": "/health/metrics",
            "features_url": "/api/v1/features"
        },
        "message": "Welcome to Bubble Platform - AI-Native Investment Strategy Automation",
        "next_actions": ["view_docs", "check_health", "register_user", "login_user", "create_universe", "search_assets", "validate_symbols"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=settings.debug)