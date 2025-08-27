"""
Test suite for temporal universe services.
Part C: Service Layer Updates - Sprint 2.5
"""
import pytest
from datetime import date, datetime, timezone, timedelta
from sqlalchemy.orm import Session
from unittest.mock import AsyncMock, patch

from app.models.user import User, UserRole, SubscriptionTier
from app.models.universe import Universe
from app.models.universe_snapshot import UniverseSnapshot
from app.models.asset import Asset, UniverseAsset
from app.services.universe_service import UniverseService
from app.services.temporal_universe_service import TemporalUniverseService, ScheduleConfig
from app.services.interfaces.base import ServiceResult


class TestUniverseServiceTemporal:
    """Test temporal methods added to UniverseService"""
    
    @pytest.fixture
    def universe_service(self, db_session: Session):
        """Create UniverseService instance for testing"""
        return UniverseService(db_session)
    
    @pytest.fixture
    def test_universe_with_assets(self, db_session: Session):
        """Create test universe with assets for temporal testing"""
        # Create user
        user = User(
            email="temporal@service.com",
            hashed_password="hashed123",
            full_name="Temporal Service User",
            role=UserRole.USER,
            subscription_tier=SubscriptionTier.FREE
        )
        db_session.add(user)
        db_session.commit()
        
        # Create universe
        universe = Universe(
            name="Temporal Service Universe",
            description="Universe for service testing",
            owner_id=user.id,
            screening_criteria={'market_cap': '>100B'}
        )
        db_session.add(universe)
        
        # Create assets
        assets = [
            Asset(symbol='AAPL', name='Apple Inc', is_validated=True),
            Asset(symbol='MSFT', name='Microsoft Corp', is_validated=True),
            Asset(symbol='GOOGL', name='Alphabet Inc', is_validated=True),
            Asset(symbol='AMZN', name='Amazon.com Inc', is_validated=True)
        ]
        
        for asset in assets:
            db_session.add(asset)
        
        db_session.commit()
        
        # Create universe-asset associations
        for i, asset in enumerate(assets):
            universe_asset = UniverseAsset(
                universe_id=universe.id,
                asset_id=asset.id,
                position=i,
                weight=0.25,
                added_at=datetime.now(timezone.utc)
            )
            db_session.add(universe_asset)
        
        db_session.commit()
        
        return {
            'user': user,
            'universe': universe,
            'assets': assets
        }
    
    @pytest.mark.asyncio
    async def test_create_universe_snapshot(self, universe_service: UniverseService, test_universe_with_assets):
        """Test create_universe_snapshot method"""
        user = test_universe_with_assets['user']
        universe = test_universe_with_assets['universe']
        
        # Test creating snapshot
        result = await universe_service.create_universe_snapshot(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            screening_criteria={'market_cap': '>100B', 'sector': 'Technology'},
            user_id=user.id
        )
        
        assert result.success is True
        assert 'snapshot_id' in result.metadata
        assert result.data['asset_count'] == 4
        assert result.data['turnover_rate'] == 0.0  # First snapshot
        
        # Verify snapshot was created in database
        snapshot_id = result.metadata['snapshot_id']
        snapshot = universe_service.db.query(UniverseSnapshot).filter(
            UniverseSnapshot.id == snapshot_id
        ).first()
        
        assert snapshot is not None
        assert snapshot.universe_id == universe.id
        assert snapshot.snapshot_date == date(2024, 6, 30)
        assert len(snapshot.assets) == 4
    
    @pytest.mark.asyncio
    async def test_create_universe_snapshot_duplicate_date(self, universe_service: UniverseService, test_universe_with_assets):
        """Test creating snapshot with duplicate date fails"""
        user = test_universe_with_assets['user']
        universe = test_universe_with_assets['universe']
        
        # Create first snapshot
        result1 = await universe_service.create_universe_snapshot(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            user_id=user.id
        )
        assert result1.success is True
        
        # Try to create snapshot with same date
        result2 = await universe_service.create_universe_snapshot(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),  # Same date
            user_id=user.id
        )
        
        assert result2.success is False
        assert "already exists" in result2.error
        assert "update_existing_snapshot" in result2.next_actions
    
    @pytest.mark.asyncio
    async def test_create_universe_snapshot_with_turnover(self, universe_service: UniverseService, test_universe_with_assets):
        """Test creating second snapshot calculates turnover correctly"""
        user = test_universe_with_assets['user']
        universe = test_universe_with_assets['universe']
        
        # Create first snapshot
        result1 = await universe_service.create_universe_snapshot(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            user_id=user.id
        )
        assert result1.success is True
        
        # Modify universe composition
        # Remove GOOGL and AMZN, add NVDA and TSLA
        googl_asset = universe_service.db.query(Asset).filter(Asset.symbol == 'GOOGL').first()
        amzn_asset = universe_service.db.query(Asset).filter(Asset.symbol == 'AMZN').first()
        
        # Remove associations
        universe_service.db.query(UniverseAsset).filter(
            UniverseAsset.universe_id == universe.id,
            UniverseAsset.asset_id.in_([googl_asset.id, amzn_asset.id])
        ).delete(synchronize_session=False)
        
        # Add new assets
        new_assets = [
            Asset(symbol='NVDA', name='NVIDIA Corp', is_validated=True),
            Asset(symbol='TSLA', name='Tesla Inc', is_validated=True)
        ]
        
        for asset in new_assets:
            universe_service.db.add(asset)
        
        universe_service.db.commit()
        
        # Add associations
        for i, asset in enumerate(new_assets):
            universe_asset = UniverseAsset(
                universe_id=universe.id,
                asset_id=asset.id,
                position=i + 2,  # AAPL and MSFT are positions 0,1
                weight=0.25,
                added_at=datetime.now(timezone.utc)
            )
            universe_service.db.add(universe_asset)
        
        universe_service.db.commit()
        
        # Create second snapshot
        result2 = await universe_service.create_universe_snapshot(
            universe_id=universe.id,
            snapshot_date=date(2024, 9, 30),
            user_id=user.id
        )
        
        assert result2.success is True
        assert result2.data['turnover_rate'] > 0.0  # Should have turnover
        assert len(result2.data['assets_added']) == 2
        assert len(result2.data['assets_removed']) == 2
        assert 'NVDA' in result2.data['assets_added']
        assert 'TSLA' in result2.data['assets_added']
        assert 'GOOGL' in result2.data['assets_removed']
        assert 'AMZN' in result2.data['assets_removed']
    
    @pytest.mark.asyncio
    async def test_get_universe_timeline(self, universe_service: UniverseService, test_universe_with_assets):
        """Test get_universe_timeline method"""
        user = test_universe_with_assets['user']
        universe = test_universe_with_assets['universe']
        
        # Create multiple snapshots
        dates = [date(2024, 3, 31), date(2024, 6, 30), date(2024, 9, 30)]
        
        for snapshot_date in dates:
            result = await universe_service.create_universe_snapshot(
                universe_id=universe.id,
                snapshot_date=snapshot_date,
                user_id=user.id
            )
            assert result.success is True
        
        # Test timeline retrieval
        timeline_result = await universe_service.get_universe_timeline(
            universe_id=universe.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            user_id=user.id
        )
        
        assert timeline_result.success is True
        assert len(timeline_result.data['timeline']) == 3
        assert timeline_result.data['period_analysis']['snapshot_count'] == 3
        assert timeline_result.data['period_analysis']['average_asset_count'] == 4.0
        assert timeline_result.data['universe_info']['name'] == universe.name
    
    @pytest.mark.asyncio
    async def test_get_universe_timeline_no_snapshots(self, universe_service: UniverseService, test_universe_with_assets):
        """Test get_universe_timeline with no snapshots"""
        user = test_universe_with_assets['user']
        universe = test_universe_with_assets['universe']
        
        # Test timeline with no snapshots
        timeline_result = await universe_service.get_universe_timeline(
            universe_id=universe.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            user_id=user.id
        )
        
        assert timeline_result.success is False
        assert "No snapshots found" in timeline_result.message
        assert "create_initial_snapshot" in timeline_result.next_actions
    
    @pytest.mark.asyncio
    async def test_backfill_universe_history(self, universe_service: UniverseService, test_universe_with_assets):
        """Test backfill_universe_history method"""
        user = test_universe_with_assets['user']
        universe = test_universe_with_assets['universe']
        
        # Test monthly backfill
        backfill_result = await universe_service.backfill_universe_history(
            universe_id=universe.id,
            start_date=date(2024, 3, 31),
            end_date=date(2024, 7, 31),
            frequency='monthly',
            user_id=user.id
        )
        
        assert backfill_result.success is True
        
        summary = backfill_result.data['backfill_summary']
        assert summary['success_count'] > 0
        assert summary['frequency'] == 'monthly'
        assert summary['start_date'] == '2024-03-31'
        assert summary['end_date'] == '2024-07-31'
        
        # Verify snapshots were created
        snapshots = universe_service.db.query(UniverseSnapshot).filter(
            UniverseSnapshot.universe_id == universe.id
        ).count()
        
        assert snapshots == summary['success_count']
    
    @pytest.mark.asyncio
    async def test_backfill_universe_history_quarterly(self, universe_service: UniverseService, test_universe_with_assets):
        """Test backfill with quarterly frequency"""
        user = test_universe_with_assets['user']
        universe = test_universe_with_assets['universe']
        
        # Test quarterly backfill
        backfill_result = await universe_service.backfill_universe_history(
            universe_id=universe.id,
            start_date=date(2024, 3, 31),
            end_date=date(2024, 12, 31),
            frequency='quarterly',
            user_id=user.id
        )
        
        assert backfill_result.success is True
        
        # Should create Q1, Q2, Q3, Q4 snapshots
        summary = backfill_result.data['backfill_summary']
        assert summary['success_count'] >= 2  # At least Q1 and Q4
        assert summary['frequency'] == 'quarterly'
    
    @pytest.mark.asyncio
    async def test_temporal_methods_access_control(self, universe_service: UniverseService, test_universe_with_assets):
        """Test temporal methods respect user access control"""
        user = test_universe_with_assets['user']
        universe = test_universe_with_assets['universe']
        
        # Create another user
        other_user = User(
            email="other@service.com",
            hashed_password="hashed123",
            full_name="Other User",
            role=UserRole.USER,
            subscription_tier=SubscriptionTier.FREE
        )
        universe_service.db.add(other_user)
        universe_service.db.commit()
        
        # Try to create snapshot as different user (should fail)
        result = await universe_service.create_universe_snapshot(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            user_id=other_user.id  # Different user
        )
        
        assert result.success is False
        assert result.error == "Access denied"
    
    @pytest.mark.asyncio
    async def test_temporal_methods_nonexistent_universe(self, universe_service: UniverseService):
        """Test temporal methods with nonexistent universe"""
        # Test with fake universe ID
        result = await universe_service.create_universe_snapshot(
            universe_id="fake-universe-id",
            snapshot_date=date(2024, 6, 30)
        )
        
        assert result.success is False
        assert result.error == "Universe not found"


