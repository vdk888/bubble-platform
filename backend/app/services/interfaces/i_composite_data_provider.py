from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel

from .base import BaseService, ServiceResult
from .data_provider import IDataProvider, MarketData, AssetInfo, ValidationResult

class ProviderPriority(Enum):
    """Provider priority levels for failover chain"""
    PRIMARY = 1
    SECONDARY = 2
    TERTIARY = 3

class DataSource(Enum):
    """Available data sources in the composite provider"""
    OPENBB = "openbb_terminal"
    YAHOO = "yahoo_finance"  
    ALPHA_VANTAGE = "alpha_vantage"

class FailoverStrategy(Enum):
    """Strategies for handling provider failures"""
    FAST_FAIL = "fast_fail"          # Fail quickly, move to next provider
    RETRY_ONCE = "retry_once"        # Retry failed provider once before moving
    CIRCUIT_BREAKER = "circuit_breaker"  # Temporarily disable failing providers

class ConflictResolution(Enum):
    """Strategies for resolving data conflicts between providers"""
    PRIMARY_WINS = "primary_wins"    # Always use primary provider data
    LATEST_TIMESTAMP = "latest_timestamp"  # Use data with latest timestamp
    MAJORITY_CONSENSUS = "majority_consensus"  # Use majority consensus value
    WEIGHTED_AVERAGE = "weighted_average"  # Weight by provider reliability

class CompositeProviderConfig(BaseModel):
    """Configuration for composite data provider behavior"""
    
    provider_chain: Dict[ProviderPriority, DataSource]
    failover_strategy: FailoverStrategy = FailoverStrategy.FAST_FAIL
    conflict_resolution: ConflictResolution = ConflictResolution.PRIMARY_WINS
    timeout_seconds: float = 30.0
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    enable_validation: bool = True
    quality_threshold: float = 0.8

class ProviderHealth(BaseModel):
    """Health status tracking for individual providers"""
    
    source: DataSource
    is_healthy: bool = True
    consecutive_failures: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    failure_rate: float = 0.0
    avg_response_time: float = 0.0

class DataQuality(BaseModel):
    """Data quality metrics and validation"""
    
    completeness: float = 1.0  # 0.0 to 1.0
    accuracy: float = 1.0      # 0.0 to 1.0  
    freshness: float = 1.0     # 0.0 to 1.0
    consistency: float = 1.0   # 0.0 to 1.0
    overall_score: Optional[float] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.overall_score is None:
            self.overall_score = (self.completeness + self.accuracy + self.freshness + self.consistency) / 4.0

class CompositeResult(BaseModel):
    """Enhanced result with provider attribution and quality metrics"""
    
    data: Any
    primary_source: DataSource
    contributing_sources: List[DataSource]
    quality: DataQuality
    conflicts_detected: bool = False
    failover_occurred: bool = False
    response_time_ms: float = 0.0
    metadata: Dict[str, Any] = {}
    
    model_config = {"arbitrary_types_allowed": True}

class ICompositeDataProvider(BaseService):
    """
    Interface for composite data provider with intelligent failover and conflict resolution
    
    Implements Triple-Provider Architecture: OpenBB → Yahoo → Alpha Vantage
    Features professional-grade reliability, monitoring, and quality assurance
    """
    
    @abstractmethod
    async def configure_providers(
        self,
        config: CompositeProviderConfig
    ) -> ServiceResult[bool]:
        """Configure the composite provider with failover chain and policies"""
        pass
    
    @abstractmethod
    async def fetch_with_fallback(
        self,
        operation: str,
        **kwargs
    ) -> ServiceResult[CompositeResult]:
        """
        Execute data fetch operation with automatic failover
        
        Args:
            operation: Operation name (e.g., 'historical_data', 'real_time', 'fundamentals')
            **kwargs: Operation-specific parameters
        
        Returns:
            ServiceResult containing CompositeResult with provider attribution
        """
        pass
    
    @abstractmethod
    async def get_provider_health(self) -> ServiceResult[Dict[DataSource, ProviderHealth]]:
        """Get health status of all configured providers"""
        pass
    
    @abstractmethod
    async def validate_data_quality(
        self,
        data: Any,
        source: DataSource,
        operation: str
    ) -> ServiceResult[DataQuality]:
        """Validate data quality from specific provider"""
        pass
    
    @abstractmethod
    async def resolve_conflicts(
        self,
        data_sources: Dict[DataSource, Any],
        resolution_strategy: ConflictResolution
    ) -> ServiceResult[Any]:
        """Resolve conflicts when multiple providers return different data"""
        pass
    
    @abstractmethod
    async def enable_circuit_breaker(
        self,
        source: DataSource,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 300
    ) -> ServiceResult[bool]:
        """Enable circuit breaker for specific provider"""
        pass
    
    @abstractmethod
    async def get_performance_metrics(self) -> ServiceResult[Dict[str, Any]]:
        """Get comprehensive performance metrics for all providers"""
        pass
    
    # Enhanced versions of standard IDataProvider methods with composite functionality
    
    @abstractmethod
    async def fetch_historical_data_composite(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        interval: str = "1d"
    ) -> ServiceResult[Dict[str, CompositeResult]]:
        """Fetch historical data with multi-provider intelligence"""
        pass
    
    @abstractmethod
    async def fetch_real_time_data_composite(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, CompositeResult]]:
        """Fetch real-time data with multi-provider intelligence"""
        pass
    
    @abstractmethod
    async def fetch_asset_info_composite(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, CompositeResult]]:
        """Fetch asset information with multi-provider intelligence"""
        pass
    
    @abstractmethod
    async def validate_symbols_composite(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, CompositeResult]]:
        """Validate symbols with multi-provider intelligence"""
        pass
    
    @abstractmethod
    async def fetch_fundamental_data_composite(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, CompositeResult]]:
        """
        Fetch comprehensive fundamental data using OpenBB professional features
        with Yahoo/Alpha Vantage fallback for basic metrics
        """
        pass
    
    @abstractmethod
    async def fetch_economic_indicators_composite(
        self,
        indicators: List[str]
    ) -> ServiceResult[Dict[str, CompositeResult]]:
        """
        Fetch economic indicators primarily through OpenBB Terminal
        Professional-grade macro-economic data for strategy context
        """
        pass
    
    @abstractmethod
    async def search_assets_composite(
        self,
        query: str,
        limit: int = 10
    ) -> ServiceResult[CompositeResult]:
        """Search assets across all providers with quality ranking"""
        pass
    
    @abstractmethod
    async def bulk_data_optimization(
        self,
        symbols: List[str],
        operations: List[str],
        parallel_requests: int = 5
    ) -> ServiceResult[Dict[str, Dict[str, CompositeResult]]]:
        """
        Optimized bulk data fetching for backtesting performance
        Reduces API calls through intelligent batching and caching
        Target: 5x faster backtesting through complete dataset optimization
        """
        pass
    
    @abstractmethod
    async def monitor_provider_costs(
        self,
        time_period_hours: int = 24
    ) -> ServiceResult[Dict[DataSource, Dict[str, Any]]]:
        """
        Monitor API usage and costs across all providers
        Cost optimization features for OpenBB Pro vs free tier management
        """
        pass
    
    @abstractmethod
    async def enable_real_time_monitoring(
        self,
        callback_url: Optional[str] = None
    ) -> ServiceResult[bool]:
        """
        Enable real-time monitoring of provider health and data quality
        Proactive alerting for degraded service or data inconsistencies
        """
        pass