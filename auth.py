from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
import os

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from dotenv import load_dotenv
load_dotenv()

from database import get_db
from models import User
from schemas import TokenData

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        if DEBUG:
            print(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_refresh_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        if DEBUG:
            print(f"Refresh token verification failed: {e}")
        return None


def authenticate_user(db, username: str, password: str) -> Optional[User]:
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user
    except Exception as e:
        if DEBUG:
            print(f"Authentication error: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError as e:
            if DEBUG:
                try:
                    unverified = jwt.get_unverified_claims(token)
                except Exception:
                    unverified = None
                print("JWT decode error:", e)
                print("Unverified claims:", unverified)
            raise credentials_exception

        username: str = payload.get("sub")
        client_id: int = payload.get("client_id")
        role: str = payload.get("role")

        if username is None or client_id is None:
            raise credentials_exception

        token_data = TokenData(username=username, client_id=client_id, role=role)

    except HTTPException:
        raise
    except Exception:
        raise credentials_exception

    # Database lookup
    db_session = db() if callable(db) else db
    try:
        user = db_session.query(User).filter(
            User.username == token_data.username,
            User.client_id == token_data.client_id
        ).first()

        if user is None:
            raise credentials_exception
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")
        return user
    except HTTPException:
        raise
    except Exception as e:
        if DEBUG:
            print(f"DB error in get_current_user: {e}")
        raise credentials_exception


def require_role(allowed_roles: list):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


# Pre-built role dependencies
require_business_role = require_role(["business"])
require_any_role = require_role(["business", "user"])

async def get_optional_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Optional authentication dependency"""
    if not auth or not auth.credentials:
        return None
    try:
        # We call get_current_user logic but manually handle errors
        token = auth.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        client_id: int = payload.get("client_id")
        
        if username is None:
            return None
            
        user = db.query(User).filter(
            User.username == username,
            User.client_id == client_id
        ).first()
        
        if user and user.is_active:
            return user
        return None
    except Exception:
        return None
