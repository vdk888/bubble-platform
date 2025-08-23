from sqlalchemy import Column, String, Text, ForeignKey, JSON, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from typing import List
from .base import BaseModel

class Universe(BaseModel):
    __tablename__ = "universes"
    
    name = Column(String(100), nullable=False)
    description = Column(Text)
    symbols = Column(JSON, nullable=False)  # List of asset symbols
    
    # Dynamic screening criteria
    screening_criteria = Column(JSON)  # Flexible screening rules
    last_screening_date = Column(DateTime(timezone=True))
    turnover_rate = Column(Float)  # Track universe evolution
    
    # Ownership
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="universes")
    
    # Relationships
    strategies = relationship("Strategy", back_populates="universe", cascade="all, delete-orphan")
    
    def get_symbols(self) -> List[str]:
        """Get current universe symbols"""
        return self.symbols if isinstance(self.symbols, list) else []
    
    def update_symbols(self, new_symbols: List[str]):
        """Update universe with turnover tracking"""
        if self.symbols:
            old_set = set(self.get_symbols())
            new_set = set(new_symbols)
            if old_set.union(new_set):  # Avoid division by zero
                self.turnover_rate = len(old_set.symmetric_difference(new_set)) / len(old_set.union(new_set))
        self.symbols = new_symbols
        self.last_screening_date = datetime.now(timezone.utc)