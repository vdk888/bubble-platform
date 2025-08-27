"""
Impact Analyzer - Evolution Module Component

Analyzes the impact of universe rebalances on portfolio performance,
transaction costs, and risk characteristics.
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics


class ImpactSeverity(str, Enum):
    """Impact severity levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class CostComponent(str, Enum):
    """Transaction cost components"""
    SPREAD = "spread"  # Bid-ask spread
    COMMISSION = "commission"  # Broker commission
    MARKET_IMPACT = "market_impact"  # Price impact from trading
    SLIPPAGE = "slippage"  # Execution slippage
    OPPORTUNITY = "opportunity"  # Opportunity cost of delays


@dataclass
class TransactionCost:
    """Detailed transaction cost breakdown"""
    symbol: str
    action: str  # 'buy' or 'sell'
    quantity: float
    estimated_price: float
    
    # Cost components (in basis points)
    spread_cost: float
    commission_cost: float
    market_impact_cost: float
    slippage_cost: float
    opportunity_cost: float
    
    total_cost: float
    cost_percentage: float  # As percentage of transaction value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "action": self.action,
            "quantity": self.quantity,
            "estimated_price": self.estimated_price,
            "transaction_value": self.quantity * self.estimated_price,
            "cost_breakdown": {
                "spread_cost_bps": self.spread_cost,
                "commission_cost_bps": self.commission_cost,
                "market_impact_cost_bps": self.market_impact_cost,
                "slippage_cost_bps": self.slippage_cost,
                "opportunity_cost_bps": self.opportunity_cost
            },
            "total_cost": self.total_cost,
            "cost_percentage": self.cost_percentage,
            "cost_per_share": self.total_cost / self.quantity if self.quantity > 0 else 0
        }


@dataclass
class RiskImpact:
    """Risk impact analysis of rebalancing"""
    pre_rebalance_risk: float
    post_rebalance_risk: float
    risk_change: float
    risk_change_percentage: float
    
    # Risk decomposition
    systematic_risk_change: float
    idiosyncratic_risk_change: float
    concentration_risk_change: float
    
    # Risk metrics
    tracking_error_impact: float
    beta_change: float
    volatility_impact: float
    
    # Risk assessment
    impact_severity: ImpactSeverity
    risk_recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_levels": {
                "pre_rebalance_risk": self.pre_rebalance_risk,
                "post_rebalance_risk": self.post_rebalance_risk,
                "risk_change": self.risk_change,
                "risk_change_percentage": self.risk_change_percentage
            },
            "risk_decomposition": {
                "systematic_risk_change": self.systematic_risk_change,
                "idiosyncratic_risk_change": self.idiosyncratic_risk_change,
                "concentration_risk_change": self.concentration_risk_change
            },
            "risk_metrics": {
                "tracking_error_impact": self.tracking_error_impact,
                "beta_change": self.beta_change,
                "volatility_impact": self.volatility_impact
            },
            "assessment": {
                "impact_severity": self.impact_severity.value,
                "risk_recommendations": self.risk_recommendations
            }
        }


@dataclass
class PerformanceImpact:
    """Performance impact analysis"""
    expected_return_change: float
    expected_return_change_annualized: float
    
    # Performance attribution
    sector_rotation_impact: float
    security_selection_impact: float
    timing_impact: float
    
    # Performance risk
    performance_volatility_change: float
    sharpe_ratio_impact: float
    information_ratio_impact: float
    
    # Confidence intervals
    performance_confidence_95: Tuple[float, float]
    performance_confidence_68: Tuple[float, float]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected_returns": {
                "return_change": self.expected_return_change,
                "return_change_annualized": self.expected_return_change_annualized
            },
            "performance_attribution": {
                "sector_rotation_impact": self.sector_rotation_impact,
                "security_selection_impact": self.security_selection_impact,
                "timing_impact": self.timing_impact
            },
            "performance_risk": {
                "volatility_change": self.performance_volatility_change,
                "sharpe_ratio_impact": self.sharpe_ratio_impact,
                "information_ratio_impact": self.information_ratio_impact
            },
            "confidence_intervals": {
                "95_percent": {
                    "lower": self.performance_confidence_95[0],
                    "upper": self.performance_confidence_95[1]
                },
                "68_percent": {
                    "lower": self.performance_confidence_68[0],
                    "upper": self.performance_confidence_68[1]
                }
            }
        }


