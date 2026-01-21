from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.localidade import EstadoRead, MunicipioRead
from app.services.localidades_service import LocalidadesService
from app.api.deps.security import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/estados", response_model=list[EstadoRead])
async def listar_estados(db: AsyncSession = Depends(get_db)):
    """Lista todos os estados"""
    return await LocalidadesService.get_estados(db)


@router.get("/estados/{uf}/municipios", response_model=list[MunicipioRead])
async def listar_municipios_uf(uf: str, db: AsyncSession = Depends(get_db)):
    """Lista municípios de um estado"""
    municipios = await LocalidadesService.get_municipios_por_uf(db, uf)
    if municipios is None:
        raise HTTPException(404, "UF não encontrada")
    return municipios


@router.get("/municipios/{codigo_ibge}", response_model=MunicipioRead)
async def obter_municipio(codigo_ibge: int, db: AsyncSession = Depends(get_db)):
    """Obtém um município pelo código IBGE"""
    muni = await LocalidadesService.get_municipio_por_codigo(db, codigo_ibge)
    if not muni:
        raise HTTPException(404, "Município não encontrado")
    return muni

@router.get("/municipios/{codigo_ibge}/raio", response_model=list[MunicipioRead])
async def municipios_por_raio(codigo_ibge: int, raio: float, db: AsyncSession = Depends(get_db)):
    """
    Retorna municípios dentro de um raio (em km) a partir de um município base.
    """
    try:
        municipios = await LocalidadesService.get_municipios_por_raio(db, codigo_ibge, raio)
    except LocalidadesService.PostGisUnavailableError as e:
        # Spatial functionality not available; return 501 with a clear message
        raise HTTPException(status_code=501, detail=str(e))

    if municipios is None:
        raise HTTPException(status_code=404, detail="Município base não encontrado")

    return municipios


@router.post("/sincronizar")
async def sincronizar(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Sincroniza localidades com IBGE (requer admin)"""
    await LocalidadesService.sincronizar_com_ibge(db)
    return {"status": "ok", "mensagem": "Localidades atualizadas com IBGE"}