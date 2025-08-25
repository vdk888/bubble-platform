# **SPRINT 3: MARKET DATA & INDICATORS SERVICE** (Week 4)

## **🎯 Sprint 3 Success Criteria**
- **Performance**: Indicator calculations <2s for 1000 assets (per 1_spec.md requirement)
- **Architecture**: Interface-First Design with clean service boundaries
- **Testing**: Real data testing with 80%+ coverage (following established patterns)
- **Security**: Financial-grade security with audit logging
- **Integration**: Seamless integration with existing Sprint 2 universe/asset services

## **📋 DETAILED DAILY IMPLEMENTATION PLAN**

---

## **🏗️ MONDAY: Interface-First Design Foundation**

### **Morning (3 hours): Interface Definition & Architecture Planning**

#### **Task 1.1: Market Data Interface Design** 
**File**: `backend/app/services/interfaces/market_data_service.py`
```python
# Building on existing IDataProvider patterns
class IMarketDataService(BaseService):
    @abstractmethod
    async def fetch_historical_data(
        self, 
        symbols: List[str], 
        start_date: datetime, 
        end_date: datetime,
        interval: str = "1d"
    ) -> ServiceResult[Dict[str, MarketData]]:
        """Fetch historical OHLCV data following existing ServiceResult pattern"""
        pass
    
    @abstractmethod
    async def fetch_real_time_prices(
        self, 
        symbols: List[str]
    ) -> ServiceResult[Dict[str, PriceData]]:
        """Real-time price data with <100ms target following existing patterns"""
        pass
    
    @abstractmethod
    async def validate_data_freshness(
        self, 
        data: MarketData, 
        max_age_minutes: int = 15
    ) -> ServiceResult[bool]:
        """Data validation following 1_spec.md requirement"""
        pass
```

**Integration Points**:
- Extend existing `ServiceResult` wrapper pattern
- Use established `BaseService` abstract class
- Follow existing async method signatures
- Integrate with current audit logging patterns

#### **Task 1.2: Indicator Service Interface Design**
**File**: `backend/app/services/interfaces/indicator_service.py`
```python
class IIndicatorService(BaseService):
    @abstractmethod
    async def calculate_rsi(
        self, 
        price_data: pd.DataFrame, 
        period: int = 14
    ) -> ServiceResult[pd.Series]:
        """RSI with overbought/oversold signals (-1, 0, 1 format per spec)"""
        pass
    
    @abstractmethod
    async def calculate_macd(
        self, 
        price_data: pd.DataFrame, 
        fast: int = 12, 
        slow: int = 26, 
        signal: int = 9
    ) -> ServiceResult[pd.Series]:
        """MACD with crossover signals following 1_spec.md parameters"""
        pass
    
    @abstractmethod
    async def calculate_composite_signals(
        self, 
        indicators: Dict[str, pd.Series], 
        weights: Dict[str, float]
    ) -> ServiceResult[pd.Series]:
        """Weighted signals with MACD > RSI > Momentum hierarchy per spec"""
        pass
```

#### **Task 1.3: Enhanced Pydantic Models**
**File**: `backend/app/services/interfaces/models.py`
```python
# Extend existing MarketData model
class OHLCVData(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None

class IndicatorResult(BaseModel):
    symbol: str
    indicator_type: str
    values: Dict[str, float]  # timestamp -> value mapping
    signals: Dict[str, int]   # timestamp -> signal (-1, 0, 1)
    parameters: Dict[str, Any]
    calculated_at: datetime
    confidence: float

class CompositeSignal(BaseModel):
    symbol: str
    signal: int  # Final composite signal
    components: Dict[str, IndicatorResult]
    weights: Dict[str, float]
    timestamp: datetime
```

### **Afternoon (4 hours): Database Schema & Migration Planning**

#### **Task 1.4: Database Model Extensions**
**File**: `backend/app/models/market_data.py`
```python
# Extend existing BaseModel pattern
class PriceHistory(BaseModel):
    __tablename__ = "price_history"
    
    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    open_price = Column(Numeric(precision=10, scale=4), nullable=False)
    high_price = Column(Numeric(precision=10, scale=4), nullable=False)
    low_price = Column(Numeric(precision=10, scale=4), nullable=False)
    close_price = Column(Numeric(precision=10, scale=4), nullable=False)
    volume = Column(BigInteger, nullable=False)
    adjusted_close = Column(Numeric(precision=10, scale=4))
    data_source = Column(String(50), nullable=False)  # yahoo, alpha_vantage
    
    # Relationships
    asset = relationship("Asset", back_populates="price_history")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_price_history_asset_timestamp', 'asset_id', 'timestamp'),
        Index('idx_price_history_timestamp', 'timestamp'),
        UniqueConstraint('asset_id', 'timestamp', 'data_source', name='uix_asset_timestamp_source')
    )

class IndicatorCache(BaseModel):
    __tablename__ = "indicator_cache"
    
    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=False)
    indicator_type = Column(String(50), nullable=False)  # rsi, macd, momentum
    parameters = Column(JSON, nullable=False)  # period, fast, slow, etc.
    result_data = Column(JSON, nullable=False)  # calculated values and signals
    calculated_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    asset = relationship("Asset", back_populates="indicator_results")
    
    # Indexes
    __table_args__ = (
        Index('idx_indicator_asset_type', 'asset_id', 'indicator_type'),
        Index('idx_indicator_expires', 'expires_at'),
    )
```

#### **Task 1.5: Migration Script Creation**
**File**: `backend/alembic/versions/003_add_market_data_indicators.py`
- Create tables with proper indexes and constraints
- Add foreign key relationships to existing Asset model
- Include rollback script for safe deployment
- Test migration on copy of production data structure

#### **Task 1.6: Model Relationship Updates**
**File**: `backend/app/models/asset.py`
```python
# Add to existing Asset model
class Asset(BaseModel):
    # ... existing fields ...
    
    # New relationships for Sprint 3
    price_history = relationship(
        "PriceHistory", 
        back_populates="asset", 
        cascade="all, delete-orphan",
        order_by="PriceHistory.timestamp.desc()"
    )
    
    indicator_results = relationship(
        "IndicatorCache", 
        back_populates="asset", 
        cascade="all, delete-orphan"
    )
    
    def get_latest_price(self) -> Optional[PriceHistory]:
        """Get most recent price data"""
        return self.price_history[0] if self.price_history else None
    
    def get_price_range(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[PriceHistory]:
        """Get price history for date range"""
        return [
            p for p in self.price_history 
            if start_date <= p.timestamp <= end_date
        ]
```

---

## **🔌 TUESDAY: Provider Implementation & Circuit Breaker**

### **Morning (3 hours): Enhanced Provider Implementation**

#### **Task 2.1: Alpha Vantage Provider Implementation**
**File**: `backend/app/services/providers/alpha_vantage_provider.py`
```python
# Following existing YahooDataProvider patterns
class AlphaVantageProvider(IMarketDataService):
    def __init__(self):
        self.api_key = settings.alpha_vantage_api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.rate_limiter = AsyncLimiter(5, 60)  # 5 calls per minute
        self.session = aiohttp.ClientSession()
    
    async def fetch_historical_data(
        self, 
        symbols: List[str], 
        start_date: datetime, 
        end_date: datetime,
        interval: str = "1d"
    ) -> ServiceResult[Dict[str, MarketData]]:
        """Implementation following existing ServiceResult patterns"""
        try:
            results = {}
            for symbol in symbols:
                async with self.rate_limiter:
                    data = await self._fetch_symbol_history(symbol, interval)
                    results[symbol] = data
            
            return ServiceResult.success(
                data=results,
                message=f"Retrieved historical data for {len(symbols)} symbols",
                metadata={"provider": "alpha_vantage", "symbols_count": len(symbols)}
            )
        except Exception as e:
            return ServiceResult.error(
                error=str(e),
                message="Alpha Vantage historical data fetch failed"
            )
    
    async def _fetch_symbol_history(self, symbol: str, interval: str) -> MarketData:
        """Private method for individual symbol fetching"""
        params = {
            'function': 'TIME_SERIES_DAILY_ADJUSTED',
            'symbol': symbol,
            'apikey': self.api_key,
            'outputsize': 'full'
        }
        
        async with self.session.get(self.base_url, params=params) as response:
            data = await response.json()
            return self._parse_alpha_vantage_response(data, symbol)
```

#### **Task 2.2: Circuit Breaker Implementation**
**File**: `backend/app/core/circuit_breaker.py`
```python
# New circuit breaker for market data reliability
class CircuitBreakerMarketDataService(IMarketDataService):
    def __init__(
        self, 
        primary: IMarketDataService, 
        fallback: IMarketDataService,
        failure_threshold: int = 5,
        timeout_seconds: int = 60
    ):
        self.primary = primary
        self.fallback = fallback
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.circuit_open = False
        self.last_failure_time = None
        
    async def fetch_historical_data(
        self, 
        symbols: List[str], 
        start_date: datetime, 
        end_date: datetime,
        interval: str = "1d"
    ) -> ServiceResult[Dict[str, MarketData]]:
        """Circuit breaker pattern for reliable data fetching"""
        
        # Check if circuit should be closed (reset)
        if self.circuit_open and self._should_attempt_reset():
            self.circuit_open = False
            self.failure_count = 0
            logger.info("Circuit breaker attempting reset")
        
        # Try primary service if circuit is closed
        if not self.circuit_open:
            try:
                result = await self.primary.fetch_historical_data(
                    symbols, start_date, end_date, interval
                )
                if result.success:
                    self.failure_count = 0  # Reset on success
                    return result
                else:
                    self._record_failure()
            except Exception as e:
                self._record_failure()
                logger.warning(f"Primary provider failed: {e}")
        
        # Use fallback service
        logger.info("Using fallback provider for market data")
        fallback_result = await self.fallback.fetch_historical_data(
            symbols, start_date, end_date, interval
        )
        
        # Add metadata about fallback usage
        if fallback_result.success:
            fallback_result.metadata["fallback_used"] = True
            fallback_result.metadata["primary_provider_status"] = "failed"
            
        return fallback_result
    
    def _record_failure(self):
        """Record failure and potentially open circuit"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.circuit_open = True
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
            
        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() > self.timeout_seconds
```

### **Afternoon (4 hours): Real-Time Data & WebSocket Implementation**

