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

    # If the table doesn't exist, skip safely
    if not inspector.has_table('shipment_invoices'):
        return

    # Early return if column already exists
    if _column_exists(inspector, 'shipment_invoices', 'xmls_b64'):
        return

    # Add column using PostgreSQL IF NOT EXISTS if available
    if bind.dialect.name == 'postgresql':
        try:
            op.execute("ALTER TABLE shipment_invoices ADD COLUMN IF NOT EXISTS xmls_b64 JSON")
            return
        except Exception:
            # Fall through to SQLAlchemy method
            pass

    # Final check and add using SQLAlchemy
    if not _column_exists(inspector, 'shipment_invoices', 'xmls_b64'):
        op.add_column('shipment_invoices', sa.Column('xmls_b64', sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('shipment_invoices') and _column_exists(inspector, 'shipment_invoices', 'xmls_b64'):
        op.drop_column('shipment_invoices', 'xmls_b64')
