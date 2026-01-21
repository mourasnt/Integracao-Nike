import pytest
from sqlalchemy import select
from app.models.localidades import Estado, Municipio
from app.models.shipment import Shipment
from app.services.localidades_service import LocalidadesService
from app.db import AsyncSessionLocal
from app.api.routes.cargas import listar_cargas, obter_carga


@pytest.mark.asyncio
async def test_list_cargas_includes_normalized_locations():
    async with AsyncSessionLocal() as db:
        # Create state and municipio
        async with db.begin():
            st = Estado(codigo_ibge=11, sigla='MG', nome='Minas Gerais')
            db.add(st)
        await db.commit()

        async with db.begin():
            res = await db.execute(select(Estado).where(Estado.codigo_ibge == 11))
            state = res.scalar_one()
            muni = Municipio(codigo_ibge=1100015, nome='Test City', estado_uuid=state.uuid)
            db.add(muni)
        await db.commit()

        # Create a shipment and set locations
        shipment = Shipment(service_code='1', emission_status=1, rem_cMun='1100015', dest_cMun='1100015', c_orig_calc='1100015', c_dest_calc='1100015')
        db.add(shipment)
        await db.flush()

        await LocalidadesService.set_shipment_locations(db, shipment)
        await db.commit()

        res = await listar_cargas(current_user='integracao_logistica', db=db)
        assert isinstance(res, list)
        assert len(res) >= 1
        s = res[0]
        # remetente
        assert s['rem']['UF'] == 'MG'
        assert s['rem']['municipioCodigoIbge'] == 1100015
        assert s['rem']['municipioNome'] == 'Test City'
        # destino and origem objects
        assert s['dest']['UF'] == 'MG'
        assert s['origem']['municipioCodigoIbge'] == 1100015
        assert s['destino']['UF'] == 'MG'


@pytest.mark.asyncio
async def test_get_carga_includes_normalized_locations():
    async with AsyncSessionLocal() as db:
        # Create state and municipio
        async with db.begin():
            st = Estado(codigo_ibge=12, sigla='SP', nome='Sao Paulo')
            db.add(st)
        await db.commit()

        async with db.begin():
            res = await db.execute(select(Estado).where(Estado.codigo_ibge == 12))
            state = res.scalar_one()
            muni = Municipio(codigo_ibge=1200015, nome='Other City', estado_uuid=state.uuid)
            db.add(muni)
        await db.commit()

        shipment = Shipment(service_code='1', emission_status=1, rem_cMun='1200015', dest_cMun='1200015', c_orig_calc='1200015', c_dest_calc='1200015')
        db.add(shipment)
        await db.flush()

        await LocalidadesService.set_shipment_locations(db, shipment)
        await db.commit()

        out = await obter_carga(shipment.id, current_user='integracao_logistica', db=db)
        assert out['rem']['UF'] == 'SP'
        assert out['rem']['municipioNome'] == 'Other City'
        assert out['origem']['municipioCodigoIbge'] == 1200015