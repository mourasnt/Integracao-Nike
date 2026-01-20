import os
import datetime
from typing import Optional, Tuple
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.shipment import ShipmentInvoiceTracking

from app.services.constants import VALID_CODES, VALID_CODES_SET


class TrackingService:
    """Combined tracking service: sends events to VBLOG-like endpoint and persists tracking records."""

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.usuario = os.getenv("BRUDAM_USUARIO")
        self.senha = os.getenv("BRUDAM_SENHA")
        self.endpoint = os.getenv("BRUDAM_URL_TRACKING")
        self.cliente = os.getenv("BRUDAM_CLIENTE")
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or getattr(self._client, "is_closed", False):
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    def montar_payload(
        self,
        chave_documento: str,
        codigo_evento: str,
        data_evento: Optional[datetime.datetime] = None,
        obs: Optional[str] = None,
        tipo: str = "NFE",
        anexos: Optional[list] = None,
    ) -> dict:

        # permissive validation
        data_fmt = (data_evento or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

        documento = {
            "cliente": self.cliente,
            "tipo": tipo if tipo else "PEDIDO",
            "chave": chave_documento,
            "eventos": [
                {
                    "codigo": int(codigo_evento),
                    "data": data_fmt,
                    "obs": obs or (VALID_CODES.get(codigo_evento, {}).get("message") if VALID_CODES else None),
                }
            ],
        }

        if anexos:
            documento["anexos"] = anexos

        return {"auth": {"usuario": self.usuario, "senha": self.senha}, "documentos": [documento]}

    async def enviar(
        self,
        chave_documento: str,
        codigo_evento: str,
        data_evento: Optional[datetime.datetime] = None,
        obs: Optional[str] = None,
        tipo: str = "NFE",
        anexos: Optional[list] = None,
    ) -> Tuple[bool, str]:

        payload = self.montar_payload(
            chave_documento=chave_documento,
            codigo_evento=codigo_evento,
            data_evento=data_evento,
            obs=obs,
            tipo=tipo,
            anexos=anexos,
        )

        client = await self._get_client()
        headers = {"Content-Type": "application/json"}

        resp = await client.post(self.endpoint, json=payload, headers=headers)
        text = resp.text
        print(text)
        success = resp.status_code < 300
        return success, text

    @staticmethod
    async def registrar(session: AsyncSession, shipment_invoice_id: int, codigo_evento: str, descricao: str | None = None, data_evento: Optional[datetime.datetime] = None):
        """Persist a tracking record in DB (async).

        Params:
            session: AsyncSession
            shipment_invoice_id: invoice id
            codigo_evento: event code (string)
            descricao: optional description
            data_evento: optional datetime
        """
        if data_evento is None:
            data_evento = datetime.datetime.now()
        tr = ShipmentInvoiceTracking(
            shipment_invoice_id=shipment_invoice_id,
            codigo_evento=str(codigo_evento),
            descricao=descricao,
            data_evento=data_evento,
        )
        session.add(tr)
        await session.commit()
        await session.refresh(tr)
        return tr
