# app/services/carga_service.py

from sqlalchemy.orm import Session
from uuid import UUID

from app.models.carga import Carga
from app.schemas.carga import CargaCreate, CargaUpdate


class CargaService:

    @staticmethod
    def criar_carga(db: Session, data: CargaCreate) -> Carga:
        carga = Carga(**data.dict())
        db.add(carga)
        db.commit()
        db.refresh(carga)
        return carga

    @staticmethod
    def listar_cargas(db: Session):
        return db.query(Carga).all()

    @staticmethod
    def obter_por_id(db: Session, carga_id: UUID) -> Carga:
        return db.query(Carga).filter(Carga.id == carga_id).first()

    @staticmethod
    def atualizar_carga(db: Session, carga_id: UUID, data: CargaUpdate) -> Carga:
        carga = CargaService.obter_por_id(db, carga_id)
        if not carga:
            return None

        for campo, valor in data.dict(exclude_unset=True).items():
            setattr(carga, campo, valor)

        db.commit()
        db.refresh(carga)
        return carga

    @staticmethod
    def deletar_carga(db: Session, carga_id: UUID) -> bool:
        carga = CargaService.obter_por_id(db, carga_id)
        if not carga:
            return False
        db.delete(carga)
        db.commit()
        return True
