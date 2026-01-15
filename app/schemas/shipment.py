from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
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
