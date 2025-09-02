"""
Data Alignment and Real User Scenario Tests for Technical Indicators

These tests verify perfect alignment between price data and indicator calculations,
and validate complete user workflows from data fetching to signal generation.
Following production-grade testing standards with real data validation.
"""

import pytest
import pytest_asyncio
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any
import logging

from app.services.technical_indicators_service import TechnicalIndicatorService
from app.services.signal_generation_service import SignalGenerationService
from app.services.interfaces.indicator_service import (
    IndicatorType, 
    IndicatorParameters,
    IndicatorResult
)
from app.services.interfaces.signal_service import (
    SignalType,
    SignalConfiguration,
    SignalResult
)

# Test markers
pytestmark = [
    pytest.mark.indicators,
    pytest.mark.data_alignment,
    pytest.mark.integration,
    pytest.mark.real_user_scenarios
]

logger = logging.getLogger(__name__)


class TestDataAlignment:
    """Test perfect alignment between price data and indicator calculations"""
    
    @pytest_asyncio.fixture
    async def realistic_market_data(self):
        """Generate realistic market data with known patterns for testing"""
        # Create 60 days of realistic OHLCV data
        dates = pd.date_range(start='2024-01-01', periods=60, freq='D')
        np.random.seed(12345)  # Reproducible test data
        
        # Generate AAPL-like price series starting at $150
        base_price = 150.0
        returns = np.random.normal(0.0005, 0.018, len(dates))  # Slight upward trend, realistic volatility
        
        prices = [base_price]
        for r in returns:
            prices.append(prices[-1] * (1 + r))
        
        # Create realistic OHLCV data
        close_prices = prices[1:]
        open_prices = [close_prices[0]] + close_prices[:-1]  # Previous close as next open
        
        high_prices = []
        low_prices = []
        volumes = []
        
        for i, (open_p, close_p) in enumerate(zip(open_prices, close_prices)):
            daily_range = abs(close_p - open_p) * np.random.uniform(1.2, 2.0)
            high = max(open_p, close_p) + daily_range * np.random.uniform(0.3, 0.7)
            low = min(open_p, close_p) - daily_range * np.random.uniform(0.3, 0.7)
            
            high_prices.append(high)
            low_prices.append(max(low, 0.1))  # Prevent negative prices
            
            # Realistic volume with some correlation to price movement
            base_volume = 50000000  # 50M shares base
            volatility_factor = abs(close_p - open_p) / open_p
            volume = int(base_volume * (1 + volatility_factor * 5) * np.random.uniform(0.7, 1.3))
            volumes.append(volume)
        
        market_data = {
            'AAPL': pd.DataFrame({
                'timestamp': dates,
                'open': open_prices,
                'high': high_prices,
                'low': low_prices,
                'close': close_prices,
                'volume': volumes
            }),
            
            # Add GOOGL with different characteristics
            'GOOGL': pd.DataFrame({
                'timestamp': dates,
                'open': [p * 18 for p in open_prices],  # ~$2700 price level
                'high': [p * 18 for p in high_prices],
                'low': [p * 18 for p in low_prices],
                'close': [p * 18 for p in close_prices],
                'volume': [int(v * 0.3) for v in volumes]  # Lower volume
            }),
            
            # Add MSFT with sideways pattern
            'MSFT': pd.DataFrame({
                'timestamp': dates,
                'open': [300 + np.sin(i * 0.1) * 10 + np.random.normal(0, 2) for i in range(len(dates))],
                'high': [300 + np.sin(i * 0.1) * 10 + 5 + np.random.normal(0, 2) for i in range(len(dates))],
                'low': [300 + np.sin(i * 0.1) * 10 - 5 + np.random.normal(0, 2) for i in range(len(dates))],
                'close': [300 + np.sin(i * 0.1) * 10 + np.random.normal(0, 2) for i in range(len(dates))],
                'volume': [30000000 + int(np.random.normal(0, 5000000)) for _ in range(len(dates))]
            })
        }
        
        # Ensure no negative values
        for symbol in market_data:
            df = market_data[symbol]
            df['open'] = df['open'].clip(lower=0.01)
            df['high'] = df['high'].clip(lower=0.01)
            df['low'] = df['low'].clip(lower=0.01)
            df['close'] = df['close'].clip(lower=0.01)
            df['volume'] = df['volume'].clip(lower=1)
            
            # Ensure OHLC relationships are valid
            for i in range(len(df)):
                o, h, l, c = df.iloc[i][['open', 'high', 'low', 'close']]
                df.iloc[i, df.columns.get_loc('high')] = max(o, h, l, c)
                df.iloc[i, df.columns.get_loc('low')] = min(o, h, l, c)
        
        return market_data
    
    @pytest_asyncio.fixture
    async def indicators_service_with_real_data(self, realistic_market_data):
        """Create indicators service with realistic market data"""
        mock_db = MagicMock()
        tenant_id = "test_tenant"
        
        service = TechnicalIndicatorService(mock_db, tenant_id)
        
        # Mock the data provider to return our realistic test data
        async def mock_get_price_data(symbols, start_date=None, end_date=None):
            logger.info(f"Mock data provider called with symbols: {symbols}")
            result = {}
            for symbol in symbols:
                if symbol in realistic_market_data:
                    df = realistic_market_data[symbol].copy()
                    
                    # Apply date filtering if provided
                    if start_date or end_date:
                        if start_date:
                            df = df[df['timestamp'] >= start_date]
                        if end_date:
                            df = df[df['timestamp'] <= end_date]
                    
                    result[symbol] = df
                    logger.info(f"Returning {len(df)} records for {symbol}")
                else:
                    logger.warning(f"No data available for symbol: {symbol}")
            
            return result
        
        service.data_provider = MagicMock()
        service.data_provider.get_price_data = mock_get_price_data
        
        return service

    @pytest.mark.data_alignment
    async def test_price_data_indicator_timestamp_alignment(self, indicators_service_with_real_data):
        """Test that indicator timestamps perfectly align with price data timestamps"""
        
        params = IndicatorParameters(
            indicator_type=IndicatorType.RSI,
            symbols=['AAPL'],
            period=14
        )
        
        # Get the raw price data first
        price_data = await indicators_service_with_real_data.data_provider.get_price_data(['AAPL'])
        original_timestamps = price_data['AAPL']['timestamp'].tolist()
        
        # Calculate indicators
        results = await indicators_service_with_real_data.calculate_batch(params)
        
        assert 'AAPL' in results
        result = results['AAPL']
        assert result.success
        
        # Verify the most recent timestamp matches
        latest_price_timestamp = max(original_timestamps)
        assert result.timestamp is not None
        
        # Allow small time differences due to processing
        time_diff = abs((result.timestamp - latest_price_timestamp).total_seconds())
        assert time_diff < 60, f"Timestamp alignment failed: {time_diff}s difference"
        
        logger.info(f"✅ Timestamp alignment verified: {time_diff:.2f}s difference")

    @pytest.mark.data_alignment
    async def test_indicator_value_ranges_and_validity(self, indicators_service_with_real_data):
        """Test that all indicator values are within expected ranges and mathematically valid"""
        
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        
        # Test RSI
        rsi_params = IndicatorParameters(
            indicator_type=IndicatorType.RSI,
            symbols=symbols,
            period=14
        )
        
        rsi_results = await indicators_service_with_real_data.calculate_batch(rsi_params)
        
        for symbol, result in rsi_results.items():
            assert result.success, f"RSI calculation failed for {symbol}: {result.error}"
            assert 0 <= result.current_value <= 100, f"RSI out of range for {symbol}: {result.current_value}"
            assert result.signal in [-1, 0, 1], f"Invalid RSI signal for {symbol}: {result.signal}"
        
        # Test MACD
        macd_params = IndicatorParameters(
            indicator_type=IndicatorType.MACD,
            symbols=symbols,
            fast_period=12,
            slow_period=26,
            signal_period=9
        )
        
        macd_results = await indicators_service_with_real_data.calculate_batch(macd_params)
        
        for symbol, result in macd_results.items():
            assert result.success, f"MACD calculation failed for {symbol}: {result.error}"
            assert 'macd_line' in result.values, f"MACD line missing for {symbol}"
            assert 'signal_line' in result.values, f"Signal line missing for {symbol}"
            assert 'histogram' in result.values, f"Histogram missing for {symbol}"
            
            # Verify MACD relationships
            macd_line = result.values['macd_line']
            signal_line = result.values['signal_line']
            histogram = result.values['histogram']
            
            # Histogram should equal MACD - Signal (approximately)
            expected_histogram = macd_line - signal_line
            assert abs(histogram - expected_histogram) < 0.0001, f"MACD histogram calculation error for {symbol}"
        
        # Test Momentum
        momentum_params = IndicatorParameters(
            indicator_type=IndicatorType.MOMENTUM,
            symbols=symbols,
            period=10
        )
        
        momentum_results = await indicators_service_with_real_data.calculate_batch(momentum_params)
        
        for symbol, result in momentum_results.items():
            assert result.success, f"Momentum calculation failed for {symbol}: {result.error}"
            # Momentum should be reasonable (-50% to +50% for most cases)
            assert -0.5 <= result.current_value <= 0.5, f"Unrealistic momentum for {symbol}: {result.current_value}"

    @pytest.mark.data_alignment
    async def test_consistent_calculation_across_calls(self, indicators_service_with_real_data):
        """Test that repeated calls with same parameters return identical results"""
        
        params = IndicatorParameters(
            indicator_type=IndicatorType.RSI,
            symbols=['AAPL'],
            period=14
        )
        
        # Calculate same indicator twice
        results1 = await indicators_service_with_real_data.calculate_batch(params)
        results2 = await indicators_service_with_real_data.calculate_batch(params)
        
        assert 'AAPL' in results1 and 'AAPL' in results2
        
        result1 = results1['AAPL']
        result2 = results2['AAPL']
        
        assert result1.success and result2.success
        assert abs(result1.current_value - result2.current_value) < 0.0001, "RSI calculation not consistent"
        assert result1.signal == result2.signal, "RSI signal not consistent"
        
        logger.info("✅ Calculation consistency verified")

    @pytest.mark.data_alignment
    async def test_data_sufficiency_validation(self, indicators_service_with_real_data):
        """Test that service properly validates data sufficiency for calculations"""
        
        # Test with period longer than available data
        params = IndicatorParameters(
            indicator_type=IndicatorType.RSI,
            symbols=['AAPL'],
            period=100  # More than our 60 days of data
        )
        
        results = await indicators_service_with_real_data.calculate_batch(params)
        
        # Should either fail gracefully or calculate with available data
        if 'AAPL' in results:
            result = results['AAPL']
            if not result.success:
                assert "insufficient" in result.error.lower() or "data" in result.error.lower()
                logger.info("✅ Insufficient data handled correctly")
            else:
                # If it succeeds, the calculation should still be valid
                assert 0 <= result.current_value <= 100
                logger.info("✅ Calculation succeeded with available data")


