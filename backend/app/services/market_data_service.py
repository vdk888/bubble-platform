import asyncio
import logging
from datetime import date, datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor

from .interfaces.base import BaseService, ServiceResult
from .interfaces.data_provider import IDataProvider, MarketData, AssetInfo, ValidationResult
from .interfaces.i_composite_data_provider import ICompositeDataProvider, CompositeResult, DataSource
from .implementations.composite_data_provider import CompositeDataProvider
from .implementations.provider_health_monitor import ProviderHealthMonitor

logger = logging.getLogger(__name__)

class MarketDataService(BaseService):
    """
    Enhanced market data service with composite provider integration
    
    Features:
    - Triple-provider architecture (OpenBB → Yahoo → Alpha Vantage)
    - Intelligent failover with <500ms switching time
    - Real-time provider health monitoring
    - Performance optimization for backtesting
    - Professional-grade data quality assurance
    - Cost monitoring and optimization
    """
    
    def __init__(
        self,
        openbb_api_key: Optional[str] = None,
        alpha_vantage_api_key: Optional[str] = None,
        enable_monitoring: bool = True,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 300,
        max_workers: int = 10
    ):
        """
        Initialize market data service with composite provider
        
        Args:
            openbb_api_key: OpenBB Pro API key for professional features
            alpha_vantage_api_key: Alpha Vantage API key
            enable_monitoring: Enable real-time provider health monitoring
            enable_caching: Enable data caching for performance
            cache_ttl_seconds: Cache TTL in seconds
            max_workers: Maximum concurrent operations
        """
        # Initialize composite provider
        self.composite_provider = CompositeDataProvider(
            openbb_api_key=openbb_api_key,
            alpha_vantage_api_key=alpha_vantage_api_key,
            enable_caching=enable_caching,
            cache_ttl_seconds=cache_ttl_seconds,
            max_workers=max_workers
        )
        
        # Initialize health monitor
        self.health_monitor = ProviderHealthMonitor(
            monitoring_interval_seconds=30,
            history_retention_hours=24,
            enable_alerts=enable_monitoring
        ) if enable_monitoring else None
        
        self.enable_monitoring = enable_monitoring
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        logger.info(
            f"MarketDataService initialized with composite provider "
            f"(monitoring={'enabled' if enable_monitoring else 'disabled'})"
        )
    
    async def initialize(self) -> ServiceResult[bool]:
        """Initialize the market data service and start monitoring"""
        try:
            # Start health monitoring if enabled
            if self.health_monitor:
                start_result = await self.health_monitor.start_monitoring(
                    self.composite_provider.providers
                )
                if not start_result.success:
                    logger.warning(f"Failed to start health monitoring: {start_result.error}")
            
            # Enable circuit breakers for all providers
            for source in DataSource:
                await self.composite_provider.enable_circuit_breaker(
                    source=source,
                    failure_threshold=5,
                    recovery_timeout_seconds=300
                )
            
            logger.info("MarketDataService initialization completed")
            
            return ServiceResult(
                success=True,
                data=True,
                message="Market data service initialized successfully",
                metadata={
                    "providers_configured": len(self.composite_provider.providers),
                    "monitoring_enabled": self.enable_monitoring,
                    "circuit_breakers_enabled": True
                }
            )
        
        except Exception as e:
            logger.error(f"Failed to initialize MarketDataService: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to initialize market data service"
            )
    
    async def shutdown(self) -> ServiceResult[bool]:
        """Shutdown the market data service"""
        try:
            # Stop health monitoring
            if self.health_monitor:
                await self.health_monitor.stop_monitoring()
            
            # Shutdown thread pool
            self.executor.shutdown(wait=True)
            
            logger.info("MarketDataService shutdown completed")
            
            return ServiceResult(
                success=True,
                data=True,
                message="Market data service shutdown successfully"
            )
        
        except Exception as e:
            logger.error(f"Failed to shutdown MarketDataService: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to shutdown market data service"
            )
    
    async def fetch_real_time_data_with_fallback(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, MarketData]]:
        """
        Fetch real-time market data with intelligent failover
        
        Returns raw MarketData for compatibility with existing code
        """
        try:
            logger.info(f"Fetching real-time data for {len(symbols)} symbols with fallback")
            
            # Use composite provider for fallback capability
            composite_result = await self.composite_provider.fetch_real_time_data_composite(symbols)
            
            if not composite_result.success:
                return ServiceResult(
                    success=False,
                    error=composite_result.error,
                    message=composite_result.message,
                    metadata={"provider": "composite", "symbols_requested": len(symbols)}
                )
            
            # Extract MarketData from CompositeResult
            market_data = {}
            for symbol, composite_data in composite_result.data.items():
                if isinstance(composite_data.data, dict) and symbol in composite_data.data:
                    market_data[symbol] = composite_data.data[symbol]
                elif hasattr(composite_data, 'data') and composite_data.data:
                    # Handle different data structures
                    data = composite_data.data
                    if isinstance(data, dict) and len(data) == 1:
                        market_data[symbol] = next(iter(data.values()))
                    else:
                        market_data[symbol] = data
            
            return ServiceResult(
                success=True,
                data=market_data,
                message=f"Fetched real-time data for {len(market_data)}/{len(symbols)} symbols",
                metadata={
                    "provider": "composite",
                    "symbols_successful": len(market_data),
                    "symbols_requested": len(symbols),
                    "failover_occurred": any(
                        getattr(cd, 'failover_occurred', False) 
                        for cd in composite_result.data.values()
                    )
                },
                next_actions=["update_portfolios", "calculate_indicators"] if market_data else ["retry_failed_symbols"]
            )
        
        except Exception as e:
            logger.error(f"Real-time data fetch with fallback failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch real-time data with fallback"
            )
    
    async def fetch_historical_data_with_fallback(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        interval: str = "1d"
    ) -> ServiceResult[Dict[str, List[MarketData]]]:
        """
        Fetch historical market data with intelligent failover
        
        Returns raw MarketData for compatibility with existing code
        """
        try:
            logger.info(
                f"Fetching historical data for {len(symbols)} symbols "
                f"({start_date} to {end_date}, {interval}) with fallback"
            )
            
            # Use composite provider for fallback capability
            composite_result = await self.composite_provider.fetch_historical_data_composite(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                interval=interval
            )
            
            if not composite_result.success:
                return ServiceResult(
                    success=False,
                    error=composite_result.error,
                    message=composite_result.message,
                    metadata={
                        "provider": "composite",
                        "symbols_requested": len(symbols),
                        "date_range": f"{start_date} to {end_date}",
                        "interval": interval
                    }
                )
            
            # Extract historical data from CompositeResult
            historical_data = {}
            for symbol, composite_data in composite_result.data.items():
                if hasattr(composite_data, 'data') and composite_data.data:
                    data = composite_data.data
                    if isinstance(data, dict) and symbol in data:
                        historical_data[symbol] = data[symbol]
                    elif isinstance(data, list):
                        historical_data[symbol] = data
                    elif isinstance(data, dict) and len(data) == 1:
                        historical_data[symbol] = next(iter(data.values()))
            
            return ServiceResult(
                success=True,
                data=historical_data,
                message=f"Fetched historical data for {len(historical_data)}/{len(symbols)} symbols",
                metadata={
                    "provider": "composite",
                    "symbols_successful": len(historical_data),
                    "symbols_requested": len(symbols),
                    "date_range": f"{start_date} to {end_date}",
                    "interval": interval,
                    "total_data_points": sum(len(data) for data in historical_data.values()),
                    "failover_occurred": any(
                        getattr(cd, 'failover_occurred', False) 
                        for cd in composite_result.data.values()
                    )
                },
                next_actions=["calculate_indicators", "run_backtest"] if historical_data else ["retry_failed_symbols"]
            )
        
        except Exception as e:
            logger.error(f"Historical data fetch with fallback failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch historical data with fallback"
            )
    
    async def validate_symbols_with_fallback(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, ValidationResult]]:
        """Validate symbols with intelligent failover"""
        try:
            logger.info(f"Validating {len(symbols)} symbols with fallback")
            
            # Use composite provider for validation
            composite_result = await self.composite_provider.validate_symbols_composite(symbols)
            
            if not composite_result.success:
                return ServiceResult(
                    success=False,
                    error=composite_result.error,
                    message=composite_result.message,
                    metadata={"provider": "composite", "symbols_requested": len(symbols)}
                )
            
            # Extract ValidationResult from CompositeResult
            validation_results = {}
            for symbol, composite_data in composite_result.data.items():
                if hasattr(composite_data, 'data') and composite_data.data:
                    data = composite_data.data
                    if isinstance(data, dict) and symbol in data:
                        validation_results[symbol] = data[symbol]
                    elif hasattr(data, symbol):
                        validation_results[symbol] = getattr(data, symbol)
                    elif isinstance(data, dict) and len(data) == 1:
                        validation_results[symbol] = next(iter(data.values()))
            
            valid_count = sum(1 for vr in validation_results.values() if vr.is_valid)
            
            return ServiceResult(
                success=True,
                data=validation_results,
                message=f"Validated {valid_count}/{len(symbols)} symbols successfully",
                metadata={
                    "provider": "composite",
                    "total_symbols": len(symbols),
                    "valid_symbols": valid_count,
                    "invalid_symbols": len(symbols) - valid_count,
                    "failover_occurred": any(
                        getattr(cd, 'failover_occurred', False) 
                        for cd in composite_result.data.values()
                    )
                },
                next_actions=["add_valid_symbols_to_universe"] if valid_count > 0 else ["check_symbol_accuracy"]
            )
        
        except Exception as e:
            logger.error(f"Symbol validation with fallback failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to validate symbols with fallback"
            )
    
    async def fetch_asset_info_with_fallback(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, AssetInfo]]:
        """Fetch asset information with intelligent fallover"""
        try:
            logger.info(f"Fetching asset info for {len(symbols)} symbols with fallback")
            
            # Use composite provider for asset info
            composite_result = await self.composite_provider.fetch_asset_info_composite(symbols)
            
            if not composite_result.success:
                return ServiceResult(
                    success=False,
                    error=composite_result.error,
                    message=composite_result.message,
                    metadata={"provider": "composite", "symbols_requested": len(symbols)}
                )
            
            # Extract AssetInfo from CompositeResult
            asset_info = {}
            for symbol, composite_data in composite_result.data.items():
                if hasattr(composite_data, 'data') and composite_data.data:
                    data = composite_data.data
                    if isinstance(data, dict) and symbol in data:
                        asset_info[symbol] = data[symbol]
                    elif isinstance(data, dict) and len(data) == 1:
                        asset_info[symbol] = next(iter(data.values()))
                    elif hasattr(data, 'symbol'):  # Direct AssetInfo object
                        asset_info[symbol] = data
            
            valid_count = sum(1 for ai in asset_info.values() if ai.is_valid)
            
            return ServiceResult(
                success=True,
                data=asset_info,
                message=f"Fetched asset info for {valid_count}/{len(symbols)} symbols",
                metadata={
                    "provider": "composite",
                    "symbols_successful": valid_count,
                    "symbols_requested": len(symbols),
                    "failover_occurred": any(
                        getattr(cd, 'failover_occurred', False) 
                        for cd in composite_result.data.values()
                    )
                },
                next_actions=["create_universe", "analyze_sectors"] if valid_count > 0 else ["check_symbol_accuracy"]
            )
        
        except Exception as e:
            logger.error(f"Asset info fetch with fallback failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch asset info with fallback"
            )
    
    async def fetch_fundamental_data(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, Dict[str, Any]]]:
        """
        Fetch comprehensive fundamental data using OpenBB professional features
        with fallback to basic metrics from other providers
        """
        try:
            logger.info(f"Fetching fundamental data for {len(symbols)} symbols")
            
            composite_result = await self.composite_provider.fetch_fundamental_data_composite(symbols)
            
            if not composite_result.success:
                return ServiceResult(
                    success=False,
                    error=composite_result.error,
                    message=composite_result.message,
                    metadata={"provider": "composite", "symbols_requested": len(symbols)}
                )
            
            # Extract fundamental data
            fundamental_data = {}
            for symbol, composite_data in composite_result.data.items():
                if hasattr(composite_data, 'data') and composite_data.data:
                    data = composite_data.data
                    if isinstance(data, dict):
                        if symbol in data:
                            fundamental_data[symbol] = data[symbol]
                        elif len(data) == 1:
                            fundamental_data[symbol] = next(iter(data.values()))
                        else:
                            fundamental_data[symbol] = data
            
            return ServiceResult(
                success=len(fundamental_data) > 0,
                data=fundamental_data,
                message=f"Fetched fundamental data for {len(fundamental_data)}/{len(symbols)} symbols",
                metadata={
                    "provider": "composite",
                    "professional_features": True,
                    "symbols_successful": len(fundamental_data),
                    "symbols_requested": len(symbols)
                },
                next_actions=["analyze_fundamentals", "create_screens"] if fundamental_data else ["try_basic_metrics"]
            )
        
        except Exception as e:
            logger.error(f"Fundamental data fetch failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch fundamental data"
            )
    
    async def fetch_economic_indicators(
        self,
        indicators: List[str]
    ) -> ServiceResult[Dict[str, Any]]:
        """
        Fetch economic indicators primarily through OpenBB Terminal
        Professional-grade macro-economic data for strategy context
        """
        try:
            logger.info(f"Fetching economic indicators: {indicators}")
            
            composite_result = await self.composite_provider.fetch_economic_indicators_composite(indicators)
            
            if not composite_result.success:
                return ServiceResult(
                    success=False,
                    error=composite_result.error,
                    message=composite_result.message,
                    metadata={"provider": "composite", "indicators_requested": len(indicators)}
                )
            
            # Extract economic data
            economic_data = {}
            for indicator, composite_data in composite_result.data.items():
                if hasattr(composite_data, 'data') and composite_data.data:
                    economic_data[indicator] = composite_data.data
            
            return ServiceResult(
                success=len(economic_data) > 0,
                data=economic_data,
                message=f"Fetched economic data for {len(economic_data)}/{len(indicators)} indicators",
                metadata={
                    "provider": "composite",
                    "macro_data": True,
                    "indicators_successful": len(economic_data),
                    "indicators_requested": len(indicators)
                },
                next_actions=["analyze_macro_trends", "correlate_with_assets"] if economic_data else ["check_indicator_availability"]
            )
        
        except Exception as e:
            logger.error(f"Economic indicators fetch failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch economic indicators"
            )
    
    async def search_assets(
        self,
        query: str,
        limit: int = 10
    ) -> ServiceResult[List[AssetInfo]]:
        """Search for assets across all providers with quality ranking"""
        try:
            logger.info(f"Searching for assets: '{query}' (limit: {limit})")
            
            composite_result = await self.composite_provider.search_assets_composite(query, limit)
            
            if not composite_result.success:
                return ServiceResult(
                    success=False,
                    error=composite_result.error,
                    message=composite_result.message,
                    metadata={"provider": "composite", "query": query}
                )
            
            # Extract search results
            search_results = []
            if hasattr(composite_result.data, 'data') and composite_result.data.data:
                data = composite_result.data.data
                if isinstance(data, list):
                    search_results = data
                elif isinstance(data, dict):
                    search_results = list(data.values())
            
            return ServiceResult(
                success=len(search_results) > 0,
                data=search_results,
                message=f"Found {len(search_results)} assets matching '{query}'",
                metadata={
                    "provider": "composite",
                    "query": query,
                    "results_count": len(search_results),
                    "limit": limit
                },
                next_actions=["select_assets", "refine_search"] if search_results else ["try_different_keywords"]
            )
        
        except Exception as e:
            logger.error(f"Asset search failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message=f"Failed to search for assets matching '{query}'"
            )
    
    async def bulk_data_fetch(
        self,
        symbols: List[str],
        operations: List[str],
        parallel_requests: int = 5
    ) -> ServiceResult[Dict[str, Dict[str, Any]]]:
        """
        Optimized bulk data fetching for backtesting performance
        Target: 5x faster backtesting through intelligent batching
        """
        try:
            logger.info(f"Starting bulk data fetch: {len(symbols)} symbols, {len(operations)} operations")
            
            composite_result = await self.composite_provider.bulk_data_optimization(
                symbols=symbols,
                operations=operations,
                parallel_requests=parallel_requests
            )
            
            if not composite_result.success:
                return ServiceResult(
                    success=False,
                    error=composite_result.error,
                    message=composite_result.message,
                    metadata={
                        "provider": "composite",
                        "symbols_requested": len(symbols),
                        "operations_requested": len(operations)
                    }
                )
            
            return ServiceResult(
                success=True,
                data=composite_result.data,
                message=composite_result.message,
                metadata=composite_result.metadata,
                next_actions=["process_bulk_results", "start_backtest"] if composite_result.data else ["retry_failed_operations"]
            )
        
        except Exception as e:
            logger.error(f"Bulk data fetch failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to execute bulk data fetch"
            )
    
    async def get_provider_health(self) -> ServiceResult[Dict[str, Any]]:
        """Get current provider health status and performance metrics"""
        try:
            if not self.health_monitor:
                return ServiceResult(
                    success=False,
                    error="Health monitoring not enabled",
                    message="Provider health monitoring is not enabled"
                )
            
            # Get health status
            health_result = await self.health_monitor.get_health_status()
            if not health_result.success:
                return health_result
            
            # Get performance metrics
            metrics_result = await self.health_monitor.get_performance_metrics(60)  # 1 hour window
            
            # Get provider rankings
            rankings_result = await self.health_monitor.get_provider_rankings()
            
            # Get active alerts
            alerts_result = await self.health_monitor.get_active_alerts()
            
            return ServiceResult(
                success=True,
                data={
                    "health_status": health_result.data,
                    "performance_metrics": metrics_result.data if metrics_result.success else {},
                    "provider_rankings": rankings_result.data if rankings_result.success else [],
                    "active_alerts": alerts_result.data if alerts_result.success else []
                },
                message="Provider health information retrieved successfully",
                metadata={
                    "monitoring_enabled": self.enable_monitoring,
                    "healthy_providers": health_result.metadata.get("healthy_providers", []),
                    "unhealthy_providers": health_result.metadata.get("unhealthy_providers", [])
                }
            )
        
        except Exception as e:
            logger.error(f"Failed to get provider health: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to retrieve provider health information"
            )
    
    async def get_cost_analysis(
        self,
        time_period_hours: int = 24
    ) -> ServiceResult[Dict[str, Any]]:
        """Get cost analysis and optimization recommendations"""
        try:
            cost_result = await self.composite_provider.monitor_provider_costs(time_period_hours)
            
            if not cost_result.success:
                return cost_result
            
            # Add optimization recommendations
            cost_data = cost_result.data
            recommendations = []
            
            for source, data in cost_data.items():
                if data["cost_per_successful_request"] > 0.01:
                    recommendations.append(f"Consider reducing usage of {source.value} (high cost per request)")
                if data["success_rate"] < 0.8:
                    recommendations.append(f"Investigate {source.value} reliability issues (low success rate)")
            
            return ServiceResult(
                success=True,
                data={
                    "cost_breakdown": cost_data,
                    "recommendations": recommendations,
                    "total_cost": sum(data["estimated_cost_usd"] for data in cost_data.values()),
                    "most_expensive_provider": max(
                        cost_data.keys(), 
                        key=lambda x: cost_data[x]["estimated_cost_usd"]
                    ).value
                },
                message=f"Cost analysis completed for {time_period_hours}h period",
                metadata=cost_result.metadata
            )
        
        except Exception as e:
            logger.error(f"Failed to get cost analysis: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to retrieve cost analysis"
            )
    
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Check health of market data service and composite provider"""
        try:
            # Check composite provider health
            composite_health = await self.composite_provider.health_check()
            
            # Check health monitor if enabled
            monitor_health = None
            if self.health_monitor:
                monitor_health = await self.health_monitor.health_check()
            
            overall_healthy = composite_health.success and (not self.health_monitor or monitor_health.success)
            
            return ServiceResult(
                success=overall_healthy,
                data={
                    "service_healthy": overall_healthy,
                    "composite_provider": composite_health.data if composite_health.success else {"error": composite_health.error},
                    "health_monitor": monitor_health.data if monitor_health and monitor_health.success else {"enabled": self.enable_monitoring},
                    "configuration": {
                        "monitoring_enabled": self.enable_monitoring,
                        "max_workers": self.max_workers,
                        "providers_configured": len(self.composite_provider.providers)
                    }
                },
                message=f"Market data service health check: {'healthy' if overall_healthy else 'degraded'}",
                metadata={
                    "service_type": "market_data_service",
                    "composite_provider_healthy": composite_health.success,
                    "monitoring_enabled": self.enable_monitoring
                }
            )
            
        except Exception as e:
            logger.error(f"Market data service health check failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Market data service health check failed"
            )