import time
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import (
    AuthRegisterReq,
    AuthLoginReq,
    AuthResponse,
    AuthMeResponse,
)
from app.storage import create_user, get_user_by_email
from app.core.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(req: AuthRegisterReq):
    email = (req.email or "").strip().lower()
    password = (req.password or "").strip()
    role = (req.role or "student").strip().lower()

    print(f"\n[AUTH] Register attempt: email={email}, role={role}")

    if "@" not in email:
        print(f"[AUTH] Register failed: Invalid email format")
        raise HTTPException(400, "Valid email is required")
    if len(password) < 6:
        print(f"[AUTH] Register failed: Password too short")
        raise HTTPException(400, "Password must be at least 6 characters")
    if role not in ("student", "teacher"):
        print(f"[AUTH] Register failed: Invalid role={role}")
        raise HTTPException(400, "Role must be student or teacher")

    existing = get_user_by_email(email)
    if existing:
        print(f"[AUTH] Register failed: Email already registered")
        raise HTTPException(409, "Email already registered")

    user_id = str(uuid.uuid4())
    pw_hash = hash_password(password)
    try:
        create_user(user_id=user_id, email=email, password_hash=pw_hash, role=role, created_at=int(time.time()))
        print(f"[AUTH] User created: user_id={user_id}, email={email}, role={role}")
    except Exception as e:
        print(f"[AUTH] User creation failed: {repr(e)}")
        raise HTTPException(500, f"Registration failed: {str(e)}")

    token = create_access_token(user_id=user_id, role=role)
    print(f"[AUTH] Registration successful: token issued for {email}")
    return AuthResponse(access_token=token, user_id=user_id, email=email, role=role)


@router.post("/login", response_model=AuthResponse)
async def login(req: AuthLoginReq):
    email = (req.email or "").strip().lower()
    password = (req.password or "").strip()
    
    print(f"\n[AUTH] Login attempt: email={email}")
    
    user = get_user_by_email(email)
    if not user:
        print(f"[AUTH] Login failed: User not found")
        raise HTTPException(401, "Invalid credentials")
    
    if not verify_password(password, user["password_hash"]):
        print(f"[AUTH] Login failed: Invalid password")
        raise HTTPException(401, "Invalid credentials")

    token = create_access_token(user_id=user["id"], role=user["role"])
    print(f"[AUTH] Login successful: token issued for {email}, role={user['role']}")
    return AuthResponse(
        access_token=token,
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
    )


@router.get("/me", response_model=AuthMeResponse)
async def me(user=Depends(get_current_user)):
    print(f"[AUTH] Fetching current user: user_id={user['id']}")
    return AuthMeResponse(user_id=user["id"], email=user["email"], role=user["role"])

