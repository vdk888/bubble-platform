"""
Signal Generation API Endpoints.
Generates trading signals based on technical indicators and custom rules.
Following production-grade standards with real-time data validation.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from ...core.database import get_db
from ...core.dependencies import get_current_user
from ...models.user import User
from ...services.signal_generation_service import SignalGenerationService
from ...services.interfaces.signal_service import (
    SignalType,
    SignalStrength,
    SignalConfiguration,
    SignalResult
)

router = APIRouter()
logger = logging.getLogger(__name__)

class SignalGenerationRequest(BaseModel):
    """Request model for generating trading signals"""
    universe_id: Optional[int] = Field(None, description="Universe ID to generate signals for")
    symbols: Optional[List[str]] = Field(None, min_items=1, max_items=100, description="Specific symbols to analyze")
    signal_type: SignalType = Field(SignalType.COMPOSITE, description="Type of signal generation")
    indicators: List[str] = Field(
        default=['RSI', 'MACD', 'MOMENTUM'],
        description="Indicators to use for signal generation"
    )
    weights: Optional[Dict[str, float]] = Field(
        None,
        description="Custom weights for indicators (defaults: MACD=0.5, RSI=0.3, MOMENTUM=0.2)"
    )
    thresholds: Optional[Dict[str, Any]] = Field(
        None,
        description="Custom thresholds for signal generation"
    )
    lookback_days: int = Field(30, ge=1, le=365, description="Days of historical data to analyze")
    
    @field_validator('symbols')
    def validate_symbols(cls, v):
        if v:
            return [s.strip().upper() for s in v if s.strip()]
        return v
    
    @field_validator('weights')
    def validate_weights(cls, v):
        if v:
            total = sum(v.values())
            if total == 0:
                raise ValueError("Weights sum cannot be zero")
            # Normalize weights
            return {k: val/total for k, val in v.items()}
        return v

class SignalResponse(BaseModel):
    """Response model for generated signals"""
    symbol: str
    signal: int = Field(..., description="-1 (strong sell), 0 (hold), 1 (strong buy)")
    strength: SignalStrength
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    indicators_used: Dict[str, Dict[str, Any]] = Field(..., description="Individual indicator signals")
    reason: str = Field(..., description="Human-readable explanation of signal")
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

class BatchSignalResponse(BaseModel):
    """Response for batch signal generation"""
    signals: List[SignalResponse]
    summary: Dict[str, Any]
    generation_time_ms: float
    errors: List[Dict[str, str]] = Field(default_factory=list)

class SignalAlert(BaseModel):
    """Alert configuration for signal notifications"""
    enabled: bool = True
    signal_types: List[SignalStrength] = Field(
        default=[SignalStrength.STRONG],
        description="Signal strengths that trigger alerts"
    )
    notification_channels: List[str] = Field(
        default=['email'],
        description="Notification channels: email, sms, webhook"
    )

@router.post("/generate", response_model=BatchSignalResponse)
async def generate_signals(
    request: SignalGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate trading signals for a universe or specific symbols.
    
    Signal Types:
    - SIMPLE: Single indicator signals
    - COMPOSITE: Weighted combination of multiple indicators
    - AI_ENHANCED: ML-based signal generation (future)
    
    Returns consolidated signals with confidence scores and explanations.
    """
    start_time = datetime.now()
    
    try:
        # Initialize service
        service = SignalGenerationService(db, current_user.tenant_id)
        
        # Get symbols from universe if provided
        symbols = request.symbols
        if request.universe_id and not symbols:
            # Fetch symbols from universe
            from ...services.universe_service import UniverseService
            universe_service = UniverseService(db)
            universe = await universe_service.get_universe(
                request.universe_id, 
                current_user.tenant_id
            )
            if not universe:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Universe {request.universe_id} not found"
                )
            symbols = [asset.symbol for asset in universe.assets]
        
        if not symbols:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either universe_id or symbols must be provided"
            )
        
        # Create configuration
        config = SignalConfiguration(
            signal_type=request.signal_type,
            indicators=request.indicators,
            weights=request.weights or {
                'MACD': 0.5,
                'RSI': 0.3,
                'MOMENTUM': 0.2
            },
            thresholds=request.thresholds or {
                'rsi_oversold': 30,
                'rsi_overbought': 70,
                'momentum_bullish': 0.02,
                'momentum_bearish': -0.02
            },
            lookback_days=request.lookback_days
        )
        
        # Generate signals
        results = await service.generate_signals(symbols, config)
        
        # Format responses
        signal_responses = []
        errors = []
        signal_counts = {'buy': 0, 'sell': 0, 'hold': 0}
        
        for symbol, result in results.items():
            if result.success:
                # Determine signal strength
                if abs(result.confidence) > 0.7:
                    strength = SignalStrength.STRONG
                elif abs(result.confidence) > 0.4:
                    strength = SignalStrength.MODERATE
                else:
                    strength = SignalStrength.WEAK
                
                # Count signals
                if result.signal == 1:
                    signal_counts['buy'] += 1
                elif result.signal == -1:
                    signal_counts['sell'] += 1
                else:
                    signal_counts['hold'] += 1
                
                signal_responses.append(SignalResponse(
                    symbol=symbol,
                    signal=result.signal,
                    strength=strength,
                    confidence=abs(result.confidence),
                    indicators_used=result.indicators_used,
                    reason=result.reason,
                    timestamp=result.timestamp,
                    metadata=result.metadata
                ))
            else:
                errors.append({
                    'symbol': symbol,
                    'error': result.error or 'Signal generation failed'
                })
        
        # Calculate summary statistics
        summary = {
            'total_symbols': len(symbols),
            'signals_generated': len(signal_responses),
            'signal_distribution': signal_counts,
            'strong_signals': len([s for s in signal_responses if s.strength == SignalStrength.STRONG]),
            'average_confidence': sum(s.confidence for s in signal_responses) / len(signal_responses) if signal_responses else 0
        }
        
        generation_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Schedule background task for storing signals if needed
        if signal_responses:
            background_tasks.add_task(
                service.store_signals,
                signal_responses,
                request.universe_id
            )
        
        return BatchSignalResponse(
            signals=signal_responses,
            summary=summary,
            generation_time_ms=generation_time,
            errors=errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating signals: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate signals: {str(e)}"
        )

