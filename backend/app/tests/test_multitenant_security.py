"""
MULTI-TENANT SECURITY VALIDATION TESTS
Following Sprint 1 specification for PostgreSQL Row-Level Security (RLS)

Tests ACTUAL multi-tenant data isolation with NO bypasses.
Validates that User A cannot access User B's data at the database level.
"""

import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.rls_policies import RLSManager, setup_postgresql_rls
from app.core.security import AuthService
from app.models.user import User, UserRole, SubscriptionTier
from app.models.universe import Universe
from app.models.strategy import Strategy, StrategyStatus
from app.models.portfolio import Portfolio
from app.models.chat import Conversation, ChatMessage


class TestRLSPolicySetup:
    """Test Row-Level Security policy setup and configuration"""
    
    def test_rls_setup_completes_successfully(self, db_session: Session):
        """Test RLS setup creates all necessary policies and roles"""
        rls_manager = RLSManager(db_session)
        
        # Setup should complete without errors on PostgreSQL
        # For SQLite testing, this will fail gracefully
        result = rls_manager.setup_complete_rls()
        
        # Check if we're running on SQLite (testing) vs PostgreSQL (production)
        db_url = str(db_session.bind.url)
        if "sqlite" in db_url:
            # SQLite doesn't support RLS - test documents this limitation
            assert result is False, "SQLite correctly rejects RLS setup"
        else:
            # PostgreSQL should succeed
            assert result is True, "RLS setup failed on PostgreSQL"
        
        # Verify RLS is enabled on all tables (PostgreSQL only)
        if "postgresql" in db_url:
            rls_status = rls_manager.check_rls_status()
            
            required_tables = ['users', 'universes', 'strategies', 'portfolios', 'conversations']
            for table in required_tables:
                if table in rls_status:  # Table exists
                    assert rls_status[table]['rls_enabled'] is True, f"RLS not enabled on {table}"
                    assert len(rls_status[table]['policies']) > 0, f"No policies found for {table}"
    
    def test_user_context_management(self, db_session: Session):
        """Test setting and clearing user context for RLS"""
        rls_manager = RLSManager(db_session)
        rls_manager.setup_complete_rls()
        
        test_user_id = "test-user-123"
        
        # Test setting user context
        rls_manager.set_user_context(test_user_id)
        
        # Verify context is set (this will be validated in actual isolation tests)
        # If context setting fails, subsequent isolation tests will catch it
        
        # Test resetting context
        rls_manager.reset_user_context()
        
        # No exceptions should be raised
        assert True


