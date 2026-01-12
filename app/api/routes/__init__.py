from fastapi import APIRouter
from importlib import import_module

router = APIRouter()

# Lazy-include submodule routers to avoid circular imports at package init
def _include(name: str, prefix: str, tags: list[str]):
    mod = import_module(f".{name}", package=__package__)
    router.include_router(mod.router, prefix=prefix, tags=tags)

_include("auth", "", ["autenticacao"])
_include("emissao", "", ["emissao"])
_include("cargas", "", ["cargas"])