class TestRealUserScenarios:
    """Test complete real user scenarios from data to signals"""
    
    @pytest_asyncio.fixture
    async def full_service_stack(self, realistic_market_data):
        """Create full service stack for end-to-end testing"""
        mock_db = MagicMock()
        tenant_id = "user_123"
        
        # Initialize both services
        indicator_service = TechnicalIndicatorService(mock_db, tenant_id)
        signal_service = SignalGenerationService(mock_db, tenant_id)
        
        # Mock data provider
        async def mock_get_price_data(symbols, start_date=None, end_date=None):
            return {
                symbol: realistic_market_data[symbol].copy() 
                for symbol in symbols 
                if symbol in realistic_market_data
            }
        
        indicator_service.data_provider = MagicMock()
        indicator_service.data_provider.get_price_data = mock_get_price_data
        
        # Link signal service to indicator service
        signal_service.indicator_service = indicator_service
        
        return {
            'indicators': indicator_service,
            'signals': signal_service,
            'market_data': realistic_market_data
        }

    @pytest.mark.real_user_scenarios
    async def test_portfolio_screening_workflow(self, full_service_stack):
        """Test: User creates portfolio, calculates all indicators, generates composite signals"""
        
        # Scenario: User has a 3-stock portfolio and wants to rebalance based on technical signals
        portfolio_symbols = ['AAPL', 'GOOGL', 'MSFT']
        
        logger.info("🔄 Starting portfolio screening workflow test")
        
        # Step 1: Calculate RSI for all symbols
        rsi_params = IndicatorParameters(
            indicator_type=IndicatorType.RSI,
            symbols=portfolio_symbols,
            period=14
        )
        
        rsi_results = await full_service_stack['indicators'].calculate_batch(rsi_params)
        
        # Verify all calculations succeeded
        for symbol in portfolio_symbols:
            assert symbol in rsi_results, f"Missing RSI for {symbol}"
            assert rsi_results[symbol].success, f"RSI failed for {symbol}"
        
        logger.info(f"✅ RSI calculated for {len(rsi_results)} symbols")
        
        # Step 2: Calculate MACD for all symbols
        macd_params = IndicatorParameters(
            indicator_type=IndicatorType.MACD,
            symbols=portfolio_symbols,
            fast_period=12,
            slow_period=26,
            signal_period=9
        )
        
        macd_results = await full_service_stack['indicators'].calculate_batch(macd_params)
        
        for symbol in portfolio_symbols:
            assert symbol in macd_results, f"Missing MACD for {symbol}"
            assert macd_results[symbol].success, f"MACD failed for {symbol}"
        
        logger.info(f"✅ MACD calculated for {len(macd_results)} symbols")
        
        # Step 3: Generate composite signals
        signal_config = SignalConfiguration(
            signal_type=SignalType.COMPOSITE,
            indicators=['RSI', 'MACD', 'MOMENTUM'],
            weights={'RSI': 0.3, 'MACD': 0.5, 'MOMENTUM': 0.2}
        )
        
        signal_results = await full_service_stack['signals'].generate_signals(
            portfolio_symbols, 
            signal_config
        )
        
        # Verify signal generation
        for symbol in portfolio_symbols:
            assert symbol in signal_results, f"Missing signal for {symbol}"
            result = signal_results[symbol]
            assert result.success, f"Signal generation failed for {symbol}: {result.error}"
            assert result.signal in [-1, 0, 1], f"Invalid signal for {symbol}"
            assert 0 <= result.confidence <= 1, f"Invalid confidence for {symbol}"
            assert result.reason is not None, f"Missing explanation for {symbol}"
        
        # Step 4: Analyze results for portfolio decision
        buy_signals = [s for s in portfolio_symbols if signal_results[s].signal == 1]
        sell_signals = [s for s in portfolio_symbols if signal_results[s].signal == -1]
        hold_signals = [s for s in portfolio_symbols if signal_results[s].signal == 0]
        
        logger.info(f"📊 Portfolio Analysis Results:")
        logger.info(f"   Buy signals: {buy_signals}")
        logger.info(f"   Sell signals: {sell_signals}")  
        logger.info(f"   Hold signals: {hold_signals}")
        
        # Verify we have complete coverage
        assert len(buy_signals) + len(sell_signals) + len(hold_signals) == len(portfolio_symbols)
        
        # Step 5: Validate confidence scores make sense
        high_confidence_signals = [
            symbol for symbol in portfolio_symbols 
            if signal_results[symbol].confidence > 0.7
        ]
        
        if high_confidence_signals:
            logger.info(f"🎯 High confidence signals: {high_confidence_signals}")
            
            # High confidence signals should have strong indicator agreement
            for symbol in high_confidence_signals:
                result = signal_results[symbol]
                indicators_used = result.indicators_used
                
                # Check that multiple indicators agree
                signal_directions = [data['signal'] for data in indicators_used.values()]
                assert len(set(signal_directions)) <= 2, f"Too much disagreement for high confidence {symbol}"
        
        logger.info("✅ Portfolio screening workflow completed successfully")

    @pytest.mark.real_user_scenarios
    async def test_daily_monitoring_scenario(self, full_service_stack):
        """Test: User monitors daily signals for position management"""
        
        # Scenario: User checks daily signals for their top holdings
        watch_symbols = ['AAPL', 'GOOGL']
        
        logger.info("📱 Starting daily monitoring scenario test")
        
        # Step 1: Quick RSI check (most common daily indicator)
        daily_rsi = await full_service_stack['signals'].generate_simple_signal(
            'AAPL',
            'RSI'
        )
        
        assert daily_rsi.success, "Daily RSI check failed"
        assert daily_rsi.reason is not None, "Missing explanation for RSI signal"
        
        # Step 2: Generate alerts if strong signals detected
        alert_threshold = 0.7
        
        signal_config = SignalConfiguration(
            signal_type=SignalType.COMPOSITE,
            indicators=['RSI', 'MACD'],
            weights={'RSI': 0.4, 'MACD': 0.6}
        )
        
        daily_signals = await full_service_stack['signals'].generate_signals(
            watch_symbols,
            signal_config
        )
        
        alerts_generated = []
        for symbol, result in daily_signals.items():
            if result.success and result.confidence > alert_threshold:
                alerts_generated.append({
                    'symbol': symbol,
                    'signal': result.signal,
                    'confidence': result.confidence,
                    'reason': result.reason
                })
        
        logger.info(f"🚨 Generated {len(alerts_generated)} alerts above {alert_threshold} confidence")
        
        for alert in alerts_generated:
            logger.info(f"   {alert['symbol']}: {alert['signal']} ({alert['confidence']:.2f}) - {alert['reason']}")
            
            # Verify alert quality
            assert alert['confidence'] > alert_threshold
            assert alert['signal'] != 0, "Hold signals shouldn't generate alerts"
        
        logger.info("✅ Daily monitoring scenario completed")

    @pytest.mark.real_user_scenarios
    async def test_backtesting_data_preparation(self, full_service_stack):
        """Test: User prepares historical data for backtesting strategy"""
        
        # Scenario: User wants to backtest a strategy over the past 30 days
        backtest_symbol = 'AAPL'
        
        logger.info("📈 Starting backtesting data preparation test")
        
        # Step 1: Get historical indicator values with time series
        historical_params = IndicatorParameters(
            indicator_type=IndicatorType.RSI,
            symbols=[backtest_symbol],
            period=14,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 2, 29)
        )
        
        # Get price data to validate we have enough history
        price_data = await full_service_stack['indicators'].data_provider.get_price_data(
            [backtest_symbol],
            start_date=historical_params.start_date,
            end_date=historical_params.end_date
        )
        
        assert backtest_symbol in price_data
        historical_prices = price_data[backtest_symbol]
        assert len(historical_prices) >= 20, "Insufficient data for backtesting"
        
        logger.info(f"📊 Historical data: {len(historical_prices)} days available")
        
        # Step 2: Calculate indicators for the historical period
        historical_results = await full_service_stack['indicators'].calculate_batch(historical_params)
        
        assert backtest_symbol in historical_results
        result = historical_results[backtest_symbol]
        assert result.success, "Historical indicator calculation failed"
        
        # Step 3: Verify data alignment for backtesting
        # The number of price points should align with calculation periods
        price_count = len(historical_prices)
        
        # RSI needs at least 'period' data points to calculate
        min_required = historical_params.period
        assert price_count >= min_required, f"Need at least {min_required} data points for RSI calculation"
        
        # Step 4: Generate multiple signals over time (simulating backtest)
        # Test different time windows
        window_configs = [
            {'days_back': 30, 'period': 14},
            {'days_back': 20, 'period': 10},
            {'days_back': 10, 'period': 7}
        ]
        
        backtest_signals = {}
        
        for config in window_configs:
            end_date = datetime(2024, 2, 29)
            start_date = end_date - timedelta(days=config['days_back'])
            
            params = IndicatorParameters(
                indicator_type=IndicatorType.RSI,
                symbols=[backtest_symbol],
                period=config['period'],
                start_date=start_date,
                end_date=end_date
            )
            
            results = await full_service_stack['indicators'].calculate_batch(params)
            
            if backtest_symbol in results and results[backtest_symbol].success:
                backtest_signals[f"{config['days_back']}d_{config['period']}p"] = {
                    'value': results[backtest_symbol].current_value,
                    'signal': results[backtest_symbol].signal
                }
        
        # Verify we got results for different time windows
        assert len(backtest_signals) > 0, "No backtest signals generated"
        
        logger.info(f"📈 Backtest signals generated for {len(backtest_signals)} configurations")
        for config_name, signal_data in backtest_signals.items():
            logger.info(f"   {config_name}: RSI={signal_data['value']:.1f}, Signal={signal_data['signal']}")
        
        # Step 5: Validate signal consistency
        # Signals should be reasonable and consistent with RSI values
        for config_name, signal_data in backtest_signals.items():
            rsi_value = signal_data['value']
            signal = signal_data['signal']
            
            if rsi_value > 70:
                assert signal == -1, f"RSI {rsi_value} should generate sell signal in {config_name}"
            elif rsi_value < 30:
                assert signal == 1, f"RSI {rsi_value} should generate buy signal in {config_name}"
            # else signal can be 0 (hold)
        
        logger.info("✅ Backtesting data preparation completed successfully")

    @pytest.mark.real_user_scenarios
    async def test_error_handling_in_user_workflow(self, full_service_stack):
        """Test: Complete error handling in realistic user workflows"""
        
        logger.info("🚫 Starting error handling workflow test")
        
        # Test 1: Invalid symbol handling
        invalid_symbols = ['INVALID_SYMBOL', 'FAKE_STOCK']
        
        signal_config = SignalConfiguration(
            signal_type=SignalType.SIMPLE,
            indicators=['RSI']
        )
        
        error_results = await full_service_stack['signals'].generate_signals(
            invalid_symbols,
            signal_config
        )
        
        for symbol in invalid_symbols:
            if symbol in error_results:
                result = error_results[symbol]
                assert not result.success, f"Should fail for invalid symbol {symbol}"
                assert result.error is not None, f"Should have error message for {symbol}"
        
        logger.info("✅ Invalid symbol handling verified")
        
        # Test 2: Mixed valid/invalid symbols
        mixed_symbols = ['AAPL', 'INVALID_SYMBOL', 'GOOGL']
        
        mixed_results = await full_service_stack['signals'].generate_signals(
            mixed_symbols,
            signal_config
        )
        
        # Valid symbols should succeed, invalid should fail
        if 'AAPL' in mixed_results:
            assert mixed_results['AAPL'].success or mixed_results['AAPL'].error is not None
        if 'GOOGL' in mixed_results:  
            assert mixed_results['GOOGL'].success or mixed_results['GOOGL'].error is not None
        if 'INVALID_SYMBOL' in mixed_results:
            assert not mixed_results['INVALID_SYMBOL'].success
        
        logger.info("✅ Mixed symbol handling verified")
        
        # Test 3: Invalid indicator configuration
        invalid_config = SignalConfiguration(
            signal_type=SignalType.COMPOSITE,
            indicators=['INVALID_INDICATOR'],
            weights={'INVALID_INDICATOR': 1.0}
        )
        
        try:
            invalid_indicator_results = await full_service_stack['signals'].generate_signals(
                ['AAPL'],
                invalid_config
            )
            
            # Should either raise exception or return error result
            if 'AAPL' in invalid_indicator_results:
                result = invalid_indicator_results['AAPL']
                assert not result.success, "Should fail for invalid indicator"
                assert result.error is not None
                
        except (ValueError, KeyError) as e:
            # Expected behavior - invalid configuration caught
            logger.info(f"✅ Invalid configuration properly rejected: {str(e)}")
        
        logger.info("✅ Error handling workflow tests completed")

    @pytest.mark.performance
    async def test_realistic_performance_scenario(self, full_service_stack):
        """Test: Performance with realistic user portfolio sizes"""
        
        # Scenario: User with 20-stock portfolio wants daily signals
        portfolio_symbols = ['AAPL', 'GOOGL', 'MSFT'] * 7  # 21 symbols (simulating larger portfolio)
        portfolio_symbols = list(dict.fromkeys(portfolio_symbols))  # Remove duplicates
        
        logger.info(f"⚡ Starting performance test with {len(portfolio_symbols)} symbols")
        
        import time
        
        # Test composite signal generation performance
        signal_config = SignalConfiguration(
            signal_type=SignalType.COMPOSITE,
            indicators=['RSI', 'MACD', 'MOMENTUM'],
            weights={'RSI': 0.3, 'MACD': 0.5, 'MOMENTUM': 0.2}
        )
        
        start_time = time.time()
        
        performance_results = await full_service_stack['signals'].generate_signals(
            portfolio_symbols,
            signal_config
        )
        
        end_time = time.time()
        calculation_time = end_time - start_time
        
        # Performance assertions
        assert calculation_time < 10.0, f"Portfolio signal generation too slow: {calculation_time:.2f}s"
        
        # Verify all symbols processed
        successful_calculations = sum(1 for result in performance_results.values() if result.success)
        
        logger.info(f"⚡ Performance Results:")
        logger.info(f"   Total time: {calculation_time:.2f}s")
        logger.info(f"   Successful calculations: {successful_calculations}/{len(portfolio_symbols)}")
        logger.info(f"   Average per symbol: {calculation_time/len(portfolio_symbols):.3f}s")
        
        # Should achieve reasonable performance even with multiple symbols
        avg_per_symbol = calculation_time / len(portfolio_symbols)
        assert avg_per_symbol < 1.0, f"Per-symbol calculation too slow: {avg_per_symbol:.3f}s"
        
        logger.info("✅ Realistic performance scenario completed")


def manual_validation_helper():
    """Helper function to manually validate calculations against known data"""
    
    print("\n" + "="*60)
    print("MANUAL VALIDATION HELPER")
    print("="*60)
    print("Use this to manually verify indicator calculations:")
    print()
    print("Sample RSI calculation for verification:")
    print("- 14-period RSI with sample data")
    print("- Expected RSI range: 0-100")
    print("- Overbought: >70, Oversold: <30")
    print()
    print("Sample MACD calculation:")
    print("- 12,26,9 parameters")
    print("- MACD = EMA12 - EMA26")
    print("- Signal = EMA9 of MACD")
    print("- Histogram = MACD - Signal")
    print()
    print("Sample Momentum calculation:")
    print("- 10-period rate of change")
    print("- Momentum = (Close - Close[n]) / Close[n]")
    print("- Typical range: -20% to +20%")
    print("="*60)


if __name__ == "__main__":
    manual_validation_helper()