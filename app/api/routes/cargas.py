from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db import get_db
from app.models.shipment import Shipment
from app.services.tracking_service import TrackingService
from app.api.deps.security import get_current_user
from typing import Optional, Any

router = APIRouter(prefix="/cargas")


@router.get("/", )
async def listar_cargas( current_user: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Shipment).options(selectinload(Shipment.invoices))
    res = await db.execute(q)
    cargas = res.scalars().all()

    def serialize(c):
        return {
            "id": c.id,
            "external_ref": c.external_ref,
            "service_code": c.service_code,
            "total_weight": c.total_weight,
            "total_value": float(c.total_value) if c.total_value is not None else None,
            "volumes_qty": c.volumes_qty,
            "invoices": [
                {
                    "id": i.id,
                    "access_key": i.access_key,
                    "cte_chave": i.cte_chave
                }
                for i in c.invoices
            ]
        }

    return [serialize(c) for c in cargas]


@router.get("/{carga_id}")
async def obter_carga(carga_id: int,  current_user: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    q = select(Shipment).where(Shipment.id == carga_id).options(selectinload(Shipment.invoices))
    res = await db.execute(q)
    carga = res.scalars().first()
    if not carga:
        raise HTTPException(404, "Carga não encontrada")

    return {
        "id": carga.id,
        "external_ref": carga.external_ref,
        "service_code": carga.service_code,
        "total_weight": carga.total_weight,
        "total_value": float(carga.total_value) if carga.total_value is not None else None,
        "volumes_qty": carga.volumes_qty,
        "invoices": [
            {
                "id": i.id,
                "access_key": i.access_key,
                "cte_chave": i.cte_chave
            }
            for i in carga.invoices
        ]
    }


@router.post("/{carga_id}/status")
async def alterar_status(
    carga_id: int,
    novo_status: Optional[Any] = Body(None, example={"code": "1"}),
    anexos: Optional[list] = Body(None),
    current_user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Simple code extraction: accept "1" or {"code":"1"} or {"novo_status":"1"}
    code_val = None
    if isinstance(novo_status, (str, int)):
        code_val = str(novo_status)
    elif isinstance(novo_status, dict):
        code_val = str(novo_status.get("code") or novo_status.get("novo_status"))

    if not code_val:
        raise HTTPException(400, "novo_status inválido: forneça apenas o código, ex: {\"novo_status\": \"1\"}")

    # load carga and invoices
    q = select(Shipment).where(Shipment.id == carga_id).options(selectinload(Shipment.invoices))
    res = await db.execute(q)
    carga = res.scalars().first()
    if not carga:
        raise HTTPException(404, "Carga não encontrada")

    tv = TrackingService()
    results = []

    for inv in carga.invoices:
        if not inv or not getattr(inv, "cte_chave", None):
            results.append({"invoice": inv.id if inv else None, "ok": False, "reason": "sem cte_chave"})
            continue
        try:
            success, resp = await tv.enviar(inv.cte_chave, code_val, anexos=anexos)
            results.append({"invoice": inv.id, "ok": success, "vblog_response": resp[:500]})
            # persist tracking record
            await TrackingService.registrar(db, inv.id, code_val, descricao=None)
        except Exception as e:
            results.append({"invoice": inv.id, "ok": False, "reason": str(e)})

    return {"status": "ok", "codigo_enviado": code_val, "results": results}
