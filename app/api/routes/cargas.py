from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db import get_db
from app.models.shipment import Shipment, ShipmentInvoice
from app.services.constants import VALID_CODES, VALID_CODES_SET
from app.services.vblog_tracking import VBlogTrackingService
from app.api.deps.security import get_current_user
from typing import Optional, Any
from pathlib import Path
import datetime
from fastapi import Request

router = APIRouter(prefix="/cargas")


@router.get("/", )
async def listar_cargas( current_user: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Shipment).options(selectinload(Shipment.invoices))
    res = await db.execute(q)
    cargas = res.scalars().all()

    def serialize(c):
        return {
            "id": c.id,
            "external_ref": c.external_ref,
            "service_code": c.service_code,
            "total_weight": c.total_weight,
            "total_value": float(c.total_value) if c.total_value is not None else None,
            "volumes_qty": c.volumes_qty,
            "invoices": [
                {
                    "id": i.id,
                    "access_key": i.access_key,
                    "cte_chave": i.cte_chave
                }
                for i in c.invoices
            ]
        }

    return [serialize(c) for c in cargas]


@router.get("/{carga_id}")
async def obter_carga(carga_id: int,  current_user: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Shipment).where(Shipment.id == carga_id).options(selectinload(Shipment.invoices))
    res = await db.execute(q)
    carga = res.scalars().first()
    if not carga:
        raise HTTPException(404, "Carga não encontrada")

    return {
        "id": carga.id,
        "external_ref": carga.external_ref,
        "service_code": carga.service_code,
        "total_weight": carga.total_weight,
        "total_value": float(carga.total_value) if carga.total_value is not None else None,
        "volumes_qty": carga.volumes_qty,
        "invoices": [
            {
                "id": i.id,
                "access_key": i.access_key,
                "cte_chave": i.cte_chave
            }
            for i in carga.invoices
        ]
    }

@router.post("/{carga_id}/status")
async def alterar_status(
    carga_id: int,
    novo_status: Optional[Any] = Body(None, example={"code": "1"}),
    anexo: Optional[UploadFile] = File(None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    # Note: OpenAPI shows `novo_status` (example with {"code":"1"}) and `anexo` (file). Internally we accept string or object for `novo_status` and also a hidden `anexos` JSON field.
    q = select(ShipmentInvoice).where(ShipmentInvoice.id == carga_id)
    res = await db.execute(q)
    carga = res.scalars().first()

    if not carga:
        raise HTTPException(404, "Carga não encontrada")

    anexos_input = None
    try:
        if request is not None and request.headers.get("content-type", "").startswith("application/json"):
            body = await request.json()
            if isinstance(body, dict):
                anexos_input = body.get("anexos")
    except Exception:
        anexos_input = None

    import json

    code_val = None

    if isinstance(novo_status, (str, int)):
        s = str(novo_status).strip()
        if s.startswith("{") or s.startswith("["):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, dict) and "code" in parsed:
                    code_val = str(parsed["code"])
            except Exception:
                pass
        if code_val is None:
            code_val = s

    elif isinstance(novo_status, dict):
        if "code" in novo_status:
            code_val = str(novo_status["code"])

    elif hasattr(novo_status, "code"):
        code_val = str(novo_status.code)

    if not code_val:
        raise HTTPException(400, "novo_status inválido: forneça apenas o código, ex: {\"novo_status\": \"1\"}")

    if code_val not in VALID_CODES_SET:
        raise HTTPException(400, "Código tracking inválido")

    code_to_send = code_val

    # Build full status model using domain model to auto-fill message/type
    from app.models.shipment import ShipmentStatus
    novo_status_model = ShipmentStatus(code=code_to_send)
    carga.status = novo_status_model.model_dump()

    if not code_to_send:
        # nada a enviar (ex.: PENDENTE ou status sem mapeamento)
        return {"status": "ok", "codigo_enviado": None}

    # Process attachments (single file `anexo` and JSON `anexos` if provided)
    from app.services.attachments_service import AttachmentService
    import base64
    import httpx

    attachment_svc = AttachmentService()

    anexos_final = []

    # single file from multipart/form-data (field 'anexo')
    if anexo:
        content = await anexo.read()
        saved = attachment_svc.save_file(content, original_name=getattr(anexo, "filename", None))
        b64 = base64.b64encode(content).decode()
        anexos_final.append({"arquivo": {"nome": saved["url"], "dados": b64}})

    # anexos from JSON body (not exposed in openapi schema)
    if anexos_input:
        for item in anexos_input:
            arquivo = item.get("arquivo", {})
            nome = arquivo.get("nome")
            dados = arquivo.get("dados")
            if dados:
                saved = attachment_svc.save_base64(dados, original_name=None)
                anexos_final.append({"arquivo": {"nome": saved["url"], "dados": dados}})
            elif nome and nome.startswith("http"):
                try:
                    async with httpx.AsyncClient() as client:
                        r = await client.get(nome)
                    if r.status_code < 300:
                        content = r.content
                        saved = attachment_svc.save_file(content, original_name=Path(nome).name)
                        b64 = base64.b64encode(content).decode()
                        anexos_final.append({"arquivo": {"nome": saved["url"], "dados": b64}})
                except Exception:
                    continue

    # Atualiza status interno
    db.commit()
    db.refresh(carga)

    # Envia tracking para cada CT-e da carga
    tv = VBlogTrackingService()  # usa env vars se não passar cnpj/token
    results = []
    
    # registrar tracking interno
    from app.schemas.tracking import TrackingCreate
    from app.services.tracking_service import TrackingService

    success, resp_text = await tv.enviar(carga.access_key, code_to_send, anexos=anexos_final)
    results.append({"cte": str(carga.id), "ok": success, "vblog_response": resp_text[:500]})

    TrackingService.registrar(
            db,
            TrackingCreate(
                shipment_invoice_id=carga.id,
                codigo_evento=code_to_send,
                descricao=VALID_CODES[code_to_send]["message"],
                data_evento=datetime.datetime.now(datetime.timezone.utc)
            )
        )

    return {"status": "ok", "codigo_enviado": code_to_send, "results": results}

@router.post("/{carga_id}/upload-xml")
async def upload_xml(
    carga_id: int,
    xmls: Optional[list[UploadFile]] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    q = select(ShipmentInvoice).where(ShipmentInvoice.id == carga_id)
    res = await db.execute(q)
    invoice = res.scalars().first()

    if not invoice:
        raise HTTPException(404, "Carga não encontrada")
    
    if not xmls or len(xmls) == 0:
        raise HTTPException(400, "Nenhum arquivo XML enviado")

    xmls_b64 = []
    for xml_file in xmls:
        content = await xml_file.read()
        import base64
        xml_b64 = base64.b64encode(content).decode('utf-8')
        xmls_b64.append(xml_b64)

    invoice.xmls_b64 = xmls_b64
    db.add(invoice)
    await db.commit()

    return {"status": "ok", "xmls_b64": xmls_b64}
