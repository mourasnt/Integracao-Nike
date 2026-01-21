"""create localidades tables

Revision ID: 0008_create_localidades_tables
Revises: 0007_add_remetente_ndoc
Create Date: 2026-01-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision = '0008_create_localidades_tables'
down_revision = '0007_add_remetente_ndoc'
branch_labels = None
depends_on = None


def upgrade():
    # Detect PostGIS extension availability (best-effort)
    conn = op.get_bind()
    has_postgis = False
    try:
        res = conn.execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'postgis' LIMIT 1"))
        has_postgis = res.fetchone() is not None
    except Exception:
        has_postgis = False

    # Estados
    op.create_table(
        'estados',
        sa.Column('uuid', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('codigo_ibge', sa.Integer(), nullable=False),
        sa.Column('sigla', sa.String(length=2), nullable=False),
        sa.Column('nome', sa.String(), nullable=False),
    )
    op.create_index(op.f('ix_estados_codigo_ibge'), 'estados', ['codigo_ibge'], unique=True)

    # Municipios (geometria column type depends on PostGIS availability)
    geom_col = (
        sa.Column('geometria', Geometry(geometry_type='MULTIPOLYGON', srid=3857), nullable=True)
        if has_postgis else sa.Column('geometria', sa.Text(), nullable=True)
    )

    op.create_table(
        'municipios',
        sa.Column('uuid', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('codigo_ibge', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(), nullable=False),
        sa.Column('estado_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('estados.uuid', ondelete='CASCADE'), nullable=False),
        geom_col,
    )
    op.create_index(op.f('ix_municipios_codigo_ibge'), 'municipios', ['codigo_ibge'], unique=True)

    # If PostGIS is not available, add a best-effort comment to the column
    if not has_postgis:
        try:
            conn.execute(sa.text("COMMENT ON COLUMN municipios.geometria IS 'Fallback to TEXT because PostGIS not available'"))
        except Exception:
            # Ignore any failures to keep migration robust
            pass


def downgrade():
    op.drop_index(op.f('ix_municipios_codigo_ibge'), table_name='municipios')
    op.drop_table('municipios')
    op.drop_index(op.f('ix_estados_codigo_ibge'), table_name='estados')
    op.drop_table('estados')
