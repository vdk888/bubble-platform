"""
Test suite for temporal cache functionality - Sprint 2.5 Part D

Tests comprehensive temporal caching with performance optimization,
cache invalidation, and enterprise-grade reliability.
"""
import pytest
import asyncio
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, patch
import os

from app.services.implementations.redis_temporal_cache import RedisTemporalCache
from app.services.interfaces.security import ITemporalCache


class TestRedisTemporalCache:
    """Test Redis-based temporal cache implementation"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client for testing"""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.smembers.return_value = set()
        mock_redis.sadd.return_value = 1
        mock_redis.expire.return_value = True
        mock_redis.keys.return_value = []
        mock_redis.info.return_value = {
            "used_memory_human": "1.5M",
            "used_memory_peak_human": "2.1M"
        }
        mock_redis.ttl.return_value = 3600
        
        return mock_redis
    
    @pytest.fixture
    def temporal_cache(self, mock_redis):
        """Create temporal cache with mocked Redis"""
        cache = RedisTemporalCache(redis_client=mock_redis)
        return cache
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, temporal_cache):
        """Test intelligent cache key generation with consistent hashing"""
        
        # Test basic timeline key
        key1 = temporal_cache._generate_cache_key(
            "timeline", 
            "universe-123",
            "2024-01-01",
            "2024-01-31"
        )
        
        key2 = temporal_cache._generate_cache_key(
            "timeline", 
            "universe-123",
            "2024-01-01", 
            "2024-01-31"
        )
        
        # Same parameters should generate same key
        assert key1 == key2
        assert "timeline" in key1
        assert "universe-123" in key1
        assert "range_" in key1
        
        # Test snapshot key
        snapshot_key = temporal_cache._generate_cache_key(
            "snapshot",
            "universe-456",
            snapshot_date="2024-01-15"
        )
        
        assert "snapshot" in snapshot_key
        assert "universe-456" in snapshot_key
        assert "params_" in snapshot_key
    
    @pytest.mark.asyncio
    async def test_data_compression_decompression(self, temporal_cache):
        """Test data compression and decompression"""
        
        test_data = {
            "snapshots": [
                {"date": "2024-01-01", "assets": ["AAPL", "GOOGL"]},
                {"date": "2024-01-02", "assets": ["AAPL", "GOOGL", "MSFT"]}
            ],
            "period_analysis": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "snapshot_count": 2
            }
        }
        
        # Test compression
        compressed = temporal_cache._compress_data(test_data)
        assert isinstance(compressed, str)
        assert len(compressed) > 0
        
        # Test decompression
        decompressed = temporal_cache._decompress_data(compressed)
        assert decompressed == test_data
        assert isinstance(decompressed["snapshots"], list)
        assert len(decompressed["snapshots"]) == 2
    
    @pytest.mark.asyncio
    async def test_timeline_cache_operations(self, temporal_cache, mock_redis):
        """Test timeline caching and retrieval"""
        
        timeline_data = {
            "snapshots": [
                {
                    "id": "snap-1",
                    "date": "2024-01-01",
                    "assets": ["AAPL", "GOOGL"],
                    "turnover_rate": 0.1
                }
            ],
            "period_analysis": {
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "average_turnover": 0.1,
                "snapshot_count": 1
            }
        }
        
        universe_id = "universe-test-123"
        start_date = "2024-01-01"
        end_date = "2024-01-31"
        
        # Test cache miss (returns None)
        cached_data = await temporal_cache.get_timeline(
            universe_id, start_date, end_date
        )
        assert cached_data is None
        assert temporal_cache._miss_count == 1
        
        # Test cache set
        result = await temporal_cache.set_timeline(
            universe_id, start_date, end_date, timeline_data, ttl_seconds=1800
        )
        assert result is True
        
        # Verify Redis was called correctly
        mock_redis.setex.assert_called()
        mock_redis.sadd.assert_called()
        mock_redis.expire.assert_called()
    
    @pytest.mark.asyncio 
    async def test_cache_hit_simulation(self, temporal_cache, mock_redis):
        """Test cache hit scenario with proper data retrieval"""
        
        cached_timeline_json = '''{"snapshots": [{"id": "snap-1", "date": "2024-01-01"}], "_cache_meta": {"cached_at": "2024-01-01T10:00:00"}}'''
        mock_redis.get.return_value = cached_timeline_json
        
        universe_id = "universe-cached-123"
        start_date = "2024-01-01"
        end_date = "2024-01-31"
        
        # Should return cached data
        cached_data = await temporal_cache.get_timeline(
            universe_id, start_date, end_date
        )
        
        assert cached_data is not None
        assert "snapshots" in cached_data
        assert "_cache_meta" in cached_data
        assert cached_data["_cache_meta"]["retrieved_at"] is not None
        assert temporal_cache._hit_count == 1
    
    @pytest.mark.asyncio
    async def test_snapshot_cache_operations(self, temporal_cache, mock_redis):
        """Test individual snapshot caching"""
        
        snapshot_data = {
            "id": "snap-123",
            "universe_id": "universe-456",
            "snapshot_date": "2024-01-15",
            "assets": ["AAPL", "GOOGL", "MSFT"],
            "turnover_rate": 0.05,
            "asset_count": 3
        }
        
        universe_id = "universe-456"
        snapshot_date = "2024-01-15"
        
        # Test snapshot cache set
        result = await temporal_cache.cache_snapshot(
            universe_id, snapshot_date, snapshot_data, ttl_seconds=3600
        )
        assert result is True
        
        # Mock cache hit for snapshot
        mock_redis.get.return_value = temporal_cache._compress_data(snapshot_data)
        
        # Test snapshot retrieval
        cached_snapshot = await temporal_cache.get_snapshot(universe_id, snapshot_date)
        assert cached_snapshot is not None
        assert cached_snapshot["id"] == "snap-123"
        assert cached_snapshot["asset_count"] == 3
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, temporal_cache, mock_redis):
        """Test universe cache invalidation"""
        
        universe_id = "universe-invalidate-test"
        
        # Mock existing cache keys
        cache_keys = [
            "bubble:temporal:timeline:universe-invalidate-test:range_abc123",
            "bubble:temporal:snapshot:universe-invalidate-test:params_def456"
        ]
        mock_redis.smembers.return_value = set(cache_keys)
        
        # Test invalidation
        result = await temporal_cache.invalidate_universe_cache(universe_id)
        assert result is True
        
        # Verify Redis delete operations
        mock_redis.delete.assert_called()
        mock_redis.smembers.assert_called()
    
    @pytest.mark.asyncio
    async def test_cache_statistics(self, temporal_cache, mock_redis):
        """Test cache performance statistics"""
        
        # Simulate some cache operations
        temporal_cache._hit_count = 15
        temporal_cache._miss_count = 5
        temporal_cache._error_count = 1
        
        # Mock Redis response
        mock_redis.keys.return_value = [
            "bubble:temporal:timeline:univ1:range_123",
            "bubble:temporal:snapshot:univ1:params_456",
            "bubble:temporal:timeline:univ2:range_789"
        ]
        
        stats = await temporal_cache.get_cache_stats()
        
        assert stats["hit_count"] == 15
        assert stats["miss_count"] == 5
        assert stats["error_count"] == 1
        assert stats["hit_rate"] == 0.75  # 15/(15+5) = 0.75
        assert stats["total_keys"] == 3
        assert "timeline" in stats["keys_by_type"]
        assert "snapshot" in stats["keys_by_type"]
        assert stats["compression_enabled"] is True
        assert "ttl_strategies" in stats
    
    @pytest.mark.asyncio
    async def test_ttl_strategies(self, temporal_cache):
        """Test different TTL strategies for different data types"""
        
        # Test default TTL strategies
        assert temporal_cache._get_ttl_for_type("timeline") == 1800  # 30 minutes
        assert temporal_cache._get_ttl_for_type("snapshot") == 3600  # 1 hour
        assert temporal_cache._get_ttl_for_type("universe_meta") == 7200  # 2 hours
        assert temporal_cache._get_ttl_for_type("screening") == 900  # 15 minutes
        assert temporal_cache._get_ttl_for_type("unknown") == 3600  # default
    
    @pytest.mark.asyncio
    async def test_cache_warming(self, temporal_cache, mock_redis):
        """Test cache warming functionality"""
        
        universe_ids = ["universe-1", "universe-2"]
        date_ranges = [
            {"start_date": "2024-01-01", "end_date": "2024-01-31"},
            {"start_date": "2024-02-01", "end_date": "2024-02-29"}
        ]
        
        # Test cache warming
        results = await temporal_cache.warm_cache(universe_ids, date_ranges)
        
        assert len(results) == 2
        assert results["universe-1"] is True
        assert results["universe-2"] is True
    
    @pytest.mark.asyncio
    async def test_error_handling(self, temporal_cache, mock_redis):
        """Test error handling and graceful degradation"""
        
        # Test Redis connection failure by forcing cache to create new connection
        # Reset the redis_client to None to force _ensure_connection to create a new one
        temporal_cache.redis_client = None
        
        # Mock redis.from_url to return our mock_redis, then make ping fail
        import redis.asyncio as redis
        from unittest.mock import patch
        
        from redis.exceptions import RedisError
        
        with patch.object(redis, 'from_url', return_value=mock_redis):
            mock_redis.ping.side_effect = RedisError("Redis connection failed")
            
            with pytest.raises(Exception, match="Failed to connect to Redis"):
                await temporal_cache._ensure_connection()
        
        # Reset for subsequent tests
        mock_redis.ping.side_effect = None
        mock_redis.ping.return_value = True
        temporal_cache.redis_client = mock_redis  # Restore working connection
        
        # Test error in get operation
        mock_redis.get.side_effect = Exception("Redis get failed")
        
        result = await temporal_cache.get_timeline("universe-error", "2024-01-01", "2024-01-31")
        assert result is None  # Should return None on error, not crash
        assert temporal_cache._error_count > 0
        
        # Reset for set operation test
        mock_redis.get.side_effect = None
        mock_redis.setex.side_effect = Exception("Redis set failed")
        
        set_result = await temporal_cache.set_timeline(
            "universe-error", "2024-01-01", "2024-01-31", {"test": "data"}
        )
        assert set_result is False  # Should return False on error
    
    @pytest.mark.asyncio
    async def test_cache_cleanup(self, temporal_cache, mock_redis):
        """Test expired key cleanup functionality"""
        
        # Mock expired keys (TTL = -2)
        mock_redis.keys.return_value = [
            "bubble:temporal:timeline:univ1:range_123",
            "bubble:temporal:snapshot:univ1:params_456"
        ]
        mock_redis.ttl.return_value = -2  # Expired
        
        expired_count = await temporal_cache.cleanup_expired_keys()
        assert expired_count == 2
        
        # Verify TTL check was called
        assert mock_redis.ttl.call_count >= 2


