from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

# jwt import with fallback for test environments where python-jose may not be installed
try:
    from jose import jwt
    _JWT_AVAILABLE = True
except Exception:
    _JWT_AVAILABLE = False
    import base64
    import json

    class _FallbackJWT:
        @staticmethod
        def encode(data, secret, algorithm=None):
            # Not secure — only for tests/local runs when jose is missing
            return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()

        @staticmethod
        def decode(token, secret, algorithms=None):
            try:
                return json.loads(base64.urlsafe_b64decode(token.encode()).decode())
            except Exception as e:
                raise e

    jwt = _FallbackJWT()


# Use HTTP Bearer for Swagger UI to accept a JWT token directly (no username/password)
bearer_scheme = HTTPBearer(auto_error=False)

def create_access_token(data: dict):
    try:
        from loguru import logger
        print("Creating access token for sub=%s", data.get('sub'))
    except Exception:
        pass
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    # Format as required: 2026-01-09T16:00:00-03-00
    expire_brasilia = expire.astimezone(timezone(timedelta(hours=-3)))
    expire_str = expire_brasilia.strftime("%Y-%m-%dT%H:%M:%S-03-00")

    to_encode = data.copy()
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm if _JWT_AVAILABLE else None)
    return encoded_jwt, expire_str


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    print("Attempting to authorize request via bearer token")
    if credentials is None or not credentials.credentials:
        print("No credentials presented in bearer token header")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm] if _JWT_AVAILABLE else None)
        username: str = payload.get("sub")
        if username is None:
            print("JWT valid but 'sub' missing: %s", payload)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        print("Authenticated user=%s via token", username)
        return username
    except Exception as e:
        print("Token decode failed: %s", str(e))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
