"""
Technical Indicators API Endpoints.
Provides calculation of RSI, MACD, Momentum and other technical indicators.
Following Interface-First Design with production-grade standards.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
import pandas as pd

from ...core.database import get_db
from ...core.dependencies import get_current_user
from ...models.user import User
from ...services.technical_indicators_service import TechnicalIndicatorService
from ...services.interfaces.indicator_service import (
    IndicatorType, 
    IndicatorParameters,
    IndicatorResult
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Request/Response Models
class IndicatorRequest(BaseModel):
    """Request model for calculating technical indicators"""
    symbols: List[str] = Field(..., min_items=1, max_items=100, description="List of asset symbols")
    indicator_type: IndicatorType = Field(..., description="Type of indicator to calculate")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Indicator-specific parameters")
    start_date: Optional[datetime] = Field(None, description="Start date for historical data")
    end_date: Optional[datetime] = Field(None, description="End date for historical data")
    
    @field_validator('symbols')
    def validate_symbols(cls, v):
        # Clean and uppercase symbols
        return [s.strip().upper() for s in v if s.strip()]
    
    @field_validator('parameters')
    def validate_parameters(cls, v, values):
        """Validate parameters based on indicator type"""
        if 'indicator_type' not in values.data:
            return v
            
        indicator_type = values.data['indicator_type']
        
        # Set default parameters if not provided
        if not v:
            defaults = {
                IndicatorType.RSI: {'period': 14},
                IndicatorType.MACD: {'fast_period': 12, 'slow_period': 26, 'signal_period': 9},
                IndicatorType.MOMENTUM: {'period': 10}
            }
            return defaults.get(indicator_type, {})
        
        # Validate parameter ranges
        if indicator_type == IndicatorType.RSI:
            period = v.get('period', 14)
            if not 2 <= period <= 100:
                raise ValueError("RSI period must be between 2 and 100")
                
        elif indicator_type == IndicatorType.MACD:
            fast = v.get('fast_period', 12)
            slow = v.get('slow_period', 26)
            signal = v.get('signal_period', 9)
            if fast >= slow:
                raise ValueError("MACD fast period must be less than slow period")
            if not 2 <= signal <= 50:
                raise ValueError("MACD signal period must be between 2 and 50")
                
        elif indicator_type == IndicatorType.MOMENTUM:
            period = v.get('period', 10)
            if not 1 <= period <= 100:
                raise ValueError("Momentum period must be between 1 and 100")
                
        return v

class IndicatorResponse(BaseModel):
    """Response model for indicator calculations"""
    symbol: str
    indicator_type: str
    current_value: Optional[float] = Field(None, description="Current indicator value")
    signal: int = Field(..., description="Trading signal: -1 (sell), 0 (hold), 1 (buy)")
    values: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional indicator values (e.g., MACD components)")
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class BatchIndicatorResponse(BaseModel):
    """Response for batch indicator calculations"""
    results: List[IndicatorResponse]
    calculation_time_ms: float
    errors: List[Dict[str, str]] = Field(default_factory=list)

@router.post("/calculate", response_model=BatchIndicatorResponse)
async def calculate_indicators(
    request: IndicatorRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate technical indicators for given symbols.
    
    Supported indicators:
    - RSI: Relative Strength Index (14-period default)
    - MACD: Moving Average Convergence Divergence (12,26,9 default)
    - Momentum: Rate of change indicator (10-period default)
    
    Returns trading signals: -1 (sell), 0 (hold), 1 (buy)
    """
    start_time = datetime.now()
    
    try:
        # Initialize service
        service = TechnicalIndicatorService(db, current_user.tenant_id)
        
        # Convert parameters to IndicatorParameters
        params = IndicatorParameters(
            indicator_type=request.indicator_type,
            symbols=request.symbols,
            period=request.parameters.get('period'),
            fast_period=request.parameters.get('fast_period'),
            slow_period=request.parameters.get('slow_period'),
            signal_period=request.parameters.get('signal_period'),
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        # Calculate indicators
        results = await service.calculate_batch(params)
        
        # Format responses
        responses = []
        errors = []
        
        for symbol in request.symbols:
            if symbol in results:
                result = results[symbol]
                if result.success:
                    responses.append(IndicatorResponse(
                        symbol=symbol,
                        indicator_type=request.indicator_type.value,
                        current_value=result.current_value,
                        signal=result.signal,
                        values=result.values,
                        timestamp=result.timestamp,
                        metadata=result.metadata or {}
                    ))
                else:
                    errors.append({
                        'symbol': symbol,
                        'error': result.error or 'Calculation failed'
                    })
            else:
                errors.append({
                    'symbol': symbol,
                    'error': 'No data available'
                })
        
        calculation_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return BatchIndicatorResponse(
            results=responses,
            calculation_time_ms=calculation_time,
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate indicators: {str(e)}"
        )

@router.get("/types", response_model=List[Dict[str, Any]])
async def get_indicator_types(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of available indicator types and their parameters.
    """
    return [
        {
            "type": IndicatorType.RSI.value,
            "name": "Relative Strength Index",
            "description": "Momentum oscillator measuring speed and magnitude of price changes",
            "default_parameters": {"period": 14},
            "signals": {
                "overbought": ">70",
                "oversold": "<30"
            }
        },
        {
            "type": IndicatorType.MACD.value,
            "name": "MACD",
            "description": "Trend-following momentum indicator",
            "default_parameters": {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9
            },
            "signals": {
                "bullish": "MACD crosses above signal",
                "bearish": "MACD crosses below signal"
            }
        },
        {
            "type": IndicatorType.MOMENTUM.value,
            "name": "Momentum",
            "description": "Rate of change in price",
            "default_parameters": {"period": 10},
            "signals": {
                "bullish": ">2%",
                "bearish": "<-2%"
            }
        }
    ]

@router.get("/history/{symbol}")
async def get_indicator_history(
    symbol: str,
    indicator_type: IndicatorType = Query(..., description="Type of indicator"),
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get historical indicator values for a symbol.
    
    Returns time series data for charting and analysis.
    """
    try:
        service = TechnicalIndicatorService(db, current_user.tenant_id)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        params = IndicatorParameters(
            indicator_type=indicator_type,
            symbols=[symbol.upper()],
            start_date=start_date,
            end_date=end_date
        )
        
        # Get historical data with indicators
        result = await service.calculate_with_history(params)
        
        if not result or symbol.upper() not in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data available for {symbol}"
            )
        
        symbol_result = result[symbol.upper()]
        
        if not symbol_result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=symbol_result.error or "Failed to calculate indicators"
            )
        
        return {
            "symbol": symbol.upper(),
            "indicator_type": indicator_type.value,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data": symbol_result.history,
            "current_value": symbol_result.current_value,
            "signal": symbol_result.signal,
            "metadata": symbol_result.metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching indicator history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch indicator history: {str(e)}"
        )

