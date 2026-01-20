from app.utils.mappers import minuta_to_shipment_payload, nota_to_invoice_payload

class Dummy:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_minuta_mapping_basic():
    minuta = Dummy(cServ=1, cTab='T', tpEmi=1, cStatus=1, cAut='A', nDocEmit='N', dEmi='2024-01-01', carga=Dummy(pBru='10.5', vTot='100', qVol='2', pCub='2.0', cOrigCalc='1', cDestCalc='2'), horarios=Dummy(et_origem='2026-01-01T00:00:00+00:00', chegada_coleta='2026-01-02T00:00:00+00:00'))
    rem = Dummy(nDoc='111', xNome='Rem', xLgr='Rua A')
    dest = Dummy(nDoc='222', xNome='Dest', xLgr='Rua B')
    toma = Dummy(nDoc='333')
    receb = Dummy(nDoc='444', xNome='Receb')
    raw = '{}'

    payload = minuta_to_shipment_payload(minuta, rem, dest, toma, receb, raw)
    assert payload['service_code'] == '1'
    assert payload['c_tab'] == 'T'
    assert payload['pbru'] == '10.5'
    assert payload['total_weight'] == 10.5
    assert payload['volumes_qty'] == 2
    assert payload['raw_payload'] == raw
    # New mappings
    assert payload['rem_xLgr'] == 'Rua A'
    assert payload['dest_xLgr'] == 'Rua B'
    assert payload['recebedor_nDoc'] == '444'
    assert payload['et_origem'] == '2026-01-01T00:00:00+00:00'


def test_nota_mapping_basic():
    nf = Dummy(nPed='PED', serie='1', nDoc='123', dEmi='2024-01-01', vBC='10', vNF=1200.0, nCFOP='5102', pBru='10.5', qVol='3', chave='44CHAVE', cte={'Chave': 'CTECHAVE'})
    payload = nota_to_invoice_payload(nf, shipment_id=42)
    assert payload['shipment_id'] == 42
    assert payload['invoice_number'] == '123'
    assert payload['access_key'] == '44CHAVE'
    assert payload['cte_chave'] == 'CTECHAVE'