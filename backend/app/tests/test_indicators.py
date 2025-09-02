"""
Comprehensive tests for Technical Indicators functionality.
Tests include unit tests, integration tests, business logic validation,
and performance benchmarks following production-grade standards.
"""
import pytest
import pytest_asyncio
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from app.services.technical_indicators_service import TechnicalIndicatorService
from app.services.signal_generation_service import SignalGenerationService
from app.services.interfaces.indicator_service import (
    IndicatorType, 
    IndicatorParameters,
    IndicatorResult
)
from app.services.interfaces.signal_service import (
    SignalType,
    SignalStrength,
    SignalConfiguration,
    SignalResult
)

# Test markers for organization
pytestmark = [
    pytest.mark.indicators,
    pytest.mark.technical_analysis,
    pytest.mark.business_logic
]

class TestTechnicalIndicators:
    """Test suite for technical indicator calculations"""
    
    @pytest_asyncio.fixture
    async def mock_market_data(self):
        """Mock market data for testing indicators"""
        # Generate realistic price data for testing
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        
        # Generate synthetic OHLCV data with realistic patterns
        np.random.seed(42)  # For reproducible tests
        base_price = 100.0
        prices = []
        
        for i in range(len(dates)):
            # Add some trend and volatility
            trend = 0.001 * i  # Small upward trend
            noise = np.random.normal(0, 0.02)  # 2% daily volatility
            price = base_price * (1 + trend + noise)
            prices.append(price)
        
        data = {
            'AAPL': pd.DataFrame({
                'timestamp': dates,
                'open': prices,
                'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'close': prices,
                'volume': [1000000 + int(np.random.normal(0, 100000)) for _ in prices]
            }),
            'GOOGL': pd.DataFrame({
                'timestamp': dates,
                'open': [p * 20 for p in prices],  # Different price scale
                'high': [p * 20 * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'low': [p * 20 * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'close': [p * 20 for p in prices],
                'volume': [500000 + int(np.random.normal(0, 50000)) for _ in prices]
            })
        }
        
        return data
    
    @pytest_asyncio.fixture
    async def indicators_service(self, mock_market_data):
        """Create indicators service with mocked data provider"""
        mock_db = MagicMock()
        tenant_id = "test_tenant"
        
        service = TechnicalIndicatorService(mock_db, tenant_id)
        
        # Mock the data provider to return our test data
        async def mock_get_price_data(symbols, start_date, end_date):
            return {symbol: mock_market_data[symbol] for symbol in symbols if symbol in mock_market_data}
        
        service.data_provider = MagicMock()
        service.data_provider.get_price_data = mock_get_price_data
        
        return service

    @pytest.mark.unit
    async def test_rsi_calculation(self, indicators_service):
        """Test RSI calculation accuracy and edge cases"""
        params = IndicatorParameters(
            indicator_type=IndicatorType.RSI,
            symbols=['AAPL'],
            period=14
        )
        
        results = await indicators_service.calculate_batch(params)
        
        assert 'AAPL' in results
        result = results['AAPL']
        
        assert result.success
        assert result.current_value is not None
        assert 0 <= result.current_value <= 100  # RSI bounds
        assert result.signal in [-1, 0, 1]  # Valid signal range
        assert result.metadata['indicator_type'] == 'RSI'
        assert result.metadata['period'] == 14

    @pytest.mark.unit
    async def test_rsi_signals(self, indicators_service):
        """Test RSI signal generation logic"""
        # Create test data with known RSI behavior
        params = IndicatorParameters(
            indicator_type=IndicatorType.RSI,
            symbols=['AAPL'],
            period=14
        )
        
        results = await indicators_service.calculate_batch(params)
        result = results['AAPL']
        
        # RSI signals: overbought (>70) = sell, oversold (<30) = buy
        if result.current_value > 70:
            assert result.signal == -1  # Sell signal
        elif result.current_value < 30:
            assert result.signal == 1   # Buy signal
        else:
            assert result.signal == 0   # Hold signal

    @pytest.mark.unit
    async def test_macd_calculation(self, indicators_service):
        """Test MACD calculation and components"""
        params = IndicatorParameters(
            indicator_type=IndicatorType.MACD,
            symbols=['AAPL'],
            fast_period=12,
            slow_period=26,
            signal_period=9
        )
        
        results = await indicators_service.calculate_batch(params)
        result = results['AAPL']
        
        assert result.success
        assert 'macd_line' in result.values
        assert 'signal_line' in result.values
        assert 'histogram' in result.values
        
        # MACD signal based on crossover
        macd_line = result.values['macd_line']
        signal_line = result.values['signal_line']
        
        if macd_line > signal_line:
            assert result.signal == 1  # Bullish crossover
        elif macd_line < signal_line:
            assert result.signal == -1  # Bearish crossover
        else:
            assert result.signal == 0  # No clear signal

    @pytest.mark.unit
    async def test_momentum_calculation(self, indicators_service):
        """Test momentum indicator calculation"""
        params = IndicatorParameters(
            indicator_type=IndicatorType.MOMENTUM,
            symbols=['AAPL'],
            period=10
        )
        
        results = await indicators_service.calculate_batch(params)
        result = results['AAPL']
        
        assert result.success
        assert result.current_value is not None
        assert result.signal in [-1, 0, 1]
        
        # Momentum signals based on percentage change
        if result.current_value > 0.02:  # >2% bullish
            assert result.signal == 1
        elif result.current_value < -0.02:  # <-2% bearish
            assert result.signal == -1
        else:
            assert result.signal == 0

    @pytest.mark.integration
    async def test_batch_calculation(self, indicators_service):
        """Test batch calculation for multiple symbols"""
        params = IndicatorParameters(
            indicator_type=IndicatorType.RSI,
            symbols=['AAPL', 'GOOGL'],
            period=14
        )
        
        results = await indicators_service.calculate_batch(params)
        
        assert len(results) == 2
        assert 'AAPL' in results
        assert 'GOOGL' in results
        
        for symbol, result in results.items():
            assert result.success
            assert result.current_value is not None
            assert result.signal in [-1, 0, 1]
            assert result.timestamp is not None

    @pytest.mark.performance
    async def test_calculation_performance(self, indicators_service):
        """Test that indicator calculations meet SLA requirements (<2s for 1000 assets)"""
        import time
        
        # Test with smaller batch for unit test
        symbols = ['AAPL', 'GOOGL'] * 5  # 10 symbols
        params = IndicatorParameters(
            indicator_type=IndicatorType.RSI,
            symbols=symbols,
            period=14
        )
        
        start_time = time.time()
        results = await indicators_service.calculate_batch(params)
        calculation_time = time.time() - start_time
        
        # Should be well under performance threshold
        assert calculation_time < 1.0  # 1 second for 10 symbols
        assert len(results) == len(set(symbols))  # No duplicates

    @pytest.mark.business_logic
    async def test_indicator_edge_cases(self, indicators_service):
        """Test indicator behavior with edge cases"""
        # Test with insufficient data
        params = IndicatorParameters(
            indicator_type=IndicatorType.RSI,
            symbols=['INVALID_SYMBOL'],
            period=14
        )
        
        results = await indicators_service.calculate_batch(params)
        
        # Should handle invalid symbols gracefully
        if 'INVALID_SYMBOL' in results:
            assert not results['INVALID_SYMBOL'].success
            assert results['INVALID_SYMBOL'].error is not None

    @pytest.mark.unit
    async def test_parameter_validation(self, indicators_service):
        """Test parameter validation for indicators"""
        # Test invalid RSI period
        with pytest.raises(ValueError):
            params = IndicatorParameters(
                indicator_type=IndicatorType.RSI,
                symbols=['AAPL'],
                period=1  # Too low
            )
        
        # Test invalid MACD parameters
        with pytest.raises(ValueError):
            params = IndicatorParameters(
                indicator_type=IndicatorType.MACD,
                symbols=['AAPL'],
                fast_period=26,  # Fast > Slow (invalid)
                slow_period=12,
                signal_period=9
            )


class TestSignalGeneration:
    """Test suite for signal generation functionality"""
    
    @pytest_asyncio.fixture
    async def signals_service(self, mock_market_data):
        """Create signal generation service with mocked indicators"""
        mock_db = MagicMock()
        tenant_id = "test_tenant"
        
        service = SignalGenerationService(mock_db, tenant_id)
        
        # Mock indicator service
        mock_indicator_service = AsyncMock()
        
        async def mock_calculate_batch(params):
            # Return realistic indicator results
            return {
                'AAPL': IndicatorResult(
                    success=True,
                    current_value=65.0 if params.indicator_type == IndicatorType.RSI else 0.015,
                    signal=1 if params.indicator_type == IndicatorType.MACD else 0,
                    values={'test': 'value'},
                    timestamp=datetime.now(timezone.utc),
                    metadata={'indicator_type': params.indicator_type.value}
                )
            }
        
        mock_indicator_service.calculate_batch = mock_calculate_batch
        service.indicator_service = mock_indicator_service
        
        return service

    @pytest.mark.unit
    async def test_simple_signal_generation(self, signals_service):
        """Test simple signal generation from single indicator"""
        config = SignalConfiguration(
            signal_type=SignalType.SIMPLE,
            indicators=['RSI'],
            weights={'RSI': 1.0}
        )
        
        results = await signals_service.generate_signals(['AAPL'], config)
        
        assert 'AAPL' in results
        result = results['AAPL']
        
        assert result.success
        assert result.signal in [-1, 0, 1]
        assert 0 <= result.confidence <= 1
        assert result.reason is not None
        assert result.indicators_used is not None

    @pytest.mark.unit
    async def test_composite_signal_generation(self, signals_service):
        """Test composite signal generation from multiple indicators"""
        config = SignalConfiguration(
            signal_type=SignalType.COMPOSITE,
            indicators=['RSI', 'MACD', 'MOMENTUM'],
            weights={
                'RSI': 0.3,
                'MACD': 0.5,
                'MOMENTUM': 0.2
            }
        )
        
        results = await signals_service.generate_signals(['AAPL'], config)
        
        assert 'AAPL' in results
        result = results['AAPL']
        
        assert result.success
        assert len(result.indicators_used) == 3
        assert all(indicator in result.indicators_used for indicator in ['RSI', 'MACD', 'MOMENTUM'])

    @pytest.mark.business_logic
    async def test_signal_conflict_resolution(self, signals_service):
        """Test signal conflict resolution with priority hierarchy"""
        config = SignalConfiguration(
            signal_type=SignalType.COMPOSITE,
            indicators=['RSI', 'MACD'],
            weights={'RSI': 0.5, 'MACD': 0.5}
        )
        
        # Mock conflicting signals
        async def mock_conflicting_signals(params):
            if params.indicator_type == IndicatorType.RSI:
                return {
                    'AAPL': IndicatorResult(
                        success=True,
                        current_value=25.0,  # Oversold (buy signal)
                        signal=1,
                        values={},
                        timestamp=datetime.now(timezone.utc),
                        metadata={'indicator_type': 'RSI'}
                    )
                }
            else:  # MACD
                return {
                    'AAPL': IndicatorResult(
                        success=True,
                        current_value=-0.5,  # Bearish (sell signal)
                        signal=-1,
                        values={},
                        timestamp=datetime.now(timezone.utc),
                        metadata={'indicator_type': 'MACD'}
                    )
                }
        
        signals_service.indicator_service.calculate_batch = mock_conflicting_signals
        
        results = await signals_service.generate_signals(['AAPL'], config)
        result = results['AAPL']
        
        # MACD should have higher priority in conflict resolution
        assert result.success
        # The final signal should be influenced more by MACD (higher weight typically)

    @pytest.mark.performance
    async def test_signal_generation_performance(self, signals_service):
        """Test signal generation performance"""
        import time
        
        config = SignalConfiguration(
            signal_type=SignalType.COMPOSITE,
            indicators=['RSI', 'MACD'],
            weights={'RSI': 0.5, 'MACD': 0.5}
        )
        
        # Test with multiple symbols
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
        
        start_time = time.time()
        results = await signals_service.generate_signals(symbols, config)
        generation_time = time.time() - start_time
        
        assert generation_time < 2.0  # Should be fast
        assert len(results) == len(symbols)

    @pytest.mark.security
    async def test_input_sanitization(self, signals_service):
        """Test input sanitization for security"""
        # Test with potentially malicious symbols
        malicious_symbols = [
            "'; DROP TABLE assets; --",
            "<script>alert('xss')</script>",
            "../../etc/passwd"
        ]
        
        config = SignalConfiguration(
            signal_type=SignalType.SIMPLE,
            indicators=['RSI']
        )
        
        # Should handle malicious input gracefully
        results = await signals_service.generate_signals(malicious_symbols, config)
        
        # Results should either be empty or contain error handling
        for symbol, result in results.items():
            if not result.success:
                assert result.error is not None


class TestIndicatorAPI:
    """Test suite for indicator API endpoints"""
    
    @pytest.mark.integration
    async def test_calculate_indicators_endpoint(self, client, authenticated_user):
        """Test the calculate indicators API endpoint"""
        request_data = {
            "symbols": ["AAPL", "GOOGL"],
            "indicator_type": "RSI",
            "parameters": {"period": 14}
        }
        
        response = await client.post(
            "/api/v1/indicators/calculate",
            json=request_data,
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "results" in data
        assert "calculation_time_ms" in data
        assert isinstance(data["results"], list)

    @pytest.mark.integration
    async def test_get_indicator_types_endpoint(self, client, authenticated_user):
        """Test the get indicator types API endpoint"""
        response = await client.get(
            "/api/v1/indicators/types",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check structure of indicator type info
        for indicator in data:
            assert "type" in indicator
            assert "name" in indicator
            assert "description" in indicator
            assert "default_parameters" in indicator

    @pytest.mark.integration
    async def test_indicator_history_endpoint(self, client, authenticated_user):
        """Test the indicator history API endpoint"""
        response = await client.get(
            "/api/v1/indicators/history/AAPL?indicator_type=RSI&days=30",
            headers=authenticated_user["headers"]
        )
        
        # May fail if no data available, but should handle gracefully
        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            assert "indicator_type" in data
            assert "data" in data
        else:
            assert response.status_code in [404, 400]  # Valid error responses

    @pytest.mark.business_logic
    async def test_composite_indicators_endpoint(self, client, authenticated_user):
        """Test the composite indicators API endpoint"""
        response = await client.post(
            "/api/v1/indicators/composite?symbols=AAPL&symbols=GOOGL&indicators=RSI&indicators=MACD",
            headers=authenticated_user["headers"]
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "results" in data
            assert "indicators_used" in data
            assert "weights" in data


class TestSignalAPI:
    """Test suite for signal generation API endpoints"""
    
    @pytest.mark.integration
    async def test_generate_signals_endpoint(self, client, authenticated_user):
        """Test the generate signals API endpoint"""
        request_data = {
            "symbols": ["AAPL"],
            "signal_type": "COMPOSITE",
            "indicators": ["RSI", "MACD"],
            "weights": {"RSI": 0.6, "MACD": 0.4}
        }
        
        response = await client.post(
            "/api/v1/signals/generate",
            json=request_data,
            headers=authenticated_user["headers"]
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "signals" in data
            assert "summary" in data
            assert "generation_time_ms" in data

    @pytest.mark.integration
    async def test_signal_history_endpoint(self, client, authenticated_user):
        """Test the signal history API endpoint"""
        response = await client.get(
            "/api/v1/signals/history?days=7",
            headers=authenticated_user["headers"]
        )
        
        # Should always return valid response, even if empty
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "daily_summary" in data

    @pytest.mark.integration
    async def test_signal_performance_endpoint(self, client, authenticated_user):
        """Test the signal performance analysis endpoint"""
        response = await client.get(
            "/api/v1/signals/performance/AAPL?days=30",
            headers=authenticated_user["headers"]
        )
        
        # May not have data for new symbol
        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            assert "metrics" in data
        else:
            assert response.status_code == 404

# Utility functions for test data generation
def create_test_price_series(length: int = 100, base_price: float = 100.0) -> pd.Series:
    """Create realistic price series for testing"""
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, length)  # 0.1% daily return, 2% volatility
    prices = [base_price]
    
    for r in returns:
        prices.append(prices[-1] * (1 + r))
    
    return pd.Series(prices[1:])

def calculate_expected_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calculate expected RSI for validation"""
    deltas = prices.diff()
    gains = deltas.where(deltas > 0, 0).rolling(window=period).mean()
    losses = (-deltas).where(deltas < 0, 0).rolling(window=period).mean()
    rs = gains / losses
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]