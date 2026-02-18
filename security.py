from datetime import datetime, timedelta, UTC
from typing import Any, Union
import jwt
from pwdlib import PasswordHash
from config import settings

# --- HELPERS ---

# 1. Setup Password Hashing
password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    """
    Takes a plain text password (e.g., 'secret123') and returns a secure hash string.
    """
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies if a plain text password matches the stored hash.
    Returns True if valid, False otherwise.
    """
    return password_hash.verify(plain_password, hashed_password)

# 2. Setup JWT Logic
def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    """ 
    **Create JWT Access Token**
    
    Encodes user data (payload) into a JSON Web Token (JWT).
    
    **Payload claims:**
    - `sub` (Subject): User ID.
    - `exp` (Expiration): When the token becomes invalid.
    """
    to_encode = data.copy()

    # Calculate expiration time
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    
    # Sign the token using users SECRET_KEY and Algorithm (HS256)
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.secret_key.get_secret_value(), 
        algorithm=settings.algorithm
    )
    return encoded_jwt

def verify_access_token(token: str) -> Union[str, None]:
    """ 
    **Verify JWT Token**
    
    Decodes a token to ensure it hasn't been tampered with and is not expired.
    Returns the `user_id` (sub) if valid, or None if invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require": ["exp", "sub"]}, # Force check for expiration and subject
        )
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None