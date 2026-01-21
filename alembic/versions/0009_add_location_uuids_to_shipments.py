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


def upgrade():
    # Add UF sigla and UUID references for remetente
    op.add_column('shipments', sa.Column('rem_uf', sa.String(length=2), nullable=True))
    op.add_column('shipments', sa.Column('rem_estado_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('estados.uuid'), nullable=True))
    op.add_column('shipments', sa.Column('rem_municipio_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('municipios.uuid'), nullable=True))

    # Destinatario
    op.add_column('shipments', sa.Column('dest_uf', sa.String(length=2), nullable=True))
    op.add_column('shipments', sa.Column('dest_estado_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('estados.uuid'), nullable=True))
    op.add_column('shipments', sa.Column('dest_municipio_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('municipios.uuid'), nullable=True))

    # Recebedor
    op.add_column('shipments', sa.Column('recebedor_uf', sa.String(length=2), nullable=True))
    op.add_column('shipments', sa.Column('recebedor_estado_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('estados.uuid'), nullable=True))
    op.add_column('shipments', sa.Column('recebedor_municipio_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('municipios.uuid'), nullable=True))

    # Origem/Destino
    op.add_column('shipments', sa.Column('origem_uf', sa.String(length=2), nullable=True))
    op.add_column('shipments', sa.Column('origem_estado_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('estados.uuid'), nullable=True))
    op.add_column('shipments', sa.Column('origem_municipio_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('municipios.uuid'), nullable=True))

    op.add_column('shipments', sa.Column('destino_uf', sa.String(length=2), nullable=True))
    op.add_column('shipments', sa.Column('destino_estado_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('estados.uuid'), nullable=True))
    op.add_column('shipments', sa.Column('destino_municipio_uuid', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('municipios.uuid'), nullable=True))


def downgrade():
    for col in ['destino_municipio_uuid','destino_estado_uuid','destino_uf','origem_municipio_uuid','origem_estado_uuid','origem_uf','recebedor_municipio_uuid','recebedor_estado_uuid','recebedor_uf','dest_municipio_uuid','dest_estado_uuid','dest_uf','rem_municipio_uuid','rem_estado_uuid','rem_uf']:
        try:
            op.drop_column('shipments', col)
        except Exception:
            pass
