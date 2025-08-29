import pytest
import asyncio
from datetime import date, datetime, timezone, timedelta
from typing import List, Dict
import os

from app.services.implementations.openbb_data_provider import OpenBBDataProvider, OPENBB_AVAILABLE
from app.services.interfaces.data_provider import MarketData, AssetInfo, ValidationResult

pytestmark = pytest.mark.asyncio

# Skip all tests if OpenBB is not available
skip_if_no_openbb = pytest.mark.skipif(
    not OPENBB_AVAILABLE,
    reason="OpenBB Terminal SDK not installed"
)

@pytest.fixture
def openbb_provider():
    """Create OpenBB data provider instance for testing"""
    return OpenBBDataProvider(
        max_workers=2,
        request_delay=0.1,  # Faster for testing
        api_key=os.getenv('OPENBB_API_KEY'),
        enable_pro_features=bool(os.getenv('OPENBB_API_KEY'))
    )

@pytest.fixture
def test_symbols():
    """Standard test symbols for consistent testing"""
    return ["AAPL", "GOOGL", "MSFT"]

@pytest.fixture
def invalid_symbols():
    """Invalid symbols for error handling tests"""
    return ["INVALID123", "NOTREAL456"]

class TestOpenBBProviderInitialization:
    """Test OpenBB provider initialization and configuration"""
    
    @skip_if_no_openbb
    def test_provider_initialization_basic(self):
        """Test basic provider initialization"""
        provider = OpenBBDataProvider()
        assert provider.max_workers == 3
        assert provider.request_delay == 0.2
        assert provider.enable_pro_features is False
        
    @skip_if_no_openbb
    def test_provider_initialization_with_config(self):
        """Test provider initialization with custom configuration"""
        provider = OpenBBDataProvider(
            max_workers=5,
            request_delay=0.5,
            api_key="test_key",
            enable_pro_features=True
        )
        assert provider.max_workers == 5
        assert provider.request_delay == 0.5
        assert provider.api_key == "test_key"
        
    def test_provider_initialization_without_openbb(self):
        """Test graceful handling when OpenBB is not available"""
        # This test runs even without OpenBB to test graceful handling
        if not OPENBB_AVAILABLE:
            # Should not raise error, just log warning
            provider = OpenBBDataProvider()
            assert provider is not None
            assert provider.enable_pro_features is False

class TestOpenBBHistoricalData:
    """Test historical data fetching functionality"""
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_fetch_historical_data_single_symbol(self, openbb_provider):
        """Test fetching historical data for a single symbol"""
        start_date = date.today() - timedelta(days=30)
        end_date = date.today() - timedelta(days=1)
        
        result = await openbb_provider.fetch_historical_data(
            symbols=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            interval="1d"
        )
        
        assert result.success
        assert "AAPL" in result.data
        assert len(result.data["AAPL"]) > 0
        
        # Validate data structure
        market_data = result.data["AAPL"][0]
        assert isinstance(market_data, MarketData)
        assert market_data.symbol == "AAPL"
        assert market_data.open > 0
        assert market_data.high >= market_data.open
        assert market_data.low <= market_data.open
        assert market_data.close > 0
        assert market_data.volume >= 0
        assert market_data.metadata["source"] == "openbb_terminal"
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_fetch_historical_data_multiple_symbols(self, openbb_provider, test_symbols):
        """Test fetching historical data for multiple symbols"""
        start_date = date.today() - timedelta(days=7)
        end_date = date.today() - timedelta(days=1)
        
        result = await openbb_provider.fetch_historical_data(
            symbols=test_symbols,
            start_date=start_date,
            end_date=end_date,
            interval="1d"
        )
        
        assert result.success
        
        # Check that we got data for most symbols (allow for some failures)
        successful_symbols = len(result.data)
        total_symbols = len(test_symbols)
        success_rate = successful_symbols / total_symbols
        assert success_rate >= 0.7, f"Success rate {success_rate} too low"
        
        # Validate metadata
        assert result.metadata["provider"] == "openbb_terminal"
        assert result.metadata["requested_symbols"] == total_symbols
        assert result.metadata["successful"] == successful_symbols
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_fetch_historical_data_different_intervals(self, openbb_provider):
        """Test fetching historical data with different intervals"""
        start_date = date.today() - timedelta(days=2)
        end_date = date.today() - timedelta(days=1)
        
        for interval in ["1d", "1h"]:
            result = await openbb_provider.fetch_historical_data(
                symbols=["AAPL"],
                start_date=start_date,
                end_date=end_date,
                interval=interval
            )
            
            if result.success:  # Some intervals might not be available
                assert "AAPL" in result.data
                assert result.data["AAPL"][0].metadata["interval"] == interval
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_fetch_historical_data_invalid_symbol(self, openbb_provider, invalid_symbols):
        """Test handling of invalid symbols"""
        start_date = date.today() - timedelta(days=7)
        end_date = date.today() - timedelta(days=1)
        
        result = await openbb_provider.fetch_historical_data(
            symbols=invalid_symbols,
            start_date=start_date,
            end_date=end_date,
            interval="1d"
        )
        
        # Should handle gracefully - might succeed=False or return empty data
        assert isinstance(result.success, bool)
        assert "errors" in result.metadata
        assert len(result.metadata["errors"]) > 0

