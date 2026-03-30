#!/usr/bin/env python3
"""Test authentication configuration and token generation/validation."""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("\n" + "="*60)
print("STEMbotix Authentication Configuration Test")
print("="*60)

# Check environment variables
auth_secret = os.getenv("AUTH_SECRET", "change-me-in-production")
token_max_age = int(os.getenv("AUTH_TOKEN_MAX_AGE_SECONDS", "604800"))

print(f"\n✓ AUTH_SECRET: {'SET' if auth_secret != 'change-me-in-production' else 'USING DEFAULT (INSECURE)'}")
print(f"✓ TOKEN_MAX_AGE: {token_max_age} seconds ({token_max_age // 86400} days)")

# Test token creation and validation
try:
    from app.core.auth import create_access_token, decode_access_token
    
    print("\n" + "-"*60)
    print("Testing Token Generation and Validation")
    print("-"*60)
    
    # Create a test token
    test_user_id = "test-user-123"
    test_role = "teacher"
    
    token = create_access_token(user_id=test_user_id, role=test_role)
    print(f"\n✓ Token created: {token[:50]}...")
    
    # Decode and validate
    payload = decode_access_token(token)
    print(f"✓ Token validated successfully")
    print(f"  - User ID: {payload.get('uid')}")
    print(f"  - Role: {payload.get('role')}")
    
    if payload.get('uid') == test_user_id and payload.get('role') == test_role:
        print("\n✅ AUTHENTICATION SYSTEM OK")
    else:
        print("\n❌ Token payload mismatch")
        sys.exit(1)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("Test Complete - Ready to test endpoints")
print("="*60 + "\n")