@dataclass
class ImpactAnalysis:
    """Comprehensive rebalance impact analysis"""
    analysis_id: str
    universe_id: str
    analysis_date: datetime
    
    # Rebalance details
    old_composition: Dict[str, float]
    new_composition: Dict[str, float]
    turnover_rate: float
    
    # Impact components
    transaction_costs: List[TransactionCost]
    risk_impact: RiskImpact
    performance_impact: PerformanceImpact
    
    # Summary metrics
    total_transaction_cost: float
    net_expected_benefit: float  # Expected performance - costs
    benefit_cost_ratio: float
    
    # Recommendations
    execution_recommendations: List[str]
    timing_recommendations: List[str]
    risk_mitigation_suggestions: List[str]
    
    # Confidence score
    analysis_confidence: float  # 0-1 confidence in analysis
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_metadata": {
                "analysis_id": self.analysis_id,
                "universe_id": self.universe_id,
                "analysis_date": self.analysis_date.isoformat(),
                "analysis_confidence": self.analysis_confidence
            },
            "rebalance_details": {
                "old_composition": self.old_composition,
                "new_composition": self.new_composition,
                "turnover_rate": self.turnover_rate,
                "symbols_added": list(set(self.new_composition.keys()) - set(self.old_composition.keys())),
                "symbols_removed": list(set(self.old_composition.keys()) - set(self.new_composition.keys())),
                "symbols_reweighted": [
                    symbol for symbol in set(self.old_composition.keys()) & set(self.new_composition.keys())
                    if abs(self.old_composition[symbol] - self.new_composition[symbol]) > 0.001
                ]
            },
            "cost_analysis": {
                "transaction_costs": [cost.to_dict() for cost in self.transaction_costs],
                "total_transaction_cost": self.total_transaction_cost,
                "cost_by_component": self._aggregate_costs_by_component()
            },
            "risk_analysis": self.risk_impact.to_dict(),
            "performance_analysis": self.performance_impact.to_dict(),
            "summary": {
                "net_expected_benefit": self.net_expected_benefit,
                "benefit_cost_ratio": self.benefit_cost_ratio,
                "overall_recommendation": self._get_overall_recommendation()
            },
            "recommendations": {
                "execution": self.execution_recommendations,
                "timing": self.timing_recommendations,
                "risk_mitigation": self.risk_mitigation_suggestions
            }
        }
    
    def _aggregate_costs_by_component(self) -> Dict[str, float]:
        """Aggregate transaction costs by component"""
        components = {
            "spread": sum(cost.spread_cost for cost in self.transaction_costs),
            "commission": sum(cost.commission_cost for cost in self.transaction_costs),
            "market_impact": sum(cost.market_impact_cost for cost in self.transaction_costs),
            "slippage": sum(cost.slippage_cost for cost in self.transaction_costs),
            "opportunity": sum(cost.opportunity_cost for cost in self.transaction_costs)
        }
        return components
    
    def _get_overall_recommendation(self) -> str:
        """Get overall recommendation based on analysis"""
        if self.benefit_cost_ratio > 2.0:
            return "Highly Recommended"
        elif self.benefit_cost_ratio > 1.0:
            return "Recommended"
        elif self.benefit_cost_ratio > 0.5:
            return "Marginal Benefit"
        else:
            return "Not Recommended"


