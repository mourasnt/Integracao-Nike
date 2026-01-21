"""replace location uuids with ibge codes and names

Revision ID: 0010_replace_location_uuids_with_codes
Revises: 0009_add_location_uuids
Create Date: 2026-01-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0010_replace_location_uuids_with_codes'
down_revision = '0009_add_location_uuids'
branch_labels = None
depends_on = None


def upgrade():
    # Drop UUID columns (if present) and add IBGE code + name columns
    to_drop = [
        'rem_estado_uuid','rem_municipio_uuid',
        'dest_estado_uuid','dest_municipio_uuid',
        'recebedor_estado_uuid','recebedor_municipio_uuid',
        'origem_estado_uuid','origem_municipio_uuid',
        'destino_state_uuid','destino_municipio_uuid','destino_estado_uuid'
    ]
    # Drop safer: attempt each
    cols_to_try = [
        'rem_estado_uuid','rem_municipio_uuid',
        'dest_estado_uuid','dest_municipio_uuid',
        'recebedor_estado_uuid','recebedor_municipio_uuid',
        'origem_estado_uuid','origem_municipio_uuid',
        'destino_estado_uuid','destino_municipio_uuid'
    ]
    for c in cols_to_try:
        try:
            op.drop_column('shipments', c)
        except Exception:
            pass

    # Add IBGE/code columns
    op.add_column('shipments', sa.Column('rem_estado_codigo_ibge', sa.Integer(), nullable=True))
    op.add_column('shipments', sa.Column('rem_municipio_codigo_ibge', sa.Integer(), nullable=True))
    op.add_column('shipments', sa.Column('rem_municipio_nome', sa.String(length=255), nullable=True))

    op.add_column('shipments', sa.Column('dest_estado_codigo_ibge', sa.Integer(), nullable=True))
    op.add_column('shipments', sa.Column('dest_municipio_codigo_ibge', sa.Integer(), nullable=True))
    op.add_column('shipments', sa.Column('dest_municipio_nome', sa.String(length=255), nullable=True))

    op.add_column('shipments', sa.Column('recebedor_estado_codigo_ibge', sa.Integer(), nullable=True))
    op.add_column('shipments', sa.Column('recebedor_municipio_codigo_ibge', sa.Integer(), nullable=True))
    op.add_column('shipments', sa.Column('recebedor_municipio_nome', sa.String(length=255), nullable=True))

    op.add_column('shipments', sa.Column('origem_estado_codigo_ibge', sa.Integer(), nullable=True))
    op.add_column('shipments', sa.Column('origem_municipio_codigo_ibge', sa.Integer(), nullable=True))
    op.add_column('shipments', sa.Column('origem_municipio_nome', sa.String(length=255), nullable=True))

    op.add_column('shipments', sa.Column('destino_estado_codigo_ibge', sa.Integer(), nullable=True))
    op.add_column('shipments', sa.Column('destino_municipio_codigo_ibge', sa.Integer(), nullable=True))
    op.add_column('shipments', sa.Column('destino_municipio_nome', sa.String(length=255), nullable=True))


def downgrade():
    # remove added columns
    for col in ['destino_municipio_nome','destino_municipio_codigo_ibge','destino_estado_codigo_ibge','origem_municipio_nome','origem_municipio_codigo_ibge','origem_estado_codigo_ibge','recebedor_municipio_nome','recebedor_municipio_codigo_ibge','recebedor_estado_codigo_ibge','dest_municipio_nome','dest_municipio_codigo_ibge','dest_estado_codigo_ibge','rem_municipio_nome','rem_municipio_codigo_ibge','rem_estado_codigo_ibge']:
        try:
            op.drop_column('shipments', col)
        except Exception:
            pass
    # Note: we do NOT attempt to re-add UUID columns automatically in downgrade