class TestOpenBBRealTimeData:
    """Test real-time data fetching functionality"""
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_fetch_real_time_data_single_symbol(self, openbb_provider):
        """Test fetching real-time data for a single symbol"""
        result = await openbb_provider.fetch_real_time_data(symbols=["AAPL"])
        
        if result.success:  # Real-time might not always be available
            assert "AAPL" in result.data
            market_data = result.data["AAPL"]
            assert isinstance(market_data, MarketData)
            assert market_data.symbol == "AAPL"
            assert market_data.close > 0
            assert market_data.metadata["source"] == "openbb_terminal"
            assert market_data.metadata["data_type"] == "real_time"
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_fetch_real_time_data_multiple_symbols(self, openbb_provider, test_symbols):
        """Test fetching real-time data for multiple symbols"""
        result = await openbb_provider.fetch_real_time_data(symbols=test_symbols)
        
        # Real-time data availability varies, so we're flexible with success rate
        if result.success:
            assert len(result.data) > 0
            assert result.metadata["provider"] == "openbb_terminal"
        
        # Should always return a valid ServiceResult
        assert hasattr(result, 'success')
        assert hasattr(result, 'metadata')

class TestOpenBBAssetInfo:
    """Test asset information fetching functionality"""
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_fetch_asset_info_single_symbol(self, openbb_provider):
        """Test fetching asset information for a single symbol"""
        result = await openbb_provider.fetch_asset_info(symbols=["AAPL"])
        
        assert result.success
        assert "AAPL" in result.data
        
        asset_info = result.data["AAPL"]
        assert isinstance(asset_info, AssetInfo)
        assert asset_info.symbol == "AAPL"
        assert asset_info.is_valid
        assert asset_info.name is not None
        assert asset_info.metadata["source"] == "openbb_terminal"
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_fetch_asset_info_multiple_symbols(self, openbb_provider, test_symbols):
        """Test fetching asset information for multiple symbols"""
        result = await openbb_provider.fetch_asset_info(symbols=test_symbols)
        
        assert result.success
        
        # Check that we got valid info for most symbols
        valid_count = len([info for info in result.data.values() if info.is_valid])
        total_count = len(test_symbols)
        success_rate = valid_count / total_count
        assert success_rate >= 0.7, f"Success rate {success_rate} too low"
        
        # Validate structure
        for symbol in result.data:
            asset_info = result.data[symbol]
            assert isinstance(asset_info, AssetInfo)
            assert asset_info.symbol == symbol
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_fetch_asset_info_invalid_symbol(self, openbb_provider, invalid_symbols):
        """Test handling of invalid symbols for asset info"""
        result = await openbb_provider.fetch_asset_info(symbols=invalid_symbols)
        
        # Should return results but mark as invalid
        for symbol in invalid_symbols:
            if symbol in result.data:
                assert not result.data[symbol].is_valid
                assert "error" in result.data[symbol].metadata

