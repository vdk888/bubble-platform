"""
Test configuration and fixtures for Bubble Platform backend tests.
Following Interface First Design principles for comprehensive test coverage.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.models.base import Base
from app.models.user import User, UserRole, SubscriptionTier
from app.services.interfaces.base import ServiceResult
from app.core.config import settings

# Test database URL - use memory database to avoid I/O issues
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool  # Use StaticPool for in-memory database
)

# Enable foreign key constraints for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")  
def client():
    """Create a test client with database dependency override."""
    import os
    from unittest.mock import Mock
    
    # Prevent FastAPI startup from creating main database tables
    original_env = os.environ.get("ENVIRONMENT")
    os.environ["ENVIRONMENT"] = "testing"
    
    # Create tables in our test database
    Base.metadata.create_all(bind=engine)
    
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Configure test timeouts for rate limiting tests
    # Rate limiting is REAL and tested - no bypasses, just proper timing
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Cleanup
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    
    # Restore original environment
    if original_env:
        os.environ["ENVIRONMENT"] = original_env
    elif "ENVIRONMENT" in os.environ:
        del os.environ["ENVIRONMENT"]


# Interface First Design Test Fixtures
# Following Phase 2 Step 4 security best practices

@pytest.fixture
def mock_asset_validation_service():
    """Create mock asset validation service following Interface First Design."""
    mock_service = Mock()
    
    # Default mock responses
    default_asset_info = Mock(
        symbol="AAPL",
        name="Apple Inc.",
        sector="Technology", 
        industry="Consumer Electronics",
        market_cap=3000000000000,
        pe_ratio=28.5,
        dividend_yield=0.005,
        is_valid=True,
        last_updated=datetime.now(timezone.utc)
    )
    
    default_validation_result = Mock(
        symbol="AAPL",
        is_valid=True,
        provider="yahoo_finance",
        confidence=1.0,
        error=None,
        timestamp=datetime.now(timezone.utc),
        source="real_time",
        asset_info=default_asset_info
    )
    
    # Configure async methods with proper async functions (not AsyncMock)
    async def validate_symbol_mixed_strategy_mock(symbol: str):
        """Mock validate_symbol_mixed_strategy with async function"""
        return ServiceResult(
            success=True,
            data=default_validation_result,
            message="Symbol validation completed"
        )
    
    async def validate_symbols_bulk_mixed_strategy_mock(symbols: list):
        """Mock validate_symbols_bulk_mixed_strategy with async function"""  
        results = {symbol: default_validation_result for symbol in symbols}
        return ServiceResult(
            success=True,
            data=results,
            message="Bulk validation completed"
        )
    
    # Assign async function mocks
    mock_service.validate_symbol_mixed_strategy = validate_symbol_mixed_strategy_mock
    mock_service.validate_symbols_bulk_mixed_strategy = validate_symbols_bulk_mixed_strategy_mock
    
    return mock_service


@pytest.fixture
def authenticated_test_user(db_session: Session):
    """Create a test user with proper authentication setup."""
    from app.core.security import AuthService
    auth_service = AuthService()
    
    test_user = User(
        id="test-user-authenticated",
        email="test@example.com",
        hashed_password=auth_service.get_password_hash("SecureTestPassword2025!"),
        full_name="Test User",
        role=UserRole.USER,
        subscription_tier=SubscriptionTier.PRO,
        is_verified=True
    )
    db_session.add(test_user)
    db_session.commit()
    return test_user


@pytest.fixture
def interface_first_client(client: TestClient, authenticated_test_user: User):
    """Create authenticated client using Interface First Design dependency override."""
    # Override authentication dependency
    from app.api.v1.auth import get_current_user
    
    def override_get_current_user():
        return authenticated_test_user
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    yield client, authenticated_test_user
    
    # Clean up dependency override (Security best practice)
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]


def setup_service_override(service_dependency, mock_service):
    """Utility function to setup service dependency override following Interface First Design."""
    def override_service():
        return mock_service
    
    app.dependency_overrides[service_dependency] = override_service
    return override_service


def cleanup_service_override(service_dependency):
    """Utility function to clean up service dependency override (Security best practice)."""
    if service_dependency in app.dependency_overrides:
        del app.dependency_overrides[service_dependency]


@pytest.fixture
def validation_service_override(mock_asset_validation_service):
    """Set up asset validation service override following Interface First Design."""
    from app.api.v1.assets import get_asset_validation_service
    
    setup_service_override(get_asset_validation_service, mock_asset_validation_service)
    
    yield mock_asset_validation_service
    
    cleanup_service_override(get_asset_validation_service)


@pytest.fixture
def mock_universe_service():
    """Create mock universe service following Interface First Design."""
    from unittest.mock import Mock
    from app.services.interfaces.base import ServiceResult
    from app.models.universe import Universe
    from datetime import datetime, timezone
    
    mock_service = Mock()
    
    # Track created universes for consistent responses
    mock_service._created_universes = {}
    
    # Mock methods using async functions to match service interface
    async def create_universe_mock(user_id: str, name: str, description: str = "", initial_symbols: list = None):
        """Create universe with actual parameters from test"""
        if initial_symbols is None:
            initial_symbols = []
            
        # Create mock universe object with required methods and attributes
        class MockUniverse:
            def __init__(self, id, name, description, owner_id, symbols):
                self.id = id
                self.name = name
                self.description = description
                self.owner_id = owner_id
                self.symbols = symbols or []
                self.turnover_rate = 0.0
                self.created_at = datetime.now(timezone.utc)
                self.updated_at = datetime.now(timezone.utc)
            
            def get_symbols(self):
                return self.symbols
            
            def get_asset_count(self):
                return len(self.symbols)
        
        universe = MockUniverse(
            id=f"test-universe-{hash(name) % 10000}",
            name=name,
            description=description,
            owner_id=user_id,
            symbols=initial_symbols
        )
        
        # Store for later retrieval
        mock_service._created_universes[universe.id] = universe
        
        return ServiceResult(
            success=True,
            data=universe,
            message=f"Universe '{name}' created successfully"
        )
    
    async def get_user_universes_mock(user_id: str):
        """List user universes - returns empty by default"""
        # Return universes created by this user
        user_universes = [u for u in mock_service._created_universes.values() if u.owner_id == user_id]
        return ServiceResult(
            success=True,
            data=user_universes,
            message=f"Retrieved {len(user_universes)} universes"
        )
    
    async def get_universe_by_id_mock(universe_id: str, user_id: str = None):
        """Get universe by ID - handles both API versions (with and without user_id)"""
        if universe_id in mock_service._created_universes:
            universe = mock_service._created_universes[universe_id]
            if not user_id or universe.owner_id == user_id:  # Check ownership if user_id provided
                return ServiceResult(
                    success=True,
                    data=universe,
                    message=f"Retrieved universe '{universe.name}' details"
                )
        
        return ServiceResult(
            success=False,
            data=None,
            error="Universe not found"
        )
    
    async def add_assets_to_universe_api_mock(universe_id: str, asset_symbols: list):
        """Add assets to universe - API version without user_id parameter"""
        if universe_id in mock_service._created_universes:
            universe = mock_service._created_universes[universe_id]
            # Update universe with new symbols
            existing_symbols = set(universe.symbols or [])
            new_symbols = set(asset_symbols)
            universe.symbols = list(existing_symbols.union(new_symbols))
            
            return ServiceResult(
                success=True,
                data={
                    "successful": [{"symbol": symbol} for symbol in asset_symbols],
                    "failed": [],
                    "success_count": len(asset_symbols),  # API expects success_count
                    "total_requested": len(asset_symbols)
                },
                message="Assets added successfully"
            )
        
        return ServiceResult(
            success=False,
            error="Universe not found"
        )
    
    async def remove_assets_from_universe_mock(universe_id: str, symbols: list, user_id: str):
        """Remove assets from universe"""
        if universe_id in mock_service._created_universes:
            universe = mock_service._created_universes[universe_id]
            if universe.owner_id == user_id:  # Check ownership
                existing_symbols = set(universe.symbols or [])
                symbols_to_remove = set(symbols)
                universe.symbols = list(existing_symbols - symbols_to_remove)
                
                return ServiceResult(
                    success=True,
                    data={
                        "removed_symbols": symbols,
                        "remaining_count": len(universe.symbols)
                    },
                    message="Assets removed successfully"
                )
        
        return ServiceResult(
            success=False,
            error="Universe not found"
        )
    
    async def remove_assets_from_universe_api_mock(universe_id: str, asset_symbols: list):
        """Remove assets from universe - API version without user_id parameter"""
        if universe_id in mock_service._created_universes:
            universe = mock_service._created_universes[universe_id]
            # Update universe by removing symbols
            existing_symbols = set(universe.symbols or [])
            symbols_to_remove = set(asset_symbols)
            universe.symbols = list(existing_symbols - symbols_to_remove)
            
            return ServiceResult(
                success=True,
                data={
                    "successful": [{"symbol": symbol} for symbol in asset_symbols],
                    "failed": [],
                    "success_count": len(asset_symbols),  # API expects success_count
                    "total_requested": len(asset_symbols)
                },
                message="Assets removed successfully"
            )
        
        return ServiceResult(
            success=False,
            error="Universe not found"
        )
    
    async def update_universe_mock(universe_id: str, user_id: str, name: str = None, description: str = None):
        """Update universe"""
        if universe_id in mock_service._created_universes:
            universe = mock_service._created_universes[universe_id]
            if universe.owner_id == user_id:  # Check ownership
                if name is not None:
                    universe.name = name
                if description is not None:
                    universe.description = description
                universe.updated_at = datetime.now(timezone.utc)
                
                return ServiceResult(
                    success=True,
                    data=universe,
                    message=f"Universe '{universe.name}' updated successfully"
                )
        
        return ServiceResult(
            success=False,
            error="Universe not found"
        )
    
    async def delete_universe_mock(universe_id: str, user_id: str):
        """Delete universe"""
        if universe_id in mock_service._created_universes:
            universe = mock_service._created_universes[universe_id]
            if universe.owner_id == user_id:  # Check ownership
                del mock_service._created_universes[universe_id]
                
                return ServiceResult(
                    success=True,
                    data={"deleted_universe_id": universe_id},
                    message=f"Universe '{universe.name}' deleted successfully"
                )
        
        return ServiceResult(
            success=False,
            error="Universe not found"
        )
    
    # Assign mock methods
    mock_service.create_universe = create_universe_mock
    mock_service.get_user_universes = get_user_universes_mock
    mock_service.get_universe_by_id = get_universe_by_id_mock
    mock_service.add_assets_to_universe_api = add_assets_to_universe_api_mock
    mock_service.remove_assets_from_universe = remove_assets_from_universe_mock
    mock_service.remove_assets_from_universe_api = remove_assets_from_universe_api_mock
    mock_service.update_universe = update_universe_mock
    mock_service.delete_universe = delete_universe_mock
    
    return mock_service


@pytest.fixture
def universe_service_override(mock_universe_service):
    """Set up universe service override following Interface First Design."""
    from app.api.v1.universes import get_universe_service
    
    setup_service_override(get_universe_service, mock_universe_service)
    
    yield mock_universe_service
    
    cleanup_service_override(get_universe_service)


@pytest.fixture(scope="function")
def real_rate_limit_client():
    """Create a test client with REAL rate limiting enabled (no bypasses)."""
    import os
    
    # Set testing environment but keep rate limiting active
    original_env = os.environ.get("ENVIRONMENT")
    os.environ["ENVIRONMENT"] = "testing_with_rate_limits"
    
    # Create tables in our test database
    Base.metadata.create_all(bind=engine)
    
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    # DO NOT override rate limiting - let it run with real limits but reasonable timeouts
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Cleanup
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    
    # Restore original environment
    if original_env:
        os.environ["ENVIRONMENT"] = original_env
    elif "ENVIRONMENT" in os.environ:
        del os.environ["ENVIRONMENT"]