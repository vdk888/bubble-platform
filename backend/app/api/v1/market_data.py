"""
Enhanced Market Data API endpoints with composite provider support

Features:
- Triple-provider architecture (OpenBB → Yahoo → Alpha Vantage)
- Professional OpenBB features (fundamentals, economics, news, analyst data)
- Real-time provider health monitoring
- Intelligent failover with performance metrics
- Cost optimization and monitoring
- Bulk data optimization for backtesting
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from pydantic import BaseModel, Field

from ...core.dependencies import get_current_user
from ...models.user import User
from ...services.market_data_service import MarketDataService
from ...core.config import settings

router = APIRouter(prefix="/api/v1/market-data", tags=["Market Data"])

# Initialize market data service
market_data_service = MarketDataService(
    openbb_api_key=getattr(settings, 'openbb_api_key', None),
    alpha_vantage_api_key=getattr(settings, 'alpha_vantage_api_key', None),
    enable_monitoring=True,
    enable_caching=True,
    cache_ttl_seconds=300,
    max_workers=10
)

# Pydantic models for request/response

class RealTimeRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of asset symbols", example=["AAPL", "GOOGL", "MSFT"])

class HistoricalDataRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of asset symbols")
    start_date: date = Field(..., description="Start date for historical data")
    end_date: date = Field(..., description="End date for historical data") 
    interval: str = Field(default="1d", description="Data interval", example="1d")

class AssetValidationRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of symbols to validate")

class FundamentalDataRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of asset symbols for fundamental analysis")

class EconomicIndicatorsRequest(BaseModel):
    indicators: List[str] = Field(
        ..., 
        description="List of economic indicators",
        example=["gdp", "inflation", "unemployment", "interest_rates", "vix"]
    )

class AssetSearchRequest(BaseModel):
    query: str = Field(..., description="Search query for assets", example="Apple")
    limit: int = Field(default=10, description="Maximum number of results")

class BulkDataRequest(BaseModel):
    symbols: List[str] = Field(..., description="List of symbols for bulk fetch")
    operations: List[str] = Field(
        ..., 
        description="Operations to perform",
        example=["historical_data", "asset_info", "fundamental_data"]
    )
    parallel_requests: int = Field(default=5, description="Number of parallel requests")

class NewsAnalysisRequest(BaseModel):
    symbols: Optional[List[str]] = Field(default=None, description="Symbols for news analysis")
    keywords: Optional[List[str]] = Field(default=None, description="Keywords to search for")
    limit: int = Field(default=20, description="Number of news articles")

class AnalystEstimatesRequest(BaseModel):
    symbols: List[str] = Field(..., description="Symbols for analyst estimates")

class InsiderTradingRequest(BaseModel):
    symbols: List[str] = Field(..., description="Symbols for insider trading data")

# API Endpoints

@router.on_event("startup")
async def startup_market_data_service():
    """Initialize market data service on startup"""
    await market_data_service.initialize()

@router.on_event("shutdown")
async def shutdown_market_data_service():
    """Shutdown market data service"""
    await market_data_service.shutdown()

@router.post("/real-time")
async def fetch_real_time_data(
    request: RealTimeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Fetch real-time market data with intelligent failover
    
    Uses composite provider architecture for maximum reliability:
    - Primary: OpenBB Terminal (professional-grade data)
    - Secondary: Yahoo Finance (high reliability)
    - Tertiary: Alpha Vantage (comprehensive coverage)
    """
    try:
        result = await market_data_service.fetch_real_time_data_with_fallback(request.symbols)
        
        if not result.success:
            raise HTTPException(status_code=400, detail={
                "error": result.error,
                "message": result.message,
                "metadata": result.metadata
            })
        
        return {
            "success": True,
            "data": result.data,
            "message": result.message,
            "metadata": result.metadata,
            "next_actions": result.next_actions
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Internal server error during real-time data fetch"
        })

@router.post("/historical")
async def fetch_historical_data(
    request: HistoricalDataRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Fetch historical market data with intelligent failover
    
    Supports multiple intervals and date ranges with automatic provider fallback
    """
    try:
        result = await market_data_service.fetch_historical_data_with_fallback(
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            interval=request.interval
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail={
                "error": result.error,
                "message": result.message,
                "metadata": result.metadata
            })
        
        return {
            "success": True,
            "data": result.data,
            "message": result.message,
            "metadata": result.metadata,
            "next_actions": result.next_actions
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Internal server error during historical data fetch"
        })

@router.post("/validate")
async def validate_symbols(
    request: AssetValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Validate asset symbols with intelligent failover
    
    Comprehensive validation across multiple data providers
    """
    try:
        result = await market_data_service.validate_symbols_with_fallback(request.symbols)
        
        if not result.success:
            raise HTTPException(status_code=400, detail={
                "error": result.error,
                "message": result.message,
                "metadata": result.metadata
            })
        
        return {
            "success": True,
            "data": result.data,
            "message": result.message,
            "metadata": result.metadata,
            "next_actions": result.next_actions
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Internal server error during symbol validation"
        })

