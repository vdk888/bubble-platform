"""
Tests for Universe Service - Phase 2 Step 2 Validation
Testing RLS policies, CRUD operations, and AI-friendly responses
"""
import pytest
import asyncio
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.universe import Universe
from app.models.asset import Asset, UniverseAsset
from app.services.universe_service import UniverseService, ServiceResult, BulkResult


class TestUniverseServiceCRUD:
    """Test basic CRUD operations for Universe Service"""
    
    @pytest.fixture
    def service(self, db_session: Session) -> UniverseService:
        """Create UniverseService instance with test database session"""
        return UniverseService(db_session)
    
    @pytest.fixture
    def test_user(self, db_session: Session) -> User:
        """Create test user for universe operations"""
        from app.core.security import AuthService
        auth_service = AuthService()
        
        user = User(
            email="universe_test@example.com",
            hashed_password=auth_service.get_password_hash("SecureTestPassword2025!"),
            full_name="Universe Test User"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    @pytest.fixture
    def second_user(self, db_session: Session) -> User:
        """Create second test user for isolation testing"""
        from app.core.security import AuthService
        auth_service = AuthService()
        
        user = User(
            email="second_user@example.com",
            hashed_password=auth_service.get_password_hash("SecureTestPassword2025!"),
            full_name="Second Test User"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    @pytest.mark.asyncio
    async def test_create_universe_basic(self, service: UniverseService, test_user: User):
        """Test basic universe creation"""
        result = await service.create_universe(
            user_id=test_user.id,
            name="Tech Stocks",
            description="Technology companies"
        )
        
        assert result.success is True
        assert result.data is not None
        assert result.data["name"] == "Tech Stocks"
        assert result.data["description"] == "Technology companies"
        assert result.data["owner_id"] == test_user.id
        assert result.message == "Universe 'Tech Stocks' created successfully"
        assert "add_assets_to_universe" in result.next_actions
        assert result.metadata["asset_count"] == 0
    
    @pytest.mark.asyncio
    async def test_create_universe_with_initial_assets(self, service: UniverseService, test_user: User):
        """Test universe creation with initial asset symbols"""
        result = await service.create_universe(
            user_id=test_user.id,
            name="Tech Universe",
            description="Tech stocks",
            initial_symbols=["AAPL", "GOOGL", "MSFT"]
        )
        
        if not result.success:
            print(f"ERROR: {result.error}")
            print(f"MESSAGE: {result.message}")
        
        assert result.success is True
        assert result.metadata["asset_count"] == 3
        assert result.metadata["bulk_add_result"] is not None
        assert result.metadata["bulk_add_result"]["success_count"] == 3
    
    @pytest.mark.asyncio
    async def test_create_universe_duplicate_name(self, service: UniverseService, test_user: User):
        """Test universe creation with duplicate name fails"""
        # Create first universe
        await service.create_universe(
            user_id=test_user.id,
            name="Duplicate Test",
            description="First universe"
        )
        
        # Try to create second with same name
        result = await service.create_universe(
            user_id=test_user.id,
            name="Duplicate Test",
            description="Second universe"
        )
        
        assert result.success is False
        assert "already exists" in result.error
        assert "choose_different_name" in result.next_actions
    
    @pytest.mark.asyncio
    async def test_create_universe_invalid_user(self, service: UniverseService):
        """Test universe creation with invalid user ID"""
        result = await service.create_universe(
            user_id="invalid-user-id",
            name="Test Universe",
            description="Should fail"
        )
        
        assert result.success is False
        assert result.error == "User not found"
    
    @pytest.mark.asyncio
    async def test_get_user_universes_empty(self, service: UniverseService, test_user: User):
        """Test getting universes when user has none"""
        result = await service.get_user_universes(test_user.id)
        
        assert result.success is True
        assert result.data == []
        assert result.metadata["total_universes"] == 0
        assert "create_new_universe" in result.next_actions
    
    @pytest.mark.asyncio
    async def test_get_user_universes_with_data(self, service: UniverseService, test_user: User):
        """Test getting universes with existing data"""
        # Create test universes
        await service.create_universe(test_user.id, "Universe 1", "First universe")
        await service.create_universe(test_user.id, "Universe 2", "Second universe")
        
        result = await service.get_user_universes(test_user.id)
        
        assert result.success is True
        assert len(result.data) == 2
        assert result.metadata["total_universes"] == 2
        assert any(u["name"] == "Universe 1" for u in result.data)
        assert any(u["name"] == "Universe 2" for u in result.data)
    
    @pytest.mark.asyncio
    async def test_get_universe_by_id(self, service: UniverseService, test_user: User):
        """Test getting specific universe by ID"""
        # Create universe
        create_result = await service.create_universe(test_user.id, "Test Universe", "Test description")
        universe_id = create_result.data["id"]
        
        # Get universe by ID
        result = await service.get_universe_by_id_with_user(universe_id, test_user.id)
        
        assert result.success is True
        assert result.data["id"] == universe_id
        assert result.data["name"] == "Test Universe"
        assert result.data["owner_id"] == test_user.id
        assert "add_assets_to_universe" in result.next_actions
    
    @pytest.mark.asyncio
    async def test_get_universe_by_id_not_found(self, service: UniverseService, test_user: User):
        """Test getting non-existent universe"""
        result = await service.get_universe_by_id_with_user("invalid-universe-id", test_user.id)
        
        assert result.success is False
        assert result.error == "Universe not found"
        assert "list_user_universes" in result.next_actions
    
    @pytest.mark.asyncio
    async def test_update_universe(self, service: UniverseService, test_user: User):
        """Test updating universe details"""
        # Create universe
        create_result = await service.create_universe(test_user.id, "Original Name", "Original description")
        universe_id = create_result.data["id"]
        
        # Update universe
        result = await service.update_universe(
            universe_id=universe_id,
            user_id=test_user.id,
            name="Updated Name",
            description="Updated description",
            screening_criteria={"min_market_cap": 1000000000}
        )
        
        assert result.success is True
        assert result.data["name"] == "Updated Name"
        assert result.data["description"] == "Updated description"
        assert result.data["screening_criteria"]["min_market_cap"] == 1000000000
        assert result.metadata["changes_made"] == ["name", "description", "screening_criteria"]
    
    @pytest.mark.asyncio
    async def test_update_universe_duplicate_name(self, service: UniverseService, test_user: User):
        """Test updating universe with duplicate name fails"""
        # Create two universes
        await service.create_universe(test_user.id, "Universe 1", "First")
        create_result2 = await service.create_universe(test_user.id, "Universe 2", "Second")
        universe_id = create_result2.data["id"]
        
        # Try to update second universe to have same name as first
        result = await service.update_universe(
            universe_id=universe_id,
            user_id=test_user.id,
            name="Universe 1"
        )
        
        assert result.success is False
        assert "already exists" in result.error
    
    @pytest.mark.asyncio
    async def test_delete_universe(self, service: UniverseService, test_user: User):
        """Test deleting universe"""
        # Create universe
        create_result = await service.create_universe(test_user.id, "To Delete", "Will be deleted")
        universe_id = create_result.data["id"]
        
        # Delete universe
        result = await service.delete_universe(universe_id, test_user.id)
        
        assert result.success is True
        assert result.data["deleted_universe_name"] == "To Delete"
        assert result.data["deleted_universe_id"] == universe_id
        assert "create_new_universe" in result.next_actions
        
        # Verify universe is gone
        get_result = await service.get_universe_by_id_with_user(universe_id, test_user.id)
        assert get_result.success is False


class TestUniverseServiceAssetManagement:
    """Test asset management operations"""
    
    @pytest.fixture
    def service(self, db_session: Session) -> UniverseService:
        """Create UniverseService instance"""
        return UniverseService(db_session)
    
    @pytest.fixture
    def test_user(self, db_session: Session) -> User:
        """Create test user"""
        from app.core.security import AuthService
        auth_service = AuthService()
        
        user = User(
            email="asset_test@example.com",
            hashed_password=auth_service.get_password_hash("SecureTestPassword2025!"),
            full_name="Asset Test User"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    @pytest.fixture
    def test_universe_id(self) -> str:
        """Return a test universe ID that will be created in each test"""
        return None  # Will be created by individual tests
    
    @pytest.mark.asyncio
    async def test_add_assets_to_universe(self, service: UniverseService, test_user: User):
        """Test adding assets to universe"""
        # Create test universe first
        create_result = await service.create_universe(test_user.id, "Asset Test Universe", "For testing assets")
        test_universe = create_result.data["id"]
        
        result = await service.add_assets_to_universe(
            universe_id=test_universe,
            asset_symbols=["AAPL", "GOOGL", "MSFT"],
            user_id=test_user.id
        )
        
        assert result.success is True
        assert result.data["success_count"] == 3
        assert result.data["failure_count"] == 0
        assert len(result.data["successful"]) == 3
        assert result.metadata["total_assets_in_universe"] == 3
        
        # Verify assets were created
        assert all(item["symbol"] in ["AAPL", "GOOGL", "MSFT"] for item in result.data["successful"])
    
    @pytest.mark.asyncio
    async def test_add_duplicate_assets(self, service: UniverseService, test_user: User):
        """Test adding duplicate assets shows warnings"""
        # Create test universe first
        create_result = await service.create_universe(test_user.id, "Duplicate Test Universe", "For testing duplicates")
        test_universe = create_result.data["id"]
        
        # Add initial assets
        await service.add_assets_to_universe(test_universe, ["AAPL", "GOOGL"], test_user.id)
        
        # Try to add same assets again
        result = await service.add_assets_to_universe(
            test_universe, ["AAPL", "MSFT"], test_user.id
        )
        
        assert result.success is True
        assert result.data["success_count"] == 1  # Only MSFT should be added
        assert "Asset AAPL already in universe" in result.data["warnings"]
    
    @pytest.mark.asyncio
    async def test_remove_assets_from_universe(self, service: UniverseService, test_user: User):
        """Test removing assets from universe"""
        # Create test universe first
        create_result = await service.create_universe(test_user.id, "Remove Test Universe", "For testing removal")
        test_universe = create_result.data["id"]
        
        # Add assets first
        await service.add_assets_to_universe(test_universe, ["AAPL", "GOOGL", "MSFT"], test_user.id)
        
        # Remove some assets
        result = await service.remove_assets_from_universe(
            universe_id=test_universe,
            asset_symbols=["GOOGL", "MSFT"],
            user_id=test_user.id
        )
        
        assert result.success is True
        assert result.data["success_count"] == 2
        assert result.data["failure_count"] == 0
        assert len(result.data["successful"]) == 2
        
        # Verify universe still has remaining asset
        universe_result = await service.get_universe_by_id_with_user(test_universe, test_user.id)
        assert universe_result.data["asset_count"] == 1
    
    @pytest.mark.asyncio
    async def test_remove_nonexistent_assets(self, service: UniverseService, test_user: User):
        """Test removing assets that aren't in universe"""
        # Create test universe first
        create_result = await service.create_universe(test_user.id, "Remove Test Universe", "For testing removal")
        test_universe = create_result.data["id"]
        
        result = await service.remove_assets_from_universe(
            universe_id=test_universe,
            asset_symbols=["NONEXISTENT"],
            user_id=test_user.id
        )
        
        assert result.success is False
        assert result.data["success_count"] == 0
        assert result.data["failure_count"] == 1
        assert "Asset not found in universe" in result.data["failed"][0]["error"]
    
    @pytest.mark.asyncio
    async def test_calculate_turnover_rate(self, service: UniverseService, test_user: User):
        """Test turnover rate calculation"""
        # Create test universe first
        create_result = await service.create_universe(test_user.id, "Turnover Test Universe", "For testing turnover")
        test_universe = create_result.data["id"]
        
        result = await service.calculate_turnover_rate(test_universe)
        
        assert result.success is True
        assert "turnover_rate" in result.data
        assert result.data["universe_id"] == test_universe
        assert isinstance(result.data["turnover_rate"], (int, float))


class TestUniverseServiceMultiTenant:
    """Test multi-tenant isolation and RLS policies"""
    
    @pytest.fixture
    def service(self, db_session: Session) -> UniverseService:
        """Create UniverseService instance"""
        return UniverseService(db_session)
    
    @pytest.fixture
    def user1(self, db_session: Session) -> User:
        """First test user"""
        from app.core.security import AuthService
        auth_service = AuthService()
        
        user = User(
            email="user1@example.com",
            hashed_password=auth_service.get_password_hash("SecureTestPassword1_2025!"),
            full_name="User One"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    @pytest.fixture
    def user2(self, db_session: Session) -> User:
        """Second test user"""
        from app.core.security import AuthService
        auth_service = AuthService()
        
        user = User(
            email="user2@example.com",
            hashed_password=auth_service.get_password_hash("SecureTestPassword2_2025!"),
            full_name="User Two"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    @pytest.mark.asyncio
    async def test_user_isolation_get_universes(self, service: UniverseService, user1: User, user2: User):
        """Test that users can only see their own universes"""
        # Create universes for both users
        await service.create_universe(user1.id, "User1 Universe", "Belongs to user 1")
        await service.create_universe(user2.id, "User2 Universe", "Belongs to user 2")
        
        # Each user should only see their own universe
        user1_result = await service.get_user_universes(user1.id)
        user2_result = await service.get_user_universes(user2.id)
        
        assert user1_result.success is True
        assert len(user1_result.data) == 1
        assert user1_result.data[0]["name"] == "User1 Universe"
        
        assert user2_result.success is True
        assert len(user2_result.data) == 1
        assert user2_result.data[0]["name"] == "User2 Universe"
    
    @pytest.mark.asyncio
    async def test_user_isolation_get_universe_by_id(self, service: UniverseService, user1: User, user2: User):
        """Test that users cannot access other users' universes by ID"""
        # User1 creates universe
        create_result = await service.create_universe(user1.id, "User1 Universe", "Private universe")
        universe_id = create_result.data["id"]
        
        # User1 can access their universe
        user1_result = await service.get_universe_by_id_with_user(universe_id, user1.id)
        assert user1_result.success is True
        
        # User2 cannot access User1's universe
        user2_result = await service.get_universe_by_id_with_user(universe_id, user2.id)
        assert user2_result.success is False
        assert user2_result.error == "Universe not found"
    
    @pytest.mark.asyncio
    async def test_user_isolation_update_universe(self, service: UniverseService, user1: User, user2: User):
        """Test that users cannot modify other users' universes"""
        # User1 creates universe
        create_result = await service.create_universe(user1.id, "User1 Universe", "Original description")
        universe_id = create_result.data["id"]
        
        # User2 cannot update User1's universe
        user2_update = await service.update_universe(
            universe_id=universe_id,
            user_id=user2.id,
            name="Hacked Name"
        )
        
        assert user2_update.success is False
        assert user2_update.error == "Universe not found"
        
        # Verify universe remains unchanged
        user1_get = await service.get_universe_by_id_with_user(universe_id, user1.id)
        assert user1_get.data["name"] == "User1 Universe"
    
    @pytest.mark.asyncio
    async def test_user_isolation_delete_universe(self, service: UniverseService, user1: User, user2: User):
        """Test that users cannot delete other users' universes"""
        # User1 creates universe
        create_result = await service.create_universe(user1.id, "User1 Universe", "To be protected")
        universe_id = create_result.data["id"]
        
        # User2 cannot delete User1's universe
        user2_delete = await service.delete_universe(universe_id, user2.id)
        
        assert user2_delete.success is False
        assert user2_delete.error == "Universe not found"
        
        # Verify universe still exists
        user1_get = await service.get_universe_by_id_with_user(universe_id, user1.id)
        assert user1_get.success is True
    
    @pytest.mark.asyncio
    async def test_user_isolation_asset_management(self, service: UniverseService, user1: User, user2: User):
        """Test that users cannot modify assets in other users' universes"""
        # User1 creates universe
        create_result = await service.create_universe(user1.id, "User1 Universe", "Private assets")
        universe_id = create_result.data["id"]
        
        # User2 cannot add assets to User1's universe
        add_result = await service.add_assets_to_universe(
            universe_id=universe_id,
            asset_symbols=["HACK"],
            user_id=user2.id
        )
        
        assert add_result.success is False
        assert add_result.error == "Access denied"


class TestUniverseServiceAIFriendlyResponses:
    """Test AI-friendly response formats and next actions"""
    
    @pytest.fixture
    def service(self, db_session: Session) -> UniverseService:
        """Create UniverseService instance"""
        return UniverseService(db_session)
    
    @pytest.fixture
    def test_user(self, db_session: Session) -> User:
        """Create test user"""
        from app.core.security import AuthService
        auth_service = AuthService()
        
        user = User(
            email="ai_test@example.com",
            hashed_password=auth_service.get_password_hash("SecureTestPassword2025!"),
            full_name="AI Test User"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    
    @pytest.mark.asyncio
    async def test_ai_response_format_structure(self, service: UniverseService, test_user: User):
        """Test that all responses follow AI-friendly format"""
        result = await service.create_universe(test_user.id, "AI Test Universe", "Testing AI responses")
        
        # Verify response structure
        assert hasattr(result, 'success')
        assert hasattr(result, 'data')
        assert hasattr(result, 'error')
        assert hasattr(result, 'message')
        assert hasattr(result, 'next_actions')
        assert hasattr(result, 'metadata')
        
        # Test to_dict method for AI consumption
        response_dict = result.to_dict()
        required_keys = ["success", "data", "error", "message", "next_actions", "metadata"]
        assert all(key in response_dict for key in required_keys)
    
    @pytest.mark.asyncio
    async def test_next_actions_appropriateness(self, service: UniverseService, test_user: User):
        """Test that next_actions are appropriate for each operation"""
        # Create universe - should suggest adding assets
        create_result = await service.create_universe(test_user.id, "Test Universe", "For next actions test")
        assert "add_assets_to_universe" in create_result.next_actions
        assert "create_strategy_from_universe" in create_result.next_actions
        
        # Get empty universe list - should suggest creating universe
        empty_result = await service.get_user_universes("nonexistent-user-id")
        # This will fail, but for a real empty result:
        user_result = await service.get_user_universes(test_user.id)
        assert "select_universe_for_strategy" in user_result.next_actions
        
        # Add assets - should suggest validation
        universe_id = create_result.data["id"]
        add_result = await service.add_assets_to_universe(universe_id, ["AAPL"], test_user.id)
        assert "validate_new_assets" in add_result.next_actions
    
    @pytest.mark.asyncio
    async def test_metadata_completeness(self, service: UniverseService, test_user: User):
        """Test that metadata contains useful information for AI context"""
        # Create universe with assets
        result = await service.create_universe(
            test_user.id, 
            "Metadata Test", 
            "Testing metadata", 
            initial_symbols=["AAPL", "GOOGL"]
        )
        
        assert "universe_id" in result.metadata
        assert "asset_count" in result.metadata
        assert result.metadata["asset_count"] == 2
        assert "bulk_add_result" in result.metadata
        
        # Get universe - should have comprehensive metadata
        universe_id = result.data["id"]
        get_result = await service.get_universe_by_id_with_user(universe_id, test_user.id)
        
        assert "universe_id" in get_result.metadata
        assert "asset_count" in get_result.metadata
        assert "last_modified" in get_result.metadata
    
    def test_service_result_bulk_result_serialization(self):
        """Test that ServiceResult and BulkResult can be properly serialized"""
        # Test BulkResult
        bulk_result = BulkResult()
        bulk_result.successful.append({"symbol": "AAPL", "id": "123"})
        bulk_result.failed.append({"symbol": "INVALID", "error": "Not found"})
        
        bulk_dict = bulk_result.to_dict()
        assert bulk_dict["success_count"] == 1
        assert bulk_dict["failure_count"] == 1
        assert bulk_dict["total_processed"] == 2
        
        # Test ServiceResult
        service_result = ServiceResult(
            success=True,
            data=bulk_dict,
            message="Test message",
            next_actions=["action1", "action2"],
            metadata={"key": "value"}
        )
        
        result_dict = service_result.to_dict()
        assert result_dict["success"] is True
        assert result_dict["data"] == bulk_dict
        assert len(result_dict["next_actions"]) == 2
        assert result_dict["metadata"]["key"] == "value"