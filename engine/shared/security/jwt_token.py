from datetime import datetime, timezone
from jose import jwt
from engine.shared.config import get_settings

settings = get_settings()

SECRET_KEY = getattr(settings, "SECRET_KEY", "supersecretkey")
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
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
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