class TestTemporalCacheIntegration:
    """Test integration of temporal cache with universe service"""
    
    @pytest.mark.asyncio
    async def test_factory_function(self):
        """Test temporal cache factory function with custom configuration"""
        
        custom_ttl_strategies = {
            "timeline": 900,  # 15 minutes
            "snapshot": 1800,  # 30 minutes
        }
        
        # Test factory function
        from app.services.implementations.redis_temporal_cache import create_redis_temporal_cache
        
        cache = create_redis_temporal_cache(
            redis_url="redis://test:6379",
            enable_compression=False,
            custom_ttl_strategies=custom_ttl_strategies
        )
        
        assert isinstance(cache, RedisTemporalCache)
        assert cache.enable_compression is False
        assert cache.redis_url == "redis://test:6379"
        assert cache.ttl_strategies["timeline"] == 900
        assert cache.ttl_strategies["snapshot"] == 1800
    
    @pytest.mark.asyncio 
    async def test_interface_compliance(self):
        """Test that RedisTemporalCache implements ITemporalCache correctly"""
        
        # Use test Redis URL that won't affect production
        cache = RedisTemporalCache(redis_url="redis://localhost:6379/0")
        assert isinstance(cache, ITemporalCache)
        
        # Verify all interface methods exist
        assert hasattr(cache, 'get_timeline')
        assert hasattr(cache, 'set_timeline')
        assert hasattr(cache, 'invalidate_universe_cache')
        assert hasattr(cache, 'get_cache_stats')
        
        # Verify methods are async
        import asyncio
        import inspect
        assert asyncio.iscoroutinefunction(cache.get_timeline)
        assert asyncio.iscoroutinefunction(cache.set_timeline)
        assert asyncio.iscoroutinefunction(cache.invalidate_universe_cache)
        assert asyncio.iscoroutinefunction(cache.get_cache_stats)


if __name__ == "__main__":
    pytest.main([__file__])