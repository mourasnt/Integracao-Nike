"""add remetente_ndoc column to shipment_invoices

Revision ID: 0007_add_remetente_ndoc
Revises: 0006_change_cFiscal_cPais
Create Date: 2026-01-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0007_add_remetente_ndoc'
down_revision = '0006_change_cFiscal_cPais'
branch_labels = None
depends_on = None


def _column_exists(inspector, table, column):
    try:
        cols = [c['name'] for c in inspector.get_columns(table)]
        return column in cols
    except Exception:
        return False


def _index_exists(inspector, table, index_name):
    try:
        idxs = [i['name'] for i in inspector.get_indexes(table)]
        return index_name in idxs
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # If the table doesn't exist, skip safely
    if not inspector.has_table('shipment_invoices'):
        return

    # Add column only if missing
    if not _column_exists(inspector, 'shipment_invoices', 'remetente_ndoc'):
        if bind.dialect.name == 'postgresql':
            try:
                op.execute("ALTER TABLE shipment_invoices ADD COLUMN IF NOT EXISTS remetente_ndoc VARCHAR(100)")
            except Exception:
                op.add_column('shipment_invoices', sa.Column('remetente_ndoc', sa.String(length=100), nullable=True))
        else:
            op.add_column('shipment_invoices', sa.Column('remetente_ndoc', sa.String(length=100), nullable=True))

    # Create index if not exists
    if not _index_exists(inspector, 'shipment_invoices', 'ix_shipment_invoices_remetente_ndoc'):
        try:
            op.create_index('ix_shipment_invoices_remetente_ndoc', 'shipment_invoices', ['remetente_ndoc'])
        except Exception:
            # best-effort; ignore if concurrent runs create it
            pass


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('shipment_invoices') and _index_exists(inspector, 'shipment_invoices', 'ix_shipment_invoices_remetente_ndoc'):
        try:
            op.drop_index('ix_shipment_invoices_remetente_ndoc', table_name='shipment_invoices')
        except Exception:
            pass

    if inspector.has_table('shipment_invoices') and _column_exists(inspector, 'shipment_invoices', 'remetente_ndoc'):
        try:
            op.drop_column('shipment_invoices', 'remetente_ndoc')
        except Exception:
            pass
