import pytest
import asyncio

from app.services.localidades_service import LocalidadesService
from app.db import AsyncSessionLocal


@pytest.mark.asyncio
async def test_sincronizar_com_ibge_works_without_postgis(monkeypatch):
    # Fake IBGE responses
    async def fake_get(self, url):
        class Dummy:
            def __init__(self, payload):
                self._payload = payload
            def json(self):
                return self._payload
        if 'estados' in url:
            return Dummy([{"id": 11, "sigla": "MG", "nome": "Minas Gerais"}])
        if 'municipios' in url:
            return Dummy([
                {
                    "id": 1100015,
                    "nome": "Testemunha",
                    "microrregiao": {"mesorregiao": {"UF": {"id": 11}}}
                }
            ])
        return Dummy([])

    monkeypatch.setattr('httpx.AsyncClient.get', fake_get, raising=False)

    # Skip shapefile import to avoid PostGIS requirements
    monkeypatch.setattr(LocalidadesService, '_importar_municipios_do_shapefile_sync', lambda *_: False)

    async with AsyncSessionLocal() as db:
        # Should not raise even if PostGIS is not installed
        await LocalidadesService.sincronizar_com_ibge(db)

        # Verify that estados and municipios were inserted
        from sqlalchemy import select
        from app.models.localidades import Estado, Municipio

        res = await db.execute(select(Estado).where(Estado.codigo_ibge == 11))
        estado = res.scalar_one_or_none()
        assert estado is not None

        res = await db.execute(select(Municipio).where(Municipio.codigo_ibge == 1100015))
        municipio = res.scalar_one_or_none()
        assert municipio is not None


@pytest.mark.asyncio
async def test_sincronizar_skips_failing_municipio(monkeypatch):
    # Two municipios: one will raise on insert, second should be inserted
    async def fake_get(self, url):
        class Dummy:
            def __init__(self, payload):
                self._payload = payload
            def json(self):
                return self._payload
        if 'estados' in url:
            return Dummy([{"id": 11, "sigla": "MG", "nome": "Minas Gerais"}])
        if 'municipios' in url:
            return Dummy([
                {
                    "id": 1100015,
                    "nome": "Fail City",
                    "microrregiao": {"mesorregiao": {"UF": {"id": 11}}}
                },
                {
                    "id": 1100020,
                    "nome": "Good City",
                    "microrregiao": {"mesorregiao": {"UF": {"id": 11}}}
                }
            ])
        return Dummy([])

    monkeypatch.setattr('httpx.AsyncClient.get', fake_get, raising=False)
    monkeypatch.setattr(LocalidadesService, '_importar_municipios_do_shapefile_sync', lambda *_: False)
    # Force no PostGIS so raw INSERT is used
    monkeypatch.setattr(LocalidadesService, '_postgis_available', lambda *_: False)

    from sqlalchemy.ext.asyncio import AsyncSession
    original_execute = AsyncSession.execute

    async def fake_execute(self, *args, **kwargs):
        # Detect raw INSERT INTO municipios and fail for codigo_ibge == 1100015
        sql = args[0]
        params = args[1] if len(args) > 1 else kwargs.get('params') or kwargs.get('parameters')
        if isinstance(sql, str) and 'INSERT INTO municipios' in sql:
            if params and params.get('codigo_ibge') == 1100015:
                raise Exception('simulated insert failure')
        return await original_execute(self, *args, **kwargs)

    monkeypatch.setattr(AsyncSession, 'execute', fake_execute)

    async with AsyncSessionLocal() as db:
        # Should not raise; failing municipio is skipped, the other is inserted
        await LocalidadesService.sincronizar_com_ibge(db)

        from sqlalchemy import select
        from app.models.localidades import Municipio

        res_fail = await db.execute(select(Municipio).where(Municipio.codigo_ibge == 1100015))
        assert res_fail.scalar_one_or_none() is None

        res_good = await db.execute(select(Municipio).where(Municipio.codigo_ibge == 1100020))
        assert res_good.scalar_one_or_none() is not None
