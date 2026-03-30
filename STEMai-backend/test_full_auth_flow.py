#!/usr/bin/env python3
"""
Comprehensive authentication and endpoint test.
Tests the complete flow: register → login → call protected endpoint.
"""

import os
import sys
import json
import httpx
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("\n" + "="*70)
print("STEMbotix Full Authentication & Endpoint Test")
print("="*70)

# Configuration
BACKEND_URL = "http://localhost:8123"
TEST_EMAIL = "teacher-test@stembotix.local"
TEST_PASSWORD = "testpass123"

print(f"\n📍 Backend URL: {BACKEND_URL}")
print(f"👤 Test User: {TEST_EMAIL}")

# ─────────────────────────────────────────────────────────────────────────────
# 1. TEST LOCAL AUTH SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "-"*70)
print("STEP 1: Verify Local Auth System")
print("-"*70)

try:
    from app.core.auth import create_access_token, decode_access_token
    
    token = create_access_token(user_id="test-123", role="teacher")
    payload = decode_access_token(token)
    print(f"✓ Local token creation/validation works")
    print(f"  Token prefix: {token[:30]}...")
    print(f"  Payload: uid={payload.get('uid')}, role={payload.get('role')}")
except Exception as e:
    print(f"✗ Local auth failed: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# 2. TEST BACKEND CONNECTION
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "-"*70)
print("STEP 2: Test Backend Health")
print("-"*70)

try:
    with httpx.Client(timeout=5.0) as client:
        resp = client.get(f"{BACKEND_URL}/health")
        if resp.status_code == 200:
            print(f"✓ Backend is running")
            print(f"  Response: {resp.json()}")
        else:
            print(f"✗ Backend health check failed: {resp.status_code}")
            sys.exit(1)
except Exception as e:
    print(f"✗ Cannot connect to backend: {e}")
    print(f"  Make sure backend is running: python run.py")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# 3. TEST USER REGISTRATION
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "-"*70)
print("STEP 3: Register Test User")
print("-"*70)

try:
    with httpx.Client(timeout=10.0) as client:
        # First clear existing user by trying to delete (this will fail, which is ok)
        client.post(
            f"{BACKEND_URL}/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "role": "teacher"}
        )
        
        resp = client.post(
            f"{BACKEND_URL}/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "role": "teacher"}
        )
        
        if resp.status_code == 409:
            print(f"✓ User already exists (expected)")
        elif resp.status_code == 200:
            print(f"✓ User registered successfully")
            data = resp.json()
            print(f"  User ID: {data.get('user_id')}")
            print(f"  Token: {data.get('access_token', 'N/A')[:30]}...")
        else:
            print(f"✗ Registration failed: {resp.status_code}")
            print(f"  Response: {resp.text}")
            sys.exit(1)
except Exception as e:
    print(f"✗ Registration request failed: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# 4. TEST LOGIN
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "-"*70)
print("STEP 4: Login to Get Token")
print("-"*70)

auth_token = None
user_id = None

try:
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            f"{BACKEND_URL}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            auth_token = data.get("access_token")
            user_id = data.get("user_id")
            print(f"✓ Login successful")
            print(f"  User ID: {user_id}")
            print(f"  Token: {auth_token[:40]}...")
            print(f"  Role: {data.get('role')}")
        else:
            print(f"✗ Login failed: {resp.status_code}")
            print(f"  Response: {resp.text}")
            sys.exit(1)
except Exception as e:
    print(f"✗ Login request failed: {e}")
    sys.exit(1)

if not auth_token:
    print(f"✗ No token received!")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# 5. TEST TOKEN IN AUTHORIZATION HEADER
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "-"*70)
print("STEP 5: Verify Token in Authorization Header")
print("-"*70)

try:
    with httpx.Client(timeout=10.0) as client:
        headers = {"Authorization": f"Bearer {auth_token}"}
        resp = client.get(f"{BACKEND_URL}/auth/me", headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"✓ Token is valid (verified via /auth/me)")
            print(f"  Email: {data.get('email')}")
            print(f"  Role: {data.get('role')}")
        else:
            print(f"✗ Token validation failed: {resp.status_code}")
            print(f"  Response: {resp.text}")
            sys.exit(1)
except Exception as e:
    print(f"✗ Token test request failed: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# 6. TEST BLOCKZIE ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "-"*70)
print("STEP 6: Test /api/blockzie/generate_xml Endpoint")
print("-"*70)

try:
    with httpx.Client(timeout=30.0) as client:
        payload = {
            "prompt": "Move the sprite 10 steps forward",
            "auto_start": False
        }
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        print(f"  Sending request with Authorization header...")
        print(f"  Headers: {headers}")
        print(f"  Payload: {payload}")
        
        resp = client.post(
            f"{BACKEND_URL}/api/blockzie/generate_xml",
            json=payload,
            headers=headers,
            timeout=30.0
        )
        
        print(f"\n  Response Status: {resp.status_code}")
        print(f"  Response Headers: {dict(resp.headers)}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"✓ ENDPOINT SUCCESS!")
            print(f"  XML blocks generated: {data.get('block_count', 0)}")
            print(f"  Model used: {data.get('model_used', 'N/A')}")
            print(f"  Method: {data.get('method', 'N/A')}")
        elif resp.status_code == 401:
            print(f"✗ AUTHORIZATION FAILED (401)")
            print(f"  Response: {resp.text}")
            print(f"\n  DEBUG INFO:")
            print(f"  - Token: {auth_token[:50]}...")
            print(f"  - Token length: {len(auth_token)}")
            sys.exit(1)
        else:
            print(f"✗ Request failed: {resp.status_code}")
            print(f"  Response: {resp.text}")
            sys.exit(1)
            
except Exception as e:
    print(f"✗ Blockzie endpoint request failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70)
print("✅ ALL TESTS PASSED!")
print("="*70 + "\n")
