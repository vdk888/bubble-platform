import yfinance as yf
import pandas as pd
import asyncio
from typing import List, Dict, Optional, Any
from datetime import date, datetime, timezone, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor
import time

from ..interfaces.data_provider import IDataProvider, MarketData, AssetInfo, ValidationResult, ServiceResult

logger = logging.getLogger(__name__)

class YahooDataProvider(IDataProvider):
    """Yahoo Finance implementation of data provider using yfinance 0.2.65+"""
    
    def __init__(self, max_workers: int = 5, request_delay: float = 0.1):
        """
        Initialize Yahoo Finance data provider
        
        Args:
            max_workers: Maximum number of concurrent requests
            request_delay: Delay between requests to respect rate limits
        """
        self.max_workers = max_workers
        self.request_delay = request_delay
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._last_request_time = 0.0
    
    async def _rate_limit(self):
        """Respect Yahoo Finance rate limits (approximately 60/minute for prices)"""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last_request)
        self._last_request_time = time.time()
    
    def _run_in_executor(self, func, *args):
        """Run blocking yfinance operations in thread executor"""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(self.executor, func, *args)
    
    def _get_ticker_info(self, symbol: str) -> Dict:
        """Get ticker info - blocking operation"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return info if info and 'symbol' in info else {}
        except Exception as e:
            logger.warning(f"Failed to get info for {symbol}: {e}")
            return {}
    
    def _get_ticker_history(self, symbol: str, start_date: date, end_date: date, interval: str) -> pd.DataFrame:
        """Get ticker history - blocking operation"""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date, interval=interval)
            return hist
        except Exception as e:
            logger.warning(f"Failed to get history for {symbol}: {e}")
            return pd.DataFrame()
    
    async def fetch_historical_data(
        self,
        symbols: List[str], 
        start_date: date,
        end_date: date,
        interval: str = "1d"
    ) -> ServiceResult[Dict[str, List[MarketData]]]:
        """Fetch historical price data from Yahoo Finance"""
        try:
            await self._rate_limit()
            
            result = {}
            errors = []
            
            # Process symbols concurrently but respect rate limits
            for symbol in symbols:
                try:
                    hist = await self._run_in_executor(
                        self._get_ticker_history, symbol, start_date, end_date, interval
                    )
                    
                    if hist.empty:
                        errors.append(f"No data found for {symbol}")
                        continue
                    
                    market_data = []
                    for date_idx, row in hist.iterrows():
                        market_data.append(MarketData(
                            symbol=symbol,
                            timestamp=date_idx.tz_localize(timezone.utc) if date_idx.tz is None else date_idx.astimezone(timezone.utc),
                            open=float(row['Open']),
                            high=float(row['High']),
                            low=float(row['Low']),
                            close=float(row['Close']),
                            volume=int(row['Volume']),
                            adjusted_close=float(row.get('Adj Close', row['Close'])),
                            metadata={"interval": interval, "source": "yahoo_finance"}
                        ))
                    
                    result[symbol] = market_data
                    
                except Exception as e:
                    errors.append(f"Error processing {symbol}: {str(e)}")
                    logger.error(f"Error fetching historical data for {symbol}: {e}")
            
            return ServiceResult(
                success=len(result) > 0,
                data=result,
                message=f"Fetched historical data for {len(result)}/{len(symbols)} symbols",
                metadata={
                    "requested_symbols": len(symbols),
                    "successful": len(result),
                    "errors": errors,
                    "date_range": f"{start_date} to {end_date}",
                    "interval": interval
                },
                next_actions=["analyze_price_data", "calculate_indicators"] if result else ["retry_with_different_symbols"]
            )
            
        except Exception as e:
            logger.error(f"Yahoo Finance historical data fetch failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch historical data from Yahoo Finance",
                metadata={"provider": "yahoo_finance", "symbols": symbols}
            )
    
    async def fetch_real_time_data(
        self, 
        symbols: List[str]
    ) -> ServiceResult[Dict[str, MarketData]]:
        """Fetch current market data from Yahoo Finance"""
        try:
            await self._rate_limit()
            
            result = {}
            errors = []
            
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    
                    # Get latest price data - use 1-day history for most recent data
                    hist = await self._run_in_executor(
                        lambda: ticker.history(period="1d", interval="1m")
                    )
                    
                    if hist.empty:
                        # Fallback to daily data
                        hist = await self._run_in_executor(
                            lambda: ticker.history(period="2d", interval="1d")
                        )
                    
                    if not hist.empty:
                        latest = hist.iloc[-1]
                        latest_timestamp = hist.index[-1]
                        
                        result[symbol] = MarketData(
                            symbol=symbol,
                            timestamp=latest_timestamp.tz_localize(timezone.utc) if latest_timestamp.tz is None else latest_timestamp.astimezone(timezone.utc),
                            open=float(latest['Open']),
                            high=float(latest['High']),
                            low=float(latest['Low']),
                            close=float(latest['Close']),
                            volume=int(latest['Volume']),
                            adjusted_close=float(latest.get('Adj Close', latest['Close'])),
                            metadata={"source": "yahoo_finance", "data_type": "real_time"}
                        )
                    else:
                        errors.append(f"No real-time data available for {symbol}")
                        
                except Exception as e:
                    errors.append(f"Error fetching real-time data for {symbol}: {str(e)}")
                    logger.error(f"Error fetching real-time data for {symbol}: {e}")
                
                # Small delay between requests
                if len(symbols) > 1:
                    await asyncio.sleep(self.request_delay)
            
            return ServiceResult(
                success=len(result) > 0,
                data=result,
                message=f"Fetched real-time data for {len(result)}/{len(symbols)} symbols",
                metadata={
                    "requested_symbols": len(symbols),
                    "successful": len(result),
                    "errors": errors,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                next_actions=["process_market_data", "update_portfolios"] if result else ["retry_real_time_fetch"]
            )
            
        except Exception as e:
            logger.error(f"Yahoo Finance real-time data fetch failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch real-time data from Yahoo Finance",
                metadata={"provider": "yahoo_finance", "symbols": symbols}
            )
    
    async def fetch_asset_info(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, AssetInfo]]:
        """Fetch fundamental asset information from Yahoo Finance"""
        try:
            await self._rate_limit()
            
            result = {}
            errors = []
            
            for symbol in symbols:
                try:
                    info = await self._run_in_executor(self._get_ticker_info, symbol)
                    
                    if info:
                        result[symbol] = AssetInfo(
                            symbol=symbol,
                            name=info.get('longName', info.get('shortName', symbol)),
                            sector=info.get('sector'),
                            industry=info.get('industry'),
                            market_cap=info.get('marketCap'),
                            pe_ratio=info.get('trailingPE'),
                            dividend_yield=info.get('dividendYield'),
                            is_valid=True,
                            last_updated=datetime.now(timezone.utc),
                            metadata={
                                "country": info.get('country'),
                                "currency": info.get('currency'),
                                "exchange": info.get('exchange'),
                                "website": info.get('website'),
                                "business_summary": info.get('longBusinessSummary', '')[:200] if info.get('longBusinessSummary') else None
                            }
                        )
                    else:
                        errors.append(f"No asset info found for {symbol}")
                        result[symbol] = AssetInfo(
                            symbol=symbol,
                            name=symbol,
                            is_valid=False,
                            last_updated=datetime.now(timezone.utc),
                            metadata={"error": "No info available"}
                        )
                
                except Exception as e:
                    errors.append(f"Error fetching asset info for {symbol}: {str(e)}")
                    logger.error(f"Error fetching asset info for {symbol}: {e}")
                    result[symbol] = AssetInfo(
                        symbol=symbol,
                        name=symbol,
                        is_valid=False,
                        last_updated=datetime.now(timezone.utc),
                        metadata={"error": str(e)}
                    )
                
                # Small delay between requests
                if len(symbols) > 1:
                    await asyncio.sleep(self.request_delay)
            
            return ServiceResult(
                success=len([r for r in result.values() if r.is_valid]) > 0,
                data=result,
                message=f"Fetched asset info for {len([r for r in result.values() if r.is_valid])}/{len(symbols)} symbols",
                metadata={
                    "requested_symbols": len(symbols),
                    "successful": len([r for r in result.values() if r.is_valid]),
                    "errors": errors
                },
                next_actions=["validate_assets", "create_universe"] if result else ["check_symbol_accuracy"]
            )
            
        except Exception as e:
            logger.error(f"Yahoo Finance asset info fetch failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch asset info from Yahoo Finance",
                metadata={"provider": "yahoo_finance", "symbols": symbols}
            )
    
    async def validate_symbols(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, ValidationResult]]:
        """Validate asset symbols using Yahoo Finance"""
        try:
            await self._rate_limit()
            
            result = {}
            
            for symbol in symbols:
                try:
                    info = await self._run_in_executor(self._get_ticker_info, symbol)
                    
                    if info and 'symbol' in info:
                        # Symbol is valid - create asset info
                        asset_info = AssetInfo(
                            symbol=symbol,
                            name=info.get('longName', info.get('shortName', symbol)),
                            sector=info.get('sector'),
                            industry=info.get('industry'),
                            market_cap=info.get('marketCap'),
                            pe_ratio=info.get('trailingPE'),
                            dividend_yield=info.get('dividendYield'),
                            is_valid=True,
                            last_updated=datetime.now(timezone.utc)
                        )
                        
                        result[symbol] = ValidationResult(
                            symbol=symbol,
                            is_valid=True,
                            provider="yahoo_finance",
                            timestamp=datetime.now(timezone.utc),
                            confidence=1.0,
                            asset_info=asset_info,
                            source="real_time"
                        )
                    else:
                        result[symbol] = ValidationResult(
                            symbol=symbol,
                            is_valid=False,
                            provider="yahoo_finance",
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
                        provider="yahoo_finance",
                        timestamp=datetime.now(timezone.utc),
                        error=str(e),
                        confidence=0.0,
                        source="real_time"
                    )
                
                # Small delay between requests
                if len(symbols) > 1:
                    await asyncio.sleep(self.request_delay)
            
            valid_count = len([r for r in result.values() if r.is_valid])
            
            return ServiceResult(
                success=True,  # Always successful as we return validation results
                data=result,
                message=f"Validated {valid_count}/{len(symbols)} symbols successfully",
                metadata={
                    "provider": "yahoo_finance",
                    "total_symbols": len(symbols),
                    "valid_symbols": valid_count,
                    "invalid_symbols": len(symbols) - valid_count,
                    "validation_time": datetime.now(timezone.utc).isoformat()
                },
                next_actions=["add_valid_symbols_to_universe", "retry_invalid_symbols"] if valid_count > 0 else ["check_symbol_spellings"]
            )
            
        except Exception as e:
            logger.error(f"Yahoo Finance symbol validation failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to validate symbols with Yahoo Finance",
                metadata={"provider": "yahoo_finance", "symbols": symbols}
            )
    
    async def search_assets(
        self,
        query: str,
        limit: int = 10
    ) -> ServiceResult[List[AssetInfo]]:
        """
        Search for assets by name or symbol
        Note: Yahoo Finance doesn't have a direct search API, so this is a simplified implementation
        """
        try:
            # For now, treat the query as a potential symbol and validate it
            # In a production environment, you might integrate with a dedicated search API
            symbols_to_try = [query.upper()]
            
            # Try common variations if query is short
            if len(query) <= 4:
                symbols_to_try.extend([
                    f"{query.upper()}.TO",  # Toronto Stock Exchange
                    f"{query.upper()}.L",   # London Stock Exchange
                ])
            
            result = []
            
            for symbol in symbols_to_try:
                try:
                    info = await self._run_in_executor(self._get_ticker_info, symbol)
                    
                    if info and 'symbol' in info:
                        asset_info = AssetInfo(
                            symbol=symbol,
                            name=info.get('longName', info.get('shortName', symbol)),
                            sector=info.get('sector'),
                            industry=info.get('industry'),
                            market_cap=info.get('marketCap'),
                            pe_ratio=info.get('trailingPE'),
                            dividend_yield=info.get('dividendYield'),
                            is_valid=True,
                            last_updated=datetime.now(timezone.utc),
                            metadata={"search_query": query}
                        )
                        result.append(asset_info)
                        
                        if len(result) >= limit:
                            break
                
                except Exception as e:
                    logger.debug(f"Search attempt for {symbol} failed: {e}")
                    continue
                
                await asyncio.sleep(self.request_delay)
            
            return ServiceResult(
                success=len(result) > 0,
                data=result,
                message=f"Found {len(result)} assets matching '{query}'",
                metadata={
                    "search_query": query,
                    "results_count": len(result),
                    "limit": limit
                },
                next_actions=["select_asset", "refine_search"] if result else ["try_different_search_terms"]
            )
            
        except Exception as e:
            logger.error(f"Yahoo Finance asset search failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message=f"Failed to search for assets matching '{query}'",
                metadata={"search_query": query, "provider": "yahoo_finance"}
            )
    
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Check Yahoo Finance provider health"""
        try:
            # Test with a known symbol
            test_result = await self.validate_symbols(["AAPL"])
            
            if test_result.success and test_result.data and test_result.data["AAPL"].is_valid:
                return ServiceResult(
                    success=True,
                    data={
                        "provider": "yahoo_finance",
                        "status": "healthy",
                        "test_symbol": "AAPL",
                        "yfinance_version": yf.__version__,
                        "max_workers": self.max_workers,
                        "request_delay": self.request_delay
                    },
                    message="Yahoo Finance provider is operational",
                    next_actions=["use_provider_for_data_fetching"]
                )
            else:
                return ServiceResult(
                    success=False,
                    data={"provider": "yahoo_finance", "status": "degraded"},
                    error="Health check validation failed",
                    message="Yahoo Finance provider may be experiencing issues"
                )
                
        except Exception as e:
            logger.error(f"Yahoo Finance health check failed: {e}")
            return ServiceResult(
                success=False,
                data={"provider": "yahoo_finance", "status": "unhealthy"},
                error=str(e),
                message="Yahoo Finance provider is not accessible"
            )