from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
# imports do seu projeto (get_db, get_current_user, Prefat, etc)

router = APIRouter()

# --- Modelos Pydantic para Validação ---

class HttpInfo(BaseModel):
    url: str

class DataPayload(BaseModel):
    http: HttpInfo

class PrefatRequest(BaseModel):
    layout: str
    data: DataPayload