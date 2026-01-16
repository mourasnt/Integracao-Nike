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
    # Idempotent: only add `status` if it's missing
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_column('shipments', 'status'):
        op.add_column(
            'shipments',
            sa.Column(
                'status',
                sa.JSON(),
                nullable=False,
                server_default='{"code": "10", "message": "Em processamento", "type": "info"}',
            ),
        )
    else:
        # Ensure the column has a non-null constraint and a server default to match model expectations
        try:
            op.alter_column(
                'shipments',
                'status',
                existing_type=sa.JSON(),
                nullable=False,
                server_default=sa.text("'{\"code\": \"10\", \"message\": \"Em processamento\", \"type\": \"info\"}'"),
            )
        except Exception:
            # Best-effort: if alteration isn't supported or would fail, skip to avoid breaking upgrades
            pass


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_column('shipments', 'status'):
        op.drop_column('shipments', 'status')