#### **Task 2.3: WebSocket Manager**
**File**: `backend/app/services/websocket_manager.py`
```python
# Real-time data streaming following existing async patterns
class WebSocketMarketDataManager:
    def __init__(self, market_data_service: IMarketDataService):
        self.market_data_service = market_data_service
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.active_symbols: Set[str] = set()
        self.update_task: Optional[asyncio.Task] = None
        
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect user to real-time data stream"""
        await websocket.accept()
        
        if user_id not in self.connections:
            self.connections[user_id] = set()
        
        self.connections[user_id].add(websocket)
        
        # Start update task if not running
        if not self.update_task or self.update_task.done():
            self.update_task = asyncio.create_task(self._price_update_loop())
        
        logger.info(f"WebSocket connected for user {user_id}")
    
    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect user from stream"""
        if user_id in self.connections:
            self.connections[user_id].discard(websocket)
            
            if not self.connections[user_id]:
                del self.connections[user_id]
        
        # Stop update task if no connections
        if not self.connections and self.update_task:
            self.update_task.cancel()
            
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def subscribe_to_symbols(self, user_id: str, symbols: List[str]):
        """Subscribe user to specific symbols"""
        self.active_symbols.update(symbols)
        
        # Send current prices immediately
        if symbols:
            current_prices = await self.market_data_service.fetch_real_time_prices(symbols)
            if current_prices.success:
                await self._send_to_user(user_id, {
                    "type": "price_update",
                    "data": current_prices.data,
                    "timestamp": datetime.now().isoformat()
                })
    
    async def _price_update_loop(self):
        """Background task for regular price updates"""
        while self.connections:
            try:
                if self.active_symbols:
                    prices = await self.market_data_service.fetch_real_time_prices(
                        list(self.active_symbols)
                    )
                    
                    if prices.success:
                        await self._broadcast_price_update(prices.data)
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Price update loop error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _send_to_user(self, user_id: str, message: dict):
        """Send message to specific user's connections"""
        if user_id in self.connections:
            disconnected = set()
            for websocket in self.connections[user_id]:
                try:
                    await websocket.send_json(message)
                except:
                    disconnected.add(websocket)
            
            # Clean up disconnected websockets
            self.connections[user_id] -= disconnected
```

#### **Task 2.4: WebSocket API Endpoints**
**File**: `backend/app/api/v1/market_data_websocket.py`
```python
# WebSocket endpoints following existing API patterns
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from ..auth import get_current_user_websocket

router = APIRouter()
websocket_manager = WebSocketMarketDataManager(get_market_data_service())

@router.websocket("/ws/market-data/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    user_id: str,
    current_user: User = Depends(get_current_user_websocket)
):
    """Real-time market data WebSocket endpoint"""
    # Verify user can access this stream
    if current_user.id != user_id:
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    await websocket_manager.connect(websocket, user_id)
    
    try:
        while True:
            # Listen for client messages (symbol subscriptions, etc.)
            message = await websocket.receive_json()
            
            if message.get("type") == "subscribe":
                symbols = message.get("symbols", [])
                await websocket_manager.subscribe_to_symbols(user_id, symbols)
                
            elif message.get("type") == "unsubscribe":
                # Handle unsubscribe logic
                pass
                
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        await websocket_manager.disconnect(websocket, user_id)
```

---

## **📊 WEDNESDAY: Technical Indicators Implementation**

### **Morning (3 hours): Core Indicator Algorithms**

#### **Task 3.1: RSI Implementation**
**File**: `backend/app/services/indicators/rsi_calculator.py`
```python
# Following existing calculation patterns with pandas
class RSICalculator:
    @staticmethod
    def calculate(
        price_data: pd.DataFrame, 
        period: int = 14,
        overbought_threshold: float = 70.0,
        oversold_threshold: float = 30.0
    ) -> pd.Series:
        """
        RSI calculation following 1_spec.md requirements:
        - 14-period default
        - Overbought >70, Oversold <30
        - Signal format: -1 (sell), 0 (hold), 1 (buy)
        """
        close_prices = price_data['close']
        
        # Calculate price changes
        delta = close_prices.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calculate average gains and losses using Wilder's smoothing
        avg_gains = gains.ewm(alpha=1/period, adjust=False).mean()
        avg_losses = losses.ewm(alpha=1/period, adjust=False).mean()
        
        # Calculate RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        # Generate signals based on thresholds
        signals = pd.Series(0, index=rsi.index)
        signals[rsi > overbought_threshold] = -1  # Sell signal
        signals[rsi < oversold_threshold] = 1     # Buy signal
        
        return {
            'values': rsi,
            'signals': signals,
            'parameters': {
                'period': period,
                'overbought_threshold': overbought_threshold,
                'oversold_threshold': oversold_threshold
            }
        }
    
    @staticmethod
    def validate_data(price_data: pd.DataFrame, period: int) -> bool:
        """Validate sufficient data for RSI calculation"""
        required_periods = period * 2  # Need extra periods for stability
        
        if len(price_data) < required_periods:
            raise ValueError(
                f"Insufficient data for RSI calculation. "
                f"Need {required_periods} periods, got {len(price_data)}"
            )
        
        # Check for required columns
        required_columns = ['close']
        missing_columns = [col for col in required_columns if col not in price_data.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        return True
```

#### **Task 3.2: MACD Implementation**
**File**: `backend/app/services/indicators/macd_calculator.py`
```python
class MACDCalculator:
    @staticmethod
    def calculate(
        price_data: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, pd.Series]:
        """
        MACD calculation following 1_spec.md requirements:
        - 12,26,9 parameters (fast, slow, signal)
        - Crossover detection for signals
        - Highest priority in conflict resolution
        """
        close_prices = price_data['close']
        
        # Calculate EMAs
        ema_fast = close_prices.ewm(span=fast_period).mean()
        ema_slow = close_prices.ewm(span=slow_period).mean()
        
        # Calculate MACD line
        macd_line = ema_fast - ema_slow
        
        # Calculate Signal line
        signal_line = macd_line.ewm(span=signal_period).mean()
        
        # Calculate Histogram
        histogram = macd_line - signal_line
        
        # Generate trading signals based on crossovers
        signals = pd.Series(0, index=macd_line.index)
        
        # MACD line crosses above signal line = Buy
        crossover_up = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
        signals[crossover_up] = 1
        
        # MACD line crosses below signal line = Sell
        crossover_down = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))
        signals[crossover_down] = -1
        
        return {
            'macd_line': macd_line,
            'signal_line': signal_line,
            'histogram': histogram,
            'signals': signals,
            'parameters': {
                'fast_period': fast_period,
                'slow_period': slow_period,
                'signal_period': signal_period
            }
        }
    
    @staticmethod
    def validate_data(price_data: pd.DataFrame, slow_period: int, signal_period: int) -> bool:
        """Validate sufficient data for MACD calculation"""
        required_periods = slow_period + signal_period + 10  # Buffer for EMA stability
        
        if len(price_data) < required_periods:
            raise ValueError(
                f"Insufficient data for MACD calculation. "
                f"Need {required_periods} periods, got {len(price_data)}"
            )
        
        return True
```

#### **Task 3.3: Momentum Implementation**
**File**: `backend/app/services/indicators/momentum_calculator.py`
```python
class MomentumCalculator:
    @staticmethod
    def calculate(
        price_data: pd.DataFrame,
        period: int = 10,
        signal_threshold: float = 0.02  # 2% threshold per spec
    ) -> Dict[str, pd.Series]:
        """
        Momentum calculation following 1_spec.md requirements:
        - Configurable lookback periods
        - ±2% signal thresholds
        - Simple rate of change calculation
        """
        close_prices = price_data['close']
        
        # Calculate rate of change (momentum)
        momentum = close_prices.pct_change(periods=period)
        
        # Generate signals based on momentum thresholds
        signals = pd.Series(0, index=momentum.index)
        signals[momentum > signal_threshold] = 1    # Strong positive momentum = Buy
        signals[momentum < -signal_threshold] = -1  # Strong negative momentum = Sell
        
        return {
            'values': momentum,
            'signals': signals,
            'parameters': {
                'period': period,
                'signal_threshold': signal_threshold
            }
        }
    
    @staticmethod
    def validate_data(price_data: pd.DataFrame, period: int) -> bool:
        """Validate sufficient data for momentum calculation"""
        required_periods = period + 5  # Need period + buffer
        
        if len(price_data) < required_periods:
            raise ValueError(
                f"Insufficient data for momentum calculation. "
                f"Need {required_periods} periods, got {len(price_data)}"
            )
        
        return True
```

### **Afternoon (4 hours): Composite Signal Generation**

#### **Task 3.4: Signal Composition Engine**
**File**: `backend/app/services/indicators/signal_composer.py`
```python
# Composite signal generation following 1_spec.md hierarchy
class SignalComposer:
    def __init__(self):
        # Priority hierarchy: MACD > RSI > Momentum (per spec)
        self.priority_order = ['macd', 'rsi', 'momentum']
    
    def generate_composite_signals(
        self,
        indicators: Dict[str, Dict[str, pd.Series]],
        weights: Optional[Dict[str, float]] = None
    ) -> pd.Series:
        """
        Generate composite signals following 1_spec.md requirements:
        - Weighted combination of indicators
        - MACD > RSI > Momentum hierarchy for conflict resolution
        - Output: -1 (sell), 0 (hold), 1 (buy)
        """
        if not indicators:
            raise ValueError("No indicators provided for signal composition")
        
        # Default equal weights if not provided
        if weights is None:
            weights = {name: 1.0/len(indicators) for name in indicators.keys()}
        
        # Normalize weights to sum to 1
        total_weight = sum(weights.values())
        normalized_weights = {k: v/total_weight for k, v in weights.items()}
        
        # Get all timestamps (union of all indicator timestamps)
        all_timestamps = set()
        for indicator_data in indicators.values():
            if 'signals' in indicator_data:
                all_timestamps.update(indicator_data['signals'].index)
        
        all_timestamps = sorted(all_timestamps)
        composite_signals = pd.Series(0.0, index=all_timestamps)
        
        # Calculate weighted signals
        for indicator_name, weight in normalized_weights.items():
            if indicator_name in indicators and 'signals' in indicators[indicator_name]:
                signals = indicators[indicator_name]['signals'].reindex(
                    all_timestamps, fill_value=0
                )
                composite_signals += signals * weight
        
        # Apply conflict resolution hierarchy
        final_signals = self._apply_hierarchy_resolution(indicators, composite_signals)
        
        # Convert to discrete signals (-1, 0, 1)
        result_signals = pd.Series(0, index=all_timestamps)
        result_signals[final_signals > 0.33] = 1   # Buy threshold
        result_signals[final_signals < -0.33] = -1 # Sell threshold
        
        return result_signals
    
    def _apply_hierarchy_resolution(
        self,
        indicators: Dict[str, Dict[str, pd.Series]],
        composite_signals: pd.Series
    ) -> pd.Series:
        """Apply MACD > RSI > Momentum hierarchy for conflict resolution"""
        resolved_signals = composite_signals.copy()
        
        for timestamp in composite_signals.index:
            # Check for strong signals in priority order
            for priority_indicator in self.priority_order:
                if priority_indicator in indicators:
                    indicator_data = indicators[priority_indicator]
                    if 'signals' in indicator_data:
                        signal_at_time = indicator_data['signals'].get(timestamp, 0)
                        
                        # If priority indicator has strong signal, use it
                        if abs(signal_at_time) == 1:  # Strong signal (-1 or 1)
                            resolved_signals[timestamp] = float(signal_at_time)
                            break  # Higher priority wins
        
        return resolved_signals
    
    def validate_indicators(self, indicators: Dict[str, Dict[str, pd.Series]]) -> bool:
        """Validate indicator data structure"""
        required_keys = ['signals']
        
        for name, data in indicators.items():
            if not isinstance(data, dict):
                raise ValueError(f"Indicator {name} data must be a dictionary")
            
            for key in required_keys:
                if key not in data:
                    raise ValueError(f"Indicator {name} missing required key: {key}")
                
                if not isinstance(data[key], pd.Series):
                    raise ValueError(f"Indicator {name}.{key} must be a pandas Series")
        
        return True
```

