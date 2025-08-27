"""
Test suite for UniverseSnapshot model and temporal universe functionality.
Part B: Database Schema Changes - Sprint 2.5
"""
import pytest
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User
from app.models.universe import Universe
from app.models.universe_snapshot import UniverseSnapshot
from app.core.database import get_db


class TestUniverseSnapshotModel:
    """Test UniverseSnapshot model functionality"""
    
    def test_create_universe_snapshot_basic(self, db_session: Session):
        """Test basic UniverseSnapshot creation"""
        # Create test user
        user = User(
            email="snapshot@test.com",
            hashed_password="hashed123",
            full_name="Snapshot Test User"
        )
        db_session.add(user)
        db_session.commit()
        
        # Create test universe
        universe = Universe(
            name="Test Universe",
            description="Universe for snapshot testing",
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.commit()
        
        # Test asset data
        test_assets = [
            {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.30, 'sector': 'Technology'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.25, 'sector': 'Technology'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc', 'weight': 0.25, 'sector': 'Technology'},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc', 'weight': 0.20, 'sector': 'Technology'}
        ]
        
        # Create snapshot using factory method
        snapshot = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            current_assets=test_assets,
            screening_criteria={'market_cap': '>100B', 'sector': 'Technology'}
        )
        
        db_session.add(snapshot)
        db_session.commit()
        
        # Assertions
        assert snapshot.universe_id == universe.id
        assert snapshot.snapshot_date == date(2024, 6, 30)
        assert len(snapshot.assets) == 4
        assert snapshot.turnover_rate == 0.0  # First snapshot, no previous
        assert snapshot.assets_added == []
        assert snapshot.assets_removed == []
        assert snapshot.validate_assets_structure() is True
    
    def test_universe_snapshot_factory_with_turnover(self, db_session: Session):
        """Test UniverseSnapshot factory method with turnover calculation"""
        # Create test user and universe
        user = User(
            email="turnover@test.com",
            hashed_password="hashed123",
            full_name="Turnover Test User"
        )
        db_session.add(user)
        
        universe = Universe(
            name="Turnover Test Universe",
            description="Universe for turnover testing",
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.commit()
        
        # Create first snapshot
        first_assets = [
            {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.30, 'sector': 'Technology'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.25, 'sector': 'Technology'},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc', 'weight': 0.25, 'sector': 'Technology'},
            {'symbol': 'AMZN', 'name': 'Amazon.com Inc', 'weight': 0.20, 'sector': 'Technology'}
        ]
        
        first_snapshot = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            current_assets=first_assets
        )
        db_session.add(first_snapshot)
        db_session.commit()
        
        # Create second snapshot with different composition
        second_assets = [
            {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.28, 'sector': 'Technology'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.27, 'sector': 'Technology'},
            {'symbol': 'NVDA', 'name': 'NVIDIA Corp', 'weight': 0.25, 'sector': 'Technology'},
            {'symbol': 'TSLA', 'name': 'Tesla Inc', 'weight': 0.20, 'sector': 'Technology'}
        ]
        
        second_snapshot = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 9, 30),
            current_assets=second_assets,
            previous_snapshot=first_snapshot
        )
        db_session.add(second_snapshot)
        db_session.commit()
        
        # Verify turnover calculation
        assert second_snapshot.turnover_rate > 0.0
        assert len(second_snapshot.assets_added) == 2  # NVDA, TSLA
        assert len(second_snapshot.assets_removed) == 2  # GOOGL, AMZN
        assert 'NVDA' in second_snapshot.assets_added
        assert 'TSLA' in second_snapshot.assets_added
        assert 'GOOGL' in second_snapshot.assets_removed
        assert 'AMZN' in second_snapshot.assets_removed
    
    def test_universe_snapshot_methods(self, db_session: Session):
        """Test UniverseSnapshot utility methods"""
        # Create test data
        user = User(
            email="methods@test.com",
            hashed_password="hashed123",
            full_name="Methods Test User"
        )
        db_session.add(user)
        
        universe = Universe(
            name="Methods Test Universe",
            description="Universe for methods testing",
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.commit()
        
        test_assets = [
            {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.30, 'sector': 'Technology'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.25, 'sector': 'Technology'},
            {'symbol': 'JPM', 'name': 'JPMorgan Chase', 'weight': 0.25, 'sector': 'Financial'},
            {'symbol': 'JNJ', 'name': 'Johnson & Johnson', 'weight': 0.20, 'sector': 'Healthcare'}
        ]
        
        snapshot = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            current_assets=test_assets
        )
        db_session.add(snapshot)
        db_session.commit()
        
        # Test get_asset_symbols
        symbols = snapshot.get_asset_symbols()
        assert len(symbols) == 4
        assert 'AAPL' in symbols
        assert 'MSFT' in symbols
        assert 'JPM' in symbols
        assert 'JNJ' in symbols
        
        # Test get_asset_count
        assert snapshot.get_asset_count() == 4
        
        # Test get_assets_by_sector
        sectors = snapshot.get_assets_by_sector()
        assert 'Technology' in sectors
        assert 'Financial' in sectors
        assert 'Healthcare' in sectors
        assert len(sectors['Technology']) == 2
        assert len(sectors['Financial']) == 1
        assert len(sectors['Healthcare']) == 1
        
        # Test calculate_portfolio_weight
        assert snapshot.calculate_portfolio_weight('AAPL') == 0.30
        assert snapshot.calculate_portfolio_weight('MSFT') == 0.25
        assert snapshot.calculate_portfolio_weight('INVALID') is None
        
        # Test get_turnover_analysis
        analysis = snapshot.get_turnover_analysis()
        assert 'snapshot_date' in analysis
        assert 'turnover_rate' in analysis
        assert 'assets_added' in analysis
        assert 'assets_removed' in analysis
        assert 'net_change' in analysis
        assert 'total_assets' in analysis
        assert analysis['total_assets'] == 4
    
    def test_universe_snapshot_to_dict(self, db_session: Session):
        """Test UniverseSnapshot to_dict method"""
        # Create test data
        user = User(
            email="todict@test.com",
            hashed_password="hashed123",
            full_name="ToDict Test User"
        )
        db_session.add(user)
        
        universe = Universe(
            name="ToDict Test Universe",
            description="Universe for to_dict testing",
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.commit()
        
        test_assets = [
            {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.50, 'sector': 'Technology'},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.50, 'sector': 'Technology'}
        ]
        
        snapshot = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            current_assets=test_assets,
            screening_criteria={'test': 'criteria'}
        )
        db_session.add(snapshot)
        db_session.commit()
        
        # Test to_dict
        data = snapshot.to_dict()
        
        # Verify structure
        assert 'universe_id' in data
        assert 'snapshot_date' in data
        assert 'assets' in data
        assert 'screening_criteria' in data
        assert 'turnover_rate' in data
        assert 'assets_added' in data
        assert 'assets_removed' in data
        assert 'performance_metrics' in data
        assert 'asset_count' in data
        assert 'asset_symbols' in data
        assert 'turnover_analysis' in data
        
        # Verify values
        assert data['universe_id'] == universe.id
        assert data['asset_count'] == 2
        assert len(data['asset_symbols']) == 2
        assert 'AAPL' in data['asset_symbols']
        assert 'MSFT' in data['asset_symbols']
    
    def test_universe_snapshot_validation(self, db_session: Session):
        """Test UniverseSnapshot asset structure validation"""
        # Create test data
        user = User(
            email="validation@test.com",
            hashed_password="hashed123",
            full_name="Validation Test User"
        )
        db_session.add(user)
        
        universe = Universe(
            name="Validation Test Universe",
            description="Universe for validation testing",
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.commit()
        
        # Test valid structure
        valid_assets = [
            {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.50},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.50}
        ]
        
        valid_snapshot = UniverseSnapshot(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            assets=valid_assets
        )
        assert valid_snapshot.validate_assets_structure() is True
        
        # Test invalid structure - missing required fields
        invalid_assets = [
            {'symbol': 'AAPL'},  # Missing 'name'
            {'name': 'Microsoft Corp'}  # Missing 'symbol'
        ]
        
        invalid_snapshot = UniverseSnapshot(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            assets=invalid_assets
        )
        assert invalid_snapshot.validate_assets_structure() is False
        
        # Test invalid structure - not a list
        invalid_snapshot_2 = UniverseSnapshot(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            assets={'not': 'a_list'}
        )
        assert invalid_snapshot_2.validate_assets_structure() is False
        
        # Test empty assets
        empty_snapshot = UniverseSnapshot(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            assets=[]
        )
        assert empty_snapshot.validate_assets_structure() is False


