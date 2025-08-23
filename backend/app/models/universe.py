from sqlalchemy import Column, String, Text, ForeignKey, JSON, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from typing import List, Dict, Any
from .base import BaseModel

class Universe(BaseModel):
    """
    Universe model updated for Phase 2 normalized Asset relationships.
    
    Migrated from JSON symbols storage to proper Asset entity relationships
    via UniverseAsset junction table for many-to-many associations.
    """
    __tablename__ = "universes"
    
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # DEPRECATED: symbols field - kept temporarily for migration compatibility
    # Will be removed after successful migration to Asset relationships
    symbols = Column(JSON, nullable=True)  # Made nullable for migration
    
    # Dynamic screening criteria
    screening_criteria = Column(JSON)  # Flexible screening rules
    last_screening_date = Column(DateTime(timezone=True))
    turnover_rate = Column(Float)  # Track universe evolution
    
    # Ownership
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="universes")
    
    # Relationships
    strategies = relationship("Strategy", back_populates="universe", cascade="all, delete-orphan")
    
    # NEW: Asset relationships via junction table
    asset_associations = relationship(
        "UniverseAsset", 
        back_populates="universe", 
        cascade="all, delete-orphan",
        order_by="UniverseAsset.position"
    )
    
    def __repr__(self) -> str:
        return f"<Universe(id='{self.id}', name='{self.name}', owner_id='{self.owner_id}')>"
    
    def get_symbols(self) -> List[str]:
        """
        Get current universe symbols - updated for Asset relationships.
        Falls back to legacy JSON symbols during migration period.
        """
        # New normalized approach - get symbols from Asset relationships
        if self.asset_associations:
            return [assoc.asset.symbol for assoc in self.asset_associations if assoc.asset]
        
        # Legacy fallback during migration
        if self.symbols and isinstance(self.symbols, list):
            return self.symbols
            
        return []
    
    def get_assets(self) -> List[Dict[str, Any]]:
        """Get full asset data with relationship metadata"""
        assets = []
        for assoc in self.asset_associations:
            if assoc.asset:
                asset_data = assoc.asset.to_dict()
                asset_data.update({
                    'universe_position': assoc.position,
                    'added_to_universe_at': assoc.added_at.isoformat() if assoc.added_at else None,
                    'universe_weight': float(assoc.weight) if assoc.weight else None,
                    'universe_notes': assoc.notes
                })
                assets.append(asset_data)
        return assets
    
    def get_asset_count(self) -> int:
        """Get total number of assets in universe"""
        return len(self.asset_associations)
    
    def calculate_turnover_rate(self, new_asset_ids: List[str]) -> float:
        """
        Calculate turnover rate when universe composition changes.
        Compares current assets to new asset list.
        """
        if not self.asset_associations:
            return 0.0
            
        current_asset_ids = {assoc.asset_id for assoc in self.asset_associations}
        new_asset_id_set = set(new_asset_ids)
        
        if not current_asset_ids.union(new_asset_id_set):
            return 0.0
            
        symmetric_diff = current_asset_ids.symmetric_difference(new_asset_id_set)
        union_set = current_asset_ids.union(new_asset_id_set)
        
        return len(symmetric_diff) / len(union_set)
    
    def update_symbols(self, new_symbols: List[str]):
        """
        LEGACY METHOD - kept for backward compatibility during migration.
        New code should use UniverseService.add_assets_to_universe() instead.
        """
        # Calculate turnover for legacy method
        if self.symbols:
            old_set = set(self.get_symbols())
            new_set = set(new_symbols)
            if old_set.union(new_set):  # Avoid division by zero
                self.turnover_rate = len(old_set.symmetric_difference(new_set)) / len(old_set.union(new_set))
        
        self.symbols = new_symbols
        self.last_screening_date = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Enhanced to_dict with asset relationship data"""
        base_dict = super().to_dict()
        base_dict.update({
            'name': self.name,
            'description': self.description,
            'owner_id': self.owner_id,
            'screening_criteria': self.screening_criteria,
            'last_screening_date': self.last_screening_date.isoformat() if self.last_screening_date else None,
            'turnover_rate': self.turnover_rate,
            'asset_count': self.get_asset_count(),
            'symbols': self.get_symbols(),  # For API compatibility
            'assets': self.get_assets()  # Full asset data with metadata
        })
        return base_dict