#### **Task 3.5: Indicator Service Implementation**
**File**: `backend/app/services/indicator_service.py`
```python
# Main indicator service following existing service patterns
class IndicatorService(IIndicatorService):
    def __init__(
        self,
        market_data_service: IMarketDataService,
        cache_service: Optional[Any] = None
    ):
        self.market_data_service = market_data_service
        self.cache_service = cache_service or get_redis_client()
        self.rsi_calculator = RSICalculator()
        self.macd_calculator = MACDCalculator()
        self.momentum_calculator = MomentumCalculator()
        self.signal_composer = SignalComposer()
    
    async def calculate_rsi(
        self, 
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        period: int = 14
    ) -> ServiceResult[IndicatorResult]:
        """RSI calculation with caching following existing patterns"""
        try:
            # Check cache first
            cache_key = f"rsi:{symbol}:{period}:{start_date.date()}:{end_date.date()}"
            cached_result = await self._get_cached_result(cache_key)
            if cached_result:
                return ServiceResult.success(
                    data=cached_result,
                    message=f"RSI for {symbol} retrieved from cache",
                    metadata={"source": "cache", "symbol": symbol}
                )
            
            # Fetch market data
            market_data = await self.market_data_service.fetch_historical_data(
                symbols=[symbol],
                start_date=start_date,
                end_date=end_date
            )
            
            if not market_data.success or symbol not in market_data.data:
                return ServiceResult.error(
                    error=f"No market data available for {symbol}",
                    message="RSI calculation failed due to missing market data"
                )
            
            # Convert to DataFrame for calculation
            price_data = self._market_data_to_dataframe(market_data.data[symbol])
            
            # Validate data sufficiency
            self.rsi_calculator.validate_data(price_data, period)
            
            # Calculate RSI
            rsi_result = self.rsi_calculator.calculate(price_data, period)
            
            # Create result object
            indicator_result = IndicatorResult(
                symbol=symbol,
                indicator_type="rsi",
                values=rsi_result['values'].to_dict(),
                signals=rsi_result['signals'].to_dict(),
                parameters=rsi_result['parameters'],
                calculated_at=datetime.now(),
                confidence=0.95  # RSI is highly reliable
            )
            
            # Cache result
            await self._cache_result(cache_key, indicator_result, ttl_seconds=3600)
            
            return ServiceResult.success(
                data=indicator_result,
                message=f"RSI calculated for {symbol}",
                metadata={"source": "calculated", "data_points": len(price_data)}
            )
            
        except Exception as e:
            logger.error(f"RSI calculation failed for {symbol}: {e}")
            return ServiceResult.error(
                error=str(e),
                message=f"RSI calculation failed for {symbol}"
            )
    
    async def calculate_bulk_indicators(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        indicators: List[str] = ["rsi", "macd", "momentum"]
    ) -> ServiceResult[Dict[str, Dict[str, IndicatorResult]]]:
        """
        Bulk indicator calculation optimized for performance
        Target: <2s for 1000 assets (per 1_spec.md requirement)
        """
        start_time = time.time()
        
        try:
            # Process in batches to avoid memory issues and respect rate limits
            batch_size = min(50, len(symbols))  # Adjust based on API limits
            results = {}
            
            # Use asyncio.gather for concurrent processing
            tasks = []
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                tasks.append(self._process_symbol_batch(batch, start_date, end_date, indicators))
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine results
            for batch_result in batch_results:
                if isinstance(batch_result, dict):
                    results.update(batch_result)
                else:
                    logger.error(f"Batch processing error: {batch_result}")
            
            processing_time = time.time() - start_time
            
            # Validate performance requirement
            if processing_time > 2.0 and len(symbols) <= 1000:
                logger.warning(
                    f"Performance target missed: {processing_time:.2f}s for {len(symbols)} symbols"
                )
            
            return ServiceResult.success(
                data=results,
                message=f"Bulk indicators calculated for {len(symbols)} symbols",
                metadata={
                    "processing_time_seconds": round(processing_time, 2),
                    "symbols_processed": len(results),
                    "indicators": indicators,
                    "performance_target_met": processing_time <= 2.0 or len(symbols) > 1000
                }
            )
            
        except Exception as e:
            logger.error(f"Bulk indicator calculation failed: {e}")
            return ServiceResult.error(
                error=str(e),
                message="Bulk indicator calculation failed"
            )
    
    async def _process_symbol_batch(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        indicators: List[str]
    ) -> Dict[str, Dict[str, IndicatorResult]]:
        """Process a batch of symbols for indicators"""
        batch_results = {}
        
        for symbol in symbols:
            symbol_indicators = {}
            
            if "rsi" in indicators:
                rsi_result = await self.calculate_rsi(symbol, start_date, end_date)
                if rsi_result.success:
                    symbol_indicators["rsi"] = rsi_result.data
            
            if "macd" in indicators:
                macd_result = await self.calculate_macd(symbol, start_date, end_date)
                if macd_result.success:
                    symbol_indicators["macd"] = macd_result.data
            
            if "momentum" in indicators:
                momentum_result = await self.calculate_momentum(symbol, start_date, end_date)
                if momentum_result.success:
                    symbol_indicators["momentum"] = momentum_result.data
            
            if symbol_indicators:
                batch_results[symbol] = symbol_indicators
        
        return batch_results
    
    def _market_data_to_dataframe(self, market_data: MarketData) -> pd.DataFrame:
        """Convert MarketData to pandas DataFrame for calculations"""
        # Implementation depends on MarketData structure
        # This should handle OHLCV data conversion
        pass
    
    async def _get_cached_result(self, cache_key: str) -> Optional[IndicatorResult]:
        """Get cached indicator result"""
        try:
            cached_data = await self.cache_service.get(cache_key)
            if cached_data:
                return IndicatorResult.parse_raw(cached_data)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        return None
    
    async def _cache_result(
        self, 
        cache_key: str, 
        result: IndicatorResult, 
        ttl_seconds: int = 3600
    ):
        """Cache indicator result"""
        try:
            await self.cache_service.setex(
                cache_key, 
                ttl_seconds, 
                result.json()
            )
        except Exception as e:
            logger.warning(f"Cache storage failed: {e}")
```

---

## **🚀 THURSDAY: API Endpoints & Performance Optimization**

### **Morning (3 hours): FastAPI Endpoint Implementation**

#### **Task 4.1: Market Data API Endpoints**
**File**: `backend/app/api/v1/market_data.py`
```python
# Market data API endpoints following existing patterns
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from datetime import datetime, date
from ..auth import get_current_user
from ...services.interfaces.market_data_service import IMarketDataService
from ...services.interfaces.models import *

router = APIRouter()

# Dependency injection following existing patterns
def get_market_data_service() -> IMarketDataService:
    return get_circuit_breaker_market_data_service()

@router.get("/historical/{symbol}", response_model=ServiceResult[MarketData])
async def get_historical_data(
    symbol: str,
    start_date: date = Query(..., description="Start date for historical data"),
    end_date: date = Query(default_factory=date.today, description="End date for historical data"),
    interval: str = Query("1d", regex="^(1m|5m|15m|30m|1h|1d|1wk|1mo)$"),
    current_user: User = Depends(get_current_user),
    market_data_service: IMarketDataService = Depends(get_market_data_service)
):
    """
    Get historical market data for a symbol
    Following existing API patterns with ServiceResult wrapper
    """
    try:
        # Validate symbol format
        if not re.match(r'^[A-Z]{1,5}$', symbol.upper()):
            raise HTTPException(
                status_code=400,
                detail="Invalid symbol format. Must be 1-5 uppercase letters."
            )
        
        # Validate date range
        if start_date >= end_date:
            raise HTTPException(
                status_code=400,
                detail="Start date must be before end date"
            )
        
        # Convert dates to datetime
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Fetch data
        result = await market_data_service.fetch_historical_data(
            symbols=[symbol.upper()],
            start_date=start_datetime,
            end_date=end_datetime,
            interval=interval
        )
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        if symbol.upper() not in result.data:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for symbol {symbol}"
            )
        
        # Return single symbol data wrapped in ServiceResult
        return ServiceResult.success(
            data=result.data[symbol.upper()],
            message=f"Historical data for {symbol}",
            metadata={
                "symbol": symbol.upper(),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "interval": interval,
                "data_points": len(result.data[symbol.upper()].ohlcv_data) if hasattr(result.data[symbol.upper()], 'ohlcv_data') else 0
            },
            next_actions=[
                "calculate_technical_indicators",
                "create_price_chart",
                "add_to_watchlist"
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Historical data fetch failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/bulk-historical", response_model=ServiceResult[Dict[str, MarketData]])
@limiter.limit("10/minute")  # Stricter rate limiting for bulk operations
async def get_bulk_historical_data(
    request: Request,
    symbols: str = Query(..., description="Comma-separated list of symbols (max 50)"),
    start_date: date = Query(..., description="Start date for historical data"),
    end_date: date = Query(default_factory=date.today, description="End date"),
    interval: str = Query("1d", regex="^(1m|5m|15m|30m|1h|1d|1wk|1mo)$"),
    current_user: User = Depends(get_current_user),
    market_data_service: IMarketDataService = Depends(get_market_data_service)
):
    """Bulk historical data fetch with performance monitoring"""
    start_time = time.time()
    
    try:
        # Parse and validate symbols
        symbol_list = [s.strip().upper() for s in symbols.split(',')]
        symbol_list = [s for s in symbol_list if s]  # Remove empty strings
        
        if len(symbol_list) > 50:
            raise HTTPException(
                status_code=400,
                detail="Maximum 50 symbols allowed per request"
            )
        
        if not symbol_list:
            raise HTTPException(
                status_code=400,
                detail="At least one symbol must be provided"
            )
        
        # Validate all symbols
        invalid_symbols = [s for s in symbol_list if not re.match(r'^[A-Z]{1,5}$', s)]
        if invalid_symbols:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid symbol format: {', '.join(invalid_symbols)}"
            )
        
        # Fetch data
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        result = await market_data_service.fetch_historical_data(
            symbols=symbol_list,
            start_date=start_datetime,
            end_date=end_datetime,
            interval=interval
        )
        
        processing_time = time.time() - start_time
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        # Add performance metadata
        result.metadata.update({
            "processing_time_seconds": round(processing_time, 2),
            "symbols_requested": len(symbol_list),
            "symbols_returned": len(result.data),
            "performance_target_met": processing_time <= 5.0,  # 5s target for bulk
            "rate_limit_remaining": "9 requests"  # Would be dynamic in production
        })
        
        result.next_actions = [
            "calculate_bulk_indicators",
            "create_correlation_matrix",
            "compare_performance"
        ]
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk historical data fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/real-time", response_model=ServiceResult[Dict[str, PriceData]])
@limiter.limit("60/minute")  # Higher rate limit for real-time data
async def get_real_time_prices(
    request: Request,
    symbols: str = Query(..., description="Comma-separated symbols"),
    current_user: User = Depends(get_current_user),
    market_data_service: IMarketDataService = Depends(get_market_data_service)
):
    """Real-time price data with <100ms target"""
    start_time = time.time()
    
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(',')]
        symbol_list = [s for s in symbol_list if s and re.match(r'^[A-Z]{1,5}$', s)]
        
        if not symbol_list:
            raise HTTPException(status_code=400, detail="No valid symbols provided")
        
        if len(symbol_list) > 20:
            raise HTTPException(
                status_code=400,
                detail="Maximum 20 symbols for real-time data"
            )
        
        result = await market_data_service.fetch_real_time_prices(symbol_list)
        
        processing_time = time.time() - start_time
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        # Validate performance target
        performance_target_met = processing_time <= 0.1  # 100ms target
        
        result.metadata.update({
            "processing_time_ms": round(processing_time * 1000, 2),
            "performance_target_met": performance_target_met,
            "data_freshness_seconds": 0  # Real-time data
        })
        
        if not performance_target_met:
            logger.warning(
                f"Real-time data performance target missed: {processing_time*1000:.2f}ms"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Real-time price fetch failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health", response_model=ServiceResult[Dict[str, Any]])
async def market_data_health_check(
    market_data_service: IMarketDataService = Depends(get_market_data_service)
):
    """Market data service health check"""
    try:
        # Test connectivity to providers
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "providers": {},
            "overall_status": "healthy"
        }
        
        # Test primary provider
        try:
            test_result = await market_data_service.fetch_real_time_prices(["AAPL"])
            health_data["providers"]["primary"] = {
                "status": "healthy" if test_result.success else "degraded",
                "response_time_ms": test_result.metadata.get("processing_time_ms", 0)
            }
        except Exception as e:
            health_data["providers"]["primary"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Determine overall status
        provider_statuses = [p["status"] for p in health_data["providers"].values()]
        if "failed" in provider_statuses:
            health_data["overall_status"] = "degraded"
        
        return ServiceResult.success(
            data=health_data,
            message="Market data service health check completed"
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return ServiceResult.error(
            error=str(e),
            message="Market data service health check failed"
        )
```