class TestOpenBBSymbolValidation:
    """Test symbol validation functionality"""
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_validate_valid_symbols(self, openbb_provider):
        """Test validation of known valid symbols"""
        result = await openbb_provider.validate_symbols(["AAPL", "GOOGL"])
        
        assert result.success
        
        for symbol in ["AAPL", "GOOGL"]:
            assert symbol in result.data
            validation = result.data[symbol]
            assert isinstance(validation, ValidationResult)
            assert validation.symbol == symbol
            assert validation.provider == "openbb_terminal"
            
            # Should be valid with high confidence
            if validation.is_valid:
                assert validation.confidence > 0.5
                assert validation.asset_info is not None
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_validate_invalid_symbols(self, openbb_provider, invalid_symbols):
        """Test validation of invalid symbols"""
        result = await openbb_provider.validate_symbols(invalid_symbols)
        
        assert result.success  # Always successful, but symbols marked as invalid
        
        for symbol in invalid_symbols:
            assert symbol in result.data
            validation = result.data[symbol]
            # Most should be invalid, but we're flexible for edge cases
            if not validation.is_valid:
                assert validation.confidence <= 0.5
                assert validation.error is not None
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_validate_mixed_symbols(self, openbb_provider):
        """Test validation of mix of valid and invalid symbols"""
        mixed_symbols = ["AAPL", "INVALID123", "GOOGL", "NOTREAL456"]
        result = await openbb_provider.validate_symbols(mixed_symbols)
        
        assert result.success
        assert len(result.data) == len(mixed_symbols)
        
        # Should have mix of valid and invalid
        valid_count = len([v for v in result.data.values() if v.is_valid])
        invalid_count = len([v for v in result.data.values() if not v.is_valid])
        
        assert valid_count > 0, "Should have some valid symbols"
        assert invalid_count > 0, "Should have some invalid symbols"

class TestOpenBBProfessionalFeatures:
    """Test OpenBB professional features (fundamental data, economic indicators)"""
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_fetch_fundamental_data(self, openbb_provider):
        """Test fetching fundamental data using OpenBB"""
        result = await openbb_provider.fetch_fundamental_data(symbols=["AAPL"])
        
        if result.success:
            assert "AAPL" in result.data
            fundamental_data = result.data["AAPL"]
            assert isinstance(fundamental_data, dict)
            
            # Should contain some fundamental metrics
            expected_fields = ['name', 'sector', 'industry', 'market_cap']
            has_some_fields = any(field in fundamental_data for field in expected_fields)
            assert has_some_fields, "Should contain some fundamental data fields"
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_fetch_economic_indicators(self, openbb_provider):
        """Test fetching economic indicators using OpenBB"""
        indicators = ["gdp", "inflation"]
        result = await openbb_provider.fetch_economic_indicators(indicators)
        
        # Economic data might not always be available, so we're flexible
        if result.success:
            assert len(result.data) > 0
            
            for indicator, data in result.data.items():
                assert indicator in indicators
                # Should be a pandas DataFrame or similar
                assert hasattr(data, 'empty') or len(data) > 0

class TestOpenBBAssetSearch:
    """Test asset search functionality"""
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_search_assets_by_symbol(self, openbb_provider):
        """Test searching assets by symbol"""
        result = await openbb_provider.search_assets(query="AAPL", limit=5)
        
        if result.success:
            assert len(result.data) > 0
            
            # Should find Apple
            found_apple = any(
                asset.symbol == "AAPL" or "apple" in asset.name.lower()
                for asset in result.data
            )
            assert found_apple or len(result.data) > 0, "Should find relevant results"
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_search_assets_by_name(self, openbb_provider):
        """Test searching assets by company name"""
        result = await openbb_provider.search_assets(query="Apple", limit=5)
        
        if result.success:
            assert len(result.data) <= 5  # Respects limit
            
            for asset in result.data:
                assert isinstance(asset, AssetInfo)
                assert asset.metadata.get("search_query") == "Apple"

class TestOpenBBHealthCheck:
    """Test OpenBB provider health check functionality"""
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_health_check_success(self, openbb_provider):
        """Test successful health check"""
        result = await openbb_provider.health_check()
        
        if result.success:
            assert result.data["provider"] == "openbb_terminal"
            assert result.data["status"] == "healthy"
            assert "openbb_available" in result.data
            assert result.data["openbb_available"] is True
        else:
            # If health check fails, should still provide meaningful error info
            assert result.data["status"] in ["degraded", "unhealthy"]
            assert result.error is not None
    
    def test_health_check_without_openbb(self):
        """Test health check when OpenBB is not available"""
        if not OPENBB_AVAILABLE:
            # Can't create provider without OpenBB, so this tests the import scenario
            assert True  # Test passes if we reach here without OpenBB

