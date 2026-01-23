from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db import get_db
from app.models.shipment import Shipment, ShipmentInvoice
from app.services.constants import VALID_CODES, VALID_CODES_SET
from app.api.deps.security import get_current_user
from typing import Optional, Any, List
from fastapi import Request
from loguru import logger
from app.schemas.shipment import ShipmentListRead, ShipmentDetailRead, ShipmentStatusResponse, UploadXmlResponse
from app.utils.shipment_serializers import shipment_to_read
from app.services.shipment_status_service import ShipmentStatusService
from app.services.shipment_xml_service import ShipmentXmlService

router = APIRouter(prefix="/cargas")


@router.get("/", response_model=List[ShipmentListRead])
async def listar_cargas(current_user: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user != "integracao_logistica":
        raise HTTPException(403, "Acesso negado")

    q = select(Shipment).options(selectinload(Shipment.invoices))
    res = await db.execute(q)
    cargas = res.scalars().all()

    serialized = [shipment_to_read(c, include_locations=False) for c in cargas]
    return serialized


@router.get("/{carga_id}", response_model=ShipmentDetailRead)
async def obter_carga(carga_id: int,  current_user: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Shipment).where(Shipment.id == carga_id).options(selectinload(Shipment.invoices))
    res = await db.execute(q)
    carga = res.scalars().first()
    if not carga:
        logger.debug("obter_carga: carga id=%s not found (user=%s)", carga_id, current_user)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carga não encontrada")

    logger.debug("obter_carga: user=%s retrieved carga id=%s", current_user, carga.id)

    return shipment_to_read(carga, include_locations=True)

@router.post("/{carga_id}/status", response_model=ShipmentStatusResponse)
async def alterar_status(
    carga_id: int,
    novo_status: Optional[Any] = Body(
        None,
        description="Código do novo status (ex: {\"code\": \"1\"} ou \"1\")",
    ),
    current_user: str = Depends(get_current_user),
    anexo: Optional[UploadFile] = File(None),
    recebedor: Optional[str] = Form(None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    # Mantém compatibilidade de entrada: aceita code como string/objeto e recebedor via form ou JSON, com anexos opcionais
    service = ShipmentStatusService()
    payload = await service.parse_request(novo_status=novo_status, recebedor_raw=recebedor, request=request)
    return await service.change_status(db=db, invoice_id=carga_id, payload=payload, anexo_file=anexo)

@router.post("/{carga_id}/upload-xml", response_model=UploadXmlResponse)
async def upload_xml(
    carga_id: int,
    xmls: Optional[list[UploadFile]] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    service = ShipmentXmlService()
    return await service.upload_xmls(db=db, invoice_id=carga_id, xml_files=xmls)
