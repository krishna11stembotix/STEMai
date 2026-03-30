import os
import hmac
import time
import base64
import hashlib
from typing import Optional

from fastapi import Header, HTTPException
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.storage import get_user_by_id


AUTH_SECRET = os.getenv("AUTH_SECRET", "change-me-in-production")
AUTH_SALT = "stembotix-auth"
TOKEN_MAX_AGE = int(os.getenv("AUTH_TOKEN_MAX_AGE_SECONDS", "604800"))  # 7 days


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key=AUTH_SECRET, salt=AUTH_SALT)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"{base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        salt_b64, digest_b64 = encoded.split("$", 1)
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def create_access_token(user_id: str, role: str) -> str:
    payload = {"uid": user_id, "role": role, "iat": int(time.time())}
    return _serializer().dumps(payload)


def decode_access_token(token: str) -> dict:
    try:
        print(f"[AUTH-DEBUG] Decoding token (first 20 chars): {token[:20]}...")
        print(f"[AUTH-DEBUG] AUTH_SECRET: {AUTH_SECRET[:10]}..., AUTH_SALT: {AUTH_SALT}")
        print(f"[AUTH-DEBUG] TOKEN_MAX_AGE: {TOKEN_MAX_AGE}s")
        payload = _serializer().loads(token, max_age=TOKEN_MAX_AGE)
        print(f"[AUTH-DEBUG] Token decoded successfully: {payload}")
        if not isinstance(payload, dict):
            raise ValueError("Invalid token payload")
        if payload.get("role") not in ("student", "teacher"):
            raise ValueError("Invalid role")
        return payload
    except SignatureExpired as e:
        print(f"[AUTH-DEBUG] Token expired: {e}")
        raise HTTPException(status_code=401, detail="Token expired")
    except BadSignature as e:
        print(f"[AUTH-DEBUG] Bad signature: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except ValueError as e:
        print(f"[AUTH-DEBUG] Value error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(authorization: Optional[str] = Header(default=None)):
    print(f"[AUTH-DEBUG] get_current_user called")
    print(f"[AUTH-DEBUG] Authorization header: {authorization[:50] if authorization else 'NONE'}...")
    if not authorization or not authorization.lower().startswith("bearer "):
        print(f"[AUTH-DEBUG] Missing or malformed bearer token")
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    print(f"[AUTH-DEBUG] Extracted token length: {len(token)}")
    payload = decode_access_token(token)
    user = get_user_by_id(payload["uid"])
    if not user:
        print(f"[AUTH-DEBUG] User not found for uid: {payload.get('uid')}")
        raise HTTPException(status_code=401, detail="User not found")
    print(f"[AUTH-DEBUG] User authenticated: {user.get('email', 'unknown')}")
    return user

