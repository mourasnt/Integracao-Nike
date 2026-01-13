from pydantic import BaseModel
import datetime
import uuid

class TrackingCreate(BaseModel):
    cte_cliente_id: uuid.UUID
    codigo_evento: str
    descricao: str
    data_evento: datetime.datetime

class TrackingRead(TrackingCreate):
    id: uuid.UUID
    
    class Config:
        from_attributes = True
