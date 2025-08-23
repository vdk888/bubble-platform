"""
Universe Management API Endpoints.
Following Phase 2 Step 4 specifications with AI-friendly response format.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...core.database import get_db
from ..v1.auth import get_current_user
from ...models.user import User
from ...services.universe_service import UniverseService
from ...services.interfaces.base import ServiceResult

router = APIRouter()

# Response Models for API Documentation
class UniverseResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    asset_count: int
    symbols: List[str]
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

# Initialize service (dependency injection pattern)
def get_universe_service(db: Session = Depends(get_db)) -> UniverseService:
    return UniverseService(db)

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
        universe_responses.append(UniverseResponse(
            id=universe.id,
            name=universe.name,
            description=universe.description,
            asset_count=len(universe.get_symbols()),
            symbols=universe.get_symbols(),
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
                symbol for universe in result.data 
                for symbol in universe.get_symbols()
            )) if result.data else 0,
            "user_id": current_user.id
        }
    )

@router.post("/", response_model=AIUniverseResponse, summary="Create a new universe")
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
    
    # Add initial symbols if provided
    if universe_data.symbols:
        add_result = await universe_service.add_assets_to_universe_api(
            universe_id=universe.id,
            asset_symbols=universe_data.symbols
        )
        # Update universe with assets added
        if add_result.success:
            # Refresh universe to get updated asset count
            updated_result = await universe_service.get_universe_by_id(universe.id)
            if updated_result.success:
                universe = updated_result.data
    
    response_data = UniverseResponse(
        id=universe.id,
        name=universe.name,
        description=universe.description,
        asset_count=len(universe.get_symbols()),
        symbols=universe.get_symbols(),
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

@router.post("/{universe_id}/assets", response_model=AIAssetOperationResponse, summary="Add assets to universe")
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