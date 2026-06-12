from datetime import datetime, timedelta, timezone
from jose import ExpiredSignatureError, JWTError, jwt
from engine.shared.config import get_settings
import bcrypt

settings = get_settings()

class JWTService:
    def __init__(self):
        self.secret = settings.JWT_SECRET
        self.algorithm = settings.JWT_ALGORITHM
        # Overriding with spec values as fallback if not in settings or enforcing them
        self.expiry = getattr(settings, "ACCESS_TOKEN_EXPIRE_MIN", 15)
        self.refresh_expiry_days = getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 30)


    def create_refresh_token(self, data: dict) -> str:
        """Generate a refresh token with 30 days expiry."""
        payload = data.copy()
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_expiry_days)
        payload.update({
            "exp": expire,
            "iat": now,
            "token_type": "refresh"
        })
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict:
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except Exception:
            return {}

    def verify_token(self, token: str, verify_exp: bool = True) -> dict:
        """Decode and verify token. Can ignore expiry if needed."""
        try:
            return jwt.decode(
                token, 
                self.secret, 
                algorithms=[self.algorithm],
                options={"verify_exp": verify_exp}
            )
        except ExpiredSignatureError:
            return {}
        except JWTError:
            return {}
        except Exception:
            return {}

    def create_access_token(self, data: dict, expires_delta: timedelta | None = None) -> tuple[str, datetime]:
        payload = data.copy()
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=self.expiry)
            
        payload.update({
            "exp": expire,
            "iat": now,
            "token_type": "access"
        })
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return token, expire

    def set_auth_cookies(self, response: __import__('fastapi').Response, access_token: str, refresh_token: str):
        """Attach access and refresh tokens to response cookies."""
        # Access token cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,     # True means HTTPS only, disable if testing locally without HTTPS
            samesite="lax",
            max_age=self.expiry * 60,  # Convert minutes to seconds
        )
        
        # Refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=self.refresh_expiry_days * 24 * 60 * 60,  # Convert days to seconds
        )

    def clear_auth_cookies(self, response: __import__('fastapi').Response):
        """Clear auth cookies on logout."""
        response.delete_cookie("access_token", httponly=True, secure=True, samesite="lax")
        response.delete_cookie("refresh_token", httponly=True, secure=True, samesite="lax")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Helper to delegate password verification to PasswordHelper."""
        return PasswordHelper.verify_password(plain_password, hashed_password)


class PasswordHelper:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.
        Supports:
        1. Legacy plain text comparison.
        2. Peppered bcrypt (new standard).
        3. Standard bcrypt (without pepper, for existing hashes).
        """
        if not plain_password or not hashed_password:
            return False

        # 1. Try direct match (legacy/manual placeholders)
        if plain_password == hashed_password:
            return True

        # 2. Try peppered bcrypt verification (new standard)
        peppered_password = settings.PASSWORD_SECRET + plain_password
        try:
            if bcrypt.checkpw(
                peppered_password.encode("utf-8"), 
                hashed_password.encode("utf-8")
            ):
                return True
        except Exception:
             pass

        # 3. Try standard bcrypt verification (un-peppered)
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"), 
                hashed_password.encode("utf-8")
            )
        except Exception:
            return False

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password using bcrypt and a secret pepper."""
        peppered_password = settings.PASSWORD_SECRET + password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(peppered_password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
