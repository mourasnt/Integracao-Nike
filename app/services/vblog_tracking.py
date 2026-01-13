# app/services/vblog_tracking.py

import os
import datetime
from typing import Tuple, Optional
import httpx #type: ignore

from app.services.constants import VALID_CODES, VALID_CODES_SET


class VBlogTrackingService:
    def __init__(
        self,
        client: Optional[httpx.AsyncClient] = None
    ):
        self.usuario = os.getenv("BRUDAM_USUARIO")
        self.senha = os.getenv("BRUDAM_SENHA")
        self.endpoint = os.getenv("BRUDAM_URL_TRACKING")
        self.cliente = os.getenv("BRUDAM_CLIENTE")
        self._client = client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
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

        if codigo_evento not in VALID_CODES_SET:
            raise ValueError("Código BRUDAM inválido")

        data_fmt = (data_evento or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

        documento = {
            "cliente": self.cliente,
            "tipo": tipo if tipo else "PEDIDO",
            "chave": chave_documento,
            "eventos": [
                {
                    "codigo": int(codigo_evento),
                    "data": data_fmt,
                    "obs": obs or VALID_CODES[codigo_evento]["message"]
                }
            ]
        }

        # include anexos right after eventos when provided
        if anexos:
            documento["anexos"] = anexos

        return {
            "auth": {
                "usuario": self.usuario,
                "senha": self.senha
            },
            "documentos": [ documento ]
        }

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

        print(payload)
        resp = await client.post(self.endpoint, json=payload, headers=headers)
        text = resp.text

        # Sucesso = qualquer 200/201/204
        success = resp.status_code < 300

        return success, text