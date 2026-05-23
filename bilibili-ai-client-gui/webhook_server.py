import asyncio
from typing import Optional, Callable, Dict, Any
from aiohttp import web
from utils.logger import logger


class WebhookServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 18792):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.app.router.add_post("/webhook", self._handle_webhook)
        self.app.router.add_get("/health", self._handle_health)
        self.callback: Optional[Callable] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None

    def set_callback(self, callback: Callable):
        self.callback = callback

    async def _handle_webhook(self, request):
        try:
            data = await request.json()
            logger.info(f"收到Webhook: {data}")

            if self.callback:
                asyncio.create_task(self._run_callback(data))

            return web.json_response({"status": "ok"})
        except Exception as e:
            logger.error(f"Webhook处理错误: {e}")
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def _handle_health(self, request):
        return web.json_response({"status": "healthy"})

    async def _run_callback(self, data: Dict[str, Any]):
        if self.callback:
            try:
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(data)
                else:
                    self.callback(data)
            except Exception as e:
                logger.error(f"Webhook callback error: {e}")

    async def start(self):
        if self.runner is not None:
            return
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        logger.info(f"Webhook服务已启动 {self.host}:{self.port}")

    async def stop(self):
        if self.site:
            await self.site.stop()
            self.site = None
        if self.runner:
            await self.runner.cleanup()
            self.runner = None
        logger.info("Webhook服务已停止")


class WebhookReceiver:
    def __init__(self):
        self.server: Optional[WebhookServer] = None
        self.callback: Optional[Callable] = None

    def set_callback(self, callback: Callable):
        self.callback = callback

    async def start(self, host: str = "0.0.0.0", port: int = 18792):
        self.server = WebhookServer(host, port)
        self.server.set_callback(self._on_webhook)
        await self.server.start()

    async def stop(self):
        if self.server:
            await self.server.stop()

    def _on_webhook(self, data: Dict[str, Any]):
        msg_type = data.get("type", "")

        if msg_type == "dynamic":
            msg = {
                "msg_id": str(data.get("id", "")),
                "bv_id": data.get("bv_id", ""),
                "sender_uid": str(data.get("uid", "")),
                "sender_name": data.get("uname", ""),
                "content": data.get("content", ""),
            }
        elif msg_type == "live_dm":
            msg = {
                "msg_id": str(data.get("dm_id", "")),
                "bv_id": "",
                "sender_uid": str(data.get("uid", "")),
                "sender_name": data.get("uname", ""),
                "content": data.get("msg", ""),
            }
        else:
            msg = data

        if self.callback:
            self.callback(msg)


webhook_receiver = WebhookReceiver()