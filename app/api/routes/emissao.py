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
from app.api.deps.security import get_current_user
from app.services.emissao_service import EmissaoService


router = APIRouter()


@router.post("/emissao", response_model=EmissaoResponse)
async def receive_emission(
    payload: NotfisPayload,
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Recebe um payload Notfis e persiste cada minuta e suas notas.
    
    Regras principais:
    - Autenticação via JWT obrigatória
    - Validação de campos via Pydantic (cServ, nDoc, chave, etc)
    - Transação isolada por minuta (falha em uma não afeta as outras)
    - Enriquecimento de localidades (best-effort)
    
    Returns:
        200: Todas minutas processadas com sucesso
        207: Sucesso parcial (algumas minutas falharam)
        400: Todas minutas falharam ou payload vazio
        500: Erro interno do servidor
    """
    logger.debug("/emissao called by user=%s", current_user)
    
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
