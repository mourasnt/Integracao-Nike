from fastapi import APIRouter, Depends, HTTPException, Body, File, UploadFile, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db import get_db
from app.models.shipment import Shipment, ShipmentInvoice
from app.services.constants import VALID_CODES, VALID_CODES_SET
from app.services.tracking_service import TrackingService
from app.api.deps.security import get_current_user
from typing import Optional, Any, Dict
from pathlib import Path
import datetime
from fastapi import Request
from app.services.upload_cte_service import UploadCteService, BrudamError
import base64
import xml.etree.ElementTree as ET
import re
from app.utils.db_utils import commit_or_raise
from app.services.attachments_service import AttachmentService
import base64
import httpx
import json

router = APIRouter(prefix="/cargas")


@router.get("/", )
async def listar_cargas( current_user: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user != "integracao_logistica":
        raise HTTPException(403, "Acesso negado")

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

    print(current_user)
    return [serialize(c) for c in cargas]


@router.get("/{carga_id}")
async def obter_carga(carga_id: int,  current_user: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Shipment).where(Shipment.id == carga_id).options(selectinload(Shipment.invoices))
    res = await db.execute(q)
    carga = res.scalars().first()
    if not carga:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

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
    novo_status: Optional[Any] = Body(
        None,
        description="Código do novo status (ex: {\"code\": \"1\"} ou \"1\")",
    ),
    anexo: Optional[UploadFile] = File(None),
    recebedor: Optional[str] = Form(None),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    # Note: OpenAPI shows `novo_status` (examples with {"code":"1"}) and `anexo` (file). Internally we accept string or object for `novo_status` and also a hidden `anexos` JSON field.
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

    code_val = None

    recebedor_validado = None

    # Support `recebedor` from either a form field (multipart/form-data) as a JSON string
    # or from an application/json body where `recebedor` can be a dict or JSON string.
    recebedor_input = recebedor
    if request is not None and request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = await request.json()
            if isinstance(body, dict) and "recebedor" in body:
                recebedor_input = body.get("recebedor")
        except Exception:
            pass

    if isinstance(recebedor_input, dict):
        recebedor_validado = recebedor_input
    elif isinstance(recebedor_input, str):
        try:
            recebedor_validado = json.loads(recebedor_input)
        except Exception:
            recebedor_validado = None

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
    from app.schemas.shipment import ShipmentStatus
    novo_status_model = ShipmentStatus(code=code_to_send)
    carga.status = novo_status_model.model_dump()

    if not code_to_send:
        # nada a enviar (ex.: PENDENTE ou status sem mapeamento)
        return {"status": "ok", "codigo_enviado": None}

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
        
    await commit_or_raise(db)
    await db.refresh(carga)

    # Envia tracking
    tv = TrackingService()  # uses env vars if not provided
    results = []

    success, resp_text = await tv.enviar(carga.access_key, code_to_send, anexos=anexos_final, recebedor=recebedor_validado)
    results.append({"cte": str(carga.id), "ok": success, "vblog_response": resp_text[:500]})

    # registrar tracking interno
    await tv.registrar(
        db,
        carga.id,
        code_to_send,
        descricao=VALID_CODES[code_to_send]["message"],
        data_evento=datetime.datetime.now(datetime.timezone.utc)
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
    found_chaves = []

    def extract_chave_from_cte_bytes(content_bytes: bytes) -> Optional[str]:
        try:
            text = content_bytes.decode('utf-8')
        except Exception:
            try:
                text = content_bytes.decode('latin1')
            except Exception:
                text = None
        if not text:
            return None
        # Try quick regex for <chCTe>
        m = re.search(r'<chCTe>(\d{44})</chCTe>', text)
        if m:
            return m.group(1)
        # Fallback to Id="CTe<44digits>"
        m = re.search(r'Id\s*=\s*"CTe(\d{44})"', text)
        if m:
            return m.group(1)
        # Try parsing and searching by tag-suffix (handles namespaces)
        try:
            root = ET.fromstring(text)
            for el in root.iter():
                if el.tag.endswith('chCTe') and (el.text and el.text.strip()):
                    return el.text.strip()
        except Exception:
            pass
        return None

    for xml_file in xmls:
        content = await xml_file.read()
        xml_b64 = base64.b64encode(content).decode('utf-8')
        xmls_b64.append(xml_b64)

        chave = extract_chave_from_cte_bytes(content)
        if chave:
            found_chaves.append(chave)

    # Save XMLs and detected chave (first found) to DB
    invoice.xmls_b64 = xmls_b64
    if found_chaves:
        invoice.cte_chave = found_chaves[0]
    db.add(invoice)
    await db.commit()

    upload_svc = UploadCteService()

    try:
        success, resp_text = await upload_svc.enviar(xmls_b64)
    except BrudamError as e:
        status_code = 400 if isinstance(e.status, int) and 400 <= e.status < 500 else 502
        detail = {"message": str(e.message or "Brudam error"), "brudam_status": e.status, "brudam_body": e.body}
        raise HTTPException(status_code=status_code, detail=detail)

    return {"status": success, "cte_chave": invoice.cte_chave, "xmls_b64": xmls_b64, "upload_response": resp_text}
