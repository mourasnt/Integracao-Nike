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
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm] if _JWT_AVAILABLE else None)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return username
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

async def is_front(current_user: str = Depends(get_current_user)):
    if current_user not in settings.front_users:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    return True

async def is_front_admin(current_user: str = Depends(get_current_user)):
    if current_user not in settings.front_admin_users:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    return True