#### **Task 4.2: Indicators API Endpoints**  
**File**: `backend/app/api/v1/indicators.py`
```python
# Technical indicators API endpoints
router = APIRouter()

@router.post("/calculate", response_model=ServiceResult[Dict[str, IndicatorResult]])
async def calculate_indicators(
    request: IndicatorCalculationRequest,
    current_user: User = Depends(get_current_user),
    indicator_service: IIndicatorService = Depends(get_indicator_service)
):
    """
    Calculate technical indicators for symbols
    Performance target: <2s for 1000 assets (per 1_spec.md)
    """
    start_time = time.time()
    
    try:
        # Validate request
        if not request.symbols:
            raise HTTPException(status_code=400, detail="At least one symbol required")
        
        if len(request.symbols) > 1000:
            raise HTTPException(
                status_code=400,
                detail="Maximum 1000 symbols per request"
            )
        
        # Calculate indicators
        result = await indicator_service.calculate_bulk_indicators(
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            indicators=request.indicators
        )
        
        processing_time = time.time() - start_time
        
        # Add performance validation
        performance_target_met = processing_time <= 2.0 or len(request.symbols) <= 1000
        
        if result.success:
            result.metadata.update({
                "processing_time_seconds": round(processing_time, 2),
                "performance_target_met": performance_target_met,
                "per_symbol_avg_ms": round((processing_time * 1000) / len(request.symbols), 2)
            })
            
            result.next_actions = [
                "generate_composite_signals",
                "create_strategy_from_signals",
                "backtest_signal_performance"
            ]
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Indicator calculation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/signals/composite", response_model=ServiceResult[Dict[str, CompositeSignal]])
async def generate_composite_signals(
    request: CompositeSignalRequest,
    current_user: User = Depends(get_current_user),
    indicator_service: IIndicatorService = Depends(get_indicator_service)
):
    """
    Generate composite signals with conflict resolution
    Following MACD > RSI > Momentum hierarchy per 1_spec.md
    """
    try:
        # Validate weights sum to 1.0
        if request.weights:
            total_weight = sum(request.weights.values())
            if not 0.99 <= total_weight <= 1.01:
                raise HTTPException(
                    status_code=400,
                    detail="Indicator weights must sum to 1.0"
                )
        
        result = await indicator_service.generate_composite_signals(
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            indicators=request.indicators,
            weights=request.weights
        )
        
        if result.success:
            result.next_actions = [
                "create_trading_strategy",
                "backtest_composite_signals",
                "analyze_signal_performance"
            ]
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Composite signal generation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### **Afternoon (4 hours): Performance Optimization & Caching**

#### **Task 4.3: Redis Caching Strategy**
**File**: `backend/app/services/cache/indicator_cache_service.py`
```python
# Intelligent caching for indicators following existing patterns
class IndicatorCacheService:
    def __init__(self, redis_client: Optional[Any] = None):
        self.redis = redis_client or get_redis_client()
        self.default_ttl = 3600  # 1 hour for indicators
        self.real_time_ttl = 300  # 5 minutes for real-time data
        
    async def get_cached_indicators(
        self,
        symbol: str,
        indicator_type: str,
        parameters: Dict[str, Any],
        start_date: datetime,
        end_date: datetime
    ) -> Optional[IndicatorResult]:
        """Get cached indicator results with parameter-aware keys"""
        cache_key = self._build_cache_key(
            symbol, indicator_type, parameters, start_date, end_date
        )
        
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                result = IndicatorResult.parse_raw(cached_data)
                
                # Validate cache freshness
                cache_age = datetime.now() - result.calculated_at
                if cache_age.total_seconds() < self.default_ttl:
                    return result
                else:
                    # Cache expired, remove it
                    await self.redis.delete(cache_key)
                    
        except Exception as e:
            logger.warning(f"Cache retrieval failed for {cache_key}: {e}")
            
        return None
    
    async def cache_indicators(
        self,
        symbol: str,
        indicator_type: str,
        parameters: Dict[str, Any],
        start_date: datetime,
        end_date: datetime,
        result: IndicatorResult,
        ttl_seconds: Optional[int] = None
    ):
        """Cache indicator results with intelligent TTL"""
        cache_key = self._build_cache_key(
            symbol, indicator_type, parameters, start_date, end_date
        )
        
        ttl = ttl_seconds or self._calculate_ttl(start_date, end_date)
        
        try:
            await self.redis.setex(
                cache_key,
                ttl,
                result.json()
            )
            
            # Also add to symbol index for cache invalidation
            await self._add_to_symbol_index(symbol, cache_key)
            
        except Exception as e:
            logger.warning(f"Cache storage failed for {cache_key}: {e}")
    
    async def invalidate_symbol_cache(self, symbol: str):
        """Invalidate all cached data for a symbol"""
        try:
            index_key = f"symbol_cache_index:{symbol}"
            cache_keys = await self.redis.smembers(index_key)
            
            if cache_keys:
                await self.redis.delete(*cache_keys)
                await self.redis.delete(index_key)
                
            logger.info(f"Invalidated {len(cache_keys)} cache entries for {symbol}")
            
        except Exception as e:
            logger.error(f"Cache invalidation failed for {symbol}: {e}")
    
    def _build_cache_key(
        self,
        symbol: str,
        indicator_type: str,
        parameters: Dict[str, Any],
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """Build cache key from parameters"""
        param_hash = hashlib.md5(
            json.dumps(parameters, sort_keys=True).encode()
        ).hexdigest()[:8]
        
        return (
            f"indicator:{indicator_type}:{symbol}:"
            f"{start_date.date()}:{end_date.date()}:{param_hash}"
        )
    
    def _calculate_ttl(self, start_date: datetime, end_date: datetime) -> int:
        """Calculate TTL based on date range"""
        now = datetime.now()
        
        # Real-time data (today) expires quickly
        if end_date.date() >= now.date():
            return self.real_time_ttl
        
        # Historical data can be cached longer
        days_old = (now.date() - end_date.date()).days
        if days_old > 30:
            return 86400  # 24 hours for old data
        else:
            return self.default_ttl
    
    async def _add_to_symbol_index(self, symbol: str, cache_key: str):
        """Add cache key to symbol index for invalidation"""
        index_key = f"symbol_cache_index:{symbol}"
        await self.redis.sadd(index_key, cache_key)
        await self.redis.expire(index_key, 86400)  # Index expires in 24 hours
```

#### **Task 4.4: Performance Monitoring & Optimization**
**File**: `backend/app/services/monitoring/performance_monitor.py`
```python
# Performance monitoring for Sprint 3 requirements
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
        self.performance_targets = {
            "market_data_real_time": 0.1,      # 100ms
            "market_data_historical": 0.5,     # 500ms  
            "indicator_calculation_1000": 2.0, # 2s for 1000 assets
            "websocket_connection": 1.0         # 1s connection time
        }
    
    async def measure_performance(self, operation: str, func, *args, **kwargs):
        """Measure and record performance of operations"""
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            processing_time = time.time() - start_time
            
            # Record metrics
            await self._record_metric(operation, processing_time, success=True)
            
            # Check against targets
            target_met = self._check_target(operation, processing_time, *args, **kwargs)
            
            # Add performance metadata to result
            if hasattr(result, 'metadata'):
                result.metadata.update({
                    "processing_time_seconds": round(processing_time, 3),
                    "performance_target_met": target_met,
                    "operation": operation
                })
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            await self._record_metric(operation, processing_time, success=False)
            raise e
    
    def _check_target(self, operation: str, processing_time: float, *args, **kwargs) -> bool:
        """Check if operation met performance targets"""
        
        if operation == "indicator_calculation_bulk":
            # Special handling for bulk operations
            symbol_count = len(kwargs.get('symbols', []))
            if symbol_count <= 1000:
                return processing_time <= self.performance_targets["indicator_calculation_1000"]
            else:
                # Proportional target for larger batches
                target = (symbol_count / 1000) * 2.0
                return processing_time <= target
        
        target = self.performance_targets.get(operation)
        if target:
            return processing_time <= target
        
        return True  # No target defined
    
    async def _record_metric(self, operation: str, processing_time: float, success: bool):
        """Record performance metrics"""
        timestamp = datetime.now()
        
        if operation not in self.metrics:
            self.metrics[operation] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_time": 0.0,
                "average_time": 0.0,
                "max_time": 0.0,
                "min_time": float('inf'),
                "recent_times": []
            }
        
        metric = self.metrics[operation]
        metric["total_calls"] += 1
        
        if success:
            metric["successful_calls"] += 1
        else:
            metric["failed_calls"] += 1
        
        metric["total_time"] += processing_time
        metric["average_time"] = metric["total_time"] / metric["total_calls"]
        metric["max_time"] = max(metric["max_time"], processing_time)
        metric["min_time"] = min(metric["min_time"], processing_time)
        
        # Keep recent times for trend analysis (last 100 calls)
        metric["recent_times"].append((timestamp, processing_time))
        if len(metric["recent_times"]) > 100:
            metric["recent_times"].pop(0)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "targets": self.performance_targets,
            "operations": {}
        }
        
        for operation, metrics in self.metrics.items():
            target = self.performance_targets.get(operation)
            success_rate = (metrics["successful_calls"] / metrics["total_calls"]) * 100
            
            # Calculate recent average (last 10 calls)
            recent_times = [t[1] for t in metrics["recent_times"][-10:]]
            recent_average = sum(recent_times) / len(recent_times) if recent_times else 0
            
            report["operations"][operation] = {
                "total_calls": metrics["total_calls"],
                "success_rate": round(success_rate, 2),
                "average_time": round(metrics["average_time"], 3),
                "recent_average": round(recent_average, 3),
                "max_time": round(metrics["max_time"], 3),
                "min_time": round(metrics["min_time"], 3),
                "target": target,
                "target_met": recent_average <= target if target else True
            }
        
        return report

