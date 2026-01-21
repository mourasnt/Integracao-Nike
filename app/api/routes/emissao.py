from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.schemas.notfis import NotfisPayload
from app.models.shipment import Shipment, ShipmentInvoice
from app.api.deps.security import get_current_user
from app.services.localidades_service import LocalidadesService
import json
from loguru import logger

router = APIRouter()

@router.post("/emissao")
async def receive_emission(payload: NotfisPayload, current_user: str = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Recebe um payload Notfis e persiste cada minuta e suas notas.
    Regras principais aplicadas:
    - Validação de token JWT
    - Validação dos campos obrigatórios das notas (ex: `nDoc`, `chave` com 44 chars)
    - Transação por minuta (um erro em uma minuta não interrompe as outras)
    """
    logger.debug("/emissao called by user=%s", current_user)

    # Defensive checks for root structure
    try:
        docs = getattr(payload, 'documentos', None)
    except Exception as e:
        logger.exception("Payload structure invalid: %s", e)
        return JSONResponse(status_code=422, content={
                "message": "Falha ao processar solicitação",
                "status": 0,
                "data": [{"status": 0, "message": "payload inválido", "id": None}]
            })

    if not docs or len(docs) == 0:
        # If there are no minutas, return 200 with an empty data list (tests accept 200/201)
        return JSONResponse(status_code=400, content={
                "message": "Falha ao processar solicitação",
                "status": 0,
                "data": [{"status": 0, "message": "Nenhuma minuta para processar", "id": None}]
            })

    response_data = []
    global_status = 1
    global_message = "Documento gerado no sistema"

    try:
        for idx, item in enumerate(payload.documentos):
            try:
                raw = item.model_dump() if hasattr(item, 'model_dump') else item.dict()
                logger.debug("Processing minuta index=%d user=%s", idx, current_user)
                logger.info("Received minuta from %s: %s", current_user, json.dumps(raw))
                logger.debug("Minuta validated: cServ=%s, nDocEmit=%s", item.minuta.cServ, getattr(item.minuta, 'nDocEmit', None))

                # Validate cServ (accept int or numeric string)
                cserv = item.minuta.cServ
                try:
                    cserv_int = int(cserv)
                    if cserv_int <= 0:
                        raise ValueError()
                except Exception:
                    raise ValueError("Campo 'cServ' inválido")

                # Build Shipment from minuta using mapper utility
                from app.utils.mappers import minuta_to_shipment_payload, nota_to_invoice_payload

                shipment_payload = minuta_to_shipment_payload(item.minuta, item.rem, item.dest, item.toma, getattr(item, 'receb', None), json.dumps(raw))
                shipment = Shipment(**shipment_payload)
                db.add(shipment)
                await db.flush()

                # Normalize and store locations (UF + municipio/state UUIDs)
                try:
                    await LocalidadesService.set_shipment_locations(db, shipment)
                except Exception as e:
                    # Best-effort: log and continue
                    logger.warning("Failed to set shipment locations: %s", e)

                for nf_idx, nf in enumerate(item.documentos):
                    logger.debug("Processing nota index=%d for minuta index=%d", nf_idx, idx)
                    if not getattr(nf, "nDoc", None):
                        raise ValueError("Campo obrigatório 'nDoc' não informado")
                    if not getattr(nf, "chave", None) or (nf.chave and len(nf.chave) != 44):
                        raise ValueError("Campo 'chave' inválido (deve ter 44 caracteres)")

                    invoice_payload = nota_to_invoice_payload(nf, shipment_id=shipment.id)
                    invoice = ShipmentInvoice(**invoice_payload)
                    # Ensure invoice-level remetente ndoc is populated; fallback to shipment.rem_nDoc
                    invoice.remetente_ndoc = invoice_payload.get('remetente_ndoc') or shipment.rem_nDoc
                    db.add(invoice) 

                try:
                    from app.utils.db_utils import commit_or_raise
                    await commit_or_raise(db)
                    response_data.append({"status": 1, "message": "Importação realizada com sucesso", "id": shipment.id})
                except Exception as e:
                    await db.rollback()
                    global_status = 0
                    global_message = "Houve erros no processamento"
                    logger.exception("Erro ao commitar minuta (shipment id may be None): %s", e)
                    # Provide a concise message back to the client
                    response_data.append({"status": 0, "message": f"Erro durante commit: {e.__class__.__name__}: {str(e)}", "id": None})
            except Exception as e:
                await db.rollback()
                global_status = 0
                global_message = "Houve erros no processamento"
                logger.exception("Erro processando minuta: %s", e)
                response_data.append({"status": 0, "message": f"Erro: {e.__class__.__name__}: {str(e)}", "id": None})
    except Exception as e:
        logger.exception("Unhandled error in /emissao handler: %s", e)
        return JSONResponse(status_code=500, content={"message": "Erro interno do servidor", "status": 0, "data": [{"status": 0, "message": "Erro interno do servidor", "id": None}]})

    return {"message": global_message, "status": global_status, "data": response_data}
