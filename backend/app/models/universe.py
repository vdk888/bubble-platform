from sqlalchemy import Column, String, Text, ForeignKey, JSON, Float, DateTime, and_, desc
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, date
from typing import List, Dict, Any, Optional
import pandas as pd
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
    
    # NEW: Temporal universe snapshots (Sprint 2.5)
    snapshots = relationship(
        "UniverseSnapshot", 
        back_populates="universe", 
        cascade="all, delete-orphan",
        order_by="UniverseSnapshot.snapshot_date"
    )
    
    def __repr__(self) -> str:
        return f"<Universe(id='{self.id}', name='{self.name}', owner_id='{self.owner_id}')>"
    
    def get_symbols(self) -> List[str]:
        """
        Get current universe symbols from Asset relationships.
        """
        # Get symbols from normalized Asset relationships
        if self.asset_associations:
            return [assoc.asset.symbol for assoc in self.asset_associations if assoc.asset]
            
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
    
    # NEW: Temporal universe methods (Sprint 2.5)
    def get_composition_at_date(self, target_date: date) -> Optional[List[Dict[str, Any]]]:
        """
        Get universe composition at specific historical date.
        
        Args:
            target_date: Date to get composition for
            
        Returns:
            List of asset dictionaries at that date, or None if no snapshot exists
        """
        if not self.snapshots:
            return None
        
        # Find the most recent snapshot at or before the target date
        relevant_snapshot = None
        for snapshot in sorted(self.snapshots, key=lambda s: s.snapshot_date, reverse=True):
            if snapshot.snapshot_date <= target_date:
                relevant_snapshot = snapshot
                break
        
        return relevant_snapshot.assets if relevant_snapshot else None
    
    def get_evolution_timeline(self, start_date: date, end_date: date) -> List['UniverseSnapshot']:
        """
        Get historical snapshots for timeline view.
        
        Args:
            start_date: Start date for timeline
            end_date: End date for timeline
            
        Returns:
            List of UniverseSnapshot objects in date order
        """
        if not self.snapshots:
            return []
        
        return [
            snapshot for snapshot in self.snapshots
            if start_date <= snapshot.snapshot_date <= end_date
        ]
    
    def calculate_historical_turnover(self, start_date: date, end_date: date) -> Optional[pd.Series]:
        """
        Calculate turnover rates between periods.
        
        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Pandas Series with turnover rates indexed by date, or None if insufficient data
        """
        try:
            timeline = self.get_evolution_timeline(start_date, end_date)
            
            if len(timeline) < 2:
                return None
            
            dates = []
            turnover_rates = []
            
            for snapshot in timeline:
                if snapshot.turnover_rate is not None:
                    dates.append(snapshot.snapshot_date)
                    turnover_rates.append(float(snapshot.turnover_rate))
            
            if not dates:
                return None
            
            return pd.Series(turnover_rates, index=dates, name='turnover_rate')
        
        except ImportError:
            # If pandas is not available, return simple dict
            timeline = self.get_evolution_timeline(start_date, end_date)
            return {
                snapshot.snapshot_date: float(snapshot.turnover_rate or 0.0)
                for snapshot in timeline
                if snapshot.turnover_rate is not None
            }
    
    def get_latest_snapshot(self) -> Optional['UniverseSnapshot']:
        """Get the most recent snapshot for this universe"""
        if not self.snapshots:
            return None
        
        return max(self.snapshots, key=lambda s: s.snapshot_date)
    
    def has_snapshots_in_range(self, start_date: date, end_date: date) -> bool:
        """Check if universe has any snapshots in the given date range"""
        if not self.snapshots:
            return False
        
        return any(
            start_date <= snapshot.snapshot_date <= end_date
            for snapshot in self.snapshots
        )
    
    def get_snapshot_count(self) -> int:
        """Get total number of snapshots for this universe"""
        return len(self.snapshots) if self.snapshots else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Enhanced to_dict with asset relationship data and temporal information"""
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
            'assets': self.get_assets(),  # Full asset data with metadata
            # NEW: Temporal universe information (Sprint 2.5)
            'snapshot_count': self.get_snapshot_count(),
            'has_snapshots': self.get_snapshot_count() > 0,
            'latest_snapshot_date': self.get_latest_snapshot().snapshot_date.isoformat() if self.get_latest_snapshot() else None
        })
        return base_dict