"""
Test suite for evolution module components.
Part C: Service Layer Updates - Sprint 2.5 Evolution Module
"""
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from app.services.evolution.scheduler import (
    UniverseScheduler, Schedule, ScheduleFrequency, ScheduleStatus, ScheduleExecution
)
from app.services.evolution.tracker import (
    UniverseTracker, ChangeAnalysis, TurnoverMetrics, AssetChange
)
from app.services.evolution.transition_manager import (
    TransitionManager, TransitionPlan, TransitionStrategy, TransitionRule, TransitionStatus
)
from app.services.evolution.impact_analyzer import (
    ImpactAnalyzer, ImpactAnalysis, TransactionCost, RiskImpact, PerformanceImpact, ImpactSeverity
)


class TestUniverseScheduler:
    """Test UniverseScheduler functionality"""
    
    def test_schedule_monthly_updates(self):
        """Test creating monthly update schedule"""
        scheduler = UniverseScheduler()
        
        schedule = scheduler.schedule_monthly_updates(
            universe_id='test-universe-123',
            start_date=date(2024, 6, 30),
            execution_time='09:00',
            end_date=date(2025, 6, 30)
        )
        
        assert schedule.universe_id == 'test-universe-123'
        assert schedule.frequency == ScheduleFrequency.MONTHLY
        assert schedule.status == ScheduleStatus.ACTIVE
        assert schedule.execution_time == '09:00'
        assert schedule.start_date == date(2024, 6, 30)
        assert schedule.end_date == date(2025, 6, 30)
        
        # Test next execution calculation
        next_execution = schedule.get_next_execution_date()
        assert next_execution is not None
        
        # Test schedule storage
        assert schedule.id in scheduler.schedules
        assert scheduler.get_schedule(schedule.id) == schedule
    
    def test_schedule_quarterly_updates(self):
        """Test creating quarterly update schedule"""
        scheduler = UniverseScheduler()
        
        schedule = scheduler.schedule_quarterly_updates(
            universe_id='test-universe-456',
            start_date=date(2024, 3, 31),
            execution_time='10:30',
            timezone_name='EST'
        )
        
        assert schedule.frequency == ScheduleFrequency.QUARTERLY
        assert schedule.execution_time == '10:30'
        assert schedule.timezone_name == 'EST'
        
        # Test quarterly next execution calculation
        next_execution = schedule.get_next_execution_date()
        assert next_execution is not None
    
    def test_custom_schedule_creation(self):
        """Test creating custom schedule"""
        scheduler = UniverseScheduler()
        
        schedule = scheduler.create_custom_schedule(
            universe_id='test-universe-789',
            frequency=ScheduleFrequency.WEEKLY,
            start_date=date(2024, 6, 1),
            execution_time='14:00',
            metadata={'custom_field': 'custom_value'}
        )
        
        assert schedule.frequency == ScheduleFrequency.WEEKLY
        assert schedule.metadata['custom_field'] == 'custom_value'
    
    def test_get_due_schedules(self):
        """Test retrieving schedules due for execution"""
        scheduler = UniverseScheduler()
        
        # Create schedule that should be due
        past_schedule = scheduler.create_custom_schedule(
            universe_id='past-universe',
            frequency=ScheduleFrequency.DAILY,
            start_date=date.today() - timedelta(days=1),
            execution_time='09:00'
        )
        
        # Create schedule that shouldn't be due yet
        future_schedule = scheduler.create_custom_schedule(
            universe_id='future-universe',
            frequency=ScheduleFrequency.DAILY,
            start_date=date.today() + timedelta(days=10),
            execution_time='09:00'
        )
        
        # Test getting due schedules
        check_time = datetime.now().replace(hour=10, minute=0)  # After 9 AM
        due_schedules = scheduler.get_due_schedules(check_time)
        
        # Should include past schedule, not future schedule
        due_ids = [s.id for s in due_schedules]
        assert past_schedule.id in due_ids
        assert future_schedule.id not in due_ids
    
    def test_record_execution(self):
        """Test recording schedule execution"""
        scheduler = UniverseScheduler()
        
        schedule = scheduler.schedule_monthly_updates(
            universe_id='test-universe',
            start_date=date(2024, 6, 30)
        )
        
        # Record successful execution
        planned_time = datetime(2024, 7, 31, 9, 0)
        actual_time = datetime(2024, 7, 31, 9, 5)
        
        execution = scheduler.record_execution(
            schedule_id=schedule.id,
            planned_date=planned_time,
            actual_date=actual_time,
            status=ScheduleStatus.COMPLETED,
            result={'snapshots_created': 1, 'assets_updated': 10}
        )
        
        assert execution.schedule_id == schedule.id
        assert execution.status == ScheduleStatus.COMPLETED
        assert execution.result['snapshots_created'] == 1
        
        # Verify execution is stored in schedule
        assert len(schedule.executions) == 1
        assert schedule.executions[0] == execution
    
    def test_schedule_management(self):
        """Test schedule pause, resume, and delete operations"""
        scheduler = UniverseScheduler()
        
        schedule = scheduler.schedule_monthly_updates(
            universe_id='test-universe',
            start_date=date(2024, 6, 30)
        )
        
        schedule_id = schedule.id
        
        # Test pause
        assert scheduler.pause_schedule(schedule_id) is True
        assert schedule.status == ScheduleStatus.PAUSED
        
        # Test resume
        assert scheduler.resume_schedule(schedule_id) is True
        assert schedule.status == ScheduleStatus.ACTIVE
        
        # Test delete
        assert scheduler.delete_schedule(schedule_id) is True
        assert scheduler.get_schedule(schedule_id) is None
        assert schedule_id not in scheduler.schedules
    
    def test_schedule_statistics(self):
        """Test schedule statistics calculation"""
        scheduler = UniverseScheduler()
        
        schedule = scheduler.schedule_monthly_updates(
            universe_id='test-universe',
            start_date=date(2024, 6, 30)
        )
        
        # Add some execution history
        planned_time = datetime(2024, 7, 31, 9, 0)
        actual_time_early = datetime(2024, 7, 31, 8, 55)  # 5 minutes early
        actual_time_late = datetime(2024, 8, 31, 9, 10)   # 10 minutes late
        
        scheduler.record_execution(
            schedule_id=schedule.id,
            planned_date=planned_time,
            actual_date=actual_time_early,
            status=ScheduleStatus.COMPLETED
        )
        
        scheduler.record_execution(
            schedule_id=schedule.id,
            planned_date=planned_time + timedelta(days=31),
            actual_date=actual_time_late,
            status=ScheduleStatus.COMPLETED
        )
        
        # Failed execution
        scheduler.record_execution(
            schedule_id=schedule.id,
            planned_date=planned_time + timedelta(days=62),
            actual_date=actual_time_late + timedelta(days=31),
            status=ScheduleStatus.FAILED
        )
        
        # Get statistics
        stats = scheduler.get_schedule_statistics(schedule.id)
        
        assert stats['total_executions'] == 3
        assert stats['successful_executions'] == 2
        assert stats['failed_executions'] == 1
        assert stats['success_rate'] == 2/3
        assert 'average_delay_seconds' in stats
        assert 'last_execution' in stats


