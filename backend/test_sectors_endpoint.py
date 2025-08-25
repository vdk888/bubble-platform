"""
Test script for sectors endpoint database implementation
Tests the changes made to retrieve sectors from database instead of hardcoded list
"""

import asyncio
import sys
import os
sys.path.append('/app')

from app.api.v1.assets import get_available_sectors
from app.core.database import SessionLocal, engine
from app.models.asset import Asset
from app.models.user import User
from app.models.base import Base

async def test_sectors_endpoint():
    """Test sectors endpoint with real database operations"""
    
    # Create test database
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("SECTORS ENDPOINT TEST - DATABASE IMPLEMENTATION")
        print("=" * 60)
        
        # Clean up any existing test data (handle foreign key constraints)
        from app.models.asset import UniverseAsset
        db.query(UniverseAsset).delete()  # Delete junction table records first
        db.query(Asset).delete()
        db.query(User).filter(User.email == 'test@example.com').delete()
        db.commit()
        
        # Create test user
        test_user = User(
            email='test@example.com',
            hashed_password='hashed',
            is_verified=True
        )
        db.add(test_user)
        
        # Test 1: Empty database (should return fallback sectors)
        print("\nTest 1: Empty database")
        print("-" * 40)
        result = await get_available_sectors(current_user=test_user, db=db)
        assert result.success == True
        assert result.data is not None
        assert len(result.data) > 0
        assert result.metadata.get('data_source') == 'fallback_list'
        assert result.metadata.get('database_empty') == True
        print(f"✅ Empty DB test passed - returned {len(result.data)} fallback sectors")
        print(f"   Data source: {result.metadata.get('data_source')}")
        
        # Test 2: Add validated assets with sectors
        print("\nTest 2: Database with validated assets")
        print("-" * 40)
        test_assets = [
            Asset(symbol='AAPL', name='Apple Inc', sector='Technology', is_validated=True),
            Asset(symbol='GOOGL', name='Alphabet Inc', sector='Technology', is_validated=True),
            Asset(symbol='JPM', name='JPMorgan Chase', sector='Financial Services', is_validated=True),
            Asset(symbol='JNJ', name='Johnson & Johnson', sector='Healthcare', is_validated=True),
            Asset(symbol='XOM', name='Exxon Mobil', sector='Energy', is_validated=True),
            Asset(symbol='AMZN', name='Amazon', sector='Consumer Cyclical', is_validated=True),
            Asset(symbol='INVALID', name='Invalid Asset', sector='Unknown', is_validated=False),  # Should be excluded
            Asset(symbol='NULL_SECTOR', name='No Sector Asset', sector=None, is_validated=True),  # Should be excluded
        ]
        
        for asset in test_assets:
            db.add(asset)
        db.commit()
        
        result = await get_available_sectors(current_user=test_user, db=db)
        assert result.success == True
        assert result.data is not None
        assert 'Technology' in result.data
        assert 'Financial Services' in result.data
        assert 'Healthcare' in result.data
        assert 'Energy' in result.data
        assert 'Consumer Cyclical' in result.data
        assert 'Unknown' not in result.data  # Not validated asset
        assert None not in result.data  # Null sectors excluded
        assert result.metadata.get('data_source') == 'asset_database'
        assert result.metadata.get('validated_assets_only') == True
        
        print(f"✅ Database test passed - returned {len(result.data)} distinct sectors")
        print(f"   Sectors found: {sorted(result.data)}")
        print(f"   Data source: {result.metadata.get('data_source')}")
        
        # Test 3: Performance test
        print("\nTest 3: Performance test")
        print("-" * 40)
        import time
        start_time = time.time()
        
        for _ in range(5):
            result = await get_available_sectors(current_user=test_user, db=db)
        
        avg_time = (time.time() - start_time) / 5 * 1000  # Convert to ms
        assert avg_time < 200  # Should be under 200ms as per Sprint 2 requirements
        
        print(f"✅ Performance test passed - avg response time: {avg_time:.2f}ms")
        print(f"   Sprint 2 requirement: <200ms ✓")
        
        # Test 4: AI-friendly response format
        print("\nTest 4: AI-friendly response validation")
        print("-" * 40)
        result = await get_available_sectors(current_user=test_user, db=db)
        assert hasattr(result, 'success')
        assert hasattr(result, 'data')
        assert hasattr(result, 'message')
        assert hasattr(result, 'next_actions')
        assert hasattr(result, 'metadata')
        assert isinstance(result.next_actions, list)
        assert len(result.next_actions) > 0
        assert 'filter_assets_by_sector' in result.next_actions
        
        print("✅ AI-friendly format test passed")
        print(f"   Success: {result.success}")
        print(f"   Message: {result.message}")
        print(f"   Next actions: {result.next_actions}")
        
        print("\n" + "=" * 60)
        print("ALL SECTORS ENDPOINT TESTS PASSED ✅")
        print("=" * 60)
        
        # Clean up test data (handle foreign key constraints)
        db.query(UniverseAsset).delete()  # Delete junction table records first
        db.query(Asset).delete()
        db.query(User).filter(User.email == 'test@example.com').delete()
        db.commit()
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_sectors_endpoint())