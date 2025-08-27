import pytest
import pytest_asyncio
import asyncio
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List

from app.services.asset_validation_service import AssetValidationService
from app.services.interfaces.asset_validation import ValidationStrategy, ValidationStatus, BulkValidationResult
from app.services.interfaces.data_provider import ValidationResult, AssetInfo, ServiceResult
from app.services.implementations.yahoo_data_provider import YahooDataProvider
from app.services.implementations.alpha_vantage_provider import AlphaVantageProvider

# Sprint 2 test markers for organization and filtering
pytestmark = [
    pytest.mark.sprint2,
    pytest.mark.asset_validation,
    pytest.mark.mixed_validation_strategy,
    pytest.mark.integration
]


# Global fixtures for all test classes
@pytest_asyncio.fixture
async def mock_redis_client():
    """Mock Redis client for testing"""
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.keys = AsyncMock(return_value=[])
    mock_redis.lpush = AsyncMock(return_value=1)
    mock_redis.ttl = AsyncMock(return_value=-1)
    mock_redis.info = AsyncMock(return_value={"used_memory_human": "1.5M"})
    return mock_redis

@pytest_asyncio.fixture
async def mock_yahoo_provider():
    """Mock Yahoo Finance provider"""
    mock_provider = AsyncMock(spec=YahooDataProvider)
    mock_provider.health_check = AsyncMock(return_value=ServiceResult(
        success=True,
        data={"provider": "yahoo_finance", "status": "healthy"},
        message="Yahoo Finance provider is operational"
    ))
    return mock_provider

@pytest_asyncio.fixture
async def mock_alpha_vantage_provider():
    """Mock Alpha Vantage provider"""
    mock_provider = AsyncMock(spec=AlphaVantageProvider)
    mock_provider.health_check = AsyncMock(return_value=ServiceResult(
        success=True,
        data={"provider": "alpha_vantage", "status": "healthy"},
        message="Alpha Vantage provider is operational"
    ))
    return mock_provider

@pytest_asyncio.fixture
async def validation_service(mock_redis_client, mock_yahoo_provider, mock_alpha_vantage_provider):
    """Create Asset Validation Service with mocked dependencies"""
    service = AssetValidationService(
        redis_client=mock_redis_client,
        yahoo_provider=mock_yahoo_provider,
        alpha_vantage_provider=mock_alpha_vantage_provider,
        cache_ttl=3600,
        max_concurrent_validations=10
    )
    return service

@pytest_asyncio.fixture
async def valid_validation_result():
    """Sample valid validation result"""
    return ValidationResult(
        symbol="AAPL",
        is_valid=True,
        provider="yahoo_finance",
        timestamp=datetime.now(timezone.utc),
        confidence=1.0,
        asset_info=AssetInfo(
            symbol="AAPL",
            name="Apple Inc.",
            sector="Technology",
            industry="Consumer Electronics",
            market_cap=3000000000000,
            pe_ratio=28.5,
            dividend_yield=0.0045,
            is_valid=True,
            last_updated=datetime.now(timezone.utc)
        ),
        source="real_time"
    )

@pytest_asyncio.fixture
async def invalid_validation_result():
    """Sample invalid validation result"""
    return ValidationResult(
        symbol="INVALID",
        is_valid=False,
        provider="yahoo_finance",
        timestamp=datetime.now(timezone.utc),
        error="Symbol not found",
        confidence=0.0,
        source="real_time"
    )


