"""add status column to shipments

Revision ID: 0002_add_status
Revises: 0001_initial
Create Date: 2026-01-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_add_status'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # Add the missing `status` JSON column with a server default so existing rows get a value
    op.add_column(
        'shipments',
        sa.Column(
            'status',
            sa.JSON(),
            nullable=False,
            server_default='{"code": "10", "message": "Em processamento", "type": "info"}',
        ),
    )


def downgrade():
    op.drop_column('shipments', 'status')
