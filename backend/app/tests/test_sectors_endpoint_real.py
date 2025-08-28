"""
Real data tests for the sectors endpoint using actual Docker environment.

Tests the newly implemented sectors endpoint that queries database for distinct sectors
from validated assets with fallback to hardcoded sectors when database is empty or fails.
"""
import pytest
import time
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from fastapi import status

from app.models.asset import Asset
from app.models.user import User
from app.core.security import AuthService


class TestSectorsEndpointReal:
    """Real data tests for the /api/v1/assets/sectors endpoint"""
    
    def test_sectors_with_database_data(
        self, 
        client: TestClient, 
        authenticated_test_user: User,
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
                last_validated_at=datetime.utcnow()
            )
            db_session.add(asset)
            assets_created.append(asset)
        
        # Add duplicate sector to test DISTINCT functionality
        duplicate_asset = Asset(
            symbol="DUPE1",
            name="Duplicate Sector Test",
            sector="Technology",  # Same as TEST1
            industry="Software",
            is_validated=True,
            market_cap=500000000,
            pe_ratio=20.0,
            dividend_yield=0.0,
            last_validated_at=datetime.utcnow()
        )
        db_session.add(duplicate_asset)
        assets_created.append(duplicate_asset)
        
        db_session.commit()
        
        try:
            # Create auth token
            auth_service = AuthService()
            user_data = {
                "id": authenticated_test_user.id,
                "email": authenticated_test_user.email,
                "role": authenticated_test_user.role.value,
                "subscription_tier": authenticated_test_user.subscription_tier.value
            }
            token = auth_service.create_access_token(user_data)
            
            # Act: Call sectors endpoint
            start_time = time.time()
            response = client.get(
                "/api/v1/assets/sectors",
                headers={"Authorization": f"Bearer {token}"}
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
    
    def test_sectors_fallback_empty_database(
        self, 
        client: TestClient, 
        authenticated_test_user: User,
        db_session: Session
    ):
        """Test sectors endpoint fallback when database has no validated assets"""
        
        # Arrange: Ensure database has no validated assets with sectors
        db_session.query(Asset).filter(Asset.is_validated == True).delete()
        db_session.commit()
        
        # Create auth token
        auth_service = AuthService()
        user_data = {
            "id": authenticated_test_user.id,
            "email": authenticated_test_user.email,
            "role": authenticated_test_user.role.value,
            "subscription_tier": authenticated_test_user.subscription_tier.value
        }
        token = auth_service.create_access_token(user_data)
        
        # Act: Call sectors endpoint
        response = client.get(
            "/api/v1/assets/sectors",
            headers={"Authorization": f"Bearer {token}"}
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
    
    def test_sectors_authentication_required(self, client: TestClient):
        """Test sectors endpoint requires authentication"""
        
        # Act: Call endpoint without authentication
        response = client.get("/api/v1/assets/sectors")
        
        # Assert: Should return 403 Forbidden (no credentials provided)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_sectors_sql_injection_prevention(
        self,
        client: TestClient,
        authenticated_test_user: User,
        db_session: Session
    ):
        """Test that sectors endpoint prevents SQL injection attacks"""
        
        # Arrange: Try to create asset with malicious sector name
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
            last_validated_at=datetime.utcnow()
        )
        db_session.add(asset)
        db_session.commit()
        
        try:
            # Create auth token
            auth_service = AuthService()
            user_data = {
                "id": authenticated_test_user.id,
                "email": authenticated_test_user.email,
                "role": authenticated_test_user.role.value,
                "subscription_tier": authenticated_test_user.subscription_tier.value
            }
            token = auth_service.create_access_token(user_data)
            
            # Act: Call sectors endpoint
            response = client.get(
                "/api/v1/assets/sectors",
                headers={"Authorization": f"Bearer {token}"}
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
    
    def test_sectors_filters_non_validated_assets(
        self,
        client: TestClient,
        authenticated_test_user: User,
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
            last_validated_at=datetime.utcnow()
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
            last_validated_at=datetime.utcnow()
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
            last_validated_at=datetime.utcnow()
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
            last_validated_at=datetime.utcnow()
        )
        
        assets = [validated_asset, non_validated_asset, null_sector_asset, empty_sector_asset]
        for asset in assets:
            db_session.add(asset)
        db_session.commit()
        
        try:
            # Create auth token
            auth_service = AuthService()
            user_data = {
                "id": authenticated_test_user.id,
                "email": authenticated_test_user.email,
                "role": authenticated_test_user.role.value,
                "subscription_tier": authenticated_test_user.subscription_tier.value
            }
            token = auth_service.create_access_token(user_data)
            
            # Act: Call sectors endpoint
            response = client.get(
                "/api/v1/assets/sectors",
                headers={"Authorization": f"Bearer {token}"}
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
    
    def test_sectors_response_format_compliance(
        self,
        client: TestClient,
        authenticated_test_user: User,
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
            last_validated_at=datetime.utcnow()
        )
        db_session.add(asset)
        db_session.commit()
        
        try:
            # Create auth token
            auth_service = AuthService()
            user_data = {
                "id": authenticated_test_user.id,
                "email": authenticated_test_user.email,
                "role": authenticated_test_user.role.value,
                "subscription_tier": authenticated_test_user.subscription_tier.value
            }
            token = auth_service.create_access_token(user_data)
            
            # Act: Call sectors endpoint
            response = client.get(
                "/api/v1/assets/sectors",
                headers={"Authorization": f"Bearer {token}"}
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
    
    def test_sectors_performance_with_multiple_assets(
        self,
        client: TestClient,
        authenticated_test_user: User,
        db_session: Session
    ):
        """Test sectors endpoint performance with multiple assets"""
        
        # Arrange: Create multiple assets with various sectors
        sectors_pool = [
            "Technology", "Healthcare", "Financial Services", "Energy",
            "Consumer Cyclical", "Consumer Defensive", "Industrials"
        ]
        
        assets_created = []
        for i in range(50):  # Create 50 assets
            sector = sectors_pool[i % len(sectors_pool)]  # Rotate through sectors
            asset = Asset(
                symbol=f"PERF{i:03d}",
                name=f"Performance Test Company {i}",
                sector=sector,
                industry=f"Industry {i % 10}",
                is_validated=True,
                market_cap=1000000 + i * 10000,
                pe_ratio=10.0 + (i % 30),
                dividend_yield=0.01 + (i % 50) * 0.001,
                last_validated_at=datetime.utcnow()
            )
            db_session.add(asset)
            assets_created.append(asset)
        
        db_session.commit()
        
        try:
            # Create auth token
            auth_service = AuthService()
            user_data = {
                "id": authenticated_test_user.id,
                "email": authenticated_test_user.email,
                "role": authenticated_test_user.role.value,
                "subscription_tier": authenticated_test_user.subscription_tier.value
            }
            token = auth_service.create_access_token(user_data)
            
            # Act: Call sectors endpoint and measure performance
            start_time = time.time()
            response = client.get(
                "/api/v1/assets/sectors",
                headers={"Authorization": f"Bearer {token}"}
            )
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Assert: Verify response and performance
            assert response.status_code == status.HTTP_200_OK
            
            data = response.json()
            assert data["success"] is True
            
            returned_sectors = data["data"]
            assert len(returned_sectors) == len(sectors_pool)  # All distinct sectors
            
            # Performance requirement: Should be <200ms even with 50 assets
            print(f"⏱️ Performance test (50 assets): {response_time_ms:.2f}ms")
            assert response_time_ms < 200, f"Response time {response_time_ms:.2f}ms exceeds 200ms requirement"
            
            # Verify database optimization (DISTINCT should prevent duplicates)
            for sector in sectors_pool:
                assert returned_sectors.count(sector) == 1  # Each sector appears only once
            
        finally:
            # Cleanup: Remove performance test assets
            for asset in assets_created:
                db_session.delete(asset)
            db_session.commit()


# Integration test for real Docker environment
@pytest.mark.integration
def test_sectors_endpoint_docker_integration():
    """
    Integration test that works with real Docker environment.
    This test uses HTTP requests to the actual running backend service.
    """
    import requests
    import json
    
    # Test configuration for Docker environment
    # When running inside Docker network, use service name instead of localhost
    BASE_URL = "http://backend:8000"  # Backend service in Docker network
    
    try:
        # First, verify the service is running
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code != 200:
            pytest.skip("Backend service not available for integration test")
        
        # Test 1: Authentication required
        response = requests.get(f"{BASE_URL}/api/v1/assets/sectors")
        assert response.status_code == 403  # Should require authentication (403 when no credentials provided)
        
        # Test 2: Test with mock authentication (if available)
        # Note: This would require setting up a test user in the Docker environment
        # For now, we just verify the endpoint exists and requires auth
        
        print("PASS: Docker integration test passed - endpoint exists and requires auth")
        
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Could not connect to Docker backend service: {e}")