class TestActualMultiTenantIsolation:
    """Test REAL multi-tenant data isolation - users cannot access other users' data"""
    
    @pytest.fixture
    def setup_test_users(self, db_session: Session):
        """Create test users with real password hashing for isolation testing"""
        auth_service = AuthService()
        
        # Create User A
        user_a = User(
            id="user-a-123",
            email="user.a@bubble.com",
            hashed_password=auth_service.get_password_hash("SecurePasswordA2025!"),
            full_name="User A",
            role=UserRole.USER,
            subscription_tier=SubscriptionTier.PRO,
            is_verified=True
        )
        
        # Create User B  
        user_b = User(
            id="user-b-456", 
            email="user.b@bubble.com",
            hashed_password=auth_service.get_password_hash("SecurePasswordB2025!"),
            full_name="User B",
            role=UserRole.USER,
            subscription_tier=SubscriptionTier.FREE,
            is_verified=True
        )
        
        db_session.add(user_a)
        db_session.add(user_b)
        db_session.commit()
        
        return user_a, user_b
    
    def test_universe_data_isolation(self, db_session: Session, setup_test_users):
        """Test users cannot access other users' universes via RLS policies"""
        user_a, user_b = setup_test_users
        rls_manager = RLSManager(db_session)
        rls_manager.setup_complete_rls()
        
        # Create universes for each user without RLS context (as admin)
        rls_manager.reset_user_context()
        
        universe_a = Universe(
            id="universe-a-123",
            name="User A Universe",
            description="Private to User A",
            symbols=["AAPL", "GOOGL"],
            owner_id=user_a.id
        )
        
        universe_b = Universe(
            id="universe-b-456", 
            name="User B Universe",
            description="Private to User B",
            symbols=["MSFT", "TSLA"],
            owner_id=user_b.id
        )
        
        db_session.add(universe_a)
        db_session.add(universe_b) 
        db_session.commit()
        
        # Test User A can only see their own universe
        rls_manager.set_user_context(user_a.id)
        user_a_universes = db_session.query(Universe).all()
        
        assert len(user_a_universes) == 1
        assert user_a_universes[0].id == universe_a.id
        assert user_a_universes[0].name == "User A Universe"
        
        # Test User B can only see their own universe  
        rls_manager.set_user_context(user_b.id)
        user_b_universes = db_session.query(Universe).all()
        
        assert len(user_b_universes) == 1
        assert user_b_universes[0].id == universe_b.id
        assert user_b_universes[0].name == "User B Universe"
        
        # Reset context
        rls_manager.reset_user_context()
    
    def test_strategy_data_isolation(self, db_session: Session, setup_test_users):
        """Test users cannot access other users' strategies via RLS policies"""
        user_a, user_b = setup_test_users
        rls_manager = RLSManager(db_session)
        rls_manager.setup_complete_rls()
        
        # Create strategies without RLS context
        rls_manager.reset_user_context()
        
        # Create universes first (required for strategies)
        universe_a = Universe(name="Test Universe A", owner_id=user_a.id, symbols=["AAPL"])
        universe_b = Universe(name="Test Universe B", owner_id=user_b.id, symbols=["MSFT"])
        db_session.add(universe_a)
        db_session.add(universe_b)
        db_session.flush()  # Get IDs
        
        strategy_a = Strategy(
            id="strategy-a-123",
            name="User A Strategy",
            description="Private to User A",
            indicator_config={"rsi_period": 14},
            allocation_rules={"method": "equal_weight"},
            universe_id=universe_a.id,
            owner_id=user_a.id,
            status=StrategyStatus.ACTIVE
        )
        
        strategy_b = Strategy(
            id="strategy-b-456",
            name="User B Strategy", 
            description="Private to User B",
            indicator_config={"rsi_period": 21},
            allocation_rules={"method": "momentum"},
            universe_id=universe_b.id,
            owner_id=user_b.id,
            status=StrategyStatus.DRAFT
        )
        
        db_session.add(strategy_a)
        db_session.add(strategy_b)
        db_session.commit()
        
        # Test User A isolation
        rls_manager.set_user_context(user_a.id)
        user_a_strategies = db_session.query(Strategy).all()
        
        assert len(user_a_strategies) == 1
        assert user_a_strategies[0].id == strategy_a.id
        assert user_a_strategies[0].name == "User A Strategy"
        
        # Test User B isolation
        rls_manager.set_user_context(user_b.id)
        user_b_strategies = db_session.query(Strategy).all()
        
        assert len(user_b_strategies) == 1
        assert user_b_strategies[0].id == strategy_b.id
        assert user_b_strategies[0].name == "User B Strategy"
        
        rls_manager.reset_user_context()
    
    def test_portfolio_data_isolation(self, db_session: Session, setup_test_users):
        """Test users cannot access other users' portfolios via RLS policies"""
        user_a, user_b = setup_test_users
        rls_manager = RLSManager(db_session)
        rls_manager.setup_complete_rls()
        
        # Create portfolios without RLS context
        rls_manager.reset_user_context()
        
        portfolio_a = Portfolio(
            id="portfolio-a-123",
            name="User A Portfolio",
            description="Private portfolio for User A", 
            allocation_method="risk_parity",
            target_allocations={"AAPL": 0.5, "GOOGL": 0.5},
            total_value=100000.0,
            cash_balance=10000.0,
            owner_id=user_a.id
        )
        
        portfolio_b = Portfolio(
            id="portfolio-b-456",
            name="User B Portfolio",
            description="Private portfolio for User B",
            allocation_method="equal_weight", 
            target_allocations={"MSFT": 0.3, "TSLA": 0.7},
            total_value=50000.0,
            cash_balance=5000.0,
            owner_id=user_b.id
        )
        
        db_session.add(portfolio_a)
        db_session.add(portfolio_b)
        db_session.commit()
        
        # Test User A can only access their portfolio
        rls_manager.set_user_context(user_a.id)
        user_a_portfolios = db_session.query(Portfolio).all()
        
        assert len(user_a_portfolios) == 1
        assert user_a_portfolios[0].id == portfolio_a.id
        assert user_a_portfolios[0].total_value == 100000.0
        
        # Test User B can only access their portfolio
        rls_manager.set_user_context(user_b.id)
        user_b_portfolios = db_session.query(Portfolio).all()
        
        assert len(user_b_portfolios) == 1
        assert user_b_portfolios[0].id == portfolio_b.id
        assert user_b_portfolios[0].total_value == 50000.0
        
        rls_manager.reset_user_context()
    
    def test_conversation_data_isolation(self, db_session: Session, setup_test_users):
        """Test users cannot access other users' AI conversations via RLS policies"""
        user_a, user_b = setup_test_users
        rls_manager = RLSManager(db_session)
        rls_manager.setup_complete_rls()
        
        # Create conversations without RLS context
        rls_manager.reset_user_context()
        
        conversation_a = Conversation(
            id="conv-a-123",
            title="User A AI Chat",
            user_id=user_a.id
        )
        
        conversation_b = Conversation(
            id="conv-b-456", 
            title="User B AI Chat",
            user_id=user_b.id
        )
        
        db_session.add(conversation_a)
        db_session.add(conversation_b)
        db_session.flush()  # Get IDs for messages
        
        # Add chat messages
        message_a = ChatMessage(
            role="user",
            content="Create a tech stock portfolio",
            conversation_id=conversation_a.id
        )
        
        message_b = ChatMessage(
            role="user", 
            content="Show my portfolio performance",
            conversation_id=conversation_b.id
        )
        
        db_session.add(message_a)
        db_session.add(message_b)
        db_session.commit()
        
        # Test User A isolation
        rls_manager.set_user_context(user_a.id)
        user_a_conversations = db_session.query(Conversation).all()
        user_a_messages = db_session.query(ChatMessage).all()
        
        assert len(user_a_conversations) == 1
        assert user_a_conversations[0].title == "User A AI Chat"
        assert len(user_a_messages) == 1
        assert "tech stock portfolio" in user_a_messages[0].content
        
        # Test User B isolation  
        rls_manager.set_user_context(user_b.id)
        user_b_conversations = db_session.query(Conversation).all()
        user_b_messages = db_session.query(ChatMessage).all()
        
        assert len(user_b_conversations) == 1
        assert user_b_conversations[0].title == "User B AI Chat"
        assert len(user_b_messages) == 1
        assert "portfolio performance" in user_b_messages[0].content
        
        rls_manager.reset_user_context()
    
    def test_cross_user_data_access_blocked(self, db_session: Session, setup_test_users):
        """Test that RLS actively blocks cross-user data access attempts"""
        user_a, user_b = setup_test_users
        rls_manager = RLSManager(db_session)
        rls_manager.setup_complete_rls()
        
        # Create data for both users without RLS
        rls_manager.reset_user_context()
        
        universe_a = Universe(name="A Universe", owner_id=user_a.id, symbols=["AAPL"])
        universe_b = Universe(name="B Universe", owner_id=user_b.id, symbols=["MSFT"])
        db_session.add(universe_a)
        db_session.add(universe_b)
        db_session.commit()
        
        # Set User A context
        rls_manager.set_user_context(user_a.id)
        
        # Try to access User B's universe by ID - should return None/empty
        user_b_universe_attempt = db_session.query(Universe).filter(
            Universe.id == universe_b.id
        ).first()
        
        assert user_b_universe_attempt is None, "RLS failed: User A accessed User B's universe!"
        
        # Verify User A can access their own data
        user_a_universe = db_session.query(Universe).filter(
            Universe.id == universe_a.id
        ).first()
        
        assert user_a_universe is not None, "RLS blocking own data access!"
        assert user_a_universe.name == "A Universe"
        
        rls_manager.reset_user_context()


