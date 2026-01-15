import pytest
import datetime
from app.services.tracking_service import TrackingService
from app.services.constants import VALID_CODES

@pytest.mark.asyncio
async def test_montar_payload_with_message():
    svc = TrackingService()
    payload = svc.montar_payload("3524CHAVE", "10")
    assert "auth" in payload
    assert "documentos" in payload
    doc = payload["documentos"][0]
    assert doc["chave"] == "3524CHAVE"
    assert isinstance(doc["eventos"], list)
    assert doc["eventos"][0]["codigo"] == int("10")
    # message should come from VALID_CODES when present
    expected_msg = VALID_CODES.get("10", {}).get("message")
    if expected_msg:
        assert expected_msg in doc["eventos"][0]["obs"] or doc["eventos"][0]["obs"] is None


@pytest.mark.asyncio
async def test_enviar_uses_client(monkeypatch):
    async def fake_get_client(self):
        class DummyResp:
            def __init__(self):
                self.status_code = 200
                self.text = "OK"

        class DummyClient:
            async def post(self, endpoint, json, headers):
                return DummyResp()
        return DummyClient()

    monkeypatch.setattr(TrackingService, "_get_client", fake_get_client)
    svc = TrackingService()
    success, text = await svc.enviar("3524CHAVE", "10")
    assert success is True
    assert "OK" in text
