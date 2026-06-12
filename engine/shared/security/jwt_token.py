from datetime import datetime, timezone
from jose import jwt
from engine.shared.config import get_settings

settings = get_settings()

SERVICE_TOKEN_SECRET_KEY = getattr(settings, "service_token_secret_key", "dev-service-token-secret-key")
ALGORITHM = "HS256"

def create_service_account_token(user_id: str, user_name: str, expire_at: datetime) -> str:
    """
    Generates a JWT token that expires at the exact specified datetime and contains user_id.
    """
    # Ensure expire_at is UTC
    if expire_at.tzinfo is None:
        expire_at = expire_at.replace(tzinfo=timezone.utc)
        
    to_encode = {"sub": user_name, "user_id": str(user_id), "type": "service_account"}
    to_encode.update({"exp": int(expire_at.timestamp())})
    
    encoded_jwt = jwt.encode(to_encode, SERVICE_TOKEN_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_token_expiration(token: str) -> datetime:
    """
    Extracts the expiration datetime from an existing token, even if expired.
    """
    claims = jwt.get_unverified_claims(token)
    exp = claims.get("exp")
    if exp:
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    return datetime.now(timezone.utc)

import bcrypt
import hashlib

def hash_token(token: str) -> str:
    """
    Hashes a token using bcrypt. 
    Pre-hashes with SHA-256 to bypass bcrypt's 72-byte limit for long JWTs.
    """
    # Pre-hash the long JWT token to a fixed 64-character hex string
    token_sha256 = hashlib.sha256(token.encode('utf-8')).hexdigest()
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(token_sha256.encode('utf-8'), salt).decode('utf-8')