# Global performance monitor instance
performance_monitor = PerformanceMonitor()
```

---

## **🧪 FRIDAY: Comprehensive Testing & Integration**

### **Morning (3 hours): Real Data Testing Implementation**

#### **Task 5.1: Integration Tests with Real APIs**
**File**: `backend/app/tests/test_market_data_integration.py`
```python
# Real data integration tests following existing patterns
import pytest
import asyncio
from datetime import datetime, timedelta, date
from unittest.mock import AsyncMock, patch

from app.services.market_data_service import MarketDataService
from app.services.indicator_service import IndicatorService
from app.services.providers.yahoo_data_provider import YahooDataProvider
from app.services.providers.alpha_vantage_provider import AlphaVantageProvider
from app.core.circuit_breaker import CircuitBreakerMarketDataService

# Test markers following existing pattern
pytestmark = [
    pytest.mark.integration,
    pytest.mark.market_data,
    pytest.mark.asyncio
]

class TestMarketDataIntegration:
    """
    Integration tests with real market data APIs
    Following established real data testing approach
    """
    
    @pytest.fixture
    async def yahoo_provider(self):
        """Yahoo Finance provider for testing"""
        return YahooDataProvider()
    
    @pytest.fixture
    async def alpha_vantage_provider(self):
        """Alpha Vantage provider for testing"""  
        return AlphaVantageProvider()
    
    @pytest.fixture
    async def circuit_breaker_service(self, yahoo_provider, alpha_vantage_provider):
        """Circuit breaker service with real providers"""
        return CircuitBreakerMarketDataService(
            primary=yahoo_provider,
            fallback=alpha_vantage_provider,
            failure_threshold=3,
            timeout_seconds=30
        )
    
    async def test_yahoo_real_time_data_fetch(self, yahoo_provider):
        """Test Yahoo Finance real-time data with actual API call"""
        symbols = ["AAPL", "MSFT", "GOOGL"]
        
        result = await yahoo_provider.fetch_real_time_prices(symbols)
        
        # Validate result structure
        assert result.success is True
        assert isinstance(result.data, dict)
        assert len(result.data) == len(symbols)
        
        # Validate data quality
        for symbol in symbols:
            assert symbol in result.data
            price_data = result.data[symbol]
            
            # Validate price data structure
            assert hasattr(price_data, 'current_price')
            assert isinstance(price_data.current_price, (int, float))
            assert price_data.current_price > 0
            
            # Validate timestamp freshness (within 15 minutes per spec)
            assert hasattr(price_data, 'timestamp')
            data_age = datetime.now() - price_data.timestamp
            assert data_age.total_seconds() < 900  # 15 minutes
        
        # Validate performance target
        processing_time = result.metadata.get('processing_time_seconds', float('inf'))
        assert processing_time < 0.1, f"Real-time fetch took {processing_time}s, target is 0.1s"
    
    async def test_historical_data_validation(self, yahoo_provider):
        """Test historical data with comprehensive validation"""
        symbols = ["AAPL"]
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        result = await yahoo_provider.fetch_historical_data(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            interval="1d"
        )
        
        assert result.success is True
        assert "AAPL" in result.data
        
        market_data = result.data["AAPL"]
        
        # Validate OHLCV data completeness
        assert hasattr(market_data, 'ohlcv_data')
        assert len(market_data.ohlcv_data) > 0
        
        for data_point in market_data.ohlcv_data:
            # OHLCV validation
            assert data_point.open > 0
            assert data_point.high > 0
            assert data_point.low > 0
            assert data_point.close > 0
            assert data_point.volume >= 0
            
            # Price relationship validation
            assert data_point.high >= data_point.open
            assert data_point.high >= data_point.close
            assert data_point.low <= data_point.open
            assert data_point.low <= data_point.close
            
            # Date validation
            assert start_date <= data_point.timestamp <= end_date
    
    async def test_circuit_breaker_failover(self, circuit_breaker_service):
        """Test automatic failover to backup provider"""
        symbols = ["AAPL", "MSFT"]
        
        # First, test normal operation
        result = await circuit_breaker_service.fetch_real_time_prices(symbols)
        assert result.success is True
        
        # Simulate primary provider failure
        with patch.object(
            circuit_breaker_service.primary, 
            'fetch_real_time_prices',
            side_effect=Exception("Primary provider failed")
        ):
            # Should failover to backup
            result = await circuit_breaker_service.fetch_real_time_prices(symbols)
            
            # Should still succeed with fallback
            assert result.success is True
            assert result.metadata.get('fallback_used') is True
            
            # Validate data quality from fallback
            for symbol in symbols:
                assert symbol in result.data
                price_data = result.data[symbol]
                assert price_data.current_price > 0
    
    async def test_data_freshness_validation(self, yahoo_provider):
        """Test data freshness validation per 1_spec.md requirement"""
        symbols = ["AAPL"]
        
        result = await yahoo_provider.fetch_real_time_prices(symbols)
        assert result.success is True
        
        price_data = result.data["AAPL"]
        
        # Test freshness validation
        is_fresh = await yahoo_provider.validate_data_freshness(
            data=price_data,
            max_age_minutes=15
        )
        assert is_fresh.success is True
        
        # Test stale data rejection
        # Create artificially old data
        old_data = price_data
        old_data.timestamp = datetime.now() - timedelta(minutes=20)
        
        is_fresh = await yahoo_provider.validate_data_freshness(
            data=old_data,
            max_age_minutes=15
        )
        assert is_fresh.success is False
        assert "too old" in is_fresh.error.lower()
    
    async def test_rate_limiting_compliance(self, yahoo_provider):
        """Test rate limiting doesn't break functionality"""
        symbols = ["AAPL"] * 10  # Multiple requests for same symbol
        
        start_time = datetime.now()
        
        # Make multiple rapid requests
        tasks = []
        for _ in range(5):
            task = yahoo_provider.fetch_real_time_prices(["AAPL"])
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # All requests should succeed (rate limiting should delay, not fail)
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 5
        
        # Processing should be throttled (longer than unthrottled time)
        assert processing_time > 1.0  # Should be throttled
        
        for result in successful_results:
            assert result.success is True
            assert "AAPL" in result.data

class TestIndicatorIntegration:
    """Integration tests for indicator calculations with real data"""
    
    @pytest.fixture
    async def indicator_service(self, circuit_breaker_service):
        """Indicator service with real market data"""
        return IndicatorService(market_data_service=circuit_breaker_service)
    
    async def test_rsi_calculation_with_real_data(self, indicator_service):
        """Test RSI calculation with real market data"""
        symbol = "AAPL"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)  # Need enough data for RSI
        
        result = await indicator_service.calculate_rsi(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            period=14
        )
        
        assert result.success is True
        
        indicator_result = result.data
        assert indicator_result.symbol == symbol
        assert indicator_result.indicator_type == "rsi"
        
        # Validate RSI values (should be between 0 and 100)
        for timestamp, value in indicator_result.values.items():
            assert 0 <= value <= 100
        
        # Validate signals format (-1, 0, 1)
        for timestamp, signal in indicator_result.signals.items():
            assert signal in [-1, 0, 1]
        
        # Check parameters match request
        assert indicator_result.parameters['period'] == 14
        
        # Validate confidence
        assert 0 <= indicator_result.confidence <= 1
    
    async def test_bulk_indicator_performance(self, indicator_service):
        """
        Test bulk indicator calculation performance
        Target: <2s for 1000 assets (per 1_spec.md requirement)
        """
        # Use smaller sample for CI/testing, but validate scaling
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]  # 5 symbols
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        start_time = datetime.now()
        
        result = await indicator_service.calculate_bulk_indicators(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            indicators=["rsi", "macd", "momentum"]
        )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        assert result.success is True
        assert len(result.data) == len(symbols)
        
        # Validate performance scaling
        per_symbol_time = processing_time / len(symbols)
        projected_1000_time = per_symbol_time * 1000
        
        # Should project to under 2 seconds for 1000 symbols
        assert projected_1000_time < 2.0, (
            f"Performance scaling issue: {per_symbol_time:.3f}s per symbol "
            f"projects to {projected_1000_time:.2f}s for 1000 symbols"
        )
        
        # Validate result structure
        for symbol, indicators in result.data.items():
            assert symbol in symbols
            assert "rsi" in indicators
            assert "macd" in indicators  
            assert "momentum" in indicators
            
            for indicator_name, indicator_result in indicators.items():
                assert indicator_result.symbol == symbol
                assert indicator_result.indicator_type == indicator_name
    
    async def test_composite_signal_hierarchy(self, indicator_service):
        """Test composite signal hierarchy: MACD > RSI > Momentum"""
        symbol = "AAPL"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        # Generate individual indicators
        indicators = {}
        
        rsi_result = await indicator_service.calculate_rsi(symbol, start_date, end_date)
        assert rsi_result.success
        indicators["rsi"] = {"signals": pd.Series(rsi_result.data.signals)}
        
        macd_result = await indicator_service.calculate_macd(symbol, start_date, end_date)
        assert macd_result.success
        indicators["macd"] = {"signals": pd.Series(macd_result.data.signals)}
        
        # Test composite signal generation
        composite_result = await indicator_service.generate_composite_signals(
            symbols=[symbol],
            start_date=start_date,
            end_date=end_date,
            indicators=["rsi", "macd"],
            weights={"rsi": 0.3, "macd": 0.7}
        )
        
        assert composite_result.success is True
        
        composite_signal = composite_result.data[symbol]
        
        # Validate that MACD takes priority in conflicts
        macd_signals = pd.Series(macd_result.data.signals)
        composite_signals = pd.Series(composite_signal.signals)
        
        # Where MACD has strong signal (±1), composite should match
        strong_macd = macd_signals[abs(macd_signals) == 1]
        if not strong_macd.empty:
            for timestamp in strong_macd.index:
                if timestamp in composite_signals.index:
                    assert composite_signals[timestamp] == macd_signals[timestamp], \
                        "MACD priority not respected in composite signals"

