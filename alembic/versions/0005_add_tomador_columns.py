"""add tomador fields to shipments

Revision ID: 0005_add_tomador_columns
Revises: 0004_add_actor_and_horarios
Create Date: 2026-01-20 00:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0005_add_tomador_columns'
down_revision = '0004_add_actor_and_horarios'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('shipments'):
        return

    try:
        existing_cols = [c['name'] for c in inspector.get_columns('shipments')]
    except Exception:
        existing_cols = []

    def add_col_if_missing(col_name, col):
        # Re-check columns to avoid race conditions
        try:
            current_cols = [c['name'] for c in inspector.get_columns('shipments')]
        except Exception:
            current_cols = existing_cols

        if col_name in current_cols:
            return

        # Try Postgres-safe ADD COLUMN IF NOT EXISTS, otherwise fallback to op.add_column
        try:
            if bind.dialect.name == 'postgresql':
                try:
                    op.execute(f"ALTER TABLE shipments ADD COLUMN IF NOT EXISTS {col_name} {col.compile(dialect=sa.dialects.postgresql.dialect())}")
                except Exception:
                    op.add_column('shipments', col)
            else:
                op.add_column('shipments', col)
        except Exception as e:
            # Re-check and only raise if column still missing
            try:
                current_cols = [c['name'] for c in inspector.get_columns('shipments')]
            except Exception:
                current_cols = []
            if col_name not in current_cols:
                raise
            # else ignore the error (column was created concurrently)


    add_col_if_missing('tomador_nDoc', sa.Column('tomador_nDoc', sa.String(length=20), nullable=True))
    add_col_if_missing('tomador_xNome', sa.Column('tomador_xNome', sa.String(length=255), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('shipments'):
        return

    try:
        existing_cols = [c['name'] for c in inspector.get_columns('shipments')]
    except Exception:
        existing_cols = []

    if 'tomador_nDoc' in existing_cols:
        op.drop_column('shipments', 'tomador_nDoc')
    if 'tomador_xNome' in existing_cols:
        op.drop_column('shipments', 'tomador_xNome')
