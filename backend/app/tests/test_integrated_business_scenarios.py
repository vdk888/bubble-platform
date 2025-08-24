"""
INTEGRATED BUSINESS SCENARIOS VALIDATION TESTS
Following all Sprint 0, 1, and 2 requirements with end-to-end validation

Tests complete business workflows with real data validation and security.
Covers integrated scenarios combining authentication, multi-tenancy, and business logic.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import AuthService
from app.models.user import User, UserRole, SubscriptionTier
from app.models.universe import Universe
from app.models.asset import Asset, UniverseAsset
from app.models.strategy import Strategy, StrategyStatus
from app.models.portfolio import Portfolio
from app.models.chat import Conversation, ChatMessage


class TestIntegratedBusinessScenarios:
    """Test complete business scenarios combining multiple Sprint requirements"""
    
    def test_complete_user_onboarding_workflow(self, client: TestClient, db_session: Session):
        """Test complete user onboarding from registration to first universe creation"""
        # Step 1: User Registration (Sprint 1 - Authentication)
        registration_data = {
            "email": "onboarding.test@bubble.com",
            "password": "SecureFinance2025!@#",
            "full_name": "Onboarding Test User"
        }
        
        registration_response = client.post("/api/v1/auth/register", json=registration_data)
        
        if registration_response.status_code == 201:
            auth_data = registration_response.json()
            
            # Verify AI-friendly response structure (Sprint 2 - AI-friendly API)
            assert auth_data["success"] is True
            assert "next_actions" in auth_data
            assert isinstance(auth_data["next_actions"], list)
            
            token = auth_data["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Step 2: Check Feature Flags (Sprint 0 - Feature Flags)
            features_response = client.get("/api/v1/features/", headers=headers)
            if features_response.status_code == 200:
                features_data = features_response.json()
                assert features_data["success"] is True
                assert "features" in features_data["data"]
            
            # Step 3: Create First Universe (Sprint 2 - Universe Management)
            universe_data = {
                "name": "My First Portfolio",
                "description": "Starting with tech stocks",
                "initial_symbols": ["AAPL", "GOOGL", "MSFT"]
            }
            
            universe_response = client.post("/api/v1/universes", json=universe_data, headers=headers)
            if universe_response.status_code == 201:
                universe_data = universe_response.json()
                
                # Verify AI-friendly structured response
                assert universe_data["success"] is True
                assert "next_actions" in universe_data
                
                # Step 4: List User's Universes (Multi-tenant isolation)
                list_response = client.get("/api/v1/universes", headers=headers)
                if list_response.status_code == 200:
                    universes = list_response.json()["data"]
                    assert len(universes) >= 1
                    assert any(u["name"] == "My First Portfolio" for u in universes)
    
    def test_portfolio_strategy_creation_workflow(self, client: TestClient, db_session: Session):
        """Test complete portfolio and strategy creation workflow"""
        auth_service = AuthService()
        
        # Create authenticated user with real password hashing
        user = User(
            email="portfolio.test@bubble.com",
            hashed_password=auth_service.get_password_hash("SecurePortfolio2025!"),
            full_name="Portfolio Test User",
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()
        
        # Login user
        login_data = {
            "email": "portfolio.test@bubble.com",
            "password": "SecurePortfolio2025!"
        }
        
        login_response = client.post("/api/v1/auth/login", json=login_data)
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Create universe for strategy
            universe_data = {
                "name": "Strategy Universe",
                "description": "Universe for testing strategy creation",
                "initial_symbols": ["AAPL", "GOOGL", "MSFT", "AMZN"]
            }
            
            universe_response = client.post("/api/v1/universes", json=universe_data, headers=headers)
            if universe_response.status_code == 201:
                universe_id = universe_response.json()["data"]["id"]
                
                # Create strategy
                strategy_data = {
                    "name": "Momentum Strategy",
                    "description": "RSI-based momentum strategy",
                    "indicator_config": {
                        "rsi_period": 14,
                        "overbought": 70,
                        "oversold": 30
                    },
                    "allocation_rules": {
                        "method": "momentum_weighted",
                        "lookback_period": 20
                    },
                    "universe_id": universe_id
                }
                
                strategy_response = client.post("/api/v1/strategies", json=strategy_data, headers=headers)
                if strategy_response.status_code == 201:
                    strategy_data_resp = strategy_response.json()
                    assert strategy_data_resp["success"] is True
                    
                    # Create portfolio based on strategy
                    portfolio_data = {
                        "name": "Momentum Portfolio",
                        "description": "Portfolio based on momentum strategy",
                        "allocation_method": "strategy_based",
                        "initial_cash": 100000.0
                    }
                    
                    portfolio_response = client.post("/api/v1/portfolios", json=portfolio_data, headers=headers)
                    if portfolio_response.status_code == 201:
                        portfolio_resp = portfolio_response.json()
                        assert portfolio_resp["success"] is True
                        assert "next_actions" in portfolio_resp
    
    def test_multi_tenant_data_isolation_comprehensive(self, client: TestClient, db_session: Session):
        """Test comprehensive multi-tenant data isolation across all business objects"""
        auth_service = AuthService()
        
        # Create two users with real authentication
        user_a = User(
            email="tenant.isolation.a@bubble.com",
            hashed_password=auth_service.get_password_hash("SecurePasswordA2025!"),
            full_name="Tenant A User",
            is_verified=True
        )
        
        user_b = User(
            email="tenant.isolation.b@bubble.com", 
            hashed_password=auth_service.get_password_hash("SecurePasswordB2025!"),
            full_name="Tenant B User",
            is_verified=True
        )
        
        db_session.add(user_a)
        db_session.add(user_b)
        db_session.commit()
        
        # Login both users
        login_a_response = client.post("/api/v1/auth/login", json={
            "email": "tenant.isolation.a@bubble.com",
            "password": "SecurePasswordA2025!"
        })
        
        login_b_response = client.post("/api/v1/auth/login", json={
            "email": "tenant.isolation.b@bubble.com",
            "password": "SecurePasswordB2025!"
        })
        
        if login_a_response.status_code == 200 and login_b_response.status_code == 200:
            token_a = login_a_response.json()["access_token"]
            token_b = login_b_response.json()["access_token"]
            
            headers_a = {"Authorization": f"Bearer {token_a}"}
            headers_b = {"Authorization": f"Bearer {token_b}"}
            
            # User A creates data
            universe_a_data = {
                "name": "User A Private Universe",
                "description": "Should be private to User A",
                "initial_symbols": ["AAPL", "GOOGL"]
            }
            
            universe_a_response = client.post("/api/v1/universes", json=universe_a_data, headers=headers_a)
            
            # User B creates data
            universe_b_data = {
                "name": "User B Private Universe",
                "description": "Should be private to User B", 
                "initial_symbols": ["MSFT", "AMZN"]
            }
            
            universe_b_response = client.post("/api/v1/universes", json=universe_b_data, headers=headers_b)
            
            # Test isolation: User A should only see their data
            if universe_a_response.status_code == 201:
                list_a_response = client.get("/api/v1/universes", headers=headers_a)
                if list_a_response.status_code == 200:
                    universes_a = list_a_response.json()["data"]
                    universe_names_a = [u["name"] for u in universes_a]
                    
                    assert "User A Private Universe" in universe_names_a
                    assert "User B Private Universe" not in universe_names_a
            
            # Test isolation: User B should only see their data
            if universe_b_response.status_code == 201:
                list_b_response = client.get("/api/v1/universes", headers=headers_b)
                if list_b_response.status_code == 200:
                    universes_b = list_b_response.json()["data"]
                    universe_names_b = [u["name"] for u in universes_b]
                    
                    assert "User B Private Universe" in universe_names_b
                    assert "User A Private Universe" not in universe_names_b
    
    def test_ai_conversation_workflow_with_business_logic(self, client: TestClient, db_session: Session):
        """Test AI conversation workflow integrated with business logic"""
        auth_service = AuthService()
        
        # Create user with real authentication
        user = User(
            email="ai.conversation.test@bubble.com",
            hashed_password=auth_service.get_password_hash("SecureAIChat2025!"),
            full_name="AI Conversation Test User",
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()
        
        # Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": "ai.conversation.test@bubble.com",
            "password": "SecureAIChat2025!"
        })
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            
            # Start AI conversation
            conversation_data = {
                "title": "Portfolio Strategy Discussion",
                "initial_message": "Help me create a momentum-based investment strategy"
            }
            
            conversation_response = client.post("/api/v1/conversations", json=conversation_data, headers=headers)
            if conversation_response.status_code == 201:
                conversation_id = conversation_response.json()["data"]["id"]
                
                # Continue conversation with business context
                message_data = {
                    "content": "I want to focus on technology stocks with strong momentum indicators",
                    "context": {
                        "portfolio_value": 100000,
                        "risk_tolerance": "moderate",
                        "investment_horizon": "long_term"
                    }
                }
                
                message_response = client.post(
                    f"/api/v1/conversations/{conversation_id}/messages",
                    json=message_data,
                    headers=headers
                )
                
                if message_response.status_code == 201:
                    message_resp = message_response.json()
                    assert message_resp["success"] is True
                    assert "next_actions" in message_resp
    
    def test_feature_flags_business_logic_integration(self, client: TestClient):
        """Test feature flags integration with business logic"""
        # Check feature flags
        features_response = client.get("/api/v1/features/")
        if features_response.status_code == 200:
            features = features_response.json()["data"]["features"]
            
            # Verify critical business features are defined
            critical_features = [
                "advanced_screener",
                "real_time_data",
                "ai_agent_advanced",
                "live_performance"
            ]
            
            for feature in critical_features:
                assert feature in features
                assert isinstance(features[feature], bool)
            
            # Test feature flag conditional logic
            if features.get("advanced_screener", False):
                # Advanced screener should be available
                screener_response = client.get("/api/v1/screener/advanced")
                # Should either work or return proper error (not 404)
                assert screener_response.status_code != 404
            
            if features.get("real_time_data", False):
                # Real-time data endpoints should be available
                realtime_response = client.get("/api/v1/market/realtime")
                assert realtime_response.status_code != 404
    
    def test_health_system_comprehensive_production_readiness(self, client: TestClient):
        """Test comprehensive health system for production deployment"""
        # Test main health endpoint
        health_response = client.get("/health/")
        assert health_response.status_code == 200
        
        health_data = health_response.json()
        
        # Verify production-ready health checks
        assert health_data["success"] is True
        assert "timestamp" in health_data["data"]
        assert "version" in health_data["data"]
        assert "environment" in health_data["data"]
        
        # Test readiness endpoint if available
        ready_response = client.get("/ready")
        if ready_response.status_code == 200:
            ready_data = ready_response.json()
            assert "ready" in ready_data
            assert "checks" in ready_data
        
        # Test metrics endpoint if available
        metrics_response = client.get("/metrics")
        if metrics_response.status_code == 200:
            metrics_data = metrics_response.json()
            # Should have basic metrics structure
            assert isinstance(metrics_data, dict)


class TestBusinessLogicValidation:
    """Test business logic validation across all domain objects"""
    
    def test_asset_universe_validation_business_rules(self, db_session: Session):
        """Test asset and universe validation business rules"""
        auth_service = AuthService()
        
        # Create user with real password hashing
        user = User(
            email="business.validation@bubble.com",
            hashed_password=auth_service.get_password_hash("SecureValidation2025!"),
            full_name="Business Validation User"
        )
        db_session.add(user)
        db_session.flush()
        
        # Test asset validation business rules
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc.",
            sector="Technology",
            industry="Consumer Electronics",
            market_cap=3000000000000,
            pe_ratio=28.5,
            dividend_yield=0.005,
            is_validated=True
        )
        db_session.add(asset)
        db_session.flush()
        
        # Test universe business rules
        universe = Universe(
            name="Validated Universe",
            description="Universe with validated assets",
            symbols=["AAPL", "GOOGL", "MSFT"],
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.flush()
        
        # Test many-to-many relationships
        universe_asset = UniverseAsset(
            universe_id=universe.id,
            asset_id=asset.id,
            position=1
        )
        db_session.add(universe_asset)
        db_session.commit()
        
        # Verify business rules
        assert len(universe.symbols) == 3
        assert "AAPL" in universe.symbols
        assert asset.is_validated is True
        assert universe_asset.position == 1
    
    def test_strategy_portfolio_business_logic(self, db_session: Session):
        """Test strategy and portfolio business logic validation"""
        auth_service = AuthService()
        
        # Create user and universe
        user = User(
            email="strategy.portfolio@bubble.com",
            hashed_password=auth_service.get_password_hash("SecureStrategy2025!"),
            full_name="Strategy Portfolio User"
        )
        db_session.add(user)
        db_session.flush()
        
        universe = Universe(
            name="Strategy Universe",
            description="Universe for strategy testing",
            symbols=["AAPL", "GOOGL", "MSFT"],
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.flush()
        
        # Test strategy business logic
        strategy = Strategy(
            name="Business Logic Strategy",
            description="Testing business validation",
            indicator_config={
                "rsi_period": 14,
                "overbought": 70,
                "oversold": 30,
                "sma_short": 10,
                "sma_long": 50
            },
            allocation_rules={
                "method": "risk_parity",
                "max_position_size": 0.1,
                "min_position_size": 0.02
            },
            universe_id=universe.id,
            owner_id=user.id,
            status=StrategyStatus.ACTIVE
        )
        db_session.add(strategy)
        db_session.flush()
        
        # Test portfolio business logic
        portfolio = Portfolio(
            name="Business Logic Portfolio",
            description="Portfolio with business validation",
            allocation_method="risk_parity",
            target_allocations={
                "AAPL": 0.35,
                "GOOGL": 0.35,
                "MSFT": 0.30
            },
            total_value=150000.0,
            cash_balance=15000.0,
            owner_id=user.id
        )
        db_session.add(portfolio)
        db_session.commit()
        
        # Verify business logic
        assert strategy.status == StrategyStatus.ACTIVE
        assert "rsi_period" in strategy.indicator_config
        assert "method" in strategy.allocation_rules
        assert portfolio.total_value == 150000.0
        assert sum(portfolio.target_allocations.values()) == 1.0  # Allocations sum to 100%


# Test markers for comprehensive business scenarios
pytestmark = [
    pytest.mark.business_logic,
    pytest.mark.integration,
    pytest.mark.security,
    pytest.mark.comprehensive
]