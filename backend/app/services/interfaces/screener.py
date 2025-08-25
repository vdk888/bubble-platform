"""
Universe screening interface definition for dynamic filtering and rebalancing.

Following Interface-First Design methodology as specified in CLAUDE.md:
- Define contracts before implementation
- Enable parallel development and testing with mocks
- Support future microservices evolution
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

from ...models.asset import Asset
from .base import ServiceResult


class ScreeningCriteria:
    """
    Screening criteria data class for universe filtering.
    
    Supports multiple metrics as specified in planning/1_spec.md:
    - Market cap filters (min/max)
    - P/E ratio constraints
    - Dividend yield requirements  
    - Sector inclusion/exclusion
    - ROIC-based filters for fundamental analysis
    """
    
    def __init__(
        self,
        min_market_cap: Optional[float] = None,
        max_market_cap: Optional[float] = None,
        min_pe_ratio: Optional[float] = None,
        max_pe_ratio: Optional[float] = None,
        min_dividend_yield: Optional[float] = None,
        max_dividend_yield: Optional[float] = None,
        sectors_include: Optional[List[str]] = None,
        sectors_exclude: Optional[List[str]] = None,
        min_roic: Optional[float] = None,
        max_roic: Optional[float] = None,
        custom_filters: Optional[Dict[str, Any]] = None
    ):
        self.min_market_cap = min_market_cap
        self.max_market_cap = max_market_cap
        self.min_pe_ratio = min_pe_ratio
        self.max_pe_ratio = max_pe_ratio
        self.min_dividend_yield = min_dividend_yield
        self.max_dividend_yield = max_dividend_yield
        self.sectors_include = sectors_include or []
        self.sectors_exclude = sectors_exclude or []
        self.min_roic = min_roic
        self.max_roic = max_roic
        self.custom_filters = custom_filters or {}
        
    @classmethod
    def from_json(cls, criteria_dict: Dict[str, Any]) -> 'ScreeningCriteria':
        """Create ScreeningCriteria from JSON dictionary (database storage)"""
        return cls(
            min_market_cap=criteria_dict.get('min_market_cap'),
            max_market_cap=criteria_dict.get('max_market_cap'),
            min_pe_ratio=criteria_dict.get('min_pe_ratio'),
            max_pe_ratio=criteria_dict.get('max_pe_ratio'),
            min_dividend_yield=criteria_dict.get('min_dividend_yield'),
            max_dividend_yield=criteria_dict.get('max_dividend_yield'),
            sectors_include=criteria_dict.get('sectors_include', []),
            sectors_exclude=criteria_dict.get('sectors_exclude', []),
            min_roic=criteria_dict.get('min_roic'),
            max_roic=criteria_dict.get('max_roic'),
            custom_filters=criteria_dict.get('custom_filters', {})
        )
        
    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON dictionary for database storage"""
        return {
            'min_market_cap': self.min_market_cap,
            'max_market_cap': self.max_market_cap,
            'min_pe_ratio': self.min_pe_ratio,
            'max_pe_ratio': self.max_pe_ratio,
            'min_dividend_yield': self.min_dividend_yield,
            'max_dividend_yield': self.max_dividend_yield,
            'sectors_include': self.sectors_include,
            'sectors_exclude': self.sectors_exclude,
            'min_roic': self.min_roic,
            'max_roic': self.max_roic,
            'custom_filters': self.custom_filters
        }


class ScreeningResult:
    """
    Result of screening operation with detailed metadata.
    
    Contains filtered assets and screening analytics for performance tracking.
    """
    
    def __init__(
        self,
        matching_assets: List[Asset],
        total_screened: int,
        criteria_applied: ScreeningCriteria,
        screening_date: datetime,
        performance_metrics: Optional[Dict[str, Any]] = None
    ):
        self.matching_assets = matching_assets
        self.total_screened = total_screened
        self.criteria_applied = criteria_applied
        self.screening_date = screening_date
        self.performance_metrics = performance_metrics or {}
        
    @property
    def match_rate(self) -> float:
        """Percentage of assets that passed screening criteria"""
        if self.total_screened == 0:
            return 0.0
        return (len(self.matching_assets) / self.total_screened) * 100


class IScreener(ABC):
    """
    Abstract interface for universe screening implementations.
    
    Enables multiple screening strategies:
    - FundamentalScreener: P/E ratio, market cap, dividend yield, ROIC
    - TechnicalScreener: Price momentum, volume, technical indicators  
    - CompositeScreener: Combined fundamental + technical criteria
    - MockScreener: For testing with predictable results
    
    Following Interface-First Design principles for clean service boundaries.
    """
    
    @abstractmethod
    async def screen_universe(
        self, 
        asset_pool: List[Asset],
        criteria: ScreeningCriteria,
        screening_date: datetime
    ) -> ScreeningResult:
        """
        Apply screening criteria to asset pool and return filtered results.
        
        Args:
            asset_pool: List of assets to screen
            criteria: Screening criteria to apply
            screening_date: Date for time-sensitive screening
            
        Returns:
            ScreeningResult with matching assets and metadata
            
        Raises:
            ScreeningError: When screening fails or criteria are invalid
        """
        pass
    
    @abstractmethod
    async def validate_criteria(self, criteria: ScreeningCriteria) -> ServiceResult:
        """
        Validate screening criteria before application.
        
        Args:
            criteria: Screening criteria to validate
            
        Returns:
            ServiceResult with validation status and suggestions
        """
        pass
    
    @abstractmethod
    async def get_screening_stats(
        self, 
        asset_pool: List[Asset],
        criteria: ScreeningCriteria
    ) -> Dict[str, Any]:
        """
        Get statistics about how screening criteria would perform.
        
        Useful for criteria optimization and understanding impact.
        
        Args:
            asset_pool: Assets to analyze
            criteria: Criteria to evaluate
            
        Returns:
            Dictionary with screening statistics and projections
        """
        pass


class ScreeningError(Exception):
    """Custom exception for screening operations"""
    pass