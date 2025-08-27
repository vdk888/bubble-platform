"""
Universe Management API Endpoints.
Following Phase 2 Step 4 specifications with AI-friendly response format.
"""
from typing import List, Optional, Dict, Any
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...core.database import get_db
from ..v1.auth import get_current_user
from ...models.user import User
from ...services.universe_service import UniverseService
from ...services.temporal_universe_service import TemporalUniverseService
from ...services.interfaces.base import ServiceResult

router = APIRouter()

# Response Models for API Documentation
class UniverseResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    asset_count: int
    symbols: List[str]
    assets: List[Dict[str, Any]] = []
    turnover_rate: Optional[float] = None
    created_at: str
    updated_at: str

class UniverseCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    symbols: Optional[List[str]] = None

class UniverseUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class AssetOperationRequest(BaseModel):
    symbols: List[str]
    
class AssetOperationResult(BaseModel):
    successful_symbols: List[str]
    failed_symbols: List[str]
    added_count: int
    total_requested: int

# AI-friendly response wrapper
class AIUniverseResponse(BaseModel):
    success: bool
    data: Optional[UniverseResponse] = None
    message: str
    next_actions: List[str] = []
    metadata: dict = {}

class AIUniverseListResponse(BaseModel):
    success: bool
    data: Optional[List[UniverseResponse]] = None
    message: str
    next_actions: List[str] = []
    metadata: dict = {}

class AIAssetOperationResponse(BaseModel):
    success: bool
    data: Optional[AssetOperationResult] = None
    message: str
    next_actions: List[str] = []
    metadata: dict = {}

# Temporal API Response Models
class UniverseSnapshotResponse(BaseModel):
    id: str
    universe_id: str
    snapshot_date: str
    assets: List[Dict[str, Any]]
    turnover_rate: Optional[float] = None
    assets_added: Optional[List[str]] = None
    assets_removed: Optional[List[str]] = None
    screening_criteria: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    created_at: str

class UniverseTimelineResponse(BaseModel):
    success: bool
    data: Optional[List[UniverseSnapshotResponse]] = None
    message: str
    next_actions: List[str] = []
    metadata: dict = {}

class UniverseCompositionResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None  # Point-in-time composition data
    message: str
    next_actions: List[str] = []
    metadata: dict = {}

class SnapshotCreateRequest(BaseModel):
    snapshot_date: Optional[str] = None  # ISO date string, defaults to today
    screening_criteria: Optional[Dict[str, Any]] = None
    force_recreation: Optional[bool] = False

class BackfillRequest(BaseModel):
    start_date: str  # ISO date string
    end_date: str    # ISO date string
    frequency: Optional[str] = "monthly"  # daily, weekly, monthly, quarterly

# Initialize services (dependency injection pattern)
def get_universe_service(db: Session = Depends(get_db)) -> UniverseService:
    return UniverseService(db)

def get_temporal_universe_service(db: Session = Depends(get_db)) -> TemporalUniverseService:
    return TemporalUniverseService(db)

@router.get("/", response_model=AIUniverseListResponse, summary="List user's universes")
async def list_universes(
    current_user: User = Depends(get_current_user),
    universe_service: UniverseService = Depends(get_universe_service)
):
    """
    List all universes for the authenticated user with AI-friendly response format.
    
    Returns:
    - AI-optimized response with next_actions suggestions
    - Universe metadata including asset counts and turnover rates
    - Structured format suitable for AI tool calling
    """
    result = await universe_service.get_user_universes(current_user.id)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )
    
    # Convert to response format
    universe_responses = []
    for universe in result.data:
        # Handle both dict and object formats from service
        if isinstance(universe, dict):
            # Convert datetime objects to ISO strings if needed
            created_at = universe["created_at"]
            if hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
            
            updated_at = universe["updated_at"]
            if hasattr(updated_at, 'isoformat'):
                updated_at = updated_at.isoformat()
                
            universe_responses.append(UniverseResponse(
                id=universe["id"],
                name=universe["name"],
                description=universe["description"],
                asset_count=len(universe.get("symbols", [])),
                symbols=universe.get("symbols", []),
                assets=universe.get("assets", []),
                turnover_rate=universe.get("turnover_rate", 0.0),
                created_at=created_at,
                updated_at=updated_at
            ))
        else:
            # Object format
            universe_responses.append(UniverseResponse(
                id=universe.id,
                name=universe.name,
                description=universe.description,
                asset_count=len(universe.get_symbols()),
                symbols=universe.get_symbols(),
                assets=universe.get_assets(),
                turnover_rate=universe.turnover_rate,
                created_at=universe.created_at.isoformat(),
                updated_at=universe.updated_at.isoformat()
            ))
    
    # AI-friendly next actions
    next_actions = ["create_universe"]
    if universe_responses:
        next_actions.extend([
            "add_assets_to_universe",
            "create_strategy_from_universe",
            "view_universe_details"
        ])
    
    return AIUniverseListResponse(
        success=True,
        data=universe_responses,
        message=f"Retrieved {len(universe_responses)} universe(s) for user",
        next_actions=next_actions,
        metadata={
            "total_universes": len(universe_responses),
            "total_unique_assets": len(set(
                symbol for universe_response in universe_responses
                for symbol in universe_response.symbols
            )) if universe_responses else 0,
            "user_id": current_user.id
        }
    )

