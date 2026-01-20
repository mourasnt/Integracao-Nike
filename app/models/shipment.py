from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Float, Numeric, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base
from app.services.constants import VALID_CODES


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

    # Actors (rem/toma/dest/recebedor) normalized fields
    tomador_cnpj = Column(String(20), nullable=True)
    tomador_nDoc = Column(String(20), nullable=True)
    tomador_xNome = Column(String(255), nullable=True)

    # Remetente
    rem_nDoc = Column(String(20), nullable=True, index=True)
    rem_xNome = Column(String(255), nullable=True)
    rem_IE = Column(String(50), nullable=True)
    rem_cFiscal = Column(Integer, nullable=True)
    rem_xFant = Column(String(255), nullable=True)
    rem_xLgr = Column(String(255), nullable=True)
    rem_nro = Column(String(50), nullable=True)
    rem_xCpl = Column(String(255), nullable=True)
    rem_xBairro = Column(String(255), nullable=True)
    rem_cMun = Column(String(7), nullable=True)
    rem_CEP = Column(String(10), nullable=True)
    rem_cPais = Column(Integer, nullable=True)
    rem_nFone = Column(String(30), nullable=True)
    rem_email = Column(String(255), nullable=True)

    # Destinatario
    dest_nDoc = Column(String(20), nullable=True, index=True)
    dest_xNome = Column(String(255), nullable=True)
    dest_IE = Column(String(50), nullable=True)
    dest_cFiscal = Column(Integer, nullable=True)
    dest_xFant = Column(String(255), nullable=True)
    dest_xLgr = Column(String(255), nullable=True)
    dest_nro = Column(String(50), nullable=True)
    dest_xCpl = Column(String(255), nullable=True)
    dest_xBairro = Column(String(255), nullable=True)
    dest_cMun = Column(String(7), nullable=True)
    dest_CEP = Column(String(10), nullable=True)
    dest_cPais = Column(Integer, nullable=True)
    dest_nFone = Column(String(30), nullable=True)
    dest_email = Column(String(255), nullable=True)

    # Recebedor (local de entrega)
    recebedor_nDoc = Column(String(20), nullable=True, index=True)
    recebedor_xNome = Column(String(255), nullable=True)
    recebedor_IE = Column(String(50), nullable=True)
    recebedor_cFiscal = Column(Integer, nullable=True)
    recebedor_xLgr = Column(String(255), nullable=True)
    recebedor_nro = Column(String(50), nullable=True)
    recebedor_xCpl = Column(String(255), nullable=True)
    recebedor_xBairro = Column(String(255), nullable=True)
    recebedor_cMun = Column(String(7), nullable=True)
    recebedor_CEP = Column(String(10), nullable=True)
    recebedor_cPais = Column(Integer, nullable=True)
    recebedor_nFone = Column(String(30), nullable=True)
    recebedor_email = Column(String(255), nullable=True)

    # Horarios (timestamps)
    et_origem = Column(DateTime(timezone=True), nullable=True)
    chegada_coleta = Column(DateTime(timezone=True), nullable=True)
    saida_coleta = Column(DateTime(timezone=True), nullable=True)
    eta_destino = Column(DateTime(timezone=True), nullable=True)
    chegada_destino = Column(DateTime(timezone=True), nullable=True)
    finalizacao = Column(DateTime(timezone=True), nullable=True)

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
