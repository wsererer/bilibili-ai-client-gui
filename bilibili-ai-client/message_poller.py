import httpx
import asyncio
import threading
import re
import time
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
                logger.info(f"Response text: {response.text[:500]}")
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

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_sync_poll, daemon=True)
        self.thread.start()
        logger.info("消息轮询已启动")

    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread = None
        logger.info("消息轮询已停止")

    def _run_sync_poll(self):
        logger.info("sync poll thread started")
        processed_ids = set()
        while self.running:
            bili_auth = config.get("bili_auth", "")
            if not bili_auth or "SESSDATA" not in bili_auth:
                logger.warning(f"bili_auth 无效（长度: {len(bili_auth)}），等待重新登录...")
                time.sleep(10)
                continue

            interval = config.get("polling_interval", 30)

            try:
                headers = {
                    "Cookie": bili_auth,
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.bilibili.com/"
                }
                
                new_messages = []
                
                with httpx.Client(timeout=30.0) as client:
                    try:
                        response = client.get(
                            f"{self.base_url}/x/msgfeed/at",
                            headers=headers
                        )
                        data = response.json()

                        if data.get("code") == 0:
                            items = data.get("data", {}).get("items", [])
                            for item in items:
                                msg_id = str(item.get("id", ""))
                                if msg_id in processed_ids:
                                    continue
                                user_info = item.get("user", {})
                                item_content = item.get("item", {})
                                sender_uid = str(user_info.get("mid", ""))
                                sender_name = user_info.get("nickname", "")
                                content = item_content.get("source_content", "")
                                uri = item_content.get("uri", "")
                                bv_id = ""
                                if uri and "video" in uri:
                                    match = re.search(r'BV[\w]+', uri)
                                    if match:
                                        bv_id = match.group(0)
                                new_messages.append({
                                    "msg_id": msg_id,
                                    "bv_id": bv_id,
                                    "sender_uid": sender_uid,
                                    "sender_name": sender_name,
                                    "content": content,
                                    "type": "at"
                                })
                        else:
                            logger.warning(f"Get mentions error: {data.get('message')}")
                    except Exception as e:
                        logger.error(f"Failed to get mentions: {e}")

                    try:
                        response = client.get(
                            f"{self.base_url}/x/dynamic/app/tabs/v2",
                            headers=headers
                        )
                        data = response.json()

                        if data.get("code") == 0:
                            tab_id = data.get("data", {}).get("tabs", [{}])[0].get("id")
                            if tab_id:
                                dyn_response = client.get(
                                    f"{self.base_url}/x/dynamic/app/feed/topic",
                                    params={"tab_id": tab_id, "pagination_str": "{}"},
                                    headers=headers
                                )
                                dyn_data = dyn_response.json()

                                if dyn_data.get("code") == 0:
                                    items = dyn_data.get("data", {}).get("items", [])
                                    for item in items:
                                        msg_id = str(item.get("id_str", ""))
                                        if msg_id in processed_ids:
                                            continue
                                        modules = item.get("modules", {})
                                        card = item.get("card", {})
                                        card_type = card.get("type", "")
                                        if card_type == "DYNAMIC_TYPE_ARCHIVE":
                                            basic_info = modules.get("module_author", {})
                                            bv_id = card.get("bvid", "")
                                            new_messages.append({
                                                "msg_id": msg_id,
                                                "bv_id": bv_id,
                                                "sender_uid": str(basic_info.get("uid", "")),
                                                "sender_name": basic_info.get("name", ""),
                                                "content": card.get("title", ""),
                                                "type": "dynamic"
                                            })
                        else:
                            logger.warning(f"Dynamic API error: {data.get('message')}")
                    except Exception as e:
                        logger.error(f"Failed to get dynamic: {e}")

                if new_messages:
                    logger.info(f"发现 {len(new_messages)} 条新消息")
                    for msg in new_messages:
                        processed_ids.add(msg["msg_id"])
                        if self.callback:
                            self.callback(msg)
                else:
                    logger.debug("无新消息")

            except Exception as e:
                logger.error(f"Sync poll error: {e}")

            time.sleep(interval)


message_poller = MessagePoller()