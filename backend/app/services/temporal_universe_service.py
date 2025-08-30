"""
Temporal Universe Service - Sprint 2.5 Part C Implementation

Service for managing time-evolving universe compositions with advanced
temporal features including scheduling, screening with snapshots, and
comprehensive turnover analysis.

Complements UniverseService with specialized temporal functionality.
"""
import uuid
import calendar
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, text, select
from datetime import datetime, timezone, date, timedelta
import asyncio

from ..models.universe import Universe
from ..models.universe_snapshot import UniverseSnapshot
from ..models.asset import Asset, UniverseAsset
from ..models.user import User
from .interfaces.base import ServiceResult
from .interfaces.screener import IScreener, ScreeningCriteria, ScreeningResult
from .implementations.fundamental_screener import FundamentalScreener


class ScheduleConfig:
    """Configuration for universe update scheduling"""
    
    def __init__(
        self, 
        frequency: str, 
        start_date: date,
        end_date: Optional[date] = None,
        timezone: str = "UTC",
        execution_time: str = "09:00"
    ):
        self.frequency = frequency  # 'daily', 'weekly', 'monthly', 'quarterly'
        self.start_date = start_date
        self.end_date = end_date
        self.timezone = timezone
        self.execution_time = execution_time
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "frequency": self.frequency,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "timezone": self.timezone,
            "execution_time": self.execution_time
        }


class TurnoverAnalysis:
    """Comprehensive turnover analysis results"""
    
    def __init__(self):
        self.period_turnovers: List[float] = []
        self.average_turnover: float = 0.0
        self.turnover_volatility: float = 0.0
        self.stable_assets: List[str] = []
        self.volatile_assets: List[str] = []
        self.trend_direction: str = "stable"  # 'increasing', 'decreasing', 'stable'
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_turnovers": self.period_turnovers,
            "average_turnover": self.average_turnover,
            "turnover_volatility": self.turnover_volatility,
            "stable_assets": self.stable_assets,
            "volatile_assets": self.volatile_assets,
            "trend_direction": self.trend_direction,
            "analysis_quality": "high" if len(self.period_turnovers) >= 6 else "limited"
        }


