"""
Universe Tracker - Evolution Module Component

Tracks universe changes over time and calculates comprehensive metrics
including turnover, stability, and composition evolution patterns.
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from collections import defaultdict
import statistics


@dataclass
class AssetChange:
    """Represents a single asset change between snapshots"""
    symbol: str
    change_type: str  # 'added', 'removed', 'weight_changed', 'unchanged'
    old_weight: Optional[float]
    new_weight: Optional[float]
    change_date: date
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "change_type": self.change_type,
            "old_weight": self.old_weight,
            "new_weight": self.new_weight,
            "weight_delta": (self.new_weight or 0) - (self.old_weight or 0),
            "change_date": self.change_date.isoformat(),
            "reason": self.reason
        }


@dataclass
class ChangeAnalysis:
    """Comprehensive analysis of changes between universe snapshots"""
    comparison_date: date
    previous_date: Optional[date]
    
    # Basic change counts
    assets_added: List[AssetChange]
    assets_removed: List[AssetChange]
    assets_weight_changed: List[AssetChange]
    assets_unchanged: List[AssetChange]
    
    # Aggregate metrics
    turnover_rate: float
    composition_stability: float
    weight_drift: float
    
    # Sector analysis
    sector_changes: Dict[str, Dict[str, Any]]
    
    # Change momentum
    change_acceleration: Optional[float]  # Change in turnover rate
    stability_trend: str  # 'improving', 'degrading', 'stable'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "comparison_date": self.comparison_date.isoformat(),
            "previous_date": self.previous_date.isoformat() if self.previous_date else None,
            "changes": {
                "assets_added": [change.to_dict() for change in self.assets_added],
                "assets_removed": [change.to_dict() for change in self.assets_removed],
                "assets_weight_changed": [change.to_dict() for change in self.assets_weight_changed],
                "assets_unchanged": [change.to_dict() for change in self.assets_unchanged]
            },
            "metrics": {
                "turnover_rate": self.turnover_rate,
                "composition_stability": self.composition_stability,
                "weight_drift": self.weight_drift,
                "total_changes": len(self.assets_added) + len(self.assets_removed) + len(self.assets_weight_changed),
                "change_acceleration": self.change_acceleration,
                "stability_trend": self.stability_trend
            },
            "sector_analysis": self.sector_changes,
            "summary": {
                "added_count": len(self.assets_added),
                "removed_count": len(self.assets_removed),
                "weight_changed_count": len(self.assets_weight_changed),
                "unchanged_count": len(self.assets_unchanged),
                "net_asset_change": len(self.assets_added) - len(self.assets_removed)
            }
        }


@dataclass
class TurnoverMetrics:
    """Comprehensive turnover metrics for universe evolution"""
    analysis_period: str
    start_date: date
    end_date: date
    
    # Basic turnover statistics
    period_turnovers: List[float]
    average_turnover: float
    turnover_volatility: float
    min_turnover: float
    max_turnover: float
    
    # Trend analysis
    turnover_trend: str  # 'increasing', 'decreasing', 'stable', 'volatile'
    trend_strength: float  # 0-1, strength of the trend
    
    # Asset stability metrics
    core_assets: List[str]  # Assets present in >80% of periods
    volatile_assets: List[str]  # Assets present in <30% of periods
    stability_score: float  # 0-1, overall stability
    
    # Frequency analysis
    rebalance_frequency: float  # Average periods between significant changes
    change_seasonality: Dict[str, float]  # Monthly/quarterly patterns
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_period": self.analysis_period,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "basic_statistics": {
                "period_turnovers": self.period_turnovers,
                "average_turnover": self.average_turnover,
                "turnover_volatility": self.turnover_volatility,
                "min_turnover": self.min_turnover,
                "max_turnover": self.max_turnover,
                "periods_analyzed": len(self.period_turnovers)
            },
            "trend_analysis": {
                "turnover_trend": self.turnover_trend,
                "trend_strength": self.trend_strength,
                "stability_score": self.stability_score
            },
            "asset_stability": {
                "core_assets": self.core_assets,
                "volatile_assets": self.volatile_assets,
                "core_asset_count": len(self.core_assets),
                "volatile_asset_count": len(self.volatile_assets)
            },
            "frequency_patterns": {
                "rebalance_frequency": self.rebalance_frequency,
                "change_seasonality": self.change_seasonality
            }
        }


class UniverseTracker:
    """
    Comprehensive universe change tracking and analysis.
    
    Provides detailed analysis of universe evolution including:
    - Asset-level change tracking
    - Turnover pattern analysis  
    - Composition stability metrics
    - Sector rotation analysis
    """
    
    def __init__(self):
        self.change_history: Dict[str, List[ChangeAnalysis]] = defaultdict(list)
        
    def track_universe_changes(
        self,
        universe_id: str,
        old_snapshot: Dict[str, Any],
        new_snapshot: Dict[str, Any]
    ) -> ChangeAnalysis:
        """
        Track and analyze changes between two universe snapshots.
        
        Args:
            universe_id: UUID of the universe being tracked
            old_snapshot: Previous snapshot data
            new_snapshot: Current snapshot data
            
        Returns:
            ChangeAnalysis with detailed change information
        """
        old_date = datetime.fromisoformat(old_snapshot['snapshot_date']).date()
        new_date = datetime.fromisoformat(new_snapshot['snapshot_date']).date()
        
        # Parse asset compositions
        old_assets = self._parse_assets(old_snapshot.get('assets', []))
        new_assets = self._parse_assets(new_snapshot.get('assets', []))
        
        old_symbols = set(old_assets.keys())
        new_symbols = set(new_assets.keys())
        
        # Identify changes
        added_symbols = new_symbols - old_symbols
        removed_symbols = old_symbols - new_symbols
        common_symbols = old_symbols & new_symbols
        
        # Create change objects
        assets_added = [
            AssetChange(
                symbol=symbol,
                change_type='added',
                old_weight=None,
                new_weight=new_assets[symbol]['weight'],
                change_date=new_date,
                reason=f"Added in {new_date} snapshot"
            )
            for symbol in added_symbols
        ]
        
        assets_removed = [
            AssetChange(
                symbol=symbol,
                change_type='removed',
                old_weight=old_assets[symbol]['weight'],
                new_weight=None,
                change_date=new_date,
                reason=f"Removed in {new_date} snapshot"
            )
            for symbol in removed_symbols
        ]
        
        # Check for weight changes in common assets
        assets_weight_changed = []
        assets_unchanged = []
        
        for symbol in common_symbols:
            old_weight = old_assets[symbol]['weight'] or 0.0
            new_weight = new_assets[symbol]['weight'] or 0.0
            
            # Consider significant if weight change > 1%
            if abs(new_weight - old_weight) > 0.01:
                assets_weight_changed.append(
                    AssetChange(
                        symbol=symbol,
                        change_type='weight_changed',
                        old_weight=old_weight,
                        new_weight=new_weight,
                        change_date=new_date,
                        reason=f"Weight changed from {old_weight:.2%} to {new_weight:.2%}"
                    )
                )
            else:
                assets_unchanged.append(
                    AssetChange(
                        symbol=symbol,
                        change_type='unchanged',
                        old_weight=old_weight,
                        new_weight=new_weight,
                        change_date=new_date
                    )
                )
        
        # Calculate aggregate metrics
        all_symbols = old_symbols.union(new_symbols)
        turnover_rate = len(old_symbols.symmetric_difference(new_symbols)) / len(all_symbols) if all_symbols else 0.0
        composition_stability = 1.0 - turnover_rate
        
        # Calculate weight drift
        weight_drift = sum(
            abs((change.new_weight or 0) - (change.old_weight or 0))
            for change in assets_weight_changed
        )
        
        # Analyze sector changes
        sector_changes = self._analyze_sector_changes(old_assets, new_assets)
        
        # Calculate change acceleration if we have previous analysis
        change_acceleration = None
        stability_trend = 'stable'
        
        if universe_id in self.change_history and self.change_history[universe_id]:
            previous_analysis = self.change_history[universe_id][-1]
            change_acceleration = turnover_rate - previous_analysis.turnover_rate
            
            # Determine trend
            if change_acceleration > 0.05:  # 5% increase in turnover
                stability_trend = 'degrading'
            elif change_acceleration < -0.05:  # 5% decrease in turnover
                stability_trend = 'improving'
        
        # Create analysis object
        analysis = ChangeAnalysis(
            comparison_date=new_date,
            previous_date=old_date,
            assets_added=assets_added,
            assets_removed=assets_removed,
            assets_weight_changed=assets_weight_changed,
            assets_unchanged=assets_unchanged,
            turnover_rate=turnover_rate,
            composition_stability=composition_stability,
            weight_drift=weight_drift,
            sector_changes=sector_changes,
            change_acceleration=change_acceleration,
            stability_trend=stability_trend
        )
        
        # Store in history
        self.change_history[universe_id].append(analysis)
        
        return analysis
    
    def calculate_turnover_metrics(
        self,
        universe_id: str,
        snapshots: List[Dict[str, Any]],
        analysis_period: str = "custom"
    ) -> TurnoverMetrics:
        """
        Calculate comprehensive turnover metrics from a series of snapshots.
        
        Args:
            universe_id: UUID of the universe
            snapshots: List of snapshot dictionaries
            analysis_period: Description of the analysis period
            
        Returns:
            TurnoverMetrics with comprehensive analysis
        """
        if len(snapshots) < 2:
            raise ValueError("Need at least 2 snapshots for turnover analysis")
        
        # Sort snapshots by date
        snapshots = sorted(snapshots, key=lambda x: x['snapshot_date'])
        
        start_date = datetime.fromisoformat(snapshots[0]['snapshot_date']).date()
        end_date = datetime.fromisoformat(snapshots[-1]['snapshot_date']).date()
        
        # Calculate period turnovers
        period_turnovers = []
        all_assets_by_period = []
        
        for i in range(1, len(snapshots)):
            # Track changes between consecutive snapshots
            analysis = self.track_universe_changes(
                universe_id + "_temp",  # Temporary ID to avoid polluting history
                snapshots[i-1],
                snapshots[i]
            )
            period_turnovers.append(analysis.turnover_rate)
            
            # Collect asset sets for stability analysis
            assets = self._parse_assets(snapshots[i].get('assets', []))
            all_assets_by_period.append(set(assets.keys()))
        
        # Basic statistics
        average_turnover = statistics.mean(period_turnovers) if period_turnovers else 0.0
        turnover_volatility = statistics.stdev(period_turnovers) if len(period_turnovers) > 1 else 0.0
        min_turnover = min(period_turnovers) if period_turnovers else 0.0
        max_turnover = max(period_turnovers) if period_turnovers else 0.0
        
        # Trend analysis
        turnover_trend, trend_strength = self._analyze_turnover_trend(period_turnovers)
        
        # Asset stability analysis
        core_assets, volatile_assets = self._analyze_asset_stability(all_assets_by_period)
        stability_score = len(core_assets) / len(set().union(*all_assets_by_period)) if all_assets_by_period else 0.0
        
        # Frequency analysis
        rebalance_frequency = self._calculate_rebalance_frequency(period_turnovers)
        change_seasonality = self._analyze_change_seasonality(snapshots, period_turnovers)
        
        return TurnoverMetrics(
            analysis_period=analysis_period,
            start_date=start_date,
            end_date=end_date,
            period_turnovers=period_turnovers,
            average_turnover=average_turnover,
            turnover_volatility=turnover_volatility,
            min_turnover=min_turnover,
            max_turnover=max_turnover,
            turnover_trend=turnover_trend,
            trend_strength=trend_strength,
            core_assets=core_assets,
            volatile_assets=volatile_assets,
            stability_score=stability_score,
            rebalance_frequency=rebalance_frequency,
            change_seasonality=change_seasonality
        )
    
    def get_asset_lifecycle(
        self,
        universe_id: str,
        symbol: str
    ) -> Dict[str, Any]:
        """
        Get lifecycle information for a specific asset in a universe.
        
        Args:
            universe_id: UUID of the universe
            symbol: Asset symbol to analyze
            
        Returns:
            Dictionary with asset lifecycle information
        """
        if universe_id not in self.change_history:
            return {"error": "No tracking history for this universe"}
        
        lifecycle_events = []
        presence_periods = []
        weight_history = []
        
        current_period_start = None
        
        for analysis in self.change_history[universe_id]:
            # Check if asset was added
            for change in analysis.assets_added:
                if change.symbol == symbol:
                    lifecycle_events.append({
                        "event": "added",
                        "date": analysis.comparison_date.isoformat(),
                        "weight": change.new_weight,
                        "reason": change.reason
                    })
                    current_period_start = analysis.comparison_date
            
            # Check if asset was removed
            for change in analysis.assets_removed:
                if change.symbol == symbol:
                    lifecycle_events.append({
                        "event": "removed",
                        "date": analysis.comparison_date.isoformat(),
                        "weight": change.old_weight,
                        "reason": change.reason
                    })
                    if current_period_start:
                        presence_periods.append({
                            "start": current_period_start.isoformat(),
                            "end": analysis.comparison_date.isoformat(),
                            "duration_days": (analysis.comparison_date - current_period_start).days
                        })
                        current_period_start = None
            
            # Track weight changes
            for change in analysis.assets_weight_changed:
                if change.symbol == symbol:
                    weight_history.append({
                        "date": analysis.comparison_date.isoformat(),
                        "old_weight": change.old_weight,
                        "new_weight": change.new_weight,
                        "change": (change.new_weight or 0) - (change.old_weight or 0)
                    })
            
            # Track unchanged periods
            for change in analysis.assets_unchanged:
                if change.symbol == symbol:
                    weight_history.append({
                        "date": analysis.comparison_date.isoformat(),
                        "weight": change.new_weight,
                        "stable": True
                    })
        
        # Calculate summary statistics
        total_presence_days = sum(period["duration_days"] for period in presence_periods)
        average_weight = statistics.mean([w["weight"] if "weight" in w else w["new_weight"] 
                                        for w in weight_history if w.get("weight") or w.get("new_weight")]) if weight_history else 0.0
        
        return {
            "symbol": symbol,
            "universe_id": universe_id,
            "lifecycle_events": lifecycle_events,
            "presence_periods": presence_periods,
            "weight_history": weight_history,
            "summary": {
                "total_presence_days": total_presence_days,
                "number_of_additions": sum(1 for e in lifecycle_events if e["event"] == "added"),
                "number_of_removals": sum(1 for e in lifecycle_events if e["event"] == "removed"),
                "average_weight": average_weight,
                "currently_present": current_period_start is not None,
                "stability_rating": "high" if len(presence_periods) <= 1 and total_presence_days > 180 else "low"
            }
        }
    
    def _parse_assets(self, assets_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Parse assets data into symbol-keyed dictionary"""
        return {
            asset['symbol']: {
                'weight': asset.get('weight', 0.0),
                'sector': asset.get('sector', 'Unknown'),
                'name': asset.get('name', asset['symbol'])
            }
            for asset in assets_data
        }
    
    def _analyze_sector_changes(
        self,
        old_assets: Dict[str, Dict[str, Any]], 
        new_assets: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze changes by sector"""
        sector_changes = defaultdict(lambda: {
            'added': [], 'removed': [], 'weight_change': 0.0
        })
        
        # Track sector changes
        for symbol, data in old_assets.items():
            sector = data['sector']
            if symbol not in new_assets:
                sector_changes[sector]['removed'].append(symbol)
            else:
                weight_change = (new_assets[symbol]['weight'] or 0) - (data['weight'] or 0)
                sector_changes[sector]['weight_change'] += weight_change
        
        for symbol, data in new_assets.items():
            sector = data['sector']
            if symbol not in old_assets:
                sector_changes[sector]['added'].append(symbol)
        
        return dict(sector_changes)
    
    def _analyze_turnover_trend(self, turnovers: List[float]) -> Tuple[str, float]:
        """Analyze turnover trend and calculate trend strength"""
        if len(turnovers) < 3:
            return "stable", 0.0
        
        # Simple linear trend analysis
        x_values = list(range(len(turnovers)))
        
        # Calculate correlation coefficient as trend strength
        n = len(turnovers)
        sum_x = sum(x_values)
        sum_y = sum(turnovers)
        sum_xy = sum(x * y for x, y in zip(x_values, turnovers))
        sum_xx = sum(x * x for x in x_values)
        sum_yy = sum(y * y for y in turnovers)
        
        correlation = (n * sum_xy - sum_x * sum_y) / (
            ((n * sum_xx - sum_x * sum_x) * (n * sum_yy - sum_y * sum_y)) ** 0.5
        )
        
        trend_strength = abs(correlation)
        
        # Determine trend direction
        if correlation > 0.3:
            trend = "increasing"
        elif correlation < -0.3:
            trend = "decreasing"
        elif trend_strength < 0.1:
            trend = "stable"
        else:
            trend = "volatile"
        
        return trend, trend_strength
    
    def _analyze_asset_stability(
        self, 
        asset_sets_by_period: List[Set[str]]
    ) -> Tuple[List[str], List[str]]:
        """Analyze asset stability across periods"""
        if not asset_sets_by_period:
            return [], []
        
        # Count appearances of each asset
        asset_counts = defaultdict(int)
        for asset_set in asset_sets_by_period:
            for asset in asset_set:
                asset_counts[asset] += 1
        
        total_periods = len(asset_sets_by_period)
        core_threshold = 0.8 * total_periods
        volatile_threshold = 0.3 * total_periods
        
        core_assets = [
            asset for asset, count in asset_counts.items()
            if count >= core_threshold
        ]
        
        volatile_assets = [
            asset for asset, count in asset_counts.items()
            if count <= volatile_threshold
        ]
        
        return core_assets, volatile_assets
    
    def _calculate_rebalance_frequency(self, turnovers: List[float]) -> float:
        """Calculate average frequency of significant rebalances"""
        if not turnovers:
            return 0.0
        
        # Define significant rebalance as turnover > 10%
        significant_rebalances = [i for i, turnover in enumerate(turnovers) if turnover > 0.1]
        
        if len(significant_rebalances) < 2:
            return float(len(turnovers))  # No pattern, return total periods
        
        # Calculate average periods between significant rebalances
        intervals = [
            significant_rebalances[i] - significant_rebalances[i-1]
            for i in range(1, len(significant_rebalances))
        ]
        
        return statistics.mean(intervals) if intervals else float(len(turnovers))
    
    def _analyze_change_seasonality(
        self, 
        snapshots: List[Dict[str, Any]], 
        turnovers: List[float]
    ) -> Dict[str, float]:
        """Analyze seasonal patterns in universe changes"""
        monthly_turnovers = defaultdict(list)
        
        for i, turnover in enumerate(turnovers):
            # Get month from snapshot (turnovers[i] corresponds to changes in snapshots[i+1])
            snapshot_date = datetime.fromisoformat(snapshots[i+1]['snapshot_date'])
            month = snapshot_date.month
            monthly_turnovers[month].append(turnover)
        
        # Calculate average turnover by month
        monthly_averages = {
            month: statistics.mean(turnovers_list)
            for month, turnovers_list in monthly_turnovers.items()
            if turnovers_list
        }
        
        return monthly_averages