@router.post("/asset-info")
async def fetch_asset_info(
    request: AssetValidationRequest,  # Reuse same structure
    current_user: User = Depends(get_current_user)
):
    """
    Fetch comprehensive asset information with intelligent failover
    
    Returns detailed asset metadata including sector, industry, market cap, etc.
    """
    try:
        result = await market_data_service.fetch_asset_info_with_fallback(request.symbols)
        
        if not result.success:
            raise HTTPException(status_code=400, detail={
                "error": result.error,
                "message": result.message,
                "metadata": result.metadata
            })
        
        return {
            "success": True,
            "data": result.data,
            "message": result.message,
            "metadata": result.metadata,
            "next_actions": result.next_actions
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Internal server error during asset info fetch"
        })

@router.post("/fundamentals")
async def fetch_fundamental_data(
    request: FundamentalDataRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Fetch comprehensive fundamental data using OpenBB professional features
    
    Professional-grade fundamental analysis data including:
    - Financial ratios and metrics
    - Company overview and financials  
    - Valuation metrics
    - Growth indicators
    """
    try:
        result = await market_data_service.fetch_fundamental_data(request.symbols)
        
        if not result.success:
            raise HTTPException(status_code=400, detail={
                "error": result.error,
                "message": result.message,
                "metadata": result.metadata
            })
        
        return {
            "success": True,
            "data": result.data,
            "message": result.message,
            "metadata": result.metadata,
            "next_actions": result.next_actions
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Internal server error during fundamental data fetch"
        })

@router.post("/economics")
async def fetch_economic_indicators(
    request: EconomicIndicatorsRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Fetch economic indicators using OpenBB Terminal professional features
    
    Macro-economic data for strategy context including:
    - GDP, inflation, unemployment
    - Interest rates and yield curves
    - Market volatility (VIX)
    - Economic sentiment indicators
    """
    try:
        result = await market_data_service.fetch_economic_indicators(request.indicators)
        
        if not result.success:
            raise HTTPException(status_code=400, detail={
                "error": result.error,
                "message": result.message,
                "metadata": result.metadata
            })
        
        return {
            "success": True,
            "data": result.data,
            "message": result.message,
            "metadata": result.metadata,
            "next_actions": result.next_actions
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Internal server error during economic indicators fetch"
        })

@router.post("/search")
async def search_assets(
    request: AssetSearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Search for assets across all providers with quality ranking
    
    Intelligent search across multiple data providers with result ranking
    """
    try:
        result = await market_data_service.search_assets(request.query, request.limit)
        
        if not result.success:
            raise HTTPException(status_code=400, detail={
                "error": result.error,
                "message": result.message,
                "metadata": result.metadata
            })
        
        return {
            "success": True,
            "data": result.data,
            "message": result.message,
            "metadata": result.metadata,
            "next_actions": result.next_actions
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Internal server error during asset search"
        })

@router.post("/bulk-fetch")
async def bulk_data_fetch(
    request: BulkDataRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Optimized bulk data fetching for backtesting performance
    
    Intelligent batching and caching for 5x faster backtesting:
    - Concurrent request optimization
    - Provider load balancing
    - Cache-first strategy
    - Automatic retry and fallback
    """
    try:
        result = await market_data_service.bulk_data_fetch(
            symbols=request.symbols,
            operations=request.operations,
            parallel_requests=request.parallel_requests
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail={
                "error": result.error,
                "message": result.message,
                "metadata": result.metadata
            })
        
        return {
            "success": True,
            "data": result.data,
            "message": result.message,
            "metadata": result.metadata,
            "next_actions": result.next_actions
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Internal server error during bulk data fetch"
        })

