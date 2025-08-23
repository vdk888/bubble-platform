from abc import abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from pydantic import BaseModel
from .base import BaseService, ServiceResult

class MarketData(BaseModel):
    """Market data structure for OHLCV information"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float  
    close: float
    volume: int
    adjusted_close: Optional[float] = None
    metadata: Dict[str, Any] = {}

class AssetInfo(BaseModel):
    """Asset fundamental information structure"""
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    is_valid: bool = True
    last_updated: Optional[datetime] = None
    metadata: Dict[str, Any] = {}

class ValidationResult(BaseModel):
    """Asset validation result"""
    symbol: str
    is_valid: bool
    provider: str
    timestamp: datetime
    error: Optional[str] = None
    confidence: float = 1.0  # 0.0 to 1.0
    asset_info: Optional[AssetInfo] = None
    source: str = "real_time"  # "cache", "real_time", "background"

class IDataProvider(BaseService):
    """Interface for market data providers (Yahoo Finance, Alpha Vantage, etc.)"""
    
    @abstractmethod
    async def fetch_historical_data(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        interval: str = "1d"
    ) -> ServiceResult[Dict[str, List[MarketData]]]:
        """Fetch historical price data"""
        pass
    
    @abstractmethod
    async def fetch_real_time_data(
        self, 
        symbols: List[str]
    ) -> ServiceResult[Dict[str, MarketData]]:
        """Fetch current market data"""
        pass
    
    @abstractmethod  
    async def fetch_asset_info(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, AssetInfo]]:
        """Fetch fundamental asset information"""
        pass
    
    @abstractmethod
    async def validate_symbols(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, ValidationResult]]:
        """Validate asset symbols and return validation results"""
        pass
    
    @abstractmethod
    async def search_assets(
        self,
        query: str,
        limit: int = 10
    ) -> ServiceResult[List[AssetInfo]]:
        """Search for assets by name or symbol"""
        pass