@router.post("/", response_model=AIUniverseResponse, status_code=status.HTTP_201_CREATED, summary="Create a new universe")
async def create_universe(
    universe_data: UniverseCreateRequest,
    current_user: User = Depends(get_current_user),
    universe_service: UniverseService = Depends(get_universe_service)
):
    """
    Create a new investment universe for the authenticated user.
    
    Supports AI tool calling with structured request/response format.
    Initial symbols can be provided or added later via asset operations.
    """
    result = await universe_service.create_universe(
        user_id=current_user.id,
        name=universe_data.name,
        description=universe_data.description or ""
    )
    
    if not result.success:
        if "already exists" in result.error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error
            )
    
    universe = result.data
    
    # Handle case where universe might be a dict (from create_universe) or object (from get_universe_by_id)
    universe_id = universe["id"] if isinstance(universe, dict) else universe.id
    
    # Add initial symbols if provided
    if universe_data.symbols:
        add_result = await universe_service.add_assets_to_universe_api(
            universe_id=universe_id,
            asset_symbols=universe_data.symbols
        )
        # Update universe with assets added - refresh to get updated asset count
        if add_result.success:
            # Always refresh universe to get updated asset count as model object
            updated_result = await universe_service.get_universe_by_id(universe_id)
            if updated_result.success:
                universe = updated_result.data  # Now guaranteed to be model object
    
    # Ensure we have a model object, not a dict
    if isinstance(universe, dict):
        # If still a dict, get the actual model object
        refresh_result = await universe_service.get_universe_by_id(universe_id)
        if refresh_result.success:
            universe = refresh_result.data
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created universe"
            )
    
    response_data = UniverseResponse(
        id=universe.id,
        name=universe.name,
        description=universe.description,
        asset_count=len(universe.get_symbols()),
        symbols=universe.get_symbols(),
        assets=universe.get_assets(),
        turnover_rate=universe.turnover_rate,
        created_at=universe.created_at.isoformat(),
        updated_at=universe.updated_at.isoformat()
    )
    
    # AI-friendly next actions based on current state
    next_actions = []
    if not universe.get_symbols():
        next_actions.extend(["add_assets_to_universe", "search_assets_by_sector"])
    else:
        next_actions.extend([
            "create_strategy_from_universe",
            "validate_universe_assets",
            "add_more_assets"
        ])
    
    return AIUniverseResponse(
        success=True,
        data=response_data,
        message=f"Universe '{universe.name}' created successfully",
        next_actions=next_actions,
        metadata={
            "universe_id": universe.id,
            "initial_symbols_added": len(universe_data.symbols) if universe_data.symbols else 0,
            "creation_method": "api_direct"
        }
    )

