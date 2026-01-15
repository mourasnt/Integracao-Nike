from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from json import JSONDecodeError
from app.api.routes import router
from app.db import engine, Base

# Configure Loguru-based logging
from app.logging import configure_logging
from contextlib import asynccontextmanager

configure_logging(level="DEBUG")

@asynccontextmanager
async def lifespan(app: FastAPI):
    import app.models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            from app.models.user import User
            await conn.run_sync(User.__table__.create, checkfirst=True)
        except Exception:
            pass

    yield

app = FastAPI(title="Integração Nike Store - Notfis/JSON", lifespan=lifespan)


def _serialize_validation_errors(errors):
    sanitized = []
    for e in (errors or []):
        try:
            sanitized.append({
                "loc": e.get("loc"),
                "msg": str(e.get("msg")),
                "type": e.get("type"),
                "input": repr(e.get("input"))
            })
        except Exception:
            sanitized.append({"loc": e.get("loc"), "msg": str(e), "type": "error", "input": None})
    return sanitized


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    from loguru import logger
    try:

        if request.url.path == "/emissao":
            errors = exc.errors() or []
            first = errors[0] if errors else {}
            msg = first.get("msg", str(exc))

            loc = first.get("loc", [])
            logger.debug("Validation error for /emissao: {}", first)

            if isinstance(loc, (list, tuple)) and 'documentos' in loc:
                return JSONResponse(status_code=400, content={
                "message": "Falha ao processar solicitação",
                "status": 0,
                "data": [{"status": 0, "message": msg, "id": None}]
            })

            if isinstance(loc, (list, tuple)) and len(loc) > 0:
                field = loc[-1]
                if field == "nDoc":
                    msg = "Campo obrigatório 'nDoc' não informado"
                elif field == "chave":
                    msg = "Campo obrigatório 'chave' não informado"
                else:
                    msg = f"Campo '{field}' inválido: {msg}"
            return JSONResponse(status_code=400, content={
                "message": "Falha ao processar solicitação",
                "status": 0,
                "data": [{"status": 0, "message": msg, "id": None}]
            })

        logger.debug("Validation error for {}: {}", request.url.path, exc.errors())
        return JSONResponse(status_code=400, content={
            "message": "Falha ao processar solicitação",
            "status": 0,
            "data": [{"status": 0, "message": "Erro de validação", "id": None}]
        })
    except Exception as e:
        logger.exception("Unhandled exception in validation_exception_handler: {}", str(e))
        # Return a safe, spec-compatible error response instead of raising
        return JSONResponse(status_code=500, content={
            "message": "Falha ao processar solicitação",
            "status": 0,
            "data": [{"status": 0, "message": "Erro interno na validação", "id": None}]
        })


@app.exception_handler(JSONDecodeError)
async def json_decode_exception_handler(request: Request, exc: JSONDecodeError):
    from loguru import logger

    try:
        body = await request.body()
        logger.error('Invalid JSON received at %s: %s', request.url.path, body)
    except Exception as e:
        logger.exception('Failed to read request body for JSONDecodeError: %s', str(e))

    return JSONResponse(status_code=400, content={
        "message": "Falha ao processar solicitação",
        "status": 0,
        "data": [{"status": 0, "message": "JSON inválido", "id": None}]
    })


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    from loguru import logger

    logger.warning("HTTPException handled for %s: %s", request.url.path, exc)
    if exc.status_code in (401, 403):
        return JSONResponse(status_code=exc.status_code, content={
            "message": "Acesso não autorizado",
            "status": 0,
            "data": [{"status": 0, "message": "Acesso não autorizado", "id": None}]
        })

    return JSONResponse(status_code=exc.status_code, content={
        "message": str(exc.detail) or "Erro",
        "status": 0,
        "data": [{"status": 0, "message": str(exc.detail) or "Erro", "id": None}]
    })


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    from loguru import logger
    try:
        body = await request.body()
    except Exception:
        body = b"<failed to read body>"
    logger.exception("Unhandled exception on %s %s: %s -- body=%s", request.method, request.url.path, exc, body)
 
    return JSONResponse(status_code=500, content={
        "message": "Erro interno do servidor",
        "status": 0,
        "data": [{"status": 0, "message": "Erro interno do servidor", "id": None}]
    })

app.include_router(router)