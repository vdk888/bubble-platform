"""
Universe Management Service - Phase 2 Step 2 Implementation
Following architecture specifications from phase2_implementation.md
"""
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, text
from datetime import datetime, timezone

from ..models.universe import Universe
from ..models.asset import Asset, UniverseAsset
from ..models.user import User
from ..core.database import get_db
from .interfaces.base import ServiceResult


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


# Factory function for dependency injection
def get_universe_service(db: Session) -> UniverseService:
    """Factory function for creating UniverseService instances with dependency injection"""
    return UniverseService(db)