@router.get("/{universe_id}", response_model=AIUniverseResponse, summary="Get universe details")
async def get_universe(
    universe_id: str,
    current_user: User = Depends(get_current_user),
    universe_service: UniverseService = Depends(get_universe_service)
):
    """
    Get detailed information about a specific universe.
    
    Returns comprehensive universe data suitable for AI analysis and tool calling.
    """
    result = await universe_service.get_universe_by_id(universe_id)
    
    if not result.success:
        if "not found" in result.error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error
            )
    
    universe = result.data
    
    # Verify user ownership (multi-tenant security)
    if universe.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Universe belongs to another user"
        )
    
    response_data = UniverseResponse(
        id=universe.id,
        name=universe.name,
        description=universe.description,
        asset_count=len(universe.get_symbols()),
        symbols=universe.get_symbols(),
        assets=universe.get_assets(),
        turnover_rate=universe.turnover_rate,
        created_at=universe.created_at.isoformat(),
        updated_at=universe.updated_at.isoformat()
    )
    
    # AI-friendly next actions based on universe state
    next_actions = []
    if universe.get_symbols():
        next_actions.extend([
            "create_strategy_from_universe",
            "validate_universe_assets",
            "calculate_universe_performance",
            "modify_universe_assets"
        ])
    else:
        next_actions.extend([
            "add_assets_to_universe",
            "search_assets_by_sector"
        ])
    
    return AIUniverseResponse(
        success=True,
        data=response_data,
        message=f"Retrieved universe '{universe.name}' details",
        next_actions=next_actions,
        metadata={
            "universe_id": universe.id,
            "asset_diversity": len(set(universe.get_symbols())),
            "last_modified": universe.updated_at.isoformat(),
            "has_turnover_data": universe.turnover_rate is not None
        }
    )

@router.put("/{universe_id}", response_model=AIUniverseResponse, summary="Update universe")
async def update_universe(
    universe_id: str,
    update_data: UniverseUpdateRequest,
    current_user: User = Depends(get_current_user),
    universe_service: UniverseService = Depends(get_universe_service)
):
    """
    Update universe metadata (name and description).
    
    Asset modifications are handled via separate asset operation endpoints.
    """
    # First verify universe exists and user owns it
    get_result = await universe_service.get_universe_by_id(universe_id)
    
    if not get_result.success:
        if "not found" in get_result.error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_result.error
            )
    
    universe = get_result.data
    if universe.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Universe belongs to another user"
        )
    
    # Perform update
    result = await universe_service.update_universe_api(
        universe_id=universe_id,
        name=update_data.name,
        description=update_data.description
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )
    
    updated_universe = result.data
    
    response_data = UniverseResponse(
        id=updated_universe.id,
        name=updated_universe.name,
        description=updated_universe.description,
        asset_count=len(updated_universe.get_symbols()),
        symbols=updated_universe.get_symbols(),
        assets=updated_universe.get_assets(),
        turnover_rate=updated_universe.turnover_rate,
        created_at=updated_universe.created_at.isoformat(),
        updated_at=updated_universe.updated_at.isoformat()
    )
    
    return AIUniverseResponse(
        success=True,
        data=response_data,
        message=f"Universe '{updated_universe.name}' updated successfully",
        next_actions=[
            "add_assets_to_universe",
            "create_strategy_from_universe",
            "view_universe_performance"
        ],
        metadata={
            "universe_id": updated_universe.id,
            "fields_updated": [
                field for field, value in [
                    ("name", update_data.name),
                    ("description", update_data.description)
                ] if value is not None
            ]
        }
    )

@router.delete("/{universe_id}", summary="Delete universe")
async def delete_universe(
    universe_id: str,
    current_user: User = Depends(get_current_user),
    universe_service: UniverseService = Depends(get_universe_service)
):
    """
    Delete a universe and all its relationships.
    
    This is a destructive operation with cascading effects on strategies and portfolios.
    """
    # Verify ownership before deletion
    get_result = await universe_service.get_universe_by_id(universe_id)
    
    if not get_result.success:
        if "not found" in get_result.error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_result.error
            )
    
    universe = get_result.data
    if universe.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Universe belongs to another user"
        )
    
    # Perform deletion
    result = await universe_service.delete_universe_api(universe_id)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )
    
    return {
        "success": True,
        "message": f"Universe '{universe.name}' deleted successfully",
        "next_actions": [
            "create_new_universe",
            "view_remaining_universes"
        ],
        "metadata": {
            "deleted_universe_id": universe_id,
            "cascade_effects": "Strategies and portfolios using this universe may be affected"
        }
    }

