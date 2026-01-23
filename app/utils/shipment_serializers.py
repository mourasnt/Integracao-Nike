from __future__ import annotations

from typing import Any, Dict, Optional

from app.models.shipment import Shipment, ShipmentInvoice
from app.schemas.shipment import (
    ActorOut,
    HorariosOut,
    LocationOut,
    ShipmentInvoiceOut,
    ShipmentRead,
)


def _actor_from(shipment: Shipment, prefix: str, include_normalized: bool = True) -> Optional[ActorOut]:
    if shipment is None:
        return None

    data: Dict[str, Any] = {
        "nDoc": getattr(shipment, f"{prefix}_nDoc", None),
        "IE": getattr(shipment, f"{prefix}_IE", None),
        "cFiscal": getattr(shipment, f"{prefix}_cFiscal", None),
        "xNome": getattr(shipment, f"{prefix}_xNome", None),
        "xFant": getattr(shipment, f"{prefix}_xFant", None),
        "xLgr": getattr(shipment, f"{prefix}_xLgr", None),
        "nro": getattr(shipment, f"{prefix}_nro", None),
        "xCpl": getattr(shipment, f"{prefix}_xCpl", None),
        "xBairro": getattr(shipment, f"{prefix}_xBairro", None),
        "cMun": getattr(shipment, f"{prefix}_cMun", None),
        "CEP": getattr(shipment, f"{prefix}_CEP", None),
        "cPais": getattr(shipment, f"{prefix}_cPais", None),
        "nFone": getattr(shipment, f"{prefix}_nFone", None),
        "email": getattr(shipment, f"{prefix}_email", None),
    }

    if include_normalized:
        data.update(
            {
                "UF": getattr(shipment, f"{prefix}_uf", None),
                "municipioCodigoIbge": getattr(shipment, f"{prefix}_municipio_codigo_ibge", None),
                "municipioNome": getattr(shipment, f"{prefix}_municipio_nome", None),
            }
        )

    # If every value is None, return None to avoid noisy payloads
    if all(value is None for value in data.values()):
        return None

    return ActorOut(**data)


def _horarios_from(shipment: Shipment) -> Optional[HorariosOut]:
    if shipment is None:
        return None

    data = {
        "et_origem": shipment.et_origem,
        "chegada_coleta": shipment.chegada_coleta,
        "saida_coleta": shipment.saida_coleta,
        "eta_destino": shipment.eta_destino,
        "chegada_destino": shipment.chegada_destino,
        "finalizacao": shipment.finalizacao,
    }

    if all(value is None for value in data.values()):
        return None

    return HorariosOut(**data)


def _location_from(shipment: Shipment, prefix: str) -> Optional[LocationOut]:
    """Build LocationOut from JSON field or individual fields as fallback."""
    if shipment is None:
        return None

    # Try to use the JSON field directly (origem or destino)
    json_field = getattr(shipment, prefix, None)
    if json_field and isinstance(json_field, dict):
        return LocationOut(
            uf=json_field.get("uf"),
            municipio=json_field.get("municipio")
        )

    # Fallback: build from individual fields
    uf = getattr(shipment, f"{prefix}_uf", None)
    municipio_nome = getattr(shipment, f"{prefix}_municipio_nome", None)
    municipio_codigo = getattr(shipment, f"{prefix}_municipio_codigo_ibge", None)

    if not uf and not municipio_nome:
        return None

    return LocationOut(
        uf=uf,
        municipio=municipio_nome or (str(municipio_codigo) if municipio_codigo else None)
    )


def _invoice_from(invoice: ShipmentInvoice) -> ShipmentInvoiceOut:
    return ShipmentInvoiceOut(
        id=invoice.id,
        access_key=getattr(invoice, "access_key", None),
        cte_chave=getattr(invoice, "cte_chave", None),
        remetente_ndoc=getattr(invoice, "remetente_ndoc", None),
    )


def shipment_to_read(shipment: Shipment, include_locations: bool = True) -> ShipmentRead:
    return ShipmentRead(
        id=shipment.id,
        external_ref=getattr(shipment, "external_ref", None),
        service_code=getattr(shipment, "service_code", None),
        total_weight=float(shipment.total_weight) if shipment.total_weight is not None else None,
        total_value=float(shipment.total_value) if shipment.total_value is not None else None,
        volumes_qty=shipment.volumes_qty,
        rem=_actor_from(shipment, "rem"),
        dest=_actor_from(shipment, "dest"),
        toma=_actor_from(shipment, "tomador", include_normalized=False),
        recebedor=_actor_from(shipment, "recebedor"),
        horarios=_horarios_from(shipment),
        origem=_location_from(shipment, "origem") if include_locations else None,
        destino=_location_from(shipment, "destino") if include_locations else None,
        invoices=[_invoice_from(inv) for inv in getattr(shipment, "invoices", [])],
    )