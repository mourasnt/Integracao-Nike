from sqlalchemy import Column, Integer, String, DateTime, Float, Numeric, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base

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

    cfop = Column(String(20), nullable=True)

    shipment = relationship("Shipment", back_populates="invoices")
