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
    UF: Optional[str] = None
    municipioCodigoIbge: Optional[int] = None
    municipioNome: Optional[str] = None


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