@router.post("/{universe_id}/assets", response_model=AIAssetOperationResponse, summary="Add assets to universe", status_code=status.HTTP_201_CREATED)
async def add_assets(
    universe_id: str,
    assets_data: AssetOperationRequest,
    current_user: User = Depends(get_current_user),
    universe_service: UniverseService = Depends(get_universe_service)
):
    """
    Add assets to an existing universe with validation and bulk processing.
    
    Features:
    - Real-time asset validation via mixed strategy
    - Bulk processing with detailed success/failure tracking
    - AI-friendly response format with next action suggestions
    """
    # Verify universe ownership
    get_result = await universe_service.get_universe_by_id(universe_id)
    
    if not get_result.success:
        if "not found" in get_result.error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_result.error
            )
    
    universe = get_result.data
    if universe.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Universe belongs to another user"
        )
    
    # Add assets with bulk processing
    result = await universe_service.add_assets_to_universe_api(
        universe_id=universe_id,
        asset_symbols=assets_data.symbols
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )
    
    bulk_result = result.data
    
    # Format response
    operation_result = AssetOperationResult(
        successful_symbols=[item["symbol"] for item in bulk_result.get("successful", [])],
        failed_symbols=[item["symbol"] for item in bulk_result.get("failed", [])],
        added_count=bulk_result.get("success_count", 0),
        total_requested=len(assets_data.symbols)
    )
    
    # AI-friendly next actions
    next_actions = []
    if operation_result.successful_symbols:
        next_actions.extend([
            "validate_added_assets",
            "create_strategy_from_universe",
            "view_updated_universe"
        ])
    if operation_result.failed_symbols:
        next_actions.append("retry_failed_symbols")
    
    # Handle edge case following "Never trust user input" principle
    success_rate = (operation_result.added_count / operation_result.total_requested * 100) if operation_result.total_requested > 0 else 0
    
    return AIAssetOperationResponse(
        success=True,  # Adding 0 assets is a valid operation - following "Never trust user input" graceful handling
        data=operation_result,
        message=f"Added {operation_result.added_count}/{operation_result.total_requested} assets to universe",
        next_actions=next_actions,
        metadata={
            "universe_id": universe_id,
            "universe_name": universe.name,
            "success_rate": round(success_rate, 1),
            "failed_symbols": operation_result.failed_symbols,
            "validation_strategy": "mixed_real_time"
        }
    )

@router.delete("/{universe_id}/assets", response_model=AIAssetOperationResponse, summary="Remove assets from universe")
async def remove_assets(
    universe_id: str,
    assets_data: AssetOperationRequest,
    current_user: User = Depends(get_current_user),
    universe_service: UniverseService = Depends(get_universe_service)
):
    """
    Remove assets from an existing universe with bulk processing support.
    """
    # Verify universe ownership
    get_result = await universe_service.get_universe_by_id(universe_id)
    
    if not get_result.success:
        if "not found" in get_result.error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_result.error
            )
    
    universe = get_result.data
    if universe.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Universe belongs to another user"
        )
    
    # Remove assets
    result = await universe_service.remove_assets_from_universe_api(
        universe_id=universe_id,
        asset_symbols=assets_data.symbols
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )
    
    bulk_result = result.data
    
    operation_result = AssetOperationResult(
        successful_symbols=[item["symbol"] for item in bulk_result.get("successful", [])],
        failed_symbols=[item["symbol"] for item in bulk_result.get("failed", [])],
        added_count=bulk_result.get("success_count", 0),  # Actually removed count
        total_requested=len(assets_data.symbols)
    )
    
    return AIAssetOperationResponse(
        success=operation_result.added_count > 0,
        data=operation_result,
        message=f"Removed {operation_result.added_count}/{operation_result.total_requested} assets from universe",
        next_actions=[
            "view_updated_universe",
            "add_replacement_assets",
            "recalculate_turnover_rate"
        ],
        metadata={
            "universe_id": universe_id,
            "universe_name": universe.name,
            "operation_type": "removal",
            "turnover_impact": bulk_result.get("success_count", 0) > 0
        }
    )

# =========================================================================
# TEMPORAL UNIVERSE ENDPOINTS - Sprint 2.5 Part D Implementation
# =========================================================================

