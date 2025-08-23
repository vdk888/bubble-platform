from abc import abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from enum import Enum
from .base import BaseService, ServiceResult
from .data_provider import ValidationResult

class ValidationStrategy(str, Enum):
    """Asset validation strategies"""
    CACHE_ONLY = "cache_only"
    REAL_TIME = "real_time"
    MIXED = "mixed"
    BACKGROUND = "background"

class ValidationStatus(str, Enum):
    """Validation status values"""
    VALID = "valid"
    INVALID = "invalid"
    PENDING = "pending"
    ERROR = "error"
    EXPIRED = "expired"

class BulkValidationResult(BaseModel):
    """Bulk validation operation result"""
    total_requested: int
    successful_validations: int
    failed_validations: int
    pending_validations: int
    results: Dict[str, ValidationResult]
    errors: Dict[str, str] = {}
    processing_time: float
    cache_hits: int = 0
    cache_misses: int = 0

class IAssetValidationService(BaseService):
    """Interface for asset validation with mixed strategies"""
    
    @abstractmethod
    async def validate_symbol_mixed_strategy(
        self,
        symbol: str,
        force_refresh: bool = False
    ) -> ServiceResult[ValidationResult]:
        """
        Validate a single symbol using mixed strategy:
        1. Check Redis cache
        2. Real-time validation for common symbols  
        3. Background validation for edge cases
        4. Graceful degradation on failures
        """
        pass
    
    @abstractmethod
    async def validate_symbols_bulk(
        self,
        symbols: List[str],
        strategy: ValidationStrategy = ValidationStrategy.MIXED,
        max_concurrent: int = 10
    ) -> ServiceResult[BulkValidationResult]:
        """Validate multiple symbols with specified strategy"""
        pass
    
    @abstractmethod
    async def validate_real_time(
        self,
        symbol: str,
        timeout: int = 30
    ) -> ServiceResult[ValidationResult]:
        """
        Real-time validation with provider fallback:
        Primary: Yahoo Finance
        Fallback: Alpha Vantage
        """
        pass
    
    @abstractmethod
    async def get_cached_validation(
        self,
        symbol: str
    ) -> ServiceResult[Optional[ValidationResult]]:
        """Get validation result from cache"""
        pass
    
    @abstractmethod
    async def cache_validation_result(
        self,
        symbol: str,
        result: ValidationResult,
        ttl: int = 3600
    ) -> ServiceResult[bool]:
        """Cache validation result with TTL"""
        pass
    
    @abstractmethod
    async def queue_background_validation(
        self,
        symbols: List[str],
        priority: int = 1
    ) -> ServiceResult[str]:
        """Queue symbols for background validation, returns job_id"""
        pass
    
    @abstractmethod
    async def get_validation_stats(
        self,
        timeframe_hours: int = 24
    ) -> ServiceResult[Dict[str, Any]]:
        """Get validation performance statistics"""
        pass
    
    @abstractmethod
    async def invalidate_cache(
        self,
        symbols: Optional[List[str]] = None
    ) -> ServiceResult[int]:
        """Invalidate cache for specific symbols or all cache"""
        pass