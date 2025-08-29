# Service Interfaces for Interface-First Design

from .base import BaseService, ServiceResult
from .data_provider import IDataProvider, MarketData, AssetInfo, ValidationResult
from .i_composite_data_provider import (
    ICompositeDataProvider, CompositeProviderConfig, ProviderHealth, 
    DataQuality, CompositeResult, ProviderPriority, DataSource, 
    FailoverStrategy, ConflictResolution
)
from .screener import IScreener, ScreeningCriteria, ScreeningResult, ScreeningError

__all__ = [
    # Base
    'BaseService',
    'ServiceResult',
    
    # Data Provider interfaces 
    'IDataProvider', 
    'MarketData',
    'AssetInfo', 
    'ValidationResult',
    
    # Composite data provider
    'ICompositeDataProvider',
    'CompositeProviderConfig', 
    'ProviderHealth',
    'DataQuality',
    'CompositeResult',
    'ProviderPriority',
    'DataSource',
    'FailoverStrategy', 
    'ConflictResolution',
    
    # Screener
    'IScreener', 
    'ScreeningCriteria', 
    'ScreeningResult', 
    'ScreeningError'
]