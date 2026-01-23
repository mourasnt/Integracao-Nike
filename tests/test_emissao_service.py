"""Testes unitários para o EmissaoService.

Testa cenários de sucesso, falha parcial e falha total no processamento
de minutas, usando mocks para isolar do banco de dados.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.emissao_service import EmissaoService
from app.schemas.notfis import (
    NotfisPayload, MinutaStructure, MinutaHeader, Actor, 
    NotaFiscalItem, Carga, Horarios
)
from app.schemas.emissao import MinutaResult, EmissaoResponse


# ============================================================
# Fixtures para criar payloads de teste
# ============================================================

@pytest.fixture
def valid_carga():
    """Carga válida para testes."""
    return Carga(pBru="100.5", pCub="50.0", qVol="10", vTot="5000.00")


@pytest.fixture
def valid_actor():
    """Actor (remetente/destinatário) válido para testes."""
    return Actor(
        nDoc="12345678901234",
        IE="123456789",
        cFiscal=1,
        xNome="Empresa Teste LTDA",
        xFant="Empresa Teste",
        xLgr="Rua Teste",
        nro="123",
        xCpl="Sala 1",
        xBairro="Centro",
        cMun="3550308",
        CEP="01310100",
        cPais=1058,
        nFone="11999999999",
        email="teste@email.com"
    )


@pytest.fixture
def valid_minuta_header(valid_carga):
    """Header de minuta válido para testes."""
    return MinutaHeader(
        toma="0",
        nDocEmit="DOC123",
        dEmi="2026-01-23",
        cServ="1",
        cTab="TAB01",
        tpEmi=1,
        cStatus=0,
        cAut="AUT123",
        carga=valid_carga,
        cOrigCalc="3550308",
        cDestCalc="3304557"
    )


@pytest.fixture
def valid_nota():
    """Nota fiscal válida para testes."""
    return NotaFiscalItem(
        nPed="PED123",
        serie="1",
        nDoc="12345",
        dEmi="2026-01-23",
        vBC="1000.00",
        vICMS="180.00",
        vBCST="0.00",
        vST="0.00",
        vProd="1000.00",
        vNF=1000.0,
        nCFOP="5102",
        pBru="10.5",
        qVol="2",
        chave="12345678901234567890123456789012345678901234",
        tpDoc="NFe",
        xEsp="CAIXA",
        xNat="VENDA"
    )


@pytest.fixture
def valid_minuta_structure(valid_minuta_header, valid_actor, valid_nota):
    """Estrutura completa de minuta válida."""
    return MinutaStructure(
        minuta=valid_minuta_header,
        rem=valid_actor,
        dest=valid_actor,
        toma=valid_actor,
        documentos=[valid_nota]
    )


@pytest.fixture
def valid_payload(valid_minuta_structure):
    """Payload Notfis completo válido."""
    return NotfisPayload(documentos=[valid_minuta_structure])


# ============================================================
# Testes de processamento de payload
# ============================================================

class TestEmissaoService:
    """Testes para o EmissaoService."""

    @pytest.mark.asyncio
    async def test_process_payload_success(self, valid_payload):
        """Testa processamento bem-sucedido de payload."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.begin = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(), __aexit__=AsyncMock()))
        mock_db.begin_nested = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(), __aexit__=AsyncMock()))
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.rollback = AsyncMock()
        
        # Mock shipment com ID
        mock_shipment = MagicMock()
        mock_shipment.id = 1
        mock_shipment.service_code = "1"
        mock_shipment.rem_nDoc = "12345678901234"
        
        with patch('app.services.emissao_service.Shipment', return_value=mock_shipment):
            with patch('app.services.emissao_service.ShipmentInvoice'):
                with patch('app.services.emissao_service.LocalidadesService.set_shipment_locations', new_callable=AsyncMock):
                    service = EmissaoService(mock_db)
                    
                    # Act
                    result = await service.process_payload(valid_payload, "test_user")
        
        # Assert
        assert isinstance(result, EmissaoResponse)
        assert result.status == 1
        assert len(result.data) == 1
        assert result.data[0].status == 1
        assert result.data[0].id == 1

    @pytest.mark.asyncio
    async def test_process_payload_empty_documentos(self):
        """Testa que payload sem documentos não processa nada."""
        # Arrange
        mock_db = AsyncMock()
        payload = NotfisPayload(documentos=[])
        
        # Isso deve falhar na validação do Pydantic, mas vamos testar o service
        # se receber uma lista vazia (edge case)
        service = EmissaoService(mock_db)
        
        # Act
        result = await service.process_payload(payload, "test_user")
        
        # Assert
        assert isinstance(result, EmissaoResponse)
        assert len(result.data) == 0
        assert result.status == 1  # Nenhuma falha se nenhum processamento

    @pytest.mark.asyncio
    async def test_process_minuta_db_error(self, valid_minuta_structure):
        """Testa tratamento de erro de banco de dados."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.begin = MagicMock(side_effect=Exception("DB connection error"))
        mock_db.rollback = AsyncMock()
        
        service = EmissaoService(mock_db)
        
        # Act
        result = await service._process_minuta(0, valid_minuta_structure, "test_user")
        
        # Assert
        assert isinstance(result, MinutaResult)
        assert result.status == 0
        assert "DB connection error" in result.message

    @pytest.mark.asyncio
    async def test_enrichment_failure_does_not_fail_transaction(self, valid_payload):
        """Testa que falha no enriquecimento de localidades não falha a transação."""
        # Arrange
        mock_db = AsyncMock()
        mock_db.begin = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(), __aexit__=AsyncMock()))
        mock_db.begin_nested = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(), __aexit__=AsyncMock()))
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        
        mock_shipment = MagicMock()
        mock_shipment.id = 1
        mock_shipment.service_code = "1"
        mock_shipment.rem_nDoc = "12345678901234"
        
        with patch('app.services.emissao_service.Shipment', return_value=mock_shipment):
            with patch('app.services.emissao_service.ShipmentInvoice'):
                # Localidades falha
                with patch('app.services.emissao_service.LocalidadesService.set_shipment_locations', 
                          new_callable=AsyncMock, 
                          side_effect=Exception("PostGIS error")):
                    service = EmissaoService(mock_db)
                    
                    # Act
                    result = await service.process_payload(valid_payload, "test_user")
        
        # Assert - deve ter sucesso mesmo com falha no enriquecimento
        assert result.status == 1
        assert result.data[0].status == 1


# ============================================================
# Testes de schemas de resposta
# ============================================================

class TestEmissaoResponse:
    """Testes para o schema EmissaoResponse."""

    def test_has_failures_true(self):
        """Testa detecção de falhas."""
        response = EmissaoResponse(
            message="Test",
            status=0,
            data=[
                MinutaResult(status=1, message="OK", id=1),
                MinutaResult(status=0, message="Erro", id=None)
            ]
        )
        assert response.has_failures() is True

    def test_has_failures_false(self):
        """Testa quando não há falhas."""
        response = EmissaoResponse(
            message="Test",
            status=1,
            data=[
                MinutaResult(status=1, message="OK", id=1),
                MinutaResult(status=1, message="OK", id=2)
            ]
        )
        assert response.has_failures() is False

    def test_all_failed(self):
        """Testa quando todas minutas falharam."""
        response = EmissaoResponse(
            message="Test",
            status=0,
            data=[
                MinutaResult(status=0, message="Erro", id=None),
                MinutaResult(status=0, message="Erro", id=None)
            ]
        )
        assert response.all_failed() is True

    def test_get_http_status_success(self):
        """Testa código HTTP 200 para sucesso total."""
        response = EmissaoResponse(
            message="OK",
            status=1,
            data=[MinutaResult(status=1, message="OK", id=1)]
        )
        assert response.get_http_status() == 200

    def test_get_http_status_partial(self):
        """Testa código HTTP 207 para sucesso parcial."""
        response = EmissaoResponse(
            message="Parcial",
            status=0,
            data=[
                MinutaResult(status=1, message="OK", id=1),
                MinutaResult(status=0, message="Erro", id=None)
            ]
        )
        assert response.get_http_status() == 207

    def test_get_http_status_all_failed(self):
        """Testa código HTTP 400 quando todas falharam."""
        response = EmissaoResponse(
            message="Erro",
            status=0,
            data=[MinutaResult(status=0, message="Erro", id=None)]
        )
        assert response.get_http_status() == 400

    def test_get_http_status_empty(self):
        """Testa código HTTP 400 para payload vazio."""
        response = EmissaoResponse(
            message="Vazio",
            status=0,
            data=[]
        )
        assert response.get_http_status() == 400
