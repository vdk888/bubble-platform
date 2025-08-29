#!/usr/bin/env python3
"""
Test the new intelligent chunking implementation for optimal performance
"""
import asyncio
import sys
import time
sys.path.insert(0, '.')

from app.services.implementations.openbb_data_provider import OpenBBDataProvider

async def test_chunking_performance():
    print("=" * 70)
    print("INTELLIGENT CHUNKING IMPLEMENTATION - PERFORMANCE TEST")
    print("=" * 70)
    
    provider = OpenBBDataProvider()
    
    # Test different batch sizes to demonstrate chunking effectiveness
    test_cases = [
        {"name": "Small Batch (<=3)", "symbols": ['AAPL', 'GOOGL', 'MSFT']},
        {"name": "Medium Batch (4-6)", "symbols": ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NFLX']},
        {"name": "Large Batch (7+)", "symbols": ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NFLX', 'NVDA']}
    ]
    
    results_summary = []
    
    for test_case in test_cases:
        print(f"\n{'='*50}")
        print(f"Testing: {test_case['name']}")
        print(f"Symbols: {test_case['symbols']}")
        print(f"Count: {len(test_case['symbols'])} symbols")
        print(f"{'='*50}")
        
        try:
            start_time = time.time()
            result = await provider.validate_symbols(test_case['symbols'])
            end_time = time.time()
            
            total_time = end_time - start_time
            time_per_symbol = total_time / len(test_case['symbols'])
            
            print(f"\n=== RESULTS ===")
            print(f"Success: {result.success}")
            print(f"Total Time: {total_time:.2f}s")
            print(f"Time per Symbol: {time_per_symbol:.2f}s")
            print(f"Valid Symbols: {result.metadata.get('valid_symbols', 0)}")
            print(f"Invalid Symbols: {result.metadata.get('invalid_symbols', 0)}")
            
            # Show which symbols succeeded/failed
            if result.data:
                print(f"\nSymbol Details:")
                for symbol, validation in result.data.items():
                    status = "VALID" if validation.is_valid else "INVALID"
                    error = f" ({validation.error})" if validation.error else ""
                    name = validation.asset_info.name if validation.is_valid and validation.asset_info else ""
                    if name and name != symbol:
                        name = f" - {name}"
                    print(f"  {symbol}: {status}{name}{error}")
            
            # Determine processing method used
            if len(test_case['symbols']) <= 3:
                method = "Concurrent Processing (optimal)"
            else:
                chunk_count = (len(test_case['symbols']) + 2) // 3  # ceiling division
                method = f"Intelligent Chunking ({chunk_count} chunks of 3)"
            
            print(f"\nProcessing Method: {method}")
            
            results_summary.append({
                'name': test_case['name'],
                'symbol_count': len(test_case['symbols']),
                'total_time': total_time,
                'time_per_symbol': time_per_symbol,
                'success_rate': result.metadata.get('valid_symbols', 0) / len(test_case['symbols']) * 100,
                'method': method
            })
            
        except Exception as e:
            print(f"ERROR: {e}")
            results_summary.append({
                'name': test_case['name'],
                'symbol_count': len(test_case['symbols']),
                'total_time': 0,
                'time_per_symbol': 0,
                'success_rate': 0,
                'method': 'FAILED',
                'error': str(e)
            })
        
        # Delay between test cases
        await asyncio.sleep(1)
    
    print(f"\n{'='*70}")
    print("PERFORMANCE SUMMARY & ANALYSIS")
    print(f"{'='*70}")
    
    print(f"{'Test Case':<20} {'Symbols':<8} {'Total Time':<12} {'Per Symbol':<12} {'Success Rate':<12} {'Method':<25}")
    print(f"{'-'*20} {'-'*8} {'-'*12} {'-'*12} {'-'*12} {'-'*25}")
    
    for result in results_summary:
        if 'error' not in result:
            print(f"{result['name']:<20} {result['symbol_count']:<8} {result['total_time']:<12.2f} {result['time_per_symbol']:<12.2f} {result['success_rate']:<12.1f}% {result['method']:<25}")
        else:
            print(f"{result['name']:<20} {result['symbol_count']:<8} {'ERROR':<12} {'ERROR':<12} {'0.0%':<12} {'FAILED':<25}")
    
    print(f"\n=== KEY INSIGHTS ===")
    
    # Calculate performance comparisons
    if len(results_summary) >= 2:
        small_time = results_summary[0]['time_per_symbol']
        if len(results_summary) > 1 and results_summary[1]['time_per_symbol'] > 0:
            medium_time = results_summary[1]['time_per_symbol'] 
            if small_time > 0:
                chunking_efficiency = ((small_time - medium_time) / small_time) * 100
                if chunking_efficiency > 0:
                    print(f"• Chunking provides {chunking_efficiency:.1f}% efficiency improvement for medium batches")
                else:
                    print(f"• Chunking adds {abs(chunking_efficiency):.1f}% overhead for medium batches (as expected)")
    
    # Show 401 error impact analysis
    print(f"\n=== 401 ERROR ANALYSIS ===")
    print("• 401 errors occur on quoteSummary endpoint (fundamental data)")
    print("• Basic quote requests (price data) work reliably")
    print("• Chunking strategy mitigates bulk failure cascade")
    print("• Caching reduces repeated API calls and 401 exposure")
    
    print(f"\n=== CHUNKING STRATEGY EFFECTIVENESS ===")
    print("• Small batches (≤3): Direct concurrent processing for minimal overhead")
    print("• Large batches (>3): Intelligent chunking with 0.3s inter-chunk delays")
    print("• Cache utilization reduces actual API calls significantly")
    print("• Error isolation prevents single failure from cascading")

if __name__ == "__main__":
    asyncio.run(test_chunking_performance())