import os
import datetime
from typing import Optional, Tuple
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.shipment import ShipmentInvoiceTracking

from app.services.constants import VALID_CODES, VALID_CODES_SET


class UploadCteService:

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.usuario = os.getenv("BRUDAM_USUARIO")
        self.senha = os.getenv("BRUDAM_SENHA")
        self.endpoint = os.getenv("BRUDAM_URL_UPLOAD_CTE")
        self.endpoint_login = os.getenv("BRUDAM_URL_LOGIN")
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or getattr(self._client, "is_closed", False):
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client
    
    async def login(self) -> str:

        client = await self._get_client()

        payload = {
            "usuario": self.usuario,
            "senha": self.senha
        }

        resp = await client.post(self.endpoint_login, json=payload, headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        data = resp.json()
        token = data.get("data").get("token")
        return token

    async def enviar(
        self,
        ctes_base64: list,
    ) -> Tuple[bool, str]:

        if not ctes_base64:
            return False
        
        payload = ctes_base64

        client = await self._get_client()

        token = await self.login()
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

        resp = await client.post(self.endpoint, json=payload, headers=headers)
        text = resp.text
        success = resp.status_code < 300
        return success, text