class TestTemporalUniverseService:
    """Test TemporalUniverseService functionality"""
    
    @pytest.fixture
    def temporal_service(self, db_session: Session):
        """Create TemporalUniverseService instance for testing"""
        return TemporalUniverseService(db_session)
    
    @pytest.fixture
    def test_universe_with_screening(self, db_session: Session):
        """Create test universe with screening criteria"""
        user = User(
            email="temporal@screening.com",
            hashed_password="hashed123",
            full_name="Temporal Screening User",
            role=UserRole.USER,
            subscription_tier=SubscriptionTier.FREE
        )
        db_session.add(user)
        db_session.commit()
        
        universe = Universe(
            name="Temporal Screening Universe",
            description="Universe for temporal screening",
            owner_id=user.id,
            screening_criteria={
                'market_cap': '>100B',
                'sector': 'Technology'
            }
        )
        db_session.add(universe)
        db_session.commit()
        
        return {'user': user, 'universe': universe}
    
    @pytest.mark.asyncio
    async def test_schedule_universe_updates(self, temporal_service: TemporalUniverseService, test_universe_with_screening):
        """Test schedule_universe_updates method"""
        user = test_universe_with_screening['user']
        universe = test_universe_with_screening['universe']
        
        # Create schedule configuration
        schedule_config = ScheduleConfig(
            frequency='monthly',
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=365),
            timezone='UTC',
            execution_time='09:00'
        )
        
        # Test scheduling
        result = await temporal_service.schedule_universe_updates(
            universe_id=universe.id,
            schedule_config=schedule_config,
            user_id=user.id
        )
        
        assert result.success is True
        assert result.data['schedule_config']['frequency'] == 'monthly'
        assert len(result.data['next_executions']) > 0
        assert 'test_screening_criteria' in result.next_actions
        
        # Verify schedule was stored in universe
        temporal_service.db.refresh(universe)
        assert 'schedule' in universe.screening_criteria
        assert universe.screening_criteria['schedule']['frequency'] == 'monthly'
    
    @pytest.mark.asyncio
    async def test_schedule_universe_updates_no_criteria(self, temporal_service: TemporalUniverseService, db_session: Session):
        """Test scheduling fails without screening criteria"""
        user = User(
            email="nocriteria@test.com",
            hashed_password="hashed123",
            full_name="No Criteria User",
            role=UserRole.USER,
            subscription_tier=SubscriptionTier.FREE
        )
        db_session.add(user)
        db_session.commit()
        
        universe = Universe(
            name="No Criteria Universe",
            description="Universe without screening criteria",
            owner_id=user.id
            # No screening_criteria set
        )
        db_session.add(universe)
        db_session.commit()
        
        schedule_config = ScheduleConfig(
            frequency='monthly',
            start_date=date.today() + timedelta(days=30)
        )
        
        result = await temporal_service.schedule_universe_updates(
            universe_id=universe.id,
            schedule_config=schedule_config,
            user_id=user.id
        )
        
        assert result.success is False
        assert result.error == "No screening criteria"
        assert "configure_screening_criteria" in result.next_actions
    
    @pytest.mark.asyncio
    async def test_get_point_in_time_composition(self, temporal_service: TemporalUniverseService, test_universe_with_screening):
        """Test get_point_in_time_composition method"""
        user = test_universe_with_screening['user']
        universe = test_universe_with_screening['universe']
        
        # Create test snapshot
        snapshot = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            current_assets=[
                {'symbol': 'AAPL', 'name': 'Apple Inc', 'weight': 0.50},
                {'symbol': 'MSFT', 'name': 'Microsoft Corp', 'weight': 0.50}
            ]
        )
        temporal_service.db.add(snapshot)
        temporal_service.db.commit()
        
        # Test point-in-time retrieval
        result = await temporal_service.get_point_in_time_composition(
            universe_id=universe.id,
            target_date=date(2024, 7, 15),  # After snapshot date
            user_id=user.id,
            include_context=True
        )
        
        assert result.success is True
        assert result.data['composition']['target_date'] == '2024-07-15'
        assert result.data['composition']['snapshot_date'] == '2024-06-30'
        assert result.data['composition']['asset_count'] == 2
        assert 'context' in result.data
        assert result.metadata['days_difference'] == 15
    
    @pytest.mark.asyncio
    async def test_get_point_in_time_composition_no_snapshot(self, temporal_service: TemporalUniverseService, test_universe_with_screening):
        """Test point-in-time composition with no available snapshot"""
        user = test_universe_with_screening['user']
        universe = test_universe_with_screening['universe']
        
        # Test without any snapshots
        result = await temporal_service.get_point_in_time_composition(
            universe_id=universe.id,
            target_date=date(2024, 6, 30),
            user_id=user.id
        )
        
        assert result.success is False
        assert result.error == "No snapshot found"
        assert "create_historical_snapshot" in result.next_actions
    
    @pytest.mark.asyncio
    async def test_calculate_turnover_analysis_insufficient_data(self, temporal_service: TemporalUniverseService, test_universe_with_screening):
        """Test turnover analysis with insufficient data"""
        user = test_universe_with_screening['user']
        universe = test_universe_with_screening['universe']
        
        # Create only one snapshot (need at least 2 for analysis)
        snapshot = UniverseSnapshot.create_from_universe_state(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            current_assets=[{'symbol': 'AAPL', 'name': 'Apple Inc'}]
        )
        temporal_service.db.add(snapshot)
        temporal_service.db.commit()
        
        # Test analysis with insufficient data
        result = await temporal_service.calculate_turnover_analysis(
            universe_id=universe.id,
            analysis_period='6months',
            user_id=user.id
        )
        
        assert result.success is False
        assert result.error == "Insufficient data"
        assert "create_more_snapshots" in result.next_actions


