from datetime import datetime, timedelta, timezone
from jose import ExpiredSignatureError, JWTError, jwt
from engine.shared.config import get_settings
import bcrypt

settings = get_settings()

class JWTService:
    def __init__(self):
        self.secret = settings.JWT_SECRET
        self.algorithm = settings.JWT_ALGORITHM
        self.expiry = settings.ACCESS_TOKEN_EXPIRE_MIN
        self.refresh_expiry = settings.REFRESH_TOKEN_EXPIRE_MIN


    def create_refresh_token(self, data: dict) -> str:
        """Generate a refresh token with 30 min expiry."""
        payload = data.copy()
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.refresh_expiry)
        payload.update({
            "exp": expire,
            "iat": now,
            "type": "refresh"
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
            "type": "access"
        })
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return token, expire

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
