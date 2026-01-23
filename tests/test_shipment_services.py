import pytest
from unittest.mock import AsyncMock, Mock, patch
from io import BytesIO

from app.services.shipment_status_service import ShipmentStatusService
from app.services.shipment_xml_service import ShipmentXmlService
from app.schemas.shipment import ShipmentStatusRequest, AttachmentIn, AttachmentFile
from app.models.shipment import Shipment, ShipmentInvoice
from app.db import AsyncSessionLocal
from fastapi import UploadFile, HTTPException


@pytest.mark.asyncio
async def test_status_service_change_status_success():
    """Test successful status change with tracking send."""
    async with AsyncSessionLocal() as db:
        # Create shipment and invoice
        shipment = Shipment(service_code="1", emission_status=1)
        db.add(shipment)
        await db.flush()

        invoice = ShipmentInvoice(shipment_id=shipment.id, access_key="12345678901234567890123456789012345678901234")
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)

        # Mock tracking service
        mock_tracking = Mock()
        mock_tracking.enviar = AsyncMock(return_value=(True, "OK"))
        mock_tracking.registrar = AsyncMock()

        service = ShipmentStatusService(tracking_svc=mock_tracking)
        payload = ShipmentStatusRequest(code="1")

        result = await service.change_status(db=db, invoice_id=invoice.id, payload=payload)

        assert result.status == "ok"
        assert result.codigo_enviado == "1"
        assert len(result.results) == 1
        assert result.results[0].ok is True
        mock_tracking.enviar.assert_called_once()
        mock_tracking.registrar.assert_called_once()


@pytest.mark.asyncio
async def test_status_service_invalid_code():
    """Test status change with invalid code raises HTTPException."""
    service = ShipmentStatusService()

    with pytest.raises(HTTPException) as exc_info:
        await service.parse_request(novo_status="999", recebedor_raw=None, request=None)

    assert exc_info.value.status_code == 400
    assert "inválido" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_status_service_with_file_attachment():
    """Test status change with file upload attachment."""
    async with AsyncSessionLocal() as db:
        shipment = Shipment(service_code="1", emission_status=1)
        db.add(shipment)
        await db.flush()

        invoice = ShipmentInvoice(shipment_id=shipment.id, access_key="12345678901234567890123456789012345678901234")
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)

        # Create mock upload file
        file_content = b"test file content"
        upload_file = UploadFile(filename="test.pdf", file=BytesIO(file_content))

        mock_tracking = Mock()
        mock_tracking.enviar = AsyncMock(return_value=(True, "OK"))
        mock_tracking.registrar = AsyncMock()

        service = ShipmentStatusService(tracking_svc=mock_tracking)
        payload = ShipmentStatusRequest(code="1")

        result = await service.change_status(db=db, invoice_id=invoice.id, payload=payload, anexo_file=upload_file)

        assert result.status == "ok"
        # Verify tracking was called with attachments
        call_args = mock_tracking.enviar.call_args
        assert call_args.kwargs["anexos"] is not None
        assert len(call_args.kwargs["anexos"]) == 1


@pytest.mark.asyncio
async def test_status_service_with_base64_attachment():
    """Test status change with base64 attachment in payload."""
    async with AsyncSessionLocal() as db:
        shipment = Shipment(service_code="1", emission_status=1)
        db.add(shipment)
        await db.flush()

        invoice = ShipmentInvoice(shipment_id=shipment.id, access_key="12345678901234567890123456789012345678901234")
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)

        mock_tracking = Mock()
        mock_tracking.enviar = AsyncMock(return_value=(True, "OK"))
        mock_tracking.registrar = AsyncMock()

        service = ShipmentStatusService(tracking_svc=mock_tracking)

        # Create attachment with base64 data
        attachment = AttachmentIn(arquivo=AttachmentFile(dados="dGVzdCBmaWxlIGNvbnRlbnQ="))
        payload = ShipmentStatusRequest(code="1", anexos=[attachment])

        result = await service.change_status(db=db, invoice_id=invoice.id, payload=payload)

        assert result.status == "ok"
        call_args = mock_tracking.enviar.call_args
        assert len(call_args.kwargs["anexos"]) == 1