class TemporalUniverseService:
    """
    Service for managing time-evolving universe compositions.
    
    Provides advanced temporal features:
    - Automated universe screening with snapshot creation
    - Scheduling of periodic universe updates  
    - Point-in-time composition retrieval with historical context
    - Comprehensive turnover pattern analysis
    - Asset stability tracking over time
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def _set_rls_context(self, user_id: str):
        """Set Row-Level Security context for multi-tenant isolation"""
        try:
            self.db.execute(text("SET LOCAL app.current_user_id = :user_id"), {"user_id": user_id})
        except Exception:
            # For SQLite development, RLS is simulated through query filtering
            pass
    
    async def schedule_universe_updates(
        self, 
        universe_id: str, 
        schedule_config: ScheduleConfig,
        user_id: str
    ) -> ServiceResult:
        """
        Schedule automatic universe screening updates.
        
        Args:
            universe_id: UUID of universe to schedule
            schedule_config: Scheduling configuration
            user_id: User requesting the scheduling
            
        Returns:
            ServiceResult with schedule details and next execution time
        """
        try:
            self._set_rls_context(user_id)
            
            # Verify universe exists and user has access
            universe = self.db.query(Universe).filter(
                and_(Universe.id == universe_id, Universe.owner_id == user_id)
            ).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Cannot schedule updates for non-existent or inaccessible universe"
                )
            
            if not universe.screening_criteria:
                return ServiceResult(
                    success=False,
                    error="No screening criteria",
                    message="Universe must have screening criteria before scheduling updates",
                    next_actions=[
                        "configure_screening_criteria",
                        "set_universe_screening_rules"
                    ]
                )
            
            # Calculate next execution dates based on frequency
            next_dates = self._calculate_next_execution_dates(schedule_config, limit=5)
            
            # Store schedule in universe metadata (in a real implementation, this would use a job scheduler)
            universe.screening_criteria['schedule'] = schedule_config.to_dict()
            universe.screening_criteria['next_executions'] = [d.isoformat() for d in next_dates]
            universe.screening_criteria['schedule_created'] = datetime.now(timezone.utc).isoformat()
            
            # Mark the JSON field as modified so SQLAlchemy detects the change
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(universe, 'screening_criteria')
            
            self.db.commit()
            
            return ServiceResult(
                success=True,
                data={
                    "schedule_config": schedule_config.to_dict(),
                    "next_executions": [d.isoformat() for d in next_dates],
                    "universe_info": {
                        "id": universe_id,
                        "name": universe.name,
                        "current_asset_count": universe.get_asset_count()
                    }
                },
                message=f"Scheduled {schedule_config.frequency} updates for universe '{universe.name}'",
                next_actions=[
                    "test_screening_criteria",
                    "preview_next_update",
                    "modify_schedule",
                    "monitor_universe_changes"
                ],
                metadata={
                    "universe_id": universe_id,
                    "frequency": schedule_config.frequency,
                    "next_execution": next_dates[0].isoformat() if next_dates else None,
                    "schedule_active": True
                }
            )
            
        except Exception as e:
            self.db.rollback()
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to schedule universe updates"
            )
    
    async def apply_screening_with_snapshots(
        self, 
        universe_id: str, 
        screening_date: date,
        user_id: str,
        create_snapshot: bool = True,
        screener: IScreener = None
    ) -> ServiceResult:
        """
        Apply screening and create snapshot without modifying current universe.
        
        This method enables "simulation mode" where screening results are captured
        as snapshots without changing the live universe composition.
        
        Args:
            universe_id: UUID of universe to screen
            screening_date: Date to apply screening for
            user_id: User requesting the screening
            create_snapshot: Whether to create a snapshot of results
            screener: Screener implementation (defaults to FundamentalScreener)
            
        Returns:
            ServiceResult with screening results and optional snapshot
        """
        try:
            self._set_rls_context(user_id)
            
            # Verify universe exists and user has access
            universe = self.db.query(Universe).options(
                selectinload(Universe.asset_associations).selectinload(UniverseAsset.asset)
            ).filter(
                and_(Universe.id == universe_id, Universe.owner_id == user_id)
            ).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Cannot apply screening for non-existent or inaccessible universe"
                )
            
            if not universe.screening_criteria:
                return ServiceResult(
                    success=False,
                    error="No screening criteria",
                    message="Universe must have screening criteria to apply screening",
                    next_actions=["configure_screening_criteria"]
                )
            
            # Initialize screener
            if screener is None:
                screener = FundamentalScreener(self.db)
            
            # Parse screening criteria
            criteria = ScreeningCriteria.from_json(universe.screening_criteria)
            
            # Validate criteria
            validation_result = await screener.validate_criteria(criteria)
            if not validation_result.success:
                return ServiceResult(
                    success=False,
                    error="Invalid screening criteria",
                    message=validation_result.message,
                    metadata=validation_result.metadata
                )
            
            # Get asset pool for screening
            asset_pool = self.db.query(Asset).filter(Asset.is_validated == True).all()
            
            # Apply screening
            screening_result = await screener.screen_universe(
                asset_pool=asset_pool,
                criteria=criteria,
                screening_date=datetime.combine(screening_date, datetime.min.time().replace(tzinfo=timezone.utc))
            )
            
            # Prepare screened assets for snapshot
            screened_assets = []
            for asset in screening_result.matching_assets:
                screened_assets.append({
                    'symbol': asset.symbol,
                    'name': asset.name,
                    'weight': None,  # Equal weight or calculated from screening
                    'asset_id': asset.id,
                    'reason_added': f"Met screening criteria on {screening_date}",
                    'sector': asset.asset_metadata.get('sector', 'Unknown') if asset.asset_metadata else 'Unknown'
                })
            
            # Calculate changes vs current universe
            current_symbols = {asset['symbol'] for asset in universe.get_assets()}
            screened_symbols = {asset['symbol'] for asset in screened_assets}
            
            changes_analysis = {
                "symbols_to_add": list(screened_symbols - current_symbols),
                "symbols_to_remove": list(current_symbols - screened_symbols),
                "symbols_unchanged": list(current_symbols & screened_symbols),
                "turnover_if_applied": len(screened_symbols.symmetric_difference(current_symbols)) / 
                                     len(screened_symbols.union(current_symbols)) if screened_symbols.union(current_symbols) else 0.0
            }
            
            # Create snapshot if requested
            snapshot_data = None
            if create_snapshot:
                # Get previous snapshot for turnover calculation
                previous_snapshot = self.db.query(UniverseSnapshot).filter(
                    and_(
                        UniverseSnapshot.universe_id == universe_id,
                        UniverseSnapshot.snapshot_date < screening_date
                    )
                ).order_by(UniverseSnapshot.snapshot_date.desc()).first()
                
                # Create snapshot with screening results
                snapshot = UniverseSnapshot.create_from_universe_state(
                    universe_id=universe_id,
                    snapshot_date=screening_date,
                    current_assets=screened_assets,
                    screening_criteria=universe.screening_criteria,
                    previous_snapshot=previous_snapshot
                )
                
                # Mark this as a simulation snapshot
                snapshot.screening_criteria['simulation_mode'] = True
                snapshot.screening_criteria['applied_to_live_universe'] = False
                
                self.db.add(snapshot)
                self.db.commit()
                self.db.refresh(snapshot)
                
                snapshot_data = snapshot.to_dict()
            
            return ServiceResult(
                success=True,
                data={
                    "screening_result": {
                        "screening_date": screening_date.isoformat(),
                        "total_screened": screening_result.total_screened,
                        "matches_found": len(screening_result.matching_assets),
                        "match_rate": screening_result.match_rate,
                        "screened_assets": screened_assets
                    },
                    "changes_analysis": changes_analysis,
                    "snapshot": snapshot_data,
                    "universe_info": {
                        "id": universe_id,
                        "name": universe.name,
                        "current_asset_count": universe.get_asset_count()
                    }
                },
                message=f"Screening applied for {screening_date} with {len(screened_assets)} qualifying assets",
                next_actions=[
                    "apply_changes_to_universe" if changes_analysis["turnover_if_applied"] > 0 else "maintain_current_composition",
                    "compare_with_current",
                    "analyze_turnover_impact",
                    "schedule_regular_screening"
                ],
                metadata={
                    "universe_id": universe_id,
                    "screening_date": screening_date.isoformat(),
                    "simulation_mode": True,
                    "turnover_if_applied": changes_analysis["turnover_if_applied"],
                    "snapshot_created": create_snapshot
                }
            )
            
        except Exception as e:
            self.db.rollback()
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to apply screening with snapshots"
            )
    
    async def get_point_in_time_composition(
        self, 
        universe_id: str, 
        target_date: date,
        user_id: str,
        include_context: bool = True
    ) -> ServiceResult:
        """
        Get universe composition at specific historical date with context.
        
        Args:
            universe_id: UUID of universe
            target_date: Date to retrieve composition for
            user_id: User requesting the data
            include_context: Whether to include historical context and analysis
            
        Returns:
            ServiceResult with point-in-time composition and optional context
        """
        try:
            self._set_rls_context(user_id)
            
            # Verify universe exists and user has access
            universe = self.db.query(Universe).filter(
                and_(Universe.id == universe_id, Universe.owner_id == user_id)
            ).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Cannot retrieve composition for non-existent or inaccessible universe"
                )
            
            # Find the most recent snapshot at or before target date
            snapshot = self.db.query(UniverseSnapshot).filter(
                and_(
                    UniverseSnapshot.universe_id == universe_id,
                    UniverseSnapshot.snapshot_date <= target_date
                )
            ).order_by(UniverseSnapshot.snapshot_date.desc()).first()
            
            if not snapshot:
                return ServiceResult(
                    success=False,
                    error="No snapshot found",
                    message=f"No universe snapshot found for {target_date} or earlier",
                    next_actions=[
                        "create_historical_snapshot",
                        "backfill_universe_history",
                        "choose_later_date"
                    ]
                )
            
            composition_data = {
                "target_date": target_date.isoformat(),
                "snapshot_date": snapshot.snapshot_date.isoformat(),
                "assets": snapshot.assets,
                "asset_count": len(snapshot.assets),
                "screening_criteria": snapshot.screening_criteria
            }
            
            # Add historical context if requested
            context_data = {}
            if include_context:
                # Get snapshots around this date for context
                context_snapshots = self.db.query(UniverseSnapshot).filter(
                    and_(
                        UniverseSnapshot.universe_id == universe_id,
                        UniverseSnapshot.snapshot_date >= (target_date - timedelta(days=90)),
                        UniverseSnapshot.snapshot_date <= (target_date + timedelta(days=90))
                    )
                ).order_by(UniverseSnapshot.snapshot_date.asc()).all()
                
                # Calculate composition stability around this date
                if len(context_snapshots) > 1:
                    stability_scores = []
                    for i in range(1, len(context_snapshots)):
                        prev_symbols = {asset['symbol'] for asset in context_snapshots[i-1].assets}
                        curr_symbols = {asset['symbol'] for asset in context_snapshots[i].assets}
                        
                        if prev_symbols.union(curr_symbols):
                            stability = 1.0 - (len(prev_symbols.symmetric_difference(curr_symbols)) / 
                                             len(prev_symbols.union(curr_symbols)))
                            stability_scores.append(stability)
                    
                    avg_stability = sum(stability_scores) / len(stability_scores) if stability_scores else 1.0
                    
                    context_data = {
                        "period_stability": avg_stability,
                        "context_snapshots": len(context_snapshots),
                        "composition_volatility": 1.0 - avg_stability,
                        "data_quality": "high" if len(context_snapshots) >= 6 else "moderate"
                    }
            
            return ServiceResult(
                success=True,
                data={
                    "composition": composition_data,
                    "context": context_data,
                    "universe_info": {
                        "id": universe_id,
                        "name": universe.name,
                        "description": universe.description
                    }
                },
                message=f"Retrieved universe composition for {target_date} (snapshot from {snapshot.snapshot_date})",
                next_actions=[
                    "compare_with_current",
                    "analyze_composition_changes",
                    "view_asset_performance",
                    "get_related_snapshots"
                ],
                metadata={
                    "universe_id": universe_id,
                    "target_date": target_date.isoformat(),
                    "actual_snapshot_date": snapshot.snapshot_date.isoformat(),
                    "days_difference": (target_date - snapshot.snapshot_date).days,
                    "context_included": include_context
                }
            )
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to retrieve point-in-time composition"
            )
    
    async def calculate_turnover_analysis(
        self, 
        universe_id: str, 
        analysis_period: str,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> ServiceResult:
        """
        Analyze universe turnover patterns over time.
        
        Args:
            universe_id: UUID of universe to analyze
            analysis_period: Period type ('3months', '6months', '1year', 'all', 'custom')
            user_id: User requesting the analysis
            start_date: Custom start date (if analysis_period is 'custom')
            end_date: Custom end date (if analysis_period is 'custom')
            
        Returns:
            ServiceResult with comprehensive turnover analysis
        """
        try:
            self._set_rls_context(user_id)
            
            # Verify universe exists and user has access
            universe = self.db.query(Universe).filter(
                and_(Universe.id == universe_id, Universe.owner_id == user_id)
            ).first()
            
            if not universe:
                return ServiceResult(
                    success=False,
                    error="Universe not found",
                    message="Cannot analyze turnover for non-existent or inaccessible universe"
                )
            
            # Calculate date range based on analysis_period
            end_analysis_date = end_date or date.today()
            
            if analysis_period == '3months':
                start_analysis_date = end_analysis_date - timedelta(days=90)
            elif analysis_period == '6months':
                start_analysis_date = end_analysis_date - timedelta(days=180)
            elif analysis_period == '1year':
                start_analysis_date = end_analysis_date - timedelta(days=365)
            elif analysis_period == 'custom':
                if not start_date:
                    return ServiceResult(
                        success=False,
                        error="Start date required for custom period",
                        message="Custom analysis period requires both start and end dates"
                    )
                start_analysis_date = start_date
            else:  # 'all'
                # Get earliest snapshot date
                earliest_snapshot = self.db.query(UniverseSnapshot).filter(
                    UniverseSnapshot.universe_id == universe_id
                ).order_by(UniverseSnapshot.snapshot_date.asc()).first()
                
                start_analysis_date = earliest_snapshot.snapshot_date if earliest_snapshot else end_analysis_date
            
            # Get snapshots in analysis period
            snapshots = self.db.query(UniverseSnapshot).filter(
                and_(
                    UniverseSnapshot.universe_id == universe_id,
                    UniverseSnapshot.snapshot_date >= start_analysis_date,
                    UniverseSnapshot.snapshot_date <= end_analysis_date
                )
            ).order_by(UniverseSnapshot.snapshot_date.asc()).all()
            
            if len(snapshots) < 2:
                return ServiceResult(
                    success=False,
                    error="Insufficient data",
                    message=f"Need at least 2 snapshots for turnover analysis, found {len(snapshots)}",
                    next_actions=[
                        "create_more_snapshots",
                        "backfill_historical_data",
                        "adjust_analysis_period"
                    ]
                )
            
            # Perform comprehensive turnover analysis
            analysis = TurnoverAnalysis()
            
            # Calculate period turnovers
            for snapshot in snapshots:
                if snapshot.turnover_rate is not None:
                    analysis.period_turnovers.append(float(snapshot.turnover_rate))
            
            if analysis.period_turnovers:
                analysis.average_turnover = sum(analysis.period_turnovers) / len(analysis.period_turnovers)
                
                # Calculate turnover volatility (standard deviation)
                if len(analysis.period_turnovers) > 1:
                    variance = sum((x - analysis.average_turnover) ** 2 for x in analysis.period_turnovers) / len(analysis.period_turnovers)
                    analysis.turnover_volatility = variance ** 0.5
            
            # Identify stable and volatile assets
            asset_appearances = {}
            total_snapshots = len(snapshots)
            
            for snapshot in snapshots:
                for asset in snapshot.assets:
                    symbol = asset['symbol']
                    if symbol not in asset_appearances:
                        asset_appearances[symbol] = 0
                    asset_appearances[symbol] += 1
            
            # Assets appearing in >80% of snapshots are considered stable
            stability_threshold = 0.8 * total_snapshots
            volatility_threshold = 0.3 * total_snapshots
            
            for symbol, appearances in asset_appearances.items():
                if appearances >= stability_threshold:
                    analysis.stable_assets.append(symbol)
                elif appearances <= volatility_threshold:
                    analysis.volatile_assets.append(symbol)
            
            # Determine turnover trend
            if len(analysis.period_turnovers) >= 3:
                recent_avg = sum(analysis.period_turnovers[-3:]) / 3
                earlier_avg = sum(analysis.period_turnovers[:3]) / 3
                
                if recent_avg > earlier_avg * 1.2:
                    analysis.trend_direction = "increasing"
                elif recent_avg < earlier_avg * 0.8:
                    analysis.trend_direction = "decreasing"
                else:
                    analysis.trend_direction = "stable"
            
            return ServiceResult(
                success=True,
                data={
                    "analysis": analysis.to_dict(),
                    "period_info": {
                        "start_date": start_analysis_date.isoformat(),
                        "end_date": end_analysis_date.isoformat(),
                        "total_days": (end_analysis_date - start_analysis_date).days,
                        "snapshots_analyzed": len(snapshots),
                        "analysis_period": analysis_period
                    },
                    "universe_info": {
                        "id": universe_id,
                        "name": universe.name,
                        "current_asset_count": universe.get_asset_count()
                    }
                },
                message=f"Turnover analysis completed for {analysis_period} period",
                next_actions=[
                    "optimize_screening_criteria",
                    "identify_stability_factors",
                    "create_turnover_alerts",
                    "compare_with_benchmarks"
                ],
                metadata={
                    "universe_id": universe_id,
                    "analysis_quality": analysis.to_dict()["analysis_quality"],
                    "average_turnover": analysis.average_turnover,
                    "stability_score": 1.0 - analysis.average_turnover
                }
            )
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to calculate turnover analysis"
            )
    
    def _calculate_next_execution_dates(self, config: ScheduleConfig, limit: int = 10) -> List[date]:
        """Calculate next execution dates based on schedule configuration"""
        dates = []
        current_date = config.start_date
        
        while len(dates) < limit and (not config.end_date or current_date <= config.end_date):
            if current_date >= date.today():
                dates.append(current_date)
            
            # Move to next scheduled date
            if config.frequency == 'daily':
                current_date += timedelta(days=1)
            elif config.frequency == 'weekly':
                current_date += timedelta(weeks=1)
            elif config.frequency == 'monthly':
                # Move to next month, handling month-end dates properly
                if current_date.month == 12:
                    next_year = current_date.year + 1
                    next_month = 1
                else:
                    next_year = current_date.year
                    next_month = current_date.month + 1
                
                # Handle cases where the day doesn't exist in the next month
                # (e.g., January 31 -> February 31 doesn't exist)
                try:
                    current_date = current_date.replace(year=next_year, month=next_month)
                except ValueError:
                    # If the day doesn't exist in the next month, use the last day of that month
                    last_day = calendar.monthrange(next_year, next_month)[1]
                    current_date = current_date.replace(year=next_year, month=next_month, day=last_day)
                    
            elif config.frequency == 'quarterly':
                # Move to next quarter, handling month-end dates properly
                new_month = current_date.month + 3
                new_year = current_date.year
                if new_month > 12:
                    new_month -= 12
                    new_year += 1
                
                # Handle cases where the day doesn't exist in the target month
                try:
                    current_date = current_date.replace(year=new_year, month=new_month)
                except ValueError:
                    # If the day doesn't exist in the target month, use the last day of that month
                    last_day = calendar.monthrange(new_year, new_month)[1]
                    current_date = current_date.replace(year=new_year, month=new_month, day=last_day)
            else:
                break  # Unknown frequency
        
        return dates


# Factory function for dependency injection
def get_temporal_universe_service(db: Session) -> TemporalUniverseService:
    """Factory function for creating TemporalUniverseService instances with dependency injection"""
    return TemporalUniverseService(db)