class TestMixedValidationStrategy:
    """Test mixed validation strategy implementation"""

    @pytest.mark.asyncio
    async def test_validate_symbol_cache_hit(self, validation_service, mock_redis_client, valid_validation_result):
        """Test validation with cache hit (fastest path)"""
        # Setup cache hit
        cached_data = valid_validation_result.model_dump()
        cached_data['timestamp'] = cached_data['timestamp'].isoformat()
        cached_data['asset_info']['last_updated'] = cached_data['asset_info']['last_updated'].isoformat()
        mock_redis_client.get.return_value = json.dumps(cached_data, default=str)
        mock_redis_client.ttl.return_value = 1800  # 30 minutes remaining

        # Execute
        result = await validation_service.validate_symbol_mixed_strategy("AAPL")

        # Assert
        assert result.success is True
        assert result.data.symbol == "AAPL"
        assert result.data.is_valid is True
        assert result.data.source == "cache"
        assert result.metadata["source"] == "cache"
        assert "ttl_remaining" in result.metadata
        
        # Verify cache was checked
        mock_redis_client.get.assert_called_once_with("asset_validation:AAPL")

    @pytest.mark.asyncio
    async def test_validate_symbol_cache_miss_yahoo_success(self, validation_service, mock_redis_client, mock_yahoo_provider, valid_validation_result):
        """Test validation with cache miss, Yahoo Finance success"""
        # Setup cache miss
        mock_redis_client.get.return_value = None
        
        # Setup Yahoo Finance success
        mock_yahoo_provider.validate_symbols.return_value = ServiceResult(
            success=True,
            data={"AAPL": valid_validation_result}
        )

        # Execute
        result = await validation_service.validate_symbol_mixed_strategy("AAPL")

        # Assert
        assert result.success is True
        assert result.data.symbol == "AAPL"
        assert result.data.is_valid is True
        assert result.metadata["source"] == "real_time"
        assert result.metadata["provider"] == "yahoo_finance"
        assert result.metadata["cached"] is True
        
        # Verify cache was updated
        mock_redis_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_symbol_force_refresh(self, validation_service, mock_redis_client, mock_yahoo_provider, valid_validation_result):
        """Test validation with force refresh (skips cache)"""
        # Setup Yahoo Finance success
        mock_yahoo_provider.validate_symbols.return_value = ServiceResult(
            success=True,
            data={"AAPL": valid_validation_result}
        )

        # Execute with force refresh
        result = await validation_service.validate_symbol_mixed_strategy("AAPL", force_refresh=True)

        # Assert
        assert result.success is True
        assert result.data.symbol == "AAPL"
        assert result.metadata["source"] == "real_time"
        
        # Verify cache was not checked
        mock_redis_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_symbol_all_providers_fail(self, validation_service, mock_redis_client, mock_yahoo_provider, mock_alpha_vantage_provider):
        """Test validation when all providers fail"""
        # Setup cache miss
        mock_redis_client.get.return_value = None
        
        # Setup all providers failing
        mock_yahoo_provider.validate_symbols.return_value = ServiceResult(
            success=False,
            error="Yahoo Finance error"
        )
        mock_alpha_vantage_provider.validate_symbols.return_value = ServiceResult(
            success=False,
            error="Alpha Vantage error"
        )

        # Execute
        result = await validation_service.validate_symbol_mixed_strategy("INVALID")

        # Assert
        assert result.success is False
        assert result.data.symbol == "INVALID"
        assert result.data.is_valid is False
        assert result.metadata["source"] == "mixed_strategy"
        assert result.metadata["background_queued"] is True
        assert "check_symbol_spelling" in result.next_actions


