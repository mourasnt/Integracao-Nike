from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.schemas.notfis import NotfisPayload
from app.models.shipment import Shipment, ShipmentInvoice
from app.api.deps.security import get_current_user
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
        return JSONResponse(status_code=422, content={"detail": "Payload inválido"})

    if not docs or len(docs) == 0:
        # If there are no minutas, return 200 with an empty data list (tests accept 200/201)
        return JSONResponse(status_code=200, content={"message": "Nenhuma minuta para processar", "status": 1, "data": []})

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

                shipment = Shipment(
                    service_code=str(item.minuta.cServ),
                    c_tab=getattr(item.minuta, 'cTab', None),
                    tp_emi=getattr(item.minuta, 'tpEmi', None),
                    emission_status=item.minuta.cStatus,
                    c_aut=getattr(item.minuta, 'cAut', None),
                    n_doc_emit=getattr(item.minuta, 'nDocEmit', None),
                    d_emi=getattr(item.minuta, 'dEmi', None),
                    tomador_cnpj=item.toma.nDoc if item.toma else None,
                    rem_nDoc=item.rem.nDoc,
                    rem_xNome=item.rem.xNome,
                    dest_nDoc=item.dest.nDoc,
                    dest_xNome=item.dest.xNome,
                    pbru=item.minuta.carga.pBru if item.minuta.carga else None,
                    pcub=item.minuta.carga.pCub if item.minuta.carga else None,
                    qvol=item.minuta.carga.qVol if item.minuta.carga else None,
                    vtot=item.minuta.carga.vTot if item.minuta.carga else None,
                    c_orig_calc=item.minuta.carga.cOrigCalc if item.minuta.carga else None,
                    c_dest_calc=item.minuta.carga.cDestCalc if item.minuta.carga else None,
                    total_weight=float(item.minuta.carga.pBru) if item.minuta.carga and item.minuta.carga.pBru else None,
                    total_value=float(item.minuta.carga.vTot) if item.minuta.carga and item.minuta.carga.vTot else None,
                    volumes_qty=int(item.minuta.carga.qVol) if item.minuta.carga and item.minuta.carga.qVol else None,
                    raw_payload=json.dumps(raw)
                )
                db.add(shipment)
                await db.flush()

                for nf_idx, nf in enumerate(item.documentos):
                    logger.debug("Processing nota index=%d for minuta index=%d", nf_idx, idx)
                    if not getattr(nf, "nDoc", None):
                        raise ValueError("Campo obrigatório 'nDoc' não informado")
                    if not getattr(nf, "chave", None) or (nf.chave and len(nf.chave) != 44):
                        raise ValueError("Campo 'chave' inválido (deve ter 44 caracteres)")

                    invoice = ShipmentInvoice(
                        shipment_id=shipment.id,
                        n_ped=getattr(nf, 'nPed', None),
                        invoice_number=nf.nDoc,
                        invoice_series=nf.serie,
                        d_emi=getattr(nf, 'dEmi', None),
                        v_bc=getattr(nf, 'vBC', None),
                        v_icms=getattr(nf, 'vICMS', None),
                        v_bcst=getattr(nf, 'vBCST', None),
                        v_st=getattr(nf, 'vST', None),
                        v_prod=getattr(nf, 'vProd', None),
                        invoice_value=nf.vNF,
                        ncfop=getattr(nf, 'nCFOP', None),
                        pbru=getattr(nf, 'pBru', None),
                        qvol=getattr(nf, 'qVol', None),
                        access_key=nf.chave,
                        tp_doc=getattr(nf, 'tpDoc', None),
                        x_esp=getattr(nf, 'xEsp', None),
                        x_nat=getattr(nf, 'xNat', None),
                        cte_chave=None if not getattr(nf, 'cte', None) else nf.cte.get('Chave')
                    )
                    db.add(invoice)

                try:
                    await db.commit()
                    response_data.append({"status": 1, "message": "Importação realizada com sucesso", "id": shipment.id})
                except Exception as e:
                    await db.rollback()
                    global_status = 0
                    global_message = "Houve erros no processamento"
                    logger.exception("Erro ao commitar minuta (shipment id may be None): %s", e)
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
