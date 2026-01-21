import uuid
from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, DeclarativeBase
from geoalchemy2 import Geometry  # Para tipos de dados espaciais

# Base declarativa para as classes
class Base(DeclarativeBase):
    pass

class Estado(Base):
    __tablename__ = "estados"
    
    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo_ibge = Column(Integer, unique=True, index=True, nullable=False)
    sigla = Column(String(length=2), nullable=False)
    nome = Column(String, nullable=False)

    municipios = relationship("Municipio", back_populates="estado", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Estado(uuid={self.uuid}, sigla='{self.sigla}', nome='{self.nome}')>"

class Municipio(Base):
    __tablename__ = "municipios"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo_ibge = Column(Integer, unique=True, index=True, nullable=False)
    nome = Column(String, nullable=False)
    estado_uuid = Column(UUID(as_uuid=True), ForeignKey("estados.uuid", ondelete="CASCADE"), nullable=False)

    # Geometria MULTIPOLYGON no PostGIS (SRID 3857 - métrico)
    geometria = Column(Geometry(geometry_type='MULTIPOLYGON', srid=3857), nullable=True)

    estado = relationship("Estado", back_populates="municipios")

    def __repr__(self):
        return f"<Municipio(uuid={self.uuid}, nome='{self.nome}', codigo_ibge={self.codigo_ibge})>"