class TestRealTimeValidation:
    """Test real-time validation with provider fallback"""

    @pytest.mark.asyncio
    async def test_validate_real_time_yahoo_success(self, validation_service, mock_yahoo_provider, valid_validation_result):
        """Test real-time validation with Yahoo Finance success"""
        # Setup Yahoo Finance success
        mock_yahoo_provider.validate_symbols.return_value = ServiceResult(
            success=True,
            data={"AAPL": valid_validation_result}
        )

        # Execute
        result = await validation_service.validate_real_time("AAPL")

        # Assert
        assert result.success is True
        assert result.data.symbol == "AAPL"
        assert result.data.is_valid is True
        assert result.metadata["primary_provider"] == "yahoo_finance"
        assert "cache_result" in result.next_actions

    @pytest.mark.asyncio
    async def test_validate_real_time_yahoo_fail_alpha_success(self, validation_service, mock_yahoo_provider, mock_alpha_vantage_provider, valid_validation_result):
        """Test real-time validation with Yahoo Finance failure, Alpha Vantage success"""
        # Setup Yahoo Finance failure
        mock_yahoo_provider.validate_symbols.return_value = ServiceResult(
            success=False,
            error="Yahoo Finance error"
        )
        
        # Setup Alpha Vantage success (fallback)
        alpha_result = valid_validation_result.model_copy(update={"provider": "alpha_vantage"})
        mock_alpha_vantage_provider.validate_symbols.return_value = ServiceResult(
            success=True,
            data={"AAPL": alpha_result}
        )

        # Execute
        result = await validation_service.validate_real_time("AAPL")

        # Assert
        assert result.success is True
        assert result.data.symbol == "AAPL"
        assert result.data.is_valid is True
        assert result.data.provider == "alpha_vantage"
        assert result.metadata["fallback_provider"] == "alpha_vantage"

    @pytest.mark.asyncio
    async def test_validate_real_time_both_providers_fail(self, validation_service, mock_yahoo_provider, mock_alpha_vantage_provider):
        """Test real-time validation when both providers fail"""
        # Setup both providers failing
        mock_yahoo_provider.validate_symbols.return_value = ServiceResult(
            success=False,
            error="Yahoo Finance error"
        )
        mock_alpha_vantage_provider.validate_symbols.return_value = ServiceResult(
            success=False,
            error="Alpha Vantage error"
        )

        # Execute
        result = await validation_service.validate_real_time("INVALID")

        # Assert
        assert result.success is False
        assert result.data.symbol == "INVALID"
        assert result.data.is_valid is False
        assert result.data.provider == "both_failed"
        assert result.metadata["attempted_providers"] == ["yahoo_finance", "alpha_vantage"]
        assert "check_symbol_spelling" in result.next_actions


class TestBulkValidation:
    """Test bulk validation operations"""

    @pytest.mark.asyncio
    async def test_validate_symbols_bulk_mixed_strategy(self, validation_service, mock_redis_client, mock_yahoo_provider, valid_validation_result):
        """Test bulk validation with mixed strategy"""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        
        # Setup cache miss for all
        mock_redis_client.get.return_value = None
        
        # Setup Yahoo Finance success for all
        yahoo_results = {}
        for symbol in symbols:
            result = valid_validation_result.model_copy(update={"symbol": symbol})
            yahoo_results[symbol] = result
        
        mock_yahoo_provider.validate_symbols.return_value = ServiceResult(
            success=True,
            data=yahoo_results
        )

        # Execute
        result = await validation_service.validate_symbols_bulk(symbols, ValidationStrategy.MIXED)

        # Assert
        assert result.success is True
        assert isinstance(result.data, BulkValidationResult)
        assert result.data.total_requested == 3
        assert result.data.successful_validations == 3
        assert result.data.failed_validations == 0
        assert result.data.pending_validations == 0
        assert len(result.data.results) == 3
        assert result.data.cache_misses == 3

    @pytest.mark.asyncio
    async def test_validate_symbols_bulk_cache_only(self, validation_service, mock_redis_client, valid_validation_result):
        """Test bulk validation with cache-only strategy"""
        symbols = ["AAPL", "GOOGL"]
        
        # Setup cache hit for AAPL, miss for GOOGL
        def cache_side_effect(key):
            if "AAPL" in key:
                cached_data = valid_validation_result.model_dump()
                cached_data['timestamp'] = cached_data['timestamp'].isoformat()
                cached_data['asset_info']['last_updated'] = cached_data['asset_info']['last_updated'].isoformat()
                return json.dumps(cached_data, default=str)
            return None
        
        mock_redis_client.get.side_effect = cache_side_effect

        # Execute
        result = await validation_service.validate_symbols_bulk(symbols, ValidationStrategy.CACHE_ONLY)

        # Assert
        assert result.success is True  # At least one cache hit
        assert result.data.successful_validations == 1  # Only AAPL found in cache
        assert result.data.failed_validations == 1  # GOOGL not in cache
        assert result.data.cache_hits == 1
        assert result.data.cache_misses == 1

    @pytest.mark.asyncio
    async def test_validate_symbols_bulk_concurrency_limit(self, validation_service, mock_yahoo_provider, valid_validation_result):
        """Test bulk validation respects concurrency limits"""
        # Create many symbols to test concurrency
        symbols = [f"STOCK{i}" for i in range(20)]
        
        # Setup Yahoo Finance success for all
        yahoo_results = {}
        for symbol in symbols:
            result = valid_validation_result.model_copy(update={"symbol": symbol})
            yahoo_results[symbol] = result
        
        mock_yahoo_provider.validate_symbols.return_value = ServiceResult(
            success=True,
            data=yahoo_results
        )

        # Execute with limited concurrency
        start_time = asyncio.get_event_loop().time()
        result = await validation_service.validate_symbols_bulk(symbols, ValidationStrategy.REAL_TIME, max_concurrent=5)
        end_time = asyncio.get_event_loop().time()

        # Assert
        assert result.success is True
        assert result.data.successful_validations == 20
        assert result.metadata["concurrent_requests"] == 5
        # Should complete reasonably quickly even with concurrency limits
        assert end_time - start_time < 10  # Less than 10 seconds


