from datetime import UTC, timedelta, datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash 
from config import settings
import models
from database import get_db
from schemas import Token

router = APIRouter()

password_hash = PasswordHash.recommended()
    
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/token")

# --- HELPERS ---

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password:str) -> bool:
    return password_hash.verify(plain_password, hashed_password) 

def create_access_token(data:dict, expires_delta: timedelta | None = None) -> str:
    """ Create a JWT access token """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes,
        )
    to_encode.update({"exp": expire})
    encode_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )

    return encode_jwt

def verify_access_token(token:str) -> str | None:
    """ Verify a JWT access token and return the subject (user_id) if valid"""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError:
        return None
    else:
        return payload.get("sub")
    

# --- ENDPOINT ---

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Standard OAuth2 Login Endpoint.
    1. Receives username/password (form_data).
    2. Checks DB.
    3. Returns JWT Token.
    """
    # NOTE: OAuth2PasswordRequestForm uses 'username' field, but we treat it as email. 
    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == form_data.username.lower())
    )
    user = result.scalars().first()

    # Auth
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate token
    access_token_expire = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expire,
    )
    
    return Token(access_token=access_token, token_type="bearer")

