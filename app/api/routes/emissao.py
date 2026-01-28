"""Endpoint de emissão de minutas (Notfis).

Este módulo contém o handler HTTP que recebe payloads Notfis e delega
o processamento ao EmissaoService.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db import get_db
from app.schemas.notfis import NotfisPayload
from app.schemas.emissao import EmissaoResponse
from app.api.deps.security import is_api_user
from app.services.emissao_service import EmissaoService


router = APIRouter()


@router.post("/emissao", response_model=EmissaoResponse)
async def receive_emission(
    payload: NotfisPayload,
    current_user: str = Depends(is_api_user),
    db: AsyncSession = Depends(get_db)
):
    
    # Validação de payload vazio
    if not payload.documentos:
        logger.warning("/emissao called with empty documentos by user=%s", current_user)
        return JSONResponse(
            status_code=400,
            content={
                "message": "Falha ao processar solicitação",
                "status": 0,
                "data": [{"status": 0, "message": "Nenhuma minuta para processar", "id": None}]
            }
        )
    
    try:
        # Delegar processamento ao service
        service = EmissaoService(db)
        result = await service.process_payload(payload, current_user)
        
        # Retornar com status HTTP apropriado
        return JSONResponse(
            status_code=result.get_http_status(),
            content=result.model_dump()
        )
        
    except Exception as e:
        logger.exception("Unhandled error in /emissao handler: %s", e)
        return JSONResponse(
            status_code=500,
            content={
                "message": "Erro interno do servidor",
                "status": 0,
                "data": [{"status": 0, "message": "Erro interno do servidor", "id": None}]
            }
        )
