from fastapi import APIRouter, status, HTTPException
from datetime import datetime, timezone
import psutil
import redis
import anthropic
from ...core.config import settings
from ...core.database import SessionLocal
from sqlalchemy import text

router = APIRouter()

# Global counters for metrics (in production, use Redis or dedicated metrics service)
request_counter = 0
error_counter = 0

async def check_database_connection() -> bool:
    """Check database connectivity"""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

async def check_redis_connection() -> bool:
    """Check Redis connectivity"""
    try:
        r = redis.from_url(settings.redis_url)
        r.ping()
        return True
    except Exception as e:
        print(f"Redis connection failed: {e}")
        return False

async def check_claude_api_status() -> bool:
    """Check Claude API connectivity"""
    try:
        client = anthropic.Anthropic(api_key=settings.claude_api_key)
        # Simple test call - just check if API key is valid
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            messages=[{"role": "user", "content": "test"}]
        )
        return True
    except Exception as e:
        print(f"Claude API connection failed: {e}")
        return False

@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "environment": settings.environment
    }

@router.get("/ready")
async def readiness_check():
    """Comprehensive readiness check for Kubernetes"""
    checks = {}
    overall_ready = True
    
    # Database check
    db_ready = await check_database_connection()
    checks["database"] = {"ready": db_ready, "service": "PostgreSQL"}
    if not db_ready:
        overall_ready = False
    
    # Redis check
    redis_ready = await check_redis_connection()
    checks["redis"] = {"ready": redis_ready, "service": "Redis"}
    if not redis_ready:
        overall_ready = False
    
    # Claude API check (optional - don't fail readiness if it's down)
    claude_ready = await check_claude_api_status()
    checks["claude_api"] = {"ready": claude_ready, "service": "Claude API", "optional": True}
    
    response_data = {
        "ready": overall_ready,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks
    }
    
    # Return 503 if not ready (for load balancer health checks)
    if not overall_ready:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=response_data)
    
    return response_data

@router.get("/metrics")
async def metrics_endpoint():
    """Prometheus-style metrics endpoint"""
    global request_counter, error_counter
    
    # System metrics
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # Database connection pool info
    try:
        with SessionLocal() as db:
            active_connections = len(db.get_bind().pool.checkedout())
    except:
        active_connections = -1
    
    metrics_data = {
        # Application metrics
        "http_requests_total": request_counter,
        "http_errors_total": error_counter,
        "database_connections_active": active_connections,
        
        # System metrics
        "memory_usage_bytes": memory.used,
        "memory_usage_percent": memory.percent,
        "disk_usage_bytes": disk.used,
        "disk_usage_percent": (disk.used / disk.total) * 100,
        "cpu_usage_percent": cpu_percent,
        
        # Business metrics (placeholder - implement based on your needs)
        "active_users_count": 0,  # await get_active_user_count()
        "total_portfolios": 0,    # await get_total_portfolio_count()
        "total_strategies": 0,    # await get_total_strategy_count()
        
        # Timestamp
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return metrics_data

@router.get("/detailed")
async def detailed_health_check():
    """Detailed health check with all system information"""
    db_healthy = await check_database_connection()
    redis_healthy = await check_redis_connection()
    claude_healthy = await check_claude_api_status()
    
    # System information
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    detailed_info = {
        "status": "healthy" if all([db_healthy, redis_healthy]) else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "environment": settings.environment,
        "services": {
            "database": {
                "healthy": db_healthy,
                "type": "PostgreSQL",
                "url": settings.database_url.split('@')[-1] if '@' in settings.database_url else "localhost"
            },
            "redis": {
                "healthy": redis_healthy,
                "type": "Redis",
                "url": settings.redis_url
            },
            "claude_api": {
                "healthy": claude_healthy,
                "type": "Claude API",
                "optional": True
            }
        },
        "system": {
            "memory": {
                "used_mb": round(memory.used / 1024 / 1024, 2),
                "available_mb": round(memory.available / 1024 / 1024, 2),
                "percent_used": memory.percent
            },
            "disk": {
                "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "percent_used": round((disk.used / disk.total) * 100, 2)
            },
            "cpu_percent": psutil.cpu_percent(interval=1)
        },
        "configuration": {
            "debug": settings.debug,
            "paper_trading_enabled": settings.paper_trading_enabled,
            "rebalancing_threshold": settings.rebalancing_threshold
        }
    }
    
    return detailed_info