@router.get("/{universe_id}/timeline", response_model=UniverseTimelineResponse, summary="Get universe evolution timeline")
async def get_universe_timeline(
    universe_id: str,
    start_date: Optional[date] = Query(None, description="Start date for timeline (ISO format)"),
    end_date: Optional[date] = Query(None, description="End date for timeline (ISO format)"),
    frequency: Optional[str] = Query("monthly", description="Timeline frequency: daily, weekly, monthly, quarterly"),
    current_user: User = Depends(get_current_user),
    universe_service: UniverseService = Depends(get_universe_service)
):
    """
    Get universe evolution timeline showing historical snapshots.
    
    Returns temporal view of universe composition changes over time,
    enabling analysis of turnover patterns and evolution trends.
    
    Features:
    - Configurable date range and frequency
    - Turnover analysis between periods
    - Asset addition/removal tracking
    - Performance metrics evolution
    """
    # Verify universe ownership
    get_result = await universe_service.get_universe_by_id(universe_id)
    
    if not get_result.success:
        if "not found" in get_result.error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_result.error
            )
    
    universe = get_result.data
    if universe.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Universe belongs to another user"
        )
    
    # Get timeline data using existing temporal service method
    result = await universe_service.get_universe_timeline(
        universe_id=universe_id,
        start_date=start_date,
        end_date=end_date,
        frequency=frequency
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )
    
    timeline_data = result.data
    snapshots = timeline_data.get("snapshots", [])
    
    # Convert to response format
    snapshot_responses = []
    for snapshot in snapshots:
        # Handle both dict and object formats from service
        if isinstance(snapshot, dict):
            snapshot_responses.append(UniverseSnapshotResponse(
                id=snapshot["id"],
                universe_id=snapshot["universe_id"],
                snapshot_date=snapshot["snapshot_date"],
                assets=snapshot["assets"],
                turnover_rate=snapshot.get("turnover_rate"),
                assets_added=snapshot.get("assets_added"),
                assets_removed=snapshot.get("assets_removed"),
                screening_criteria=snapshot.get("screening_criteria"),
                performance_metrics=snapshot.get("performance_metrics"),
                created_at=snapshot["created_at"]
            ))
        else:
            # Object format
            snapshot_responses.append(UniverseSnapshotResponse(
                id=snapshot.id,
                universe_id=snapshot.universe_id,
                snapshot_date=snapshot.snapshot_date.isoformat(),
                assets=snapshot.assets,
                turnover_rate=float(snapshot.turnover_rate) if snapshot.turnover_rate else None,
                assets_added=snapshot.assets_added,
                assets_removed=snapshot.assets_removed,
                screening_criteria=snapshot.screening_criteria,
                performance_metrics=snapshot.performance_metrics,
                created_at=snapshot.created_at.isoformat()
            ))
    
    # AI-friendly next actions
    next_actions = ["view_universe_details"]
    if snapshot_responses:
        next_actions.extend([
            "create_universe_snapshot",
            "analyze_turnover_patterns",
            "run_backtest_with_temporal_data",
            "view_composition_at_date"
        ])
    else:
        next_actions.extend([
            "create_universe_snapshot",
            "backfill_universe_history"
        ])
    
    return UniverseTimelineResponse(
        success=True,
        data=snapshot_responses,
        message=f"Retrieved {len(snapshot_responses)} snapshot(s) for universe timeline",
        next_actions=next_actions,
        metadata={
            "universe_id": universe_id,
            "universe_name": universe.name,
            "timeline_period": f"{start_date or 'earliest'} to {end_date or 'latest'}",
            "frequency": frequency,
            "total_snapshots": len(snapshot_responses),
            "date_range": timeline_data.get("date_range", {}),
            "turnover_stats": timeline_data.get("turnover_analysis", {})
        }
    )

