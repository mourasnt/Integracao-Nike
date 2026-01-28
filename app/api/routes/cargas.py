from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db import get_db
from app.models.shipment import Shipment, ShipmentInvoice
from app.services.constants import VALID_CODES, VALID_CODES_SET
from app.api.deps.security import is_front, is_front_admin
from fastapi import Request
from loguru import logger
import json
from app.schemas.shipment import ShipmentListRead, ShipmentDetailRead, ShipmentStatusResponse, UploadXmlResponse
from app.utils.shipment_serializers import shipment_to_read
from app.services.shipment_status_service import ShipmentStatusService
from app.services.shipment_xml_service import ShipmentXmlService

router = APIRouter(prefix="/cargas")


@router.get("/", response_model=List[ShipmentListRead])
async def listar_cargas(current_user: str = Depends(is_front), db: AsyncSession = Depends(get_db)):

    q = select(Shipment).options(selectinload(Shipment.invoices))
    res = await db.execute(q)
    cargas = res.scalars().all()

    serialized = [shipment_to_read(c, include_locations=False) for c in cargas]
    return serialized


@router.get("/{carga_id}", response_model=ShipmentDetailRead)
async def obter_carga(carga_id: int,  current_user: str = Depends(is_front), db: AsyncSession = Depends(get_db)):
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
    current_user: str = Depends(is_front_admin),
    anexo: Optional[UploadFile] = File(None),
    new_status: Optional[str] = Form(None, description="Status from form data (multipart)"),
    recebedor: Optional[str] = Form(None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    content_type = request.headers.get("content-type", "") if request else ""
    logger.info(f"=== alterar_status endpoint ===")
    logger.info(f"carga_id: {carga_id}")
    logger.info(f"Content-Type: {content_type}")
    logger.info(f"new_status (Form): {new_status}, type: {type(new_status)}")
    logger.info(f"anexo: {anexo.filename if anexo else None}")
    logger.info(f"recebedor: {recebedor}")
    
    status_input = None
    
    # For JSON requests, read body directly from request (Body() doesn't work well with Form())
    if content_type.startswith("application/json"):
        try:
            body = await request.json()
            logger.info(f"Parsed JSON body: {body}")
            status_input = body
        except Exception as e:
            logger.error(f"Failed to parse JSON body: {e}")
    
    # For multipart form, use new_status field
    elif content_type.startswith("multipart/"):
        if new_status:
            logger.info(f"Parsing new_status from form: {new_status}")
            try:
                status_input = json.loads(new_status)
                logger.info(f"Successfully parsed new_status to: {status_input}")
            except Exception as e:
                logger.error(f"Failed to parse new_status as JSON: {e}")
                status_input = new_status
    
    logger.info(f"Final status_input: {status_input}, type: {type(status_input)}")
    
    service = ShipmentStatusService()
    payload = await service.parse_request(novo_status=status_input, recebedor_raw=recebedor, request=request)
    logger.info(f"Payload after parse_request: code={payload.code}")
    return await service.change_status(db=db, invoice_id=carga_id, payload=payload, anexo_file=anexo)

@router.post("/{carga_id}/upload-xml", response_model=UploadXmlResponse)
async def upload_xml(
    carga_id: int,
    xmls: Optional[list[UploadFile]] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(is_front_admin),
):
    service = ShipmentXmlService()
    return await service.upload_xmls(db=db, invoice_id=carga_id, xml_files=xmls)