class TestPerformanceValidation:
    """Performance validation tests for Sprint 3 requirements"""
    
    async def test_real_time_performance_target(self):
        """Validate <100ms target for real-time data"""
        provider = YahooDataProvider()
        symbols = ["AAPL", "MSFT"]
        
        # Warm up (first call may be slower due to connection setup)
        await provider.fetch_real_time_prices(symbols)
        
        # Measure actual performance
        start_time = datetime.now()
        result = await provider.fetch_real_time_prices(symbols)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        assert result.success is True
        assert processing_time < 0.1, f"Real-time fetch took {processing_time*1000:.2f}ms, target is 100ms"
    
    async def test_historical_data_performance_target(self):
        """Validate <500ms target for historical data"""
        provider = YahooDataProvider()
        symbol = "AAPL"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # 1 year of data
        
        start_time = datetime.now()
        result = await provider.fetch_historical_data(
            symbols=[symbol],
            start_date=start_date,
            end_date=end_date
        )
        processing_time = (datetime.now() - start_time).total_seconds()
        
        assert result.success is True
        assert processing_time < 0.5, f"Historical fetch took {processing_time*1000:.2f}ms, target is 500ms"
    
    @pytest.mark.slow
    async def test_websocket_connection_performance(self):
        """Test WebSocket connection establishment <1s target"""
        from app.services.websocket_manager import WebSocketMarketDataManager
        
        market_data_service = MarketDataService()  # Use real service
        manager = WebSocketMarketDataManager(market_data_service)
        
        # Mock WebSocket for testing
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        
        start_time = datetime.now()
        await manager.connect(mock_websocket, "test_user")
        connection_time = (datetime.now() - start_time).total_seconds()
        
        assert connection_time < 1.0, f"WebSocket connection took {connection_time:.2f}s, target is 1s"
        
        # Cleanup
        await manager.disconnect(mock_websocket, "test_user")

# Test configuration
@pytest.fixture(autouse=True)
async def setup_test_environment():
    """Setup test environment with proper configuration"""
    # Ensure test environment variables are set
    import os
    if not os.getenv('ALPHA_VANTAGE_API_KEY'):
        pytest.skip("ALPHA_VANTAGE_API_KEY not set, skipping integration tests")
    
    # Set test-appropriate rate limits
    from app.services.providers.yahoo_data_provider import YahooDataProvider
    YahooDataProvider.request_delay = 0.1  # Faster for testing
```

#### **Task 5.2: Security Testing**
**File**: `backend/app/tests/test_market_data_security.py`
```python
# Security tests for market data following existing security patterns
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.core.config import settings

# Following existing security test patterns
pytestmark = [
    pytest.mark.security,
    pytest.mark.market_data
]

class TestMarketDataSecurity:
    """Security tests for market data endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def authenticated_headers(self, test_user_token):
        return {"Authorization": f"Bearer {test_user_token}"}
    
    def test_unauthenticated_access_blocked(self, client):
        """Test that unauthenticated requests are blocked"""
        endpoints = [
            "/api/v1/market-data/historical/AAPL",
            "/api/v1/market-data/real-time?symbols=AAPL",
            "/api/v1/indicators/calculate"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
            assert "authentication" in response.json()["detail"].lower()
    
    def test_sql_injection_protection(self, client, authenticated_headers):
        """Test SQL injection prevention in symbol parameters"""
        malicious_symbols = [
            "AAPL'; DROP TABLE assets; --",
            "AAPL' UNION SELECT * FROM users --",
            "'; DELETE FROM price_history; --",
        ]
        
        for malicious_symbol in malicious_symbols:
            response = client.get(
                f"/api/v1/market-data/historical/{malicious_symbol}",
                headers=authenticated_headers,
                params={
                    "start_date": "2023-01-01",
                    "end_date": "2023-01-31"
                }
            )
            
            # Should reject invalid symbol format, not execute SQL
            assert response.status_code == 400
            assert "invalid symbol format" in response.json()["detail"].lower()
    
    def test_xss_prevention_in_responses(self, client, authenticated_headers):
        """Test XSS prevention in API responses"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>"
        ]
        
        for payload in xss_payloads:
            response = client.get(
                f"/api/v1/market-data/historical/{payload}",
                headers=authenticated_headers,
                params={
                    "start_date": "2023-01-01", 
                    "end_date": "2023-01-31"
                }
            )
            
            # Should reject and sanitize
            assert response.status_code == 400
            response_text = response.text
            
            # Ensure no script tags in response
            assert "<script>" not in response_text
            assert "javascript:" not in response_text
            assert "onerror=" not in response_text
    
    def test_rate_limiting_enforcement(self, client, authenticated_headers):
        """Test rate limiting prevents abuse"""
        # Test real-time endpoint rate limits (60/minute)
        for i in range(65):  # Exceed limit
            response = client.get(
                "/api/v1/market-data/real-time",
                headers=authenticated_headers,
                params={"symbols": "AAPL"}
            )
            
            if i < 60:
                assert response.status_code in [200, 500]  # Normal or service error
            else:
                # Should be rate limited
                assert response.status_code == 429
                assert "rate limit" in response.json()["detail"].lower()
    
    def test_input_validation_comprehensive(self, client, authenticated_headers):
        """Test comprehensive input validation"""
        
        # Test invalid date formats
        invalid_dates = [
            "not-a-date",
            "2023-13-01",  # Invalid month
            "2023-01-32",  # Invalid day
            "2023/01/01",  # Wrong format
        ]
        
        for invalid_date in invalid_dates:
            response = client.get(
                "/api/v1/market-data/historical/AAPL",
                headers=authenticated_headers,
                params={
                    "start_date": invalid_date,
                    "end_date": "2023-01-31"
                }
            )
            assert response.status_code == 422  # Validation error
        
        # Test date range validation
        response = client.get(
            "/api/v1/market-data/historical/AAPL", 
            headers=authenticated_headers,
            params={
                "start_date": "2023-01-31",
                "end_date": "2023-01-01"  # End before start
            }
        )
        assert response.status_code == 400
        assert "start date must be before end date" in response.json()["detail"].lower()
        
        # Test symbol validation
        invalid_symbols = [
            "",           # Empty
            "A" * 10,     # Too long
            "123",        # Numbers
            "AA-BB",      # Special characters
            "apl",        # Lowercase
        ]
        
        for invalid_symbol in invalid_symbols:
            response = client.get(
                f"/api/v1/market-data/historical/{invalid_symbol}",
                headers=authenticated_headers,
                params={
                    "start_date": "2023-01-01",
                    "end_date": "2023-01-31"
                }
            )
            assert response.status_code == 400
    
    def test_api_key_protection(self):
        """Test that API keys are not exposed in responses or logs"""
        from app.services.providers.alpha_vantage_provider import AlphaVantageProvider
        
        provider = AlphaVantageProvider()
        
        # API key should not be in string representation
        provider_str = str(provider)
        assert settings.alpha_vantage_api_key not in provider_str
        
        # API key should not be in __dict__
        if hasattr(provider, '__dict__'):
            dict_str = str(provider.__dict__)
            assert settings.alpha_vantage_api_key not in dict_str
    
    def test_error_information_disclosure(self, client, authenticated_headers):
        """Test that errors don't disclose sensitive information"""
        # Force an error condition
        response = client.get(
            "/api/v1/market-data/historical/NONEXISTENT",
            headers=authenticated_headers,
            params={
                "start_date": "2023-01-01",
                "end_date": "2023-01-31"
            }
        )
        
        error_response = response.json()
        error_detail = str(error_response)
        
        # Should not contain sensitive information
        sensitive_info = [
            settings.alpha_vantage_api_key,
            settings.database_url,
            settings.secret_key,
            "traceback",
            "internal server error"
        ]
        
        for sensitive in sensitive_info:
            if sensitive:  # Only check if value exists
                assert sensitive not in error_detail.lower()
    
    def test_audit_logging_for_financial_operations(self, client, authenticated_headers, caplog):
        """Test that financial operations are properly logged"""
        import logging
        caplog.set_level(logging.INFO)
        
        # Make a request that should be audited
        response = client.get(
            "/api/v1/market-data/real-time",
            headers=authenticated_headers,
            params={"symbols": "AAPL,MSFT"}
        )
        
        # Check that audit log entries were created
        log_messages = [record.message for record in caplog.records]
        
        # Should have audit log entry
        audit_found = any("market_data_access" in msg for msg in log_messages)
        assert audit_found, "Market data access not properly audited"
```

### **Afternoon (4 hours): Database Integration & Final Testing**

#### **Task 5.3: Database Integration Testing**
**File**: `backend/app/tests/test_market_data_database.py`
```python
# Database integration tests following existing patterns
import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.database import get_db_session
from app.models.market_data import PriceHistory, IndicatorCache
from app.models.asset import Asset
from app.services.market_data_service import MarketDataService

pytestmark = [
    pytest.mark.integration,
    pytest.mark.database,
    pytest.mark.asyncio
]

