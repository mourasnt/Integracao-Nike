import pytest
from sqlalchemy import select
from app.models.localidades import Estado, Municipio
from app.models.shipment import Shipment
from app.services.localidades_service import LocalidadesService
from app.db import AsyncSessionLocal
import uuid


@pytest.mark.asyncio
async def test_emissao_sets_location_fields(monkeypatch):
    # Insert a state and municipality
    async with AsyncSessionLocal() as db:
        async with db.begin():
            st = Estado(codigo_ibge=11, sigla='MG', nome='Minas Gerais')
            db.add(st)
        await db.commit()

        # need to refresh to have uuid
        async with db.begin():
            res = await db.execute(select(Estado).where(Estado.codigo_ibge == 11))
            state = res.scalar_one()
            muni = Municipio(codigo_ibge=1100015, nome='Test City', estado_uuid=state.uuid)
            db.add(muni)
        await db.commit()

        # Build a Shipment with rem_cMun and dest_cMun and origem/destino codes
        shipment = Shipment(service_code='1', emission_status=1, rem_cMun='1100015', dest_cMun='1100015', c_orig_calc='1100015', c_dest_calc='1100015')
        db.add(shipment)
        await db.flush()

        # Set locations
        await LocalidadesService.set_shipment_locations(db, shipment)
        await db.commit()

        res = await db.execute(select(Shipment).where(Shipment.id == shipment.id))
        s = res.scalar_one()
        assert s.rem_municipio_codigo_ibge == 1100015
        assert s.rem_municipio_nome == 'Test City'
        assert s.rem_uf == 'MG'
        assert s.dest_municipio_codigo_ibge == 1100015
        assert s.origem_municipio_codigo_ibge == 1100015
        assert s.destino_uf == 'MG'