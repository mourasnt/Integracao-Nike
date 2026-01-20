"""change cFiscal and cPais columns to integer

Revision ID: 0006_change_cFiscal_cPais
Revises: 0005_add_tomador_columns
Create Date: 2026-01-20 00:45:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0006_change_cFiscal_cPais'
down_revision = '0005_add_tomador_columns'
branch_labels = None
depends_on = None


def _column_exists(inspector, table, column):
    try:
        cols = [c['name'] for c in inspector.get_columns(table)]
        return column in cols
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # List of (col_name, target_type_sql, using_expr)
    changes = [
        ('rem_cFiscal', 'INTEGER', "rem_cFiscal::integer"),
        ('dest_cFiscal', 'INTEGER', "dest_cFiscal::integer"),
        ('recebedor_cFiscal', 'INTEGER', "recebedor_cFiscal::integer"),
        ('rem_cPais', 'INTEGER', "rem_cPais::integer"),
        ('dest_cPais', 'INTEGER', "dest_cPais::integer"),
        ('recebedor_cPais', 'INTEGER', "recebedor_cPais::integer"),
    ]

    for col, target, using in changes:
        if not _column_exists(inspector, 'shipments', col):
            continue

        # Check existing type, skip if it's already integer-like
        try:
            cols = inspector.get_columns('shipments')
            colinfo = next((c for c in cols if c['name'] == col), None)
            if colinfo is not None:
                typ_str = str(colinfo.get('type', '')).lower()
                if 'int' in typ_str or 'integer' in typ_str:
                    # already integer type, skip
                    continue
        except Exception:
            # if inspection fails, proceed to sanitize/alter
            colinfo = None

        try:
            # Sanitize: remove all non-digits, set empty strings to NULL
            # Use quoted identifiers to preserve original casing (if any)
            op.execute(f"UPDATE shipments SET \"{col}\" = regexp_replace(COALESCE(\"{col}\"::text, ''), '\\D', '', 'g') WHERE \"{col}\" IS NOT NULL;")
            op.execute(f"UPDATE shipments SET \"{col}\" = NULL WHERE \"{col}\" = '';")

            # Finally alter column type using safe cast; use NULLIF to avoid casting empty string
            op.execute(f"ALTER TABLE shipments ALTER COLUMN \"{col}\" TYPE {target} USING NULLIF(\"{col}\", '')::integer")
        except Exception as e:
            # Provide a helpful message and re-raise so operator can inspect DB if needed
            raise RuntimeError(f"Failed to convert column {col} to {target}: {e}")



def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Revert to varchar(50)
    for col in ['rem_cFiscal', 'dest_cFiscal', 'recebedor_cFiscal']:
        if _column_exists(inspector, 'shipments', col):
            try:
                op.execute(f"ALTER TABLE shipments ALTER COLUMN {col} TYPE VARCHAR(50)")
            except Exception:
                pass

    for col in ['rem_cPais', 'dest_cPais', 'recebedor_cPais']:
        if _column_exists(inspector, 'shipments', col):
            try:
                op.execute(f"ALTER TABLE shipments ALTER COLUMN {col} TYPE VARCHAR(10)")
            except Exception:
                pass
