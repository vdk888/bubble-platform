"""
Technical Indicators Service Interface - Sprint 3 Implementation

Interface for calculating technical indicators (RSI, MACD, Momentum) and generating
trading signals following the Interface-First Design pattern.

This interface enables:
- Clean separation of concerns
- Easy testing with mock implementations
- Future flexibility to swap implementations
- Clear contract for indicator calculations
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from datetime import date, datetime
import pandas as pd
from enum import Enum
from dataclasses import dataclass


class IndicatorType(Enum):
    """Supported technical indicator types"""
    RSI = "rsi"
    MACD = "macd"  
    MOMENTUM = "momentum"


class SignalType(Enum):
    """Trading signal types"""
    BUY = 1
    HOLD = 0
    SELL = -1


class IndicatorConfig:
    """Configuration for technical indicators"""
    
    def __init__(self):
        # RSI Configuration
        self.rsi_period: int = 14
        self.rsi_overbought: float = 70.0
        self.rsi_oversold: float = 30.0
        
        # MACD Configuration
        self.macd_fast: int = 12
        self.macd_slow: int = 26
        self.macd_signal: int = 9
        
        # Momentum Configuration
        self.momentum_period: int = 10
        self.momentum_threshold_positive: float = 2.0  # +2% threshold
        self.momentum_threshold_negative: float = -2.0  # -2% threshold
        
        # Signal Generation
        self.max_data_age_minutes: int = 15  # Reject data older than 15 minutes
        
        # Composite Signal Weights (must sum to 1.0)
        self.weight_rsi: float = 0.3
        self.weight_macd: float = 0.5
        self.weight_momentum: float = 0.2


@dataclass
class IndicatorParameters:
    """Parameters for indicator calculations"""
    indicator_type: IndicatorType
    symbols: List[str]
    period: Optional[int] = None
    fast_period: Optional[int] = None
    slow_period: Optional[int] = None
    signal_period: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@dataclass
class IndicatorResult:
    """Result of indicator calculation"""
    success: bool
    current_value: Optional[float] = None
    signal: int = 0  # -1, 0, 1
    values: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None


class IIndicatorService(ABC):
    """
    Interface for technical indicator calculations and signal generation.
    
    All implementations must follow these standards:
    - RSI: 14-period default with 70/30 overbought/oversold levels
    - MACD: 12,26,9 parameters with crossover detection
    - Momentum: Configurable lookback with ±2% thresholds
    - Signal Format: pandas Series with -1, 0, 1 values
    - Performance: <2 seconds for 1000 assets
    - Data Validation: Reject market data >15 minutes old
    """
    
    @abstractmethod
    async def calculate_rsi(
        self, 
        prices: pd.DataFrame,
        period: int = 14,
        column: str = 'close'
    ) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).
        
        Args:
            prices: DataFrame with price data (must have 'close' column)
            period: RSI period (default 14)
            column: Column to use for calculation
            
        Returns:
            Series with RSI values (0-100 scale)
            
        Raises:
            ValueError: If insufficient data or invalid parameters
        """
        pass
    
    @abstractmethod
    async def calculate_macd(
        self,
        prices: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        column: str = 'close'
    ) -> Dict[str, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            prices: DataFrame with price data
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line EMA period (default 9)
            column: Column to use for calculation
            
        Returns:
            Dictionary with 'macd', 'signal', and 'histogram' Series
            
        Raises:
            ValueError: If insufficient data or invalid parameters
        """
        pass
    
    @abstractmethod
    async def calculate_momentum(
        self,
        prices: pd.DataFrame,
        period: int = 10,
        column: str = 'close'
    ) -> pd.Series:
        """
        Calculate price momentum (rate of change).
        
        Args:
            prices: DataFrame with price data
            period: Lookback period for momentum
            column: Column to use for calculation
            
        Returns:
            Series with momentum values (percentage change)
            
        Raises:
            ValueError: If insufficient data or invalid parameters
        """
        pass
    
    @abstractmethod
    async def generate_rsi_signals(
        self,
        rsi_values: pd.Series,
        overbought: float = 70.0,
        oversold: float = 30.0
    ) -> pd.Series:
        """
        Generate trading signals from RSI values.
        
        Args:
            rsi_values: Series of RSI values
            overbought: Overbought threshold (default 70)
            oversold: Oversold threshold (default 30)
            
        Returns:
            Series with signals (-1: sell, 0: hold, 1: buy)
        """
        pass
    
    @abstractmethod
    async def generate_macd_signals(
        self,
        macd_data: Dict[str, pd.Series]
    ) -> pd.Series:
        """
        Generate trading signals from MACD crossovers.
        
        Args:
            macd_data: Dictionary with 'macd', 'signal' Series
            
        Returns:
            Series with signals (-1: sell, 0: hold, 1: buy)
        """
        pass
    
    @abstractmethod
    async def generate_momentum_signals(
        self,
        momentum_values: pd.Series,
        threshold_positive: float = 2.0,
        threshold_negative: float = -2.0
    ) -> pd.Series:
        """
        Generate trading signals from momentum.
        
        Args:
            momentum_values: Series of momentum values (percentage)
            threshold_positive: Positive momentum threshold (default +2%)
            threshold_negative: Negative momentum threshold (default -2%)
            
        Returns:
            Series with signals (-1: sell, 0: hold, 1: buy)
        """
        pass
    
    @abstractmethod
    async def generate_composite_signals(
        self,
        indicators: Dict[str, pd.Series],
        weights: Optional[Dict[str, float]] = None,
        conflict_resolution: str = "weighted"
    ) -> pd.Series:
        """
        Generate weighted composite signals from multiple indicators.
        
        Args:
            indicators: Dictionary of indicator signals
            weights: Weights for each indicator (must sum to 1.0)
            conflict_resolution: Strategy for conflicts ('weighted', 'priority', 'unanimous')
            
        Returns:
            Series with composite signals (-1: sell, 0: hold, 1: buy)
            
        Notes:
            Priority hierarchy: MACD > RSI > Momentum
        """
        pass
    
    @abstractmethod
    async def validate_data_freshness(
        self,
        data: pd.DataFrame,
        max_age_minutes: int = 15
    ) -> bool:
        """
        Validate that market data is fresh enough for calculations.
        
        Args:
            data: DataFrame with timestamp information
            max_age_minutes: Maximum age in minutes (default 15)
            
        Returns:
            True if data is fresh, False otherwise
        """
        pass
    
    @abstractmethod
    async def calculate_all_indicators(
        self,
        prices: pd.DataFrame,
        config: Optional[IndicatorConfig] = None
    ) -> Dict[str, pd.Series]:
        """
        Calculate all supported indicators at once.
        
        Args:
            prices: DataFrame with price data
            config: Indicator configuration (uses defaults if None)
            
        Returns:
            Dictionary with all indicator values and signals
            
        Performance Requirement:
            Must complete within 2 seconds for 1000 assets
        """
        pass
    
    @abstractmethod
    async def batch_calculate_indicators(
        self,
        symbol_data: Dict[str, pd.DataFrame],
        indicators: List[str],
        config: Optional[IndicatorConfig] = None
    ) -> Dict[str, Dict[str, pd.Series]]:
        """
        Batch calculate indicators for multiple symbols.
        
        Args:
            symbol_data: Dictionary mapping symbols to price DataFrames
            indicators: List of indicators to calculate
            config: Indicator configuration
            
        Returns:
            Nested dict: {symbol: {indicator: Series}}
            
        Performance Requirement:
            Optimized for bulk processing with parallel execution
        """
        pass