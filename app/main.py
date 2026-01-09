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
    # Import models to ensure all tables are registered in Base.metadata
    # (avoids missing tables if a model module hasn't been imported yet)
    import app.models  # noqa: F401

    # Ensure DB schema exists for tests and local runs
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Explicitly ensure `users_api` exists in case of metadata import ordering issues
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
        # For the /emissao endpoint we need to return a 200 with the client's spec
        if request.url.path == "/emissao":
            errors = exc.errors() or []
            first = errors[0] if errors else {}
            msg = first.get("msg", str(exc))
            # If the missing field is present in the location, make a clearer message
            loc = first.get("loc", [])
            logger.debug("Validation error for /emissao: {}", first)

            # If the root 'documentos' is missing, return 422 (test expects 400/422 for missing payload)
            if isinstance(loc, (list, tuple)) and 'documentos' in loc:
                return JSONResponse(status_code=422, content={"detail": _serialize_validation_errors(errors)})
            if 'Lista de minutas vazia' in msg:
                return JSONResponse(status_code=422, content={"detail": _serialize_validation_errors(errors)})

            if isinstance(loc, (list, tuple)) and len(loc) > 0:
                field = loc[-1]
                if field == "nDoc":
                    msg = "Campo obrigatório 'nDoc' não informado"
                elif field == "chave":
                    msg = "Campo obrigatório 'chave' não informado"
                else:
                    msg = f"Campo '{field}' inválido: {msg}"
            return JSONResponse(status_code=200, content={
                "message": "Falha ao processar solicitação",
                "status": 0,
                "data": [{"status": 0, "message": msg, "id": None}]
            })

        # Otherwise preserve default behavior (422) so auth endpoints return standard validation errors
        logger.debug("Validation error for {}: {}", request.url.path, exc.errors())
        return JSONResponse(status_code=422, content={"detail": _serialize_validation_errors(exc.errors())})
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
    # Log the raw body for auditing if possible
    try:
        body = await request.body()
        logger.error('Invalid JSON received at %s: %s', request.url.path, body)
    except Exception as e:
        logger.exception('Failed to read request body for JSONDecodeError: %s', str(e))

    return JSONResponse(status_code=200, content={
        "message": "Falha ao processar solicitação",
        "status": 0,
        "data": [{"status": 0, "message": "JSON inválido", "id": None}]
    })


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    from loguru import logger
    # For authorization errors we want to return the actual HTTP status (401/403)
    logger.warning("HTTPException handled for %s: %s", request.url.path, exc)
    if exc.status_code in (401, 403):
        return JSONResponse(status_code=exc.status_code, content={
            "message": "Acesso não autorizado",
            "status": 0,
            "data": [{"status": 0, "message": "Acesso não autorizado", "id": None}]
        })

    # Other HTTP errors — return structured error
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
    # Return a spec-aligned error payload but keep HTTP 500 to highlight server error
    return JSONResponse(status_code=500, content={
        "message": "Erro interno do servidor",
        "status": 0,
        "data": [{"status": 0, "message": "Erro interno do servidor", "id": None}]
    })

app.include_router(router)
