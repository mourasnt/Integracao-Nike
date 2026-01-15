from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models.prefat import Prefat
from app.api.deps.security import get_current_user
from app.schemas.prefat import PrefatRequest
import base64
import httpx

router = APIRouter()

@router.get("/prefat")
async def get_prefat(db: AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)):
    q = select(Prefat)
    res = await db.execute(q)
    prefats = res.scalars().all()

    def serialize(p):
        return {
            "id": p.id,
            "prefat_base64": p.prefat_base64,
            "created_at": p.created_at.isoformat()
        }

    return [serialize(p) for p in prefats]

@router.get("/prefat/{prefat_id}")
async def get_prefat_by_id(prefat_id: int, db: AsyncSession = Depends(get_db), current_user: str = Depends(get_current_user)):
    prefat = await db.get(Prefat, prefat_id)
    if not prefat:
        return {"error": "Prefat not found"}

    return {
        "id": prefat.id,
        "prefat_base64": prefat.prefat_base64,
        "created_at": prefat.created_at.isoformat()
    }

@router.post("/prefat")
async def create_prefat(
    request: PrefatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    try:
        layout_recebido = request.layout
        url_recebida = request.data.http.url

        if layout_recebido != "PROCEDA50":
            return {
                "code": 0,
                "message": "Layout inválido",
                "status": False
            }
        
        if not url_recebida:
            return {
                "code": 0,
                "message": "URL inválida",
                "status": False
            }

        async with httpx.AsyncClient() as client:
            response = await client.get(url_recebida)
            response.raise_for_status()
            
            file_content = response.content

        encoded_string = base64.b64encode(file_content).decode('utf-8')


        new_prefat = Prefat(
            prefat_base64=encoded_string
        )
        
        db.add(new_prefat)
        await db.commit()
        await db.refresh(new_prefat)
        
        return {
            "code": 1,
            "message": "Arquivo recebido com sucesso",
            "status": True
        }
    
    except Exception as e:
        await db.rollback()
        print(f"Erro ao criar prefat: {e}")
        return {
            "code": 0,
            "message": "Erro na recepção dos arquivos",
            "status": False
        }