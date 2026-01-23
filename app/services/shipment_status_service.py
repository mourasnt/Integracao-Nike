from __future__ import annotations

import base64
import datetime
import json
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.shipment import ShipmentInvoice
from app.schemas.shipment import (
    AttachmentIn,
    ShipmentStatus,
    ShipmentStatusRequest,
    ShipmentStatusResponse,
    ShipmentStatusResult,
)
from app.services.attachments_service import AttachmentService
from app.services.constants import VALID_CODES, VALID_CODES_SET
from app.services.tracking_service import TrackingService
from app.utils.db_utils import commit_or_raise


class ShipmentStatusService:
    def __init__(self, attachment_svc: Optional[AttachmentService] = None, tracking_svc: Optional[TrackingService] = None):
        self.attachment_svc = attachment_svc or AttachmentService()
        self.tracking_svc = tracking_svc or TrackingService()

    @staticmethod
    async def parse_request(
        novo_status: Optional[Any],
        recebedor_raw: Optional[Any],
        request,
    ) -> ShipmentStatusRequest:
        """Parse flexible status input (string/int/dict) plus recebedor/anexos from either JSON or form."""
        anexos_input = None
        recebedor_validado = None

        # Try to read JSON body when content-type is application/json
        if request is not None and request.headers.get("content-type", "").startswith("application/json"):
            try:
                body = await request.json()
                if isinstance(body, dict):
                    anexos_input = body.get("anexos") or None
                    if "recebedor" in body:
                        recebedor_raw = body.get("recebedor", recebedor_raw)
            except Exception:
                pass

        # Recebedor can arrive as dict or JSON string
        if isinstance(recebedor_raw, dict):
            recebedor_validado = recebedor_raw
        elif isinstance(recebedor_raw, str):
            try:
                recebedor_validado = json.loads(recebedor_raw)
            except Exception:
                recebedor_validado = None

        # Normalize status code
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

        # Validate early against known codes
        if code_val not in VALID_CODES_SET:
            raise HTTPException(400, "Código tracking inválido")

        # Let Pydantic perform final validation and structure
        return ShipmentStatusRequest(code=code_val, recebedor=recebedor_validado, anexos=anexos_input)

    async def change_status(
        self,
        db: AsyncSession,
        invoice_id: int,
        payload: ShipmentStatusRequest,
        anexo_file: Optional[UploadFile] = None,
    ) -> ShipmentStatusResponse:
        # Load invoice with parent shipment
        q = select(ShipmentInvoice).where(ShipmentInvoice.id == invoice_id).options(selectinload(ShipmentInvoice.shipment))
        res = await db.execute(q)
        invoice = res.scalars().first()
        if not invoice:
            raise HTTPException(404, "Carga não encontrada")

        # Build status model (auto fills message/type)
        novo_status_model = ShipmentStatus(code=payload.code)

        # Persist status on parent shipment if available
        if getattr(invoice, "shipment", None):
            invoice.shipment.status = novo_status_model.model_dump()
            db.add(invoice.shipment)

        # Collect attachments (from file upload and/or JSON payload)
        anexos_final = []
        anexos_final.extend(await self._from_payload(payload.anexos))
        anexos_final.extend(await self._from_file(anexo_file))

        # Attach recebedor into attachment payload if present
        recebedor_validado = payload.recebedor.dict() if hasattr(payload.recebedor, "dict") else payload.recebedor
        if recebedor_validado and len(anexos_final) > 0:
            for item in anexos_final:
                item["recebedor"] = recebedor_validado

        # Persist recebedor fields on shipment when provided
        if recebedor_validado and getattr(invoice, "shipment", None):
            self._persist_recebedor(invoice.shipment, recebedor_validado)
            db.add(invoice.shipment)
        elif recebedor_validado:
            # fallback to invoice dict in the unlikely absence of shipment relation
            invoice.__dict__["recebedor_nDoc"] = recebedor_validado.get("nDoc")
            invoice.__dict__["recebedor_xNome"] = recebedor_validado.get("xNome")
            invoice.__dict__["recebedor_nFone"] = recebedor_validado.get("nFone")

        await commit_or_raise(db)
        await db.refresh(invoice)

        # Fallback recebedor from DB if not provided
        if not recebedor_validado:
            recebedor_validado = self._recebedor_from_db(invoice)

        remetente_validado = getattr(invoice, "remetente_ndoc", None) or (
            invoice.shipment.rem_nDoc if getattr(invoice, "shipment", None) and getattr(invoice.shipment, "rem_nDoc", None) else None
        )

        # Send tracking
        success, resp_text = await self.tracking_svc.enviar(
            chave_documento=invoice.access_key,
            codigo_evento=payload.code,
            anexos=anexos_final,
            recebedor=recebedor_validado,
            remetente_cnpj=remetente_validado,
        )

        # Register internal tracking
        await self.tracking_svc.registrar(
            db,
            invoice.id,
            payload.code,
            descricao=VALID_CODES[payload.code]["message"],
            data_evento=datetime.datetime.now(datetime.timezone.utc),
        )

        return ShipmentStatusResponse(
            status="ok",
            codigo_enviado=payload.code,
            results=[ShipmentStatusResult(cte=str(invoice.id), ok=success, vblog_response=(resp_text or "")[:500])],
        )

    async def _from_file(self, anexo_file: Optional[UploadFile]):
        anexos = []
        if not anexo_file:
            return anexos
        content = await anexo_file.read()
        saved = self.attachment_svc.save_file(content, original_name=getattr(anexo_file, "filename", None))
        b64 = base64.b64encode(content).decode()
        anexos.append({"arquivo": {"nome": saved["url"], "dados": b64}})
        return anexos

    async def _from_payload(self, anexos_payload: Optional[list[AttachmentIn]]):
        anexos = []
        if not anexos_payload:
            return anexos

        # anexos_payload may come as list of dicts; rely on pydantic coercion when possible
        for item in anexos_payload:
            try:
                arquivo = item["arquivo"] if isinstance(item, dict) else getattr(item, "arquivo", {})
            except Exception:
                arquivo = {}

            nome = arquivo.get("nome") if isinstance(arquivo, dict) else getattr(arquivo, "nome", None)
            dados = arquivo.get("dados") if isinstance(arquivo, dict) else getattr(arquivo, "dados", None)

            if dados:
                saved = self.attachment_svc.save_base64(dados, original_name=None)
                anexos.append({"arquivo": {"nome": saved["url"], "dados": dados}})
            elif nome and str(nome).startswith("http"):
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(nome)
                    if resp.status_code < 300:
                        content = resp.content
                        saved = self.attachment_svc.save_file(content, original_name=Path(nome).name)
                        b64 = base64.b64encode(content).decode()
                        anexos.append({"arquivo": {"nome": saved["url"], "dados": b64}})
                except Exception:
                    continue
        return anexos

    @staticmethod
    def _persist_recebedor(shipment, recebedor: dict):
        shipment.recebedor_nDoc = recebedor.get("nDoc") or shipment.recebedor_nDoc
        shipment.recebedor_xNome = recebedor.get("xNome") or shipment.recebedor_xNome
        shipment.recebedor_IE = recebedor.get("IE") or shipment.recebedor_IE
        shipment.recebedor_cFiscal = recebedor.get("cFiscal") or shipment.recebedor_cFiscal
        shipment.recebedor_xLgr = recebedor.get("xLgr") or shipment.recebedor_xLgr
        shipment.recebedor_nro = recebedor.get("nro") or shipment.recebedor_nro
        shipment.recebedor_xCpl = recebedor.get("xCpl") or shipment.recebedor_xCpl
        shipment.recebedor_xBairro = recebedor.get("xBairro") or shipment.recebedor_xBairro
        shipment.recebedor_cMun = recebedor.get("cMun") or shipment.recebedor_cMun
        shipment.recebedor_CEP = recebedor.get("CEP") or shipment.recebedor_CEP
        shipment.recebedor_cPais = recebedor.get("cPais") or shipment.recebedor_cPais
        shipment.recebedor_nFone = recebedor.get("nFone") or shipment.recebedor_nFone
        shipment.recebedor_email = recebedor.get("email") or shipment.recebedor_email

    @staticmethod
    def _recebedor_from_db(invoice):
        try:
            db_r = {
                "nDoc": getattr(invoice, "recebedor_nDoc", None),
                "xNome": getattr(invoice, "recebedor_xNome", None),
                "IE": getattr(invoice, "recebedor_IE", None),
                "cFiscal": getattr(invoice, "recebedor_cFiscal", None),
                "xLgr": getattr(invoice, "recebedor_xLgr", None),
                "nro": getattr(invoice, "recebedor_nro", None),
                "xCpl": getattr(invoice, "recebedor_xCpl", None),
                "xBairro": getattr(invoice, "recebedor_xBairro", None),
                "cMun": getattr(invoice, "recebedor_cMun", None),
                "CEP": getattr(invoice, "recebedor_CEP", None),
                "cPais": getattr(invoice, "recebedor_cPais", None),
                "nFone": getattr(invoice, "recebedor_nFone", None),
                "email": getattr(invoice, "recebedor_email", None),
            }
            if db_r.get("nDoc") or db_r.get("xNome"):
                return db_r
        except Exception:
            return None
        return None
