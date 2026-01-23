from __future__ import annotations

import base64
import re
import xml.etree.ElementTree as ET
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shipment import ShipmentInvoice
from app.schemas.shipment import UploadXmlResponse
from app.services.upload_cte_service import BrudamError, UploadCteService


class ShipmentXmlService:
    """Service for handling XML upload and CTe processing."""

    def __init__(self, upload_cte_svc: Optional[UploadCteService] = None):
        self.upload_cte_svc = upload_cte_svc or UploadCteService()

    @staticmethod
    def extract_chave_from_cte_bytes(content_bytes: bytes) -> Optional[str]:
        """Extract chCTe from CTe XML bytes using multiple strategies."""
        try:
            text = content_bytes.decode("utf-8")
        except Exception:
            try:
                text = content_bytes.decode("latin1")
            except Exception:
                text = None

        if not text:
            return None

        # Try quick regex for <chCTe>
        m = re.search(r"<chCTe>(\d{44})</chCTe>", text)
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
                if el.tag.endswith("chCTe") and (el.text and el.text.strip()):
                    return el.text.strip()
        except Exception:
            pass

        return None

    async def upload_xmls(
        self,
        db: AsyncSession,
        invoice_id: int,
        xml_files: list[UploadFile],
    ) -> UploadXmlResponse:
        """Process XML files, extract chave, persist to DB, and send to Brudam."""
        # Load invoice
        q = select(ShipmentInvoice).where(ShipmentInvoice.id == invoice_id)
        res = await db.execute(q)
        invoice = res.scalars().first()

        if not invoice:
            raise HTTPException(404, "Carga não encontrada")

        if not xml_files or len(xml_files) == 0:
            raise HTTPException(400, "Nenhum arquivo XML enviado")

        xmls_b64 = []
        found_chaves = []

        # Encode and extract chaves from all files
        for xml_file in xml_files:
            content = await xml_file.read()
            xml_b64 = base64.b64encode(content).decode("utf-8")
            xmls_b64.append(xml_b64)

            chave = self.extract_chave_from_cte_bytes(content)
            if chave:
                found_chaves.append(chave)

        # Save XMLs and detected chave (first found) to DB
        invoice.xmls_b64 = xmls_b64
        if found_chaves:
            invoice.cte_chave = found_chaves[0]
        db.add(invoice)
        await db.commit()

        # Send to Brudam
        try:
            success, resp_text = await self.upload_cte_svc.enviar(xmls_b64)
        except BrudamError as e:
            status_code = 400 if isinstance(e.status, int) and 400 <= e.status < 500 else 502
            detail = {
                "message": str(e.message or "Brudam error"),
                "brudam_status": e.status,
                "brudam_body": e.body,
            }
            raise HTTPException(status_code=status_code, detail=detail)

        return UploadXmlResponse(
            status=success,
            cte_chave=invoice.cte_chave,
            xmls_b64=xmls_b64,
            upload_response=resp_text,
        )
