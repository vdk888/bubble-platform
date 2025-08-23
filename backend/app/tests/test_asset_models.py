"""
Tests for Phase 2 Asset models and relationships.

This module validates:
- Asset entity model functionality
- UniverseAsset junction table relationships
- Universe model updated functionality with Asset relationships
- Database schema integrity and constraints
- Model validation and business logic
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.universe import Universe
from app.models.asset import Asset, UniverseAsset


class TestAssetModel:
    """Test suite for Asset entity model."""
    
    def test_create_basic_asset(self, db_session: Session):
        """Test creating a basic asset with minimal required fields."""
        asset = Asset(
            symbol="AAPL",
            name="Apple Inc."
        )
        db_session.add(asset)
        db_session.commit()
        db_session.refresh(asset)
        
        assert asset.id is not None
        assert asset.symbol == "AAPL"
        assert asset.name == "Apple Inc."
        assert asset.is_validated is False  # Default value
        assert asset.is_active is True  # From BaseModel
        assert asset.created_at is not None
        assert asset.updated_at is not None
        assert asset.asset_metadata == {}  # Default empty dict
    
    def test_create_comprehensive_asset(self, db_session: Session):
        """Test creating an asset with all fields populated."""
        asset = Asset(
            symbol="GOOGL",
            name="Alphabet Inc. Class A",
            sector="Technology", 
            industry="Internet Content & Information",
            market_cap=1500000000000,  # $1.5T
            pe_ratio=Decimal("25.50"),
            dividend_yield=Decimal("0.0000"),  # No dividend
            is_validated=True,
            last_validated_at=datetime.now(timezone.utc),
            validation_source="yahoo_finance",
            validation_errors=None,
            asset_metadata={"exchange": "NASDAQ", "currency": "USD"}
        )
        db_session.add(asset)
        db_session.commit()
        db_session.refresh(asset)
        
        assert asset.symbol == "GOOGL"
        assert asset.name == "Alphabet Inc. Class A"
        assert asset.sector == "Technology"
        assert asset.industry == "Internet Content & Information"
        assert asset.market_cap == 1500000000000
        assert asset.pe_ratio == Decimal("25.50")
        assert asset.dividend_yield == Decimal("0.0000")
        assert asset.is_validated is True
        assert asset.last_validated_at is not None
        assert asset.validation_source == "yahoo_finance"
        assert asset.asset_metadata["exchange"] == "NASDAQ"
        assert asset.asset_metadata["currency"] == "USD"
    
    def test_asset_symbol_unique_constraint(self, db_session: Session):
        """Test that asset symbols must be unique."""
        asset1 = Asset(symbol="AAPL", name="Apple Inc.")
        asset2 = Asset(symbol="AAPL", name="Apple Inc. Duplicate")
        
        db_session.add(asset1)
        db_session.commit()
        
        # Adding second asset with same symbol should fail
        db_session.add(asset2)
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_asset_to_dict(self, db_session: Session):
        """Test Asset model to_dict() method with all fields."""
        now = datetime.now(timezone.utc)
        asset = Asset(
            symbol="TSLA",
            name="Tesla, Inc.",
            sector="Consumer Cyclical",
            industry="Auto Manufacturers",
            market_cap=800000000000,
            pe_ratio=Decimal("45.75"),
            dividend_yield=Decimal("0.0000"),
            is_validated=True,
            last_validated_at=now,
            validation_source="alpha_vantage",
            asset_metadata={"beta": 2.1, "52_week_high": 415.0}
        )
        db_session.add(asset)
        db_session.commit()
        db_session.refresh(asset)
        
        asset_dict = asset.to_dict()
        
        # Check all expected fields are present
        assert asset_dict["symbol"] == "TSLA"
        assert asset_dict["name"] == "Tesla, Inc."
        assert asset_dict["sector"] == "Consumer Cyclical"
        assert asset_dict["industry"] == "Auto Manufacturers"
        assert asset_dict["market_cap"] == 800000000000.0
        assert asset_dict["pe_ratio"] == 45.75
        assert asset_dict["dividend_yield"] == 0.0
        assert asset_dict["is_validated"] is True
        assert asset_dict["last_validated_at"] is not None
        # Just check that it's a valid timestamp format, not exact match due to timezone differences
        assert "2025-08-23T" in asset_dict["last_validated_at"]
        assert asset_dict["validation_source"] == "alpha_vantage"
        assert asset_dict["asset_metadata"]["beta"] == 2.1
        assert asset_dict["asset_metadata"]["52_week_high"] == 415.0
        assert "id" in asset_dict
        assert "created_at" in asset_dict
        assert "updated_at" in asset_dict
    
    def test_asset_is_stale_validation(self, db_session: Session):
        """Test Asset.is_stale_validation() method logic."""
        # Asset with no validation
        asset_unvalidated = Asset(symbol="NVDA", name="NVIDIA Corporation")
        assert asset_unvalidated.is_stale_validation() is True
        
        # Asset with recent validation
        asset_fresh = Asset(
            symbol="AMD",
            name="Advanced Micro Devices",
            is_validated=True,
            last_validated_at=datetime.now(timezone.utc)
        )
        assert asset_fresh.is_stale_validation(max_age_hours=24) is False
        
        # Asset with old validation (simulated)
        old_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
        asset_stale = Asset(
            symbol="INTC", 
            name="Intel Corporation",
            is_validated=True,
            last_validated_at=old_time
        )
        assert asset_stale.is_stale_validation(max_age_hours=24) is True
    
    def test_asset_update_validation_status(self, db_session: Session):
        """Test Asset.update_validation_status() method."""
        asset = Asset(symbol="META", name="Meta Platforms, Inc.")
        db_session.add(asset)
        db_session.commit()
        db_session.refresh(asset)
        
        # Store initial validation time (None)
        initial_validation_time = asset.last_validated_at
        
        # Update with success
        asset.update_validation_status(
            is_valid=True,
            source="yahoo_finance",
            error_message=None,
            metadata_updates={"exchange": "NASDAQ", "volume": 25000000}
        )
        
        assert asset.is_validated is True
        assert asset.validation_source == "yahoo_finance"
        assert asset.validation_errors is None
        assert asset.last_validated_at is not None  # Should now be set
        assert asset.last_validated_at != initial_validation_time  # Should be different from initial None
        assert asset.asset_metadata["exchange"] == "NASDAQ"
        assert asset.asset_metadata["volume"] == 25000000
        
        # Update with error
        asset.update_validation_status(
            is_valid=False,
            source="alpha_vantage",
            error_message="Symbol not found",
            metadata_updates={"error_code": 404}
        )
        
        assert asset.is_validated is False
        assert asset.validation_source == "alpha_vantage"
        assert asset.validation_errors == "Symbol not found"
        assert asset.asset_metadata["error_code"] == 404
        # Previous metadata should be preserved
        assert asset.asset_metadata["exchange"] == "NASDAQ"


class TestUniverseAssetModel:
    """Test suite for UniverseAsset junction table model."""
    
    def test_create_universe_asset_relationship(self, db_session: Session):
        """Test creating a basic universe-asset relationship."""
        # Create dependencies
        user = User(email="test@example.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        universe = Universe(name="Tech Universe", owner_id=user.id)
        asset = Asset(symbol="AAPL", name="Apple Inc.")
        
        db_session.add_all([universe, asset])
        db_session.commit()
        db_session.refresh(universe)
        db_session.refresh(asset)
        
        # Create relationship
        universe_asset = UniverseAsset(
            universe_id=universe.id,
            asset_id=asset.id,
            position=1
        )
        db_session.add(universe_asset)
        db_session.commit()
        db_session.refresh(universe_asset)
        
        assert universe_asset.id is not None
        assert universe_asset.universe_id == universe.id
        assert universe_asset.asset_id == asset.id
        assert universe_asset.position == 1
        assert universe_asset.added_at is not None
        assert universe_asset.is_active is True
    
    def test_universe_asset_with_metadata(self, db_session: Session):
        """Test UniverseAsset with all optional fields."""
        # Create dependencies - user first to get ID
        user = User(email="test@example.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        universe = Universe(name="Dividend Universe", owner_id=user.id)
        asset = Asset(symbol="JNJ", name="Johnson & Johnson")
        
        db_session.add_all([universe, asset])
        db_session.commit()
        db_session.refresh(universe)
        db_session.refresh(asset)
        
        # Create relationship with metadata
        universe_asset = UniverseAsset(
            universe_id=universe.id,
            asset_id=asset.id,
            position=5,
            weight=Decimal("0.2500"),  # 25% weight
            notes="Defensive healthcare stock with consistent dividends"
        )
        db_session.add(universe_asset)
        db_session.commit()
        db_session.refresh(universe_asset)
        
        assert universe_asset.position == 5
        assert universe_asset.weight == Decimal("0.2500")
        assert universe_asset.notes == "Defensive healthcare stock with consistent dividends"
    
    def test_universe_asset_relationships(self, db_session: Session):
        """Test that UniverseAsset properly relates to Universe and Asset."""
        # Create dependencies - user first to get ID
        user = User(email="test@example.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        universe = Universe(name="FAANG Universe", owner_id=user.id)
        asset = Asset(symbol="NFLX", name="Netflix, Inc.")
        
        db_session.add_all([universe, asset])
        db_session.commit()
        db_session.refresh(universe)
        db_session.refresh(asset)
        
        # Create relationship
        universe_asset = UniverseAsset(
            universe_id=universe.id,
            asset_id=asset.id
        )
        db_session.add(universe_asset)
        db_session.commit()
        db_session.refresh(universe_asset)
        
        # Test relationships work
        assert universe_asset.universe.name == "FAANG Universe"
        assert universe_asset.asset.symbol == "NFLX"
        assert universe_asset.asset.name == "Netflix, Inc."
    
    def test_universe_asset_to_dict(self, db_session: Session):
        """Test UniverseAsset to_dict() method."""
        # Create dependencies - user first to get ID
        user = User(email="test@example.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        universe = Universe(name="Test Universe", owner_id=user.id)
        asset = Asset(symbol="AMZN", name="Amazon.com, Inc.")
        
        db_session.add_all([universe, asset])
        db_session.commit()
        db_session.refresh(universe)
        db_session.refresh(asset)
        
        universe_asset = UniverseAsset(
            universe_id=universe.id,
            asset_id=asset.id,
            position=3,
            weight=Decimal("0.1750"),
            notes="E-commerce leader"
        )
        db_session.add(universe_asset)
        db_session.commit()
        db_session.refresh(universe_asset)
        
        ua_dict = universe_asset.to_dict()
        
        assert ua_dict["universe_id"] == universe.id
        assert ua_dict["asset_id"] == asset.id
        assert ua_dict["position"] == 3
        assert ua_dict["weight"] == 0.1750
        assert ua_dict["notes"] == "E-commerce leader"
        assert ua_dict["added_at"] is not None
        assert "id" in ua_dict
        assert "created_at" in ua_dict


class TestUniverseModelUpdated:
    """Test suite for updated Universe model with Asset relationships."""
    
    def test_universe_get_symbols_from_relationships(self, db_session: Session):
        """Test Universe.get_symbols() using new Asset relationships."""
        # Create dependencies - user first to get ID
        user = User(email="test@example.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        universe = Universe(name="Tech Giants", owner_id=user.id)
        
        assets = [
            Asset(symbol="AAPL", name="Apple Inc."),
            Asset(symbol="GOOGL", name="Alphabet Inc."),
            Asset(symbol="MSFT", name="Microsoft Corporation")
        ]
        
        db_session.add_all([universe] + assets)
        db_session.commit()
        
        # Add assets to universe via relationships
        for i, asset in enumerate(assets):
            universe_asset = UniverseAsset(
                universe_id=universe.id,
                asset_id=asset.id,
                position=i + 1
            )
            db_session.add(universe_asset)
        
        db_session.commit()
        db_session.refresh(universe)
        
        # Test get_symbols() returns symbols from relationships
        symbols = universe.get_symbols()
        assert len(symbols) == 3
        assert "AAPL" in symbols
        assert "GOOGL" in symbols
        assert "MSFT" in symbols
    
    def test_universe_get_symbols_legacy_fallback(self, db_session: Session):
        """Test Universe.get_symbols() falls back to legacy JSON symbols."""
        # Create user first to get ID
        user = User(email="test@example.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Create universe with legacy JSON symbols (no asset relationships)
        universe = Universe(
            name="Legacy Universe",
            symbols=["TSLA", "NFLX", "NVDA"],  # Legacy JSON field
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.commit()
        db_session.refresh(universe)
        
        # Should fall back to legacy symbols since no asset relationships exist
        symbols = universe.get_symbols()
        assert symbols == ["TSLA", "NFLX", "NVDA"]
    
    def test_universe_get_assets_with_metadata(self, db_session: Session):
        """Test Universe.get_assets() returns full asset data with relationship metadata."""
        # Create dependencies - user first to get ID
        user = User(email="test@example.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        universe = Universe(name="Dividend Stocks", owner_id=user.id)
        
        asset = Asset(
            symbol="KO",
            name="The Coca-Cola Company",
            sector="Consumer Defensive",
            dividend_yield=Decimal("0.0320"),
            is_validated=True,
            asset_metadata={"dividend_aristocrat": True}
        )
        
        db_session.add_all([universe, asset])
        db_session.commit()
        db_session.refresh(universe)
        db_session.refresh(asset)
        
        # Add asset to universe with relationship metadata
        universe_asset = UniverseAsset(
            universe_id=universe.id,
            asset_id=asset.id,
            position=1,
            weight=Decimal("0.3000"),
            notes="Stable dividend payer"
        )
        db_session.add(universe_asset)
        db_session.commit()
        db_session.refresh(universe)
        
        # Test get_assets() returns enriched data
        assets = universe.get_assets()
        assert len(assets) == 1
        
        asset_data = assets[0]
        # Asset data
        assert asset_data["symbol"] == "KO"
        assert asset_data["name"] == "The Coca-Cola Company"
        assert asset_data["sector"] == "Consumer Defensive"
        assert asset_data["dividend_yield"] == 0.032
        assert asset_data["is_validated"] is True
        assert asset_data["asset_metadata"]["dividend_aristocrat"] is True
        
        # Relationship metadata
        assert asset_data["universe_position"] == 1
        assert asset_data["universe_weight"] == 0.3000
        assert asset_data["universe_notes"] == "Stable dividend payer"
        assert asset_data["added_to_universe_at"] is not None
    
    def test_universe_get_asset_count(self, db_session: Session):
        """Test Universe.get_asset_count() method."""
        # Create user first to get ID
        user = User(email="test@example.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        universe = Universe(name="Small Universe", owner_id=user.id)
        
        db_session.add(universe)
        db_session.commit()
        db_session.refresh(universe)
        
        # Initially empty
        assert universe.get_asset_count() == 0
        
        # Add some assets
        assets = [
            Asset(symbol="AAPL", name="Apple Inc."),
            Asset(symbol="GOOGL", name="Alphabet Inc.")
        ]
        db_session.add_all(assets)
        db_session.commit()
        
        for asset in assets:
            universe_asset = UniverseAsset(
                universe_id=universe.id,
                asset_id=asset.id
            )
            db_session.add(universe_asset)
        
        db_session.commit()
        db_session.refresh(universe)
        
        assert universe.get_asset_count() == 2
    
    def test_universe_calculate_turnover_rate(self, db_session: Session):
        """Test Universe.calculate_turnover_rate() method."""
        # Create universe with existing assets - user first to get ID
        user = User(email="test@example.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        universe = Universe(name="Turnover Test", owner_id=user.id)
        
        initial_assets = [
            Asset(symbol="AAPL", name="Apple Inc."),
            Asset(symbol="GOOGL", name="Alphabet Inc."),
            Asset(symbol="MSFT", name="Microsoft Corporation")
        ]
        
        db_session.add_all([universe] + initial_assets)
        db_session.commit()
        db_session.refresh(universe)
        
        # Add initial assets to universe
        for asset in initial_assets:
            universe_asset = UniverseAsset(
                universe_id=universe.id,
                asset_id=asset.id
            )
            db_session.add(universe_asset)
        
        db_session.commit()
        db_session.refresh(universe)
        
        # Test turnover calculation with partial overlap
        # Current: [AAPL, GOOGL, MSFT]
        # New: [AAPL, TSLA, NFLX] 
        # Overlap: AAPL (1), Different: GOOGL, MSFT, TSLA, NFLX (4)
        # Turnover = 4 / 5 = 0.8
        
        new_asset_ids = [initial_assets[0].id, "new_asset_1", "new_asset_2"]
        turnover = universe.calculate_turnover_rate(new_asset_ids)
        
        # Should be 4 different assets out of 5 total unique assets
        expected_turnover = 4.0 / 5.0  # 0.8
        assert abs(turnover - expected_turnover) < 0.001
    
    def test_universe_to_dict_enhanced(self, db_session: Session):
        """Test Universe.to_dict() includes asset count and symbols."""
        # Create user first to get ID
        user = User(email="test@example.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        universe = Universe(
            name="Enhanced Universe",
            description="Test universe with assets",
            owner_id=user.id
        )
        
        asset = Asset(symbol="V", name="Visa Inc.")
        
        db_session.add_all([universe, asset])
        db_session.commit()
        db_session.refresh(universe)
        db_session.refresh(asset)
        
        # Add asset to universe
        universe_asset = UniverseAsset(
            universe_id=universe.id,
            asset_id=asset.id
        )
        db_session.add(universe_asset)
        db_session.commit()
        db_session.refresh(universe)
        
        universe_dict = universe.to_dict()
        
        assert universe_dict["name"] == "Enhanced Universe"
        assert universe_dict["description"] == "Test universe with assets"
        assert universe_dict["owner_id"] == user.id
        assert universe_dict["asset_count"] == 1
        assert universe_dict["symbols"] == ["V"]
        assert len(universe_dict["assets"]) == 1
        assert universe_dict["assets"][0]["symbol"] == "V"
        assert universe_dict["assets"][0]["name"] == "Visa Inc."


class TestDatabaseConstraintsAndIndexes:
    """Test database-level constraints and indexes."""
    
    def test_asset_foreign_key_constraints(self, db_session: Session):
        """Test foreign key constraints on UniverseAsset table."""
        # Create valid universe and asset - user first to get ID
        user = User(email="test@example.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        universe = Universe(name="Test Universe", owner_id=user.id)
        asset = Asset(symbol="TEST", name="Test Asset")
        
        db_session.add_all([universe, asset])
        db_session.commit()
        
        # Valid relationship should work
        valid_ua = UniverseAsset(
            universe_id=universe.id,
            asset_id=asset.id
        )
        db_session.add(valid_ua)
        db_session.commit()  # Should succeed
        
        # Invalid universe_id should fail
        invalid_ua = UniverseAsset(
            universe_id="non-existent-id",
            asset_id=asset.id
        )
        db_session.add(invalid_ua)
        with pytest.raises(IntegrityError):
            db_session.commit()
        
        db_session.rollback()
        
        # Invalid asset_id should fail  
        invalid_ua2 = UniverseAsset(
            universe_id=universe.id,
            asset_id="non-existent-id"
        )
        db_session.add(invalid_ua2)
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_cascade_delete_behavior(self, db_session: Session):
        """Test cascade delete behavior when parent entities are deleted."""
        # Create full hierarchy - user first to get ID
        user = User(email="test@example.com", hashed_password="hash123")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        universe = Universe(name="Test Universe", owner_id=user.id)
        asset = Asset(symbol="DEL", name="Delete Test Asset")
        
        db_session.add_all([universe, asset])
        db_session.commit()
        db_session.refresh(universe)
        db_session.refresh(asset)
        
        universe_asset = UniverseAsset(
            universe_id=universe.id,
            asset_id=asset.id
        )
        db_session.add(universe_asset)
        db_session.commit()
        
        # Verify relationship exists
        assert db_session.query(UniverseAsset).filter_by(
            universe_id=universe.id, 
            asset_id=asset.id
        ).first() is not None
        
        # Delete universe - should cascade delete universe_asset
        db_session.delete(universe)
        db_session.commit()
        
        # UniverseAsset should be deleted
        assert db_session.query(UniverseAsset).filter_by(
            universe_id=universe.id
        ).first() is None
        
        # Asset should still exist (no cascade from universe)
        assert db_session.query(Asset).filter_by(id=asset.id).first() is not None