@pytest.mark.asyncio
async def test_status_service_with_recebedor():
    """Test status change persists recebedor on shipment."""
    async with AsyncSessionLocal() as db:
        shipment = Shipment(service_code="1", emission_status=1)
        db.add(shipment)
        await db.flush()

        invoice = ShipmentInvoice(shipment_id=shipment.id, access_key="12345678901234567890123456789012345678901234")
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)

        mock_tracking = Mock()
        mock_tracking.enviar = AsyncMock(return_value=(True, "OK"))
        mock_tracking.registrar = AsyncMock()

        service = ShipmentStatusService(tracking_svc=mock_tracking)

        recebedor_data = {"nDoc": "12345678000199", "xNome": "Empresa Teste", "nFone": "1234567890"}
        payload = ShipmentStatusRequest(code="1", recebedor=recebedor_data)

        await service.change_status(db=db, invoice_id=invoice.id, payload=payload)

        # Refresh and verify recebedor was persisted
        await db.refresh(shipment)
        assert shipment.recebedor_nDoc == "12345678000199"
        assert shipment.recebedor_xNome == "Empresa Teste"
        assert shipment.recebedor_nFone == "1234567890"


@pytest.mark.asyncio
async def test_status_service_invoice_not_found():
    """Test status change with non-existent invoice raises 404."""
    async with AsyncSessionLocal() as db:
        service = ShipmentStatusService()
        payload = ShipmentStatusRequest(code="1")

        with pytest.raises(HTTPException) as exc_info:
            await service.change_status(db=db, invoice_id=99999, payload=payload)

        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_xml_service_extract_chave_success():
    """Test XML chave extraction from valid CTe XML."""
    service = ShipmentXmlService()

    xml_content = b"""<?xml version="1.0"?>
<cteProc>
  <CTe>
    <infCte Id="CTe12345678901234567890123456789012345678901234">
      <ide>
        <chCTe>12345678901234567890123456789012345678901234</chCTe>
      </ide>
    </infCte>
  </CTe>
</cteProc>"""

    chave = service.extract_chave_from_cte_bytes(xml_content)
    assert chave == "12345678901234567890123456789012345678901234"


@pytest.mark.asyncio
async def test_xml_service_extract_chave_from_id_attribute():
    """Test XML chave extraction from Id attribute when chCTe tag is missing."""
    service = ShipmentXmlService()

    xml_content = b"""<?xml version="1.0"?>
<cteProc>
  <CTe>
    <infCte Id="CTe99887766554433221100998877665544332211009988">
    </infCte>
  </CTe>
</cteProc>"""

    chave = service.extract_chave_from_cte_bytes(xml_content)
    assert chave == "99887766554433221100998877665544332211009988"


@pytest.mark.asyncio
async def test_xml_service_upload_xmls_success():
    """Test successful XML upload with chave detection and Brudam send."""
    async with AsyncSessionLocal() as db:
        shipment = Shipment(service_code="1", emission_status=1)
        db.add(shipment)
        await db.flush()

        invoice = ShipmentInvoice(shipment_id=shipment.id)
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)

        xml_content = b"""<?xml version="1.0"?>
<cteProc><CTe><infCte><ide><chCTe>11223344556677889900112233445566778899001122</chCTe></ide></infCte></CTe></cteProc>"""

        upload_file = UploadFile(filename="cte.xml", file=BytesIO(xml_content))

        mock_upload_cte = Mock()
        mock_upload_cte.enviar = AsyncMock(return_value=(True, "Upload successful"))

        service = ShipmentXmlService(upload_cte_svc=mock_upload_cte)

        result = await service.upload_xmls(db=db, invoice_id=invoice.id, xml_files=[upload_file])

        assert result.status is True
        assert result.cte_chave == "11223344556677889900112233445566778899001122"
        assert len(result.xmls_b64) == 1
        mock_upload_cte.enviar.assert_called_once()


@pytest.mark.asyncio
async def test_xml_service_no_files_raises_400():
    """Test upload without files raises HTTPException 400."""
    async with AsyncSessionLocal() as db:
        shipment = Shipment(service_code="1", emission_status=1)
        db.add(shipment)
        await db.flush()

        invoice = ShipmentInvoice(shipment_id=shipment.id)
        db.add(invoice)
        await db.commit()

        service = ShipmentXmlService()

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_xmls(db=db, invoice_id=invoice.id, xml_files=[])

        assert exc_info.value.status_code == 400
        assert "Nenhum arquivo XML enviado" in exc_info.value.detail


@pytest.mark.asyncio
async def test_xml_service_invoice_not_found():
    """Test upload with non-existent invoice raises 404."""
    async with AsyncSessionLocal() as db:
        service = ShipmentXmlService()

        upload_file = UploadFile(filename="test.xml", file=BytesIO(b"<xml/>"))

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_xmls(db=db, invoice_id=99999, xml_files=[upload_file])

        assert exc_info.value.status_code == 404