@pytest.mark.integration
class TestTemporalServicesIntegration:
    """Integration tests for temporal services"""
    
    @pytest.mark.asyncio
    async def test_temporal_workflow_integration(self, db_session: Session):
        """Test complete temporal workflow integration"""
        # Create test data
        user = User(
            email="workflow@integration.com",
            hashed_password="hashed123",
            full_name="Workflow Integration User",
            role=UserRole.USER,
            subscription_tier=SubscriptionTier.FREE
        )
        db_session.add(user)
        db_session.commit()
        
        universe = Universe(
            name="Workflow Integration Universe",
            description="Universe for workflow testing",
            owner_id=user.id,
            screening_criteria={'market_cap': '>100B'}
        )
        db_session.add(universe)
        
        # Add assets
        assets = [
            Asset(symbol='AAPL', name='Apple Inc', is_validated=True),
            Asset(symbol='MSFT', name='Microsoft Corp', is_validated=True)
        ]
        
        for asset in assets:
            db_session.add(asset)
        
        db_session.commit()
        
        # Add universe-asset associations
        for i, asset in enumerate(assets):
            universe_asset = UniverseAsset(
                universe_id=universe.id,
                asset_id=asset.id,
                position=i,
                weight=0.50,
                added_at=datetime.now(timezone.utc)
            )
            db_session.add(universe_asset)
        
        db_session.commit()
        
        # Initialize services
        universe_service = UniverseService(db_session)
        temporal_service = TemporalUniverseService(db_session)
        
        # Step 1: Create initial snapshot
        snapshot_result = await universe_service.create_universe_snapshot(
            universe_id=universe.id,
            snapshot_date=date(2024, 6, 30),
            user_id=user.id
        )
        assert snapshot_result.success is True
        
        # Step 2: Backfill history
        backfill_result = await universe_service.backfill_universe_history(
            universe_id=universe.id,
            start_date=date(2024, 3, 31),
            end_date=date(2024, 5, 31),
            frequency='monthly',
            user_id=user.id
        )
        assert backfill_result.success is True
        
        # Step 3: Get timeline
        timeline_result = await universe_service.get_universe_timeline(
            universe_id=universe.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            user_id=user.id
        )
        assert timeline_result.success is True
        assert timeline_result.data['period_analysis']['snapshot_count'] >= 3
        
        # Step 4: Point-in-time composition
        pit_result = await temporal_service.get_point_in_time_composition(
            universe_id=universe.id,
            target_date=date(2024, 7, 15),
            user_id=user.id
        )
        assert pit_result.success is True
        
        # Step 5: Schedule updates
        schedule_config = ScheduleConfig(
            frequency='monthly',
            start_date=date.today() + timedelta(days=30)
        )
        
        schedule_result = await temporal_service.schedule_universe_updates(
            universe_id=universe.id,
            schedule_config=schedule_config,
            user_id=user.id
        )
        assert schedule_result.success is True
        
        # Verify complete workflow created proper data structure
        snapshots = db_session.query(UniverseSnapshot).filter(
            UniverseSnapshot.universe_id == universe.id
        ).count()
        
        assert snapshots >= 3  # Initial + backfilled snapshots
    
    @pytest.mark.asyncio
    async def test_temporal_services_performance(self, db_session: Session):
        """Test temporal services performance with multiple snapshots"""
        import time
        
        # Create test data
        user = User(
            email="performance@test.com",
            hashed_password="hashed123",
            full_name="Performance Test User",
            role=UserRole.USER,
            subscription_tier=SubscriptionTier.FREE
        )
        db_session.add(user)
        db_session.commit()
        
        universe = Universe(
            name="Performance Test Universe",
            description="Universe for performance testing",
            owner_id=user.id
        )
        db_session.add(universe)
        db_session.commit()
        
        # Create multiple snapshots quickly
        universe_service = UniverseService(db_session)
        
        start_time = time.time()
        
        dates = [
            date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 31),
            date(2024, 4, 30), date(2024, 5, 31), date(2024, 6, 30),
            date(2024, 7, 31), date(2024, 8, 31), date(2024, 9, 30)
        ]
        
        for snapshot_date in dates:
            result = await universe_service.create_universe_snapshot(
                universe_id=universe.id,
                snapshot_date=snapshot_date,
                user_id=user.id
            )
            assert result.success is True
        
        creation_time = time.time() - start_time
        
        # Test timeline retrieval performance
        start_time = time.time()
        
        timeline_result = await universe_service.get_universe_timeline(
            universe_id=universe.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            user_id=user.id
        )
        
        retrieval_time = time.time() - start_time
        
        assert timeline_result.success is True
        assert timeline_result.data['period_analysis']['snapshot_count'] == 9
        
        # Performance assertions (should be fast)
        assert creation_time < 5.0  # Creating 9 snapshots should take < 5 seconds
        assert retrieval_time < 1.0  # Timeline retrieval should take < 1 second