import os
import datetime
from typing import Optional, Tuple
import httpx
import json
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

        try:
            resp = await client.post(self.endpoint_login, json=payload, headers={"Content-Type": "application/json"})
            resp.raise_for_status()
            data = resp.json()
            token = data.get("data", {}).get("token")
            if not token:
                # Response was OK but token is missing: return useful debug info
                raise Exception(f"Brudam login: token not found in response: {resp.text}")
            return token
        except httpx.HTTPStatusError as e:
            # Extract response body for more details from Brudam
            body = None
            if getattr(e, "response", None) is not None:
                try:
                    body = e.response.json()
                except Exception:
                    body = e.response.text
                status = e.response.status_code
            else:
                body = str(e)
                status = "n/a"
            raise Exception(f"Brudam login failed: status={status} body={body}") from e
        except httpx.RequestError as e:
            # Network/timeout errors
            raise Exception(f"Brudam login request failed: {str(e)}") from e

    async def enviar(
        self,
        ctes_base64: list,
    ) -> Tuple[bool, str]:

        if not ctes_base64:
            return False, "no ctes provided"
        
        payload = ctes_base64

        client = await self._get_client()

        # login may raise Exception with useful message
        try:
            token = await self.login()
        except Exception as e:
            return False, f"login error: {e}"

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}

        try:
            resp = await client.post(self.endpoint, json=payload, headers=headers)
            # If status >= 400, capture body for debugging and return
            if resp.status_code >= 400:
                try:
                    body = resp.json()
                    body_text = json.dumps(body)
                except Exception:
                    body_text = resp.text
                return False, f"Brudam returned error: status={resp.status_code} body={body_text}"

            text = resp.text
            success = resp.status_code < 300
            return success, text
        except httpx.RequestError as e:
            # network/timeout/connection errors
            return False, f"request error: {str(e)}"