#!/usr/bin/env python3
"""
Test script to verify middleware ordering for rate limiting vs authentication.
This will help understand the current behavior and determine if there's actually a problem.
"""

import requests
import time
import os
from fastapi.testclient import TestClient
from app.main import app

def test_middleware_order():
    """Test current middleware order and behavior."""
    
    print("=== Testing Middleware Order ===")
    
    # Enable rate limiting for this test
    os.environ["ENVIRONMENT"] = "testing_with_rate_limits"
    
    with TestClient(app) as client:
        print(f"1. Testing unauthenticated requests to /api/v1/auth/register")
        
        # Test registration without authentication (should hit rate limiting first)
        successful_requests = 0
        rate_limited_requests = 0
        auth_failed_requests = 0
        
        for i in range(8):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"test{i}@example.com",
                    "password": "SuperSecure2025Password!@#$%",  # Use a password that will pass validation
                    "full_name": "Test User"
                }
            )
            
            print(f"  Request {i+1}: Status {response.status_code}")
            
            if response.status_code == 201:
                successful_requests += 1
            elif response.status_code == 429:
                rate_limited_requests += 1
                print(f"    Rate limited: {response.json()}")
            elif response.status_code == 401:
                auth_failed_requests += 1
                print(f"    Auth failed: {response.json()}")
            else:
                print(f"    Other status: {response.json()}")
            
            time.sleep(0.1)  # Small delay
        
        print(f"\n=== Results ===")
        print(f"Successful requests: {successful_requests}")
        print(f"Rate limited requests: {rate_limited_requests}")
        print(f"Auth failed requests: {auth_failed_requests}")
        
        print(f"\n2. Testing protected endpoint without authentication")
        
        # Test protected endpoint without auth token
        response = client.get("/api/v1/auth/me")
        print(f"  GET /api/v1/auth/me without auth: Status {response.status_code}")
        if response.status_code != 200:
            print(f"    Response: {response.json()}")
        
        print(f"\n3. Testing if rate limiting applies to protected endpoints")
        
        # Make multiple requests to protected endpoint to see if rate limiting applies
        auth_errors = 0
        rate_limits = 0
        
        for i in range(6):
            response = client.get("/api/v1/auth/me")
            if response.status_code == 401:
                auth_errors += 1
            elif response.status_code == 429:
                rate_limits += 1
                print(f"    Request {i+1}: Rate limited! {response.json()}")
            else:
                print(f"    Request {i+1}: Status {response.status_code}")
            
            time.sleep(0.1)
        
        print(f"  Auth errors (401): {auth_errors}")
        print(f"  Rate limits (429): {rate_limits}")
        
        if rate_limits > 0:
            print(f"✅ GOOD: Rate limiting is applied BEFORE authentication")
        else:
            print(f"❌ ISSUE: Rate limiting may not be applied before authentication")

if __name__ == "__main__":
    test_middleware_order()