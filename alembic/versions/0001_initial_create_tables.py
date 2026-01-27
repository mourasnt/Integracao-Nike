"""initial consolidated schema with all tables and columns

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Detect PostGIS extension availability
    conn = op.get_bind()
    has_postgis = False
    try:
        res = conn.execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'postgis' LIMIT 1"))
        has_postgis = res.fetchone() is not None
    except Exception:
        has_postgis = False

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
    # 2. LOCALIDADES (Estados e Municípios)
    # =========================================================
    op.create_table(
        'estados',
        sa.Column('uuid', UUID(as_uuid=True), primary_key=True),
        sa.Column('codigo_ibge', sa.Integer(), nullable=False),
        sa.Column('sigla', sa.String(length=2), nullable=False),
        sa.Column('nome', sa.String(), nullable=False),
    )
    op.create_index(op.f('ix_estados_codigo_ibge'), 'estados', ['codigo_ibge'], unique=True)

    # Geometria column depends on PostGIS availability
    geom_col = (
        sa.Column('geometria', Geometry(geometry_type='MULTIPOLYGON', srid=3857), nullable=True)
        if has_postgis else sa.Column('geometria', sa.Text(), nullable=True)
    )

    op.create_table(
        'municipios',
        sa.Column('uuid', UUID(as_uuid=True), primary_key=True),
        sa.Column('codigo_ibge', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(), nullable=False),
        sa.Column('estado_uuid', UUID(as_uuid=True), sa.ForeignKey('estados.uuid', ondelete='CASCADE'), nullable=False),
        geom_col,
    )
    op.create_index(op.f('ix_municipios_codigo_ibge'), 'municipios', ['codigo_ibge'], unique=True)

    if not has_postgis:
        try:
            conn.execute(sa.text("COMMENT ON COLUMN municipios.geometria IS 'Fallback to TEXT because PostGIS not available'"))
        except Exception:
            pass

    # =========================================================
    # 3. SHIPMENTS (Todas as colunas consolidadas)
    # =========================================================
    op.create_table(
        'shipments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('external_ref', sa.String(length=255), nullable=True),
        sa.Column('integration_date', sa.DateTime(timezone=True), server_default=sa.func.now()),
        
        # Service info
        sa.Column('service_code', sa.String(length=50), nullable=False),
        sa.Column('emission_status', sa.Integer(), nullable=False),
        sa.Column('c_tab', sa.String(length=50), nullable=True),
        sa.Column('tp_emi', sa.Integer(), nullable=True),
        sa.Column('c_aut', sa.String(length=100), nullable=True),
        sa.Column('n_doc_emit', sa.String(length=30), nullable=True),
        sa.Column('d_emi', sa.String(length=50), nullable=True),
        
        # Carga
        sa.Column('pbru', sa.String(length=50), nullable=True),
        sa.Column('pcub', sa.String(length=50), nullable=True),
        sa.Column('qvol', sa.String(length=50), nullable=True),
        sa.Column('vtot', sa.String(length=50), nullable=True),
        sa.Column('c_orig_calc', sa.String(length=20), nullable=True),
        sa.Column('c_dest_calc', sa.String(length=20), nullable=True),
        sa.Column('total_weight', sa.Float(), nullable=True),
        sa.Column('total_value', sa.Numeric(12, 2), nullable=True),
        sa.Column('volumes_qty', sa.Integer(), nullable=True),
        sa.Column('raw_payload', sa.Text(), nullable=True),
        
        # Tomador
        sa.Column('tomador_cnpj', sa.String(length=20), nullable=True),
        sa.Column('tomador_nDoc', sa.String(length=20), nullable=True),
        sa.Column('tomador_xNome', sa.String(length=255), nullable=True),
        
        # Remetente
        sa.Column('rem_nDoc', sa.String(length=20), nullable=True),
        sa.Column('rem_xNome', sa.String(length=255), nullable=True),
        sa.Column('rem_IE', sa.String(length=50), nullable=True),
        sa.Column('rem_cFiscal', sa.Integer(), nullable=True),
        sa.Column('rem_xFant', sa.String(length=255), nullable=True),
        sa.Column('rem_xLgr', sa.String(length=255), nullable=True),
        sa.Column('rem_nro', sa.String(length=50), nullable=True),
        sa.Column('rem_xCpl', sa.String(length=255), nullable=True),
        sa.Column('rem_xBairro', sa.String(length=255), nullable=True),
        sa.Column('rem_cMun', sa.String(length=7), nullable=True),
        sa.Column('rem_CEP', sa.String(length=10), nullable=True),
        sa.Column('rem_cPais', sa.Integer(), nullable=True),
        sa.Column('rem_nFone', sa.String(length=30), nullable=True),
        sa.Column('rem_email', sa.String(length=255), nullable=True),
        sa.Column('rem_uf', sa.String(length=2), nullable=True),
        sa.Column('rem_estado_codigo_ibge', sa.Integer(), nullable=True),
        sa.Column('rem_municipio_codigo_ibge', sa.Integer(), nullable=True),
        sa.Column('rem_municipio_nome', sa.String(length=255), nullable=True),
        
        # Destinatario
        sa.Column('dest_nDoc', sa.String(length=20), nullable=True),
        sa.Column('dest_xNome', sa.String(length=255), nullable=True),
        sa.Column('dest_IE', sa.String(length=50), nullable=True),
        sa.Column('dest_cFiscal', sa.Integer(), nullable=True),
        sa.Column('dest_xFant', sa.String(length=255), nullable=True),
        sa.Column('dest_xLgr', sa.String(length=255), nullable=True),
        sa.Column('dest_nro', sa.String(length=50), nullable=True),
        sa.Column('dest_xCpl', sa.String(length=255), nullable=True),
        sa.Column('dest_xBairro', sa.String(length=255), nullable=True),
        sa.Column('dest_cMun', sa.String(length=7), nullable=True),
        sa.Column('dest_CEP', sa.String(length=10), nullable=True),
        sa.Column('dest_cPais', sa.Integer(), nullable=True),
        sa.Column('dest_nFone', sa.String(length=30), nullable=True),
        sa.Column('dest_email', sa.String(length=255), nullable=True),
        sa.Column('dest_uf', sa.String(length=2), nullable=True),
        sa.Column('dest_estado_codigo_ibge', sa.Integer(), nullable=True),
        sa.Column('dest_municipio_codigo_ibge', sa.Integer(), nullable=True),
        sa.Column('dest_municipio_nome', sa.String(length=255), nullable=True),
        
        # Recebedor
        sa.Column('recebedor_nDoc', sa.String(length=20), nullable=True),
        sa.Column('recebedor_xNome', sa.String(length=255), nullable=True),
        sa.Column('recebedor_IE', sa.String(length=50), nullable=True),
        sa.Column('recebedor_cFiscal', sa.Integer(), nullable=True),
        sa.Column('recebedor_xLgr', sa.String(length=255), nullable=True),
        sa.Column('recebedor_nro', sa.String(length=50), nullable=True),
        sa.Column('recebedor_xCpl', sa.String(length=255), nullable=True),
        sa.Column('recebedor_xBairro', sa.String(length=255), nullable=True),
        sa.Column('recebedor_cMun', sa.String(length=7), nullable=True),
        sa.Column('recebedor_CEP', sa.String(length=10), nullable=True),
        sa.Column('recebedor_cPais', sa.Integer(), nullable=True),
        sa.Column('recebedor_nFone', sa.String(length=30), nullable=True),
        sa.Column('recebedor_email', sa.String(length=255), nullable=True),
        sa.Column('recebedor_uf', sa.String(length=2), nullable=True),
        sa.Column('recebedor_estado_codigo_ibge', sa.Integer(), nullable=True),
        sa.Column('recebedor_municipio_codigo_ibge', sa.Integer(), nullable=True),
        sa.Column('recebedor_municipio_nome', sa.String(length=255), nullable=True),
        
        # Origem/Destino (c_orig_calc/c_dest_calc)
        sa.Column('origem_uf', sa.String(length=2), nullable=True),
        sa.Column('origem_estado_codigo_ibge', sa.Integer(), nullable=True),
        sa.Column('origem_municipio_codigo_ibge', sa.Integer(), nullable=True),
        sa.Column('origem_municipio_nome', sa.String(length=255), nullable=True),
        sa.Column('destino_uf', sa.String(length=2), nullable=True),
        sa.Column('destino_estado_codigo_ibge', sa.Integer(), nullable=True),
        sa.Column('destino_municipio_codigo_ibge', sa.Integer(), nullable=True),
        sa.Column('destino_municipio_nome', sa.String(length=255), nullable=True),
        
        # Origem/Destino JSON consolidados
        sa.Column('origem', sa.JSON(), nullable=True),
        sa.Column('destino', sa.JSON(), nullable=True),
        
        # Horarios
        sa.Column('et_origem', sa.DateTime(timezone=True), nullable=True),
        sa.Column('chegada_coleta', sa.DateTime(timezone=True), nullable=True),
        sa.Column('saida_coleta', sa.DateTime(timezone=True), nullable=True),
        sa.Column('eta_destino', sa.DateTime(timezone=True), nullable=True),
        sa.Column('chegada_destino', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finalizacao', sa.DateTime(timezone=True), nullable=True),
        
        # Status
        sa.Column('status', sa.JSON(), nullable=False, server_default='{"code": "10", "message": "Em processamento", "type": "info"}'),
    )
    
    # Indexes for shipments
    op.create_index('ix_shipments_rem_nDoc', 'shipments', ['rem_nDoc'])
    op.create_index('ix_shipments_dest_nDoc', 'shipments', ['dest_nDoc'])
    op.create_index('ix_shipments_recebedor_nDoc', 'shipments', ['recebedor_nDoc'])

    # =========================================================
    # 4. SHIPMENT INVOICES (Todas as colunas consolidadas)
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
        sa.Column('xmls_b64', sa.JSON(), nullable=True),
        sa.Column('remetente_ndoc', sa.String(length=100), nullable=True),
    )
    
    # Indexes for shipment_invoices
    op.create_index('ix_shipment_invoices_shipment_id', 'shipment_invoices', ['shipment_id'])
    op.create_index('ix_shipment_invoices_remetente_ndoc', 'shipment_invoices', ['remetente_ndoc'])

    # =========================================================
    # 5. SHIPMENT INVOICE TRACKINGS
    # =========================================================
    op.create_table(
        'shipment_invoice_trackings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('shipment_invoice_id', sa.Integer(), sa.ForeignKey('shipment_invoices.id'), nullable=False),
        sa.Column('codigo_evento', sa.String(length=20), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=True),
        sa.Column('data_evento', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_shipment_invoice_trackings_shipment_invoice_id', 'shipment_invoice_trackings', ['shipment_invoice_id'])

    # =========================================================
    # 6. PREFATS
    # =========================================================
    op.create_table(
        'prefats',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('prefat_base64', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('shipment_invoice_trackings')
    op.drop_table('shipment_invoices')
    op.drop_table('shipments')
    op.drop_table('municipios')
    op.drop_table('estados')
    op.drop_index(op.f('ix_users_api_username'), table_name='users_api')
    op.drop_table('users_api')
    op.drop_table('prefats')