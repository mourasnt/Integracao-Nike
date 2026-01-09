"""initial consolidated schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================
    # 1. USERS API
    # =========================================================
    op.create_table(
        'users_api',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(length=150), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(op.f('ix_users_api_username'), 'users_api', ['username'], unique=True)

    # =========================================================
    # 2. SHIPMENTS (Com todos os campos consolidados)
    # =========================================================
    op.create_table(
        'shipments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('external_ref', sa.String(length=255), nullable=True),
        sa.Column('integration_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        # Consolidado: service_code já como String(50)
        sa.Column('service_code', sa.String(length=50), nullable=False),
        sa.Column('emission_status', sa.Integer(), nullable=False),
        
        sa.Column('tomador_cnpj', sa.String(length=20), nullable=True),
        sa.Column('sender_cnpj', sa.String(length=20), nullable=True),
        sa.Column('receiver_cnpj', sa.String(length=20), nullable=True),
        
        sa.Column('total_weight', sa.Float(), nullable=True),
        sa.Column('total_value', sa.Numeric(12, 2), nullable=True),
        sa.Column('volumes_qty', sa.Integer(), nullable=True),
        sa.Column('raw_payload', sa.Text(), nullable=True),

        # Campos extras de emissão (da antiga migração 2)
        sa.Column('c_tab', sa.String(length=50), nullable=True),
        sa.Column('tp_emi', sa.Integer(), nullable=True),
        sa.Column('c_aut', sa.String(length=100), nullable=True),
        sa.Column('n_doc_emit', sa.String(length=30), nullable=True),
        sa.Column('d_emi', sa.String(length=50), nullable=True),
        sa.Column('pbru', sa.String(length=50), nullable=True),
        sa.Column('pcub', sa.String(length=50), nullable=True),
        sa.Column('qvol', sa.String(length=50), nullable=True),
        sa.Column('vtot', sa.String(length=50), nullable=True),
        sa.Column('c_orig_calc', sa.String(length=20), nullable=True),
        sa.Column('c_dest_calc', sa.String(length=20), nullable=True),
        sa.Column('rem_nDoc', sa.String(length=20), nullable=True),
        sa.Column('rem_xNome', sa.String(length=255), nullable=True),
        sa.Column('dest_nDoc', sa.String(length=20), nullable=True),
        sa.Column('dest_xNome', sa.String(length=255), nullable=True),
    )

    # =========================================================
    # 3. SHIPMENT INVOICES (Com todos os campos consolidados)
    # =========================================================
    op.create_table(
        'shipment_invoices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('shipment_id', sa.Integer(), sa.ForeignKey('shipments.id'), nullable=False),
        sa.Column('invoice_number', sa.String(length=100), nullable=True),
        sa.Column('invoice_series', sa.String(length=50), nullable=True),
        sa.Column('access_key', sa.String(length=64), nullable=True),
        sa.Column('invoice_value', sa.Numeric(12, 2), nullable=True),
        sa.Column('cfop', sa.String(length=20), nullable=True),

        # Campos extras de emissão (da antiga migração 2)
        sa.Column('n_ped', sa.String(length=100), nullable=True),
        sa.Column('d_emi', sa.String(length=50), nullable=True),
        sa.Column('v_bc', sa.String(length=50), nullable=True),
        sa.Column('v_icms', sa.String(length=50), nullable=True),
        sa.Column('v_bcst', sa.String(length=50), nullable=True),
        sa.Column('v_st', sa.String(length=50), nullable=True),
        sa.Column('v_prod', sa.String(length=50), nullable=True),
        sa.Column('ncfop', sa.String(length=20), nullable=True),
        sa.Column('pbru', sa.String(length=50), nullable=True),
        sa.Column('qvol', sa.String(length=50), nullable=True),
        sa.Column('tp_doc', sa.String(length=20), nullable=True),
        sa.Column('x_esp', sa.String(length=255), nullable=True),
        sa.Column('x_nat', sa.String(length=255), nullable=True),
        sa.Column('cte_chave', sa.String(length=100), nullable=True),
    )


def downgrade():
    op.drop_table('shipment_invoices')
    op.drop_table('shipments')
    op.drop_index(op.f('ix_users_api_username'), table_name='users_api')
    op.drop_table('users_api')