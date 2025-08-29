from sqlalchemy import Column, String, Text, DECIMAL, BIGINT, Boolean, DateTime, Index, ForeignKey, JSON
from sqlalchemy.orm import relationship, validates
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import re
from .base import BaseModel

class Asset(BaseModel):
    """
    Asset entity model with normalized metadata storage.
    
    Following Phase 2 Decision #2: Separate Asset Entity with Relationships
    - Enables V1 advanced screener capabilities
    - Supports complex queries and proper domain modeling
    - Clean service boundaries for microservices migration
    """
    __tablename__ = "assets"
    
    # Core asset identification
    symbol = Column(String(50), unique=True, nullable=False, index=True)  # Increased from 20 to 50 for longer symbols
    name = Column(String(255), nullable=False)
    
    # Fundamental data for screening
    sector = Column(String(100), index=True)
    industry = Column(String(100))
    market_cap = Column(BIGINT)  # Market cap in USD
    pe_ratio = Column(DECIMAL(8, 2))  # Price-to-earnings ratio
    dividend_yield = Column(DECIMAL(5, 4))  # Dividend yield as decimal (0.0350 = 3.5%)
    
    # Validation tracking (Phase 2 Decision #1: Mixed Validation Strategy)
    is_validated = Column(Boolean, default=False, nullable=False, index=True)
    last_validated_at = Column(DateTime(timezone=True))
    validation_source = Column(String(50))  # 'yahoo', 'alpha_vantage', etc.
    validation_errors = Column(Text)  # Store validation error messages
    
    # Flexible metadata storage for additional data
    asset_metadata = Column(JSON, default=dict)  # JSON for extensibility (compatible with both SQLite and PostgreSQL)
    
    # Relationships - many-to-many with universes
    universe_associations = relationship(
        "UniverseAsset", 
        back_populates="asset", 
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Asset(symbol='{self.symbol}', name='{self.name}', validated={self.is_validated})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Enhanced to_dict with asset-specific fields"""
        base_dict = super().to_dict()
        base_dict.update({
            'symbol': self.symbol,
            'name': self.name,
            'sector': self.sector,
            'industry': self.industry,
            'market_cap': float(self.market_cap) if self.market_cap is not None else None,
            'pe_ratio': float(self.pe_ratio) if self.pe_ratio is not None else None,
            'dividend_yield': float(self.dividend_yield) if self.dividend_yield is not None else None,
            'is_validated': self.is_validated,
            'last_validated_at': self.last_validated_at.isoformat() if self.last_validated_at else None,
            'validation_source': self.validation_source,
            'asset_metadata': self.asset_metadata or {}
        })
        return base_dict
    
    def is_stale_validation(self, max_age_hours: int = 24) -> bool:
        """Check if asset validation is stale"""
        if not self.is_validated or not self.last_validated_at:
            return True
        
        now = datetime.now(timezone.utc)
        age_hours = (now - self.last_validated_at).total_seconds() / 3600
        return age_hours > max_age_hours
    
    @validates('symbol')
    def validate_symbol(self, key, symbol):
        """Validate that symbol looks like a valid stock ticker"""
        if not symbol:
            raise ValueError("Symbol cannot be empty")
        
        # Check for obvious non-symbol patterns
        if len(symbol) > 20:  # Even with increased length, flag unusually long symbols
            raise ValueError(f"Symbol '{symbol}' appears to be descriptive text, not a ticker symbol")
        
        # Check for patterns that suggest descriptive text
        descriptive_patterns = [
            r'universe',
            r'without',
            r'temporal',
            r'data',
            r'static',
            r'\s+',  # Multiple spaces
        ]
        
        for pattern in descriptive_patterns:
            if re.search(pattern, symbol.lower()):
                raise ValueError(f"Symbol '{symbol}' appears to contain descriptive text. Please use valid ticker symbols only (e.g., AAPL, GOOGL, MSFT)")
        
        return symbol.upper()  # Always store symbols in uppercase

    def update_validation_status(
        self, 
        is_valid: bool, 
        source: str, 
        error_message: Optional[str] = None,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update validation status with tracking"""
        self.is_validated = is_valid
        self.last_validated_at = datetime.now(timezone.utc)
        self.validation_source = source
        self.validation_errors = error_message
        
        if metadata_updates:
            current_metadata = self.asset_metadata or {}
            current_metadata.update(metadata_updates)
            self.asset_metadata = current_metadata


class UniverseAsset(BaseModel):
    """
    Junction table for many-to-many relationship between Universe and Asset.
    
    This replaces the JSON symbols field in Universe with proper normalized relationships.
    Supports ordering, tracking when assets were added, and additional relationship metadata.
    """
    __tablename__ = "universe_assets"
    
    # Foreign keys
    universe_id = Column(String(36), ForeignKey("universes.id"), nullable=False, index=True)
    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=False, index=True)
    
    # Relationship metadata
    position = Column(BIGINT)  # For ordering assets within universe
    added_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    weight = Column(DECIMAL(5, 4))  # Optional weight for the asset in universe (0.0000-1.0000)
    notes = Column(Text)  # Optional notes about why this asset is in the universe
    
    # Relationships
    universe = relationship("Universe", back_populates="asset_associations")
    asset = relationship("Asset", back_populates="universe_associations")
    
    # Composite primary key
    __table_args__ = (
        Index('idx_universe_assets_universe', 'universe_id'),
        Index('idx_universe_assets_asset', 'asset_id'),
        Index('idx_universe_assets_composite', 'universe_id', 'asset_id'),
        # Ensure uniqueness
        {'extend_existing': True}
    )
    
    def __repr__(self) -> str:
        return f"<UniverseAsset(universe_id='{self.universe_id}', asset_id='{self.asset_id}', position={self.position})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Enhanced to_dict for relationship metadata"""
        base_dict = super().to_dict()
        base_dict.update({
            'universe_id': self.universe_id,
            'asset_id': self.asset_id,
            'position': self.position,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'weight': float(self.weight) if self.weight else None,
            'notes': self.notes
        })
        return base_dict