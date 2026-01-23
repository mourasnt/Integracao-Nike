from pydantic import BaseModel, field_validator, model_validator

# EmailStr optionally requires the "email-validator" package. Provide a safe
# fallback (str) when the package is not installed so tests and environments
# without that optional dependency still import successfully.
try:
    from pydantic import EmailStr  # type: ignore
except Exception:
    EmailStr = str  # type: ignore
from typing import Optional, List
from datetime import datetime
from app.services.constants import VALID_CODES


class ShipmentStatus(BaseModel):
    code: str
    message: Optional[str] = None
    type: Optional[str] = None

    @field_validator("code")
    def validate_code(cls, v):
        if v not in VALID_CODES:
            raise ValueError(f"Código de status inválido: {v}")
        return v

    @model_validator(mode="after")
    def fill_from_code(self):
        info = VALID_CODES.get(self.code)
        if info:
            if not self.message:
                self.message = info.get("message")
            if not self.type:
                self.type = info.get("type")
        return self


class AttachmentFile(BaseModel):
    nome: Optional[str] = None
    dados: Optional[str] = None


class AttachmentIn(BaseModel):
    arquivo: AttachmentFile


class ShipmentStatusResult(BaseModel):
    cte: str
    ok: bool
    vblog_response: Optional[str] = None


class ShipmentStatusResponse(BaseModel):
    status: str
    codigo_enviado: Optional[str] = None
    results: List[ShipmentStatusResult] = []


class ActorOut(BaseModel):
    nDoc: Optional[str] = None
    IE: Optional[str] = None
    cFiscal: Optional[int] = None
    xNome: Optional[str] = None
    xFant: Optional[str] = None
    xLgr: Optional[str] = None
    nro: Optional[str] = None
    xCpl: Optional[str] = None
    xBairro: Optional[str] = None
    cMun: Optional[str] = None
    CEP: Optional[str] = None
    cPais: Optional[int] = None
    nFone: Optional[str] = None
    email: Optional[str] = None

    # Normalized location fields
    UF: Optional[str] = None
    municipioCodigoIbge: Optional[int] = None
    municipioNome: Optional[str] = None


class HorariosOut(BaseModel):
    et_origem: Optional[datetime] = None
    chegada_coleta: Optional[datetime] = None
    saida_coleta: Optional[datetime] = None
    eta_destino: Optional[datetime] = None
    chegada_destino: Optional[datetime] = None
    finalizacao: Optional[datetime] = None


class LocationOut(BaseModel):
    uf: Optional[str] = None
    municipio: Optional[str] = None

    class Config:
        from_attributes = True


class ShipmentInvoiceOut(BaseModel):
    id: int
    access_key: Optional[str] = None
    cte_chave: Optional[str] = None
    remetente_ndoc: Optional[str] = None

    class Config:
        from_attributes = True


class ShipmentRead(BaseModel):
    id: int
    external_ref: Optional[str] = None
    service_code: Optional[str] = None
    total_weight: Optional[float] = None
    total_value: Optional[float] = None
    volumes_qty: Optional[int] = None
    rem: Optional[ActorOut] = None
    dest: Optional[ActorOut] = None
    recebedor: Optional[ActorOut] = None
    toma: Optional[ActorOut] = None
    horarios: Optional[HorariosOut] = None
    origem: Optional[LocationOut] = None
    destino: Optional[LocationOut] = None
    invoices: List[ShipmentInvoiceOut] = []

    class Config:
        from_attributes = True


class ShipmentListRead(ShipmentRead):
    """Alias for list responses; kept for clarity/forward extension."""
    pass


class ShipmentDetailRead(ShipmentRead):
    """Alias for detail responses; kept for clarity/forward extension."""
    pass


class RecebedorIn(ActorOut):
    """Input model for recebedor; extends ActorOut for reuse."""
    pass


class ShipmentStatusRequest(BaseModel):
    code: str
    recebedor: Optional[RecebedorIn] = None
    anexos: Optional[List[AttachmentIn]] = None

    @field_validator("code")
    def validate_code(cls, v):
        if v not in VALID_CODES:
            raise ValueError(f"Código de status inválido: {v}")
        return v


class UploadXmlResponse(BaseModel):
    status: bool
    cte_chave: Optional[str] = None
    xmls_b64: List[str]
    upload_response: Optional[str] = None
