from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Float, Numeric, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base
from pydantic import BaseModel, field_validator, model_validator
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
    

class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    external_ref = Column(String(255), nullable=True)
    integration_date = Column(DateTime(timezone=True), server_default=func.now())

    # Minuta fields
    service_code = Column(String(50), nullable=False)
    c_tab = Column(String(50), nullable=True)
    tp_emi = Column(Integer, nullable=True)
    emission_status = Column(Integer, nullable=False)
    c_aut = Column(String(100), nullable=True)
    n_doc_emit = Column(String(30), nullable=True)
    d_emi = Column(String(50), nullable=True)

    # carga
    pbru = Column(String(50), nullable=True)
    pcub = Column(String(50), nullable=True)
    qvol = Column(String(50), nullable=True)
    vtot = Column(String(50), nullable=True)
    c_orig_calc = Column(String(20), nullable=True)
    c_dest_calc = Column(String(20), nullable=True)

    # Actors (rem/toma/dest) minimal storage
    tomador_cnpj = Column(String(20), nullable=True)
    rem_nDoc = Column(String(20), nullable=True)
    rem_xNome = Column(String(255), nullable=True)
    dest_nDoc = Column(String(20), nullable=True)
    dest_xNome = Column(String(255), nullable=True)

    total_weight = Column(Float, nullable=True)
    total_value = Column(Numeric(12,2), nullable=True)
    volumes_qty = Column(Integer, nullable=True)
    raw_payload = Column(Text, nullable=True)

    status = Column(
        JSON,
        nullable=False,
        default=lambda: {"code": "10", **VALID_CODES["10"]},
    )

    invoices = relationship("ShipmentInvoice", back_populates="shipment", cascade="all, delete-orphan")

class ShipmentInvoice(Base):
    __tablename__ = "shipment_invoices"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False, index=True)

    # Nota fields
    n_ped = Column(String(100), nullable=True)
    invoice_series = Column(String(50), nullable=True)
    invoice_number = Column(String(100), nullable=True)
    d_emi = Column(String(50), nullable=True)
    v_bc = Column(String(50), nullable=True)
    v_icms = Column(String(50), nullable=True)
    v_bcst = Column(String(50), nullable=True)
    v_st = Column(String(50), nullable=True)
    v_prod = Column(String(50), nullable=True)
    invoice_value = Column(Numeric(12,2), nullable=True)
    ncfop = Column(String(20), nullable=True)
    pbru = Column(String(50), nullable=True)
    qvol = Column(String(50), nullable=True)
    access_key = Column(String(64), nullable=True)
    tp_doc = Column(String(20), nullable=True)
    x_esp = Column(String(255), nullable=True)
    x_nat = Column(String(255), nullable=True)
    cte_chave = Column(String(100), nullable=True)
    xmls_b64 = Column(JSON, nullable=True)

    cfop = Column(String(20), nullable=True)

    trackings = relationship("ShipmentInvoiceTracking", back_populates="invoice", cascade="all, delete-orphan")
    shipment = relationship("Shipment", back_populates="invoices")


class ShipmentInvoiceTracking(Base):
    __tablename__ = "shipment_invoice_trackings"

    id = Column(Integer, primary_key=True, index=True)
    shipment_invoice_id = Column(Integer, ForeignKey("shipment_invoices.id"), nullable=False, index=True)
    codigo_evento = Column(String(20), nullable=False)
    descricao = Column(String(255), nullable=True)
    data_evento = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("ShipmentInvoice", back_populates="trackings")