class TestCacheOperations:
    """Test cache operations"""

    @pytest.mark.asyncio
    async def test_get_cached_validation_exists(self, validation_service, mock_redis_client, valid_validation_result):
        """Test retrieving existing cached validation"""
        # Setup cached data
        cached_data = valid_validation_result.model_dump()
        cached_data['timestamp'] = cached_data['timestamp'].isoformat()
        cached_data['asset_info']['last_updated'] = cached_data['asset_info']['last_updated'].isoformat()
        mock_redis_client.get.return_value = json.dumps(cached_data, default=str)
        mock_redis_client.ttl.return_value = 1800

        # Execute
        result = await validation_service.get_cached_validation("AAPL")

        # Assert
        assert result.success is True
        assert result.data.symbol == "AAPL"
        assert result.data.is_valid is True
        assert result.metadata["cache_key"] == "asset_validation:AAPL"

    @pytest.mark.asyncio
    async def test_get_cached_validation_not_exists(self, validation_service, mock_redis_client):
        """Test retrieving non-existent cached validation"""
        # Setup cache miss
        mock_redis_client.get.return_value = None

        # Execute
        result = await validation_service.get_cached_validation("AAPL")

        # Assert
        assert result.success is False
        assert result.data is None
        assert "No cached validation found" in result.message

    @pytest.mark.asyncio
    async def test_cache_validation_result(self, validation_service, mock_redis_client, valid_validation_result):
        """Test caching validation result"""
        # Execute
        result = await validation_service.cache_validation_result("AAPL", valid_validation_result, 3600)

        # Assert
        assert result.success is True
        assert result.data is True
        assert result.metadata["ttl"] == 3600
        mock_redis_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_cache_specific_symbols(self, validation_service, mock_redis_client):
        """Test invalidating cache for specific symbols"""
        symbols = ["AAPL", "GOOGL"]
        mock_redis_client.delete.return_value = 2

        # Execute
        result = await validation_service.invalidate_cache(symbols)

        # Assert
        assert result.success is True
        assert result.data == 2
        assert result.metadata["symbols"] == symbols
        mock_redis_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_cache_all(self, validation_service, mock_redis_client):
        """Test invalidating all validation cache"""
        mock_redis_client.keys.return_value = ["asset_validation:AAPL", "asset_validation:GOOGL"]
        mock_redis_client.delete.return_value = 2

        # Execute
        result = await validation_service.invalidate_cache()

        # Assert
        assert result.success is True
        assert result.data == 2
        assert result.metadata["pattern"] == "asset_validation:*"


class TestBackgroundValidation:
    """Test background validation queue operations"""

    @pytest.mark.asyncio
    async def test_queue_background_validation(self, validation_service, mock_redis_client):
        """Test queueing symbols for background validation"""
        symbols = ["AAPL", "GOOGL"]

        # Mock Celery task (the new implementation tries Celery first)
        with patch('app.workers.asset_validation_worker.bulk_validate_assets') as mock_task:
            # Mock successful Celery task queuing
            mock_task.apply_async.return_value.id = "celery-task-123"
            
            # Execute
            result = await validation_service.queue_background_validation(symbols, user_id="test-user", priority=1)

            # Assert - Now expects Celery task ID
            assert result.success is True
            assert result.data == "celery-task-123"  # Celery task ID format
            assert result.metadata["task_type"] == "bulk_validation"
            assert result.metadata["symbols_count"] == 2
            assert result.metadata["user_id"] == "test-user"