@router.post("/composite")
async def calculate_composite_indicators(
    symbols: List[str] = Query(..., description="List of symbols"),
    indicators: List[IndicatorType] = Query(..., description="List of indicators to combine"),
    weights: Optional[List[float]] = Query(None, description="Weights for each indicator"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calculate composite signals from multiple indicators.
    
    Combines RSI, MACD, and Momentum with configurable weights.
    Default weights follow priority: MACD > RSI > Momentum.
    """
    if not indicators:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one indicator must be specified"
        )
    
    # Default weights if not provided
    if not weights:
        weight_map = {
            IndicatorType.MACD: 0.5,
            IndicatorType.RSI: 0.3,
            IndicatorType.MOMENTUM: 0.2
        }
        weights = [weight_map.get(ind, 0.33) for ind in indicators]
    elif len(weights) != len(indicators):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Number of weights must match number of indicators"
        )
    
    # Normalize weights
    total_weight = sum(weights)
    if total_weight == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Weights sum cannot be zero"
        )
    weights = [w / total_weight for w in weights]
    
    try:
        service = TechnicalIndicatorService(db, current_user.tenant_id)
        
        # Calculate all indicators
        all_results = {}
        for indicator in indicators:
            params = IndicatorParameters(
                indicator_type=indicator,
                symbols=symbols
            )
            results = await service.calculate_batch(params)
            all_results[indicator] = results
        
        # Combine signals
        composite_results = []
        for symbol in symbols:
            composite_signal = 0
            valid_count = 0
            indicator_values = {}
            
            for i, indicator in enumerate(indicators):
                if symbol in all_results[indicator]:
                    result = all_results[indicator][symbol]
                    if result.success:
                        composite_signal += result.signal * weights[i]
                        valid_count += 1
                        indicator_values[indicator.value] = {
                            'value': result.current_value,
                            'signal': result.signal,
                            'weight': weights[i]
                        }
            
            if valid_count > 0:
                # Convert weighted signal to discrete signal
                if composite_signal > 0.3:
                    final_signal = 1  # Buy
                elif composite_signal < -0.3:
                    final_signal = -1  # Sell
                else:
                    final_signal = 0  # Hold
                
                composite_results.append({
                    'symbol': symbol,
                    'composite_signal': final_signal,
                    'weighted_score': composite_signal,
                    'indicators': indicator_values,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
        
        return {
            'results': composite_results,
            'indicators_used': [ind.value for ind in indicators],
            'weights': weights
        }
        
    except Exception as e:
        logger.error(f"Error calculating composite indicators: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate composite indicators: {str(e)}"
        )