class TestUniverseTracker:
    """Test UniverseTracker functionality"""
    
    def test_track_universe_changes_basic(self):
        """Test basic universe change tracking"""
        tracker = UniverseTracker()
        
        old_snapshot = {
            'snapshot_date': '2024-06-30',
            'assets': [
                {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.30, 'sector': 'Technology'},
                {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.25, 'sector': 'Technology'},
                {'symbol': 'GOOGL', 'name': 'Alphabet Inc', 'weight': 0.25, 'sector': 'Technology'},
                {'symbol': 'AMZN', 'name': 'Amazon.com Inc', 'weight': 0.20, 'sector': 'Technology'}
            ]
        }
        
        new_snapshot = {
            'snapshot_date': '2024-09-30',
            'assets': [
                {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.28, 'sector': 'Technology'},
                {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.27, 'sector': 'Technology'},
                {'symbol': 'NVDA', 'name': 'NVIDIA Corp', 'weight': 0.25, 'sector': 'Technology'},
                {'symbol': 'TSLA', 'name': 'Tesla Inc', 'weight': 0.20, 'sector': 'Technology'}
            ]
        }
        
        analysis = tracker.track_universe_changes(
            'test-universe',
            old_snapshot,
            new_snapshot
        )
        
        assert isinstance(analysis, ChangeAnalysis)
        assert analysis.comparison_date == date(2024, 9, 30)
        assert analysis.previous_date == date(2024, 6, 30)
        
        # Check changes
        assert len(analysis.assets_added) == 2  # NVDA, TSLA
        assert len(analysis.assets_removed) == 2  # GOOGL, AMZN
        assert len(analysis.assets_weight_changed) == 2  # AAPL, MSFT (weight changes)
        assert len(analysis.assets_unchanged) == 0  # No unchanged (all weights changed)
        
        # Check symbols
        added_symbols = [change.symbol for change in analysis.assets_added]
        removed_symbols = [change.symbol for change in analysis.assets_removed]
        
        assert 'NVDA' in added_symbols
        assert 'TSLA' in added_symbols
        assert 'GOOGL' in removed_symbols
        assert 'AMZN' in removed_symbols
        
        # Check turnover calculation
        assert analysis.turnover_rate > 0.0
        assert analysis.composition_stability < 1.0
    
    def test_track_universe_changes_weight_only(self):
        """Test tracking changes that are weight-only (no additions/removals)"""
        tracker = UniverseTracker()
        
        old_snapshot = {
            'snapshot_date': '2024-06-30',
            'assets': [
                {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.50, 'sector': 'Technology'},
                {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.50, 'sector': 'Technology'}
            ]
        }
        
        new_snapshot = {
            'snapshot_date': '2024-09-30',
            'assets': [
                {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.60, 'sector': 'Technology'},
                {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.40, 'sector': 'Technology'}
            ]
        }
        
        analysis = tracker.track_universe_changes(
            'test-universe',
            old_snapshot,
            new_snapshot
        )
        
        # Should be no additions/removals, only weight changes
        assert len(analysis.assets_added) == 0
        assert len(analysis.assets_removed) == 0
        assert len(analysis.assets_weight_changed) == 2
        assert analysis.turnover_rate == 0.0  # No symbol changes
        assert analysis.weight_drift > 0.0  # But weight drift should be positive
    
    def test_calculate_turnover_metrics(self):
        """Test comprehensive turnover metrics calculation"""
        tracker = UniverseTracker()
        
        # Create series of snapshots showing evolution
        snapshots = [
            {
                'snapshot_date': '2024-01-31',
                'assets': [
                    {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.25},
                    {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.25},
                    {'symbol': 'GOOGL', 'name': 'Alphabet Inc', 'weight': 0.25},
                    {'symbol': 'AMZN', 'name': 'Amazon.com Inc', 'weight': 0.25}
                ]
            },
            {
                'snapshot_date': '2024-02-29',
                'assets': [
                    {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.25},
                    {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.25},
                    {'symbol': 'GOOGL', 'name': 'Alphabet Inc', 'weight': 0.25},
                    {'symbol': 'NVDA', 'name': 'NVIDIA Corp', 'weight': 0.25}  # AMZN -> NVDA
                ]
            },
            {
                'snapshot_date': '2024-03-31',
                'assets': [
                    {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.25},
                    {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.25},
                    {'symbol': 'NVDA', 'name': 'NVIDIA Corp', 'weight': 0.25},
                    {'symbol': 'TSLA', 'name': 'Tesla Inc', 'weight': 0.25}  # GOOGL -> TSLA
                ]
            }
        ]
        
        metrics = tracker.calculate_turnover_metrics(
            'test-universe',
            snapshots,
            'test-period'
        )
        
        assert isinstance(metrics, TurnoverMetrics)
        assert metrics.analysis_period == 'test-period'
        assert len(metrics.period_turnovers) == 2  # 3 snapshots = 2 transitions
        assert metrics.average_turnover > 0.0
        
        # Check stability analysis
        assert 'AAPL' in metrics.core_assets  # Present in all periods
        assert 'MSFT' in metrics.core_assets  # Present in all periods
        assert len(metrics.volatile_assets) > 0  # AMZN, GOOGL should be volatile
    
    def test_get_asset_lifecycle(self):
        """Test asset lifecycle tracking"""
        tracker = UniverseTracker()
        
        # Create some change history first
        old_snapshot = {
            'snapshot_date': '2024-06-30',
            'assets': [{'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.50}]
        }
        
        new_snapshot = {
            'snapshot_date': '2024-09-30',
            'assets': [{'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 1.0}]  # AAPL removed
        }
        
        # Track changes to build history
        tracker.track_universe_changes('test-universe', old_snapshot, new_snapshot)
        
        # Get lifecycle for AAPL (should show removal)
        lifecycle = tracker.get_asset_lifecycle('test-universe', 'AAPL')
        
        assert lifecycle['symbol'] == 'AAPL'
        assert lifecycle['universe_id'] == 'test-universe'
        assert len(lifecycle['lifecycle_events']) > 0
        
        # Should have removal event
        events = lifecycle['lifecycle_events']
        removal_events = [e for e in events if e['event'] == 'removed']
        assert len(removal_events) > 0
    
    def test_sector_analysis(self):
        """Test sector change analysis"""
        tracker = UniverseTracker()
        
        old_snapshot = {
            'snapshot_date': '2024-06-30',
            'assets': [
                {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.50, 'sector': 'Technology'},
                {'symbol': 'JPM', 'name': 'JPMorgan Chase', 'weight': 0.50, 'sector': 'Financial'}
            ]
        }
        
        new_snapshot = {
            'snapshot_date': '2024-09-30',
            'assets': [
                {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.33, 'sector': 'Technology'},
                {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.33, 'sector': 'Technology'},
                {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'weight': 0.34, 'sector': 'Healthcare'}
            ]
        }
        
        analysis = tracker.track_universe_changes('test-universe', old_snapshot, new_snapshot)
        
        # Check sector changes
        assert 'Technology' in analysis.sector_changes
        assert 'Financial' in analysis.sector_changes
        assert 'Healthcare' in analysis.sector_changes
        
        # Technology sector should have additions
        tech_changes = analysis.sector_changes['Technology']
        assert 'MSFT' in tech_changes['added']
        
        # Financial sector should have removals
        financial_changes = analysis.sector_changes['Financial']
        assert 'JPM' in financial_changes['removed']


class TestTransitionManager:
    """Test TransitionManager functionality"""
    
    def test_manage_gradual_transition_basic(self):
        """Test basic gradual transition planning"""
        manager = TransitionManager()
        
        old_composition = {
            'AAPL': 0.30,
            'MSFT': 0.25,
            'GOOGL': 0.25,
            'AMZN': 0.20
        }
        
        new_composition = {
            'AAPL': 0.28,
            'MSFT': 0.27,
            'NVDA': 0.25,
            'TSLA': 0.20
        }
        
        rules = TransitionRule(
            max_daily_turnover=0.05,
            max_single_position_change=0.02
        )
        
        plan = manager.manage_gradual_transition(
            universe_id='test-universe',
            old_composition=old_composition,
            new_composition=new_composition,
            strategy=TransitionStrategy.GRADUAL,
            rules=rules
        )
        
        assert isinstance(plan, TransitionPlan)
        assert plan.universe_id == 'test-universe'
        assert plan.strategy == TransitionStrategy.GRADUAL
        assert plan.status == TransitionStatus.PENDING
        assert len(plan.steps) > 0
        assert plan.total_expected_cost > 0.0
    
    def test_immediate_transition_strategy(self):
        """Test immediate transition strategy"""
        manager = TransitionManager()
        
        old_composition = {'AAPL': 0.50, 'MSFT': 0.50}
        new_composition = {'GOOGL': 0.50, 'AMZN': 0.50}
        
        plan = manager.manage_gradual_transition(
            universe_id='test-universe',
            old_composition=old_composition,
            new_composition=new_composition,
            strategy=TransitionStrategy.IMMEDIATE
        )
        
        # Immediate strategy should create only one step
        assert len(plan.steps) == 1
        assert plan.steps[0].step_number == 1
        assert plan.expected_completion_date == plan.start_date
    
    def test_execute_transition_step(self):
        """Test executing transition steps"""
        manager = TransitionManager()
        
        old_composition = {'AAPL': 1.0}
        new_composition = {'MSFT': 1.0}
        
        plan = manager.manage_gradual_transition(
            universe_id='test-universe',
            old_composition=old_composition,
            new_composition=new_composition,
            strategy=TransitionStrategy.IMMEDIATE
        )
        
        step_id = plan.steps[0].id
        
        # Execute the step
        result = manager.execute_transition_step(
            plan_id=plan.id,
            step_id=step_id,
            actual_cost=150.0,
            notes="Executed successfully"
        )
        
        assert result['success'] is True
        assert result['step_executed']['status'] == 'completed'
        assert result['step_executed']['actual_cost'] == 150.0
        assert result['plan_progress'] == 100.0  # Should be 100% complete
        assert result['plan_status'] == 'completed'
    
    def test_transition_status_tracking(self):
        """Test transition status and progress tracking"""
        manager = TransitionManager()
        
        old_composition = {'AAPL': 0.50, 'MSFT': 0.50}
        new_composition = {'GOOGL': 0.50, 'AMZN': 0.50}
        
        rules = TransitionRule(max_daily_turnover=0.01)  # Very small to create multiple steps
        
        plan = manager.manage_gradual_transition(
            universe_id='test-universe',
            old_composition=old_composition,
            new_composition=new_composition,
            strategy=TransitionStrategy.GRADUAL,
            rules=rules
        )
        
        # Get initial status
        status = manager.get_transition_status(plan.id)
        assert status is not None
        assert status['plan']['status'] == 'pending'
        assert status['plan']['progress_percentage'] == 0.0
        
        # Execute first step if available
        ready_steps = status['ready_steps']
        if ready_steps:
            first_step_id = ready_steps[0]['id']
            manager.execute_transition_step(plan.id, first_step_id)
            
            # Check progress update
            updated_status = manager.get_transition_status(plan.id)
            assert updated_status['plan']['progress_percentage'] > 0.0
    
    def test_transition_management_operations(self):
        """Test pause, resume, cancel operations"""
        manager = TransitionManager()
        
        old_composition = {'AAPL': 1.0}
        new_composition = {'MSFT': 1.0}
        
        plan = manager.manage_gradual_transition(
            universe_id='test-universe',
            old_composition=old_composition,
            new_composition=new_composition
        )
        
        plan_id = plan.id
        
        # Test pause
        assert manager.pause_transition(plan_id) is True
        assert plan.status == TransitionStatus.PAUSED
        
        # Test resume
        assert manager.resume_transition(plan_id) is True
        assert plan.status == TransitionStatus.IN_PROGRESS
        
        # Test cancel
        assert manager.cancel_transition(plan_id) is True
        assert plan.status == TransitionStatus.CANCELLED
        assert plan_id not in manager.active_transitions
        assert plan_id in manager.completed_transitions


class TestImpactAnalyzer:
    """Test ImpactAnalyzer functionality"""
    
    def test_analyze_rebalance_impact_basic(self):
        """Test basic rebalance impact analysis"""
        analyzer = ImpactAnalyzer()
        
        old_composition = {
            'AAPL': 0.30,
            'MSFT': 0.25,
            'GOOGL': 0.25,
            'AMZN': 0.20
        }
        
        new_composition = {
            'AAPL': 0.28,
            'MSFT': 0.27,
            'NVDA': 0.25,
            'TSLA': 0.20
        }
        
        analysis = analyzer.analyze_rebalance_impact(
            universe_id='test-universe',
            old_composition=old_composition,
            new_composition=new_composition,
            portfolio_value=1000000.0
        )
        
        assert isinstance(analysis, ImpactAnalysis)
        assert analysis.universe_id == 'test-universe'
        assert analysis.turnover_rate > 0.0
        assert analysis.total_transaction_cost > 0.0
        assert len(analysis.transaction_costs) > 0
        assert analysis.analysis_confidence > 0.0
        
        # Check that we have transaction costs for changed positions
        symbols_with_costs = [cost.symbol for cost in analysis.transaction_costs]
        assert 'GOOGL' in symbols_with_costs  # Should have sell cost
        assert 'AMZN' in symbols_with_costs   # Should have sell cost
        assert 'NVDA' in symbols_with_costs   # Should have buy cost
        assert 'TSLA' in symbols_with_costs   # Should have buy cost
    
    def test_transaction_cost_calculation(self):
        """Test detailed transaction cost calculation"""
        analyzer = ImpactAnalyzer()
        
        old_composition = {'AAPL': 1.0}
        new_composition = {'MSFT': 1.0}
        
        # Test with custom transaction costs
        custom_costs = {
            'AAPL': {'spread': 3.0, 'commission': 1.0, 'market_impact': 2.0},
            'MSFT': {'spread': 4.0, 'commission': 1.5, 'market_impact': 2.5}
        }
        
        analysis = analyzer.analyze_rebalance_impact(
            universe_id='test-universe',
            old_composition=old_composition,
            new_composition=new_composition,
            portfolio_value=1000000.0,
            transaction_costs=custom_costs
        )
        
        # Should have costs for both AAPL (sell) and MSFT (buy)
        assert len(analysis.transaction_costs) == 2
        
        # Find AAPL cost (sell)
        aapl_cost = next(cost for cost in analysis.transaction_costs if cost.symbol == 'AAPL')
        assert aapl_cost.action == 'sell'
        assert aapl_cost.spread_cost == 3.0
        assert aapl_cost.commission_cost == 1.0
        
        # Find MSFT cost (buy)
        msft_cost = next(cost for cost in analysis.transaction_costs if cost.symbol == 'MSFT')
        assert msft_cost.action == 'buy'
        assert msft_cost.spread_cost == 4.0
        assert msft_cost.commission_cost == 1.5
    
    def test_risk_impact_analysis(self):
        """Test risk impact analysis"""
        analyzer = ImpactAnalyzer()
        
        # High concentration -> low concentration (should reduce risk)
        old_composition = {'AAPL': 1.0}  # Very concentrated
        new_composition = {'AAPL': 0.25, 'MSFT': 0.25, 'GOOGL': 0.25, 'AMZN': 0.25}  # Diversified
        
        analysis = analyzer.analyze_rebalance_impact(
            universe_id='test-universe',
            old_composition=old_composition,
            new_composition=new_composition
        )
        
        risk_impact = analysis.risk_impact
        
        assert isinstance(risk_impact, RiskImpact)
        assert risk_impact.pre_rebalance_risk > risk_impact.post_rebalance_risk  # Risk should decrease
        assert risk_impact.risk_change < 0.0  # Negative change = risk reduction
        assert risk_impact.concentration_risk_change < 0.0  # Concentration should decrease
        assert risk_impact.impact_severity in [ImpactSeverity.LOW, ImpactSeverity.MODERATE]
    
    def test_compare_rebalance_scenarios(self):
        """Test scenario comparison functionality"""
        analyzer = ImpactAnalyzer()
        
        current_composition = {'AAPL': 0.50, 'MSFT': 0.50}
        
        scenarios = [
            {
                'name': 'Conservative',
                'composition': {'AAPL': 0.45, 'MSFT': 0.55}  # Small change
            },
            {
                'name': 'Aggressive',
                'composition': {'GOOGL': 0.50, 'AMZN': 0.50}  # Complete change
            },
            {
                'name': 'Moderate',
                'composition': {'AAPL': 0.25, 'MSFT': 0.25, 'GOOGL': 0.25, 'AMZN': 0.25}
            }
        ]
        
        comparison = analyzer.compare_rebalance_scenarios(
            universe_id='test-universe',
            current_composition=current_composition,
            scenarios=scenarios
        )
        
        assert comparison['scenarios_analyzed'] == 3
        assert comparison['best_scenario'] is not None
        assert 'recommendation' in comparison
        
        # Check that scenarios are ranked by score
        scenario_scores = [s['summary_metrics']['overall_score'] for s in comparison['scenario_analyses']]
        assert scenario_scores == sorted(scenario_scores, reverse=True)  # Should be descending
    
    def test_impact_analysis_to_dict(self):
        """Test ImpactAnalysis serialization"""
        analyzer = ImpactAnalyzer()
        
        old_composition = {'AAPL': 0.60, 'MSFT': 0.40}
        new_composition = {'AAPL': 0.40, 'MSFT': 0.60}
        
        analysis = analyzer.analyze_rebalance_impact(
            universe_id='test-universe',
            old_composition=old_composition,
            new_composition=new_composition
        )
        
        data = analysis.to_dict()
        
        # Check structure
        assert 'analysis_metadata' in data
        assert 'rebalance_details' in data
        assert 'cost_analysis' in data
        assert 'risk_analysis' in data
        assert 'performance_analysis' in data
        assert 'summary' in data
        assert 'recommendations' in data
        
        # Check specific fields
        assert data['analysis_metadata']['universe_id'] == 'test-universe'
        assert 'turnover_rate' in data['rebalance_details']
        assert 'total_transaction_cost' in data['cost_analysis']
        assert 'net_expected_benefit' in data['summary']
        
        # Check recommendations exist
        assert 'execution' in data['recommendations']
        assert 'timing' in data['recommendations']
        assert 'risk_mitigation' in data['recommendations']


@pytest.mark.integration
class TestEvolutionModuleIntegration:
    """Integration tests for evolution module components working together"""
    
    def test_scheduler_tracker_integration(self):
        """Test integration between scheduler and tracker"""
        scheduler = UniverseScheduler()
        tracker = UniverseTracker()
        
        # Create schedule
        schedule = scheduler.schedule_monthly_updates(
            universe_id='integration-test',
            start_date=date(2024, 6, 30)
        )
        
        # Simulate execution with tracking
        old_snapshot = {
            'snapshot_date': '2024-06-30',
            'assets': [{'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 1.0}]
        }
        
        new_snapshot = {
            'snapshot_date': '2024-07-31',
            'assets': [{'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 1.0}]
        }
        
        # Track changes
        change_analysis = tracker.track_universe_changes(
            'integration-test',
            old_snapshot,
            new_snapshot
        )
        
        # Record execution with tracking results
        execution_result = {
            'snapshots_created': 1,
            'turnover_rate': change_analysis.turnover_rate,
            'assets_changed': len(change_analysis.assets_added) + len(change_analysis.assets_removed)
        }
        
        execution = scheduler.record_execution(
            schedule_id=schedule.id,
            planned_date=datetime(2024, 7, 31, 9, 0),
            actual_date=datetime(2024, 7, 31, 9, 5),
            status=ScheduleStatus.COMPLETED,
            result=execution_result
        )
        
        # Verify integration
        assert execution.result['turnover_rate'] == change_analysis.turnover_rate
        assert execution.result['assets_changed'] == 2  # 1 added + 1 removed
    
    def test_transition_impact_integration(self):
        """Test integration between transition manager and impact analyzer"""
        transition_manager = TransitionManager()
        impact_analyzer = ImpactAnalyzer()
        
        old_composition = {'AAPL': 0.60, 'MSFT': 0.40}
        new_composition = {'AAPL': 0.40, 'MSFT': 0.40, 'GOOGL': 0.20}
        
        # Analyze impact first
        impact_analysis = impact_analyzer.analyze_rebalance_impact(
            universe_id='integration-test',
            old_composition=old_composition,
            new_composition=new_composition
        )
        
        # Use impact analysis to inform transition rules
        rules = TransitionRule(
            max_daily_turnover=min(0.05, impact_analysis.turnover_rate / 5),  # Spread over 5 days
            max_single_position_change=0.02,
            max_total_cost=impact_analysis.total_transaction_cost * 1.1  # 10% buffer
        )
        
        # Create transition plan
        transition_plan = transition_manager.manage_gradual_transition(
            universe_id='integration-test',
            old_composition=old_composition,
            new_composition=new_composition,
            strategy=TransitionStrategy.COST_OPTIMIZED,
            rules=rules
        )
        
        # Verify integration
        assert transition_plan.total_expected_cost <= rules.max_total_cost
        assert len(transition_plan.steps) > 1  # Should be gradual due to rules
    
    def test_complete_evolution_workflow(self):
        """Test complete evolution workflow with all components"""
        scheduler = UniverseScheduler()
        tracker = UniverseTracker()
        transition_manager = TransitionManager()
        impact_analyzer = ImpactAnalyzer()
        
        # Step 1: Set up monitoring schedule
        schedule = scheduler.schedule_monthly_updates(
            universe_id='workflow-test',
            start_date=date(2024, 6, 30)
        )
        
        # Step 2: Simulate universe evolution over time
        monthly_snapshots = [
            {
                'snapshot_date': '2024-06-30',
                'assets': [
                    {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.50},
                    {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.50}
                ]
            },
            {
                'snapshot_date': '2024-07-31',
                'assets': [
                    {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.40},
                    {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.35},
                    {'symbol': 'GOOGL', 'name': 'Alphabet Inc', 'weight': 0.25}
                ]
            },
            {
                'snapshot_date': '2024-08-31',
                'assets': [
                    {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.25},
                    {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.25},
                    {'symbol': 'GOOGL', 'name': 'Alphabet Inc', 'weight': 0.25},
                    {'symbol': 'AMZN', 'name': 'Amazon.com Inc', 'weight': 0.25}
                ]
            }
        ]
        
        # Step 3: Track changes and build history
        for i in range(1, len(monthly_snapshots)):
            change_analysis = tracker.track_universe_changes(
                'workflow-test',
                monthly_snapshots[i-1],
                monthly_snapshots[i]
            )
            
            # Record execution
            scheduler.record_execution(
                schedule_id=schedule.id,
                planned_date=datetime(2024, 6+i, 30 if 6+i in [6,8] else 31, 9, 0),
                actual_date=datetime(2024, 6+i, 30 if 6+i in [6,8] else 31, 9, 2),
                status=ScheduleStatus.COMPLETED,
                result={
                    'turnover_rate': change_analysis.turnover_rate,
                    'stability_trend': change_analysis.stability_trend
                }
            )
        
        # Step 4: Analyze overall turnover patterns
        turnover_metrics = tracker.calculate_turnover_metrics(
            'workflow-test',
            monthly_snapshots,
            'Q3-2024'
        )
        
        # Step 5: Plan future transition
        current_composition = {asset['symbol']: asset['weight'] for asset in monthly_snapshots[-1]['assets']}
        target_composition = {'AAPL': 0.30, 'MSFT': 0.30, 'GOOGL': 0.20, 'NVDA': 0.20}
        
        # Impact analysis
        impact_analysis = impact_analyzer.analyze_rebalance_impact(
            universe_id='workflow-test',
            old_composition=current_composition,
            new_composition=target_composition
        )
        
        # Transition planning
        transition_plan = transition_manager.manage_gradual_transition(
            universe_id='workflow-test',
            old_composition=current_composition,
            new_composition=target_composition
        )
        
        # Step 6: Verify complete workflow results
        assert len(schedule.executions) == 2  # July and August executions
        assert len(turnover_metrics.period_turnovers) == 2
        assert turnover_metrics.average_turnover > 0.0
        assert impact_analysis.total_transaction_cost > 0.0
        assert len(transition_plan.steps) > 0
        
        # Verify workflow coherence
        schedule_stats = scheduler.get_schedule_statistics(schedule.id)
        assert schedule_stats['success_rate'] == 1.0  # All executions successful
        
        # Core assets should be stable across the evolution
        assert 'AAPL' in turnover_metrics.core_assets
        assert 'MSFT' in turnover_metrics.core_assets