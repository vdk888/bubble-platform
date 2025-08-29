import asyncio
import logging
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import statistics

from ..interfaces.base import BaseService, ServiceResult
from ..interfaces.i_composite_data_provider import DataSource, ProviderHealth

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Provider health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning" 
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class HealthMetric:
    """Individual health metric measurement"""
    timestamp: datetime
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None
    operation: str = "health_check"

@dataclass
class PerformanceWindow:
    """Performance metrics over a time window"""
    window_size_minutes: int
    success_count: int
    failure_count: int
    avg_response_time_ms: float
    p95_response_time_ms: float
    error_rate: float

class ProviderHealthMonitor(BaseService):
    """
    Real-time provider health monitoring with intelligent alerting
    
    Features:
    - Continuous health monitoring across all providers
    - Performance trend analysis and alerting
    - Automatic degraded service detection
    - Circuit breaker recommendations
    - Cost optimization insights
    - Provider comparison and ranking
    """
    
    def __init__(
        self,
        monitoring_interval_seconds: int = 30,
        history_retention_hours: int = 24,
        alert_thresholds: Optional[Dict[str, float]] = None,
        enable_alerts: bool = True
    ):
        """
        Initialize provider health monitor
        
        Args:
            monitoring_interval_seconds: How often to check provider health
            history_retention_hours: How long to retain historical metrics
            alert_thresholds: Custom thresholds for health alerts
            enable_alerts: Enable/disable alerting system
        """
        self.monitoring_interval = monitoring_interval_seconds
        self.history_retention = timedelta(hours=history_retention_hours)
        self.enable_alerts = enable_alerts
        
        # Default alert thresholds
        self.alert_thresholds = {
            "error_rate_warning": 0.1,        # 10% error rate
            "error_rate_critical": 0.25,      # 25% error rate
            "response_time_warning": 2000,    # 2 seconds
            "response_time_critical": 5000,   # 5 seconds
            "consecutive_failures_warning": 3,
            "consecutive_failures_critical": 5
        }
        
        if alert_thresholds:
            self.alert_thresholds.update(alert_thresholds)
        
        # Health metrics storage
        self.health_history: Dict[DataSource, deque] = {
            source: deque(maxlen=1000) for source in DataSource
        }
        
        # Current health status
        self.current_health: Dict[DataSource, ProviderHealth] = {
            source: ProviderHealth(source=source) 
            for source in DataSource
        }
        
        # Performance tracking
        self.performance_windows: Dict[DataSource, Dict[int, PerformanceWindow]] = {
            source: {} for source in DataSource
        }
        
        # Alert management
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        self.alert_history: List[Dict[str, Any]] = []
        
        # Monitoring task
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
        
        logger.info(
            f"ProviderHealthMonitor initialized: interval={monitoring_interval_seconds}s, "
            f"retention={history_retention_hours}h, alerts={'enabled' if enable_alerts else 'disabled'}"
        )
    
    async def start_monitoring(
        self,
        providers: Dict[DataSource, Any]
    ) -> ServiceResult[bool]:
        """Start continuous health monitoring"""
        try:
            if self.is_monitoring:
                return ServiceResult(
                    success=False,
                    error="Monitoring already active",
                    message="Health monitoring is already running"
                )
            
            self.providers = providers
            self.is_monitoring = True
            
            # Start background monitoring task
            self.monitoring_task = asyncio.create_task(
                self._monitoring_loop()
            )
            
            logger.info("Provider health monitoring started")
            
            return ServiceResult(
                success=True,
                data=True,
                message="Provider health monitoring started successfully",
                metadata={
                    "monitoring_interval_seconds": self.monitoring_interval,
                    "providers_monitored": len(providers),
                    "alert_thresholds": self.alert_thresholds
                }
            )
        
        except Exception as e:
            logger.error(f"Failed to start health monitoring: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to start provider health monitoring"
            )
    
    async def stop_monitoring(self) -> ServiceResult[bool]:
        """Stop health monitoring"""
        try:
            if not self.is_monitoring:
                return ServiceResult(
                    success=True,
                    data=True,
                    message="Monitoring was not running"
                )
            
            self.is_monitoring = False
            
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("Provider health monitoring stopped")
            
            return ServiceResult(
                success=True,
                data=True,
                message="Provider health monitoring stopped successfully"
            )
        
        except Exception as e:
            logger.error(f"Failed to stop health monitoring: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to stop provider health monitoring"
            )
    
    async def _monitoring_loop(self):
        """Main monitoring loop - runs continuously in background"""
        try:
            while self.is_monitoring:
                start_time = time.time()
                
                # Check health of all providers
                health_tasks = [
                    self._check_provider_health(source, provider)
                    for source, provider in self.providers.items()
                ]
                
                # Execute health checks concurrently
                health_results = await asyncio.gather(*health_tasks, return_exceptions=True)
                
                # Process results and update metrics
                for i, (source, _) in enumerate(self.providers.items()):
                    result = health_results[i]
                    if isinstance(result, Exception):
                        logger.warning(f"Health check failed for {source.value}: {result}")
                        self._record_health_metric(source, HealthMetric(
                            timestamp=datetime.now(timezone.utc),
                            response_time_ms=0,
                            success=False,
                            error_message=str(result)
                        ))
                    else:
                        self._record_health_metric(source, result)
                
                # Update performance windows
                self._update_performance_windows()
                
                # Check for alerts
                if self.enable_alerts:
                    await self._check_alerts()
                
                # Cleanup old data
                self._cleanup_old_data()
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0, self.monitoring_interval - elapsed)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
        
        except asyncio.CancelledError:
            logger.info("Health monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Health monitoring loop error: {e}")
            # Try to restart monitoring after error
            if self.is_monitoring:
                await asyncio.sleep(10)
                self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _check_provider_health(self, source: DataSource, provider: Any) -> HealthMetric:
        """Check health of individual provider"""
        start_time = time.time()
        
        try:
            # Use provider's health check method if available
            if hasattr(provider, 'health_check'):
                result = await provider.health_check()
                response_time = (time.time() - start_time) * 1000
                
                return HealthMetric(
                    timestamp=datetime.now(timezone.utc),
                    response_time_ms=response_time,
                    success=result.success,
                    error_message=result.error if not result.success else None
                )
            
            # Fallback: simple symbol validation test
            test_result = await provider.validate_symbols(["AAPL"])
            response_time = (time.time() - start_time) * 1000
            
            return HealthMetric(
                timestamp=datetime.now(timezone.utc),
                response_time_ms=response_time,
                success=test_result.success,
                error_message=test_result.error if not test_result.success else None
            )
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthMetric(
                timestamp=datetime.now(timezone.utc),
                response_time_ms=response_time,
                success=False,
                error_message=str(e)
            )
    
    def _record_health_metric(self, source: DataSource, metric: HealthMetric):
        """Record health metric for provider"""
        # Add to history
        self.health_history[source].append(metric)
        
        # Update current health status
        health = self.current_health[source]
        health.last_success = metric.timestamp if metric.success else health.last_success
        health.last_failure = metric.timestamp if not metric.success else health.last_failure
        
        # Calculate consecutive failures
        recent_metrics = list(self.health_history[source])[-10:]  # Last 10 checks
        consecutive_failures = 0
        for m in reversed(recent_metrics):
            if not m.success:
                consecutive_failures += 1
            else:
                break
        
        health.consecutive_failures = consecutive_failures
        
        # Calculate recent metrics
        if recent_metrics:
            total_recent = len(recent_metrics)
            failures_recent = sum(1 for m in recent_metrics if not m.success)
            successes_recent = total_recent - failures_recent
            
            health.failure_rate = failures_recent / total_recent
            health.avg_response_time = statistics.mean([m.response_time_ms for m in recent_metrics])
            health.is_healthy = (
                health.failure_rate < 0.5 and 
                consecutive_failures < 3 and
                health.avg_response_time < 5000  # 5 seconds
            )
    
    def _update_performance_windows(self):
        """Update performance windows for trend analysis"""
        current_time = datetime.now(timezone.utc)
        
        # Define time windows (in minutes)
        windows = [5, 15, 60, 240]  # 5min, 15min, 1hr, 4hr
        
        for source in DataSource:
            metrics = [m for m in self.health_history[source]]
            
            for window_minutes in windows:
                window_start = current_time - timedelta(minutes=window_minutes)
                window_metrics = [
                    m for m in metrics 
                    if m.timestamp >= window_start
                ]
                
                if window_metrics:
                    successes = sum(1 for m in window_metrics if m.success)
                    failures = len(window_metrics) - successes
                    error_rate = failures / len(window_metrics)
                    
                    response_times = [m.response_time_ms for m in window_metrics]
                    avg_response_time = statistics.mean(response_times)
                    p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 5 else avg_response_time
                    
                    self.performance_windows[source][window_minutes] = PerformanceWindow(
                        window_size_minutes=window_minutes,
                        success_count=successes,
                        failure_count=failures,
                        avg_response_time_ms=avg_response_time,
                        p95_response_time_ms=p95_response_time,
                        error_rate=error_rate
                    )
    
    async def _check_alerts(self):
        """Check for alert conditions and generate alerts"""
        current_time = datetime.now(timezone.utc)
        
        for source in DataSource:
            health = self.current_health[source]
            
            # Check error rate alerts
            if health.failure_rate >= self.alert_thresholds["error_rate_critical"]:
                await self._create_alert(
                    source, AlertLevel.CRITICAL,
                    f"Critical error rate: {health.failure_rate:.1%}",
                    {"error_rate": health.failure_rate, "threshold": self.alert_thresholds["error_rate_critical"]}
                )
            elif health.failure_rate >= self.alert_thresholds["error_rate_warning"]:
                await self._create_alert(
                    source, AlertLevel.WARNING,
                    f"High error rate: {health.failure_rate:.1%}",
                    {"error_rate": health.failure_rate, "threshold": self.alert_thresholds["error_rate_warning"]}
                )
            
            # Check response time alerts
            if health.avg_response_time >= self.alert_thresholds["response_time_critical"]:
                await self._create_alert(
                    source, AlertLevel.CRITICAL,
                    f"Critical response time: {health.avg_response_time:.0f}ms",
                    {"avg_response_time": health.avg_response_time, "threshold": self.alert_thresholds["response_time_critical"]}
                )
            elif health.avg_response_time >= self.alert_thresholds["response_time_warning"]:
                await self._create_alert(
                    source, AlertLevel.WARNING,
                    f"High response time: {health.avg_response_time:.0f}ms",
                    {"avg_response_time": health.avg_response_time, "threshold": self.alert_thresholds["response_time_warning"]}
                )
            
            # Check consecutive failures
            if health.consecutive_failures >= self.alert_thresholds["consecutive_failures_critical"]:
                await self._create_alert(
                    source, AlertLevel.CRITICAL,
                    f"Critical: {health.consecutive_failures} consecutive failures",
                    {"consecutive_failures": health.consecutive_failures, "threshold": self.alert_thresholds["consecutive_failures_critical"]}
                )
            elif health.consecutive_failures >= self.alert_thresholds["consecutive_failures_warning"]:
                await self._create_alert(
                    source, AlertLevel.WARNING,
                    f"Warning: {health.consecutive_failures} consecutive failures",
                    {"consecutive_failures": health.consecutive_failures, "threshold": self.alert_thresholds["consecutive_failures_warning"]}
                )
    
    async def _create_alert(
        self,
        source: DataSource,
        level: AlertLevel,
        message: str,
        metadata: Dict[str, Any]
    ):
        """Create and manage alerts"""
        alert_key = f"{source.value}_{level.value}_{hash(message)}"
        
        # Check if alert already exists (avoid spam)
        if alert_key in self.active_alerts:
            # Update existing alert
            self.active_alerts[alert_key]["last_seen"] = datetime.now(timezone.utc)
            self.active_alerts[alert_key]["count"] += 1
        else:
            # Create new alert
            alert = {
                "alert_id": alert_key,
                "source": source.value,
                "level": level.value,
                "message": message,
                "metadata": metadata,
                "created": datetime.now(timezone.utc),
                "last_seen": datetime.now(timezone.utc),
                "count": 1,
                "acknowledged": False
            }
            
            self.active_alerts[alert_key] = alert
            self.alert_history.append(alert.copy())
            
            logger.warning(f"ALERT [{level.value.upper()}] {source.value}: {message}")
    
    def _cleanup_old_data(self):
        """Clean up old historical data"""
        current_time = datetime.now(timezone.utc)
        cutoff_time = current_time - self.history_retention
        
        for source in DataSource:
            # Remove old health metrics
            while (self.health_history[source] and 
                   self.health_history[source][0].timestamp < cutoff_time):
                self.health_history[source].popleft()
        
        # Clean up old alerts (keep last 100)
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
    
    async def get_health_status(self) -> ServiceResult[Dict[DataSource, ProviderHealth]]:
        """Get current health status of all providers"""
        try:
            return ServiceResult(
                success=True,
                data=dict(self.current_health),
                message="Health status retrieved successfully",
                metadata={
                    "monitoring_active": self.is_monitoring,
                    "healthy_providers": [
                        s.value for s, h in self.current_health.items() if h.is_healthy
                    ],
                    "unhealthy_providers": [
                        s.value for s, h in self.current_health.items() if not h.is_healthy
                    ]
                }
            )
        
        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to retrieve health status"
            )
    
    async def get_performance_metrics(
        self,
        time_window_minutes: int = 60
    ) -> ServiceResult[Dict[str, Any]]:
        """Get detailed performance metrics for specified time window"""
        try:
            metrics = {}
            
            for source in DataSource:
                if time_window_minutes in self.performance_windows[source]:
                    window = self.performance_windows[source][time_window_minutes]
                    
                    metrics[source.value] = {
                        "window_minutes": window.window_size_minutes,
                        "total_requests": window.success_count + window.failure_count,
                        "successes": window.success_count,
                        "failures": window.failure_count,
                        "error_rate": window.error_rate,
                        "avg_response_time_ms": window.avg_response_time_ms,
                        "p95_response_time_ms": window.p95_response_time_ms,
                        "health_status": "healthy" if self.current_health[source].is_healthy else "unhealthy"
                    }
                else:
                    metrics[source.value] = {
                        "window_minutes": time_window_minutes,
                        "message": "Insufficient data for this time window"
                    }
            
            return ServiceResult(
                success=True,
                data=metrics,
                message=f"Performance metrics retrieved for {time_window_minutes} minute window",
                metadata={
                    "time_window_minutes": time_window_minutes,
                    "available_windows": list(next(iter(self.performance_windows.values())).keys())
                }
            )
        
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to retrieve performance metrics"
            )
    
    async def get_active_alerts(self) -> ServiceResult[List[Dict[str, Any]]]:
        """Get all active alerts"""
        try:
            active_alerts = [
                alert for alert in self.active_alerts.values()
                if not alert["acknowledged"]
            ]
            
            return ServiceResult(
                success=True,
                data=active_alerts,
                message=f"Retrieved {len(active_alerts)} active alerts",
                metadata={
                    "total_active": len(active_alerts),
                    "critical_alerts": len([a for a in active_alerts if a["level"] == "critical"]),
                    "warning_alerts": len([a for a in active_alerts if a["level"] == "warning"])
                }
            )
        
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to retrieve active alerts"
            )
    
    async def acknowledge_alert(self, alert_id: str) -> ServiceResult[bool]:
        """Acknowledge an alert"""
        try:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id]["acknowledged"] = True
                self.active_alerts[alert_id]["acknowledged_at"] = datetime.now(timezone.utc)
                
                logger.info(f"Alert acknowledged: {alert_id}")
                
                return ServiceResult(
                    success=True,
                    data=True,
                    message=f"Alert {alert_id} acknowledged"
                )
            else:
                return ServiceResult(
                    success=False,
                    error="Alert not found",
                    message=f"Alert {alert_id} not found"
                )
        
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to acknowledge alert"
            )
    
    async def get_provider_rankings(self) -> ServiceResult[List[Dict[str, Any]]]:
        """Get provider performance rankings"""
        try:
            rankings = []
            
            for source in DataSource:
                health = self.current_health[source]
                
                # Calculate overall score (0-100)
                reliability_score = (1 - health.failure_rate) * 40  # 40% weight
                performance_score = max(0, 40 - (health.avg_response_time / 100))  # 40% weight  
                availability_score = 20 if health.is_healthy else 0  # 20% weight
                
                overall_score = reliability_score + performance_score + availability_score
                
                rankings.append({
                    "provider": source.value,
                    "overall_score": round(overall_score, 1),
                    "reliability_score": round(reliability_score, 1),
                    "performance_score": round(performance_score, 1),
                    "availability_score": round(availability_score, 1),
                    "is_healthy": health.is_healthy,
                    "error_rate": health.failure_rate,
                    "avg_response_time_ms": health.avg_response_time,
                    "consecutive_failures": health.consecutive_failures
                })
            
            # Sort by overall score
            rankings.sort(key=lambda x: x["overall_score"], reverse=True)
            
            return ServiceResult(
                success=True,
                data=rankings,
                message="Provider rankings calculated successfully",
                metadata={
                    "ranking_criteria": "reliability (40%) + performance (40%) + availability (20%)",
                    "best_provider": rankings[0]["provider"] if rankings else None,
                    "worst_provider": rankings[-1]["provider"] if rankings else None
                }
            )
        
        except Exception as e:
            logger.error(f"Failed to calculate provider rankings: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to calculate provider rankings"
            )
    
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Health check for the health monitor itself"""
        try:
            return ServiceResult(
                success=True,
                data={
                    "monitoring_active": self.is_monitoring,
                    "providers_monitored": len(self.providers) if hasattr(self, 'providers') else 0,
                    "alerts_enabled": self.enable_alerts,
                    "monitoring_interval_seconds": self.monitoring_interval,
                    "active_alerts_count": len(self.active_alerts),
                    "alert_history_count": len(self.alert_history),
                    "health_data_points": sum(len(history) for history in self.health_history.values()),
                    "memory_usage_tracking": self.enable_alerts  # Placeholder
                },
                message="Provider health monitor is operational",
                metadata={
                    "monitor_type": "provider_health_monitor",
                    "version": "1.0.0"
                }
            )
        
        except Exception as e:
            logger.error(f"Health monitor health check failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Health monitor health check failed"
            )