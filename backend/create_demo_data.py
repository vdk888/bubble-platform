#!/usr/bin/env python3
"""
Demo Data Generator for Temporal Universe System

Creates comprehensive test data including:
1. Test user with simple credentials  
2. Tech Leaders Portfolio universe with major tech stocks
3. Historical snapshots spanning 6 months with realistic turnover
4. Performance metrics and timeline data for frontend testing

Usage: python create_demo_data.py
"""
import asyncio
import sys
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
import random

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import get_db
from app.core.security import auth_service
from app.models.user import User, SubscriptionTier, UserRole
from app.models.universe import Universe
from app.models.universe_snapshot import UniverseSnapshot
from app.models.asset import Asset, UniverseAsset
from sqlalchemy.orm import Session


class DemoDataGenerator:
    """Generate comprehensive demo data for temporal universe system"""
    
    def __init__(self):
        # Demo user credentials - simple and memorable
        self.demo_email = "demo@bubble.ai" 
        self.demo_password = "Demo123!"  # Simple but secure password
        
        # Major tech stocks for Tech Leaders Portfolio
        self.tech_stocks = [
            {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology", "market_cap": 3000000000000},
            {"symbol": "GOOGL", "name": "Alphabet Inc. Class A", "sector": "Technology", "market_cap": 2000000000000},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology", "market_cap": 2800000000000},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Discretionary", "market_cap": 1800000000000},
            {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Discretionary", "market_cap": 800000000000},
            {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Technology", "market_cap": 900000000000},
            {"symbol": "NFLX", "name": "Netflix Inc.", "sector": "Technology", "market_cap": 200000000000},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology", "market_cap": 1200000000000},
        ]
        
        # Additional stocks for realistic turnover
        self.additional_stocks = [
            {"symbol": "ORCL", "name": "Oracle Corporation", "sector": "Technology", "market_cap": 400000000000},
            {"symbol": "CRM", "name": "Salesforce Inc.", "sector": "Technology", "market_cap": 250000000000},
            {"symbol": "ADBE", "name": "Adobe Inc.", "sector": "Technology", "market_cap": 300000000000},
            {"symbol": "PYPL", "name": "PayPal Holdings Inc.", "sector": "Technology", "market_cap": 100000000000},
        ]
        
        self.all_stocks = self.tech_stocks + self.additional_stocks
        
    async def create_demo_user(self, db: Session) -> User:
        """Create demo user with simple credentials"""
        print("Creating demo user...")
        
        # Check if demo user already exists
        existing_user = db.query(User).filter(User.email == self.demo_email).first()
        if existing_user:
            print(f"Demo user already exists: {self.demo_email}")
            return existing_user
        
        # Create new demo user
        demo_user = User(
            email=self.demo_email,
            hashed_password=auth_service.get_password_hash(self.demo_password),
            full_name="Demo User",
            role=UserRole.USER,
            subscription_tier=SubscriptionTier.PRO,  # Give pro access for full features
            is_verified=True
        )
        
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
        
        print(f"Created demo user: {self.demo_email}")
        print(f"Password: {self.demo_password}")
        return demo_user
    
    async def create_assets(self, db: Session) -> Dict[str, Asset]:
        """Create all asset entities"""
        print("Creating asset entities...")
        
        assets = {}
        for stock_info in self.all_stocks:
            # Check if asset already exists
            existing_asset = db.query(Asset).filter(Asset.symbol == stock_info["symbol"]).first()
            if existing_asset:
                assets[stock_info["symbol"]] = existing_asset
                continue
            
            # Create new asset
            asset = Asset(
                symbol=stock_info["symbol"],
                name=stock_info["name"],
                sector=stock_info["sector"],
                market_cap=stock_info["market_cap"],
                is_validated=True,
                last_validated_at=datetime.utcnow(),
                validation_source="demo_data"
            )
            
            db.add(asset)
            assets[stock_info["symbol"]] = asset
        
        db.commit()
        print(f"Created {len(assets)} asset entities")
        return assets
    
    async def create_tech_universe(self, db: Session, user: User, assets: Dict[str, Asset]) -> Universe:
        """Create Tech Leaders Portfolio universe"""
        print("Creating Tech Leaders Portfolio universe...")
        
        # Check if universe already exists
        existing_universe = db.query(Universe).filter(
            Universe.name == "Tech Leaders Portfolio",
            Universe.owner_id == user.id
        ).first()
        
        if existing_universe:
            print("Tech Leaders Portfolio already exists")
            return existing_universe
        
        # Create universe
        universe = Universe(
            name="Tech Leaders Portfolio",
            description="Major technology companies portfolio showcasing temporal universe features with realistic turnover patterns",
            owner_id=user.id,
            screening_criteria={
                "sector": ["Technology", "Consumer Discretionary"],
                "market_cap_min": 100000000000,  # 100B minimum
                "criteria_type": "fundamental_screening"
            }
        )
        
        db.add(universe)
        db.commit()
        db.refresh(universe)
        
        # Add initial assets to universe (core tech stocks)
        core_symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META"]
        for i, symbol in enumerate(core_symbols):
            if symbol in assets:
                universe_asset = UniverseAsset(
                    universe_id=universe.id,
                    asset_id=assets[symbol].id,
                    position=i + 1,
                    weight=1.0 / len(core_symbols),  # Equal weight initially
                    added_at=datetime.utcnow(),
                    notes=f"Core tech holding - {symbol}"
                )
                db.add(universe_asset)
        
        db.commit()
        print(f"Created Tech Leaders Portfolio with {len(core_symbols)} initial assets")
        return universe
    
    def generate_realistic_performance_metrics(self, assets: List[Dict[str, Any]], date: date) -> Dict[str, Any]:
        """Generate realistic performance metrics for a snapshot"""
        # Simulate some realistic financial metrics
        random.seed(date.toordinal())  # Consistent randomness based on date
        
        expected_return = random.uniform(0.08, 0.15)  # 8-15% expected annual return
        volatility = random.uniform(0.15, 0.25)  # 15-25% volatility
        sharpe_estimate = expected_return / volatility
        
        # Sector allocation
        sectors = {}
        for asset in assets:
            sector = asset.get('sector', 'Unknown')
            sectors[sector] = sectors.get(sector, 0) + 1
        
        total_assets = len(assets)
        sector_allocation = {
            sector: (count / total_assets) * 100 
            for sector, count in sectors.items()
        }
        
        return {
            "expected_return": round(expected_return, 4),
            "volatility": round(volatility, 4),
            "sharpe_estimate": round(sharpe_estimate, 2),
            "sector_allocation": sector_allocation,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def create_historical_snapshots(self, db: Session, universe: Universe, assets: Dict[str, Asset]) -> List[UniverseSnapshot]:
        """Generate 6 months of historical snapshots with realistic turnover"""
        print("Creating historical snapshots...")
        
        snapshots = []
        
        # Start 6 months ago
        start_date = date.today() - timedelta(days=180)
        
        # Generate monthly snapshots
        for month_offset in range(6):
            snapshot_date = start_date + timedelta(days=30 * month_offset)
            
            # Check if snapshot already exists
            existing_snapshot = db.query(UniverseSnapshot).filter(
                UniverseSnapshot.universe_id == universe.id,
                UniverseSnapshot.snapshot_date == snapshot_date
            ).first()
            
            if existing_snapshot:
                snapshots.append(existing_snapshot)
                continue
            
            # Generate universe composition for this period
            composition = self.generate_period_composition(month_offset, assets)
            
            # Calculate turnover vs previous snapshot
            previous_snapshot = snapshots[-1] if snapshots else None
            
            snapshot = UniverseSnapshot.create_from_universe_state(
                universe_id=universe.id,
                snapshot_date=snapshot_date,
                current_assets=composition,
                screening_criteria={
                    "sector": ["Technology", "Consumer Discretionary"],
                    "market_cap_min": 100000000000,
                    "rebalance_trigger": "monthly",
                    "snapshot_period": f"Month_{month_offset + 1}"
                },
                previous_snapshot=previous_snapshot
            )
            
            # Add performance metrics
            snapshot.performance_metrics = self.generate_realistic_performance_metrics(composition, snapshot_date)
            
            db.add(snapshot)
            snapshots.append(snapshot)
        
        db.commit()
        print(f"Created {len(snapshots)} historical snapshots")
        return snapshots
    
    def generate_period_composition(self, month_offset: int, assets: Dict[str, Asset]) -> List[Dict[str, Any]]:
        """Generate realistic universe composition for a specific month"""
        # Base composition (always included)
        core_holdings = ["AAPL", "GOOGL", "MSFT"]
        
        # Variable holdings that create realistic turnover
        period_holdings = []
        
        if month_offset == 0:  # Month 1 - Initial composition
            period_holdings = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META"]
        elif month_offset == 1:  # Month 2 - Add NVDA, keep others
            period_holdings = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA"]
        elif month_offset == 2:  # Month 3 - Remove AMZN, add NFLX
            period_holdings = ["AAPL", "GOOGL", "MSFT", "TSLA", "META", "NVDA", "NFLX"]
        elif month_offset == 3:  # Month 4 - Add ORCL, remove TSLA
            period_holdings = ["AAPL", "GOOGL", "MSFT", "META", "NVDA", "NFLX", "ORCL"]
        elif month_offset == 4:  # Month 5 - Add back TSLA and AMZN, remove NFLX
            period_holdings = ["AAPL", "GOOGL", "MSFT", "META", "NVDA", "ORCL", "TSLA", "AMZN"]
        else:  # Month 6 - Final composition with CRM
            period_holdings = ["AAPL", "GOOGL", "MSFT", "META", "NVDA", "TSLA", "AMZN", "CRM"]
        
        # Convert to composition with metadata
        composition = []
        total_holdings = len(period_holdings)
        
        for i, symbol in enumerate(period_holdings):
            if symbol in assets:
                asset = assets[symbol]
                weight = 1.0 / total_holdings  # Equal weight for simplicity
                
                composition.append({
                    "symbol": symbol,
                    "name": asset.name,
                    "asset_id": asset.id,
                    "sector": asset.sector,
                    "weight": round(weight, 4),
                    "reason_added": self.get_reason_for_holding(symbol, month_offset),
                    "market_cap": asset.market_cap,
                    "position": i + 1
                })
        
        return composition
    
    def get_reason_for_holding(self, symbol: str, month_offset: int) -> str:
        """Generate realistic reasons for holding assets"""
        reasons = {
            "AAPL": "Core technology holding - consistent performance",
            "GOOGL": "Digital advertising leader with AI capabilities", 
            "MSFT": "Cloud computing and enterprise software dominance",
            "AMZN": "E-commerce and cloud infrastructure leader",
            "TSLA": "Electric vehicle innovation and energy storage",
            "META": "Social media platforms and metaverse development",
            "NVDA": "AI and semiconductor market leader",
            "NFLX": "Streaming entertainment and content creation",
            "ORCL": "Enterprise database and cloud solutions",
            "CRM": "Customer relationship management software leader"
        }
        
        return reasons.get(symbol, f"Fundamental screening criteria met - Month {month_offset + 1}")
    
    async def generate_demo_data(self):
        """Main function to generate all demo data"""
        print("Starting Demo Data Generation for Temporal Universe System")
        print("=" * 60)
        
        # Get database session
        db = next(get_db())
        
        try:
            # 1. Create demo user
            user = await self.create_demo_user(db)
            
            # 2. Create asset entities
            assets = await self.create_assets(db)
            
            # 3. Create Tech Leaders Portfolio universe
            universe = await self.create_tech_universe(db, user, assets)
            
            # 4. Create historical snapshots
            snapshots = await self.create_historical_snapshots(db, universe, assets)
            
            print("\n" + "=" * 60)
            print("Demo Data Generation Complete!")
            print("=" * 60)
            
            # Print summary
            print(f"DEMO DATA SUMMARY:")
            print(f"   - User: {user.email}")
            print(f"   - Password: {self.demo_password}")
            print(f"   - Universe: {universe.name}")
            print(f"   - Total Assets: {len(assets)}")
            print(f"   - Historical Snapshots: {len(snapshots)}")
            print(f"   - Timeline Span: {snapshots[0].snapshot_date} to {snapshots[-1].snapshot_date}")
            
            # Calculate and display turnover statistics
            turnover_rates = [float(s.turnover_rate or 0.0) for s in snapshots if s.turnover_rate]
            if turnover_rates:
                avg_turnover = sum(turnover_rates) / len(turnover_rates)
                print(f"   - Average Turnover: {avg_turnover:.1%}")
            
            print(f"\nLOGIN CREDENTIALS:")
            print(f"   Email: {user.email}")
            print(f"   Password: {self.demo_password}")
            print(f"   Subscription: {user.subscription_tier.value}")
            
            print(f"\nFEATURES TO TEST:")
            print(f"   - Timeline visualization with 6 months of data")
            print(f"   - Universe evolution charts showing asset changes")
            print(f"   - Turnover analysis with realistic monthly changes")
            print(f"   - Historical composition tracking")
            print(f"   - Performance metrics evolution")
            
        except Exception as e:
            print(f"Error generating demo data: {e}")
            db.rollback()
            raise
        finally:
            db.close()


async def main():
    """Run the demo data generation"""
    generator = DemoDataGenerator()
    await generator.generate_demo_data()


if __name__ == "__main__":
    print("Demo Data Generator for Bubble Platform")
    print("Generating comprehensive test data for temporal universe system...")
    print()
    
    # Run the generator
    asyncio.run(main())