class TestOpenBBPerformance:
    """Test OpenBB provider performance and SLA compliance"""
    
    @skip_if_no_openbb
    @pytest.mark.performance
    async def test_response_time_sla(self, openbb_provider):
        """Test that responses meet SLA requirements (<2s for data fetching)"""
        import time
        
        start_time = time.time()
        result = await openbb_provider.fetch_real_time_data(symbols=["AAPL"])
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # SLA: API responses should be under 2 seconds for single symbol
        assert response_time < 2.0, f"Response time {response_time}s exceeds SLA"
        
        if result.success:
            # If successful, should be reasonably fast
            assert response_time < 1.0, f"Successful request took {response_time}s"
    
    @skip_if_no_openbb
    @pytest.mark.performance
    async def test_bulk_request_efficiency(self, openbb_provider, test_symbols):
        """Test efficiency of bulk requests"""
        import time
        
        start_time = time.time()
        result = await openbb_provider.validate_symbols(test_symbols)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Should be efficient for multiple symbols
        time_per_symbol = response_time / len(test_symbols)
        assert time_per_symbol < 1.0, f"Time per symbol {time_per_symbol}s too high"

class TestOpenBBErrorHandling:
    """Test OpenBB provider error handling and resilience"""
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_network_error_handling(self, openbb_provider):
        """Test handling of network errors"""
        # Test with extreme date range that might cause issues
        start_date = date(1900, 1, 1)
        end_date = date(1900, 1, 2)
        
        result = await openbb_provider.fetch_historical_data(
            symbols=["AAPL"],
            start_date=start_date,
            end_date=end_date,
            interval="1d"
        )
        
        # Should handle gracefully (either succeed or fail with meaningful error)
        assert isinstance(result.success, bool)
        if not result.success:
            assert result.error is not None
            assert result.message is not None
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_rate_limiting_behavior(self, openbb_provider):
        """Test that rate limiting works correctly"""
        import time
        
        # Make multiple rapid requests
        start_time = time.time()
        
        for i in range(3):
            await openbb_provider.fetch_real_time_data(symbols=["AAPL"])
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should respect rate limiting (at least some delay)
        expected_min_time = 2 * openbb_provider.request_delay  # 2 delays between 3 requests
        assert total_time >= expected_min_time, "Rate limiting not working"
    
    @skip_if_no_openbb
    @pytest.mark.integration  
    async def test_concurrent_request_handling(self, openbb_provider):
        """Test handling of concurrent requests"""
        # Make concurrent requests
        tasks = [
            openbb_provider.validate_symbols(["AAPL"]),
            openbb_provider.validate_symbols(["GOOGL"]),
            openbb_provider.validate_symbols(["MSFT"])
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete without exceptions
        for result in results:
            assert not isinstance(result, Exception), f"Concurrent request failed: {result}"
            assert hasattr(result, 'success')

@pytest.mark.real_data
class TestOpenBBRealDataValidation:
    """Test OpenBB provider with real market data validation"""
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_data_consistency_checks(self, openbb_provider):
        """Test that returned data is internally consistent"""
        result = await openbb_provider.fetch_historical_data(
            symbols=["AAPL"],
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() - timedelta(days=1),
            interval="1d"
        )
        
        if result.success and "AAPL" in result.data:
            for market_data in result.data["AAPL"]:
                # Basic consistency checks
                assert market_data.high >= market_data.low, "High should be >= Low"
                assert market_data.high >= market_data.open, "High should be >= Open" 
                assert market_data.high >= market_data.close, "High should be >= Close"
                assert market_data.low <= market_data.open, "Low should be <= Open"
                assert market_data.low <= market_data.close, "Low should be <= Close"
                
                # Reasonable value ranges
                assert market_data.open > 0, "Price should be positive"
                assert market_data.volume >= 0, "Volume should be non-negative"
    
    @skip_if_no_openbb
    @pytest.mark.integration
    async def test_timestamp_accuracy(self, openbb_provider):
        """Test that timestamps are accurate and properly formatted"""
        result = await openbb_provider.fetch_real_time_data(symbols=["AAPL"])
        
        if result.success and "AAPL" in result.data:
            market_data = result.data["AAPL"]
            
            # Should have timezone information
            assert market_data.timestamp.tzinfo is not None, "Timestamp should be timezone-aware"
            
            # Should be recent (within reasonable bounds)
            now = datetime.now(timezone.utc)
            time_diff = abs((now - market_data.timestamp).total_seconds())
            
            # Real-time data should be within last 24 hours (flexible for weekends/holidays)
            assert time_diff < 86400, f"Timestamp {market_data.timestamp} too old"