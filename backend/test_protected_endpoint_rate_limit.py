#!/usr/bin/env python3
"""
Test script to specifically test rate limiting on protected endpoints.
"""

import os
import time
from fastapi.testclient import TestClient
from app.main import app

def test_protected_endpoint_rate_limiting():
    """Test that protected endpoints get rate limited before auth check."""
    
    print("=== Testing Protected Endpoint Rate Limiting ===")
    
    # Enable rate limiting for this test
    os.environ["ENVIRONMENT"] = "testing_with_rate_limits"
    
    with TestClient(app) as client:
        print("Testing /api/v1/auth/me (protected endpoint) without authentication")
        
        # Make many requests to the protected endpoint without auth
        responses = []
        for i in range(15):
            response = client.get("/api/v1/auth/me")
            responses.append(response.status_code)
            print(f"  Request {i+1}: Status {response.status_code}")
            
            if response.status_code == 429:
                print(f"    Rate limited: {response.json()}")
                break
            elif response.status_code == 403:
                print(f"    Auth required: {response.json()}")
            elif response.status_code == 401:
                print(f"    Unauthorized: {response.json()}")
            
            time.sleep(0.05)  # Small delay to avoid overwhelming
        
        # Count response types
        status_429 = responses.count(429)
        status_403 = responses.count(403)
        status_401 = responses.count(401)
        
        print(f"\n=== Summary ===")
        print(f"Rate limited (429): {status_429}")
        print(f"Forbidden (403): {status_403}")
        print(f"Unauthorized (401): {status_401}")
        
        if status_429 > 0:
            print("✅ GOOD: Rate limiting is being applied to protected endpoints")
        else:
            print("❌ ISSUE: Protected endpoints bypass rate limiting")
            
        # Now test with a different endpoint pattern to see rate limit config
        print(f"\nTesting different endpoint for rate limit behavior...")
        
        # Test general endpoint rate limiting
        print("Testing /health/ (exempt endpoint)")
        for i in range(5):
            response = client.get("/health/")
            print(f"  Health request {i+1}: Status {response.status_code}")
            if response.status_code == 429:
                print(f"    Unexpected rate limit on exempt endpoint: {response.json()}")
                break

if __name__ == "__main__":
    test_protected_endpoint_rate_limiting()