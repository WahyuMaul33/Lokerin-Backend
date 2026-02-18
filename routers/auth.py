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
from security import verify_password, create_access_token

router = APIRouter()

# Defines where the user sends their credentials to get a token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/token")

# --- AUTH ENDPOINT ---

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    **Login Endpoint (OAuth2 Standard)**
    
    1. Receives `username` (email) and `password` via form-data.
    2. Verifies credentials against the database.
    3. If valid, issues a JWT Bearer Token.
    
    **Note:** OAuth2PasswordRequestForm uses 'username' field, but we treat it as email.
    """
    # 1. Fetch User
    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == form_data.username.lower())
    )
    user = result.scalars().first()

    # 2. Validate Credentials (using helper from security.py)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Generate Token (using helper from security.py)
    access_token_expire = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expire,
    )
    
    return Token(access_token=access_token, token_type="bearer")


