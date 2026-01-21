import pytest
from fastapi import HTTPException

from app.api.routes.localidades import municipios_por_raio
from app.services.localidades_service import LocalidadesService


@pytest.mark.asyncio
async def test_municipios_por_raio_returns_501_when_postgis_not_available(monkeypatch):
    async def fake_get_municipios_por_raio(db, codigo_ibge, raio):
        raise LocalidadesService.PostGisUnavailableError("PostGIS not available for test")

    monkeypatch.setattr(LocalidadesService, "get_municipios_por_raio", fake_get_municipios_por_raio)

    with pytest.raises(HTTPException) as excinfo:
        await municipios_por_raio(123, 10.0, db=None)

    assert excinfo.value.status_code == 501
    assert "PostGIS" in excinfo.value.detail


@pytest.mark.asyncio
async def test_municipios_por_raio_returns_results_when_postgis_available(monkeypatch):
    async def fake_get_municipios_por_raio(db, codigo_ibge, raio):
        return []

    monkeypatch.setattr(LocalidadesService, "get_municipios_por_raio", fake_get_municipios_por_raio)

    res = await municipios_por_raio(123, 10.0, db=None)
    assert res == []