class TestUniverseTemporalMethods:
    """Test Universe model temporal methods"""
    
    def test_universe_get_composition_at_date(self, db_session: Session):
        """Test Universe.get_composition_at_date method"""
        # Create test data
        user = User(
            email="composition@test.com",
            hashed_password="hashed123",
            full_name="Composition Test User"
        )
        db_session.add(user)
        
        universe = Universe(
            name="Composition Test Universe",
            description="Universe for composition testing",
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.commit()
        
        # Create snapshots with different dates
        june_assets = [
            {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.50},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.50}
        ]
        
        sept_assets = [
            {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.33},
            {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.33},
            {'symbol': 'GOOGL', 'name': 'Alphabet Inc', 'weight': 0.34}
        ]
        
        june_snapshot = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            current_assets=june_assets
        )
        
        sept_snapshot = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 9, 30),
            current_assets=sept_assets
        )
        
        db_session.add(june_snapshot)
        db_session.add(sept_snapshot)
        db_session.commit()
        
        # Test getting composition at different dates
        composition_july = universe.get_composition_at_date(date(2024, 7, 15))
        composition_october = universe.get_composition_at_date(date(2024, 10, 15))
        composition_early = universe.get_composition_at_date(date(2024, 1, 1))
        
        # July should get June snapshot (most recent at or before)
        assert composition_july is not None
        assert len(composition_july) == 2
        
        # October should get September snapshot
        assert composition_october is not None
        assert len(composition_october) == 3
        
        # Early date should get None (no snapshots before)
        assert composition_early is None
    
    def test_universe_get_evolution_timeline(self, db_session: Session):
        """Test Universe.get_evolution_timeline method"""
        # Create test data
        user = User(
            email="timeline@test.com",
            hashed_password="hashed123",
            full_name="Timeline Test User"
        )
        db_session.add(user)
        
        universe = Universe(
            name="Timeline Test Universe",
            description="Universe for timeline testing",
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.commit()
        
        # Create multiple snapshots
        dates_and_assets = [
            (date(2024, 3, 31), [{'symbol': 'AAPL', 'name': 'Apple Inc'}]),
            (date(2024, 6, 30), [{'symbol': 'AAPL', 'name': 'Apple Inc'}, {'symbol': 'MSFT', 'name': 'Microsoft Corp'}]),
            (date(2024, 9, 30), [{'symbol': 'MSFT', 'name': 'Microsoft Corp'}, {'symbol': 'GOOGL', 'name': 'Alphabet Inc'}])
        ]
        
        for snapshot_date, assets in dates_and_assets:
            snapshot = UniverseSnapshot.create_from_universe_state(
                universe_id=universe.id,
                snapshot_date=snapshot_date,
                current_assets=assets
            )
            db_session.add(snapshot)
        
        db_session.commit()
        
        # Test timeline retrieval
        full_timeline = universe.get_evolution_timeline(date(2024, 1, 1), date(2024, 12, 31))
        partial_timeline = universe.get_evolution_timeline(date(2024, 6, 1), date(2024, 9, 30))
        empty_timeline = universe.get_evolution_timeline(date(2025, 1, 1), date(2025, 12, 31))
        
        # Verify results
        assert len(full_timeline) == 3
        assert len(partial_timeline) == 2
        assert len(empty_timeline) == 0
        
        # Verify order (should be chronological)
        assert full_timeline[0].snapshot_date == date(2024, 3, 31)
        assert full_timeline[1].snapshot_date == date(2024, 6, 30)
        assert full_timeline[2].snapshot_date == date(2024, 9, 30)
    
    def test_universe_snapshot_count_methods(self, db_session: Session):
        """Test Universe snapshot counting and metadata methods"""
        # Create test data
        user = User(
            email="count@test.com",
            hashed_password="hashed123",
            full_name="Count Test User"
        )
        db_session.add(user)
        
        universe = Universe(
            name="Count Test Universe",
            description="Universe for count testing",
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.commit()
        
        # Initially no snapshots
        assert universe.get_snapshot_count() == 0
        assert universe.get_latest_snapshot() is None
        assert universe.has_snapshots_in_range(date(2024, 1, 1), date(2024, 12, 31)) is False
        
        # Add snapshots
        snapshot1 = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            current_assets=[{'symbol': 'AAPL', 'name': 'Apple Inc'}]
        )
        
        snapshot2 = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 9, 30),
            current_assets=[{'symbol': 'MSFT', 'name': 'Microsoft Corp'}]
        )
        
        db_session.add(snapshot1)
        db_session.add(snapshot2)
        db_session.commit()
        
        # Test after adding snapshots
        assert universe.get_snapshot_count() == 2
        
        latest = universe.get_latest_snapshot()
        assert latest is not None
        assert latest.snapshot_date == date(2024, 9, 30)
        
        assert universe.has_snapshots_in_range(date(2024, 1, 1), date(2024, 12, 31)) is True
        assert universe.has_snapshots_in_range(date(2025, 1, 1), date(2025, 12, 31)) is False
    
    def test_universe_to_dict_with_temporal_info(self, db_session: Session):
        """Test Universe.to_dict includes temporal information"""
        # Create test data
        user = User(
            email="temporal@test.com",
            hashed_password="hashed123",
            full_name="Temporal Test User"
        )
        db_session.add(user)
        
        universe = Universe(
            name="Temporal Test Universe",
            description="Universe for temporal to_dict testing",
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.commit()
        
        # Add snapshot
        snapshot = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            current_assets=[{'symbol': 'AAPL', 'name': 'Apple Inc'}]
        )
        db_session.add(snapshot)
        db_session.commit()
        
        # Test to_dict includes temporal information
        data = universe.to_dict()
        
        assert 'snapshot_count' in data
        assert 'has_snapshots' in data
        assert 'latest_snapshot_date' in data
        
        assert data['snapshot_count'] == 1
        assert data['has_snapshots'] is True
        assert data['latest_snapshot_date'] == '2024-06-30'


