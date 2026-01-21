from typing import Optional


def _safe_get(obj, attr, default=None):
    return getattr(obj, attr, default) if obj is not None else default


def minuta_to_shipment_payload(minuta, rem, dest, toma, receb, raw_payload: str) -> dict:
    carga = _safe_get(minuta, "carga")
    horarios = _safe_get(minuta, "horarios")

    payload = {
        "service_code": str(_safe_get(minuta, "cServ")) if _safe_get(minuta, "cServ") is not None else None,
        "c_tab": _safe_get(minuta, "cTab"),
        "tp_emi": _safe_get(minuta, "tpEmi"),
        "emission_status": _safe_get(minuta, "cStatus"),
        "c_aut": _safe_get(minuta, "cAut"),
        "n_doc_emit": _safe_get(minuta, "nDocEmit"),
        "d_emi": _safe_get(minuta, "dEmi"),
        "c_orig_calc": _safe_get(minuta, "cOrigCalc"),
        "c_dest_calc": _safe_get(minuta, "cDestCalc"),

        # carga
        "pbru": _safe_get(carga, "pBru"),
        "pcub": _safe_get(carga, "pCub"),
        "qvol": _safe_get(carga, "qVol"),
        "vtot": _safe_get(carga, "vTot"),

        # actors (basic)
        "tomador_cnpj": _safe_get(toma, "nDoc"),
        "tomador_nDoc": _safe_get(toma, "nDoc"),
        "tomador_xNome": _safe_get(toma, "xNome"),

        # rem (full details)
        "rem_nDoc": _safe_get(rem, "nDoc"),
        "rem_xNome": _safe_get(rem, "xNome"),
        "rem_IE": _safe_get(rem, "IE"),
        "rem_cFiscal": _safe_get(rem, "cFiscal"),
        "rem_xFant": _safe_get(rem, "xFant"),
        "rem_xLgr": _safe_get(rem, "xLgr"),
        "rem_nro": _safe_get(rem, "nro"),
        "rem_xCpl": _safe_get(rem, "xCpl"),
        "rem_xBairro": _safe_get(rem, "xBairro"),
        "rem_cMun": _safe_get(rem, "cMun"),
        "rem_CEP": _safe_get(rem, "CEP"),
        "rem_cPais": _safe_get(rem, "cPais"),
        "rem_nFone": _safe_get(rem, "nFone"),
        "rem_email": _safe_get(rem, "email"),

        # dest (full details)
        "dest_nDoc": _safe_get(dest, "nDoc"),
        "dest_xNome": _safe_get(dest, "xNome"),
        "dest_IE": _safe_get(dest, "IE"),
        "dest_cFiscal": _safe_get(dest, "cFiscal"),
        "dest_xFant": _safe_get(dest, "xFant"),
        "dest_xLgr": _safe_get(dest, "xLgr"),
        "dest_nro": _safe_get(dest, "nro"),
        "dest_xCpl": _safe_get(dest, "xCpl"),
        "dest_xBairro": _safe_get(dest, "xBairro"),
        "dest_cMun": _safe_get(dest, "cMun"),
        "dest_CEP": _safe_get(dest, "CEP"),
        "dest_cPais": _safe_get(dest, "cPais"),
        "dest_nFone": _safe_get(dest, "nFone"),
        "dest_email": _safe_get(dest, "email"),

        # recebedor (optional)
        "recebedor_nDoc": _safe_get(receb, "nDoc"),
        "recebedor_xNome": _safe_get(receb, "xNome"),
        "recebedor_IE": _safe_get(receb, "IE"),
        "recebedor_cFiscal": _safe_get(receb, "cFiscal"),
        "recebedor_xLgr": _safe_get(receb, "xLgr"),
        "recebedor_nro": _safe_get(receb, "nro"),
        "recebedor_xCpl": _safe_get(receb, "xCpl"),
        "recebedor_xBairro": _safe_get(receb, "xBairro"),
        "recebedor_cMun": _safe_get(receb, "cMun"),
        "recebedor_CEP": _safe_get(receb, "CEP"),
        "recebedor_cPais": _safe_get(receb, "cPais"),
        "recebedor_nFone": _safe_get(receb, "nFone"),
        "recebedor_email": _safe_get(receb, "email"),

        # horarios (if provided on minuta)
        "et_origem": _safe_get(horarios, "et_origem"),
        "chegada_coleta": _safe_get(horarios, "chegada_coleta"),
        "saida_coleta": _safe_get(horarios, "saida_coleta"),
        "eta_destino": _safe_get(horarios, "eta_destino"),
        "chegada_destino": _safe_get(horarios, "chegada_destino"),
        "finalizacao": _safe_get(horarios, "finalizacao"),

        # derived
        "total_weight": float(_safe_get(carga, "pBru")) if carga and _safe_get(carga, "pBru") else None,
        "total_value": float(_safe_get(carga, "vTot")) if carga and _safe_get(carga, "vTot") else None,
        "volumes_qty": int(_safe_get(carga, "qVol")) if carga and _safe_get(carga, "qVol") else None,
        "raw_payload": raw_payload,
    }

    # Remove keys with None to avoid overriding DB defaults unnecessarily
    return {k: v for k, v in payload.items()}


def nota_to_invoice_payload(nf, shipment_id: Optional[int] = None) -> dict:
    # Attempt to extract remetente nDoc from nota payload (robust to different shapes)
    remetente_ndoc = None
    nf_rem = _safe_get(nf, "rem") or _safe_get(nf, "remetente")
    if isinstance(nf_rem, dict):
        remetente_ndoc = nf_rem.get("nDoc")
    elif hasattr(nf_rem, "nDoc"):
        remetente_ndoc = getattr(nf_rem, "nDoc")

    payload = {
        "shipment_id": shipment_id,
        "n_ped": _safe_get(nf, "nPed"),
        "invoice_number": _safe_get(nf, "nDoc"),
        "invoice_series": _safe_get(nf, "serie"),
        "d_emi": _safe_get(nf, "dEmi"),
        "v_bc": _safe_get(nf, "vBC"),
        "v_icms": _safe_get(nf, "vICMS"),
        "v_bcst": _safe_get(nf, "vBCST"),
        "v_st": _safe_get(nf, "vST"),
        "v_prod": _safe_get(nf, "vProd"),
        "invoice_value": _safe_get(nf, "vNF"),
        "ncfop": _safe_get(nf, "nCFOP"),
        "pbru": _safe_get(nf, "pBru"),
        "qvol": _safe_get(nf, "qVol"),
        "access_key": _safe_get(nf, "chave"),
        "tp_doc": _safe_get(nf, "tpDoc"),
        "x_esp": _safe_get(nf, "xEsp"),
        "x_nat": _safe_get(nf, "xNat"),
        "cte_chave": (_safe_get(nf, "cte", {}) or {}).get("Chave") if _safe_get(nf, "cte") else None,
        "remetente_ndoc": remetente_ndoc,
    }

    return {k: v for k, v in payload.items()} 
