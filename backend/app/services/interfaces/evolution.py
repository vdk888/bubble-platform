"""
Evolution Module Interfaces - Interface-First Design Implementation
Following planning document standards for clean architecture and testability.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass

from .base import ServiceResult


class IUniverseScheduler(ABC):
    """Interface for universe update scheduling and automation"""
    
    @abstractmethod
    async def schedule_monthly_updates(
        self,
        universe_id: str,
        start_date: date,
        execution_time: str = "09:00",
        end_date: Optional[date] = None,
        timezone_name: str = "UTC"
    ) -> ServiceResult[Dict[str, Any]]:
        """Schedule monthly universe updates"""
        pass
    
    @abstractmethod
    async def schedule_quarterly_updates(
        self,
        universe_id: str,
        start_date: date,
        execution_time: str = "09:00", 
        end_date: Optional[date] = None,
        timezone_name: str = "UTC"
    ) -> ServiceResult[Dict[str, Any]]:
        """Schedule quarterly universe updates"""
        pass
    
    @abstractmethod
    async def get_due_schedules(
        self,
        check_time: Optional[datetime] = None
    ) -> ServiceResult[List[Dict[str, Any]]]:
        """Get schedules that are due for execution"""
        pass
    
    @abstractmethod
    async def record_execution(
        self,
        schedule_id: str,
        planned_date: datetime,
        actual_date: datetime,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> ServiceResult[Dict[str, Any]]:
        """Record schedule execution results"""
        pass


class IUniverseTracker(ABC):
    """Interface for universe change tracking and analysis"""
    
    @abstractmethod
    async def track_universe_changes(
        self,
        universe_id: str,
        old_snapshot: Dict[str, Any],
        new_snapshot: Dict[str, Any]
    ) -> ServiceResult[Dict[str, Any]]:
        """Track and analyze changes between universe snapshots"""
        pass
    
    @abstractmethod
    async def calculate_turnover_metrics(
        self,
        universe_id: str,
        snapshots: List[Dict[str, Any]],
        analysis_period: str = "custom"
    ) -> ServiceResult[Dict[str, Any]]:
        """Calculate comprehensive turnover metrics from snapshots"""
        pass
    
    @abstractmethod
    async def get_asset_lifecycle(
        self,
        universe_id: str,
        symbol: str
    ) -> ServiceResult[Dict[str, Any]]:
        """Get lifecycle information for a specific asset"""
        pass


class ITransitionManager(ABC):
    """Interface for managing gradual universe transitions"""
    
    @abstractmethod
    async def manage_gradual_transition(
        self,
        universe_id: str,
        old_composition: Dict[str, float],
        new_composition: Dict[str, float],
        strategy: str = "gradual",
        rules: Optional[Dict[str, Any]] = None,
        start_date: Optional[date] = None
    ) -> ServiceResult[Dict[str, Any]]:
        """Create and manage gradual transition between compositions"""
        pass
    
    @abstractmethod
    async def execute_transition_step(
        self,
        plan_id: str,
        step_id: str,
        actual_cost: Optional[float] = None,
        notes: Optional[str] = None
    ) -> ServiceResult[Dict[str, Any]]:
        """Execute a specific transition step"""
        pass
    
    @abstractmethod
    async def get_transition_status(
        self,
        plan_id: str
    ) -> ServiceResult[Optional[Dict[str, Any]]]:
        """Get current status of a transition plan"""
        pass


class IImpactAnalyzer(ABC):
    """Interface for analyzing rebalance impacts"""
    
    @abstractmethod
    async def analyze_rebalance_impact(
        self,
        universe_id: str,
        old_composition: Dict[str, float],
        new_composition: Dict[str, float],
        portfolio_value: float = 1000000.0,
        transaction_costs: Optional[Dict[str, Dict[str, float]]] = None
    ) -> ServiceResult[Dict[str, Any]]:
        """Perform comprehensive rebalance impact analysis"""
        pass
    
    @abstractmethod
    async def compare_rebalance_scenarios(
        self,
        universe_id: str,
        current_composition: Dict[str, float],
        scenarios: List[Dict[str, Any]]
    ) -> ServiceResult[Dict[str, Any]]:
        """Compare multiple rebalancing scenarios"""
        pass


class IEvolutionOrchestrator(ABC):
    """High-level interface for orchestrating evolution operations"""
    
    @abstractmethod
    async def setup_universe_monitoring(
        self,
        universe_id: str,
        monitoring_frequency: str = "monthly",
        start_date: Optional[date] = None
    ) -> ServiceResult[Dict[str, Any]]:
        """Set up comprehensive universe monitoring"""
        pass
    
    @abstractmethod
    async def execute_smart_rebalance(
        self,
        universe_id: str,
        target_composition: Dict[str, float],
        analysis_options: Optional[Dict[str, Any]] = None
    ) -> ServiceResult[Dict[str, Any]]:
        """Execute intelligent rebalancing with impact analysis"""
        pass
    
    @abstractmethod
    async def get_evolution_dashboard(
        self,
        universe_id: str,
        period_days: int = 90
    ) -> ServiceResult[Dict[str, Any]]:
        """Get comprehensive evolution dashboard data"""
        pass