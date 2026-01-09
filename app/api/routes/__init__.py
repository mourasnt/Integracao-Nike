from fastapi import APIRouter

router = APIRouter()

from . import auth, emissao

# Explicitly include routers
router.include_router(auth.router, prefix="", tags=["autenticacao"])
router.include_router(emissao.router, prefix="", tags=["emissao"])
