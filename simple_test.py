#!/usr/bin/env python3
"""Simple test script without Unicode characters"""

import requests
import json
from datetime import date

API_BASE = "http://localhost:8000"
USERNAME = "demo@bubble.ai"
PASSWORD = "Demo123!"

def main():
    print("Testing Manual Snapshot Creation")
    print("=" * 40)
    
    # Login
    print("1. Authenticating...")
    login_response = requests.post(f"{API_BASE}/api/v1/auth/login/", json={
        "email": USERNAME,
        "password": PASSWORD
    })
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.status_code}")
        return
    
    auth_data = login_response.json()
    token = auth_data.get("access_token")
    print("Login successful")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # List universes
    print("\n2. Listing universes...")
    universes_response = requests.get(f"{API_BASE}/api/v1/universes/", headers=headers)
    
    if universes_response.status_code != 200:
        print(f"Failed to fetch universes: {universes_response.status_code}")
        return
    
    universes_data = universes_response.json()
    universes = universes_data.get("data", [])
    
    print(f"Found {len(universes)} universes:")
    for universe in universes:
        print(f"  - {universe['name']} (ID: {universe['id'][:8]}...) - {universe.get('asset_count', 0)} assets")
    
    if not universes:
        print("No universes found")
        return
    
    # Use first universe
    test_universe = universes[0]
    print(f"\n3. Testing with: '{test_universe['name']}'")
    universe_id = test_universe['id']
    
    # Test timeline retrieval
    print(f"\n4. Testing timeline retrieval...")
    timeline_response = requests.get(f"{API_BASE}/api/v1/universes/{universe_id}/timeline/", headers=headers)
    
    if timeline_response.status_code == 200:
        timeline_data = timeline_response.json()
        snapshots = timeline_data.get("data", {}).get("snapshots", [])
        print(f"Timeline retrieved successfully! Found {len(snapshots)} snapshots:")
        for snapshot in snapshots:
            snapshot_date = snapshot.get('snapshot_date', 'Unknown')
            asset_count = len(snapshot.get('assets', []))
            turnover = snapshot.get('turnover_rate', 0)
            print(f"  - {snapshot_date}: {asset_count} assets, turnover: {turnover:.2%}")
    else:
        print(f"Timeline retrieval failed: {timeline_response.status_code}")
        print(timeline_response.text)
    
    print(f"\nTesting completed!")

if __name__ == "__main__":
    main()