class ImpactAnalyzer:
    """
    Comprehensive impact analyzer for universe rebalances.
    
    Analyzes transaction costs, risk impacts, and performance implications
    of universe composition changes to support informed rebalancing decisions.
    """
    
    def __init__(self):
        # Cost model parameters (in basis points)
        self.default_spread_cost = 5.0  # 5 bps
        self.default_commission_cost = 2.0  # 2 bps
        self.default_market_impact_base = 3.0  # 3 bps base
        self.default_slippage_cost = 2.0  # 2 bps
        
        # Risk model parameters
        self.default_correlation_matrix = {}  # Would be populated with actual correlations
        self.default_beta_estimates = {}  # Would be populated with actual betas
        
    def analyze_rebalance_impact(
        self,
        universe_id: str,
        old_composition: Dict[str, float],
        new_composition: Dict[str, float],
        portfolio_value: float = 1000000.0,  # $1M default
        transaction_costs: Optional[Dict[str, Dict[str, float]]] = None
    ) -> ImpactAnalysis:
        """
        Perform comprehensive impact analysis of a rebalance.
        
        Args:
            universe_id: UUID of universe being rebalanced
            old_composition: Current composition (symbol -> weight)
            new_composition: Target composition (symbol -> weight)
            portfolio_value: Total portfolio value
            transaction_costs: Optional custom transaction cost parameters
            
        Returns:
            ImpactAnalysis with comprehensive impact assessment
        """
        analysis_id = f"impact_{universe_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Calculate turnover
        turnover_rate = self._calculate_turnover(old_composition, new_composition)
        
        # Analyze transaction costs
        transaction_cost_analysis = self._analyze_transaction_costs(
            old_composition, new_composition, portfolio_value, transaction_costs
        )
        
        # Analyze risk impact
        risk_analysis = self._analyze_risk_impact(old_composition, new_composition)
        
        # Analyze performance impact
        performance_analysis = self._analyze_performance_impact(old_composition, new_composition)
        
        # Calculate summary metrics
        total_transaction_cost = sum(cost.total_cost for cost in transaction_cost_analysis)
        net_expected_benefit = performance_analysis.expected_return_change_annualized * portfolio_value - total_transaction_cost
        benefit_cost_ratio = (performance_analysis.expected_return_change_annualized * portfolio_value) / total_transaction_cost if total_transaction_cost > 0 else float('inf')
        
        # Generate recommendations
        execution_recs = self._generate_execution_recommendations(transaction_cost_analysis, turnover_rate)
        timing_recs = self._generate_timing_recommendations(performance_analysis, risk_analysis)
        risk_recs = self._generate_risk_mitigation_recommendations(risk_analysis)
        
        # Calculate confidence score
        confidence = self._calculate_analysis_confidence(
            len(old_composition) + len(new_composition),
            turnover_rate,
            performance_analysis,
            risk_analysis
        )
        
        return ImpactAnalysis(
            analysis_id=analysis_id,
            universe_id=universe_id,
            analysis_date=datetime.now(),
            old_composition=old_composition,
            new_composition=new_composition,
            turnover_rate=turnover_rate,
            transaction_costs=transaction_cost_analysis,
            risk_impact=risk_analysis,
            performance_impact=performance_analysis,
            total_transaction_cost=total_transaction_cost,
            net_expected_benefit=net_expected_benefit,
            benefit_cost_ratio=benefit_cost_ratio,
            execution_recommendations=execution_recs,
            timing_recommendations=timing_recs,
            risk_mitigation_suggestions=risk_recs,
            analysis_confidence=confidence
        )
    
    def compare_rebalance_scenarios(
        self,
        universe_id: str,
        current_composition: Dict[str, float],
        scenarios: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare multiple rebalancing scenarios.
        
        Args:
            universe_id: UUID of universe
            current_composition: Current composition
            scenarios: List of scenario dictionaries with 'name' and 'composition'
            
        Returns:
            Comparison analysis of all scenarios
        """
        scenario_analyses = []
        
        for scenario in scenarios:
            analysis = self.analyze_rebalance_impact(
                universe_id,
                current_composition,
                scenario['composition']
            )
            
            scenario_analyses.append({
                'scenario_name': scenario['name'],
                'analysis': analysis,
                'summary_metrics': {
                    'turnover_rate': analysis.turnover_rate,
                    'total_cost': analysis.total_transaction_cost,
                    'expected_benefit': analysis.net_expected_benefit,
                    'benefit_cost_ratio': analysis.benefit_cost_ratio,
                    'risk_impact': analysis.risk_impact.risk_change,
                    'overall_score': self._calculate_scenario_score(analysis)
                }
            })
        
        # Rank scenarios
        scenario_analyses.sort(
            key=lambda x: x['summary_metrics']['overall_score'],
            reverse=True
        )
        
        return {
            'universe_id': universe_id,
            'comparison_date': datetime.now().isoformat(),
            'scenarios_analyzed': len(scenarios),
            'scenario_analyses': scenario_analyses,
            'best_scenario': scenario_analyses[0]['scenario_name'] if scenario_analyses else None,
            'recommendation': self._generate_scenario_recommendation(scenario_analyses)
        }
    
    def _calculate_turnover(
        self,
        old_composition: Dict[str, float],
        new_composition: Dict[str, float]
    ) -> float:
        """Calculate portfolio turnover rate"""
        all_symbols = set(old_composition.keys()) | set(new_composition.keys())
        
        if not all_symbols:
            return 0.0
        
        total_change = sum(
            abs(new_composition.get(symbol, 0.0) - old_composition.get(symbol, 0.0))
            for symbol in all_symbols
        )
        
        return total_change / 2.0  # Divide by 2 as turnover counts one-way
    
    def _analyze_transaction_costs(
        self,
        old_composition: Dict[str, float],
        new_composition: Dict[str, float],
        portfolio_value: float,
        custom_costs: Optional[Dict[str, Dict[str, float]]] = None
    ) -> List[TransactionCost]:
        """Analyze transaction costs for each position change"""
        costs = []
        all_symbols = set(old_composition.keys()) | set(new_composition.keys())
        
        for symbol in all_symbols:
            old_weight = old_composition.get(symbol, 0.0)
            new_weight = new_composition.get(symbol, 0.0)
            weight_change = new_weight - old_weight
            
            if abs(weight_change) < 0.001:  # Skip insignificant changes
                continue
            
            action = "buy" if weight_change > 0 else "sell"
            quantity = abs(weight_change) * portfolio_value
            estimated_price = 100.0  # Placeholder - would use real price data
            
            # Get cost parameters (custom or default)
            if custom_costs and symbol in custom_costs:
                cost_params = custom_costs[symbol]
            else:
                cost_params = {}
            
            spread_cost = cost_params.get('spread', self.default_spread_cost)
            commission_cost = cost_params.get('commission', self.default_commission_cost)
            
            # Market impact scales with trade size
            base_market_impact = cost_params.get('market_impact', self.default_market_impact_base)
            size_factor = min(abs(weight_change) * 100, 50)  # Cap at 50bps additional
            market_impact_cost = base_market_impact + size_factor * 0.1
            
            slippage_cost = cost_params.get('slippage', self.default_slippage_cost)
            opportunity_cost = 0.0  # Would be calculated based on timing
            
            # Convert basis points to dollar costs
            transaction_value = quantity * estimated_price
            total_cost_bps = spread_cost + commission_cost + market_impact_cost + slippage_cost + opportunity_cost
            total_cost = transaction_value * (total_cost_bps / 10000)
            
            cost = TransactionCost(
                symbol=symbol,
                action=action,
                quantity=quantity,
                estimated_price=estimated_price,
                spread_cost=spread_cost,
                commission_cost=commission_cost,
                market_impact_cost=market_impact_cost,
                slippage_cost=slippage_cost,
                opportunity_cost=opportunity_cost,
                total_cost=total_cost,
                cost_percentage=total_cost_bps / 100
            )
            
            costs.append(cost)
        
        return costs
    
    def _analyze_risk_impact(
        self,
        old_composition: Dict[str, float],
        new_composition: Dict[str, float]
    ) -> RiskImpact:
        """Analyze risk impact of rebalancing"""
        
        # Simplified risk calculation (in practice would use actual risk models)
        old_concentration = self._calculate_concentration_risk(old_composition)
        new_concentration = self._calculate_concentration_risk(new_composition)
        
        pre_rebalance_risk = 0.15 + old_concentration * 0.05  # Base 15% vol + concentration premium
        post_rebalance_risk = 0.15 + new_concentration * 0.05
        
        risk_change = post_rebalance_risk - pre_rebalance_risk
        risk_change_percentage = (risk_change / pre_rebalance_risk) * 100
        
        # Risk decomposition (simplified)
        systematic_risk_change = risk_change * 0.7  # 70% systematic
        idiosyncratic_risk_change = risk_change * 0.2  # 20% idiosyncratic
        concentration_risk_change = (new_concentration - old_concentration) * 0.05
        
        # Impact assessment
        if abs(risk_change_percentage) < 2:
            severity = ImpactSeverity.LOW
        elif abs(risk_change_percentage) < 5:
            severity = ImpactSeverity.MODERATE
        elif abs(risk_change_percentage) < 10:
            severity = ImpactSeverity.HIGH
        else:
            severity = ImpactSeverity.CRITICAL
        
        # Recommendations
        recommendations = []
        if new_concentration > 0.3:
            recommendations.append("Consider diversification to reduce concentration risk")
        if risk_change > 0.02:
            recommendations.append("Monitor increased risk levels closely")
        if len(new_composition) < 10:
            recommendations.append("Consider adding more positions to improve diversification")
        
        return RiskImpact(
            pre_rebalance_risk=pre_rebalance_risk,
            post_rebalance_risk=post_rebalance_risk,
            risk_change=risk_change,
            risk_change_percentage=risk_change_percentage,
            systematic_risk_change=systematic_risk_change,
            idiosyncratic_risk_change=idiosyncratic_risk_change,
            concentration_risk_change=concentration_risk_change,
            tracking_error_impact=abs(risk_change) * 0.5,
            beta_change=0.0,  # Would calculate from actual betas
            volatility_impact=risk_change,
            impact_severity=severity,
            risk_recommendations=recommendations
        )
    
    def _analyze_performance_impact(
        self,
        old_composition: Dict[str, float],
        new_composition: Dict[str, float]
    ) -> PerformanceImpact:
        """Analyze performance impact of rebalancing"""
        
        # Simplified performance calculation (would use expected returns model)
        old_expected_return = sum(weight * 0.08 for weight in old_composition.values())  # 8% base return
        new_expected_return = sum(weight * 0.08 for weight in new_composition.values())
        
        return_change = new_expected_return - old_expected_return
        return_change_annualized = return_change
        
        # Performance attribution (simplified)
        sector_rotation = return_change * 0.4
        security_selection = return_change * 0.4
        timing_impact = return_change * 0.2
        
        # Performance risk
        volatility_change = 0.01  # 1% change in volatility
        sharpe_impact = return_change / 0.15 if return_change != 0 else 0.0
        
        # Confidence intervals (simplified)
        std_error = 0.02  # 2% standard error
        conf_95 = (return_change - 1.96 * std_error, return_change + 1.96 * std_error)
        conf_68 = (return_change - std_error, return_change + std_error)
        
        return PerformanceImpact(
            expected_return_change=return_change,
            expected_return_change_annualized=return_change_annualized,
            sector_rotation_impact=sector_rotation,
            security_selection_impact=security_selection,
            timing_impact=timing_impact,
            performance_volatility_change=volatility_change,
            sharpe_ratio_impact=sharpe_impact,
            information_ratio_impact=sharpe_impact * 0.8,
            performance_confidence_95=conf_95,
            performance_confidence_68=conf_68
        )
    
    def _calculate_concentration_risk(self, composition: Dict[str, float]) -> float:
        """Calculate Herfindahl concentration index"""
        if not composition:
            return 0.0
        
        return sum(weight ** 2 for weight in composition.values())
    
    def _generate_execution_recommendations(
        self,
        transaction_costs: List[TransactionCost],
        turnover_rate: float
    ) -> List[str]:
        """Generate execution recommendations based on costs"""
        recommendations = []
        
        total_cost = sum(cost.total_cost for cost in transaction_costs)
        high_cost_threshold = 0.005  # 50 bps
        
        if total_cost > high_cost_threshold:
            recommendations.append("Consider gradual execution to reduce market impact")
        
        if turnover_rate > 0.5:
            recommendations.append("High turnover detected - validate rebalancing necessity")
        
        large_trades = [cost for cost in transaction_costs if cost.cost_percentage > 0.01]
        if large_trades:
            recommendations.append(f"Break down {len(large_trades)} large trades to reduce impact")
        
        return recommendations
    
    def _generate_timing_recommendations(
        self,
        performance: PerformanceImpact,
        risk: RiskImpact
    ) -> List[str]:
        """Generate timing recommendations"""
        recommendations = []
        
        if performance.expected_return_change < 0:
            recommendations.append("Consider delaying rebalance if performance impact is negative")
        
        if risk.impact_severity == ImpactSeverity.HIGH:
            recommendations.append("Time rebalance during low volatility periods")
        
        return recommendations
    
    def _generate_risk_mitigation_recommendations(self, risk: RiskImpact) -> List[str]:
        """Generate risk mitigation recommendations"""
        return risk.risk_recommendations
    
    def _calculate_analysis_confidence(
        self,
        num_positions: int,
        turnover_rate: float,
        performance: PerformanceImpact,
        risk: RiskImpact
    ) -> float:
        """Calculate confidence score for analysis"""
        base_confidence = 0.5
        
        # More positions = higher confidence
        position_factor = min(num_positions / 20, 1.0) * 0.2
        
        # Lower turnover = higher confidence
        turnover_factor = (1.0 - min(turnover_rate, 1.0)) * 0.2
        
        # Reasonable performance expectations = higher confidence
        performance_factor = 0.1 if abs(performance.expected_return_change) < 0.1 else 0.0
        
        return min(base_confidence + position_factor + turnover_factor + performance_factor, 1.0)
    
    def _calculate_scenario_score(self, analysis: ImpactAnalysis) -> float:
        """Calculate overall score for a scenario"""
        # Weighted score based on benefit-cost ratio, risk impact, and confidence
        bcr_score = min(analysis.benefit_cost_ratio / 2.0, 1.0) * 0.5  # 50% weight
        risk_score = max(0, 1.0 - abs(analysis.risk_impact.risk_change_percentage) / 10) * 0.3  # 30% weight
        confidence_score = analysis.analysis_confidence * 0.2  # 20% weight
        
        return bcr_score + risk_score + confidence_score
    
    def _generate_scenario_recommendation(self, scenario_analyses: List[Dict[str, Any]]) -> str:
        """Generate recommendation based on scenario comparison"""
        if not scenario_analyses:
            return "No scenarios to compare"
        
        best_scenario = scenario_analyses[0]
        best_score = best_scenario['summary_metrics']['overall_score']
        
        if best_score > 0.8:
            return f"Strongly recommend {best_scenario['scenario_name']}"
        elif best_score > 0.6:
            return f"Recommend {best_scenario['scenario_name']} with monitoring"
        elif best_score > 0.4:
            return f"Consider {best_scenario['scenario_name']} but evaluate risks"
        else:
            return "None of the scenarios show compelling benefits"