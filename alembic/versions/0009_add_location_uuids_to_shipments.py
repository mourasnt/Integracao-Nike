"""add location uuids to shipments

Revision ID: 0009_add_location_uuids
Revises: 0008_create_localidades_tables
Create Date: 2026-01-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0009_add_location_uuids'
down_revision = '0008_create_localidades_tables'
branch_labels = None
depends_on = None


def _column_exists(inspector, table, column):
    """Check if a column exists in a table."""
    try:
        cols = [c['name'] for c in inspector.get_columns(table)]
        return column in cols
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('shipments'):
        return

    def add_col_if_missing(col_name, col_def):
        if _column_exists(inspector, 'shipments', col_name):
            return
        try:
            op.add_column('shipments', col_def)
        except Exception:
            # Re-check if column was added concurrently
            if not _column_exists(inspector, 'shipments', col_name):
                raise

    # Add UF sigla and UUID references for remetente
    add_col_if_missing('rem_uf', sa.Column('rem_uf', sa.String(length=2), nullable=True))
    add_col_if_missing('rem_estado_uuid', sa.Column('rem_estado_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('estados.uuid'), nullable=True))
    add_col_if_missing('rem_municipio_uuid', sa.Column('rem_municipio_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('municipios.uuid'), nullable=True))

    # Destinatario
    add_col_if_missing('dest_uf', sa.Column('dest_uf', sa.String(length=2), nullable=True))
    add_col_if_missing('dest_estado_uuid', sa.Column('dest_estado_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('estados.uuid'), nullable=True))
    add_col_if_missing('dest_municipio_uuid', sa.Column('dest_municipio_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('municipios.uuid'), nullable=True))

    # Recebedor
    add_col_if_missing('recebedor_uf', sa.Column('recebedor_uf', sa.String(length=2), nullable=True))
    add_col_if_missing('recebedor_estado_uuid', sa.Column('recebedor_estado_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('estados.uuid'), nullable=True))
    add_col_if_missing('recebedor_municipio_uuid', sa.Column('recebedor_municipio_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('municipios.uuid'), nullable=True))

    # Origem/Destino
    add_col_if_missing('origem_uf', sa.Column('origem_uf', sa.String(length=2), nullable=True))
    add_col_if_missing('origem_estado_uuid', sa.Column('origem_estado_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('estados.uuid'), nullable=True))
    add_col_if_missing('origem_municipio_uuid', sa.Column('origem_municipio_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('municipios.uuid'), nullable=True))

    add_col_if_missing('destino_uf', sa.Column('destino_uf', sa.String(length=2), nullable=True))
    add_col_if_missing('destino_estado_uuid', sa.Column('destino_estado_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('estados.uuid'), nullable=True))
    add_col_if_missing('destino_municipio_uuid', sa.Column('destino_municipio_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('municipios.uuid'), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('shipments'):
        return

    for col in ['destino_municipio_uuid','destino_estado_uuid','destino_uf','origem_municipio_uuid','origem_estado_uuid','origem_uf','recebedor_municipio_uuid','recebedor_estado_uuid','recebedor_uf','dest_municipio_uuid','dest_estado_uuid','dest_uf','rem_municipio_uuid','rem_estado_uuid','rem_uf']:
        if _column_exists(inspector, 'shipments', col):
            try:
                op.drop_column('shipments', col)
            except Exception:
                pass
