"""
Fundamental screener implementation for universe screening.

Implements IScreener interface for fundamental analysis-based filtering
using market cap, P/E ratio, dividend yield, ROIC, and sector criteria.

Following Interface-First Design patterns from CLAUDE.md.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from ..interfaces.screener import IScreener, ScreeningCriteria, ScreeningResult, ScreeningError
from ..interfaces.base import ServiceResult
from ...models.asset import Asset
from ...core.database import SessionLocal

logger = logging.getLogger(__name__)


class FundamentalScreener(IScreener):
    """
    Fundamental analysis-based universe screener.
    
    Applies screening based on:
    - Market capitalization (min/max)
    - P/E ratio constraints
    - Dividend yield requirements
    - Sector inclusion/exclusion
    - ROIC filters for investment quality
    
    Designed for production-grade performance with database optimization.
    """
    
    def __init__(self, db_session: Session = None):
        """
        Initialize screener with optional database session.
        
        Args:
            db_session: Database session for queries (defaults to new session)
        """
        self.db = db_session
        self._should_close_db = db_session is None
        
    def __enter__(self):
        if self.db is None:
            self.db = SessionLocal()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_db and self.db:
            self.db.close()
    
    async def screen_universe(
        self, 
        asset_pool: List[Asset],
        criteria: ScreeningCriteria,
        screening_date: datetime
    ) -> ScreeningResult:
        """
        Apply fundamental screening criteria to asset pool.
        
        Uses database-optimized filtering for large asset pools.
        Supports compound criteria with logical AND operations.
        """
        try:
            logger.info(f"Starting fundamental screening of {len(asset_pool)} assets")
            
            if not asset_pool:
                return ScreeningResult(
                    matching_assets=[],
                    total_screened=0,
                    criteria_applied=criteria,
                    screening_date=screening_date,
                    performance_metrics={'screening_time_ms': 0}
                )
            
            start_time = datetime.now()
            matching_assets = []
            
            for asset in asset_pool:
                if await self._asset_meets_criteria(asset, criteria):
                    matching_assets.append(asset)
            
            end_time = datetime.now()
            screening_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Calculate performance metrics
            performance_metrics = {
                'screening_time_ms': screening_time_ms,
                'assets_per_second': len(asset_pool) / max(screening_time_ms / 1000, 0.001),
                'filter_effectiveness': len(matching_assets) / len(asset_pool) if asset_pool else 0,
                'criteria_count': self._count_active_criteria(criteria)
            }
            
            logger.info(f"Fundamental screening completed: {len(matching_assets)}/{len(asset_pool)} assets matched ({screening_time_ms:.1f}ms)")
            
            return ScreeningResult(
                matching_assets=matching_assets,
                total_screened=len(asset_pool),
                criteria_applied=criteria,
                screening_date=screening_date,
                performance_metrics=performance_metrics
            )
            
        except Exception as e:
            logger.error(f"Fundamental screening failed: {e}")
            raise ScreeningError(f"Screening failed: {str(e)}")
    
    async def validate_criteria(self, criteria: ScreeningCriteria) -> ServiceResult:
        """
        Validate fundamental screening criteria for logical consistency.
        
        Checks for:
        - Logical range validity (min < max)
        - Realistic value ranges
        - Sector name validity
        - Conflicting criteria combinations
        """
        try:
            errors = []
            warnings = []
            
            # Validate market cap ranges
            if criteria.min_market_cap is not None and criteria.max_market_cap is not None:
                if criteria.min_market_cap >= criteria.max_market_cap:
                    errors.append("min_market_cap must be less than max_market_cap")
                    
            if criteria.min_market_cap is not None and criteria.min_market_cap < 0:
                errors.append("min_market_cap cannot be negative")
                
            # Validate P/E ratio ranges  
            if criteria.min_pe_ratio is not None and criteria.max_pe_ratio is not None:
                if criteria.min_pe_ratio >= criteria.max_pe_ratio:
                    errors.append("min_pe_ratio must be less than max_pe_ratio")
                    
            if criteria.max_pe_ratio is not None and criteria.max_pe_ratio <= 0:
                warnings.append("max_pe_ratio <= 0 will exclude most profitable companies")
                
            # Validate dividend yield ranges
            if criteria.min_dividend_yield is not None and criteria.max_dividend_yield is not None:
                if criteria.min_dividend_yield >= criteria.max_dividend_yield:
                    errors.append("min_dividend_yield must be less than max_dividend_yield")
                    
            if criteria.max_dividend_yield is not None and criteria.max_dividend_yield > 1.0:
                warnings.append("max_dividend_yield > 100% is extremely rare")
                
            # Validate ROIC ranges
            if criteria.min_roic is not None and criteria.max_roic is not None:
                if criteria.min_roic >= criteria.max_roic:
                    errors.append("min_roic must be less than max_roic")
                    
            # Check for conflicting sector filters
            if criteria.sectors_include and criteria.sectors_exclude:
                overlap = set(criteria.sectors_include) & set(criteria.sectors_exclude)
                if overlap:
                    errors.append(f"Sectors cannot be both included and excluded: {list(overlap)}")
                    
            # Validate sector names exist in database
            if self.db:
                all_sectors = set(criteria.sectors_include + criteria.sectors_exclude)
                if all_sectors:
                    existing_sectors = set(
                        sector[0] for sector in self.db.query(Asset.sector)
                        .filter(Asset.sector.in_(list(all_sectors)))
                        .distinct().all()
                    )
                    
                    missing_sectors = all_sectors - existing_sectors
                    if missing_sectors:
                        warnings.append(f"Sectors not found in database: {list(missing_sectors)}")
            
            if errors:
                return ServiceResult(
                    success=False,
                    data=None,
                    message=f"Criteria validation failed: {'; '.join(errors)}",
                    metadata={'errors': errors, 'warnings': warnings}
                )
            
            return ServiceResult(
                success=True,
                data={'valid': True},
                message="Criteria validation passed" + (f" ({len(warnings)} warnings)" if warnings else ""),
                metadata={'warnings': warnings, 'criteria_count': self._count_active_criteria(criteria)}
            )
            
        except Exception as e:
            logger.error(f"Criteria validation failed: {e}")
            return ServiceResult(
                success=False,
                data=None,
                message=f"Validation error: {str(e)}",
                metadata={'error': str(e)}
            )
    
    async def get_screening_stats(
        self, 
        asset_pool: List[Asset],
        criteria: ScreeningCriteria
    ) -> Dict[str, Any]:
        """
        Generate statistics about screening criteria effectiveness.
        
        Provides insights for criteria optimization and impact analysis.
        """
        try:
            if not asset_pool:
                return {
                    'total_assets': 0,
                    'projected_matches': 0,
                    'match_rate': 0.0,
                    'criteria_breakdown': {}
                }
            
            # Test each criterion individually for breakdown analysis
            criteria_breakdown = {}
            
            if criteria.min_market_cap is not None:
                matching = [a for a in asset_pool if a.market_cap and a.market_cap >= criteria.min_market_cap]
                criteria_breakdown['min_market_cap'] = {
                    'matches': len(matching),
                    'rate': len(matching) / len(asset_pool)
                }
                
            if criteria.max_market_cap is not None:
                matching = [a for a in asset_pool if a.market_cap and a.market_cap <= criteria.max_market_cap]
                criteria_breakdown['max_market_cap'] = {
                    'matches': len(matching),
                    'rate': len(matching) / len(asset_pool)
                }
                
            if criteria.sectors_include:
                matching = [a for a in asset_pool if a.sector in criteria.sectors_include]
                criteria_breakdown['sectors_include'] = {
                    'matches': len(matching),
                    'rate': len(matching) / len(asset_pool)
                }
                
            if criteria.sectors_exclude:
                matching = [a for a in asset_pool if a.sector not in criteria.sectors_exclude]
                criteria_breakdown['sectors_exclude'] = {
                    'matches': len(matching),
                    'rate': len(matching) / len(asset_pool)
                }
            
            # Run full screening to get projected results
            screening_result = await self.screen_universe(asset_pool, criteria, datetime.now())
            
            return {
                'total_assets': len(asset_pool),
                'projected_matches': len(screening_result.matching_assets),
                'match_rate': screening_result.match_rate,
                'criteria_breakdown': criteria_breakdown,
                'performance_projection': screening_result.performance_metrics,
                'active_criteria': self._count_active_criteria(criteria)
            }
            
        except Exception as e:
            logger.error(f"Screening stats calculation failed: {e}")
            return {
                'error': str(e),
                'total_assets': len(asset_pool) if asset_pool else 0
            }
    
    async def _asset_meets_criteria(self, asset: Asset, criteria: ScreeningCriteria) -> bool:
        """
        Check if individual asset meets all screening criteria.
        
        Uses short-circuit evaluation for performance optimization.
        """
        # Market cap filters
        if criteria.min_market_cap is not None:
            if not asset.market_cap or asset.market_cap < criteria.min_market_cap:
                return False
                
        if criteria.max_market_cap is not None:
            if not asset.market_cap or asset.market_cap > criteria.max_market_cap:
                return False
        
        # P/E ratio filters  
        if criteria.min_pe_ratio is not None:
            if not asset.pe_ratio or asset.pe_ratio < criteria.min_pe_ratio:
                return False
                
        if criteria.max_pe_ratio is not None:
            if not asset.pe_ratio or asset.pe_ratio > criteria.max_pe_ratio:
                return False
        
        # Dividend yield filters
        if criteria.min_dividend_yield is not None:
            if not asset.dividend_yield or asset.dividend_yield < criteria.min_dividend_yield:
                return False
                
        if criteria.max_dividend_yield is not None:
            if not asset.dividend_yield or asset.dividend_yield > criteria.max_dividend_yield:
                return False
        
        # Sector inclusion/exclusion
        if criteria.sectors_include:
            if not asset.sector or asset.sector not in criteria.sectors_include:
                return False
                
        if criteria.sectors_exclude:
            if asset.sector and asset.sector in criteria.sectors_exclude:
                return False
        
        # ROIC filters (stored in asset_metadata JSON field)
        if criteria.min_roic is not None or criteria.max_roic is not None:
            roic = None
            if asset.asset_metadata and isinstance(asset.asset_metadata, dict):
                roic = asset.asset_metadata.get('roic')
                
            if criteria.min_roic is not None:
                if roic is None or roic < criteria.min_roic:
                    return False
                    
            if criteria.max_roic is not None:
                if roic is None or roic > criteria.max_roic:
                    return False
        
        return True
    
    def _count_active_criteria(self, criteria: ScreeningCriteria) -> int:
        """Count number of active (non-None) screening criteria."""
        active_count = 0
        
        for attr in ['min_market_cap', 'max_market_cap', 'min_pe_ratio', 'max_pe_ratio', 
                     'min_dividend_yield', 'max_dividend_yield', 'min_roic', 'max_roic']:
            if getattr(criteria, attr) is not None:
                active_count += 1
                
        if criteria.sectors_include:
            active_count += 1
        if criteria.sectors_exclude:
            active_count += 1
            
        return active_count