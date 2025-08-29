#!/usr/bin/env python3
"""
Test script to create a manual snapshot for a universe to validate temporal functionality.
This demonstrates the dividend portfolio snapshot creation process.
"""

import requests
import json
from datetime import date

# Configuration
API_BASE = "http://localhost:8000"
USERNAME = "demo@bubble.ai"
PASSWORD = "Demo123!"

def main():
    print("Testing Manual Snapshot Creation for Dividend Portfolio")
    print("=" * 60)
    
    # Step 1: Login
    print("1. Authenticating with demo user...")
    login_response = requests.post(f"{API_BASE}/api/v1/auth/login", json={
        "email": USERNAME,
        "password": PASSWORD
    })
    
    if login_response.status_code != 200:
        print(f"[ERROR] Login failed: {login_response.status_code}")
        print(login_response.text)
        return
    
    auth_data = login_response.json()
    token = auth_data.get("access_token")
    print(f"[SUCCESS] Login successful")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 2: List universes to find dividend portfolio
    print("\n2. Listing user universes...")
    universes_response = requests.get(f"{API_BASE}/api/v1/universes", headers=headers)
    
    if universes_response.status_code != 200:
        print(f"❌ Failed to fetch universes: {universes_response.status_code}")
        return
    
    universes_data = universes_response.json()
    universes = universes_data.get("data", [])
    
    print(f"📊 Found {len(universes)} universes:")
    for universe in universes:
        print(f"  - {universe['name']} (ID: {universe['id'][:8]}...) - {universe.get('asset_count', 0)} assets")
    
    # Find a universe to test (prefer one with "dividend" in name, or use first available)
    test_universe = None
    for universe in universes:
        if "dividend" in universe['name'].lower():
            test_universe = universe
            break
    
    if not test_universe and universes:
        test_universe = universes[0]  # Use first universe if no dividend portfolio found
    
    if not test_universe:
        print("❌ No universes found to test with")
        return
    
    print(f"\n3. Selected test universe: '{test_universe['name']}'")
    universe_id = test_universe['id']
    
    # Step 3: Test timeline retrieval (should show all snapshots now)
    print(f"\n4. Testing timeline retrieval for universe {universe_id[:8]}...")
    timeline_response = requests.get(f"{API_BASE}/api/v1/universes/{universe_id}/timeline", headers=headers)
    
    if timeline_response.status_code == 200:
        timeline_data = timeline_response.json()
        snapshots = timeline_data.get("data", {}).get("snapshots", [])
        print(f"✅ Timeline retrieved successfully!")
        print(f"📈 Found {len(snapshots)} snapshots:")
        for snapshot in snapshots:
            snapshot_date = snapshot.get('snapshot_date', 'Unknown')
            asset_count = len(snapshot.get('assets', []))
            turnover = snapshot.get('turnover_rate', 0)
            print(f"  - {snapshot_date}: {asset_count} assets, turnover: {turnover:.2%}")
    else:
        print(f"❌ Timeline retrieval failed: {timeline_response.status_code}")
        print(timeline_response.text)
    
    # Step 4: Create a new snapshot manually
    print(f"\n5. Creating manual snapshot for today...")
    snapshot_request = {
        "snapshot_date": date.today().isoformat(),
        "screening_criteria": {
            "reason": "Manual test snapshot",
            "source": "test_script"
        }
    }
    
    create_response = requests.post(
        f"{API_BASE}/api/v1/universes/{universe_id}/snapshots",
        headers=headers,
        json=snapshot_request
    )
    
    if create_response.status_code == 201:
        snapshot_data = create_response.json()
        print("✅ Snapshot created successfully!")
        created_snapshot = snapshot_data.get("data", [{}])[0] if snapshot_data.get("data") else {}
        print(f"📸 Snapshot ID: {created_snapshot.get('id', 'Unknown')}")
        print(f"📅 Date: {created_snapshot.get('snapshot_date', 'Unknown')}")
        print(f"📊 Assets: {len(created_snapshot.get('assets', []))} symbols")
    else:
        print(f"⚠️ Snapshot creation result: {create_response.status_code}")
        print(create_response.text)
    
    # Step 5: Re-test timeline to see if it now includes more snapshots
    print(f"\n6. Re-testing timeline after snapshot creation...")
    timeline_response = requests.get(f"{API_BASE}/api/v1/universes/{universe_id}/timeline", headers=headers)
    
    if timeline_response.status_code == 200:
        timeline_data = timeline_response.json()
        snapshots = timeline_data.get("data", {}).get("snapshots", [])
        print(f"✅ Updated timeline retrieved!")
        print(f"📈 Now showing {len(snapshots)} snapshots total:")
        for snapshot in snapshots[-3:]:  # Show last 3 snapshots
            snapshot_date = snapshot.get('snapshot_date', 'Unknown')
            asset_count = len(snapshot.get('assets', []))
            turnover = snapshot.get('turnover_rate', 0)
            print(f"  - {snapshot_date}: {asset_count} assets, turnover: {turnover:.2%}")
        
        if len(snapshots) > 3:
            print(f"  ... and {len(snapshots) - 3} more historical snapshots")
            
    print(f"\n🎉 Manual snapshot testing completed!")
    print(f"💡 Your dividend portfolio should now show temporal data in the frontend")

if __name__ == "__main__":
    main()