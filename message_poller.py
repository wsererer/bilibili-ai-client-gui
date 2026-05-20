import httpx
import asyncio
from typing import Optional, Callable
from utils.logger import logger
from config import config


class MessagePoller:
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.callback: Optional[Callable] = None
        self.base_url = "https://api.bilibili.com"
        self.retry_count = 0
        self.max_retries = 5
        self.base_delay = 5

    def set_callback(self, callback: Callable):
        self.callback = callback

    def _get_retry_delay(self) -> float:
        delay = self.base_delay * (2 ** self.retry_count)
        return min(delay, 300)

    def _reset_retry(self):
        self.retry_count = 0

    async def getdynamic(self, bili_auth: str) -> list:
        try:
            headers = {"Cookie": bili_auth}
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/x/dynamic/app/tabs/v2",
                    headers=headers
                )
                data = response.json()

                if data.get("code") != 0:
                    logger.warning(f"Dynamic API error: {data.get('message')}")
                    return []

                tab_id = data.get("data", {}).get("tabs", [{}])[0].get("id")
                if not tab_id:
                    return []

                dyn_response = await client.get(
                    f"{self.base_url}/x/dynamic/app/feed/topic",
                    params={"tab_id": tab_id, "pagination_str": "{}"},
                    headers=headers
                )
                dyn_data = dyn_response.json()

                if dyn_data.get("code") != 0:
                    return []

                items = dyn_data.get("data", {}).get("items", [])
                messages = []

                for item in items:
                    modules = item.get("modules", {})
                    dynamic_module = modules.get("module_dynamic", {})

                    card = item.get("card", {})
                    card_type = card.get("type", "")

                    if card_type == "DYNAMIC_TYPE_ARCHIVE":
                        basic_info = modules.get("module_author", {})
                        bv_id = card.get("bvid", "")

                        messages.append({
                            "msg_id": str(item.get("id_str", "")),
                            "bv_id": bv_id,
                            "sender_uid": str(basic_info.get("uid", "")),
                            "sender_name": basic_info.get("name", ""),
                            "content": card.get("title", ""),
                        })

                return messages

        except Exception as e:
            logger.error(f"Failed to get dynamic: {e}")
            return []

    async def get_mentions(self, bili_auth: str) -> list:
        try:
            headers = {
                "Cookie": bili_auth,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.bilibili.com/"
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info("Calling /x/msgfeed/at API...")
                response = await client.get(
                    f"{self.base_url}/x/msgfeed/at",
                    headers=headers
                )
                logger.info(f"Response status: {response.status_code}")
                data = response.json()

                if data.get("code") != 0:
                    logger.warning(f"Get mentions error: {data.get('message')}")
                    return []

                items = data.get("data", {}).get("items", [])
                logger.info(f"Got {len(items)} items from at feed")
                messages = []

                for item in items:
                    user_info = item.get("user", {})
                    item_content = item.get("item", {})

                    msg_id = str(item.get("id", ""))
                    sender_uid = str(user_info.get("mid", ""))
                    sender_name = user_info.get("nickname", "")
                    content = item_content.get("source_content", "")
                    uri = item_content.get("uri", "")

                    bv_id = ""
                    if uri and "video" in uri:
                        import re
                        match = re.search(r'BV[\w]+', uri)
                        if match:
                            bv_id = match.group(0)

                    if not bv_id and content:
                        bv_id = content[:20]

                    messages.append({
                        "msg_id": msg_id,
                        "bv_id": bv_id,
                        "sender_uid": sender_uid,
                        "sender_name": sender_name,
                        "content": content,
                        "type": "at"
                    })

                if messages:
                    logger.info(f"Found {len(messages)} @ messages")

                return messages

        except Exception as e:
            logger.error(f"Failed to get mentions: {e}")
            return []

    async def get_live_dm(self, bili_auth: str, room_id: str = "22664225") -> list:
        try:
            headers = {"Cookie": bili_auth}
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/xlive/web-room/v1/dm/get_svga_info",
                    params={"id": room_id, "type": "0"},
                    headers=headers
                )
                return []
        except Exception as e:
            logger.error(f"Failed to get live DM: {e}")
            return []

    async def poll_loop(self):
        bili_auth = config.get("bili_auth", "")
        if not bili_auth:
            logger.warning("未设置 bili_auth，无法获取消息")
            await asyncio.sleep(5)
            return

        interval = config.get("polling_interval", 30)

        while self.running:
            try:
                dynamic_msgs = await self.getdynamic(bili_auth)
                mention_msgs = await self.get_mentions(bili_auth)

                all_messages = dynamic_msgs + mention_msgs

                if all_messages:
                    self._reset_retry()
                    for msg in all_messages:
                        if self.callback:
                            self.callback(msg)
                    logger.info(f"获取到 {len(dynamic_msgs)} 条动态, {len(mention_msgs)} 条@消息")
                elif dynamic_msgs is None or mention_msgs is None:
                    self.retry_count += 1
                    if self.retry_count >= self.max_retries:
                        logger.error(f"连续失败 {self.max_retries} 次，等待 {(delay := self._get_retry_delay())} 秒后重试...")
                        await asyncio.sleep(delay)
                        self.retry_count = 0
                    else:
                        logger.warning(f"获取失败，第 {self.retry_count} 次重试")
                        await asyncio.sleep(self._get_retry_delay())

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Polling error: {e}")
                self.retry_count += 1
                await asyncio.sleep(self._get_retry_delay())

            await asyncio.sleep(interval)

    def start(self):
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self.poll_loop())
        logger.info("消息轮询已启动")

    def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            self.task = None
        logger.info("消息轮询已停止")


message_poller = MessagePoller()