"""Add origem and destino JSON columns to shipments

Revision ID: 0011_add_origem_destino_json
Revises: 0010_replace_location_codes
Create Date: 2026-01-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0011_add_origem_destino_json'
down_revision = '0010_replace_location_codes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('shipments', sa.Column('origem', postgresql.JSON(), nullable=True))
    op.add_column('shipments', sa.Column('destino', postgresql.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('shipments', 'destino')
    op.drop_column('shipments', 'origem')
