"""
Transition Manager - Evolution Module Component

Manages gradual universe transitions to minimize market impact and
provide smooth evolution from one universe composition to another.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from enum import Enum
import uuid


class TransitionStrategy(str, Enum):
    """Universe transition strategies"""
    IMMEDIATE = "immediate"  # All changes at once
    GRADUAL = "gradual"  # Phased transition over time
    VOLUME_WEIGHTED = "volume_weighted"  # Based on trading volume
    COST_OPTIMIZED = "cost_optimized"  # Minimize transaction costs
    RISK_MANAGED = "risk_managed"  # Minimize portfolio risk during transition


class TransitionStatus(str, Enum):
    """Transition execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class TransitionStep:
    """Individual step in a transition plan"""
    id: str
    step_number: int
    execution_date: date
    actions: List[Dict[str, Any]]  # List of buy/sell actions
    expected_cost: float
    expected_risk: float
    dependencies: List[str]  # Step IDs this step depends on
    status: TransitionStatus
    actual_execution_date: Optional[date]
    actual_cost: Optional[float]
    notes: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "step_number": self.step_number,
            "execution_date": self.execution_date.isoformat(),
            "actions": self.actions,
            "expected_cost": self.expected_cost,
            "expected_risk": self.expected_risk,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "actual_execution_date": self.actual_execution_date.isoformat() if self.actual_execution_date else None,
            "actual_cost": self.actual_cost,
            "notes": self.notes,
            "action_count": len(self.actions),
            "is_ready": len([dep for dep in self.dependencies if dep not in []]) == 0  # Simplified check
        }


@dataclass
class TransitionRule:
    """Rules governing transition behavior"""
    max_daily_turnover: float = 0.05  # Maximum 5% of portfolio per day
    max_single_position_change: float = 0.02  # Maximum 2% position change per step
    min_days_between_steps: int = 1
    max_total_cost: Optional[float] = None
    risk_budget: Optional[float] = None
    volume_constraints: Dict[str, float] = None  # Symbol -> max % of daily volume
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_daily_turnover": self.max_daily_turnover,
            "max_single_position_change": self.max_single_position_change,
            "min_days_between_steps": self.min_days_between_steps,
            "max_total_cost": self.max_total_cost,
            "risk_budget": self.risk_budget,
            "volume_constraints": self.volume_constraints or {}
        }


@dataclass
class TransitionPlan:
    """Complete transition plan from one universe composition to another"""
    id: str
    universe_id: str
    source_composition: Dict[str, float]  # symbol -> weight
    target_composition: Dict[str, float]  # symbol -> weight
    strategy: TransitionStrategy
    rules: TransitionRule
    steps: List[TransitionStep]
    created_at: datetime
    start_date: date
    expected_completion_date: date
    status: TransitionStatus
    total_expected_cost: float
    total_expected_risk: float
    progress_percentage: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "universe_id": self.universe_id,
            "source_composition": self.source_composition,
            "target_composition": self.target_composition,
            "strategy": self.strategy.value,
            "rules": self.rules.to_dict(),
            "steps": [step.to_dict() for step in self.steps],
            "created_at": self.created_at.isoformat(),
            "start_date": self.start_date.isoformat(),
            "expected_completion_date": self.expected_completion_date.isoformat(),
            "status": self.status.value,
            "total_expected_cost": self.total_expected_cost,
            "total_expected_risk": self.total_expected_risk,
            "progress_percentage": self.progress_percentage,
            "metadata": {
                "total_steps": len(self.steps),
                "completed_steps": len([s for s in self.steps if s.status == TransitionStatus.COMPLETED]),
                "estimated_days": (self.expected_completion_date - self.start_date).days,
                "symbols_to_add": list(set(self.target_composition.keys()) - set(self.source_composition.keys())),
                "symbols_to_remove": list(set(self.source_composition.keys()) - set(self.target_composition.keys())),
                "symbols_to_reweight": [
                    symbol for symbol in set(self.source_composition.keys()) & set(self.target_composition.keys())
                    if abs(self.source_composition[symbol] - self.target_composition[symbol]) > 0.001
                ]
            }
        }


