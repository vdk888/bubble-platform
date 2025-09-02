"""
Signal Generation Service Interface - Sprint 3 Implementation

Interface for generating trading signals from technical indicators following
the Interface-First Design pattern. Supports simple, composite, and AI-enhanced signals.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass


class SignalType(Enum):
    """Types of signal generation strategies"""
    SIMPLE = "simple"        # Single indicator signals
    COMPOSITE = "composite"  # Weighted combination of indicators
    AI_ENHANCED = "ai"       # ML-based signal generation (future)


class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


@dataclass
class SignalConfiguration:
    """Configuration for signal generation"""
    signal_type: SignalType
    indicators: List[str]
    weights: Optional[Dict[str, float]] = None
    thresholds: Optional[Dict[str, Any]] = None
    lookback_days: int = 30
    min_confidence: float = 0.3


@dataclass
class SignalResult:
    """Result of signal generation"""
    success: bool
    signal: int = 0  # -1 (sell), 0 (hold), 1 (buy)
    confidence: float = 0.0  # 0.0 to 1.0
    indicators_used: Optional[Dict[str, Dict[str, Any]]] = None
    reason: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ISignalService(ABC):
    """
    Interface for trading signal generation.
    
    Provides methods to generate signals from technical indicators with
    configurable strategies and composite weighting.
    """
    
    @abstractmethod
    async def generate_signals(
        self,
        symbols: List[str],
        config: SignalConfiguration
    ) -> Dict[str, SignalResult]:
        """
        Generate trading signals for multiple symbols.
        
        Args:
            symbols: List of symbols to analyze
            config: Signal generation configuration
            
        Returns:
            Dict mapping symbols to signal results
        """
        pass
    
    @abstractmethod
    async def generate_simple_signal(
        self,
        symbol: str,
        indicator: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> SignalResult:
        """
        Generate signal from single indicator.
        
        Args:
            symbol: Symbol to analyze
            indicator: Indicator name (RSI, MACD, MOMENTUM)
            parameters: Indicator-specific parameters
            
        Returns:
            Signal result
        """
        pass
    
    @abstractmethod
    async def generate_composite_signal(
        self,
        symbol: str,
        indicators: List[str],
        weights: Dict[str, float]
    ) -> SignalResult:
        """
        Generate weighted composite signal from multiple indicators.
        
        Args:
            symbol: Symbol to analyze
            indicators: List of indicators to combine
            weights: Weights for each indicator
            
        Returns:
            Composite signal result
        """
        pass
    
    @abstractmethod
    async def get_signal_history(
        self,
        symbol: Optional[str] = None,
        universe_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        signal_type: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical signals for analysis.
        
        Args:
            symbol: Filter by symbol
            universe_id: Filter by universe
            start_date: Start date for history
            end_date: End date for history
            signal_type: Filter by signal type (-1, 0, 1)
            
        Returns:
            List of historical signals
        """
        pass
    
    @abstractmethod
    async def analyze_signal_performance(
        self,
        symbol: str,
        lookback_days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze historical performance of signals.
        
        Args:
            symbol: Symbol to analyze
            lookback_days: Number of days to analyze
            
        Returns:
            Performance metrics or None if insufficient data
        """
        pass
    
    @abstractmethod
    async def configure_alerts(
        self,
        universe_id: int,
        enabled: bool,
        signal_types: List[SignalStrength],
        notification_channels: List[str],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Configure real-time signal alerts.
        
        Args:
            universe_id: Universe to monitor
            enabled: Enable/disable alerts
            signal_types: Signal strengths to alert on
            notification_channels: Notification methods
            user_id: User ID for alerts
            
        Returns:
            Alert configuration
        """
        pass
    
    @abstractmethod
    async def backtest_signals(
        self,
        universe_id: int,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float,
        position_size: float
    ) -> Optional[Dict[str, Any]]:
        """
        Backtest signal-based trading strategy.
        
        Args:
            universe_id: Universe to backtest
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Starting capital
            position_size: Position size as fraction
            
        Returns:
            Backtest results or None if insufficient data
        """
        pass
    
    @abstractmethod
    async def store_signals(
        self,
        signals: List[Any],
        universe_id: Optional[int] = None
    ) -> bool:
        """
        Store generated signals for history tracking.
        
        Args:
            signals: List of signal responses
            universe_id: Associated universe ID
            
        Returns:
            True if stored successfully
        """
        pass