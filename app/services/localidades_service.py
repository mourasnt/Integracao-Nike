import asyncio
import httpx
import json

from sqlalchemy import select, text, func, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import selectinload, joinedload, defer

try:
    import geopandas as gpd
    import pandas as pd
except ImportError:
    raise ImportError(
        "As bibliotecas 'geopandas' e 'pandas' são necessárias para geoprocessamento."
    )

from app.models.localidades import Estado, Municipio


# -------------------------------------------------------------------
# CONSTANTES
# -------------------------------------------------------------------

IBGE_ESTADOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
IBGE_MUNIS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"

SHAPEFILE_MUNICIPIOS_PATH = "./dados_geo/BR_Municipios_2024.shp"


# -------------------------------------------------------------------
# SERVICE
# -------------------------------------------------------------------

class LocalidadesService:

    @staticmethod
    async def _find_municipio_info_by_codigo(db: AsyncSession, codigo_ibge: int):
        """Return (municipio_codigo, municipio_nome, estado_codigo, estado_sigla) or (None,None,None,None) if not found."""
        try:
            result = await db.execute(select(Municipio).options(selectinload(Municipio.estado)).where(Municipio.codigo_ibge == codigo_ibge))
            muni = result.scalar_one_or_none()
            if not muni:
                return None, None, None, None
            estado = muni.estado
            return muni.codigo_ibge, muni.nome, (estado.codigo_ibge if estado else None), (estado.sigla if estado else None)
        except Exception:
            return None, None, None, None

    @staticmethod
    async def set_shipment_locations(db: AsyncSession, shipment):
        """Resolve and set normalized UF + municipio/estado codes on a Shipment instance.

        This function will attempt to use IBGE codes found on the shipment (e.g. rem_cMun, dest_cMun, recebedor_cMun, c_orig_calc, c_dest_calc).
        It will not raise on missing entries — it will just skip them.
        """
        # Mapping config: field -> (ibge_source_attr, uf_attr, estado_codigo_attr, municipio_codigo_attr, municipio_nome_attr)
        mapping = {
            'rem': ('rem_cMun', 'rem_uf', 'rem_estado_codigo_ibge', 'rem_municipio_codigo_ibge', 'rem_municipio_nome'),
            'dest': ('dest_cMun', 'dest_uf', 'dest_estado_codigo_ibge', 'dest_municipio_codigo_ibge', 'dest_municipio_nome'),
            'recebedor': ('recebedor_cMun', 'recebedor_uf', 'recebedor_estado_codigo_ibge', 'recebedor_municipio_codigo_ibge', 'recebedor_municipio_nome'),
            'origem': ('c_orig_calc', 'origem_uf', 'origem_estado_codigo_ibge', 'origem_municipio_codigo_ibge', 'origem_municipio_nome'),
            'destino': ('c_dest_calc', 'destino_uf', 'destino_estado_codigo_ibge', 'destino_municipio_codigo_ibge', 'destino_municipio_nome'),
        }

        for key, (src_attr, uf_attr, estado_attr, municipio_attr, municipio_nome_attr) in mapping.items():
            try:
                val = getattr(shipment, src_attr, None)
                if val is None:
                    continue
                # normalize numeric IBGE if provided as string
                try:
                    codigo = int(str(val).strip())
                except Exception:
                    codigo = None

                if codigo:
                    muni_codigo, muni_nome, est_codigo, est_sigla = await LocalidadesService._find_municipio_info_by_codigo(db, codigo)
                    if muni_codigo is not None:
                        setattr(shipment, municipio_attr, muni_codigo)
                    if muni_nome:
                        setattr(shipment, municipio_nome_attr, muni_nome)
                    if est_codigo is not None:
                        setattr(shipment, estado_attr, est_codigo)
                    if est_sigla:
                        setattr(shipment, uf_attr, est_sigla)
            except Exception as e:
                # Best-effort: do not raise; just log and continue
                print(f"[WARN] set_shipment_locations failed for {key}: {e}")
                continue


    # ===============================================================
    # URL SÍNCRONA (GeoPandas / psycopg2)
    # ===============================================================
    @staticmethod
    def _get_sync_db_url(db: AsyncSession) -> str:
        async_engine = db.get_bind()
        if not async_engine:
            raise ConnectionError("AsyncSession não está associada a um Engine.")

        url: URL = async_engine.url

        return (
            f"postgresql+psycopg2://{url.username}:{url.password}"
            f"@{url.host}:{url.port}/{url.database}"
        )

    @staticmethod
    class PostGisUnavailableError(Exception):
        """Raised when spatial/PostGIS features are not available in the DB."""
        pass

    @staticmethod
    async def _postgis_available(db: AsyncSession) -> bool:
        """Detect if the PostGIS extension is installed in the connected DB.

        Best-effort: returns False if the check fails for any reason.
        """
        try:
            result = await db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'postgis' LIMIT 1"))
            return result.scalar_one_or_none() is not None
        except Exception:
            return False

    @staticmethod
    async def get_municipios_por_raio(db: AsyncSession, codigo_ibge: int, raio_km: float):
        """
        Retorna municípios dentro de um raio (em km) a partir de um município base.

        Raises PostGisUnavailableError when PostGIS isn't available.
        """

        # Ensure PostGIS is available before running spatial queries
        if not await LocalidadesService._postgis_available(db):
            raise LocalidadesService.PostGisUnavailableError(
                "Spatial features not available: PostGIS extension is not enabled"
            )

        result = await db.execute(
            select(Municipio.geometria).where(Municipio.codigo_ibge == codigo_ibge)
        )
        geom_base = result.scalar_one_or_none()

        if not geom_base:
            return None

        stmt = (
            select(Municipio)
            .options(joinedload(Municipio.estado))
            .where(
                func.ST_DWithin(
                    Municipio.geometria,
                    func.ST_Transform(geom_base, 3857),
                    raio_km * 1000
                )
            )
            .order_by(Municipio.nome)
        )

        result = await db.execute(stmt)
        results = result.scalars().all()
        for r in results:
            r.codigo_ibge = str(r.codigo_ibge)
        return results

    # CONSULTAS
    @staticmethod
    async def get_estados(db: AsyncSession):
        result = await db.execute(
            select(Estado).order_by(Estado.sigla)
        )
        return result.scalars().all()

    # MUNICÍPIOS COMO GEOJSON (SEM ORM NA RESPOSTA)
    @staticmethod
    async def get_municipios_por_uf(db: AsyncSession, uf: str):
        uf = uf.upper()

        result = await db.execute(
            select(Estado.uuid).where(Estado.sigla == uf)
        )
        estado_uuid = result.scalar_one_or_none()

        if not estado_uuid:
            return None

        result = await db.execute(
            select(Municipio).options(selectinload(Municipio.estado), defer(Municipio.geometria)).where(Municipio.estado_uuid == estado_uuid).order_by(Municipio.nome)
        )
        return result.scalars().all()

    # ---------------------------------------------------------------
    @staticmethod
    async def get_municipio_por_codigo(db: AsyncSession, codigo_ibge: int):
        result = await db.execute(
            select(Municipio).options(selectinload(Municipio.estado), defer(Municipio.geometria)).where(Municipio.codigo_ibge == codigo_ibge)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_estado_por_codigo(db: AsyncSession, codigo_ibge: int):
        result = await db.execute(
            select(Estado).where(Estado.codigo_ibge == codigo_ibge)
        )
        return result.scalar_one_or_none()

    # ===============================================================
    # FUNÇÃO SÍNCRONA — SHAPEFILE
    # ===============================================================
    @staticmethod
    def _importar_municipios_do_shapefile_sync(db_url: str):
        try:
            print(f"[SHP] Lendo: {SHAPEFILE_MUNICIPIOS_PATH}")
            gdf = gpd.read_file(SHAPEFILE_MUNICIPIOS_PATH)

            gdf = gdf.rename(columns={
                "CD_MUN": "codigo_ibge",
                "NM_MUN": "nome_shape",
            })

            gdf["codigo_ibge"] = (
                pd.to_numeric(gdf["codigo_ibge"], errors="coerce")
                .astype(str).str.split(".").str[0].astype(int)
            )

            if gdf.crs is None or gdf.crs.to_epsg() != 4674:
                gdf = gdf.set_crs(epsg=4674, allow_override=True)

            # Converte para CRS métrico (EPSG:3857) para permitir consultas espaciais eficientes
            gdf = gdf.to_crs(epsg=3857)

            engine = create_engine(db_url)

            with engine.begin() as conn:
                gdf.to_postgis(
                    name="municipios_temp_geometria",
                    con=conn,
                    if_exists="replace",
                    schema="public",
                    index=True,
                    chunksize=1000,
                )

            print("[SHP] Importação concluída.")
            return True

        except Exception as e:
            print(f"[ERRO SHP] {type(e).__name__}: {e}")
            return False

    # ===============================================================
    # SINCRONIZAÇÃO COMPLETA
    # ===============================================================
    @staticmethod
    async def sincronizar_com_ibge(db: AsyncSession):

        print("=== SINCRONIZAÇÃO DE LOCALIDADES ===")

        db_url_sync = LocalidadesService._get_sync_db_url(db)

        async with httpx.AsyncClient(timeout=60) as client:

            # ----------------------------------------------------------
            # ESTADOS
            # ----------------------------------------------------------
            estados = (await client.get(IBGE_ESTADOS_URL)).json()
            estado_map = {}

            for e in estados:
                result = await db.execute(
                    select(Estado).where(Estado.codigo_ibge == e["id"])
                )
                estado = result.scalar_one_or_none()

                if not estado:
                    estado = Estado(
                        codigo_ibge=e["id"],
                        sigla=e["sigla"],
                        nome=e["nome"],
                    )
                    db.add(estado)
                else:
                    estado.sigla = e["sigla"]
                    estado.nome = e["nome"]

                estado_map[e["id"]] = estado

            await db.commit()
            print("✔ Estados sincronizados")

            # ----------------------------------------------------------
            # MUNICÍPIOS (SEM GEOMETRIA)
            # ----------------------------------------------------------
            municipios = (await client.get(IBGE_MUNIS_URL)).json()

            # Detect PostGIS availability for later decisions
            has_postgis = await LocalidadesService._postgis_available(db)

            for m in municipios:
                microrregiao = m.get("microrregiao")
                mesorregiao = microrregiao.get("mesorregiao") if isinstance(microrregiao, dict) else {}
                uf = mesorregiao.get("UF") if isinstance(mesorregiao, dict) else {}
                uf_uuid = uf.get("id") if isinstance(uf, dict) else None
                if not uf_uuid:
                    continue

                estado = estado_map.get(uf_uuid)
                if not estado:
                    continue

                try:
                    # Prevent premature autoflush (which can trigger geometry binders) while we read/modify
                    with db.no_autoflush:
                        result = await db.execute(
                            select(Municipio).options(defer(Municipio.geometria))
                            .where(Municipio.codigo_ibge == m["id"])
                        )
                        municipio = result.scalar_one_or_none()

                    if not municipio:
                        # If PostGIS is not available, avoid GeoAlchemy geometry binders by using raw INSERT
                        if not has_postgis:
                            import uuid as _uuid
                            await db.execute(text(
                                "INSERT INTO municipios (uuid, codigo_ibge, nome, estado_uuid) VALUES (:uuid, :codigo_ibge, :nome, :estado_uuid)"
                            ), {
                                "uuid": str(_uuid.uuid4()),
                                "codigo_ibge": m["id"],
                                "nome": m["nome"],
                                "estado_uuid": str(estado.uuid),
                            })
                        else:
                            db.add(Municipio(
                                codigo_ibge=m["id"],
                                nome=m["nome"],
                                estado_uuid=estado.uuid,
                            ))
                    else:
                        # Update existing - use raw UPDATE when PostGIS unavailable to avoid geometry binders
                        if not has_postgis:
                            await db.execute(text(
                                "UPDATE municipios SET nome = :nome, estado_uuid = :estado WHERE codigo_ibge = :codigo_ibge"
                            ), {"nome": m["nome"], "estado": str(estado.uuid), "codigo_ibge": m["id"]})
                        else:
                            municipio.nome = m["nome"]
                            municipio.estado_uuid = estado.uuid

                except Exception as e:
                    # Log and skip this municipio; continue with the rest
                    print(f"[WARN] failed to process municipio {m.get('id')} - {e}")
                    continue

            await db.commit()
            print("✔ Municípios sincronizados")

        # --------------------------------------------------------------
        # GEOMETRIA
        # --------------------------------------------------------------
        print("✔ Importando geometria...")
        ok = await asyncio.to_thread(
            LocalidadesService._importar_municipios_do_shapefile_sync,
            db_url_sync,
        )

        if not ok:
            print("[WARN] shapefile import failed, skipping geometry import")
            return

        # Only run geometry import SQL if PostGIS is available
        if not has_postgis:
            print("[WARN] PostGIS not available; skipping geometry SQL update")
            try:
                await db.execute(text("DROP TABLE IF EXISTS municipios_temp_geometria;"))
                await db.commit()
            except Exception:
                pass
            print("=== SINCRONIZAÇÃO FINALIZADA COM SUCESSO (sem geometria) ===")
            return

        try:
            await db.execute(text("""
                UPDATE municipios m
                SET geometria = ST_Multi(ST_Transform(t.geometry, 3857))
                FROM municipios_temp_geometria t
                WHERE m.codigo_ibge = t.codigo_ibge;
            """))

            await db.execute(text("DROP TABLE IF EXISTS municipios_temp_geometria;"))
            await db.commit()
            print("=== SINCRONIZAÇÃO FINALIZADA COM SUCESSO ===")
        except Exception as e:
            print(f"[WARN] failed to assign geometries: {e}")
            try:
                await db.execute(text("DROP TABLE IF EXISTS municipios_temp_geometria;"))
                await db.commit()
            except Exception:
                pass
            print("=== SINCRONIZAÇÃO FINALIZADA COM SUCESSO (geometria parcial/missing) ===")