@router.get("/{universe_id}/snapshots", response_model=UniverseTimelineResponse, summary="Get all universe snapshots")
async def get_universe_snapshots(
    universe_id: str,
    limit: Optional[int] = Query(50, description="Maximum number of snapshots to return"),
    offset: Optional[int] = Query(0, description="Number of snapshots to skip"),
    current_user: User = Depends(get_current_user),
    universe_service: UniverseService = Depends(get_universe_service)
):
    """
    Get all historical snapshots for a universe with pagination support.
    
    Returns complete snapshot history for analysis and debugging.
    Useful for understanding universe evolution patterns and data quality.
    """
    # Verify universe ownership
    get_result = await universe_service.get_universe_by_id(universe_id)
    
    if not get_result.success:
        if "not found" in get_result.error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_result.error
            )
    
    universe = get_result.data
    if universe.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Universe belongs to another user"
        )
    
    # Get all snapshots using timeline method with no date restrictions
    result = await universe_service.get_universe_timeline(
        universe_id=universe_id,
        start_date=None,  # Get all historical data
        end_date=None,
        frequency="all"  # Get all snapshots regardless of frequency
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )
    
    timeline_data = result.data
    all_snapshots = timeline_data.get("snapshots", [])
    
    # Apply pagination
    total_snapshots = len(all_snapshots)
    paginated_snapshots = all_snapshots[offset:offset + limit]
    
    # Convert to response format
    snapshot_responses = []
    for snapshot in paginated_snapshots:
        if isinstance(snapshot, dict):
            snapshot_responses.append(UniverseSnapshotResponse(
                id=snapshot["id"],
                universe_id=snapshot["universe_id"],
                snapshot_date=snapshot["snapshot_date"],
                assets=snapshot["assets"],
                turnover_rate=snapshot.get("turnover_rate"),
                assets_added=snapshot.get("assets_added"),
                assets_removed=snapshot.get("assets_removed"),
                screening_criteria=snapshot.get("screening_criteria"),
                performance_metrics=snapshot.get("performance_metrics"),
                created_at=snapshot["created_at"]
            ))
        else:
            snapshot_responses.append(UniverseSnapshotResponse(
                id=snapshot.id,
                universe_id=snapshot.universe_id,
                snapshot_date=snapshot.snapshot_date.isoformat(),
                assets=snapshot.assets,
                turnover_rate=float(snapshot.turnover_rate) if snapshot.turnover_rate else None,
                assets_added=snapshot.assets_added,
                assets_removed=snapshot.assets_removed,
                screening_criteria=snapshot.screening_criteria,
                performance_metrics=snapshot.performance_metrics,
                created_at=snapshot.created_at.isoformat()
            ))
    
    # AI-friendly next actions
    next_actions = ["create_universe_snapshot", "view_universe_details"]
    if snapshot_responses:
        next_actions.extend([
            "get_universe_timeline",
            "analyze_snapshot_details",
            "compare_snapshots"
        ])
    if total_snapshots > offset + limit:
        next_actions.append("load_more_snapshots")
    
    return UniverseTimelineResponse(
        success=True,
        data=snapshot_responses,
        message=f"Retrieved {len(snapshot_responses)} of {total_snapshots} total snapshots",
        next_actions=next_actions,
        metadata={
            "universe_id": universe_id,
            "universe_name": universe.name,
            "total_snapshots": total_snapshots,
            "returned_snapshots": len(snapshot_responses),
            "pagination": {
                "limit": limit,
                "offset": offset,
                "has_more": total_snapshots > offset + limit
            }
        }
    )

@router.post("/{universe_id}/snapshots", response_model=UniverseTimelineResponse, status_code=status.HTTP_201_CREATED, summary="Create universe snapshot")
async def create_universe_snapshot(
    universe_id: str,
    snapshot_data: SnapshotCreateRequest,
    current_user: User = Depends(get_current_user),
    universe_service: UniverseService = Depends(get_universe_service)
):
    """
    Create a new universe snapshot capturing current composition.
    
    Features:
    - Point-in-time universe composition capture
    - Automatic turnover calculation vs previous snapshot
    - Asset change tracking (additions/removals)
    - Performance metrics calculation
    - Configurable snapshot date (defaults to today)
    """
    # Verify universe ownership
    get_result = await universe_service.get_universe_by_id(universe_id)
    
    if not get_result.success:
        if "not found" in get_result.error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_result.error
            )
    
    universe = get_result.data
    if universe.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Universe belongs to another user"
        )
    
    # Parse snapshot date if provided
    snapshot_date = None
    if snapshot_data.snapshot_date:
        try:
            from datetime import datetime
            snapshot_date = datetime.fromisoformat(snapshot_data.snapshot_date).date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid snapshot_date format. Use ISO format (YYYY-MM-DD)"
            )
    
    # Create snapshot using existing temporal service method
    result = await universe_service.create_universe_snapshot(
        universe_id=universe_id,
        snapshot_date=snapshot_date,
        screening_criteria=snapshot_data.screening_criteria,
        force_recreation=snapshot_data.force_recreation or False
    )
    
    if not result.success:
        if "already exists" in result.error and not snapshot_data.force_recreation:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{result.error}. Use force_recreation=true to overwrite."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error
            )
    
    snapshot = result.data
    
    # Convert to response format
    if isinstance(snapshot, dict):
        snapshot_response = UniverseSnapshotResponse(
            id=snapshot["id"],
            universe_id=snapshot["universe_id"],
            snapshot_date=snapshot["snapshot_date"],
            assets=snapshot["assets"],
            turnover_rate=snapshot.get("turnover_rate"),
            assets_added=snapshot.get("assets_added"),
            assets_removed=snapshot.get("assets_removed"),
            screening_criteria=snapshot.get("screening_criteria"),
            performance_metrics=snapshot.get("performance_metrics"),
            created_at=snapshot["created_at"]
        )
    else:
        snapshot_response = UniverseSnapshotResponse(
            id=snapshot.id,
            universe_id=snapshot.universe_id,
            snapshot_date=snapshot.snapshot_date.isoformat(),
            assets=snapshot.assets,
            turnover_rate=float(snapshot.turnover_rate) if snapshot.turnover_rate else None,
            assets_added=snapshot.assets_added,
            assets_removed=snapshot.assets_removed,
            screening_criteria=snapshot.screening_criteria,
            performance_metrics=snapshot.performance_metrics,
            created_at=snapshot.created_at.isoformat()
        )
    
    # AI-friendly next actions
    next_actions = [
        "get_universe_timeline",
        "view_snapshot_details",
        "compare_with_previous_snapshot"
    ]
    if snapshot_response.turnover_rate and snapshot_response.turnover_rate > 0:
        next_actions.append("analyze_turnover_impact")
    if snapshot_response.assets:
        next_actions.extend([
            "run_backtest_with_snapshot",
            "create_strategy_from_snapshot"
        ])
    
    return UniverseTimelineResponse(
        success=True,
        data=[snapshot_response],
        message=f"Universe snapshot created successfully for {snapshot_response.snapshot_date}",
        next_actions=next_actions,
        metadata={
            "universe_id": universe_id,
            "universe_name": universe.name,
            "snapshot_date": snapshot_response.snapshot_date,
            "asset_count": len(snapshot_response.assets),
            "turnover_rate": snapshot_response.turnover_rate,
            "has_changes": bool(snapshot_response.assets_added or snapshot_response.assets_removed),
            "creation_method": "api_manual"
        }
    )