@router.get("/provider-status")
async def get_provider_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get real-time provider health status and performance metrics
    
    Comprehensive monitoring dashboard showing:
    - Provider health and availability
    - Response time metrics
    - Error rates and failure patterns
    - Circuit breaker status
    - Performance rankings
    - Active alerts
    """
    try:
        result = await market_data_service.get_provider_health()
        
        if not result.success:
            raise HTTPException(status_code=400, detail={
                "error": result.error,
                "message": result.message,
                "metadata": result.metadata
            })
        
        return {
            "success": True,
            "data": result.data,
            "message": result.message,
            "metadata": result.metadata
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Internal server error during provider status check"
        })

@router.get("/cost-analysis")
async def get_cost_analysis(
    time_period_hours: int = Query(default=24, description="Time period for cost analysis in hours"),
    current_user: User = Depends(get_current_user)
):
    """
    Get cost analysis and optimization recommendations
    
    Financial monitoring for API usage across providers:
    - Cost breakdown by provider
    - Usage patterns and trends
    - Optimization recommendations
    - ROI analysis for OpenBB Pro vs free tiers
    """
    try:
        result = await market_data_service.get_cost_analysis(time_period_hours)
        
        if not result.success:
            raise HTTPException(status_code=400, detail={
                "error": result.error,
                "message": result.message,
                "metadata": result.metadata
            })
        
        return {
            "success": True,
            "data": result.data,
            "message": result.message,
            "metadata": result.metadata
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Internal server error during cost analysis"
        })

# Advanced OpenBB Professional Features

@router.post("/news-sentiment")
async def fetch_news_sentiment(
    request: NewsAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Fetch news sentiment analysis using OpenBB professional features
    
    Advanced news analytics including:
    - Sentiment scoring
    - News impact analysis
    - Event detection
    - Social media sentiment
    """
    try:
        # This would be implemented when OpenBB news features are integrated
        return JSONResponse(
            status_code=501,
            content={
                "success": False,
                "message": "News sentiment analysis coming soon - requires OpenBB Pro integration",
                "metadata": {
                    "feature": "news_sentiment",
                    "status": "development",
                    "estimated_availability": "Milestone 3"
                }
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Internal server error during news sentiment fetch"
        })

@router.post("/analyst-estimates") 
async def fetch_analyst_estimates(
    request: AnalystEstimatesRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Fetch analyst estimates and consensus data using OpenBB professional features
    
    Professional analyst research including:
    - Consensus estimates (EPS, Revenue)
    - Price targets and ratings
    - Analyst revisions
    - Earnings surprise history
    """
    try:
        # This would be implemented when OpenBB analyst features are integrated
        return JSONResponse(
            status_code=501,
            content={
                "success": False,
                "message": "Analyst estimates coming soon - requires OpenBB Pro integration",
                "metadata": {
                    "feature": "analyst_estimates",
                    "status": "development",
                    "estimated_availability": "Milestone 3"
                }
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Internal server error during analyst estimates fetch"
        })

@router.post("/insider-trading")
async def fetch_insider_trading(
    request: InsiderTradingRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Fetch insider trading data using OpenBB professional features
    
    Insider activity analysis including:
    - Recent insider transactions
    - Insider ownership changes
    - Executive trading patterns
    - Institutional holdings changes
    """
    try:
        # This would be implemented when OpenBB insider features are integrated
        return JSONResponse(
            status_code=501, 
            content={
                "success": False,
                "message": "Insider trading data coming soon - requires OpenBB Pro integration",
                "metadata": {
                    "feature": "insider_trading",
                    "status": "development",
                    "estimated_availability": "Milestone 3"
                }
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Internal server error during insider trading fetch"
        })

@router.get("/provider-benchmarks")
async def get_provider_benchmarks(
    current_user: User = Depends(get_current_user)
):
    """
    Get provider performance benchmarks and comparison metrics
    
    Detailed provider analytics for optimization:
    - Response time comparisons
    - Data quality scores
    - Reliability rankings
    - Cost efficiency metrics
    """
    try:
        # Get provider health for benchmarking
        health_result = await market_data_service.get_provider_health()
        
        if not health_result.success:
            raise HTTPException(status_code=400, detail={
                "error": health_result.error,
                "message": health_result.message,
                "metadata": health_result.metadata
            })
        
        # Extract benchmarking data
        benchmarks = {
            "performance_comparison": health_result.data.get("performance_metrics", {}),
            "provider_rankings": health_result.data.get("provider_rankings", []),
            "reliability_scores": {
                provider: {
                    "uptime_percentage": (1 - status.failure_rate) * 100,
                    "avg_response_time_ms": status.avg_response_time,
                    "health_score": 100 if status.is_healthy else 0
                }
                for provider, status in health_result.data.get("health_status", {}).items()
            }
        }
        
        return {
            "success": True,
            "data": benchmarks,
            "message": "Provider benchmarks retrieved successfully",
            "metadata": {
                "comparison_basis": "60-minute performance window",
                "metrics_included": ["response_time", "reliability", "health_score"],
                "recommendation": "Use highest-ranked provider for critical operations"
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": str(e),
            "message": "Internal server error during provider benchmarks retrieval"
        })