@pytest.mark.integration
class TestUniverseSnapshotIntegration:
    """Integration tests for UniverseSnapshot with database constraints"""
    
    def test_unique_constraint_universe_snapshot_date(self, db_session: Session):
        """Test unique constraint on (universe_id, snapshot_date)"""
        # Create test data
        user = User(
            email="unique@test.com",
            hashed_password="hashed123",
            full_name="Unique Test User"
        )
        db_session.add(user)
        
        universe = Universe(
            name="Unique Test Universe",
            description="Universe for unique constraint testing",
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.commit()
        
        # Create first snapshot
        snapshot1 = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            current_assets=[{'symbol': 'AAPL', 'name': 'Apple Inc'}]
        )
        db_session.add(snapshot1)
        db_session.commit()
        
        # Try to create duplicate snapshot (should fail)
        snapshot2 = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),  # Same date
            current_assets=[{'symbol': 'MSFT', 'name': 'Microsoft Corp'}]
        )
        db_session.add(snapshot2)
        
        # This should raise an integrity error due to unique constraint
        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            db_session.commit()
    
    def test_foreign_key_cascade_deletion(self, db_session: Session):
        """Test cascade deletion when universe is deleted"""
        # Create test data
        user = User(
            email="cascade@test.com",
            hashed_password="hashed123",
            full_name="Cascade Test User"
        )
        db_session.add(user)
        
        universe = Universe(
            name="Cascade Test Universe",
            description="Universe for cascade testing",
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.commit()
        
        # Create snapshot
        snapshot = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            current_assets=[{'symbol': 'AAPL', 'name': 'Apple Inc'}]
        )
        db_session.add(snapshot)
        db_session.commit()
        
        snapshot_id = snapshot.id
        
        # Verify snapshot exists
        found_snapshot = db_session.query(UniverseSnapshot).filter(
            UniverseSnapshot.id == snapshot_id
        ).first()
        assert found_snapshot is not None
        
        # Delete universe
        db_session.delete(universe)
        db_session.commit()
        
        # Verify snapshot was cascade deleted
        found_snapshot_after = db_session.query(UniverseSnapshot).filter(
            UniverseSnapshot.id == snapshot_id
        ).first()
        assert found_snapshot_after is None