@router.get("/{universe_id}/composition/{composition_date}", response_model=UniverseCompositionResponse, summary="Get composition at specific date")
async def get_composition_at_date(
    universe_id: str,
    composition_date: date,
    current_user: User = Depends(get_current_user),
    universe_service: UniverseService = Depends(get_universe_service),
    temporal_service: TemporalUniverseService = Depends(get_temporal_universe_service)
):
    """
    Get universe composition at a specific historical date.
    
    Returns the exact universe state as of the specified date,
    using the closest available snapshot or interpolation.
    
    Features:
    - Point-in-time composition retrieval
    - Snapshot-based historical accuracy
    - Context information about data source
    - Asset metadata at the specified date
    """
    # Verify universe ownership
    get_result = await universe_service.get_universe_by_id(universe_id)
    
    if not get_result.success:
        if "not found" in get_result.error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_result.error
            )
    
    universe = get_result.data
    if universe.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Universe belongs to another user"
        )
    
    # Get point-in-time composition using temporal service
    result = await temporal_service.get_point_in_time_composition(
        universe_id=universe_id,
        target_date=composition_date
    )
    
    if not result.success:
        if "no snapshots found" in result.error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No snapshot data available for universe on or before {composition_date}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error
            )
    
    composition_data = result.data
    
    # AI-friendly next actions
    next_actions = [
        "view_universe_details",
        "get_universe_timeline",
        "compare_with_current_composition"
    ]
    
    if composition_data.get("assets"):
        next_actions.extend([
            "run_backtest_from_date",
            "analyze_performance_since_date",
            "create_strategy_from_composition"
        ])
    
    # Check if this is an exact match or interpolated
    is_exact_match = composition_data.get("snapshot_date") == composition_date.isoformat()
    
    return UniverseCompositionResponse(
        success=True,
        data=composition_data,
        message=f"Retrieved universe composition for {composition_date} ({'exact match' if is_exact_match else 'nearest snapshot'})",
        next_actions=next_actions,
        metadata={
            "universe_id": universe_id,
            "universe_name": universe.name,
            "requested_date": composition_date.isoformat(),
            "actual_snapshot_date": composition_data.get("snapshot_date"),
            "is_exact_match": is_exact_match,
            "asset_count": len(composition_data.get("assets", [])),
            "data_source": composition_data.get("source", "snapshot"),
            "context": composition_data.get("context", {})
        }
    )

