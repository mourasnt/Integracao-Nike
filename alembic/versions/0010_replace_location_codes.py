"""replace location uuids with ibge codes and names

Revision ID: 0010_replace_location_codes
Revises: 0009_add_location_uuids
Create Date: 2026-01-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0010_replace_location_codes'
down_revision = '0009_add_location_uuids'
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

    # Drop UUID columns if present
    cols_to_drop = [
        'rem_estado_uuid','rem_municipio_uuid',
        'dest_estado_uuid','dest_municipio_uuid',
        'recebedor_estado_uuid','recebedor_municipio_uuid',
        'origem_estado_uuid','origem_municipio_uuid',
        'destino_estado_uuid','destino_municipio_uuid'
    ]
    
    for col in cols_to_drop:
        if _column_exists(inspector, 'shipments', col):
            try:
                op.drop_column('shipments', col)
            except Exception:
                pass

    # Add IBGE/code columns only if they don't exist
    def add_col_if_missing(col_name, col_def):
        if _column_exists(inspector, 'shipments', col_name):
            return
        try:
            op.add_column('shipments', col_def)
        except Exception:
            if not _column_exists(inspector, 'shipments', col_name):
                raise

    add_col_if_missing('rem_estado_codigo_ibge', sa.Column('rem_estado_codigo_ibge', sa.Integer(), nullable=True))
    add_col_if_missing('rem_municipio_codigo_ibge', sa.Column('rem_municipio_codigo_ibge', sa.Integer(), nullable=True))
    add_col_if_missing('rem_municipio_nome', sa.Column('rem_municipio_nome', sa.String(length=255), nullable=True))

    add_col_if_missing('dest_estado_codigo_ibge', sa.Column('dest_estado_codigo_ibge', sa.Integer(), nullable=True))
    add_col_if_missing('dest_municipio_codigo_ibge', sa.Column('dest_municipio_codigo_ibge', sa.Integer(), nullable=True))
    add_col_if_missing('dest_municipio_nome', sa.Column('dest_municipio_nome', sa.String(length=255), nullable=True))

    add_col_if_missing('recebedor_estado_codigo_ibge', sa.Column('recebedor_estado_codigo_ibge', sa.Integer(), nullable=True))
    add_col_if_missing('recebedor_municipio_codigo_ibge', sa.Column('recebedor_municipio_codigo_ibge', sa.Integer(), nullable=True))
    add_col_if_missing('recebedor_municipio_nome', sa.Column('recebedor_municipio_nome', sa.String(length=255), nullable=True))

    add_col_if_missing('origem_estado_codigo_ibge', sa.Column('origem_estado_codigo_ibge', sa.Integer(), nullable=True))
    add_col_if_missing('origem_municipio_codigo_ibge', sa.Column('origem_municipio_codigo_ibge', sa.Integer(), nullable=True))
    add_col_if_missing('origem_municipio_nome', sa.Column('origem_municipio_nome', sa.String(length=255), nullable=True))

    add_col_if_missing('destino_estado_codigo_ibge', sa.Column('destino_estado_codigo_ibge', sa.Integer(), nullable=True))
    add_col_if_missing('destino_municipio_codigo_ibge', sa.Column('destino_municipio_codigo_ibge', sa.Integer(), nullable=True))
    add_col_if_missing('destino_municipio_nome', sa.Column('destino_municipio_nome', sa.String(length=255), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('shipments'):
        return

    # Remove added columns
    for col in ['destino_municipio_nome','destino_municipio_codigo_ibge','destino_estado_codigo_ibge','origem_municipio_nome','origem_municipio_codigo_ibge','origem_estado_codigo_ibge','recebedor_municipio_nome','recebedor_municipio_codigo_ibge','recebedor_estado_codigo_ibge','dest_municipio_nome','dest_municipio_codigo_ibge','dest_estado_codigo_ibge','rem_municipio_nome','rem_municipio_codigo_ibge','rem_estado_codigo_ibge']:
        if _column_exists(inspector, 'shipments', col):
            try:
                op.drop_column('shipments', col)
            except Exception:
                pass
    # Note: we do NOT attempt to re-add UUID columns automatically in downgrade