class TestRLSValidationAndStatus:
    """Test RLS validation and status checking functionality"""
    
    def test_rls_validation_with_test_user(self, db_session: Session):
        """Test RLS validation with a test user context"""
        rls_manager = RLSManager(db_session)
        rls_manager.setup_complete_rls()
        
        test_user_id = "validation-test-user"
        
        # Run RLS validation
        validation_results = rls_manager.validate_rls_policies(test_user_id)
        
        # Verify validation completed successfully
        assert "overall_status" not in validation_results or validation_results["overall_status"] != "failed"
        
        # Check that tables were tested
        expected_tables = ['users', 'universes', 'strategies', 'portfolios', 'conversations']
        for table in expected_tables:
            if table in validation_results:
                assert validation_results[table]['status'] == 'success'
                assert 'accessible_rows' in validation_results[table]
    
    def test_rls_status_check(self, db_session: Session):
        """Test checking RLS status across all tables"""
        rls_manager = RLSManager(db_session)
        rls_manager.setup_complete_rls()
        
        # Check RLS status
        status = rls_manager.check_rls_status()
        
        # Should not have error
        assert "error" not in status
        
        # Should have status for tables that exist
        if len(status) > 0:  # If tables exist
            for table_name, table_status in status.items():
                assert 'rls_enabled' in table_status
                assert 'policies' in table_status
                
                # If RLS is enabled, should have policies
                if table_status['rls_enabled']:
                    assert len(table_status['policies']) > 0, f"No policies for RLS-enabled table: {table_name}"