@router.post("/{universe_id}/backfill", response_model=UniverseTimelineResponse, summary="Generate historical snapshots")
async def backfill_universe_history(
    universe_id: str,
    backfill_data: BackfillRequest,
    current_user: User = Depends(get_current_user),
    universe_service: UniverseService = Depends(get_universe_service)
):
    """
    Generate historical snapshots for a universe over a specified period.
    
    Creates multiple snapshots at regular intervals to build complete
    temporal history. Useful for backtesting and historical analysis.
    
    Features:
    - Configurable date range and frequency
    - Bulk snapshot generation
    - Automatic turnover calculation
    - Progress tracking and error handling
    - Validation against existing snapshots
    """
    # Verify universe ownership
    get_result = await universe_service.get_universe_by_id(universe_id)
    
    if not get_result.success:
        if "not found" in get_result.error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=get_result.error
            )
    
    universe = get_result.data
    if universe.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Universe belongs to another user"
        )
    
    # Parse dates
    try:
        from datetime import datetime
        start_date = datetime.fromisoformat(backfill_data.start_date).date()
        end_date = datetime.fromisoformat(backfill_data.end_date).date()
        
        if start_date >= end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before end_date"
            )
            
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DD)"
        )
    
    # Validate frequency
    valid_frequencies = ["daily", "weekly", "monthly", "quarterly"]
    if backfill_data.frequency not in valid_frequencies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid frequency. Must be one of: {', '.join(valid_frequencies)}"
        )
    
    # Generate historical snapshots using existing service method
    result = await universe_service.backfill_universe_history(
        universe_id=universe_id,
        start_date=start_date,
        end_date=end_date,
        frequency=backfill_data.frequency
    )
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error
        )
    
    backfill_result = result.data
    created_snapshots = backfill_result.get("created_snapshots", [])
    
    # Convert snapshots to response format
    snapshot_responses = []
    for snapshot in created_snapshots:
        if isinstance(snapshot, dict):
            snapshot_responses.append(UniverseSnapshotResponse(
                id=snapshot["id"],
                universe_id=snapshot["universe_id"],
                snapshot_date=snapshot["snapshot_date"],
                assets=snapshot["assets"],
                turnover_rate=snapshot.get("turnover_rate"),
                assets_added=snapshot.get("assets_added"),
                assets_removed=snapshot.get("assets_removed"),
                screening_criteria=snapshot.get("screening_criteria"),
                performance_metrics=snapshot.get("performance_metrics"),
                created_at=snapshot["created_at"]
            ))
        else:
            snapshot_responses.append(UniverseSnapshotResponse(
                id=snapshot.id,
                universe_id=snapshot.universe_id,
                snapshot_date=snapshot.snapshot_date.isoformat(),
                assets=snapshot.assets,
                turnover_rate=float(snapshot.turnover_rate) if snapshot.turnover_rate else None,
                assets_added=snapshot.assets_added,
                assets_removed=snapshot.assets_removed,
                screening_criteria=snapshot.screening_criteria,
                performance_metrics=snapshot.performance_metrics,
                created_at=snapshot.created_at.isoformat()
            ))
    
    # AI-friendly next actions
    next_actions = [
        "get_universe_timeline",
        "view_backfill_summary"
    ]
    
    if snapshot_responses:
        next_actions.extend([
            "run_historical_backtest",
            "analyze_turnover_patterns",
            "compare_historical_performance"
        ])
        
    # Calculate summary statistics
    total_requested = backfill_result.get("total_periods", 0)
    total_created = len(snapshot_responses)
    skipped_count = backfill_result.get("skipped_existing", 0)
    
    return UniverseTimelineResponse(
        success=True,
        data=snapshot_responses,
        message=f"Backfill completed: {total_created} snapshots created, {skipped_count} skipped (already existed)",
        next_actions=next_actions,
        metadata={
            "universe_id": universe_id,
            "universe_name": universe.name,
            "backfill_period": f"{backfill_data.start_date} to {backfill_data.end_date}",
            "frequency": backfill_data.frequency,
            "total_periods_requested": total_requested,
            "snapshots_created": total_created,
            "snapshots_skipped": skipped_count,
            "success_rate": round((total_created / total_requested * 100) if total_requested > 0 else 0, 1),
            "processing_time": backfill_result.get("processing_time", 0),
            "operation_summary": backfill_result.get("summary", {})
        }
    )