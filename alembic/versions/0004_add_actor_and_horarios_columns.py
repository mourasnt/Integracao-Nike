"""add actor fields and horarios to shipments

Revision ID: 0004_add_actor_and_horarios
Revises: 0003_add_xmls_b64
Create Date: 2026-01-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004_add_actor_and_horarios'
down_revision = '0003_add_xmls_b64'
branch_labels = None
depends_on = None


def _column_exists(inspector, table, column):
    """Check if a column exists in a table."""
    try:
        cols = [c['name'] for c in inspector.get_columns(table)]
        return column in cols
    except Exception:
        return False


def _index_exists(inspector, table, index_name):
    """Check if an index exists in a table."""
    try:
        idxs = [i['name'] for i in inspector.get_indexes(table)]
        return index_name in idxs
    except Exception:
        return False


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
        # Re-check current columns at call time to minimize race conditions
        try:
            current_cols = [c['name'] for c in inspector.get_columns('shipments')]
        except Exception:
            current_cols = existing_cols

        if col_name in current_cols:
            return

        # Try adding the column, but handle errors gracefully to keep migration idempotent
        try:
            op.add_column('shipments', col)
        except Exception as e:
            # If the column already exists or another concurrent change happened, ignore and continue.
            # Re-check and only raise if column truly missing after the failure.
            try:
                current_cols = [c['name'] for c in inspector.get_columns('shipments')]
            except Exception:
                current_cols = []
            if col_name not in current_cols:
                raise
            # otherwise, ignore the error and proceed

    # Remetente
    add_col_if_missing('rem_IE', sa.Column('rem_IE', sa.String(length=50), nullable=True))
    add_col_if_missing('rem_cFiscal', sa.Column('rem_cFiscal', sa.String(length=50), nullable=True))
    add_col_if_missing('rem_xFant', sa.Column('rem_xFant', sa.String(length=255), nullable=True))
    add_col_if_missing('rem_xLgr', sa.Column('rem_xLgr', sa.String(length=255), nullable=True))
    add_col_if_missing('rem_nro', sa.Column('rem_nro', sa.String(length=50), nullable=True))
    add_col_if_missing('rem_xCpl', sa.Column('rem_xCpl', sa.String(length=255), nullable=True))
    add_col_if_missing('rem_xBairro', sa.Column('rem_xBairro', sa.String(length=255), nullable=True))
    add_col_if_missing('rem_cMun', sa.Column('rem_cMun', sa.String(length=7), nullable=True))
    add_col_if_missing('rem_CEP', sa.Column('rem_CEP', sa.String(length=10), nullable=True))
    add_col_if_missing('rem_cPais', sa.Column('rem_cPais', sa.String(length=10), nullable=True))
    add_col_if_missing('rem_nFone', sa.Column('rem_nFone', sa.String(length=30), nullable=True))
    add_col_if_missing('rem_email', sa.Column('rem_email', sa.String(length=255), nullable=True))

    # Destinatario
    add_col_if_missing('dest_IE', sa.Column('dest_IE', sa.String(length=50), nullable=True))
    add_col_if_missing('dest_cFiscal', sa.Column('dest_cFiscal', sa.String(length=50), nullable=True))
    add_col_if_missing('dest_xFant', sa.Column('dest_xFant', sa.String(length=255), nullable=True))
    add_col_if_missing('dest_xLgr', sa.Column('dest_xLgr', sa.String(length=255), nullable=True))
    add_col_if_missing('dest_nro', sa.Column('dest_nro', sa.String(length=50), nullable=True))
    add_col_if_missing('dest_xCpl', sa.Column('dest_xCpl', sa.String(length=255), nullable=True))
    add_col_if_missing('dest_xBairro', sa.Column('dest_xBairro', sa.String(length=255), nullable=True))
    add_col_if_missing('dest_cMun', sa.Column('dest_cMun', sa.String(length=7), nullable=True))
    add_col_if_missing('dest_CEP', sa.Column('dest_CEP', sa.String(length=10), nullable=True))
    add_col_if_missing('dest_cPais', sa.Column('dest_cPais', sa.String(length=10), nullable=True))
    add_col_if_missing('dest_nFone', sa.Column('dest_nFone', sa.String(length=30), nullable=True))
    add_col_if_missing('dest_email', sa.Column('dest_email', sa.String(length=255), nullable=True))

    # Recebedor
    add_col_if_missing('recebedor_nDoc', sa.Column('recebedor_nDoc', sa.String(length=20), nullable=True))
    add_col_if_missing('recebedor_xNome', sa.Column('recebedor_xNome', sa.String(length=255), nullable=True))
    add_col_if_missing('recebedor_IE', sa.Column('recebedor_IE', sa.String(length=50), nullable=True))
    add_col_if_missing('recebedor_cFiscal', sa.Column('recebedor_cFiscal', sa.String(length=50), nullable=True))
    add_col_if_missing('recebedor_xLgr', sa.Column('recebedor_xLgr', sa.String(length=255), nullable=True))
    add_col_if_missing('recebedor_nro', sa.Column('recebedor_nro', sa.String(length=50), nullable=True))
    add_col_if_missing('recebedor_xCpl', sa.Column('recebedor_xCpl', sa.String(length=255), nullable=True))
    add_col_if_missing('recebedor_xBairro', sa.Column('recebedor_xBairro', sa.String(length=255), nullable=True))
    add_col_if_missing('recebedor_cMun', sa.Column('recebedor_cMun', sa.String(length=7), nullable=True))
    add_col_if_missing('recebedor_CEP', sa.Column('recebedor_CEP', sa.String(length=10), nullable=True))
    add_col_if_missing('recebedor_cPais', sa.Column('recebedor_cPais', sa.String(length=10), nullable=True))
    add_col_if_missing('recebedor_nFone', sa.Column('recebedor_nFone', sa.String(length=30), nullable=True))
    add_col_if_missing('recebedor_email', sa.Column('recebedor_email', sa.String(length=255), nullable=True))

    # Horarios
    add_col_if_missing('et_origem', sa.Column('et_origem', sa.DateTime(timezone=True), nullable=True))
    add_col_if_missing('chegada_coleta', sa.Column('chegada_coleta', sa.DateTime(timezone=True), nullable=True))
    add_col_if_missing('saida_coleta', sa.Column('saida_coleta', sa.DateTime(timezone=True), nullable=True))
    add_col_if_missing('eta_destino', sa.Column('eta_destino', sa.DateTime(timezone=True), nullable=True))
    add_col_if_missing('chegada_destino', sa.Column('chegada_destino', sa.DateTime(timezone=True), nullable=True))
    add_col_if_missing('finalizacao', sa.Column('finalizacao', sa.DateTime(timezone=True), nullable=True))

    # Create indexes for nDoc fields if they don't exist
    if not _index_exists(inspector, 'shipments', 'ix_shipments_rem_nDoc'):
        try:
            op.create_index('ix_shipments_rem_nDoc', 'shipments', ['rem_nDoc'])
        except Exception:
            pass
    if not _index_exists(inspector, 'shipments', 'ix_shipments_dest_nDoc'):
        try:
            op.create_index('ix_shipments_dest_nDoc', 'shipments', ['dest_nDoc'])
        except Exception:
            pass
    if not _index_exists(inspector, 'shipments', 'ix_shipments_recebedor_nDoc'):
        try:
            op.create_index('ix_shipments_recebedor_nDoc', 'shipments', ['recebedor_nDoc'])
        except Exception:
            pass


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('shipments'):
        return

    # Drop indexes if they exist
    if _index_exists(inspector, 'shipments', 'ix_shipments_rem_nDoc'):
        try:
            op.drop_index('ix_shipments_rem_nDoc', table_name='shipments')
        except Exception:
            pass
    if _index_exists(inspector, 'shipments', 'ix_shipments_dest_nDoc'):
        try:
            op.drop_index('ix_shipments_dest_nDoc', table_name='shipments')
        except Exception:
            pass
    if _index_exists(inspector, 'shipments', 'ix_shipments_recebedor_nDoc'):
        try:
            op.drop_index('ix_shipments_recebedor_nDoc', table_name='shipments')
        except Exception:
            pass

    # Drop columns if they exist
    def drop_col_if_exists(col_name):
        try:
            cols = [c['name'] for c in inspector.get_columns('shipments')]
        except Exception:
            cols = []
        if col_name in cols:
            op.drop_column('shipments', col_name)

    for c in ['rem_IE','rem_cFiscal','rem_xFant','rem_xLgr','rem_nro','rem_xCpl','rem_xBairro','rem_cMun','rem_CEP','rem_cPais','rem_nFone','rem_email',
              'dest_IE','dest_cFiscal','dest_xFant','dest_xLgr','dest_nro','dest_xCpl','dest_xBairro','dest_cMun','dest_CEP','dest_cPais','dest_nFone','dest_email',
              'recebedor_nDoc','recebedor_xNome','recebedor_IE','recebedor_cFiscal','recebedor_xLgr','recebedor_nro','recebedor_xCpl','recebedor_xBairro','recebedor_cMun','recebedor_CEP','recebedor_cPais','recebedor_nFone','recebedor_email',
              'et_origem','chegada_coleta','saida_coleta','eta_destino','chegada_destino','finalizacao']:
        drop_col_if_exists(c)
