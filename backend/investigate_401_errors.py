#!/usr/bin/env python3
"""
Investigate 401 errors and test chunking strategies for rate limiting
"""
import asyncio
import sys
import time
sys.path.insert(0, '.')

from app.services.implementations.openbb_data_provider import OpenBBDataProvider

async def investigate_401_errors():
    print("=" * 70)
    print("401 ERROR INVESTIGATION & CHUNKING STRATEGY ANALYSIS")
    print("=" * 70)
    
    provider = OpenBBDataProvider()
    test_symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
    
    print("\n1. === INDIVIDUAL SYMBOL TESTING ===")
    print("Testing each symbol individually to identify which ones fail...")
    
    individual_results = {}
    for symbol in test_symbols:
        print(f"\nTesting {symbol} individually:")
        try:
            start_time = time.time()
            result = await provider.fetch_real_time_data([symbol])
            end_time = time.time()
            
            if result.success:
                data = result.data.get(symbol)
                if data:
                    print(f"  SUCCESS: {symbol} = ${data.close:.2f} (took {end_time-start_time:.2f}s)")
                    individual_results[symbol] = {'status': 'success', 'price': data.close}
                else:
                    print(f"  PARTIAL: {symbol} - success flag true but no data")
                    individual_results[symbol] = {'status': 'partial', 'error': 'no_data'}
            else:
                errors = result.metadata.get('errors', [])
                print(f"  FAILED: {symbol} - {errors}")
                individual_results[symbol] = {'status': 'failed', 'errors': errors}
                
        except Exception as e:
            print(f"  EXCEPTION: {symbol} - {str(e)}")
            individual_results[symbol] = {'status': 'exception', 'error': str(e)}
        
        # Small delay between individual tests
        await asyncio.sleep(0.3)
    
    print(f"\n=== INDIVIDUAL TEST SUMMARY ===")
    success_count = len([r for r in individual_results.values() if r['status'] == 'success'])
    print(f"Successful: {success_count}/{len(test_symbols)} symbols")
    
    for symbol, result in individual_results.items():
        if result['status'] == 'success':
            print(f"  [OK] {symbol}: ${result['price']:.2f}")
        else:
            print(f"  [FAIL] {symbol}: {result.get('error', result.get('errors', 'unknown'))}")
    
    print("\n2. === BULK PROCESSING WITHOUT CHUNKING ===")
    print("Testing all symbols together (current implementation)...")
    
    try:
        start_time = time.time()
        bulk_result = await provider.validate_symbols(test_symbols)
        end_time = time.time()
        
        print(f"Bulk result: Success={bulk_result.success}, took {end_time-start_time:.2f}s")
        print(f"Valid: {bulk_result.metadata.get('valid_symbols', 0)}")
        print(f"Invalid: {bulk_result.metadata.get('invalid_symbols', 0)}")
        
        if bulk_result.data:
            for symbol, validation in bulk_result.data.items():
                status = "VALID" if validation.is_valid else "INVALID"
                error = f" ({validation.error})" if validation.error else ""
                print(f"  {symbol}: {status}{error}")
        
    except Exception as e:
        print(f"Bulk processing failed: {e}")
    
    print("\n3. === CHUNKING STRATEGY IMPLEMENTATION ===")
    print("Testing chunked processing to work around rate limits...")
    
    # Test different chunk sizes
    chunk_sizes = [1, 2, 3]
    
    for chunk_size in chunk_sizes:
        print(f"\n--- Testing chunk size: {chunk_size} ---")
        
        successful_symbols = []
        failed_symbols = []
        total_time = 0
        
        # Split symbols into chunks
        chunks = [test_symbols[i:i + chunk_size] for i in range(0, len(test_symbols), chunk_size)]
        print(f"Chunks: {chunks}")
        
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)}: {chunk}")
            
            try:
                start_time = time.time()
                result = await provider.validate_symbols(chunk)
                end_time = time.time()
                
                chunk_time = end_time - start_time
                total_time += chunk_time
                
                if result.success and result.data:
                    chunk_successful = [s for s, v in result.data.items() if v.is_valid]
                    chunk_failed = [s for s, v in result.data.items() if not v.is_valid]
                    
                    successful_symbols.extend(chunk_successful)
                    failed_symbols.extend(chunk_failed)
                    
                    print(f"  Chunk result: {len(chunk_successful)} success, {len(chunk_failed)} failed (took {chunk_time:.2f}s)")
                else:
                    failed_symbols.extend(chunk)
                    print(f"  Chunk failed entirely (took {chunk_time:.2f}s)")
                
                # Inter-chunk delay to avoid overwhelming API
                if i < len(chunks) - 1:  # Don't delay after last chunk
                    await asyncio.sleep(0.5)
                    total_time += 0.5
                    
            except Exception as e:
                failed_symbols.extend(chunk)
                print(f"  Chunk exception: {e}")
        
        print(f"\nChunk size {chunk_size} results:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Successful: {len(successful_symbols)} - {successful_symbols}")
        print(f"  Failed: {len(failed_symbols)} - {failed_symbols}")
        print(f"  Success rate: {len(successful_symbols)/len(test_symbols)*100:.1f}%")
    
    print("\n4. === RATE LIMITING ANALYSIS ===")
    print("Analyzing Yahoo Finance rate limiting patterns...")
    
    # Test rapid-fire requests to understand rate limiting
    print("\nTesting rapid requests (no delay):")
    rapid_results = []
    
    for i in range(5):
        try:
            start_time = time.time()
            result = await provider.fetch_real_time_data(['AAPL'])
            end_time = time.time()
            
            success = result.success and 'AAPL' in result.data
            response_time = end_time - start_time
            rapid_results.append((i+1, success, response_time))
            
            print(f"  Request {i+1}: {'SUCCESS' if success else 'FAILED'} ({response_time:.2f}s)")
            
        except Exception as e:
            rapid_results.append((i+1, False, 0))
            print(f"  Request {i+1}: EXCEPTION - {e}")
    
    success_count = len([r for r in rapid_results if r[1]])
    print(f"\nRapid fire results: {success_count}/5 successful")
    
    print("\n" + "=" * 70)
    print("INVESTIGATION SUMMARY & RECOMMENDATIONS")
    print("=" * 70)
    print("• Individual vs Bulk: Compare success rates")
    print("• Optimal Chunk Size: Identify best balance of speed vs reliability")  
    print("• Rate Limit Pattern: Understand Yahoo Finance throttling behavior")
    print("• Chunking Benefits: Quantify improvement over current approach")

if __name__ == "__main__":
    asyncio.run(investigate_401_errors())