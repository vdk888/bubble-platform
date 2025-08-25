"""
Comprehensive tests for the sectors endpoint with real database operations.

Tests the newly implemented sectors endpoint that queries database for distinct sectors
from validated assets with fallback to hardcoded sectors when database is empty or fails.

Testing Requirements:
1. Test endpoint behavior with database sectors vs fallback
2. Test with real data using actual Docker environment 
3. Performance testing (<200ms requirement)
4. Security testing (multi-tenant isolation, SQL injection prevention)
5. Error handling and fallback mechanisms
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.orm import Session
from fastapi import status

from app.main import app
from app.core.database import get_db
from app.models.asset import Asset
from app.models.user import User


class TestSectorsEndpoint:
    """Test suite for the /api/v1/assets/sectors endpoint"""
    
    @pytest.mark.asyncio
    async def test_sectors_with_database_data(
        self, 
        client: AsyncClient, 
        test_user_token: str,
        db_session: Session
    ):
        """Test sectors endpoint returns database sectors when assets exist"""
        
        # Arrange: Create test assets with various sectors in database
        test_sectors = [
            "Technology", 
            "Healthcare", 
            "Financial Services",
            "Energy", 
            "Consumer Cyclical"
        ]
        
        assets_created = []
        for i, sector in enumerate(test_sectors):
            asset = Asset(
                symbol=f"TEST{i+1}",
                name=f"Test Company {i+1}",
                sector=sector,
                industry=f"Test Industry {i+1}",
                is_validated=True,
                market_cap=1000000000 + i * 100000000,  # Varied market caps
                pe_ratio=15.5 + i,
                dividend_yield=0.02 + i * 0.005,
                last_updated=datetime.utcnow()
            )
            db_session.add(asset)
            assets_created.append(asset)
        
        # Add some duplicate sectors to test DISTINCT functionality
        duplicate_asset = Asset(
            symbol="DUPE1",
            name="Duplicate Sector Test",
            sector="Technology",  # Same as TEST1
            industry="Software",
            is_validated=True,
            market_cap=500000000,
            pe_ratio=20.0,
            dividend_yield=0.0,
            last_updated=datetime.utcnow()
        )
        db_session.add(duplicate_asset)
        assets_created.append(duplicate_asset)
        
        db_session.commit()
        
        try:
            # Act: Call sectors endpoint
            start_time = time.time()
            response = await client.get(
                "/api/v1/assets/sectors",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Assert: Verify response structure and content
            assert response.status_code == status.HTTP_200_OK
            
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert "message" in data
            assert "next_actions" in data
            assert "metadata" in data
            
            # Verify we get database sectors (not fallback)
            returned_sectors = data["data"]
            assert isinstance(returned_sectors, list)
            assert len(returned_sectors) == len(test_sectors)  # Should be 5 distinct sectors
            
            # Verify all test sectors are returned (order may vary due to ORDER BY)
            for sector in test_sectors:
                assert sector in returned_sectors
            
            # Verify AI-friendly response format
            assert "Retrieved" in data["message"]
            assert "sectors from asset database" in data["message"]
            
            expected_actions = [
                "filter_assets_by_sector",
                "create_sector_universe", 
                "compare_sector_performance"
            ]
            for action in expected_actions:
                assert action in data["next_actions"]
            
            # Verify metadata indicates database source
            metadata = data["metadata"]
            assert metadata["data_source"] == "asset_database"
            assert metadata["validated_assets_only"] is True
            assert metadata["total_sectors"] == len(test_sectors)
            assert "last_updated" in metadata
            
            # Performance requirement: <200ms
            print(f"⏱️ Sectors endpoint response time: {response_time_ms:.2f}ms")
            assert response_time_ms < 200, f"Response time {response_time_ms:.2f}ms exceeds 200ms requirement"
            
        finally:
            # Cleanup: Remove test assets
            for asset in assets_created:
                db_session.delete(asset)
            db_session.commit()
    
    @pytest.mark.asyncio
    async def test_sectors_fallback_empty_database(
        self, 
        client: AsyncClient, 
        test_user_token: str,
        db_session: Session
    ):
        """Test sectors endpoint fallback when database has no validated assets"""
        
        # Arrange: Ensure database has no validated assets with sectors
        # (Clean database state should already handle this, but be explicit)
        db_session.query(Asset).filter(Asset.is_validated == True).delete()
        db_session.commit()
        
        # Act: Call sectors endpoint
        response = await client.get(
            "/api/v1/assets/sectors",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        
        # Assert: Should return fallback sectors
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["success"] is True
        
        returned_sectors = data["data"]
        assert isinstance(returned_sectors, list)
        
        # Should contain standard fallback sectors
        expected_fallback_sectors = [
            "Technology",
            "Healthcare", 
            "Financial Services",
            "Consumer Cyclical",
            "Consumer Defensive",
            "Energy",
            "Industrials",
            "Real Estate",
            "Materials",
            "Utilities",
            "Communication Services"
        ]
        
        assert len(returned_sectors) == len(expected_fallback_sectors)
        for sector in expected_fallback_sectors:
            assert sector in returned_sectors
        
        # Verify message indicates fallback
        assert "fallback sectors" in data["message"]
        assert "no database sectors available" in data["message"]
        
        # Verify metadata indicates fallback source
        metadata = data["metadata"]
        assert metadata["data_source"] == "fallback_list"
        assert metadata["database_empty"] is True
        
        # Should suggest populating database
        expected_actions = [
            "validate_assets_to_populate_sectors",
            "create_sector_universe",
            "filter_assets_by_sector"
        ]
        for action in expected_actions:
            assert action in data["next_actions"]
    
    @pytest.mark.asyncio
    async def test_sectors_fallback_database_error(
        self,
        client: AsyncClient,
        test_user_token: str,
        monkeypatch
    ):
        """Test sectors endpoint fallback when database query fails"""
        
        # Arrange: Mock database session to raise exception
        def mock_get_db_with_error():
            """Mock database session that raises exception on query"""
            class MockQuery:
                def filter(self, *args):
                    return self
                def distinct(self):
                    return self
                def order_by(self, *args):
                    return self
                def all(self):
                    raise Exception("Database connection failed")
            
            class MockSession:
                def query(self, *args):
                    return MockQuery()
            
            return MockSession()
        
        # Replace database dependency with error-raising mock
        app.dependency_overrides[get_db] = mock_get_db_with_error
        
        try:
            # Act: Call sectors endpoint (should handle error gracefully)
            response = await client.get(
                "/api/v1/assets/sectors",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            
            # Assert: Should return fallback sectors despite database error
            assert response.status_code == status.HTTP_200_OK
            
            data = response.json()
            assert data["success"] is True
            
            returned_sectors = data["data"]
            assert isinstance(returned_sectors, list)
            assert len(returned_sectors) > 0  # Should have fallback sectors
            
            # Verify message indicates database error
            assert "fallback sectors" in data["message"]
            assert "database error" in data["message"]
            
            # Verify metadata indicates error handling
            metadata = data["metadata"]
            assert metadata["data_source"] == "fallback_list"
            assert metadata["database_error"] is True
            assert "error" in metadata
            
            # Should suggest retry action
            assert "retry_sector_query" in data["next_actions"]
            
        finally:
            # Cleanup: Remove dependency override
            if get_db in app.dependency_overrides:
                del app.dependency_overrides[get_db]
    
    @pytest.mark.asyncio
    async def test_sectors_authentication_required(self, client: AsyncClient):
        """Test sectors endpoint requires authentication"""
        
        # Act: Call endpoint without authentication
        response = await client.get("/api/v1/assets/sectors")
        
        # Assert: Should return 401 Unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_sectors_sql_injection_prevention(
        self,
        client: AsyncClient,
        test_user_token: str,
        db_session: Session
    ):
        """Test that sectors endpoint prevents SQL injection attacks"""
        
        # Arrange: Try to create asset with malicious sector name
        # This tests that the query properly uses SQLAlchemy ORM (not raw SQL)
        malicious_sector = "'; DROP TABLE assets; --"
        
        asset = Asset(
            symbol="MALICIOUS",
            name="Test SQL Injection",
            sector=malicious_sector,  # Malicious sector name
            industry="Test",
            is_validated=True,
            market_cap=1000000,
            pe_ratio=15.0,
            dividend_yield=0.02,
            last_updated=datetime.utcnow()
        )
        db_session.add(asset)
        db_session.commit()
        
        try:
            # Act: Call sectors endpoint
            response = await client.get(
                "/api/v1/assets/sectors",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            
            # Assert: Should handle malicious input safely
            assert response.status_code == status.HTTP_200_OK
            
            data = response.json()
            assert data["success"] is True
            
            # The malicious sector should be returned as-is (safely escaped by ORM)
            # but the database should still exist (no SQL injection occurred)
            returned_sectors = data["data"]
            assert malicious_sector in returned_sectors
            
            # Verify database still exists by checking asset count
            asset_count = db_session.query(Asset).count()
            assert asset_count > 0  # Database wasn't dropped
            
        finally:
            # Cleanup
            db_session.delete(asset)
            db_session.commit()
    
    @pytest.mark.asyncio
    async def test_sectors_performance_with_large_dataset(
        self,
        client: AsyncClient,
        test_user_token: str,
        db_session: Session
    ):
        """Test sectors endpoint performance with larger dataset"""
        
        # Arrange: Create many assets with various sectors
        sectors_pool = [
            "Technology", "Healthcare", "Financial Services", "Energy",
            "Consumer Cyclical", "Consumer Defensive", "Industrials",
            "Real Estate", "Materials", "Utilities", "Communication Services"
        ]
        
        assets_created = []
        for i in range(100):  # Create 100 assets
            sector = sectors_pool[i % len(sectors_pool)]  # Rotate through sectors
            asset = Asset(
                symbol=f"PERF{i:03d}",
                name=f"Performance Test Company {i}",
                sector=sector,
                industry=f"Industry {i % 20}",  # 20 different industries
                is_validated=True,
                market_cap=1000000 + i * 10000,
                pe_ratio=10.0 + (i % 30),
                dividend_yield=0.01 + (i % 50) * 0.001,
                last_updated=datetime.utcnow() - timedelta(days=i % 30)
            )
            db_session.add(asset)
            assets_created.append(asset)
        
        db_session.commit()
        
        try:
            # Act: Call sectors endpoint and measure performance
            start_time = time.time()
            response = await client.get(
                "/api/v1/assets/sectors",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Assert: Verify response and performance
            assert response.status_code == status.HTTP_200_OK
            
            data = response.json()
            assert data["success"] is True
            
            returned_sectors = data["data"]
            assert len(returned_sectors) == len(sectors_pool)  # All distinct sectors
            
            # Performance requirement: Should still be <200ms even with 100 assets
            print(f"⏱️ Performance test (100 assets): {response_time_ms:.2f}ms")
            assert response_time_ms < 200, f"Response time {response_time_ms:.2f}ms exceeds 200ms requirement"
            
            # Verify database optimization (DISTINCT should prevent duplicates)
            for sector in sectors_pool:
                assert returned_sectors.count(sector) == 1  # Each sector appears only once
            
        finally:
            # Cleanup: Remove performance test assets
            for asset in assets_created:
                db_session.delete(asset)
            db_session.commit()
    
    @pytest.mark.asyncio
    async def test_sectors_filters_non_validated_assets(
        self,
        client: AsyncClient,
        test_user_token: str,
        db_session: Session
    ):
        """Test that sectors endpoint only returns sectors from validated assets"""
        
        # Arrange: Create both validated and non-validated assets
        validated_asset = Asset(
            symbol="VALID1",
            name="Validated Asset",
            sector="Technology",
            industry="Software",
            is_validated=True,  # This should be included
            market_cap=1000000000,
            pe_ratio=15.0,
            dividend_yield=0.02,
            last_updated=datetime.utcnow()
        )
        
        non_validated_asset = Asset(
            symbol="INVALID1",
            name="Non-validated Asset",
            sector="Healthcare",  # This sector should NOT appear in results
            industry="Pharmaceuticals",
            is_validated=False,  # This should be excluded
            market_cap=500000000,
            pe_ratio=20.0,
            dividend_yield=0.03,
            last_updated=datetime.utcnow()
        )
        
        null_sector_asset = Asset(
            symbol="NULLSEC1",
            name="Null Sector Asset",
            sector=None,  # This should be excluded (null sector)
            industry="Unknown",
            is_validated=True,
            market_cap=200000000,
            pe_ratio=12.0,
            dividend_yield=0.01,
            last_updated=datetime.utcnow()
        )
        
        empty_sector_asset = Asset(
            symbol="EMPTYSEC1",
            name="Empty Sector Asset",
            sector="",  # This should be excluded (empty sector)
            industry="Unknown",
            is_validated=True,
            market_cap=300000000,
            pe_ratio=18.0,
            dividend_yield=0.015,
            last_updated=datetime.utcnow()
        )
        
        assets = [validated_asset, non_validated_asset, null_sector_asset, empty_sector_asset]
        for asset in assets:
            db_session.add(asset)
        db_session.commit()
        
        try:
            # Act: Call sectors endpoint
            response = await client.get(
                "/api/v1/assets/sectors",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            
            # Assert: Should only return sectors from validated assets with non-null/empty sectors
            assert response.status_code == status.HTTP_200_OK
            
            data = response.json()
            assert data["success"] is True
            
            returned_sectors = data["data"]
            
            # Should only contain "Technology" from validated_asset
            assert "Technology" in returned_sectors
            assert "Healthcare" not in returned_sectors  # Excluded (not validated)
            assert None not in returned_sectors  # Excluded (null sector)
            assert "" not in returned_sectors  # Excluded (empty sector)
            
            # Should have exactly 1 sector
            assert len(returned_sectors) == 1
            
        finally:
            # Cleanup
            for asset in assets:
                db_session.delete(asset)
            db_session.commit()
    
    @pytest.mark.asyncio 
    async def test_sectors_response_format_compliance(
        self,
        client: AsyncClient,
        test_user_token: str,
        db_session: Session
    ):
        """Test that sectors endpoint response format matches AI-friendly specification"""
        
        # Arrange: Create a test asset
        asset = Asset(
            symbol="FORMAT1",
            name="Format Test Asset",
            sector="Technology",
            industry="Software",
            is_validated=True,
            market_cap=1000000000,
            pe_ratio=15.0,
            dividend_yield=0.02,
            last_updated=datetime.utcnow()
        )
        db_session.add(asset)
        db_session.commit()
        
        try:
            # Act: Call sectors endpoint
            response = await client.get(
                "/api/v1/assets/sectors",
                headers={"Authorization": f"Bearer {test_user_token}"}
            )
            
            # Assert: Verify complete AI-friendly response structure
            assert response.status_code == status.HTTP_200_OK
            
            data = response.json()
            
            # Required top-level fields
            required_fields = ["success", "data", "message", "next_actions", "metadata"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
            
            # Verify field types
            assert isinstance(data["success"], bool)
            assert isinstance(data["data"], list)
            assert isinstance(data["message"], str)
            assert isinstance(data["next_actions"], list)
            assert isinstance(data["metadata"], dict)
            
            # Verify metadata structure
            metadata = data["metadata"]
            required_metadata = ["total_sectors", "data_source", "validated_assets_only", "last_updated"]
            for field in required_metadata:
                assert field in metadata, f"Missing required metadata field: {field}"
            
            # Verify metadata types and values
            assert isinstance(metadata["total_sectors"], int)
            assert metadata["total_sectors"] >= 0
            assert isinstance(metadata["data_source"], str)
            assert metadata["data_source"] in ["asset_database", "fallback_list"]
            assert isinstance(metadata["validated_assets_only"], bool)
            assert isinstance(metadata["last_updated"], str)
            
            # Verify last_updated is valid ISO datetime
            try:
                datetime.fromisoformat(metadata["last_updated"].replace('Z', '+00:00'))
            except ValueError:
                pytest.fail("last_updated is not valid ISO datetime format")
            
            # Verify next_actions are valid
            assert len(data["next_actions"]) > 0
            valid_actions = [
                "filter_assets_by_sector",
                "create_sector_universe",
                "compare_sector_performance",
                "validate_assets_to_populate_sectors",
                "retry_sector_query"
            ]
            for action in data["next_actions"]:
                assert action in valid_actions, f"Invalid next_action: {action}"
                
        finally:
            # Cleanup
            db_session.delete(asset)
            db_session.commit()


@pytest.mark.integration
class TestSectorsEndpointIntegration:
    """Integration tests for sectors endpoint with real database and Docker environment"""
    
    @pytest.mark.asyncio
    async def test_sectors_with_real_docker_environment(self, client: AsyncClient, test_user_token: str):
        """Test sectors endpoint in actual Docker environment with real database"""
        
        # This test runs against the real Docker database
        # It verifies the endpoint works in production-like environment
        
        # Act: Call sectors endpoint
        start_time = time.time()
        response = await client.get(
            "/api/v1/assets/sectors",
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        
        # Assert: Basic response verification
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        
        # Performance check in Docker environment
        print(f"⏱️ Docker environment response time: {response_time_ms:.2f}ms")
        # Docker might be slightly slower, so allow up to 500ms
        assert response_time_ms < 500, f"Docker response time {response_time_ms:.2f}ms exceeds 500ms limit"
        
        # Verify AI-friendly format is maintained
        assert "message" in data
        assert "next_actions" in data
        assert "metadata" in data
        
        print(f"✅ Sectors endpoint working in Docker environment")
        print(f"📊 Returned {len(data['data'])} sectors")
        print(f"🔧 Data source: {data['metadata'].get('data_source', 'unknown')}")