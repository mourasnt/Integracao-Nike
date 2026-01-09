from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from app.schemas.auth import AuthIn, AuthOut, AuthData
from app.api.deps.security import create_access_token
from app.models.user import User
from app.api.deps.hashing import verify_password
from app.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/autenticacao", response_model=AuthOut)
async def login(payload: AuthIn, db: AsyncSession = Depends(get_db)):
    from loguru import logger
    try:
        logger.debug("Attempting login for usuario=%s", payload.usuario)
        q = await db.execute(select(User).where(User.username == payload.usuario))
        user = q.scalars().first()
        if not user or not verify_password(payload.senha, user.password_hash):
            logger.warning("Failed login attempt for usuario=%s", payload.usuario)
            return AuthOut(message="Usuário ou senha incorretos", status=0, data=None)

        token, expire_str = create_access_token({"sub": user.username})
        logger.debug("User %s authenticated, token created, expire=%s", user.username, expire_str)
        data = AuthData(message="Autenticação realizada com sucesso.", access_key=token, expire_at=expire_str)
        return AuthOut(message="OK", status=1, data=data)

    except Exception as e:
        logger.exception("Unhandled error in /autenticacao: %s", e)
        # Return a spec-compliant failure payload (200 with status 0) to avoid exposing internals
        return AuthOut(message="Erro interno", status=0, data=None)