class TestMarketDataDatabase:
    """Database integration tests for market data storage"""
    
    @pytest.fixture
    async def db_session(self):
        """Test database session"""
        async with get_db_session() as session:
            yield session
    
    @pytest.fixture
    async def test_asset(self, db_session: Session):
        """Create test asset for testing"""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc.",
            sector="Technology",
            industry="Consumer Electronics",
            market_cap=3000000000000,
            pe_ratio=25.5,
            dividend_yield=0.005,
            is_validated=True
        )
        
        db_session.add(asset)
        await db_session.commit()
        await db_session.refresh(asset)
        
        return asset
    
    async def test_price_history_storage(self, db_session: Session, test_asset: Asset):
        """Test storing price history data"""
        price_data = PriceHistory(
            asset_id=test_asset.id,
            timestamp=datetime.now(),
            open_price=150.00,
            high_price=155.00,
            low_price=149.00,
            close_price=153.50,
            volume=50000000,
            adjusted_close=153.50,
            data_source="yahoo"
        )
        
        db_session.add(price_data)
        await db_session.commit()
        
        # Verify storage
        stored_price = await db_session.get(PriceHistory, price_data.id)
        assert stored_price is not None
        assert stored_price.asset_id == test_asset.id
        assert stored_price.close_price == 153.50
        assert stored_price.data_source == "yahoo"
        
        # Test relationship
        await db_session.refresh(test_asset, ['price_history'])
        assert len(test_asset.price_history) == 1
        assert test_asset.price_history[0].id == price_data.id
    
    async def test_indicator_cache_storage(self, db_session: Session, test_asset: Asset):
        """Test storing indicator calculations in cache"""
        indicator_data = IndicatorCache(
            asset_id=test_asset.id,
            indicator_type="rsi",
            parameters={"period": 14},
            result_data={
                "values": {"2023-01-01": 65.5, "2023-01-02": 67.2},
                "signals": {"2023-01-01": 0, "2023-01-02": 0}
            },
            calculated_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        db_session.add(indicator_data)
        await db_session.commit()
        
        # Verify storage
        stored_indicator = await db_session.get(IndicatorCache, indicator_data.id)
        assert stored_indicator is not None
        assert stored_indicator.indicator_type == "rsi"
        assert stored_indicator.parameters == {"period": 14}
        assert "values" in stored_indicator.result_data
        assert "signals" in stored_indicator.result_data
        
        # Test relationship
        await db_session.refresh(test_asset, ['indicator_results'])
        assert len(test_asset.indicator_results) == 1
    
    async def test_bulk_price_insertion_performance(
        self, 
        db_session: Session, 
        test_asset: Asset
    ):
        """Test bulk price insertion performance for large datasets"""
        import time
        
        # Generate 1000 price records
        price_records = []
        base_time = datetime.now() - timedelta(days=1000)
        
        for i in range(1000):
            price_records.append(PriceHistory(
                asset_id=test_asset.id,
                timestamp=base_time + timedelta(days=i),
                open_price=150.00 + (i * 0.1),
                high_price=155.00 + (i * 0.1),
                low_price=149.00 + (i * 0.1),
                close_price=153.50 + (i * 0.1),
                volume=50000000 + (i * 1000),
                data_source="yahoo"
            ))
        
        start_time = time.time()
        
        # Bulk insert
        db_session.add_all(price_records)
        await db_session.commit()
        
        insertion_time = time.time() - start_time
        
        # Should insert 1000 records quickly (under 5 seconds)
        assert insertion_time < 5.0, f"Bulk insertion took {insertion_time:.2f}s, should be under 5s"
        
        # Verify insertion
        await db_session.refresh(test_asset, ['price_history'])
        assert len(test_asset.price_history) == 1000
    
    async def test_price_history_querying_performance(
        self, 
        db_session: Session, 
        test_asset: Asset
    ):
        """Test price history query performance with indexes"""
        import time
        
        # First create some test data
        await self.test_bulk_price_insertion_performance(db_session, test_asset)
        
        # Test time-range query performance
        start_date = datetime.now() - timedelta(days=100)
        end_date = datetime.now() - timedelta(days=50)
        
        start_time = time.time()
        
        # Query with time range (should use index)
        query_result = await db_session.execute(
            select(PriceHistory).where(
                PriceHistory.asset_id == test_asset.id,
                PriceHistory.timestamp >= start_date,
                PriceHistory.timestamp <= end_date
            )
        )
        
        price_records = query_result.scalars().all()
        query_time = time.time() - start_time
        
        # Should be fast with proper indexing
        assert query_time < 0.1, f"Query took {query_time:.3f}s, should be under 0.1s"
        assert len(price_records) == 50  # 50 days in range
    
    async def test_database_constraint_enforcement(
        self, 
        db_session: Session, 
        test_asset: Asset
    ):
        """Test database constraints and data integrity"""
        from sqlalchemy.exc import IntegrityError
        
        # Test unique constraint on asset_id + timestamp + data_source
        timestamp = datetime.now()
        
        price1 = PriceHistory(
            asset_id=test_asset.id,
            timestamp=timestamp,
            open_price=150.00,
            high_price=155.00,
            low_price=149.00,
            close_price=153.50,
            volume=50000000,
            data_source="yahoo"
        )
        
        price2 = PriceHistory(
            asset_id=test_asset.id,
            timestamp=timestamp,  # Same timestamp
            open_price=151.00,
            high_price=156.00,
            low_price=150.00,
            close_price=154.50,
            volume=51000000,
            data_source="yahoo"  # Same source
        )
        
        db_session.add(price1)
        await db_session.commit()
        
        # Second insert should fail due to unique constraint
        db_session.add(price2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
    
    async def test_cascade_deletion(self, db_session: Session, test_asset: Asset):
        """Test cascade deletion of related data"""
        # Add price history and indicators
        await self.test_price_history_storage(db_session, test_asset)
        await self.test_indicator_cache_storage(db_session, test_asset)
        
        # Verify data exists
        price_count = await db_session.scalar(
            select(func.count(PriceHistory.id)).where(
                PriceHistory.asset_id == test_asset.id
            )
        )
        indicator_count = await db_session.scalar(
            select(func.count(IndicatorCache.id)).where(
                IndicatorCache.asset_id == test_asset.id
            )
        )
        
        assert price_count > 0
        assert indicator_count > 0
        
        # Delete asset (should cascade)
        await db_session.delete(test_asset)
        await db_session.commit()
        
        # Verify cascade deletion
        remaining_price_count = await db_session.scalar(
            select(func.count(PriceHistory.id)).where(
                PriceHistory.asset_id == test_asset.id
            )
        )
        remaining_indicator_count = await db_session.scalar(
            select(func.count(IndicatorCache.id)).where(
                IndicatorCache.asset_id == test_asset.id
            )
        )
        
        assert remaining_price_count == 0
        assert remaining_indicator_count == 0
```

#### **Task 5.4: End-to-End Integration Testing**
**File**: `backend/app/tests/test_sprint3_e2e.py`
```python
# End-to-end integration tests for complete Sprint 3 workflow
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import json

from app.main import app

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.sprint3,
    pytest.mark.slow
]

class TestSprint3EndToEnd:
    """End-to-end tests for complete Sprint 3 functionality"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def authenticated_headers(self, test_user_token):
        return {"Authorization": f"Bearer {test_user_token}"}
    
    async def test_complete_market_data_to_signals_workflow(
        self, 
        client: TestClient, 
        authenticated_headers: dict
    ):
        """Test complete workflow: Market Data → Indicators → Signals"""
        
        # Step 1: Fetch historical market data
        start_date = (datetime.now() - timedelta(days=60)).date()
        end_date = datetime.now().date()
        
        market_data_response = client.get(
            "/api/v1/market-data/historical/AAPL",
            headers=authenticated_headers,
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )
        
        assert market_data_response.status_code == 200
        market_data = market_data_response.json()
        assert market_data["success"] is True
        assert "data" in market_data
        
        # Step 2: Calculate technical indicators
        indicator_request = {
            "symbols": ["AAPL"],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "indicators": ["rsi", "macd", "momentum"]
        }
        
        indicators_response = client.post(
            "/api/v1/indicators/calculate",
            headers=authenticated_headers,
            json=indicator_request
        )
        
        assert indicators_response.status_code == 200
        indicators_data = indicators_response.json()
        assert indicators_data["success"] is True
        assert "AAPL" in indicators_data["data"]
        
        apple_indicators = indicators_data["data"]["AAPL"]
        assert "rsi" in apple_indicators
        assert "macd" in apple_indicators
        assert "momentum" in apple_indicators
        
        # Step 3: Generate composite signals
        signal_request = {
            "symbols": ["AAPL"],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "indicators": ["rsi", "macd", "momentum"],
            "weights": {"rsi": 0.3, "macd": 0.5, "momentum": 0.2}
        }
        
        signals_response = client.post(
            "/api/v1/indicators/signals/composite",
            headers=authenticated_headers,
            json=signal_request
        )
        
        assert signals_response.status_code == 200
        signals_data = signals_response.json()
        assert signals_data["success"] is True
        assert "AAPL" in signals_data["data"]
        
        # Step 4: Validate signal format and hierarchy
        apple_signals = signals_data["data"]["AAPL"]
        
        # Validate composite signal structure
        assert "signal" in apple_signals  # Final composite signal
        assert "components" in apple_signals  # Individual indicator results
        assert "weights" in apple_signals  # Applied weights
        
        # Validate signal values are in correct format (-1, 0, 1)
        final_signal = apple_signals["signal"]
        assert final_signal in [-1, 0, 1]
        
        # Validate components contain all requested indicators
        components = apple_signals["components"]
        assert "rsi" in components
        assert "macd" in components
        assert "momentum" in components
        
        # Validate weights were applied correctly
        applied_weights = apple_signals["weights"]
        assert applied_weights == {"rsi": 0.3, "macd": 0.5, "momentum": 0.2}
    
    async def test_real_time_data_to_websocket_workflow(
        self,
        client: TestClient,
        authenticated_headers: dict
    ):
        """Test real-time data workflow with WebSocket integration"""
        
        # Step 1: Test real-time price fetch
        realtime_response = client.get(
            "/api/v1/market-data/real-time",
            headers=authenticated_headers,
            params={"symbols": "AAPL,MSFT"}
        )
        
        assert realtime_response.status_code == 200
        realtime_data = realtime_response.json()
        assert realtime_data["success"] is True
        
        # Validate real-time data structure
        prices = realtime_data["data"]
        assert "AAPL" in prices
        assert "MSFT" in prices
        
        for symbol, price_data in prices.items():
            assert "current_price" in price_data
            assert "timestamp" in price_data
            assert price_data["current_price"] > 0
            
            # Validate data freshness
            timestamp = datetime.fromisoformat(price_data["timestamp"])
            data_age = datetime.now() - timestamp
            assert data_age.total_seconds() < 900  # <15 minutes per spec
        
        # Step 2: Test WebSocket connection (mock test)
        # Note: Full WebSocket testing requires specialized test setup
        # This validates the WebSocket endpoint exists and is authenticated
        
        websocket_health = client.get(
            "/api/v1/market-data/health",
            headers=authenticated_headers
        )
        
        assert websocket_health.status_code == 200
        health_data = websocket_health.json()
        assert health_data["success"] is True
    
    async def test_bulk_processing_performance_e2e(
        self,
        client: TestClient,
        authenticated_headers: dict
    ):
        """Test bulk processing performance across the entire pipeline"""
        
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA", "AMZN", "META", "NFLX"]
        start_date = (datetime.now() - timedelta(days=30)).date()
        end_date = datetime.now().date()
        
        # Test bulk historical data fetch
        bulk_request_start = datetime.now()
        
        bulk_response = client.get(
            "/api/v1/market-data/bulk-historical",
            headers=authenticated_headers,
            params={
                "symbols": ",".join(symbols),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )
        
        bulk_fetch_time = (datetime.now() - bulk_request_start).total_seconds()
        
        assert bulk_response.status_code == 200
        bulk_data = bulk_response.json()
        assert bulk_data["success"] is True
        
        # Should fetch data for all symbols
        fetched_symbols = list(bulk_data["data"].keys())
        assert len(fetched_symbols) == len(symbols)
        
        # Test bulk indicator calculation
        indicator_request_start = datetime.now()
        
        bulk_indicators = client.post(
            "/api/v1/indicators/calculate",
            headers=authenticated_headers,
            json={
                "symbols": symbols,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "indicators": ["rsi", "macd"]
            }
        )
        
        indicator_calc_time = (datetime.now() - indicator_request_start).total_seconds()
        
        assert bulk_indicators.status_code == 200
        indicators_data = bulk_indicators.json()
        assert indicators_data["success"] is True
        
        # Validate performance targets
        # Bulk data fetch should be reasonable for 8 symbols
        assert bulk_fetch_time < 10.0, f"Bulk fetch took {bulk_fetch_time:.2f}s"
        
        # Indicator calculation should scale well
        per_symbol_time = indicator_calc_time / len(symbols)
        projected_1000_time = per_symbol_time * 1000
        
        # Should project to under 2 seconds for 1000 symbols (per spec)
        assert projected_1000_time < 2.0, (
            f"Indicator performance doesn't scale: {per_symbol_time:.3f}s per symbol "
            f"projects to {projected_1000_time:.2f}s for 1000 symbols"
        )
        
        # Validate all indicators calculated for all symbols
        for symbol in symbols:
            assert symbol in indicators_data["data"]
            symbol_indicators = indicators_data["data"][symbol]
            assert "rsi" in symbol_indicators
            assert "macd" in symbol_indicators
    
    async def test_error_handling_and_fallback_e2e(
        self,
        client: TestClient,
        authenticated_headers: dict
    ):
        """Test error handling and fallback mechanisms end-to-end"""
        
        # Test invalid symbol handling
        invalid_response = client.get(
            "/api/v1/market-data/historical/INVALID_SYMBOL_123",
            headers=authenticated_headers,
            params={
                "start_date": "2023-01-01",
                "end_date": "2023-01-31"
            }
        )
        
        assert invalid_response.status_code == 400
        error_data = invalid_response.json()
        assert "invalid symbol format" in error_data["detail"].lower()
        
        # Test provider fallback (simulate by using a symbol that might fail on primary)
        fallback_response = client.get(
            "/api/v1/market-data/historical/AAPL",
            headers=authenticated_headers,
            params={
                "start_date": "2023-01-01",
                "end_date": "2023-01-31"
            }
        )
        
        # Should succeed even if fallback is used
        assert fallback_response.status_code == 200
        fallback_data = fallback_response.json()
        assert fallback_data["success"] is True
        
        # Test graceful degradation with partial failures
        mixed_symbols_response = client.get(
            "/api/v1/market-data/bulk-historical",
            headers=authenticated_headers,
            params={
                "symbols": "AAPL,INVALID123,MSFT,BADSTOCK,GOOGL",
                "start_date": "2023-01-01",
                "end_date": "2023-01-31"
            }
        )
        
        # Should reject due to invalid symbols
        assert mixed_symbols_response.status_code == 400
    
    async def test_cache_effectiveness_e2e(
        self,
        client: TestClient,
        authenticated_headers: dict
    ):
        """Test caching effectiveness across requests"""
        
        request_params = {
            "start_date": "2023-01-01",
            "end_date": "2023-01-31"
        }
        
        # First request (should hit provider)
        first_start = datetime.now()
        first_response = client.get(
            "/api/v1/market-data/historical/AAPL",
            headers=authenticated_headers,
            params=request_params
        )
        first_time = (datetime.now() - first_start).total_seconds()
        
        assert first_response.status_code == 200
        first_data = first_response.json()
        assert first_data["success"] is True
        
        # Second identical request (should hit cache)
        second_start = datetime.now()
        second_response = client.get(
            "/api/v1/market-data/historical/AAPL",
            headers=authenticated_headers,
            params=request_params
        )
        second_time = (datetime.now() - second_start).total_seconds()
        
        assert second_response.status_code == 200
        second_data = second_response.json()
        assert second_data["success"] is True
        
        # Cache should make second request faster
        assert second_time < first_time, (
            f"Cache not effective: first={first_time:.3f}s, second={second_time:.3f}s"
        )
        
        # Data should be identical
        assert first_data["data"] == second_data["data"]

# Performance validation
@pytest.mark.slow
class TestSprint3PerformanceValidation:
    """Comprehensive performance validation for Sprint 3"""
    
    async def test_all_performance_targets_met(
        self,
        client: TestClient,
        authenticated_headers: dict
    ):
        """Validate all Sprint 3 performance targets are met"""
        
        performance_results = {}
        
        # Test 1: Real-time data <100ms
        rt_start = datetime.now()
        rt_response = client.get(
            "/api/v1/market-data/real-time",
            headers=authenticated_headers,
            params={"symbols": "AAPL"}
        )
        rt_time = (datetime.now() - rt_start).total_seconds()
        
        performance_results["real_time_ms"] = rt_time * 1000
        assert rt_time < 0.1, f"Real-time target missed: {rt_time*1000:.2f}ms > 100ms"
        
        # Test 2: Historical data <500ms
        hist_start = datetime.now()
        hist_response = client.get(
            "/api/v1/market-data/historical/AAPL",
            headers=authenticated_headers,
            params={
                "start_date": "2023-01-01",
                "end_date": "2023-12-31"
            }
        )
        hist_time = (datetime.now() - hist_start).total_seconds()
        
        performance_results["historical_ms"] = hist_time * 1000
        assert hist_time < 0.5, f"Historical target missed: {hist_time*1000:.2f}ms > 500ms"
        
        # Test 3: Indicator calculation scaling
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]  # 5 symbols for testing
        
        ind_start = datetime.now()
        ind_response = client.post(
            "/api/v1/indicators/calculate",
            headers=authenticated_headers,
            json={
                "symbols": symbols,
                "start_date": "2023-11-01",
                "end_date": "2023-11-30",
                "indicators": ["rsi", "macd"]
            }
        )
        ind_time = (datetime.now() - ind_start).total_seconds()
        
        # Calculate projected time for 1000 symbols
        per_symbol_time = ind_time / len(symbols)
        projected_1000_time = per_symbol_time * 1000
        
        performance_results["indicator_per_symbol_ms"] = per_symbol_time * 1000
        performance_results["projected_1000_symbols_s"] = projected_1000_time
        
        assert projected_1000_time < 2.0, (
            f"Indicator scaling target missed: projects to {projected_1000_time:.2f}s > 2s"
        )
        
        # Log performance summary
        print("\n=== Sprint 3 Performance Summary ===")
        print(f"Real-time data: {performance_results['real_time_ms']:.2f}ms (target: <100ms)")
        print(f"Historical data: {performance_results['historical_ms']:.2f}ms (target: <500ms)")
        print(f"Indicator calc per symbol: {performance_results['indicator_per_symbol_ms']:.2f}ms")
        print(f"Projected 1000 symbols: {performance_results['projected_1000_symbols_s']:.2f}s (target: <2s)")
        print("=====================================")
        
        # All performance targets met
        assert all([
            performance_results['real_time_ms'] < 100,
            performance_results['historical_ms'] < 500,
            performance_results['projected_1000_symbols_s'] < 2.0
        ]), "One or more performance targets not met"
```

## **📋 FINAL TESTING & DEPLOYMENT CHECKLIST**

### **🔍 Testing Validation Checklist**
- [ ] **Unit Tests**: >80% coverage for all services and interfaces
- [ ] **Integration Tests**: Real API calls with actual providers (Yahoo Finance, Alpha Vantage)
- [ ] **Security Tests**: Input validation, rate limiting, audit logging
- [ ] **Performance Tests**: <100ms real-time, <500ms historical, <2s for 1000 assets
- [ ] **Database Tests**: Schema migrations, constraint enforcement, cascade deletion
- [ ] **End-to-End Tests**: Complete market data → indicators → signals workflow

### **🚀 Deployment Readiness Checklist**
- [ ] **Environment Variables**: All API keys configured securely
- [ ] **Database Migrations**: Tested forward and rollback migrations
- [ ] **Cache Configuration**: Redis TTL strategies implemented
- [ ] **Rate Limiting**: Provider-appropriate limits configured
- [ ] **Monitoring**: Performance monitoring and alerting active
- [ ] **Health Checks**: Comprehensive health check endpoints
- [ ] **Error Handling**: Graceful degradation and fallback mechanisms
- [ ] **Security Validation**: Authentication, authorization, audit logging

### **📊 Success Metrics Validation**
- [ ] **Performance Targets Met**: All timing requirements validated
- [ ] **Data Quality**: Fresh data validation (<15min per spec)
- [ ] **Signal Accuracy**: MACD > RSI > Momentum hierarchy implemented
- [ ] **Cache Effectiveness**: Cache hit rates >70% for repeated requests
- [ ] **Error Handling**: Graceful fallback with <1% total failure rate
- [ ] **Integration Quality**: Seamless integration with existing Sprint 2 services

---

**🎯 Sprint 3 Success Criteria Summary:**
1. **✅ Interface-First Design**: All services implement clean interfaces with dependency injection
2. **✅ Performance Requirements**: <2s for 1000 assets indicator calculation (per 1_spec.md)
3. **✅ Real Data Testing**: 80%+ test coverage with actual API integration
4. **✅ Security Integration**: Financial-grade security with audit trails
5. **✅ Production Readiness**: Circuit breaker, caching, monitoring, and error handling
6. **✅ Sprint Integration**: Seamless connection with Sprint 2 universe/asset services

**Sprint 3 delivers a bulletproof market data and indicators service that integrates perfectly with existing architecture while meeting all performance, security, and quality requirements.**