class TestValidationStats:
    """Test validation statistics and monitoring"""

    @pytest.mark.asyncio
    async def test_get_validation_stats(self, validation_service, mock_redis_client):
        """Test getting validation performance statistics"""
        # Setup some stats
        validation_service._validation_stats.update({
            "total_requests": 100,
            "cache_hits": 60,
            "cache_misses": 40,
            "yahoo_success": 35,
            "yahoo_failures": 5,
            "alpha_vantage_success": 3,
            "alpha_vantage_failures": 2
        })

        # Execute
        result = await validation_service.get_validation_stats(24)

        # Assert
        assert result.success is True
        assert result.data["total_requests"] == 100
        assert result.data["cache_hit_ratio"] == 0.6  # 60/100
        assert result.data["yahoo_success_rate"] == 0.875  # 35/40
        assert result.data["timeframe_hours"] == 24
        assert "redis_memory_used" in result.data

    @pytest.mark.asyncio
    async def test_health_check(self, validation_service, mock_redis_client, mock_yahoo_provider, mock_alpha_vantage_provider):
        """Test service health check"""
        # Execute
        result = await validation_service.health_check()

        # Assert
        assert result.success is True
        assert result.data["service"] == "asset_validation"
        assert result.data["status"] == "healthy"
        assert result.data["redis"] == "connected"
        assert result.data["yahoo_finance"] == "healthy"
        assert result.data["alpha_vantage"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_degraded_redis(self, validation_service, mock_redis_client, mock_yahoo_provider, mock_alpha_vantage_provider):
        """Test service health check with Redis issues"""
        # Setup Redis failure
        mock_redis_client.ping.side_effect = Exception("Redis connection error")

        # Execute
        result = await validation_service.health_check()

        # Assert - Following production resilience principle, degraded state should report False
        assert result.success is False  # Degraded state with Redis failure
        assert result.data["status"] == "degraded"  # Correctly reports degraded state
        assert "error:" in result.data["redis"]


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_validate_symbol_with_redis_error(self, validation_service, mock_redis_client, mock_yahoo_provider, valid_validation_result):
        """Test validation continues when Redis fails"""
        # Setup Redis error for cache operations
        mock_redis_client.get.side_effect = Exception("Redis error")
        
        # Setup Yahoo Finance success
        mock_yahoo_provider.validate_symbols.return_value = ServiceResult(
            success=True,
            data={"AAPL": valid_validation_result}
        )

        # Execute - should handle Redis error gracefully
        result = await validation_service.validate_symbol_mixed_strategy("AAPL")

        # Should still succeed via real-time validation
        assert result.success is True
        assert result.data.symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_validate_empty_symbol_list(self, validation_service):
        """Test bulk validation with empty symbol list"""
        # Execute
        result = await validation_service.validate_symbols_bulk([])

        # Assert - Following "Never trust user input" principle, empty list should be False
        assert result.success is False  # Empty list is not a valid input
        assert result.data.total_requested == 0
        assert result.data.successful_validations == 0

    @pytest.mark.asyncio
    async def test_validate_duplicate_symbols(self, validation_service, mock_yahoo_provider, valid_validation_result):
        """Test bulk validation with duplicate symbols"""
        symbols = ["AAPL", "AAPL", "GOOGL"]
        
        # Setup Yahoo Finance success
        yahoo_results = {
            "AAPL": valid_validation_result,
            "GOOGL": valid_validation_result.model_copy(update={"symbol": "GOOGL"})
        }
        mock_yahoo_provider.validate_symbols.return_value = ServiceResult(
            success=True,
            data=yahoo_results
        )

        # Execute
        result = await validation_service.validate_symbols_bulk(symbols, ValidationStrategy.REAL_TIME)

        # Assert - should handle duplicates gracefully
        assert result.success is True
        # Total requested includes duplicates, but results should be unique
        assert result.data.total_requested == 3