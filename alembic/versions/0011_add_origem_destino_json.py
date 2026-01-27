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


def _column_exists(inspector, table, column):
    """Check if a column exists in a table."""
    try:
        cols = [c['name'] for c in inspector.get_columns(table)]
        return column in cols
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('shipments'):
        return

    # Add columns only if they don't exist
    if not _column_exists(inspector, 'shipments', 'origem'):
        try:
            op.add_column('shipments', sa.Column('origem', postgresql.JSON(), nullable=True))
        except Exception:
            if not _column_exists(inspector, 'shipments', 'origem'):
                raise

    if not _column_exists(inspector, 'shipments', 'destino'):
        try:
            op.add_column('shipments', sa.Column('destino', postgresql.JSON(), nullable=True))
        except Exception:
            if not _column_exists(inspector, 'shipments', 'destino'):
                raise


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('shipments'):
        return

    if _column_exists(inspector, 'shipments', 'destino'):
        try:
            op.drop_column('shipments', 'destino')
        except Exception:
            pass

    if _column_exists(inspector, 'shipments', 'origem'):
        try:
            op.drop_column('shipments', 'origem')
        except Exception:
            pass
