# app/services/carga_service.py

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.models.carga import Carga
from app.schemas.carga import CargaCreate, CargaUpdate


class CargaService:

    @staticmethod
    async def criar_carga(db: AsyncSession, data: CargaCreate) -> Carga:
        carga = Carga(**data.model_dump() if hasattr(data, 'model_dump') else data.dict())
        db.add(carga)
        await db.commit()
        await db.refresh(carga)
        return carga

    @staticmethod
    async def listar_cargas(db: AsyncSession):
        q = await db.execute(select(Carga))
        return q.scalars().all()

    @staticmethod
    async def obter_por_id(db: AsyncSession, carga_id: UUID) -> Carga:
        return await db.get(Carga, carga_id)

    @staticmethod
    async def atualizar_carga(db: AsyncSession, carga_id: UUID, data: CargaUpdate) -> Carga:
        carga = await CargaService.obter_por_id(db, carga_id)
        if not carga:
            return None

        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(carga, campo, valor)

        await db.commit()
        await db.refresh(carga)
        return carga

    @staticmethod
    async def deletar_carga(db: AsyncSession, carga_id: UUID) -> bool:
        carga = await CargaService.obter_por_id(db, carga_id)
        if not carga:
            return False
        await db.delete(carga)
        await db.commit()
        return True
