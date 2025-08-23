import asyncio
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
import redis.asyncio as redis
from sqlalchemy.orm import Session
from sqlalchemy import select
import time

from .interfaces.asset_validation import (
    IAssetValidationService, 
    ValidationStrategy, 
    ValidationStatus, 
    BulkValidationResult,
    ServiceResult
)
from .interfaces.data_provider import ValidationResult
from .implementations.yahoo_data_provider import YahooDataProvider
from .implementations.alpha_vantage_provider import AlphaVantageProvider
from ..models.asset import Asset
from ..core.database import get_db

logger = logging.getLogger(__name__)

class AssetValidationService(IAssetValidationService):
    """
    Asset Validation Service implementing mixed validation strategy:
    1. Redis caching for fast responses
    2. Yahoo Finance as primary provider
    3. Alpha Vantage as fallback provider
    4. Background validation queue for edge cases
    5. Graceful degradation on failures
    """
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        yahoo_provider: Optional[YahooDataProvider] = None,
        alpha_vantage_provider: Optional[AlphaVantageProvider] = None,
        cache_ttl: int = 3600,  # 1 hour default TTL
        max_concurrent_validations: int = 10
    ):
        """
        Initialize Asset Validation Service
        
        Args:
            redis_client: Redis client for caching
            yahoo_provider: Yahoo Finance data provider
            alpha_vantage_provider: Alpha Vantage fallback provider
            cache_ttl: Default cache TTL in seconds
            max_concurrent_validations: Max concurrent validation requests
        """
        self.redis_client = redis_client or self._create_redis_client()
        self.yahoo_provider = yahoo_provider or YahooDataProvider()
        self.alpha_vantage_provider = alpha_vantage_provider or AlphaVantageProvider()
        self.cache_ttl = cache_ttl
        self.max_concurrent_validations = max_concurrent_validations
        
        # Performance tracking
        self._validation_stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "yahoo_success": 0,
            "yahoo_failures": 0,
            "alpha_vantage_success": 0,
            "alpha_vantage_failures": 0,
            "average_response_time": 0.0
        }
    
    def _create_redis_client(self) -> redis.Redis:
        """Create Redis client with default configuration"""
        try:
            import os
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            return redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.error(f"Failed to create Redis client: {e}")
            raise
    
    def _get_cache_key(self, symbol: str) -> str:
        """Generate cache key for symbol validation"""
        return f"asset_validation:{symbol.upper()}"
    
    def _get_stats_key(self) -> str:
        """Get cache key for validation statistics"""
        return "asset_validation:stats"
    
    async def validate_symbol_mixed_strategy(
        self,
        symbol: str,
        force_refresh: bool = False
    ) -> ServiceResult[ValidationResult]:
        """
        Validate a single symbol using mixed strategy:
        1. Check Redis cache (if not force_refresh)
        2. Real-time validation for common symbols  
        3. Background validation for edge cases
        4. Graceful degradation on failures
        """
        start_time = time.time()
        symbol = symbol.upper()
        
        try:
            self._validation_stats["total_requests"] += 1
            
            # Step 1: Check Redis cache (unless force refresh)
            if not force_refresh:
                cached_result = await self.get_cached_validation(symbol)
                if cached_result.success and cached_result.data:
                    self._validation_stats["cache_hits"] += 1
                    processing_time = time.time() - start_time
                    
                    # Update source to indicate cache hit
                    cached_result.data.source = "cache"
                    
                    return ServiceResult(
                        success=True,
                        data=cached_result.data,
                        message=f"Symbol {symbol} validation retrieved from cache",
                        metadata={
                            "source": "cache",
                            "processing_time": processing_time,
                            "ttl_remaining": await self._get_cache_ttl_remaining(symbol)
                        },
                        next_actions=["use_validated_symbol", "add_to_universe"]
                    )
            
            self._validation_stats["cache_misses"] += 1
            
            # Step 2: Real-time validation
            validation_result = await self.validate_real_time(symbol)
            
            if validation_result.success and validation_result.data:
                # Cache the successful result
                await self.cache_validation_result(symbol, validation_result.data, self.cache_ttl)
                
                processing_time = time.time() - start_time
                self._update_average_response_time(processing_time)
                
                return ServiceResult(
                    success=True,
                    data=validation_result.data,
                    message=f"Symbol {symbol} validated successfully",
                    metadata={
                        "source": "real_time",
                        "processing_time": processing_time,
                        "provider": validation_result.data.provider,
                        "cached": True
                    },
                    next_actions=["use_validated_symbol", "add_to_universe"]
                )
            
            # Step 3: Background validation (for edge cases)
            # For now, we'll queue it but still return the failed result
            await self.queue_background_validation([symbol])
            
            # Step 4: Graceful degradation - return failed result with helpful info
            processing_time = time.time() - start_time
            
            return ServiceResult(
                success=False,
                data=ValidationResult(
                    symbol=symbol,
                    is_valid=False,
                    provider="mixed_strategy",
                    timestamp=datetime.now(timezone.utc),
                    error=validation_result.error or "Symbol validation failed",
                    confidence=0.0,
                    source="mixed_strategy"
                ),
                error=validation_result.error,
                message=f"Symbol {symbol} validation failed, queued for background processing",
                metadata={
                    "source": "mixed_strategy",
                    "processing_time": processing_time,
                    "background_queued": True,
                    "suggestion": "Check symbol spelling or try again later"
                },
                next_actions=["check_symbol_spelling", "try_alternative_providers", "wait_for_background_validation"]
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Mixed strategy validation failed for {symbol}: {e}")
            
            return ServiceResult(
                success=False,
                data=ValidationResult(
                    symbol=symbol,
                    is_valid=False,
                    provider="mixed_strategy",
                    timestamp=datetime.now(timezone.utc),
                    error=str(e),
                    confidence=0.0,
                    source="error"
                ),
                error=str(e),
                message=f"Validation error for symbol {symbol}",
                metadata={
                    "source": "error",
                    "processing_time": processing_time
                }
            )
    
    async def validate_symbols_bulk(
        self,
        symbols: List[str],
        strategy: ValidationStrategy = ValidationStrategy.MIXED,
        max_concurrent: int = 10
    ) -> ServiceResult[BulkValidationResult]:
        """Validate multiple symbols with specified strategy"""
        start_time = time.time()
        symbols = [s.upper() for s in symbols]
        
        try:
            # Limit concurrency
            concurrent_limit = min(max_concurrent, self.max_concurrent_validations)
            
            results = {}
            errors = {}
            cache_hits = 0
            cache_misses = 0
            
            # Create semaphore for concurrency control
            semaphore = asyncio.Semaphore(concurrent_limit)
            
            async def validate_single_symbol(symbol: str):
                nonlocal cache_hits, cache_misses
                async with semaphore:
                    if strategy == ValidationStrategy.CACHE_ONLY:
                        result = await self.get_cached_validation(symbol)
                        if result.success and result.data:
                            cache_hits += 1
                            return symbol, result.data, None
                        else:
                            cache_misses += 1
                            return symbol, None, "Not found in cache"
                    
                    elif strategy == ValidationStrategy.REAL_TIME:
                        result = await self.validate_real_time(symbol)
                        cache_misses += 1  # Real-time always counts as cache miss
                        if result.success and result.data:
                            return symbol, result.data, None
                        else:
                            return symbol, None, result.error
                    
                    elif strategy == ValidationStrategy.MIXED:
                        result = await self.validate_symbol_mixed_strategy(symbol)
                        if result.metadata.get("source") == "cache":
                            cache_hits += 1
                        else:
                            cache_misses += 1
                        
                        if result.success and result.data:
                            return symbol, result.data, None
                        else:
                            return symbol, None, result.error
                    
                    else:  # BACKGROUND
                        await self.queue_background_validation([symbol])
                        return symbol, None, "Queued for background validation"
            
            # Execute all validations concurrently
            tasks = [validate_single_symbol(symbol) for symbol in symbols]
            completed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            successful_validations = 0
            failed_validations = 0
            pending_validations = 0
            
            for result in completed_results:
                if isinstance(result, Exception):
                    # Handle exceptions
                    failed_validations += 1
                    errors[f"unknown_symbol"] = str(result)
                else:
                    symbol, validation_result, error = result
                    if validation_result:
                        results[symbol] = validation_result
                        if validation_result.is_valid:
                            successful_validations += 1
                        else:
                            failed_validations += 1
                    else:
                        if strategy == ValidationStrategy.BACKGROUND or "background" in str(error):
                            pending_validations += 1
                        else:
                            failed_validations += 1
                        if error:
                            errors[symbol] = error
            
            processing_time = time.time() - start_time
            
            bulk_result = BulkValidationResult(
                total_requested=len(symbols),
                successful_validations=successful_validations,
                failed_validations=failed_validations,
                pending_validations=pending_validations,
                results=results,
                errors=errors,
                processing_time=processing_time,
                cache_hits=cache_hits,
                cache_misses=cache_misses
            )
            
            return ServiceResult(
                success=successful_validations > 0 or pending_validations > 0,
                data=bulk_result,
                message=f"Bulk validation completed: {successful_validations} successful, {failed_validations} failed, {pending_validations} pending",
                metadata={
                    "strategy": strategy.value,
                    "processing_time": processing_time,
                    "concurrent_requests": concurrent_limit,
                    "cache_hit_ratio": cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0.0
                },
                next_actions=["process_valid_symbols", "retry_failed_symbols", "check_pending_validations"] if successful_validations > 0 else ["review_failed_symbols"]
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Bulk validation failed: {e}")
            
            return ServiceResult(
                success=False,
                error=str(e),
                message="Bulk validation operation failed",
                metadata={
                    "strategy": strategy.value,
                    "processing_time": processing_time,
                    "requested_symbols": len(symbols)
                }
            )
    
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
        symbol = symbol.upper()
        
        try:
            # Try Yahoo Finance first (primary provider)
            try:
                yahoo_result = await asyncio.wait_for(
                    self.yahoo_provider.validate_symbols([symbol]),
                    timeout=timeout
                )
                
                if yahoo_result.success and yahoo_result.data and symbol in yahoo_result.data:
                    validation_result = yahoo_result.data[symbol]
                    if validation_result.is_valid:
                        self._validation_stats["yahoo_success"] += 1
                        return ServiceResult(
                            success=True,
                            data=validation_result,
                            message=f"Symbol {symbol} validated via Yahoo Finance",
                            metadata={"primary_provider": "yahoo_finance"},
                            next_actions=["cache_result", "use_validated_symbol"]
                        )
                
                self._validation_stats["yahoo_failures"] += 1
                logger.warning(f"Yahoo Finance validation failed for {symbol}")
                
            except asyncio.TimeoutError:
                self._validation_stats["yahoo_failures"] += 1
                logger.warning(f"Yahoo Finance validation timeout for {symbol}")
            except Exception as e:
                self._validation_stats["yahoo_failures"] += 1
                logger.warning(f"Yahoo Finance validation error for {symbol}: {e}")
            
            # Fallback to Alpha Vantage
            try:
                alpha_result = await asyncio.wait_for(
                    self.alpha_vantage_provider.validate_symbols([symbol]),
                    timeout=timeout
                )
                
                if alpha_result.success and alpha_result.data and symbol in alpha_result.data:
                    validation_result = alpha_result.data[symbol]
                    if validation_result.is_valid:
                        self._validation_stats["alpha_vantage_success"] += 1
                        return ServiceResult(
                            success=True,
                            data=validation_result,
                            message=f"Symbol {symbol} validated via Alpha Vantage (fallback)",
                            metadata={"fallback_provider": "alpha_vantage"},
                            next_actions=["cache_result", "use_validated_symbol"]
                        )
                
                self._validation_stats["alpha_vantage_failures"] += 1
                
            except asyncio.TimeoutError:
                self._validation_stats["alpha_vantage_failures"] += 1
                logger.warning(f"Alpha Vantage validation timeout for {symbol}")
            except Exception as e:
                self._validation_stats["alpha_vantage_failures"] += 1
                logger.warning(f"Alpha Vantage validation error for {symbol}: {e}")
            
            # Both providers failed
            return ServiceResult(
                success=False,
                data=ValidationResult(
                    symbol=symbol,
                    is_valid=False,
                    provider="both_failed",
                    timestamp=datetime.now(timezone.utc),
                    error="Both Yahoo Finance and Alpha Vantage validation failed",
                    confidence=0.0,
                    source="real_time"
                ),
                error="All validation providers failed",
                message=f"Symbol {symbol} could not be validated by any provider",
                metadata={"attempted_providers": ["yahoo_finance", "alpha_vantage"]},
                next_actions=["check_symbol_spelling", "try_manual_validation", "queue_background_validation"]
            )
            
        except Exception as e:
            logger.error(f"Real-time validation failed for {symbol}: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message=f"Real-time validation error for symbol {symbol}",
                metadata={"symbol": symbol}
            )
    
    async def get_cached_validation(
        self,
        symbol: str
    ) -> ServiceResult[Optional[ValidationResult]]:
        """Get validation result from cache"""
        try:
            cache_key = self._get_cache_key(symbol)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                validation_data = json.loads(cached_data)
                validation_result = ValidationResult(**validation_data)
                
                return ServiceResult(
                    success=True,
                    data=validation_result,
                    message=f"Validation result for {symbol} found in cache",
                    metadata={
                        "cache_key": cache_key,
                        "ttl_remaining": await self._get_cache_ttl_remaining(symbol)
                    }
                )
            else:
                return ServiceResult(
                    success=False,
                    data=None,
                    message=f"No cached validation found for {symbol}",
                    metadata={"cache_key": cache_key}
                )
                
        except Exception as e:
            logger.error(f"Cache retrieval failed for {symbol}: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message=f"Failed to retrieve cached validation for {symbol}"
            )
    
    async def cache_validation_result(
        self,
        symbol: str,
        result: ValidationResult,
        ttl: int = 3600
    ) -> ServiceResult[bool]:
        """Cache validation result with TTL"""
        try:
            cache_key = self._get_cache_key(symbol)
            
            # Convert ValidationResult to dict for JSON serialization
            result_dict = result.dict()
            if result_dict.get('timestamp'):
                result_dict['timestamp'] = result_dict['timestamp'].isoformat()
            if result_dict.get('asset_info') and result_dict['asset_info'].get('last_updated'):
                result_dict['asset_info']['last_updated'] = result_dict['asset_info']['last_updated'].isoformat()
            
            cached = await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result_dict, default=str)
            )
            
            return ServiceResult(
                success=bool(cached),
                data=bool(cached),
                message=f"Validation result for {symbol} cached with TTL {ttl}s",
                metadata={
                    "cache_key": cache_key,
                    "ttl": ttl,
                    "cached": bool(cached)
                }
            )
            
        except Exception as e:
            logger.error(f"Cache storage failed for {symbol}: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message=f"Failed to cache validation result for {symbol}"
            )
    
    async def queue_background_validation(
        self,
        symbols: List[str],
        priority: int = 1
    ) -> ServiceResult[str]:
        """Queue symbols for background validation, returns job_id"""
        try:
            job_id = f"bg_validation_{int(time.time())}_{hash(tuple(symbols)) % 10000}"
            
            job_data = {
                "job_id": job_id,
                "symbols": [s.upper() for s in symbols],
                "priority": priority,
                "queued_at": datetime.now(timezone.utc).isoformat(),
                "status": "queued"
            }
            
            # Store in Redis queue (simple implementation)
            queue_key = f"background_validation_queue:{priority}"
            await self.redis_client.lpush(queue_key, json.dumps(job_data))
            
            return ServiceResult(
                success=True,
                data=job_id,
                message=f"Queued {len(symbols)} symbols for background validation",
                metadata={
                    "job_id": job_id,
                    "symbols": symbols,
                    "priority": priority,
                    "queue_key": queue_key
                },
                next_actions=["monitor_background_job", "check_validation_status"]
            )
            
        except Exception as e:
            logger.error(f"Background validation queueing failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to queue symbols for background validation"
            )
    
    async def get_validation_stats(
        self,
        timeframe_hours: int = 24
    ) -> ServiceResult[Dict[str, Any]]:
        """Get validation performance statistics"""
        try:
            stats = self._validation_stats.copy()
            
            # Add cache statistics
            cache_info = await self.redis_client.info("memory")
            
            # Calculate additional metrics
            total_provider_requests = (
                stats["yahoo_success"] + 
                stats["yahoo_failures"] + 
                stats["alpha_vantage_success"] + 
                stats["alpha_vantage_failures"]
            )
            
            cache_hit_ratio = (
                stats["cache_hits"] / (stats["cache_hits"] + stats["cache_misses"])
                if (stats["cache_hits"] + stats["cache_misses"]) > 0 else 0.0
            )
            
            yahoo_success_rate = (
                stats["yahoo_success"] / (stats["yahoo_success"] + stats["yahoo_failures"])
                if (stats["yahoo_success"] + stats["yahoo_failures"]) > 0 else 0.0
            )
            
            alpha_vantage_success_rate = (
                stats["alpha_vantage_success"] / (stats["alpha_vantage_success"] + stats["alpha_vantage_failures"])
                if (stats["alpha_vantage_success"] + stats["alpha_vantage_failures"]) > 0 else 0.0
            )
            
            enhanced_stats = {
                **stats,
                "cache_hit_ratio": cache_hit_ratio,
                "yahoo_success_rate": yahoo_success_rate,
                "alpha_vantage_success_rate": alpha_vantage_success_rate,
                "total_provider_requests": total_provider_requests,
                "redis_memory_used": cache_info.get("used_memory_human", "N/A"),
                "timeframe_hours": timeframe_hours,
                "collected_at": datetime.now(timezone.utc).isoformat()
            }
            
            return ServiceResult(
                success=True,
                data=enhanced_stats,
                message=f"Validation statistics for last {timeframe_hours} hours",
                metadata={"timeframe_hours": timeframe_hours},
                next_actions=["analyze_performance", "optimize_caching", "scale_providers"]
            )
            
        except Exception as e:
            logger.error(f"Failed to get validation statistics: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to retrieve validation statistics"
            )
    
    async def invalidate_cache(
        self,
        symbols: Optional[List[str]] = None
    ) -> ServiceResult[int]:
        """Invalidate cache for specific symbols or all cache"""
        try:
            if symbols:
                # Invalidate specific symbols
                cache_keys = [self._get_cache_key(symbol.upper()) for symbol in symbols]
                deleted_count = await self.redis_client.delete(*cache_keys)
                
                return ServiceResult(
                    success=True,
                    data=deleted_count,
                    message=f"Invalidated cache for {deleted_count} symbols",
                    metadata={"symbols": symbols, "deleted_count": deleted_count}
                )
            else:
                # Invalidate all validation cache
                pattern = "asset_validation:*"
                keys = await self.redis_client.keys(pattern)
                if keys:
                    deleted_count = await self.redis_client.delete(*keys)
                else:
                    deleted_count = 0
                
                return ServiceResult(
                    success=True,
                    data=deleted_count,
                    message=f"Invalidated all validation cache ({deleted_count} keys)",
                    metadata={"pattern": pattern, "deleted_count": deleted_count}
                )
                
        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to invalidate cache"
            )
    
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Service health status"""
        try:
            health_data = {
                "service": "asset_validation",
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Check Redis connection
            try:
                await self.redis_client.ping()
                health_data["redis"] = "connected"
            except Exception as e:
                health_data["redis"] = f"error: {str(e)}"
            
            # Check Yahoo Finance provider
            yahoo_health = await self.yahoo_provider.health_check()
            health_data["yahoo_finance"] = "healthy" if yahoo_health.success else f"error: {yahoo_health.error}"
            
            # Check Alpha Vantage provider
            alpha_health = await self.alpha_vantage_provider.health_check()
            health_data["alpha_vantage"] = "healthy" if alpha_health.success else f"error: {alpha_health.error}"
            
            # Overall status
            overall_healthy = (
                health_data["redis"] == "connected" and
                yahoo_health.success  # At least primary provider should be healthy
            )
            
            health_data["status"] = "healthy" if overall_healthy else "degraded"
            
            return ServiceResult(
                success=overall_healthy,
                data=health_data,
                message="Asset Validation Service health check completed",
                next_actions=["use_validation_service"] if overall_healthy else ["check_provider_configurations"]
            )
            
        except Exception as e:
            logger.error(f"Asset Validation Service health check failed: {e}")
            return ServiceResult(
                success=False,
                data={"service": "asset_validation", "status": "unhealthy"},
                error=str(e),
                message="Asset Validation Service health check failed"
            )
    
    async def _get_cache_ttl_remaining(self, symbol: str) -> int:
        """Get remaining TTL for cached symbol"""
        try:
            cache_key = self._get_cache_key(symbol)
            ttl = await self.redis_client.ttl(cache_key)
            return ttl if ttl > 0 else 0
        except Exception:
            return 0
    
    def _update_average_response_time(self, response_time: float):
        """Update rolling average response time"""
        current_avg = self._validation_stats["average_response_time"]
        total_requests = self._validation_stats["total_requests"]
        
        if total_requests == 1:
            self._validation_stats["average_response_time"] = response_time
        else:
            # Rolling average
            self._validation_stats["average_response_time"] = (
                (current_avg * (total_requests - 1) + response_time) / total_requests
            )