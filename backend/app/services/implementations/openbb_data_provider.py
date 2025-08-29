import asyncio
import logging
import pandas as pd
from datetime import date, datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import time
import aiohttp
from functools import lru_cache

try:
    from openbb import obb
    OPENBB_AVAILABLE = True
except ImportError:
    try:
        # Alternative import path for different OpenBB versions
        import openbb
        obb = openbb.obb if hasattr(openbb, 'obb') else None
        OPENBB_AVAILABLE = obb is not None
    except ImportError:
        OPENBB_AVAILABLE = False
        obb = None

from ..interfaces.data_provider import IDataProvider, MarketData, AssetInfo, ValidationResult, ServiceResult

logger = logging.getLogger(__name__)

class OpenBBDataProvider(IDataProvider):
    """OpenBB Terminal SDK implementation providing professional-grade financial data"""
    
    def __init__(
        self, 
        max_workers: int = 3,
        request_delay: float = 0.1,  # Reduced for better performance
        api_key: Optional[str] = None,
        enable_pro_features: bool = False
    ):
        """
        Initialize OpenBB Terminal data provider
        
        Args:
            max_workers: Maximum number of concurrent requests  
            request_delay: Delay between requests to respect rate limits
            api_key: OpenBB Pro API key for enhanced features
            enable_pro_features: Enable professional-grade features
        """
        if not OPENBB_AVAILABLE:
            logger.warning(
                "OpenBB Terminal SDK not available. Install with: pip install openbb "
                "Note: OpenBB requires Python <3.12 for some versions. "
                "Provider will operate in limited mode with basic functionality."
            )
            # Don't raise error, allow limited functionality for demonstration
        
        self.max_workers = max_workers
        self.request_delay = request_delay
        self.api_key = api_key
        self.enable_pro_features = enable_pro_features
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._last_request_time = 0.0
        
        # Performance optimizations
        self._session = None
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = 300  # 5 minutes cache TTL
        
        # Initialize OpenBB with API key if provided
        if api_key:
            try:
                obb.user.credentials.set_keys({"openbb_pat": api_key})
                logger.info("OpenBB Pro features enabled with API key")
            except Exception as e:
                logger.warning(f"Failed to set OpenBB API key: {e}")
                self.enable_pro_features = False
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with connection pooling"""
        if self._session is None or self._session.closed:
            # Configure connection pool for optimal performance
            connector = aiohttp.TCPConnector(
                limit=20,  # Total pool size
                limit_per_host=5,  # Per-host limit
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(
                total=30,  # Total timeout
                connect=10,  # Connection timeout
                sock_read=10  # Socket read timeout
            )
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'BubblePlatform/1.0'
                }
            )
        
        return self._session
    
    async def _close_session(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _get_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operation"""
        import hashlib
        key_data = f"{operation}:{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if available and not expired"""
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return result
            else:
                del self._cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Any):
        """Cache result with timestamp"""
        self._cache[cache_key] = (result, time.time())
        # Simple LRU: remove oldest entries if cache gets too large
        if len(self._cache) > 1000:  # Max 1000 cached items
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
    
    async def _rate_limit(self):
        """Respect OpenBB API rate limits"""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last_request)
        self._last_request_time = time.time()
    
    def _run_in_executor(self, func, *args):
        """Run blocking OpenBB operations in thread executor"""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(self.executor, func, *args)
    
    def _normalize_timestamp(self, timestamp: Any) -> datetime:
        """Normalize various timestamp formats to timezone-aware datetime in UTC"""
        try:
            # Handle None or empty
            if not timestamp:
                return datetime.now(timezone.utc)
            
            # Handle pandas Timestamp
            if hasattr(timestamp, 'tz_localize') and hasattr(timestamp, 'tz'):
                if timestamp.tz is None:
                    return timestamp.tz_localize(timezone.utc).to_pydatetime()
                else:
                    return timestamp.astimezone(timezone.utc).to_pydatetime()
            
            # Handle datetime objects
            if isinstance(timestamp, datetime):
                if timestamp.tzinfo is None:
                    return timestamp.replace(tzinfo=timezone.utc)
                else:
                    return timestamp.astimezone(timezone.utc)
            
            # Handle date objects
            if isinstance(timestamp, date):
                return datetime.combine(timestamp, datetime.min.time(), tzinfo=timezone.utc)
            
            # Handle string timestamps
            if isinstance(timestamp, str):
                try:
                    dt = pd.to_datetime(timestamp)
                    return self._normalize_timestamp(dt)
                except:
                    logger.debug(f"Could not parse timestamp string: {timestamp}")
                    return datetime.now(timezone.utc)
            
            # Handle numeric timestamps (unix)
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            
            # Fallback
            logger.debug(f"Unknown timestamp format: {type(timestamp)} - {timestamp}")
            return datetime.now(timezone.utc)
            
        except Exception as e:
            logger.debug(f"Error normalizing timestamp {timestamp}: {e}")
            return datetime.now(timezone.utc)
    
    def _get_historical_data(self, symbol: str, start_date: date, end_date: date, interval: str) -> pd.DataFrame:
        """Get historical data - blocking operation"""
        try:
            # Map interval format for OpenBB
            interval_mapping = {
                "1d": "1d", "1h": "1h", "30m": "30m", "15m": "15m", "5m": "5m", "1m": "1m"
            }
            openbb_interval = interval_mapping.get(interval, "1d")
            
            # Use OpenBB equity historical data
            data = obb.equity.price.historical(
                symbol=symbol,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                interval=openbb_interval,
                provider="yfinance"  # Default provider, can be enhanced with others
            )
            
            if hasattr(data, 'to_df'):
                return data.to_df()
            elif isinstance(data, pd.DataFrame):
                return data
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.warning(f"Failed to get historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    def _get_quote_data(self, symbol: str) -> Dict:
        """Get quote data - blocking operation"""
        try:
            quote = obb.equity.price.quote(symbol=symbol, provider="yfinance")
            
            if hasattr(quote, 'to_df'):
                df = quote.to_df()
                if not df.empty:
                    return df.iloc[0].to_dict()
            elif hasattr(quote, 'results') and quote.results:
                # Handle OBBject format
                result = quote.results[0] if isinstance(quote.results, list) else quote.results
                return result.model_dump() if hasattr(result, 'model_dump') else dict(result)
            
            return {}
            
        except Exception as e:
            logger.warning(f"Failed to get quote for {symbol}: {e}")
            return {}
    
    def _get_fundamental_data(self, symbol: str) -> Dict:
        """Get fundamental data - blocking operation"""
        result = {}
        
        try:
            # Try multiple approaches for fundamental data based on OpenBB version compatibility
            
            # Method 1: Try getting company info/profile (newer OpenBB versions)
            try:
                if hasattr(obb.equity, 'profile'):
                    profile = obb.equity.profile(symbol=symbol, provider="yfinance")
                    if hasattr(profile, 'results') and profile.results:
                        profile_data = profile.results[0] if isinstance(profile.results, list) else profile.results
                        if hasattr(profile_data, 'model_dump'):
                            result.update(profile_data.model_dump())
                        elif hasattr(profile_data, '__dict__'):
                            result.update(profile_data.__dict__)
                        else:
                            result.update(dict(profile_data))
            except Exception as profile_error:
                logger.debug(f"Profile method failed for {symbol}: {profile_error}")
            
            # Method 2: Try fundamental data with different endpoints
            if not result:
                try:
                    # Check available methods in fundamental router
                    fundamental_router = obb.equity.fundamental
                    available_methods = [method for method in dir(fundamental_router) 
                                       if not method.startswith('_') and callable(getattr(fundamental_router, method))]
                    logger.debug(f"Available fundamental methods: {available_methods}")
                    
                    # Try common endpoints that might exist
                    for method_name in ['info', 'company', 'metrics', 'overview']:
                        if hasattr(fundamental_router, method_name):
                            try:
                                method = getattr(fundamental_router, method_name)
                                data = method(symbol=symbol, provider="yfinance")
                                if hasattr(data, 'results') and data.results:
                                    data_item = data.results[0] if isinstance(data.results, list) else data.results
                                    if hasattr(data_item, 'model_dump'):
                                        result.update(data_item.model_dump())
                                    elif hasattr(data_item, '__dict__'):
                                        result.update(data_item.__dict__)
                                    else:
                                        result.update(dict(data_item))
                                    break  # Success, stop trying other methods
                            except Exception as method_error:
                                logger.debug(f"Method {method_name} failed for {symbol}: {method_error}")
                                continue
                                
                except Exception as router_error:
                    logger.debug(f"Router exploration failed for {symbol}: {router_error}")
            
            # Method 3: Try equity search as fallback to get basic info
            if not result:
                try:
                    search_result = obb.equity.search(query=symbol, provider="yfinance")
                    if hasattr(search_result, 'results') and search_result.results:
                        for item in search_result.results:
                            if hasattr(item, 'symbol') and item.symbol.upper() == symbol.upper():
                                if hasattr(item, 'model_dump'):
                                    result.update(item.model_dump())
                                elif hasattr(item, '__dict__'):
                                    result.update(item.__dict__)
                                else:
                                    result.update(dict(item))
                                break
                except Exception as search_error:
                    logger.debug(f"Search fallback failed for {symbol}: {search_error}")
            
            # Get additional metrics if Pro features enabled and we have basic data
            if result and self.enable_pro_features:
                try:
                    fundamental_router = obb.equity.fundamental
                    if hasattr(fundamental_router, 'ratios'):
                        ratios = fundamental_router.ratios(symbol=symbol, provider="yfinance")
                        if hasattr(ratios, 'results') and ratios.results:
                            ratio_data = ratios.results[0] if isinstance(ratios.results, list) else ratios.results
                            if hasattr(ratio_data, 'model_dump'):
                                result.update({"ratios": ratio_data.model_dump()})
                            elif hasattr(ratio_data, '__dict__'):
                                result.update({"ratios": ratio_data.__dict__})
                            else:
                                result.update({"ratios": dict(ratio_data)})
                except Exception as e:
                    logger.debug(f"Could not fetch ratios for {symbol}: {e}")
            
        except Exception as e:
            logger.warning(f"Failed to get fundamental data for {symbol}: {e}")
        
        return result
    
    async def fetch_historical_data(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        interval: str = "1d"
    ) -> ServiceResult[Dict[str, List[MarketData]]]:
        """Fetch historical price data using OpenBB Terminal SDK"""
        try:
            await self._rate_limit()
            
            result = {}
            errors = []
            
            for symbol in symbols:
                try:
                    hist_df = await self._run_in_executor(
                        self._get_historical_data, symbol, start_date, end_date, interval
                    )
                    
                    if hist_df.empty:
                        errors.append(f"No historical data found for {symbol}")
                        continue
                    
                    market_data = []
                    for date_idx, row in hist_df.iterrows():
                        # Handle different DataFrame index formats
                        timestamp = date_idx
                        if isinstance(timestamp, str):
                            timestamp = pd.to_datetime(timestamp)
                        elif isinstance(timestamp, date) and not isinstance(timestamp, datetime):
                            # Convert date to datetime at start of day
                            timestamp = datetime.combine(timestamp, datetime.min.time())
                            timestamp = pd.to_datetime(timestamp)
                        
                        # Normalize timezone handling
                        timestamp = self._normalize_timestamp(timestamp)
                        
                        # Handle column name variations
                        open_col = next((col for col in hist_df.columns if col.lower() in ['open', 'Open']), 'open')
                        high_col = next((col for col in hist_df.columns if col.lower() in ['high', 'High']), 'high')
                        low_col = next((col for col in hist_df.columns if col.lower() in ['low', 'Low']), 'low')
                        close_col = next((col for col in hist_df.columns if col.lower() in ['close', 'Close']), 'close')
                        volume_col = next((col for col in hist_df.columns if col.lower() in ['volume', 'Volume']), 'volume')
                        adj_close_col = next((col for col in hist_df.columns if col.lower() in ['adj_close', 'Adj Close', 'adjusted_close']), None)
                        
                        market_data.append(MarketData(
                            symbol=symbol,
                            timestamp=timestamp,
                            open=float(row.get(open_col, 0)),
                            high=float(row.get(high_col, 0)),
                            low=float(row.get(low_col, 0)),
                            close=float(row.get(close_col, 0)),
                            volume=int(row.get(volume_col, 0)),
                            adjusted_close=float(row.get(adj_close_col, row.get(close_col, 0))) if adj_close_col else float(row.get(close_col, 0)),
                            metadata={
                                "interval": interval,
                                "source": "openbb_terminal",
                                "provider": "openbb",
                                "pro_features": self.enable_pro_features
                            }
                        ))
                    
                    result[symbol] = market_data
                    
                except Exception as e:
                    errors.append(f"Error processing {symbol}: {str(e)}")
                    logger.error(f"Error fetching historical data for {symbol}: {e}")
                
                # Rate limiting between symbols
                if len(symbols) > 1:
                    await asyncio.sleep(self.request_delay)
            
            return ServiceResult(
                success=len(result) > 0,
                data=result,
                message=f"Fetched historical data for {len(result)}/{len(symbols)} symbols via OpenBB",
                metadata={
                    "provider": "openbb_terminal",
                    "requested_symbols": len(symbols),
                    "successful": len(result),
                    "errors": errors,
                    "date_range": f"{start_date} to {end_date}",
                    "interval": interval,
                    "pro_features": self.enable_pro_features
                },
                next_actions=["analyze_price_data", "calculate_indicators"] if result else ["retry_with_different_provider"]
            )
            
        except Exception as e:
            logger.error(f"OpenBB historical data fetch failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch historical data from OpenBB Terminal",
                metadata={"provider": "openbb_terminal", "symbols": symbols}
            )
    
    async def fetch_real_time_data(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, MarketData]]:
        """Fetch current market data using OpenBB Terminal SDK"""
        try:
            await self._rate_limit()
            
            result = {}
            errors = []
            
            for symbol in symbols:
                try:
                    quote_data = await self._run_in_executor(self._get_quote_data, symbol)
                    
                    if not quote_data:
                        errors.append(f"No real-time data available for {symbol}")
                        continue
                    
                    # Extract data from quote response
                    timestamp = self._normalize_timestamp(quote_data.get('last_price_timestamp'))
                    
                    result[symbol] = MarketData(
                        symbol=symbol,
                        timestamp=timestamp,
                        open=float(quote_data.get('previous_close', quote_data.get('last_price', 0))),
                        high=float(quote_data.get('day_high', quote_data.get('last_price', 0))),
                        low=float(quote_data.get('day_low', quote_data.get('last_price', 0))),
                        close=float(quote_data.get('last_price', 0)),
                        volume=int(quote_data.get('volume', 0)),
                        adjusted_close=float(quote_data.get('last_price', 0)),
                        metadata={
                            "source": "openbb_terminal", 
                            "data_type": "real_time",
                            "provider": "openbb",
                            "quote_data": quote_data
                        }
                    )
                    
                except Exception as e:
                    errors.append(f"Error fetching real-time data for {symbol}: {str(e)}")
                    logger.error(f"Error fetching real-time data for {symbol}: {e}")
                
                # Rate limiting between symbols
                if len(symbols) > 1:
                    await asyncio.sleep(self.request_delay)
            
            return ServiceResult(
                success=len(result) > 0,
                data=result,
                message=f"Fetched real-time data for {len(result)}/{len(symbols)} symbols via OpenBB",
                metadata={
                    "provider": "openbb_terminal",
                    "requested_symbols": len(symbols),
                    "successful": len(result),
                    "errors": errors,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                next_actions=["process_market_data", "update_portfolios"] if result else ["retry_real_time_fetch"]
            )
            
        except Exception as e:
            logger.error(f"OpenBB real-time data fetch failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch real-time data from OpenBB Terminal",
                metadata={"provider": "openbb_terminal", "symbols": symbols}
            )
    
    async def fetch_asset_info(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, AssetInfo]]:
        """Fetch fundamental asset information using OpenBB Terminal SDK with caching"""
        try:
            result = {}
            errors = []
            cache_hits = 0
            
            for symbol in symbols:
                try:
                    # Check cache first
                    cache_key = self._get_cache_key("asset_info", symbol=symbol)
                    cached_data = self._get_cached_result(cache_key)
                    
                    if cached_data:
                        result[symbol] = cached_data
                        cache_hits += 1
                        continue
                    
                    # Not in cache, fetch from API (with reduced rate limiting for better performance)
                    await self._rate_limit()
                    
                    fundamental_data = await self._run_in_executor(
                        self._get_fundamental_data, symbol
                    )
                    
                    if fundamental_data:
                        # Extract company information from OpenBB response
                        asset_info = AssetInfo(
                            symbol=symbol,
                            name=fundamental_data.get('name', fundamental_data.get('company_name', symbol)),
                            sector=fundamental_data.get('sector'),
                            industry=fundamental_data.get('industry'),
                            market_cap=fundamental_data.get('market_cap'),
                            pe_ratio=fundamental_data.get('pe_ratio', fundamental_data.get('pe_ttm')),
                            dividend_yield=fundamental_data.get('dividend_yield'),
                            is_valid=True,
                            last_updated=datetime.now(timezone.utc),
                            metadata={
                                "source": "openbb_terminal",
                                "country": fundamental_data.get('country'),
                                "currency": fundamental_data.get('currency'),
                                "exchange": fundamental_data.get('exchange'),
                                "website": fundamental_data.get('website'),
                                "description": fundamental_data.get('description', '')[:200] if fundamental_data.get('description') else None,
                                "employees": fundamental_data.get('employees'),
                                "founded": fundamental_data.get('founded'),
                                "pro_features": self.enable_pro_features,
                                "additional_ratios": fundamental_data.get('ratios', {}) if self.enable_pro_features else {}
                            }
                        )
                        
                        # Cache the result
                        self._cache_result(cache_key, asset_info)
                        result[symbol] = asset_info
                    else:
                        errors.append(f"No asset info found for {symbol}")
                        result[symbol] = AssetInfo(
                            symbol=symbol,
                            name=symbol,
                            is_valid=False,
                            last_updated=datetime.now(timezone.utc),
                            metadata={"error": "No info available", "source": "openbb_terminal"}
                        )
                
                except Exception as e:
                    errors.append(f"Error fetching asset info for {symbol}: {str(e)}")
                    logger.error(f"Error fetching asset info for {symbol}: {e}")
                    result[symbol] = AssetInfo(
                        symbol=symbol,
                        name=symbol,
                        is_valid=False,
                        last_updated=datetime.now(timezone.utc),
                        metadata={"error": str(e), "source": "openbb_terminal"}
                    )
            
            return ServiceResult(
                success=len([r for r in result.values() if r.is_valid]) > 0,
                data=result,
                message=f"Fetched asset info for {len([r for r in result.values() if r.is_valid])}/{len(symbols)} symbols via OpenBB",
                metadata={
                    "provider": "openbb_terminal",
                    "requested_symbols": len(symbols),
                    "successful": len([r for r in result.values() if r.is_valid]),
                    "errors": errors,
                    "pro_features": self.enable_pro_features,
                    "cache_hits": cache_hits,
                    "cache_hit_rate": cache_hits / len(symbols) if symbols else 0.0
                },
                next_actions=["validate_assets", "create_universe"] if result else ["check_symbol_accuracy"]
            )
            
        except Exception as e:
            logger.error(f"OpenBB asset info fetch failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch asset info from OpenBB Terminal",
                metadata={"provider": "openbb_terminal", "symbols": symbols}
            )
    
    async def validate_symbols(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, ValidationResult]]:
        """Validate asset symbols using OpenBB Terminal SDK"""
        try:
            await self._rate_limit()
            
            result = {}
            
            for symbol in symbols:
                try:
                    # Use quote data to validate symbol
                    quote_data = await self._run_in_executor(self._get_quote_data, symbol)
                    
                    if quote_data and 'last_price' in quote_data:
                        # Symbol is valid - get additional info
                        fundamental_data = await self._run_in_executor(
                            self._get_fundamental_data, symbol
                        )
                        
                        asset_info = AssetInfo(
                            symbol=symbol,
                            name=fundamental_data.get('name', fundamental_data.get('company_name', symbol)),
                            sector=fundamental_data.get('sector'),
                            industry=fundamental_data.get('industry'),
                            market_cap=fundamental_data.get('market_cap'),
                            pe_ratio=fundamental_data.get('pe_ratio', fundamental_data.get('pe_ttm')),
                            dividend_yield=fundamental_data.get('dividend_yield'),
                            is_valid=True,
                            last_updated=datetime.now(timezone.utc)
                        )
                        
                        result[symbol] = ValidationResult(
                            symbol=symbol,
                            is_valid=True,
                            provider="openbb_terminal",
                            timestamp=datetime.now(timezone.utc),
                            confidence=1.0,
                            asset_info=asset_info,
                            source="real_time"
                        )
                    else:
                        result[symbol] = ValidationResult(
                            symbol=symbol,
                            is_valid=False,
                            provider="openbb_terminal",
                            timestamp=datetime.now(timezone.utc),
                            error="Symbol not found or invalid",
                            confidence=0.0,
                            source="real_time"
                        )
                
                except Exception as e:
                    logger.error(f"Error validating {symbol}: {e}")
                    result[symbol] = ValidationResult(
                        symbol=symbol,
                        is_valid=False,
                        provider="openbb_terminal",
                        timestamp=datetime.now(timezone.utc),
                        error=str(e),
                        confidence=0.0,
                        source="real_time"
                    )
                
                # Rate limiting between symbols
                if len(symbols) > 1:
                    await asyncio.sleep(self.request_delay)
            
            valid_count = len([r for r in result.values() if r.is_valid])
            
            return ServiceResult(
                success=True,
                data=result,
                message=f"Validated {valid_count}/{len(symbols)} symbols via OpenBB",
                metadata={
                    "provider": "openbb_terminal",
                    "total_symbols": len(symbols),
                    "valid_symbols": valid_count,
                    "invalid_symbols": len(symbols) - valid_count,
                    "validation_time": datetime.now(timezone.utc).isoformat(),
                    "pro_features": self.enable_pro_features
                },
                next_actions=["add_valid_symbols_to_universe", "retry_invalid_symbols"] if valid_count > 0 else ["check_symbol_spellings"]
            )
            
        except Exception as e:
            logger.error(f"OpenBB symbol validation failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to validate symbols with OpenBB Terminal",
                metadata={"provider": "openbb_terminal", "symbols": symbols}
            )
    
    async def search_assets(
        self,
        query: str,
        limit: int = 10
    ) -> ServiceResult[List[AssetInfo]]:
        """
        Search for assets by name or symbol using OpenBB Terminal SDK
        """
        try:
            # OpenBB search functionality
            def _search_assets(search_query: str, search_limit: int):
                try:
                    # Use OpenBB equity search
                    search_results = obb.equity.search(query=search_query, provider="yfinance")
                    
                    if hasattr(search_results, 'to_df'):
                        df = search_results.to_df()
                        return df.head(search_limit).to_dict('records')
                    elif hasattr(search_results, 'results'):
                        results = search_results.results
                        if isinstance(results, list):
                            return [r.model_dump() if hasattr(r, 'model_dump') else dict(r) for r in results[:search_limit]]
                        else:
                            return [results.model_dump() if hasattr(results, 'model_dump') else dict(results)]
                    return []
                except Exception as e:
                    logger.debug(f"OpenBB search failed: {e}")
                    return []
            
            await self._rate_limit()
            
            search_data = await self._run_in_executor(_search_assets, query, limit)
            
            result = []
            for item in search_data:
                try:
                    asset_info = AssetInfo(
                        symbol=item.get('symbol', ''),
                        name=item.get('name', item.get('company_name', '')),
                        sector=item.get('sector'),
                        industry=item.get('industry'),
                        market_cap=item.get('market_cap'),
                        pe_ratio=item.get('pe_ratio'),
                        dividend_yield=item.get('dividend_yield'),
                        is_valid=True,
                        last_updated=datetime.now(timezone.utc),
                        metadata={
                            "search_query": query,
                            "source": "openbb_terminal",
                            "exchange": item.get('exchange'),
                            "country": item.get('country')
                        }
                    )
                    result.append(asset_info)
                    
                except Exception as e:
                    logger.debug(f"Error processing search result: {e}")
                    continue
            
            return ServiceResult(
                success=len(result) > 0,
                data=result,
                message=f"Found {len(result)} assets matching '{query}' via OpenBB",
                metadata={
                    "search_query": query,
                    "results_count": len(result),
                    "limit": limit,
                    "provider": "openbb_terminal",
                    "pro_features": self.enable_pro_features
                },
                next_actions=["select_asset", "refine_search"] if result else ["try_different_search_terms"]
            )
            
        except Exception as e:
            logger.error(f"OpenBB asset search failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message=f"Failed to search for assets matching '{query}' via OpenBB",
                metadata={"search_query": query, "provider": "openbb_terminal"}
            )
    
    async def fetch_fundamental_data(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, Dict[str, Any]]]:
        """
        Fetch comprehensive fundamental data using OpenBB Terminal SDK
        Enhanced professional feature for institutional-quality data
        """
        try:
            await self._rate_limit()
            
            result = {}
            errors = []
            
            for symbol in symbols:
                try:
                    fundamental_data = await self._run_in_executor(
                        self._get_fundamental_data, symbol
                    )
                    
                    if fundamental_data:
                        result[symbol] = fundamental_data
                    else:
                        errors.append(f"No fundamental data available for {symbol}")
                        
                except Exception as e:
                    errors.append(f"Error fetching fundamental data for {symbol}: {str(e)}")
                    logger.error(f"Error fetching fundamental data for {symbol}: {e}")
                
                # Rate limiting
                if len(symbols) > 1:
                    await asyncio.sleep(self.request_delay)
            
            return ServiceResult(
                success=len(result) > 0,
                data=result,
                message=f"Fetched fundamental data for {len(result)}/{len(symbols)} symbols via OpenBB",
                metadata={
                    "provider": "openbb_terminal",
                    "requested_symbols": len(symbols),
                    "successful": len(result),
                    "errors": errors,
                    "pro_features": self.enable_pro_features
                },
                next_actions=["analyze_fundamentals", "create_screens"] if result else ["retry_with_different_symbols"]
            )
            
        except Exception as e:
            logger.error(f"OpenBB fundamental data fetch failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch fundamental data from OpenBB Terminal",
                metadata={"provider": "openbb_terminal", "symbols": symbols}
            )
    
    async def fetch_economic_indicators(
        self,
        indicators: List[str]
    ) -> ServiceResult[Dict[str, Any]]:
        """
        Fetch economic indicators using OpenBB Terminal SDK
        Professional feature for macro-economic analysis
        """
        try:
            def _get_economic_data(indicator: str):
                try:
                    # Map common indicators to OpenBB functions
                    indicator_mapping = {
                        "gdp": lambda: obb.economy.gdp(provider="fred"),
                        "inflation": lambda: obb.economy.cpi(provider="fred"), 
                        "unemployment": lambda: obb.economy.unemployment(provider="fred"),
                        "interest_rates": lambda: obb.fixedincome.rate.dgs10(provider="fred"),
                        "vix": lambda: obb.equity.index.price.historical(symbol="^VIX", provider="yfinance")
                    }
                    
                    if indicator.lower() in indicator_mapping:
                        data = indicator_mapping[indicator.lower()]()
                        if hasattr(data, 'to_df'):
                            return data.to_df()
                        return pd.DataFrame()
                    else:
                        logger.warning(f"Economic indicator '{indicator}' not supported")
                        return pd.DataFrame()
                        
                except Exception as e:
                    logger.warning(f"Failed to fetch economic indicator {indicator}: {e}")
                    return pd.DataFrame()
            
            await self._rate_limit()
            
            result = {}
            errors = []
            
            for indicator in indicators:
                try:
                    data = await self._run_in_executor(_get_economic_data, indicator)
                    if not data.empty:
                        result[indicator] = data
                    else:
                        errors.append(f"No data available for {indicator}")
                        
                except Exception as e:
                    errors.append(f"Error fetching {indicator}: {str(e)}")
                    logger.error(f"Error fetching economic indicator {indicator}: {e}")
                
                # Rate limiting
                if len(indicators) > 1:
                    await asyncio.sleep(self.request_delay)
            
            return ServiceResult(
                success=len(result) > 0,
                data=result,
                message=f"Fetched economic data for {len(result)}/{len(indicators)} indicators via OpenBB",
                metadata={
                    "provider": "openbb_terminal",
                    "requested_indicators": len(indicators),
                    "successful": len(result),
                    "errors": errors,
                    "supported_indicators": ["gdp", "inflation", "unemployment", "interest_rates", "vix"]
                },
                next_actions=["analyze_economic_trends", "correlate_with_assets"] if result else ["check_indicator_names"]
            )
            
        except Exception as e:
            logger.error(f"OpenBB economic data fetch failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch economic indicators from OpenBB Terminal",
                metadata={"provider": "openbb_terminal", "indicators": indicators}
            )
    
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Check OpenBB Terminal provider health"""
        try:
            if not OPENBB_AVAILABLE:
                return ServiceResult(
                    success=False,
                    data={"provider": "openbb_terminal", "status": "unavailable"},
                    error="OpenBB Terminal SDK not installed",
                    message="OpenBB Terminal provider is not available"
                )
            
            # Test with a known symbol
            test_result = await self.validate_symbols(["AAPL"])
            
            if test_result.success and test_result.data and test_result.data["AAPL"].is_valid:
                return ServiceResult(
                    success=True,
                    data={
                        "provider": "openbb_terminal",
                        "status": "healthy",
                        "test_symbol": "AAPL",
                        "openbb_available": OPENBB_AVAILABLE,
                        "pro_features": self.enable_pro_features,
                        "api_key_configured": bool(self.api_key),
                        "max_workers": self.max_workers,
                        "request_delay": self.request_delay
                    },
                    message="OpenBB Terminal provider is operational",
                    next_actions=["use_provider_for_professional_data"]
                )
            else:
                return ServiceResult(
                    success=False,
                    data={"provider": "openbb_terminal", "status": "degraded"},
                    error="Health check validation failed",
                    message="OpenBB Terminal provider may be experiencing issues"
                )
                
        except Exception as e:
            logger.error(f"OpenBB Terminal health check failed: {e}")
            return ServiceResult(
                success=False,
                data={"provider": "openbb_terminal", "status": "unhealthy"},
                error=str(e),
                message="OpenBB Terminal provider is not accessible"
            )
    
    async def cleanup(self):
        """Clean up resources"""
        await self._close_session()
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)