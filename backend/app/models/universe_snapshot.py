from sqlalchemy import Column, String, Date, JSON, DECIMAL, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from .base import BaseModel


class UniverseSnapshot(BaseModel):
    """
    Universe Snapshot Model - Point-in-time universe compositions
    
    Implements temporal universe system as specified in Sprint 2.5.
    Stores historical universe compositions to eliminate survivorship bias
    in backtesting and provide timeline evolution tracking.
    
    Design principles:
    - Point-in-time asset compositions with full metadata
    - Turnover tracking between periods  
    - Performance metrics at snapshot time
    - Relationship to parent Universe with cascade deletion
    - Unique constraint on (universe_id, snapshot_date)
    """
    __tablename__ = "universe_snapshots"
    
    # Core temporal identification
    universe_id = Column(String(36), ForeignKey("universes.id"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    
    # Point-in-time universe composition
    assets = Column(JSON, nullable=False)  # [{symbol, name, weight, reason_added, asset_id}, ...]
    
    # Screening and evolution metadata
    screening_criteria = Column(JSON)  # Criteria used to generate this snapshot
    turnover_rate = Column(DECIMAL(5, 4))  # Turnover rate vs previous period
    assets_added = Column(JSON)  # [symbols] added this period
    assets_removed = Column(JSON)  # [symbols] removed this period
    
    # Performance metrics at snapshot time
    performance_metrics = Column(JSON)  # {expected_return, volatility, sharpe_estimate, sector_allocation}
    
    # Relationships
    universe = relationship("Universe", back_populates="snapshots")
    
    # Database constraints
    __table_args__ = (
        # Ensure unique snapshots per universe per date
        UniqueConstraint('universe_id', 'snapshot_date', name='uq_universe_snapshot_date'),
        {'schema': None, 'extend_existing': True}
    )
    
    def __repr__(self) -> str:
        return f"<UniverseSnapshot(universe_id='{self.universe_id}', date='{self.snapshot_date}', assets={len(self.get_asset_symbols())})>"
    
    def get_asset_symbols(self) -> List[str]:
        """Extract asset symbols from the assets JSON field"""
        if not self.assets:
            return []
        
        if isinstance(self.assets, list):
            return [asset.get('symbol') for asset in self.assets if asset.get('symbol')]
        
        return []
    
    def get_asset_count(self) -> int:
        """Get total number of assets in this snapshot"""
        return len(self.get_asset_symbols())
    
    def get_assets_by_sector(self) -> Dict[str, List[str]]:
        """Group assets by sector for analysis"""
        if not self.assets:
            return {}
        
        sectors = {}
        for asset in self.assets:
            sector = asset.get('sector', 'Unknown')
            if sector not in sectors:
                sectors[sector] = []
            sectors[sector].append(asset.get('symbol'))
        
        return sectors
    
    def calculate_portfolio_weight(self, symbol: str) -> Optional[float]:
        """Get the weight of a specific asset in this snapshot"""
        if not self.assets:
            return None
        
        for asset in self.assets:
            if asset.get('symbol') == symbol:
                return asset.get('weight')
        
        return None
    
    def get_turnover_analysis(self) -> Dict[str, Any]:
        """Get detailed turnover analysis for this snapshot"""
        return {
            'snapshot_date': self.snapshot_date.isoformat() if self.snapshot_date else None,
            'turnover_rate': float(self.turnover_rate) if self.turnover_rate else 0.0,
            'assets_added': self.assets_added or [],
            'assets_removed': self.assets_removed or [],
            'net_change': len(self.assets_added or []) - len(self.assets_removed or []),
            'total_assets': self.get_asset_count()
        }
    
    def validate_assets_structure(self) -> bool:
        """Validate that assets JSON has correct structure"""
        if not self.assets:
            return False
        
        if not isinstance(self.assets, list):
            return False
        
        required_fields = ['symbol', 'name']
        for asset in self.assets:
            if not isinstance(asset, dict):
                return False
            
            for field in required_fields:
                if field not in asset:
                    return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Enhanced to_dict with snapshot-specific data"""
        base_dict = super().to_dict()
        base_dict.update({
            'universe_id': self.universe_id,
            'snapshot_date': self.snapshot_date.isoformat() if self.snapshot_date else None,
            'assets': self.assets or [],
            'screening_criteria': self.screening_criteria or {},
            'turnover_rate': float(self.turnover_rate) if self.turnover_rate is not None else 0.0,
            'assets_added': self.assets_added or [],
            'assets_removed': self.assets_removed or [],
            'performance_metrics': self.performance_metrics or {},
            'asset_count': self.get_asset_count(),
            'asset_symbols': self.get_asset_symbols(),
            'turnover_analysis': self.get_turnover_analysis()
        })
        return base_dict
    
    @classmethod
    def create_from_universe_state(
        cls, 
        universe_id: str, 
        snapshot_date: datetime, 
        current_assets: List[Dict[str, Any]],
        screening_criteria: Optional[Dict[str, Any]] = None,
        previous_snapshot: Optional['UniverseSnapshot'] = None
    ) -> 'UniverseSnapshot':
        """
        Factory method to create snapshot from current universe state
        
        Args:
            universe_id: UUID of parent universe
            snapshot_date: Date of this snapshot  
            current_assets: Current asset composition
            screening_criteria: Criteria used to generate assets
            previous_snapshot: Previous snapshot for turnover calculation
            
        Returns:
            New UniverseSnapshot instance
        """
        # Calculate turnover vs previous period
        turnover_rate = 0.0
        assets_added = []
        assets_removed = []
        
        if previous_snapshot:
            current_symbols = {asset.get('symbol') for asset in current_assets}
            previous_symbols = set(previous_snapshot.get_asset_symbols())
            
            assets_added = list(current_symbols - previous_symbols)
            assets_removed = list(previous_symbols - current_symbols)
            
            # Calculate turnover rate
            if current_symbols.union(previous_symbols):
                changes = len(current_symbols.symmetric_difference(previous_symbols))
                total = len(current_symbols.union(previous_symbols))
                turnover_rate = changes / total
        
        # Convert string dates to date objects if needed
        if isinstance(snapshot_date, str):
            from datetime import datetime as dt
            snapshot_date = dt.strptime(snapshot_date, '%Y-%m-%d').date()
        elif hasattr(snapshot_date, 'date'):
            snapshot_date = snapshot_date.date()
        
        return cls(
            universe_id=universe_id,
            snapshot_date=snapshot_date,
            assets=current_assets,
            screening_criteria=screening_criteria or {},
            turnover_rate=turnover_rate,
            assets_added=assets_added,
            assets_removed=assets_removed,
            performance_metrics={}  # Will be populated by performance calculation service
        )