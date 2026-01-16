"""add xmls_b64 column to shipment_invoices

Revision ID: 0003_add_xmls_b64
Revises: 0001_initial
Create Date: 2026-01-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_add_xmls_b64'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_column('shipment_invoices', 'xmls_b64'):
        # Prefer Postgres-safe SQL to avoid DuplicateColumnError in concurrent runs
        if bind.dialect.name == 'postgresql':
            try:
                op.execute("ALTER TABLE shipment_invoices ADD COLUMN IF NOT EXISTS xmls_b64 JSON")
            except Exception:
                op.add_column('shipment_invoices', sa.Column('xmls_b64', sa.JSON(), nullable=True))
        else:
            op.add_column('shipment_invoices', sa.Column('xmls_b64', sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_column('shipment_invoices', 'xmls_b64'):
        op.drop_column('shipment_invoices', 'xmls_b64')
