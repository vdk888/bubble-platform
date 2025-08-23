import asyncio
import aiohttp
from typing import List, Dict, Optional, Any
from datetime import date, datetime, timezone, timedelta
import logging
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.fundamentaldata import FundamentalData
import pandas as pd
import os

from ..interfaces.data_provider import IDataProvider, MarketData, AssetInfo, ValidationResult, ServiceResult

logger = logging.getLogger(__name__)

class AlphaVantageProvider(IDataProvider):
    """Alpha Vantage implementation as fallback data provider"""
    
    def __init__(self, api_key: Optional[str] = None, requests_per_minute: int = 5):
        """
        Initialize Alpha Vantage data provider
        
        Args:
            api_key: Alpha Vantage API key (default from environment)
            requests_per_minute: Rate limit for requests (free tier: 5/min, 500/day)
        """
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        if not self.api_key:
            logger.warning("No Alpha Vantage API key provided. Provider will not function.")
        
        self.requests_per_minute = requests_per_minute
        self.request_interval = 60.0 / requests_per_minute  # Seconds between requests
        self._last_request_time = 0.0
        
        # Initialize Alpha Vantage clients
        if self.api_key:
            self.timeseries = TimeSeries(key=self.api_key, output_format='pandas')
            self.fundamentals = FundamentalData(key=self.api_key, output_format='pandas')
    
    async def _rate_limit(self):
        """Respect Alpha Vantage rate limits (5 requests per minute for free tier)"""
        current_time = asyncio.get_event_loop().time()
        time_since_last_request = current_time - self._last_request_time
        if time_since_last_request < self.request_interval:
            wait_time = self.request_interval - time_since_last_request
            await asyncio.sleep(wait_time)
        self._last_request_time = asyncio.get_event_loop().time()
    
    async def _run_blocking_call(self, func, *args, **kwargs):
        """Run blocking Alpha Vantage calls in thread executor"""
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, func, *args, **kwargs)
        except Exception as e:
            logger.error(f"Alpha Vantage API call failed: {e}")
            raise
    
    async def fetch_historical_data(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        interval: str = "1d"
    ) -> ServiceResult[Dict[str, List[MarketData]]]:
        """Fetch historical price data from Alpha Vantage"""
        if not self.api_key:
            return ServiceResult(
                success=False,
                error="Alpha Vantage API key not configured",
                message="Cannot fetch historical data without API key"
            )
        
        try:
            result = {}
            errors = []
            
            # Map interval to Alpha Vantage format
            if interval == "1d":
                av_function = "TIME_SERIES_DAILY_ADJUSTED"
            elif interval == "1wk":
                av_function = "TIME_SERIES_WEEKLY_ADJUSTED"
            elif interval == "1mo":
                av_function = "TIME_SERIES_MONTHLY_ADJUSTED"
            else:
                av_function = "TIME_SERIES_DAILY_ADJUSTED"  # Default
            
            for symbol in symbols:
                try:
                    await self._rate_limit()
                    
                    if av_function == "TIME_SERIES_DAILY_ADJUSTED":
                        data, metadata = await self._run_blocking_call(
                            self.timeseries.get_daily_adjusted, symbol, outputsize='full'
                        )
                    elif av_function == "TIME_SERIES_WEEKLY_ADJUSTED":
                        data, metadata = await self._run_blocking_call(
                            self.timeseries.get_weekly_adjusted, symbol
                        )
                    elif av_function == "TIME_SERIES_MONTHLY_ADJUSTED":
                        data, metadata = await self._run_blocking_call(
                            self.timeseries.get_monthly_adjusted, symbol
                        )
                    
                    if data is not None and not data.empty:
                        # Filter data by date range
                        mask = (data.index >= pd.Timestamp(start_date)) & (data.index <= pd.Timestamp(end_date))
                        filtered_data = data[mask]
                        
                        market_data = []
                        for timestamp, row in filtered_data.iterrows():
                            market_data.append(MarketData(
                                symbol=symbol,
                                timestamp=timestamp.tz_localize(timezone.utc) if timestamp.tz is None else timestamp.astimezone(timezone.utc),
                                open=float(row.get('1. open', row.get('1. Open', 0))),
                                high=float(row.get('2. high', row.get('2. High', 0))),
                                low=float(row.get('3. low', row.get('3. Low', 0))),
                                close=float(row.get('4. close', row.get('4. Close', 0))),
                                volume=int(row.get('6. volume', row.get('6. Volume', 0))),
                                adjusted_close=float(row.get('5. adjusted close', row.get('5. Adjusted Close', 0))),
                                metadata={"source": "alpha_vantage", "interval": interval}
                            ))
                        
                        result[symbol] = market_data
                    else:
                        errors.append(f"No historical data found for {symbol}")
                
                except Exception as e:
                    errors.append(f"Error fetching historical data for {symbol}: {str(e)}")
                    logger.error(f"Alpha Vantage historical data error for {symbol}: {e}")
            
            return ServiceResult(
                success=len(result) > 0,
                data=result,
                message=f"Fetched historical data for {len(result)}/{len(symbols)} symbols from Alpha Vantage",
                metadata={
                    "provider": "alpha_vantage",
                    "requested_symbols": len(symbols),
                    "successful": len(result),
                    "errors": errors,
                    "date_range": f"{start_date} to {end_date}",
                    "interval": interval
                },
                next_actions=["analyze_price_data", "calculate_indicators"] if result else ["check_api_limits"]
            )
            
        except Exception as e:
            logger.error(f"Alpha Vantage historical data fetch failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch historical data from Alpha Vantage",
                metadata={"provider": "alpha_vantage", "symbols": symbols}
            )
    
    async def fetch_real_time_data(
        self, 
        symbols: List[str]
    ) -> ServiceResult[Dict[str, MarketData]]:
        """Fetch current market data from Alpha Vantage"""
        if not self.api_key:
            return ServiceResult(
                success=False,
                error="Alpha Vantage API key not configured",
                message="Cannot fetch real-time data without API key"
            )
        
        try:
            result = {}
            errors = []
            
            for symbol in symbols:
                try:
                    await self._rate_limit()
                    
                    # Get intraday data for most recent prices
                    data, metadata = await self._run_blocking_call(
                        self.timeseries.get_intraday, symbol, interval='5min', outputsize='compact'
                    )
                    
                    if data is not None and not data.empty:
                        # Get the most recent data point
                        latest_timestamp = data.index[0]  # Most recent
                        latest_row = data.iloc[0]
                        
                        result[symbol] = MarketData(
                            symbol=symbol,
                            timestamp=latest_timestamp.tz_localize(timezone.utc) if latest_timestamp.tz is None else latest_timestamp.astimezone(timezone.utc),
                            open=float(latest_row.get('1. open', 0)),
                            high=float(latest_row.get('2. high', 0)),
                            low=float(latest_row.get('3. low', 0)),
                            close=float(latest_row.get('4. close', 0)),
                            volume=int(latest_row.get('5. volume', 0)),
                            adjusted_close=float(latest_row.get('4. close', 0)),  # Use close as adjusted for real-time
                            metadata={"source": "alpha_vantage", "data_type": "intraday"}
                        )
                    else:
                        errors.append(f"No real-time data available for {symbol}")
                
                except Exception as e:
                    errors.append(f"Error fetching real-time data for {symbol}: {str(e)}")
                    logger.error(f"Alpha Vantage real-time data error for {symbol}: {e}")
            
            return ServiceResult(
                success=len(result) > 0,
                data=result,
                message=f"Fetched real-time data for {len(result)}/{len(symbols)} symbols from Alpha Vantage",
                metadata={
                    "provider": "alpha_vantage",
                    "requested_symbols": len(symbols),
                    "successful": len(result),
                    "errors": errors,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                next_actions=["process_market_data", "update_portfolios"] if result else ["check_api_limits"]
            )
            
        except Exception as e:
            logger.error(f"Alpha Vantage real-time data fetch failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch real-time data from Alpha Vantage",
                metadata={"provider": "alpha_vantage", "symbols": symbols}
            )
    
    async def fetch_asset_info(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, AssetInfo]]:
        """Fetch fundamental asset information from Alpha Vantage"""
        if not self.api_key:
            return ServiceResult(
                success=False,
                error="Alpha Vantage API key not configured",
                message="Cannot fetch asset info without API key"
            )
        
        try:
            result = {}
            errors = []
            
            for symbol in symbols:
                try:
                    await self._rate_limit()
                    
                    # Get company overview
                    overview, _ = await self._run_blocking_call(
                        self.fundamentals.get_company_overview, symbol
                    )
                    
                    if overview is not None and not overview.empty:
                        # Alpha Vantage returns a single row DataFrame for company overview
                        data = overview.iloc[0] if len(overview) > 0 else overview.squeeze()
                        
                        result[symbol] = AssetInfo(
                            symbol=symbol,
                            name=data.get('Name', symbol),
                            sector=data.get('Sector'),
                            industry=data.get('Industry'),
                            market_cap=float(data.get('MarketCapitalization', 0)) if data.get('MarketCapitalization') and data.get('MarketCapitalization') != 'None' else None,
                            pe_ratio=float(data.get('PERatio', 0)) if data.get('PERatio') and data.get('PERatio') != 'None' else None,
                            dividend_yield=float(data.get('DividendYield', 0)) if data.get('DividendYield') and data.get('DividendYield') != 'None' else None,
                            is_valid=True,
                            last_updated=datetime.now(timezone.utc),
                            metadata={
                                "country": data.get('Country'),
                                "currency": data.get('Currency'),
                                "exchange": data.get('Exchange'),
                                "description": data.get('Description', '')[:200] if data.get('Description') else None,
                                "52_week_high": data.get('52WeekHigh'),
                                "52_week_low": data.get('52WeekLow'),
                                "provider": "alpha_vantage"
                            }
                        )
                    else:
                        errors.append(f"No asset info found for {symbol}")
                        result[symbol] = AssetInfo(
                            symbol=symbol,
                            name=symbol,
                            is_valid=False,
                            last_updated=datetime.now(timezone.utc),
                            metadata={"error": "No info available", "provider": "alpha_vantage"}
                        )
                
                except Exception as e:
                    errors.append(f"Error fetching asset info for {symbol}: {str(e)}")
                    logger.error(f"Alpha Vantage asset info error for {symbol}: {e}")
                    result[symbol] = AssetInfo(
                        symbol=symbol,
                        name=symbol,
                        is_valid=False,
                        last_updated=datetime.now(timezone.utc),
                        metadata={"error": str(e), "provider": "alpha_vantage"}
                    )
            
            return ServiceResult(
                success=len([r for r in result.values() if r.is_valid]) > 0,
                data=result,
                message=f"Fetched asset info for {len([r for r in result.values() if r.is_valid])}/{len(symbols)} symbols from Alpha Vantage",
                metadata={
                    "provider": "alpha_vantage",
                    "requested_symbols": len(symbols),
                    "successful": len([r for r in result.values() if r.is_valid]),
                    "errors": errors
                },
                next_actions=["validate_assets", "create_universe"] if result else ["check_symbol_accuracy"]
            )
            
        except Exception as e:
            logger.error(f"Alpha Vantage asset info fetch failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to fetch asset info from Alpha Vantage",
                metadata={"provider": "alpha_vantage", "symbols": symbols}
            )
    
    async def validate_symbols(
        self,
        symbols: List[str]
    ) -> ServiceResult[Dict[str, ValidationResult]]:
        """Validate asset symbols using Alpha Vantage"""
        if not self.api_key:
            return ServiceResult(
                success=False,
                error="Alpha Vantage API key not configured",
                message="Cannot validate symbols without API key"
            )
        
        try:
            result = {}
            
            for symbol in symbols:
                try:
                    await self._rate_limit()
                    
                    # Use company overview to validate symbol
                    overview, _ = await self._run_blocking_call(
                        self.fundamentals.get_company_overview, symbol
                    )
                    
                    if overview is not None and not overview.empty and len(overview) > 0:
                        # Symbol is valid
                        data = overview.iloc[0] if len(overview) > 0 else overview.squeeze()
                        
                        asset_info = AssetInfo(
                            symbol=symbol,
                            name=data.get('Name', symbol),
                            sector=data.get('Sector'),
                            industry=data.get('Industry'),
                            market_cap=float(data.get('MarketCapitalization', 0)) if data.get('MarketCapitalization') and data.get('MarketCapitalization') != 'None' else None,
                            pe_ratio=float(data.get('PERatio', 0)) if data.get('PERatio') and data.get('PERatio') != 'None' else None,
                            dividend_yield=float(data.get('DividendYield', 0)) if data.get('DividendYield') and data.get('DividendYield') != 'None' else None,
                            is_valid=True,
                            last_updated=datetime.now(timezone.utc)
                        )
                        
                        result[symbol] = ValidationResult(
                            symbol=symbol,
                            is_valid=True,
                            provider="alpha_vantage",
                            timestamp=datetime.now(timezone.utc),
                            confidence=1.0,
                            asset_info=asset_info,
                            source="real_time"
                        )
                    else:
                        result[symbol] = ValidationResult(
                            symbol=symbol,
                            is_valid=False,
                            provider="alpha_vantage",
                            timestamp=datetime.now(timezone.utc),
                            error="Symbol not found or invalid",
                            confidence=0.0,
                            source="real_time"
                        )
                
                except Exception as e:
                    logger.error(f"Error validating {symbol} with Alpha Vantage: {e}")
                    result[symbol] = ValidationResult(
                        symbol=symbol,
                        is_valid=False,
                        provider="alpha_vantage",
                        timestamp=datetime.now(timezone.utc),
                        error=str(e),
                        confidence=0.0,
                        source="real_time"
                    )
            
            valid_count = len([r for r in result.values() if r.is_valid])
            
            return ServiceResult(
                success=True,
                data=result,
                message=f"Validated {valid_count}/{len(symbols)} symbols with Alpha Vantage",
                metadata={
                    "provider": "alpha_vantage",
                    "total_symbols": len(symbols),
                    "valid_symbols": valid_count,
                    "invalid_symbols": len(symbols) - valid_count,
                    "validation_time": datetime.now(timezone.utc).isoformat()
                },
                next_actions=["add_valid_symbols_to_universe", "retry_invalid_symbols"] if valid_count > 0 else ["check_symbol_spellings"]
            )
            
        except Exception as e:
            logger.error(f"Alpha Vantage symbol validation failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message="Failed to validate symbols with Alpha Vantage",
                metadata={"provider": "alpha_vantage", "symbols": symbols}
            )
    
    async def search_assets(
        self,
        query: str,
        limit: int = 10
    ) -> ServiceResult[List[AssetInfo]]:
        """
        Search for assets by name or symbol
        Note: Alpha Vantage has limited search capabilities, this is simplified
        """
        if not self.api_key:
            return ServiceResult(
                success=False,
                error="Alpha Vantage API key not configured",
                message="Cannot search assets without API key"
            )
        
        try:
            # Alpha Vantage doesn't have a direct search endpoint
            # We'll try the query as a symbol
            validation_result = await self.validate_symbols([query.upper()])
            
            result = []
            if validation_result.success and validation_result.data:
                validation_data = validation_result.data.get(query.upper())
                if validation_data and validation_data.is_valid and validation_data.asset_info:
                    result.append(validation_data.asset_info)
            
            return ServiceResult(
                success=len(result) > 0,
                data=result,
                message=f"Found {len(result)} assets matching '{query}' via Alpha Vantage",
                metadata={
                    "provider": "alpha_vantage",
                    "search_query": query,
                    "results_count": len(result),
                    "limit": limit,
                    "note": "Alpha Vantage search is limited to exact symbol matches"
                },
                next_actions=["select_asset", "try_yahoo_finance_search"] if result else ["try_different_search_terms"]
            )
            
        except Exception as e:
            logger.error(f"Alpha Vantage asset search failed: {e}")
            return ServiceResult(
                success=False,
                error=str(e),
                message=f"Failed to search for assets matching '{query}' via Alpha Vantage",
                metadata={"search_query": query, "provider": "alpha_vantage"}
            )
    
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """Check Alpha Vantage provider health"""
        if not self.api_key:
            return ServiceResult(
                success=False,
                data={"provider": "alpha_vantage", "status": "unconfigured"},
                error="Alpha Vantage API key not configured",
                message="Alpha Vantage provider requires API key configuration"
            )
        
        try:
            # Test with a known symbol
            test_result = await self.validate_symbols(["AAPL"])
            
            if test_result.success and test_result.data and test_result.data["AAPL"].is_valid:
                return ServiceResult(
                    success=True,
                    data={
                        "provider": "alpha_vantage",
                        "status": "healthy",
                        "test_symbol": "AAPL",
                        "api_key_configured": bool(self.api_key),
                        "requests_per_minute": self.requests_per_minute,
                        "request_interval": self.request_interval
                    },
                    message="Alpha Vantage provider is operational",
                    next_actions=["use_as_fallback_provider"]
                )
            else:
                return ServiceResult(
                    success=False,
                    data={"provider": "alpha_vantage", "status": "degraded"},
                    error="Health check validation failed",
                    message="Alpha Vantage provider may have reached API limits or is experiencing issues"
                )
                
        except Exception as e:
            logger.error(f"Alpha Vantage health check failed: {e}")
            return ServiceResult(
                success=False,
                data={"provider": "alpha_vantage", "status": "unhealthy"},
                error=str(e),
                message="Alpha Vantage provider is not accessible"
            )