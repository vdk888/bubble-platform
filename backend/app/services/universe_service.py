"""
Universe Management Service - Phase 2 Step 2 Implementation
Following architecture specifications from phase2_implementation.md
"""
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, text, select
from datetime import datetime, timezone, date

from ..models.universe import Universe
from ..models.universe_snapshot import UniverseSnapshot
from ..models.asset import Asset, UniverseAsset
from ..models.user import User
from ..core.database import get_db
from .interfaces.base import ServiceResult
from .interfaces.screener import IScreener, ScreeningCriteria, ScreeningResult
from .implementations.fundamental_screener import FundamentalScreener


class BulkResult:
    """Results for bulk operations with detailed tracking"""
    
    def __init__(self):
        self.successful: List[Dict[str, Any]] = []
        self.failed: List[Dict[str, Any]] = []
        self.warnings: List[str] = []
    
    @property
    def success_count(self) -> int:
        return len(self.successful)
    
    @property
    def failure_count(self) -> int:
        return len(self.failed)
    
    @property
    def total_processed(self) -> int:
        return self.success_count + self.failure_count
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_processed": self.total_processed,
            "successful": self.successful,
            "failed": self.failed,
            "warnings": self.warnings
        }


class UniverseService:
    """
    Universe Management Service implementing RLS policies and multi-tenant isolation.
    
    Following Phase 2 Step 2 specifications:
    - RLS policies for multi-tenant data isolation
    - CRUD operations respecting user ownership
    - Universe-asset relationship management
    - Turnover tracking for dynamic universes
    - AI-friendly response formats
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def _set_rls_context(self, user_id: str):
        """Set Row-Level Security context for multi-tenant isolation"""
        try:
            # Set the current user context for RLS policies
            self.db.execute(text("SET LOCAL app.current_user_id = :user_id"), {"user_id": user_id})
        except Exception as e:
            # For SQLite development, RLS is simulated through query filtering
            # In production PostgreSQL, this enables actual RLS policies
            pass
    
    async def create_universe(self, user_id: str, name: str, description: str = None, 
                            initial_symbols: List[str] = None) -> ServiceResult:
        """
        Create new investment universe with optional initial assets.
        Implements multi-tenant isolation and AI-friendly responses.
        """
        try:
            self._set_rls_context(user_id)
            
            # Validate user exists
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return ServiceResult(
                    success=False,
                    error="User not found",
                    message="Cannot create universe for non-existent user"
                )
            
            # Validate universe name uniqueness for user
            existing = self.db.query(Universe).filter(
                and_(Universe.owner_id == user_id, Universe.name == name)
            ).first()
            
            if existing:
                return ServiceResult(
                    success=False,
                    error="Universe name already exists",
                    message=f"Universe '{name}' already exists for this user",
                    next_actions=["choose_different_name", "update_existing_universe"]
                )
            
            # Create new universe
            universe = Universe(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                owner_id=user_id,
                screening_criteria={},
                turnover_rate=0.0
            )
            
            self.db.add(universe)
            self.db.commit()
            self.db.refresh(universe)
            
            # Add initial assets if provided
            bulk_result = None
            if initial_symbols:
                add_result = await self.add_assets_to_universe(universe.id, initial_symbols, user_id)
                bulk_result = add_result.data if add_result.success else None
            
            return ServiceResult(
                success=True,
                data=universe.to_dict(),
                message=f"Universe '{name}' created successfully",
                next_actions=[
                    "add_assets_to_universe",
                    "create_strategy_from_universe",
                    "configure_screening_criteria"
                ],
                metadata={
                    "universe_id": universe.id,
                    "asset_count": len(initial_symbols) if initial_symbols else 0,
                    "bulk_add_result": bulk_result if bulk_result else None
                }
            )
            
        except IntegrityError as e:
            self.db.rollback()
            return ServiceResult(
                success=False,
                error="Database constraint violation",
                message="Failed to create universe due to data constraint"
            )
        except Exception as e:
            self.db.rollback()
            return ServiceResult(
                success=False,
                error=str(e),
                message="Unexpected error creating universe"
            )
    
    async def get_user_universes(self, user_id: str) -> ServiceResult:
        """
        Get all universes for a user with asset metadata.
        Implements RLS isolation and includes comprehensive universe data.
        """
        try:
            self._set_rls_context(user_id)
            
            # Query universes with asset relationships pre-loaded
            universes = self.db.query(Universe).options(
                selectinload(Universe.asset_associations).selectinload(UniverseAsset.asset)
            ).filter(Universe.owner_id == user_id).all()
            
            universe_data = []
            for universe in universes:
                universe_dict = universe.to_dict()
                universe_data.append(universe_dict)
            
            return ServiceResult(
                success=True,
                data=universe_data,
                message=f"Retrieved {len(universes)} universes",
                next_actions=[
                    "create_new_universe",
                    "select_universe_for_strategy",
                    "bulk_manage_assets"
                ],
                metadata={
                    "total_universes": len(universes),
                    "total_unique_assets": len(set(
                        asset.symbol 
                        for universe in universes 
                        for asset in [assoc.asset for assoc in universe.asset_associations if assoc.asset]
                    ))
                }
            )
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to retrieve universes"
            )
    
    async def get_universe_by_id_with_user(self, universe_id: str, user_id: str) -> ServiceResult:
        """
        Get specific universe by ID with full asset details.
        Enforces user ownership through RLS.
        """
        try:
            self._set_rls_context(user_id)
            
            universe = self.db.query(Universe).options(
                selectinload(Universe.asset_associations).selectinload(UniverseAsset.asset)
            ).filter(
                and_(Universe.id == universe_id, Universe.owner_id == user_id)
            ).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Universe not found or access denied",
                    next_actions=["list_user_universes", "create_new_universe"]
                )
            
            return ServiceResult(
                success=True,
                data=universe.to_dict(),
                message=f"Retrieved universe '{universe.name}'",
                next_actions=[
                    "add_assets_to_universe",
                    "remove_assets_from_universe",
                    "update_universe_details",
                    "create_strategy_from_universe"
                ],
                metadata={
                    "universe_id": universe.id,
                    "asset_count": universe.get_asset_count(),
                    "last_modified": universe.updated_at.isoformat() if universe.updated_at else None
                }
            )
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to retrieve universe"
            )
    
    async def add_assets_to_universe(self, universe_id: str, asset_symbols: List[str], 
                                   user_id: str = None) -> ServiceResult:
        """
        Add multiple assets to universe with validation and relationship management.
        Creates Asset entities if they don't exist and manages many-to-many relationships.
        """
        try:
            if user_id:
                self._set_rls_context(user_id)
            
            # Get universe and verify ownership
            universe = self.db.query(Universe).filter(Universe.id == universe_id).first()
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Cannot add assets to non-existent universe"
                )
            
            if user_id and universe.owner_id != user_id:
                return ServiceResult(
                    success=False,
                    error="Access denied",
                    message="Cannot modify universe owned by another user"
                )
            
            bulk_result = BulkResult()
            current_position = self.db.query(UniverseAsset).filter(
                UniverseAsset.universe_id == universe_id
            ).count()
            
            for symbol in asset_symbols:
                try:
                    symbol = symbol.upper().strip()
                    
                    # Check if asset already in universe
                    existing_association = self.db.query(UniverseAsset).join(Asset).filter(
                        and_(
                            UniverseAsset.universe_id == universe_id,
                            Asset.symbol == symbol
                        )
                    ).first()
                    
                    if existing_association:
                        bulk_result.warnings.append(f"Asset {symbol} already in universe")
                        continue
                    
                    # Get or create Asset entity
                    asset = self.db.query(Asset).filter(Asset.symbol == symbol).first()
                    if not asset:
                        asset = Asset(
                            id=str(uuid.uuid4()),
                            symbol=symbol,
                            name=f"{symbol} Asset",  # Placeholder, will be updated by validation service
                            is_validated=False,
                            asset_metadata={}
                        )
                        self.db.add(asset)
                        self.db.flush()  # Get asset.id without committing
                    
                    # Create universe-asset relationship
                    universe_asset = UniverseAsset(
                        universe_id=universe_id,
                        asset_id=asset.id,
                        position=current_position,
                        added_at=datetime.now(timezone.utc),
                        weight=None,
                        notes=None
                    )
                    
                    self.db.add(universe_asset)
                    current_position += 1
                    
                    bulk_result.successful.append({
                        "symbol": symbol,
                        "asset_id": asset.id,
                        "position": current_position - 1,
                        "newly_created": not bool(self.db.query(Asset).filter(Asset.symbol == symbol).first())
                    })
                    
                except Exception as e:
                    bulk_result.failed.append({
                        "symbol": symbol,
                        "error": str(e)
                    })
            
            if bulk_result.successful:
                self.db.commit()
                
                # Update universe turnover rate
                await self._update_turnover_rate(universe_id)
            else:
                self.db.rollback()
            
            success = bulk_result.success_count > 0
            message = f"Added {bulk_result.success_count} assets to universe"
            if bulk_result.failure_count > 0:
                message += f", {bulk_result.failure_count} failed"
            
            return ServiceResult(
                success=success,
                data=bulk_result.to_dict(),
                message=message,
                next_actions=[
                    "validate_new_assets",
                    "create_strategy_from_universe",
                    "rebalance_portfolio"
                ] if success else ["retry_failed_assets"],
                metadata={
                    "universe_id": universe_id,
                    "total_assets_in_universe": current_position
                }
            )
            
        except Exception as e:
            self.db.rollback()
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to add assets to universe"
            )
    
    async def remove_assets_from_universe(self, universe_id: str, asset_symbols: List[str], 
                                        user_id: str = None) -> ServiceResult:
        """
        Remove assets from universe while maintaining relationship integrity.
        """
        try:
            if user_id:
                self._set_rls_context(user_id)
            
            # Verify universe exists and user has access
            universe = self.db.query(Universe).filter(Universe.id == universe_id).first()
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Cannot remove assets from non-existent universe"
                )
            
            if user_id and universe.owner_id != user_id:
                return ServiceResult(
                    success=False,
                    error="Access denied",
                    message="Cannot modify universe owned by another user"
                )
            
            bulk_result = BulkResult()
            
            for symbol in asset_symbols:
                try:
                    symbol = symbol.upper().strip()
                    
                    # Find and remove universe-asset relationship
                    universe_asset = self.db.query(UniverseAsset).join(Asset).filter(
                        and_(
                            UniverseAsset.universe_id == universe_id,
                            Asset.symbol == symbol
                        )
                    ).first()
                    
                    if universe_asset:
                        self.db.delete(universe_asset)
                        bulk_result.successful.append({
                            "symbol": symbol,
                            "asset_id": universe_asset.asset_id,
                            "removed_at": datetime.now(timezone.utc).isoformat()
                        })
                    else:
                        bulk_result.failed.append({
                            "symbol": symbol,
                            "error": "Asset not found in universe"
                        })
                        
                except Exception as e:
                    bulk_result.failed.append({
                        "symbol": symbol,
                        "error": str(e)
                    })
            
            if bulk_result.successful:
                self.db.commit()
                
                # Update universe turnover rate
                await self._update_turnover_rate(universe_id)
            else:
                self.db.rollback()
            
            success = bulk_result.success_count > 0
            message = f"Removed {bulk_result.success_count} assets from universe"
            if bulk_result.failure_count > 0:
                message += f", {bulk_result.failure_count} failed"
            
            return ServiceResult(
                success=success,
                data=bulk_result.to_dict(),
                message=message,
                next_actions=[
                    "add_replacement_assets",
                    "update_strategy_weights",
                    "rebalance_portfolio"
                ] if success else ["retry_failed_removals"],
                metadata={
                    "universe_id": universe_id,
                    "remaining_assets": universe.get_asset_count() - bulk_result.success_count
                }
            )
            
        except Exception as e:
            self.db.rollback()
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to remove assets from universe"
            )
    
    async def update_universe(self, universe_id: str, user_id: str, name: str = None, 
                            description: str = None, screening_criteria: Dict[str, Any] = None) -> ServiceResult:
        """
        Update universe details while maintaining data integrity.
        """
        try:
            self._set_rls_context(user_id)
            
            universe = self.db.query(Universe).filter(
                and_(Universe.id == universe_id, Universe.owner_id == user_id)
            ).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Universe not found or access denied"
                )
            
            changes = []
            if name and name != universe.name:
                # Check name uniqueness
                existing = self.db.query(Universe).filter(
                    and_(
                        Universe.owner_id == user_id,
                        Universe.name == name,
                        Universe.id != universe_id
                    )
                ).first()
                
                if existing:
                    return ServiceResult(
                        success=False,
                        error="Name already exists",
                        message=f"Universe name '{name}' already exists"
                    )
                
                universe.name = name
                changes.append("name")
            
            if description is not None:
                universe.description = description
                changes.append("description")
            
            if screening_criteria is not None:
                universe.screening_criteria = screening_criteria
                universe.last_screening_date = datetime.now(timezone.utc)
                changes.append("screening_criteria")
            
            if changes:
                universe.updated_at = datetime.now(timezone.utc)
                self.db.commit()
                self.db.refresh(universe)
            
            return ServiceResult(
                success=True,
                data=universe.to_dict(),
                message=f"Universe updated successfully: {', '.join(changes)}",
                next_actions=[
                    "apply_screening_criteria",
                    "update_strategies",
                    "rebalance_portfolios"
                ],
                metadata={
                    "universe_id": universe.id,
                    "changes_made": changes,
                    "asset_count": universe.get_asset_count()
                }
            )
            
        except Exception as e:
            self.db.rollback()
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to update universe"
            )
    
    async def delete_universe(self, universe_id: str, user_id: str) -> ServiceResult:
        """
        Delete universe with cascade handling for related strategies and portfolios.
        """
        try:
            self._set_rls_context(user_id)
            
            universe = self.db.query(Universe).filter(
                and_(Universe.id == universe_id, Universe.owner_id == user_id)
            ).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Universe not found or access denied"
                )
            
            universe_name = universe.name
            asset_count = universe.get_asset_count()
            
            # Note: Cascade deletes will handle related strategies and portfolios
            # as defined in the model relationships
            self.db.delete(universe)
            self.db.commit()
            
            return ServiceResult(
                success=True,
                data={
                    "deleted_universe_id": universe_id,
                    "deleted_universe_name": universe_name,
                    "deleted_asset_count": asset_count
                },
                message=f"Universe '{universe_name}' deleted successfully",
                next_actions=[
                    "create_new_universe",
                    "review_remaining_universes"
                ],
                metadata={
                    "deletion_timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
        except Exception as e:
            self.db.rollback()
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to delete universe"
            )
    
    async def calculate_turnover_rate(self, universe_id: str) -> ServiceResult:
        """
        Calculate universe turnover rate based on recent asset changes.
        """
        try:
            universe = self.db.query(Universe).filter(Universe.id == universe_id).first()
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Cannot calculate turnover for non-existent universe"
                )
            
            turnover_rate = universe.turnover_rate or 0.0
            
            return ServiceResult(
                success=True,
                data={
                    "universe_id": universe_id,
                    "turnover_rate": turnover_rate,
                    "last_calculated": universe.updated_at.isoformat() if universe.updated_at else None
                },
                message=f"Turnover rate calculated: {turnover_rate:.2%}",
                metadata={
                    "asset_count": universe.get_asset_count(),
                    "last_screening": universe.last_screening_date.isoformat() if universe.last_screening_date else None
                }
            )
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to calculate turnover rate"
            )
    
    async def _update_turnover_rate(self, universe_id: str):
        """
        Internal method to update turnover rate after asset changes.
        """
        try:
            universe = self.db.query(Universe).filter(Universe.id == universe_id).first()
            if universe:
                # Get current asset symbols from relationships
                current_symbols = universe.get_symbols()
                
                # Compare with legacy JSON symbols if available
                if universe.symbols:
                    old_symbols = set(universe.symbols)
                    new_symbols = set(current_symbols)
                    
                    if old_symbols.union(new_symbols):
                        turnover = len(old_symbols.symmetric_difference(new_symbols)) / len(old_symbols.union(new_symbols))
                        universe.turnover_rate = turnover
                
                # Update legacy JSON symbols for backward compatibility
                universe.symbols = current_symbols
                universe.last_screening_date = datetime.now(timezone.utc)
                
        except Exception:
            # Don't fail the main operation if turnover calculation fails
            pass

    # API Interface Wrapper Methods
    # These methods provide simplified interfaces for API endpoints
    
    async def get_universe_by_id(self, universe_id: str) -> ServiceResult:
        """
        Get universe by ID without requiring user_id parameter.
        User context is handled by authentication layer and RLS policies.
        """
        try:
            universe = self.db.query(Universe).options(
                selectinload(Universe.asset_associations).selectinload(UniverseAsset.asset)
            ).filter(Universe.id == universe_id).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message=f"Universe with ID {universe_id} not found or access denied"
                )
            
            return ServiceResult(
                success=True,
                data=universe,
                message=f"Retrieved universe '{universe.name}'",
                next_actions=[
                    "add_assets_to_universe",
                    "create_strategy_from_universe",
                    "update_universe_details"
                ],
                metadata={
                    "universe_id": universe.id,
                    "asset_count": len(universe.get_symbols()),
                    "last_updated": universe.updated_at.isoformat()
                }
            )
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to retrieve universe"
            )
    
    async def update_universe_api(self, universe_id: str, name: str = None, description: str = None) -> ServiceResult:
        """
        Update universe with simplified API interface.
        User context is handled by authentication and RLS.
        """
        try:
            universe = self.db.query(Universe).filter(Universe.id == universe_id).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Universe not found or access denied"
                )
            
            # Apply updates
            changes = []
            if name is not None and name != universe.name:
                # Check name uniqueness for this user
                existing = self.db.query(Universe).filter(
                    and_(
                        Universe.owner_id == universe.owner_id,
                        Universe.name == name,
                        Universe.id != universe_id
                    )
                ).first()
                
                if existing:
                    return ServiceResult(
                        success=False,
                        error="Universe name already exists",
                        message=f"Universe name '{name}' already exists"
                    )
                
                universe.name = name
                changes.append("name")
            
            if description is not None and description != universe.description:
                universe.description = description
                changes.append("description")
            
            if not changes:
                return ServiceResult(
                    success=True,
                    data=universe,
                    message="No changes requested",
                    metadata={"changes": []}
                )
            
            universe.updated_at = datetime.now(timezone.utc)
            
            self.db.commit()
            self.db.refresh(universe)
            
            return ServiceResult(
                success=True,
                data=universe,
                message=f"Universe updated successfully: {', '.join(changes)}",
                next_actions=[
                    "add_assets_to_universe",
                    "create_strategy_from_universe"
                ],
                metadata={
                    "changes": changes,
                    "universe_id": universe.id
                }
            )
            
        except Exception as e:
            self.db.rollback()
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to update universe"
            )
    
    async def delete_universe_api(self, universe_id: str) -> ServiceResult:
        """
        Delete universe with simplified API interface.
        User context handled by authentication and RLS.
        """
        try:
            universe = self.db.query(Universe).filter(Universe.id == universe_id).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Universe not found or access denied"
                )
            
            universe_name = universe.name
            
            # Delete universe (cascading will handle relationships)
            self.db.delete(universe)
            self.db.commit()
            
            return ServiceResult(
                success=True,
                data={"deleted_universe_id": universe_id},
                message=f"Universe '{universe_name}' deleted successfully",
                next_actions=["create_new_universe", "view_remaining_universes"],
                metadata={
                    "deleted_universe_id": universe_id,
                    "cascade_effects": "Associated universe-asset relationships deleted"
                }
            )
            
        except Exception as e:
            self.db.rollback()
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to delete universe"
            )
    
    async def add_assets_to_universe_api(self, universe_id: str, asset_symbols: List[str]) -> ServiceResult:
        """
        Add assets to universe with simplified API interface.
        """
        # This delegates to the existing detailed method but extracts user_id from universe
        try:
            universe = self.db.query(Universe).filter(Universe.id == universe_id).first()
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Universe not found or access denied"
                )
            
            # Call the existing detailed method with user_id
            result = await self.add_assets_to_universe(universe_id, asset_symbols, universe.owner_id)
            return result
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to add assets to universe"
            )
    
    async def remove_assets_from_universe_api(self, universe_id: str, asset_symbols: List[str]) -> ServiceResult:
        """
        Remove assets from universe with simplified API interface.
        """
        try:
            universe = self.db.query(Universe).filter(Universe.id == universe_id).first()
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Universe not found or access denied"
                )
            
            # Call the existing detailed method with user_id
            result = await self.remove_assets_from_universe(universe_id, asset_symbols, universe.owner_id)
            return result
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to remove assets from universe"
            )
    
    async def apply_screening_criteria(
        self, 
        universe_id: str, 
        user_id: str,
        screener: IScreener = None
    ) -> ServiceResult:
        """
        Apply screening criteria to rebalance universe automatically.
        
        Implements dynamic universe screening as specified in Sprint 2 requirements.
        Uses Interface-First Design with injected screener implementation.
        
        Args:
            universe_id: UUID of universe to screen
            user_id: User requesting the screening  
            screener: Screener implementation (defaults to FundamentalScreener)
            
        Returns:
            ServiceResult with screening results and updated universe
        """
        try:
            self._set_rls_context(user_id)
            
            # Get universe with current screening criteria
            universe = self.db.query(Universe).filter(
                and_(Universe.id == universe_id, Universe.owner_id == user_id)
            ).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Universe not found or access denied"
                )
            
            if not universe.screening_criteria:
                return ServiceResult(
                    success=False,
                    error="No screening criteria defined",
                    message="Universe has no screening criteria to apply",
                    next_actions=[
                        "configure_screening_criteria",
                        "update_universe_criteria"
                    ]
                )
            
            # Parse screening criteria from JSON
            criteria = ScreeningCriteria.from_json(universe.screening_criteria)
            
            # Use provided screener or default to FundamentalScreener
            if screener is None:
                screener = FundamentalScreener(self.db)
            
            # Validate criteria before applying
            validation_result = await screener.validate_criteria(criteria)
            if not validation_result.success:
                return ServiceResult(
                    success=False,
                    error="Invalid screening criteria",
                    message=validation_result.message,
                    metadata=validation_result.metadata
                )
            
            # Get current universe assets for screening
            current_assets = universe.get_assets()
            
            # Get expanded asset pool for screening (all validated assets)
            # This allows the universe to grow with new qualifying assets
            asset_pool = self.db.query(Asset).filter(
                Asset.is_validated == True
            ).all()
            
            # Apply screening criteria
            screening_result = await screener.screen_universe(
                asset_pool=asset_pool,
                criteria=criteria,
                screening_date=datetime.now(timezone.utc)
            )
            
            # Calculate changes needed
            current_symbols = {asset.symbol for asset in current_assets}
            new_symbols = {asset.symbol for asset in screening_result.matching_assets}
            
            symbols_to_add = list(new_symbols - current_symbols)
            symbols_to_remove = list(current_symbols - new_symbols)
            
            changes_made = []
            
            # Remove assets that no longer meet criteria
            if symbols_to_remove:
                remove_result = await self.remove_assets_from_universe(
                    universe_id, symbols_to_remove, user_id
                )
                if remove_result.success:
                    changes_made.append(f"removed_{len(symbols_to_remove)}_assets")
            
            # Add new qualifying assets
            if symbols_to_add:
                add_result = await self.add_assets_to_universe(
                    universe_id, symbols_to_add, user_id
                )
                if add_result.success:
                    changes_made.append(f"added_{len(symbols_to_add)}_assets")
            
            # Update universe screening date
            universe.last_screening_date = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(universe)
            
            return ServiceResult(
                success=True,
                data={
                    "universe": universe.to_dict(),
                    "screening_result": {
                        "total_screened": screening_result.total_screened,
                        "matches_found": len(screening_result.matching_assets),
                        "match_rate": screening_result.match_rate,
                        "symbols_added": symbols_to_add,
                        "symbols_removed": symbols_to_remove
                    }
                },
                message=f"Universe screening completed successfully. {', '.join(changes_made) if changes_made else 'No changes needed'}",
                next_actions=[
                    "review_universe_changes",
                    "update_strategies",
                    "run_backtest",
                    "schedule_next_screening"
                ],
                metadata={
                    "universe_id": universe_id,
                    "changes_made": changes_made,
                    "performance_metrics": screening_result.performance_metrics,
                    "screening_date": screening_result.screening_date.isoformat(),
                    "criteria_applied": criteria.to_json()
                }
            )
            
        except Exception as e:
            self.db.rollback()
            return ServiceResult(
                success=False,
                error=str(e),
                message=f"Universe screening failed: {str(e)}"
            )
    
    async def preview_screening_impact(
        self,
        universe_id: str,
        user_id: str,
        new_criteria: Dict[str, Any],
        screener: IScreener = None
    ) -> ServiceResult:
        """
        Preview the impact of screening criteria without applying changes.
        
        Provides "what-if" analysis for criteria optimization before commitment.
        
        Args:
            universe_id: UUID of universe to analyze
            user_id: User requesting the preview
            new_criteria: Screening criteria to test
            screener: Screener implementation (defaults to FundamentalScreener)
            
        Returns:
            ServiceResult with projected changes and statistics
        """
        try:
            self._set_rls_context(user_id)
            
            universe = self.db.query(Universe).filter(
                and_(Universe.id == universe_id, Universe.owner_id == user_id)
            ).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Universe not found or access denied"
                )
            
            # Parse and validate new criteria
            criteria = ScreeningCriteria.from_json(new_criteria)
            
            if screener is None:
                screener = FundamentalScreener(self.db)
            
            validation_result = await screener.validate_criteria(criteria)
            if not validation_result.success:
                return ServiceResult(
                    success=False,
                    error="Invalid screening criteria", 
                    message=validation_result.message,
                    metadata=validation_result.metadata
                )
            
            # Get asset pool for screening
            asset_pool = self.db.query(Asset).filter(
                Asset.is_validated == True
            ).all()
            
            # Get screening statistics
            stats = await screener.get_screening_stats(asset_pool, criteria)
            
            # Calculate projected changes
            current_assets = universe.get_assets()
            current_symbols = {asset.symbol for asset in current_assets}
            
            screening_result = await screener.screen_universe(
                asset_pool=asset_pool,
                criteria=criteria,
                screening_date=datetime.now(timezone.utc)
            )
            
            new_symbols = {asset.symbol for asset in screening_result.matching_assets}
            
            projected_additions = list(new_symbols - current_symbols)
            projected_removals = list(current_symbols - new_symbols)
            projected_unchanged = list(current_symbols & new_symbols)
            
            return ServiceResult(
                success=True,
                data={
                    "current_universe": {
                        "asset_count": len(current_assets),
                        "symbols": list(current_symbols)
                    },
                    "projected_universe": {
                        "asset_count": len(screening_result.matching_assets),
                        "symbols": list(new_symbols)
                    },
                    "projected_changes": {
                        "additions": projected_additions,
                        "removals": projected_removals, 
                        "unchanged": projected_unchanged,
                        "additions_count": len(projected_additions),
                        "removals_count": len(projected_removals),
                        "unchanged_count": len(projected_unchanged)
                    },
                    "screening_stats": stats
                },
                message=f"Screening preview completed: {len(projected_additions)} additions, {len(projected_removals)} removals",
                next_actions=[
                    "apply_screening_criteria" if projected_additions or projected_removals else "keep_current_criteria",
                    "refine_screening_criteria",
                    "compare_criteria_options"
                ],
                metadata={
                    "universe_id": universe_id,
                    "criteria_tested": criteria.to_json(),
                    "validation_passed": True,
                    "impact_level": "high" if (len(projected_additions) + len(projected_removals)) > len(current_assets) * 0.2 else "low"
                }
            )
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error=str(e),
                message=f"Screening preview failed: {str(e)}"
            )

    # TEMPORAL UNIVERSE METHODS - Sprint 2.5 Part C Implementation
    
    async def create_universe_snapshot(
        self, 
        universe_id: str, 
        snapshot_date: date, 
        screening_criteria: Dict = None,
        user_id: str = None
    ) -> ServiceResult:
        """
        Create point-in-time universe snapshot for temporal tracking.
        
        Args:
            universe_id: UUID of universe to snapshot
            snapshot_date: Date for this snapshot
            screening_criteria: Optional criteria used to generate this snapshot
            user_id: Optional user ID for RLS context
            
        Returns:
            ServiceResult with snapshot data and temporal information
        """
        try:
            if user_id:
                self._set_rls_context(user_id)
            
            # Get universe with current composition
            universe = self.db.query(Universe).options(
                selectinload(Universe.asset_associations).selectinload(UniverseAsset.asset)
            ).filter(Universe.id == universe_id).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Cannot create snapshot for non-existent universe"
                )
            
            if user_id and universe.owner_id != user_id:
                return ServiceResult(
                    success=False,
                    error="Access denied",
                    message="Cannot create snapshot for universe owned by another user"
                )
            
            # Check if snapshot already exists for this date
            existing_snapshot = self.db.query(UniverseSnapshot).filter(
                and_(
                    UniverseSnapshot.universe_id == universe_id,
                    UniverseSnapshot.snapshot_date == snapshot_date
                )
            ).first()
            
            if existing_snapshot:
                return ServiceResult(
                    success=False,
                    error="Snapshot already exists",
                    message=f"Snapshot for {snapshot_date} already exists",
                    data=existing_snapshot.to_dict(),
                    next_actions=["update_existing_snapshot", "choose_different_date"]
                )
            
            # Get current asset composition
            current_assets = []
            for assoc in universe.asset_associations:
                if assoc.asset:
                    current_assets.append({
                        'symbol': assoc.asset.symbol,
                        'name': assoc.asset.name,
                        'weight': float(assoc.weight) if assoc.weight else None,
                        'asset_id': assoc.asset.id,
                        'reason_added': f"Position {assoc.position}",
                        'sector': assoc.asset.asset_metadata.get('sector', 'Unknown') if assoc.asset.asset_metadata else 'Unknown'
                    })
            
            # Get previous snapshot for turnover calculation
            previous_snapshot = self.db.query(UniverseSnapshot).filter(
                and_(
                    UniverseSnapshot.universe_id == universe_id,
                    UniverseSnapshot.snapshot_date < snapshot_date
                )
            ).order_by(UniverseSnapshot.snapshot_date.desc()).first()
            
            # Create snapshot using factory method
            snapshot = UniverseSnapshot.create_from_universe_state(
                universe_id=universe_id,
                snapshot_date=snapshot_date,
                current_assets=current_assets,
                screening_criteria=screening_criteria or universe.screening_criteria,
                previous_snapshot=previous_snapshot
            )
            
            self.db.add(snapshot)
            self.db.commit()
            self.db.refresh(snapshot)
            
            return ServiceResult(
                success=True,
                data=snapshot.to_dict(),
                message=f"Universe snapshot created for {snapshot_date}",
                next_actions=[
                    "view_snapshot_details",
                    "compare_with_previous",
                    "schedule_next_snapshot",
                    "analyze_turnover"
                ],
                metadata={
                    "universe_id": universe_id,
                    "snapshot_id": snapshot.id,
                    "asset_count": len(current_assets),
                    "turnover_rate": float(snapshot.turnover_rate) if snapshot.turnover_rate else 0.0,
                    "has_previous_snapshot": previous_snapshot is not None
                }
            )
            
        except Exception as e:
            self.db.rollback()
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to create universe snapshot"
            )
    
    async def get_universe_timeline(
        self, 
        universe_id: str, 
        start_date: date, 
        end_date: date,
        user_id: str = None
    ) -> ServiceResult:
        """
        Get historical universe evolution timeline.
        
        Args:
            universe_id: UUID of universe
            start_date: Timeline start date
            end_date: Timeline end date
            user_id: Optional user ID for RLS context
            
        Returns:
            ServiceResult with timeline data and evolution analysis
        """
        try:
            if user_id:
                self._set_rls_context(user_id)
            
            # Verify universe exists and user has access
            universe = self.db.query(Universe).filter(Universe.id == universe_id).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Cannot get timeline for non-existent universe"
                )
            
            if user_id and universe.owner_id != user_id:
                return ServiceResult(
                    success=False,
                    error="Access denied",
                    message="Cannot access timeline for universe owned by another user"
                )
            
            # Get snapshots in date range
            snapshots = self.db.query(UniverseSnapshot).filter(
                and_(
                    UniverseSnapshot.universe_id == universe_id,
                    UniverseSnapshot.snapshot_date >= start_date,
                    UniverseSnapshot.snapshot_date <= end_date
                )
            ).order_by(UniverseSnapshot.snapshot_date.asc()).all()
            
            if not snapshots:
                return ServiceResult(
                    success=False,
                    error="No snapshots found",
                    message=f"No snapshots found for {start_date} to {end_date}",
                    next_actions=[
                        "create_initial_snapshot",
                        "backfill_historical_data",
                        "adjust_date_range"
                    ]
                )
            
            # Calculate timeline statistics
            timeline_data = []
            total_turnover = 0.0
            asset_count_changes = []
            
            for i, snapshot in enumerate(snapshots):
                snapshot_dict = snapshot.to_dict()
                
                # Add evolution metadata
                if i > 0:
                    prev_snapshot = snapshots[i-1]
                    asset_count_change = len(snapshot.assets) - len(prev_snapshot.assets)
                    asset_count_changes.append(asset_count_change)
                    
                    snapshot_dict['evolution'] = {
                        'asset_count_change': asset_count_change,
                        'days_since_previous': (snapshot.snapshot_date - prev_snapshot.snapshot_date).days,
                        'composition_stability': 1.0 - (snapshot.turnover_rate or 0.0)
                    }
                
                timeline_data.append(snapshot_dict)
                total_turnover += snapshot.turnover_rate or 0.0
            
            # Calculate aggregate statistics
            avg_turnover = total_turnover / len(snapshots) if snapshots else 0.0
            avg_asset_count = sum(len(s.assets) for s in snapshots) / len(snapshots)
            
            return ServiceResult(
                success=True,
                data={
                    "timeline": timeline_data,
                    "universe_info": {
                        "id": universe_id,
                        "name": universe.name,
                        "description": universe.description
                    },
                    "period_analysis": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "snapshot_count": len(snapshots),
                        "average_turnover": avg_turnover,
                        "average_asset_count": avg_asset_count,
                        "total_days": (end_date - start_date).days,
                        "evolution_stability": 1.0 - avg_turnover
                    }
                },
                message=f"Retrieved {len(snapshots)} snapshots for timeline analysis",
                next_actions=[
                    "analyze_turnover_patterns",
                    "identify_stable_assets", 
                    "create_evolution_chart",
                    "export_timeline_data"
                ],
                metadata={
                    "universe_id": universe_id,
                    "period_start": start_date.isoformat(),
                    "period_end": end_date.isoformat(),
                    "data_quality": "high" if len(snapshots) > 4 else "limited"
                }
            )
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to retrieve universe timeline"
            )
    
    async def backfill_universe_history(
        self,
        universe_id: str,
        start_date: date,
        end_date: date,
        frequency: str = 'monthly',
        user_id: str = None
    ) -> ServiceResult:
        """
        Generate historical snapshots using current screening criteria.
        
        Args:
            universe_id: UUID of universe to backfill
            start_date: Start date for backfill
            end_date: End date for backfill
            frequency: Snapshot frequency ('monthly', 'quarterly', 'weekly')
            user_id: Optional user ID for RLS context
            
        Returns:
            ServiceResult with backfill results and snapshot count
        """
        try:
            if user_id:
                self._set_rls_context(user_id)
            
            # Verify universe exists and user has access
            universe = self.db.query(Universe).filter(Universe.id == universe_id).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found", 
                    message="Cannot backfill history for non-existent universe"
                )
            
            if user_id and universe.owner_id != user_id:
                return ServiceResult(
                    success=False,
                    error="Access denied",
                    message="Cannot backfill history for universe owned by another user"
                )
            
            # Generate date sequence based on frequency
            dates_to_backfill = []
            current_date = start_date
            
            while current_date <= end_date:
                # Check if snapshot already exists
                existing = self.db.query(UniverseSnapshot).filter(
                    and_(
                        UniverseSnapshot.universe_id == universe_id,
                        UniverseSnapshot.snapshot_date == current_date
                    )
                ).first()
                
                if not existing:
                    dates_to_backfill.append(current_date)
                
                # Increment based on frequency
                if frequency == 'weekly':
                    from datetime import timedelta
                    current_date += timedelta(weeks=1)
                elif frequency == 'monthly':
                    # Move to next month (approximate)
                    if current_date.month == 12:
                        current_date = current_date.replace(year=current_date.year + 1, month=1)
                    else:
                        current_date = current_date.replace(month=current_date.month + 1)
                elif frequency == 'quarterly':
                    # Move to next quarter
                    new_month = current_date.month + 3
                    new_year = current_date.year
                    if new_month > 12:
                        new_month -= 12
                        new_year += 1
                    current_date = current_date.replace(year=new_year, month=new_month)
                else:
                    raise ValueError(f"Unsupported frequency: {frequency}")
            
            # Create snapshots for each date
            created_snapshots = []
            failed_dates = []
            
            for snapshot_date in dates_to_backfill:
                try:
                    # For historical backfill, we simulate what the universe would have looked like
                    # using current composition (in a real implementation, this would use historical data)
                    snapshot_result = await self.create_universe_snapshot(
                        universe_id=universe_id,
                        snapshot_date=snapshot_date,
                        screening_criteria=universe.screening_criteria,
                        user_id=user_id
                    )
                    
                    if snapshot_result.success:
                        created_snapshots.append(snapshot_result.data)
                    else:
                        failed_dates.append({
                            "date": snapshot_date.isoformat(),
                            "error": snapshot_result.error
                        })
                        
                except Exception as e:
                    failed_dates.append({
                        "date": snapshot_date.isoformat(),
                        "error": str(e)
                    })
            
            success = len(created_snapshots) > 0
            message = f"Backfilled {len(created_snapshots)} snapshots"
            if failed_dates:
                message += f", {len(failed_dates)} failed"
            
            return ServiceResult(
                success=success,
                data={
                    "created_snapshots": created_snapshots,
                    "failed_dates": failed_dates,
                    "backfill_summary": {
                        "success_count": len(created_snapshots),
                        "failure_count": len(failed_dates),
                        "total_requested": len(dates_to_backfill),
                        "frequency": frequency,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat()
                    }
                },
                message=message,
                next_actions=[
                    "view_timeline",
                    "analyze_historical_turnover",
                    "validate_backfilled_data"
                ] if success else ["retry_failed_dates", "adjust_date_range"],
                metadata={
                    "universe_id": universe_id,
                    "backfill_frequency": frequency,
                    "success_rate": len(created_snapshots) / len(dates_to_backfill) if dates_to_backfill else 0.0
                }
            )
            
        except Exception as e:
            self.db.rollback()
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to backfill universe history"
            )


# Factory function for dependency injection
def get_universe_service(db: Session) -> UniverseService:
    """Factory function for creating UniverseService instances with dependency injection"""
    return UniverseService(db)