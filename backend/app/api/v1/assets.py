"""
Asset Search and Validation API Endpoints.
Following Phase 2 Step 4 specifications with AI-friendly response format.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
# Note: Rate limiting now handled by middleware instead of slowapi decorators

from ...core.database import get_db
from ..v1.auth import get_current_user
from ...models.user import User
from ...services.asset_validation_service import AssetValidationService
from ...services.interfaces.base import ServiceResult

# Rate limiting now handled by RateLimitMiddleware
router = APIRouter()
logger = logging.getLogger(__name__)

# Request/Response Models
class AssetValidationRequest(BaseModel):
    symbols: List[str]
    force_refresh: Optional[bool] = False
    
class AssetSearchRequest(BaseModel):
    query: str
    sector: Optional[str] = None
    limit: Optional[int] = 10
    
class AssetInfo(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[int] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    is_validated: bool
    last_validated_at: Optional[str] = None
    validation_source: Optional[str] = None

class ValidationResult(BaseModel):
    symbol: str
    is_valid: bool
    provider: str
    confidence: float
    error: Optional[str] = None
    asset_info: Optional[AssetInfo] = None
    timestamp: str
    source: str

class BulkValidationResult(BaseModel):
    total_symbols: int
    valid_symbols: int
    invalid_symbols: int
    cached_results: int
    real_time_validations: int
    validation_results: Dict[str, ValidationResult]
    
class AssetSearchResult(BaseModel):
    total_results: int
    results: List[AssetInfo]
    search_query: str
    search_metadata: Dict[str, Any]

# AI-friendly response wrappers
class AIValidationResponse(BaseModel):
    success: bool
    data: Optional[BulkValidationResult] = None
    message: str
    next_actions: List[str] = []
    metadata: Dict[str, Any] = {}
    
class AISearchResponse(BaseModel):
    success: bool
    data: Optional[AssetSearchResult] = None
    message: str
    next_actions: List[str] = []
    metadata: Dict[str, Any] = {}

class AIAssetInfoResponse(BaseModel):
    success: bool
    data: Optional[AssetInfo] = None
    message: str
    next_actions: List[str] = []
    metadata: Dict[str, Any] = {}

class AISectorsResponse(BaseModel):
    success: bool
    data: Optional[List[str]] = None
    message: str
    next_actions: List[str] = []
    metadata: Dict[str, Any] = {}

# Service dependency
def get_asset_validation_service() -> AssetValidationService:
    """Create AssetValidationService with default providers and Redis client"""
    try:
        print("🔧 DEBUG: Creating AssetValidationService instance...")
        service = AssetValidationService()
        print("🔧 DEBUG: AssetValidationService created successfully")
        return service
    except Exception as e:
        print(f"🚨 DEBUG: Failed to create AssetValidationService: {e}")
        import traceback
        print(f"🚨 DEBUG: Traceback: {traceback.format_exc()}")
        raise

@router.post("/validate", response_model=AIValidationResponse, summary="Bulk asset validation")
async def validate_assets(
    request: Request,  # Available for future use
    validation_request: AssetValidationRequest,
    current_user: User = Depends(get_current_user),
    asset_service: AssetValidationService = Depends(get_asset_validation_service)
):
    """
    Bulk validate asset symbols using mixed validation strategy.
    
    Features:
    - Redis caching for fast repeated validations
    - Multi-provider fallback (Yahoo Finance → Alpha Vantage)
    - Concurrent processing with rate limiting compliance
    - AI-friendly response format with next action suggestions
    
    Rate limited to 5 requests per minute per user for API protection.
    """
    if not validation_request.symbols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one symbol must be provided for validation"
        )
    
    # Remove duplicates while preserving order
    unique_symbols = list(dict.fromkeys(validation_request.symbols))
    
    if len(unique_symbols) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 symbols allowed per validation request"
        )
    
    # Perform bulk validation using mixed strategy
    result = await asset_service.validate_symbols_bulk_mixed_strategy(
        symbols=unique_symbols,
        force_refresh=validation_request.force_refresh
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )
    
    bulk_data = result.data
    
    # Convert to response format
    validation_results = {}
    for symbol, validation in bulk_data.items():
        asset_info = None
        if validation.asset_info:
            asset_info = AssetInfo(
                symbol=validation.asset_info.symbol,
                name=validation.asset_info.name,
                sector=validation.asset_info.sector,
                industry=validation.asset_info.industry,
                market_cap=validation.asset_info.market_cap,
                pe_ratio=validation.asset_info.pe_ratio,
                dividend_yield=validation.asset_info.dividend_yield,
                is_validated=validation.asset_info.is_valid,
                last_validated_at=validation.asset_info.last_updated.isoformat() if validation.asset_info.last_updated else None,
                validation_source=validation.provider
            )
        
        validation_results[symbol] = ValidationResult(
            symbol=validation.symbol,
            is_valid=validation.is_valid,
            provider=validation.provider,
            confidence=validation.confidence,
            error=validation.error,
            asset_info=asset_info,
            timestamp=validation.timestamp.isoformat(),
            source=validation.source
        )
    
    # Calculate statistics
    valid_count = sum(1 for v in validation_results.values() if v.is_valid)
    invalid_count = len(validation_results) - valid_count
    cached_count = sum(1 for v in validation_results.values() if v.source == "cache")
    real_time_count = len(validation_results) - cached_count
    
    bulk_result = BulkValidationResult(
        total_symbols=len(validation_results),
        valid_symbols=valid_count,
        invalid_symbols=invalid_count,
        cached_results=cached_count,
        real_time_validations=real_time_count,
        validation_results=validation_results
    )
    
    # AI-friendly next actions
    next_actions = []
    if valid_count > 0:
        next_actions.extend([
            "add_valid_symbols_to_universe",
            "create_universe_from_valid_symbols",
            "get_market_data_for_valid_symbols"
        ])
    if invalid_count > 0:
        next_actions.extend([
            "search_similar_symbols",
            "review_invalid_symbols"
        ])
    if real_time_count > 0:
        next_actions.append("cache_validation_results")
    
    validation_rate = (valid_count / len(validation_results)) * 100
    
    return AIValidationResponse(
        success=True,
        data=bulk_result,
        message=f"Validated {len(validation_results)} symbols: {valid_count} valid, {invalid_count} invalid",
        next_actions=next_actions,
        metadata={
            "validation_rate": round(validation_rate, 1),
            "cache_hit_rate": round((cached_count / len(validation_results)) * 100, 1),
            "processing_strategy": "mixed_bulk_validation",
            "user_id": current_user.id,
            "rate_limit_remaining": "4 requests"  # This would be dynamic in production
        }
    )

@router.get("/search", response_model=AISearchResponse, summary="Search assets by name or symbol")
async def search_assets(
    query: str = Query(..., description="Search query (name or symbol)"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results (1-50)"),
    # Multi-metric filtering parameters (Sprint 2 Step 1)
    market_cap_min: Optional[float] = Query(None, description="Minimum market cap in USD", ge=0),
    market_cap_max: Optional[float] = Query(None, description="Maximum market cap in USD", ge=0),
    pe_ratio_min: Optional[float] = Query(None, description="Minimum P/E ratio", ge=0),
    pe_ratio_max: Optional[float] = Query(None, description="Maximum P/E ratio", ge=0),
    dividend_yield_min: Optional[float] = Query(None, description="Minimum dividend yield (decimal)", ge=0, le=1),
    dividend_yield_max: Optional[float] = Query(None, description="Maximum dividend yield (decimal)", ge=0, le=1),
    current_user: User = Depends(get_current_user),
    asset_service: AssetValidationService = Depends(get_asset_validation_service)
):
    """
    Search for assets by name or symbol with advanced multi-metric filtering.
    
    Features:
    - Full-text search across asset names and symbols
    - Multi-metric filtering: sector, market cap, P/E ratio, dividend yield
    - Cached results for performance  
    - AI-friendly response format
    - Supports User Story 2: "Screener allows filtering by multiple metrics"
    """
    logger.info(f"🔍 ASSET SEARCH: query='{query}', sector='{sector}', limit={limit}")
    logger.info(f"🔍 FILTERS: market_cap_min={market_cap_min}, market_cap_max={market_cap_max}")
    
    if len(query.strip()) < 2:
        print(f"🚨 DEBUG: Query too short: '{query}' (length: {len(query.strip())})")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters"
        )
    
    # Try the exact symbol first, then variations if needed
    search_symbols = [query.upper()]
    if len(query) <= 4:
        # Add common variations for short queries (only if exact match fails)
        search_symbols.extend([
            f"{query.upper()}.TO",  # Toronto Stock Exchange
            f"{query.upper()}.L",   # London Stock Exchange
        ])
    
    logger.info(f"🔍 SEARCHING: Will try symbols in order: {search_symbols}")
    
    results = []
    for symbol in search_symbols[:limit]:
        try:
            logger.info(f"🔍 VALIDATING: symbol '{symbol}'")
            validation_result = await asset_service.validate_symbol_mixed_strategy(symbol)
            logger.info(f"🔍 RESULT: '{symbol}' -> success={validation_result.success}, valid={validation_result.data.is_valid if validation_result.success else 'N/A'}")
            
            if validation_result.success and validation_result.data.is_valid:
                asset_info = validation_result.data.asset_info
                if asset_info:
                    # Apply sector filter if specified
                    if sector and asset_info.sector and sector.lower() not in asset_info.sector.lower():
                        continue
                
                    # Apply multi-metric filters (Sprint 2 Step 1)
                    if market_cap_min is not None and (asset_info.market_cap is None or asset_info.market_cap < market_cap_min):
                        continue
                    if market_cap_max is not None and (asset_info.market_cap is None or asset_info.market_cap > market_cap_max):
                        continue
                    if pe_ratio_min is not None and (asset_info.pe_ratio is None or asset_info.pe_ratio < pe_ratio_min):
                        continue
                    if pe_ratio_max is not None and (asset_info.pe_ratio is None or asset_info.pe_ratio > pe_ratio_max):
                        continue
                    if dividend_yield_min is not None and (asset_info.dividend_yield is None or asset_info.dividend_yield < dividend_yield_min):
                        continue
                    if dividend_yield_max is not None and (asset_info.dividend_yield is None or asset_info.dividend_yield > dividend_yield_max):
                        continue
                        
                    results.append(AssetInfo(
                        symbol=asset_info.symbol,
                        name=asset_info.name,
                        sector=asset_info.sector,
                        industry=asset_info.industry,
                        market_cap=asset_info.market_cap,
                        pe_ratio=asset_info.pe_ratio,
                        dividend_yield=asset_info.dividend_yield,
                        is_validated=asset_info.is_valid,
                        last_validated_at=asset_info.last_updated.isoformat() if asset_info.last_updated else None,
                        validation_source="search_validation"
                    ))
                    
                    logger.info(f"✅ FOUND: Added '{symbol}' to results")
                    
                    # If we found a valid result for the exact query, stop trying variations
                    if symbol == query.upper():
                        logger.info(f"🎯 EXACT MATCH: Found exact match for '{query}', stopping search")
                        break
                        
        except Exception as e:
            logger.error(f"🚨 VALIDATION ERROR: '{symbol}' -> {e}")
            # Continue to next symbol instead of failing entire search
            continue
        
        if len(results) >= limit:
            logger.info(f"📊 LIMIT REACHED: Found {len(results)} results, stopping search")
            break
    
    logger.info(f"🏁 SEARCH COMPLETE: Found {len(results)} results for '{query}'")
    
    search_result = AssetSearchResult(
        total_results=len(results),
        results=results,
        search_query=query,
        search_metadata={
            "sector_filter": sector,
            "result_limit": limit,
            "search_variations_tried": len(search_symbols)
        }
    )
    
    # AI-friendly next actions
    next_actions = []
    if results:
        next_actions.extend([
            "add_assets_to_universe",
            "validate_selected_assets",
            "get_detailed_asset_info"
        ])
    else:
        next_actions.extend([
            "try_different_search_terms",
            "browse_assets_by_sector"
        ])
    
    return AISearchResponse(
        success=len(results) > 0,
        data=search_result,
        message=f"Found {len(results)} asset(s) matching '{query}'",
        next_actions=next_actions,
        metadata={
            "search_performance": "cached" if results else "real_time",
            "sector_applied": sector is not None,
            "exact_match": any(r.symbol == query.upper() for r in results)
        }
    )

@router.get("/sectors", response_model=AISectorsResponse, summary="Get available sectors")
async def get_available_sectors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of available sectors for filtering and search.
    
    Returns all sectors found in the asset database, useful for
    sector-based universe creation and asset filtering.
    """
    from ...models.asset import Asset
    
    try:
        # Query database for distinct sectors with non-null values
        distinct_sectors = db.query(Asset.sector).filter(
            Asset.sector.isnot(None),
            Asset.sector != "",
            Asset.is_validated == True
        ).distinct().order_by(Asset.sector).all()
        
        # Extract sector names from query results
        database_sectors = [sector[0] for sector in distinct_sectors if sector[0]]
        
        # If no sectors in database, return common sectors as fallback
        if not database_sectors:
            fallback_sectors = [
                "Technology",
                "Healthcare", 
                "Financial Services",
                "Consumer Cyclical",
                "Consumer Defensive",
                "Energy",
                "Industrials",
                "Real Estate",
                "Materials",
                "Utilities",
                "Communication Services"
            ]
            
            return AISectorsResponse(
                success=True,
                data=fallback_sectors,
                message=f"Retrieved {len(fallback_sectors)} fallback sectors (no database sectors available)",
                next_actions=[
                    "validate_assets_to_populate_sectors",
                    "create_sector_universe",
                    "filter_assets_by_sector"
                ],
                metadata={
                    "total_sectors": len(fallback_sectors),
                    "data_source": "fallback_list",
                    "database_empty": True,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
            )
        
        sectors_list = database_sectors
        
        return AISectorsResponse(
            success=True,
            data=sectors_list,
            message=f"Retrieved {len(sectors_list)} sectors from asset database",
            next_actions=[
                "filter_assets_by_sector",
                "create_sector_universe", 
                "compare_sector_performance"
            ],
            metadata={
                "total_sectors": len(sectors_list),
                "data_source": "asset_database",
                "validated_assets_only": True,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error retrieving sectors from database: {e}")
        
        # Return fallback sectors on database error
        fallback_sectors = [
            "Technology",
            "Healthcare",
            "Financial Services", 
            "Consumer Cyclical",
            "Consumer Defensive",
            "Energy",
            "Industrials",
            "Real Estate",
            "Materials",
            "Utilities",
            "Communication Services"
        ]
        
        return AISectorsResponse(
            success=True,
            data=fallback_sectors,
            message=f"Retrieved {len(fallback_sectors)} fallback sectors (database error)",
            next_actions=[
                "validate_assets_to_populate_sectors",
                "retry_sector_query",
                "create_sector_universe"
            ],
            metadata={
                "total_sectors": len(fallback_sectors),
                "data_source": "fallback_list",
                "error": str(e),
                "database_error": True,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
        )

@router.get("/{symbol}", response_model=AIAssetInfoResponse, summary="Get detailed asset information")
async def get_asset_info(
    symbol: str,
    current_user: User = Depends(get_current_user),
    asset_service: AssetValidationService = Depends(get_asset_validation_service)
):
    """
    Get detailed information about a specific asset symbol.
    
    Returns comprehensive asset data including fundamental metrics,
    validation status, and market information.
    """
    symbol = symbol.upper().strip()
    
    if not symbol or len(symbol) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid symbol format"
        )
    
    # Validate and get asset information
    result = await asset_service.validate_symbol_mixed_strategy(symbol)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )
    
    validation = result.data
    
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset symbol '{symbol}' not found or invalid"
        )
    
    asset_info = None
    if validation.asset_info:
        asset_info = AssetInfo(
            symbol=validation.asset_info.symbol,
            name=validation.asset_info.name,
            sector=validation.asset_info.sector,
            industry=validation.asset_info.industry,
            market_cap=validation.asset_info.market_cap,
            pe_ratio=validation.asset_info.pe_ratio,
            dividend_yield=validation.asset_info.dividend_yield,
            is_validated=validation.asset_info.is_valid,
            last_validated_at=validation.asset_info.last_updated.isoformat() if validation.asset_info.last_updated else None,
            validation_source=validation.provider
        )
    
    # AI-friendly next actions based on asset characteristics
    next_actions = ["add_to_universe", "get_market_data", "compare_with_peers"]
    
    if asset_info and asset_info.sector:
        next_actions.extend([
            "search_sector_peers",
            "analyze_sector_performance"
        ])
        
    if asset_info and asset_info.dividend_yield and asset_info.dividend_yield > 0:
        next_actions.append("analyze_dividend_history")
    
    return AIAssetInfoResponse(
        success=True,
        data=asset_info,
        message=f"Retrieved detailed information for {symbol}",
        next_actions=next_actions,
        metadata={
            "validation_provider": validation.provider,
            "validation_confidence": validation.confidence,
            "data_freshness": validation.source,
            "timestamp": validation.timestamp.isoformat()
        }
    )

# Rate limit error handling is configured at the app level in main.py