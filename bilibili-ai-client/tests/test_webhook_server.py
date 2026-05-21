import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from webhook_server import WebhookReceiver, WebhookServer


class TestWebhookMessageNormalization:
    def test_normalize_dynamic(self):
        receiver = WebhookReceiver()
        payload = {
            "type": "dynamic",
            "bv_id": "BV1xxx",
            "content": "动态内容",
            "sender_uid": "123",
            "sender_name": "用户"
        }
        result = receiver._normalize_message(payload)
        assert result["bv_id"] == "BV1xxx"
        assert result["content"] == "动态内容"

    def test_normalize_live_dm(self):
        receiver = WebhookReceiver()
        payload = {
            "type": "live_dm",
            "bv_id": "BV1yyy",
            "content": "弹幕内容"
        }
        result = receiver._normalize_message(payload)
        assert result["bv_id"] == "BV1yyy"

    def test_normalize_passthrough(self):
        receiver = WebhookReceiver()
        payload = {
            "bv_id": "BV1zzz",
            "msg_id": "msg_001",
            "content": "其他消息"
        }
        result = receiver._normalize_message(payload)
        assert result["bv_id"] == "BV1zzz"


class TestWebhookServerStartStop:
    def test_server_initial_state(self):
        server = WebhookServer(host="127.0.0.1", port=18793)
        assert server.server is None
        assert server.host == "127.0.0.1"
        assert server.port == 18793

    @pytest.mark.asyncio
    async def test_server_start_stop(self):
        server = WebhookServer(host="127.0.0.1", port=18793)
        await server.start()
        assert server.server is not None
        await server.stop()
        assert server.server is None


class TestWebhookEndpoints:
    @pytest.mark.asyncio
    async def test_webhook_endpoint_exists(self):
        server = WebhookServer(host="127.0.0.1", port=18794)
        await server.start()

        import httpx
        client = httpx.AsyncClient()
        try:
            response = await client.post(
                f"http://127.0.0.1:18794/webhook",
                json={"type": "test", "bv_id": "BV1xxx"},
                timeout=5
            )
            assert response.status_code in [200, 400, 500]
        finally:
            await client.aclose()
            await server.stop()