class TransitionManager:
    """
    Manages gradual universe transitions with sophisticated planning and execution.
    
    Features:
    - Multiple transition strategies (immediate, gradual, volume-weighted, etc.)
    - Risk-aware transition planning
    - Cost optimization
    - Transaction cost estimation
    - Dependency management between transition steps
    """
    
    def __init__(self):
        self.active_transitions: Dict[str, TransitionPlan] = {}
        self.completed_transitions: Dict[str, TransitionPlan] = {}
    
    def manage_gradual_transition(
        self,
        universe_id: str,
        old_composition: Dict[str, float],
        new_composition: Dict[str, float],
        strategy: TransitionStrategy = TransitionStrategy.GRADUAL,
        rules: Optional[TransitionRule] = None,
        start_date: Optional[date] = None
    ) -> TransitionPlan:
        """
        Create and manage a gradual transition between universe compositions.
        
        Args:
            universe_id: UUID of universe being transitioned
            old_composition: Current composition (symbol -> weight)
            new_composition: Target composition (symbol -> weight)
            strategy: Transition strategy to use
            rules: Transition rules and constraints
            start_date: When to start transition (defaults to tomorrow)
            
        Returns:
            TransitionPlan with detailed steps and timeline
        """
        if rules is None:
            rules = TransitionRule()
        
        if start_date is None:
            start_date = date.today() + timedelta(days=1)
        
        plan_id = str(uuid.uuid4())
        
        # Calculate required changes
        changes = self._calculate_composition_changes(old_composition, new_composition)
        
        # Generate transition steps based on strategy
        steps = self._generate_transition_steps(
            changes, strategy, rules, start_date
        )
        
        # Calculate costs and risks
        total_cost, total_risk = self._estimate_transition_costs_and_risks(steps)
        
        # Determine expected completion date
        expected_completion = self._calculate_completion_date(steps)
        
        # Create transition plan
        plan = TransitionPlan(
            id=plan_id,
            universe_id=universe_id,
            source_composition=old_composition,
            target_composition=new_composition,
            strategy=strategy,
            rules=rules,
            steps=steps,
            created_at=datetime.now(),
            start_date=start_date,
            expected_completion_date=expected_completion,
            status=TransitionStatus.PENDING,
            total_expected_cost=total_cost,
            total_expected_risk=total_risk,
            progress_percentage=0.0
        )
        
        # Store plan
        self.active_transitions[plan_id] = plan
        
        return plan
    
    def execute_transition_step(
        self,
        plan_id: str,
        step_id: str,
        actual_cost: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a specific transition step.
        
        Args:
            plan_id: ID of transition plan
            step_id: ID of step to execute
            actual_cost: Actual execution cost
            notes: Optional execution notes
            
        Returns:
            Execution result with updated plan status
        """
        if plan_id not in self.active_transitions:
            return {"success": False, "error": "Transition plan not found"}
        
        plan = self.active_transitions[plan_id]
        
        # Find the step
        step = None
        for s in plan.steps:
            if s.id == step_id:
                step = s
                break
        
        if not step:
            return {"success": False, "error": "Transition step not found"}
        
        # Check if step is ready (dependencies met)
        if not self._check_step_dependencies(plan, step):
            return {"success": False, "error": "Step dependencies not met"}
        
        # Execute step
        step.status = TransitionStatus.COMPLETED
        step.actual_execution_date = date.today()
        step.actual_cost = actual_cost
        step.notes = notes
        
        # Update plan progress
        completed_steps = len([s for s in plan.steps if s.status == TransitionStatus.COMPLETED])
        plan.progress_percentage = (completed_steps / len(plan.steps)) * 100
        
        # Check if transition is complete
        if completed_steps == len(plan.steps):
            plan.status = TransitionStatus.COMPLETED
            self.completed_transitions[plan_id] = plan
            del self.active_transitions[plan_id]
        
        return {
            "success": True,
            "step_executed": step.to_dict(),
            "plan_progress": plan.progress_percentage,
            "plan_status": plan.status.value,
            "next_ready_steps": self._get_ready_steps(plan)
        }
    
    def pause_transition(self, plan_id: str) -> bool:
        """Pause an active transition"""
        if plan_id in self.active_transitions:
            self.active_transitions[plan_id].status = TransitionStatus.PAUSED
            return True
        return False
    
    def resume_transition(self, plan_id: str) -> bool:
        """Resume a paused transition"""
        if plan_id in self.active_transitions:
            plan = self.active_transitions[plan_id]
            if plan.status == TransitionStatus.PAUSED:
                plan.status = TransitionStatus.IN_PROGRESS
                return True
        return False
    
    def cancel_transition(self, plan_id: str) -> bool:
        """Cancel a transition plan"""
        if plan_id in self.active_transitions:
            self.active_transitions[plan_id].status = TransitionStatus.CANCELLED
            # Move to completed for historical reference
            self.completed_transitions[plan_id] = self.active_transitions[plan_id]
            del self.active_transitions[plan_id]
            return True
        return False
    
    def get_transition_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a transition plan"""
        plan = self.active_transitions.get(plan_id) or self.completed_transitions.get(plan_id)
        if not plan:
            return None
        
        return {
            "plan": plan.to_dict(),
            "ready_steps": self._get_ready_steps(plan) if plan.status == TransitionStatus.IN_PROGRESS else [],
            "current_composition": self._calculate_current_composition(plan),
            "remaining_changes": self._calculate_remaining_changes(plan)
        }
    
    def optimize_transition_timeline(
        self,
        plan_id: str,
        new_constraints: Optional[TransitionRule] = None
    ) -> Dict[str, Any]:
        """
        Optimize transition timeline based on new constraints or market conditions.
        
        Args:
            plan_id: ID of transition plan to optimize
            new_constraints: Optional new constraints to apply
            
        Returns:
            Optimization result with updated plan
        """
        if plan_id not in self.active_transitions:
            return {"success": False, "error": "Active transition plan not found"}
        
        plan = self.active_transitions[plan_id]
        
        if plan.status not in [TransitionStatus.PENDING, TransitionStatus.PAUSED]:
            return {"success": False, "error": "Cannot optimize transition in progress"}
        
        # Apply new constraints if provided
        if new_constraints:
            plan.rules = new_constraints
        
        # Recalculate steps with new constraints
        remaining_changes = self._calculate_remaining_changes(plan)
        new_steps = self._generate_transition_steps(
            remaining_changes, plan.strategy, plan.rules, date.today()
        )
        
        # Update plan with optimized steps
        plan.steps = new_steps
        plan.total_expected_cost, plan.total_expected_risk = self._estimate_transition_costs_and_risks(new_steps)
        plan.expected_completion_date = self._calculate_completion_date(new_steps)
        
        return {
            "success": True,
            "optimized_plan": plan.to_dict(),
            "changes": {
                "new_step_count": len(new_steps),
                "new_completion_date": plan.expected_completion_date.isoformat(),
                "new_expected_cost": plan.total_expected_cost,
                "new_expected_risk": plan.total_expected_risk
            }
        }
    
    def _calculate_composition_changes(
        self,
        old_composition: Dict[str, float],
        new_composition: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate required weight changes for each symbol"""
        all_symbols = set(old_composition.keys()) | set(new_composition.keys())
        
        changes = {}
        for symbol in all_symbols:
            old_weight = old_composition.get(symbol, 0.0)
            new_weight = new_composition.get(symbol, 0.0)
            change = new_weight - old_weight
            
            if abs(change) > 0.001:  # Only include significant changes
                changes[symbol] = change
        
        return changes
    
    def _generate_transition_steps(
        self,
        changes: Dict[str, float],
        strategy: TransitionStrategy,
        rules: TransitionRule,
        start_date: date
    ) -> List[TransitionStep]:
        """Generate transition steps based on strategy and rules"""
        
        if strategy == TransitionStrategy.IMMEDIATE:
            return self._generate_immediate_steps(changes, start_date)
        elif strategy == TransitionStrategy.GRADUAL:
            return self._generate_gradual_steps(changes, rules, start_date)
        elif strategy == TransitionStrategy.VOLUME_WEIGHTED:
            return self._generate_volume_weighted_steps(changes, rules, start_date)
        elif strategy == TransitionStrategy.COST_OPTIMIZED:
            return self._generate_cost_optimized_steps(changes, rules, start_date)
        elif strategy == TransitionStrategy.RISK_MANAGED:
            return self._generate_risk_managed_steps(changes, rules, start_date)
        else:
            return self._generate_gradual_steps(changes, rules, start_date)
    
    def _generate_immediate_steps(
        self,
        changes: Dict[str, float],
        start_date: date
    ) -> List[TransitionStep]:
        """Generate single-step immediate transition"""
        actions = []
        
        for symbol, change in changes.items():
            action_type = "buy" if change > 0 else "sell"
            actions.append({
                "symbol": symbol,
                "action": action_type,
                "weight_change": abs(change),
                "target_weight": change if change > 0 else 0,
                "priority": "high"
            })
        
        step = TransitionStep(
            id=str(uuid.uuid4()),
            step_number=1,
            execution_date=start_date,
            actions=actions,
            expected_cost=self._estimate_step_cost(actions),
            expected_risk=self._estimate_step_risk(actions),
            dependencies=[],
            status=TransitionStatus.PENDING,
            actual_execution_date=None,
            actual_cost=None,
            notes=None
        )
        
        return [step]
    
    def _generate_gradual_steps(
        self,
        changes: Dict[str, float],
        rules: TransitionRule,
        start_date: date
    ) -> List[TransitionStep]:
        """Generate gradual transition steps respecting daily turnover limits"""
        steps = []
        current_date = start_date
        remaining_changes = changes.copy()
        step_number = 1
        
        while remaining_changes:
            daily_actions = []
            daily_turnover = 0.0
            
            # Sort symbols by change magnitude (largest first)
            sorted_symbols = sorted(
                remaining_changes.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )
            
            for symbol, change in sorted_symbols:
                # Calculate how much we can change this symbol today
                max_change = min(
                    abs(change),
                    rules.max_single_position_change,
                    rules.max_daily_turnover - daily_turnover
                )
                
                if max_change <= 0.001:  # Skip insignificant changes
                    continue
                
                # Apply change in the correct direction
                actual_change = max_change if change > 0 else -max_change
                
                action_type = "buy" if actual_change > 0 else "sell"
                daily_actions.append({
                    "symbol": symbol,
                    "action": action_type,
                    "weight_change": abs(actual_change),
                    "target_weight": actual_change if actual_change > 0 else 0,
                    "priority": "medium"
                })
                
                # Update remaining changes
                remaining_changes[symbol] -= actual_change
                if abs(remaining_changes[symbol]) < 0.001:
                    del remaining_changes[symbol]
                
                daily_turnover += abs(actual_change)
                
                # Stop if we've hit daily turnover limit
                if daily_turnover >= rules.max_daily_turnover:
                    break
            
            # Create step if we have actions
            if daily_actions:
                step = TransitionStep(
                    id=str(uuid.uuid4()),
                    step_number=step_number,
                    execution_date=current_date,
                    actions=daily_actions,
                    expected_cost=self._estimate_step_cost(daily_actions),
                    expected_risk=self._estimate_step_risk(daily_actions),
                    dependencies=[steps[-1].id] if steps else [],
                    status=TransitionStatus.PENDING,
                    actual_execution_date=None,
                    actual_cost=None,
                    notes=None
                )
                steps.append(step)
                step_number += 1
            
            # Move to next trading day
            current_date += timedelta(days=rules.min_days_between_steps)
            
            # Safety break to prevent infinite loops
            if len(steps) > 100:
                break
        
        return steps
    
    def _generate_volume_weighted_steps(
        self,
        changes: Dict[str, float],
        rules: TransitionRule,
        start_date: date
    ) -> List[TransitionStep]:
        """Generate steps weighted by trading volume constraints"""
        # This is a simplified implementation
        # In practice, this would use actual trading volume data
        return self._generate_gradual_steps(changes, rules, start_date)
    
    def _generate_cost_optimized_steps(
        self,
        changes: Dict[str, float],
        rules: TransitionRule,
        start_date: date
    ) -> List[TransitionStep]:
        """Generate steps optimized for minimal transaction costs"""
        # This would use more sophisticated cost modeling
        return self._generate_gradual_steps(changes, rules, start_date)
    
    def _generate_risk_managed_steps(
        self,
        changes: Dict[str, float],
        rules: TransitionRule,
        start_date: date
    ) -> List[TransitionStep]:
        """Generate steps managed for minimal portfolio risk"""
        # This would incorporate risk modeling
        return self._generate_gradual_steps(changes, rules, start_date)
    
    def _estimate_step_cost(self, actions: List[Dict[str, Any]]) -> float:
        """Estimate transaction costs for a step"""
        # Simplified cost estimation (basis points)
        total_cost = 0.0
        for action in actions:
            weight_change = action['weight_change']
            # Assume 5 basis points transaction cost
            total_cost += weight_change * 0.0005
        return total_cost
    
    def _estimate_step_risk(self, actions: List[Dict[str, Any]]) -> float:
        """Estimate risk impact of a step"""
        # Simplified risk estimation
        total_risk = sum(action['weight_change'] for action in actions)
        return total_risk * 0.1  # Risk factor
    
    def _estimate_transition_costs_and_risks(
        self,
        steps: List[TransitionStep]
    ) -> tuple[float, float]:
        """Estimate total costs and risks for transition"""
        total_cost = sum(step.expected_cost for step in steps)
        total_risk = sum(step.expected_risk for step in steps)
        return total_cost, total_risk
    
    def _calculate_completion_date(self, steps: List[TransitionStep]) -> date:
        """Calculate expected completion date"""
        if not steps:
            return date.today()
        return max(step.execution_date for step in steps)
    
    def _check_step_dependencies(self, plan: TransitionPlan, step: TransitionStep) -> bool:
        """Check if step dependencies are met"""
        for dep_id in step.dependencies:
            dep_step = next((s for s in plan.steps if s.id == dep_id), None)
            if not dep_step or dep_step.status != TransitionStatus.COMPLETED:
                return False
        return True
    
    def _get_ready_steps(self, plan: TransitionPlan) -> List[Dict[str, Any]]:
        """Get steps that are ready for execution"""
        ready_steps = []
        for step in plan.steps:
            if (step.status == TransitionStatus.PENDING and 
                self._check_step_dependencies(plan, step) and
                step.execution_date <= date.today()):
                ready_steps.append(step.to_dict())
        return ready_steps
    
    def _calculate_current_composition(self, plan: TransitionPlan) -> Dict[str, float]:
        """Calculate current composition based on completed steps"""
        current = plan.source_composition.copy()
        
        for step in plan.steps:
            if step.status == TransitionStatus.COMPLETED:
                for action in step.actions:
                    symbol = action['symbol']
                    change = action['weight_change']
                    if action['action'] == 'sell':
                        change = -change
                    
                    current[symbol] = current.get(symbol, 0.0) + change
                    if current[symbol] <= 0.001:
                        current.pop(symbol, None)
        
        return current
    
    def _calculate_remaining_changes(self, plan: TransitionPlan) -> Dict[str, float]:
        """Calculate remaining changes needed"""
        current = self._calculate_current_composition(plan)
        target = plan.target_composition
        
        return self._calculate_composition_changes(current, target)