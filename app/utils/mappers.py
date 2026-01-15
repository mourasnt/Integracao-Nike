from typing import Optional


def _safe_get(obj, attr, default=None):
    return getattr(obj, attr, default) if obj is not None else default


def minuta_to_shipment_payload(minuta, rem, dest, toma, raw_payload: str) -> dict:
    carga = _safe_get(minuta, "carga")

    payload = {
        "service_code": str(_safe_get(minuta, "cServ")) if _safe_get(minuta, "cServ") is not None else None,
        "c_tab": _safe_get(minuta, "cTab"),
        "tp_emi": _safe_get(minuta, "tpEmi"),
        "emission_status": _safe_get(minuta, "cStatus"),
        "c_aut": _safe_get(minuta, "cAut"),
        "n_doc_emit": _safe_get(minuta, "nDocEmit"),
        "d_emi": _safe_get(minuta, "dEmi"),

        # carga
        "pbru": _safe_get(carga, "pBru"),
        "pcub": _safe_get(carga, "pCub"),
        "qvol": _safe_get(carga, "qVol"),
        "vtot": _safe_get(carga, "vTot"),
        "c_orig_calc": _safe_get(carga, "cOrigCalc"),
        "c_dest_calc": _safe_get(carga, "cDestCalc"),

        # actors
        "tomador_cnpj": _safe_get(toma, "nDoc"),
        "rem_nDoc": _safe_get(rem, "nDoc"),
        "rem_xNome": _safe_get(rem, "xNome"),
        "dest_nDoc": _safe_get(dest, "nDoc"),
        "dest_xNome": _safe_get(dest, "xNome"),

        # derived
        "total_weight": float(_safe_get(carga, "pBru")) if carga and _safe_get(carga, "pBru") else None,
        "total_value": float(_safe_get(carga, "vTot")) if carga and _safe_get(carga, "vTot") else None,
        "volumes_qty": int(_safe_get(carga, "qVol")) if carga and _safe_get(carga, "qVol") else None,
        "raw_payload": raw_payload,
    }

    # Remove keys with None to avoid overriding DB defaults unnecessarily
    return {k: v for k, v in payload.items()}


def nota_to_invoice_payload(nf, shipment_id: Optional[int] = None) -> dict:
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
    }

    return {k: v for k, v in payload.items()}
