from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash,
    create_access_token, create_refresh_token, verify_token, get_current_user
)
from app.models.user import User
from app.schemas.schemas import UserCreate, UserLogin, TokenResponse, UserResponse
from app.services.audit_service import write_audit_log

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    write_audit_log(db, "USER_REGISTER", user.id, "user", str(user.id),
                    {"email": user.email}, request.client.host if request.client else None)

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id, "email": user.email, "username": user.username,
            "role": user.role, "preferred_mode": user.preferred_mode,
        }
    }


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    user.last_login = datetime.utcnow()
    db.commit()

    write_audit_log(db, "USER_LOGIN", user.id, "user", str(user.id),
                    {}, request.client.host if request.client else None)

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id, "email": user.email, "username": user.username,
            "role": user.role, "preferred_mode": user.preferred_mode,
        }
    }


@router.post("/refresh")
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    payload = verify_token(refresh_token, "refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    access_token = create_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me/mode")
async def update_mode(mode: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if mode not in ("simple", "learning", "developer"):
        raise HTTPException(status_code=400, detail="Invalid mode")
    current_user.preferred_mode = mode
    db.commit()
    return {"preferred_mode": mode}