@router.get("/history")
async def get_signal_history(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    universe_id: Optional[int] = Query(None, description="Filter by universe"),
    days: int = Query(7, ge=1, le=90, description="Days of history"),
    signal_type: Optional[int] = Query(None, description="Filter by signal type (-1, 0, 1)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get historical signals for analysis and backtesting.
    
    Useful for:
    - Analyzing signal accuracy over time
    - Identifying patterns in signal generation
    - Backtesting signal-based strategies
    """
    try:
        service = SignalGenerationService(db, current_user.tenant_id)
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Fetch historical signals
        history = await service.get_signal_history(
            symbol=symbol.upper() if symbol else None,
            universe_id=universe_id,
            start_date=start_date,
            end_date=end_date,
            signal_type=signal_type
        )
        
        # Group by date for analysis
        daily_summary = {}
        for signal in history:
            date_key = signal['timestamp'].date().isoformat()
            if date_key not in daily_summary:
                daily_summary[date_key] = {
                    'buy_signals': 0,
                    'sell_signals': 0,
                    'hold_signals': 0,
                    'average_confidence': 0,
                    'signals': []
                }
            
            if signal['signal'] == 1:
                daily_summary[date_key]['buy_signals'] += 1
            elif signal['signal'] == -1:
                daily_summary[date_key]['sell_signals'] += 1
            else:
                daily_summary[date_key]['hold_signals'] += 1
            
            daily_summary[date_key]['signals'].append(signal)
        
        # Calculate averages
        for date_key in daily_summary:
            signals = daily_summary[date_key]['signals']
            if signals:
                daily_summary[date_key]['average_confidence'] = (
                    sum(s.get('confidence', 0) for s in signals) / len(signals)
                )
        
        return {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_signals': len(history),
            'daily_summary': daily_summary,
            'signals': history
        }
        
    except Exception as e:
        logger.error(f"Error fetching signal history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch signal history: {str(e)}"
        )

@router.post("/alerts")
async def configure_signal_alerts(
    config: SignalAlert,
    universe_id: int = Query(..., description="Universe to monitor"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Configure real-time alerts for trading signals.
    
    Monitors specified universe and sends notifications when
    strong signals are generated.
    """
    try:
        service = SignalGenerationService(db, current_user.tenant_id)
        
        # Store alert configuration
        alert_config = await service.configure_alerts(
            universe_id=universe_id,
            enabled=config.enabled,
            signal_types=config.signal_types,
            notification_channels=config.notification_channels,
            user_id=current_user.id
        )
        
        return {
            'message': 'Alert configuration saved successfully',
            'config': alert_config,
            'universe_id': universe_id
        }
        
    except Exception as e:
        logger.error(f"Error configuring alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure alerts: {str(e)}"
        )

@router.get("/performance/{symbol}")
async def get_signal_performance(
    symbol: str,
    days: int = Query(30, ge=7, le=365, description="Days to analyze"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze historical performance of signals for a symbol.
    
    Returns:
    - Signal accuracy (% of correct predictions)
    - Average return following signals
    - Best/worst signal performance
    - Signal frequency analysis
    """
    try:
        service = SignalGenerationService(db, current_user.tenant_id)
        
        # Get performance metrics
        performance = await service.analyze_signal_performance(
            symbol=symbol.upper(),
            lookback_days=days
        )
        
        if not performance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No signal history found for {symbol}"
            )
        
        return {
            'symbol': symbol.upper(),
            'period_days': days,
            'metrics': performance,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing signal performance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze signal performance: {str(e)}"
        )

@router.post("/backtest")
async def backtest_signals(
    universe_id: int = Query(..., description="Universe to backtest"),
    start_date: datetime = Query(..., description="Backtest start date"),
    end_date: datetime = Query(..., description="Backtest end date"),
    initial_capital: float = Query(100000, gt=0, description="Starting capital"),
    position_size: float = Query(0.1, gt=0, le=1, description="Position size as fraction of capital"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Backtest signal-based trading strategy.
    
    Simulates trading based on generated signals and calculates:
    - Total return
    - Sharpe ratio
    - Maximum drawdown
    - Win rate
    - Trade statistics
    """
    try:
        service = SignalGenerationService(db, current_user.tenant_id)
        
        # Run backtest
        backtest_results = await service.backtest_signals(
            universe_id=universe_id,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            position_size=position_size
        )
        
        if not backtest_results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient data for backtesting"
            )
        
        return {
            'universe_id': universe_id,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'parameters': {
                'initial_capital': initial_capital,
                'position_size': position_size
            },
            'results': backtest_results,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running signal backtest: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run signal backtest: {str(e)}"
        )