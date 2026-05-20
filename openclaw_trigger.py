import json
import subprocess
import requests
from typing import Optional, Dict, Any
from utils.logger import logger

class OpenClawTrigger:
    def __init__(self):
        self.mode = "command"
        self.webhook_url = "http://127.0.0.1:18789/hooks/agent"

    def set_mode(self, mode: str):
        self.mode = mode

    def set_webhook_url(self, url: str):
        self.webhook_url = url

    def trigger(self, bv_id: str, subtitle_text: str, sender_uid: str, sender_name: str = "") -> bool:
        message = self._build_message(bv_id, subtitle_text, sender_uid, sender_name)

        if self.mode == "webhook":
            return self._trigger_webhook(message)
        else:
            return self._trigger_command(message)

    def _build_message(self, bv_id: str, subtitle_text: str, sender_uid: str, sender_name: str) -> str:
        sender_info = f"发送者UID: {sender_uid}"
        if sender_name:
            sender_info += f" ({sender_name})"

        return f"""处理视频任务
==========
BV号: {bv_id}
{sender_info}

字幕内容:
{subtitle_text[:5000]}
==========

请生成视频摘要并保存到 ~/.openclaw/workspace/bilibili-summaries/ 目录。
格式: {{日期}}/{{BV号}}.md
"""

    def _trigger_webhook(self, message: str) -> bool:
        try:
            payload = {
                "message": message,
                "name": "bilibili-video",
                "agentId": "main"
            }

            logger.info(f"Triggering OpenClaw via webhook: {self.webhook_url}")
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code in (200, 202):
                logger.info("Webhook trigger successful")
                return True
            else:
                logger.error(f"Webhook trigger failed: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to OpenClaw gateway. Is it running?")
            return False
        except Exception as e:
            logger.error(f"Webhook trigger error: {e}")
            return False

    def _trigger_command(self, message: str) -> bool:
        try:
            logger.info("Triggering OpenClaw via command")

            cmd = ["openclaw", "agent", "--message", message]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                logger.info("Command trigger successful")
                return True
            else:
                logger.error(f"Command trigger failed: {result.stderr}")
                return False

        except FileNotFoundError:
            logger.error("openclaw command not found. Is OpenClaw installed?")
            return False
        except subprocess.TimeoutExpired:
            logger.error("Command timeout")
            return False
        except Exception as e:
            logger.error(f"Command trigger error: {e}")
            return False

    def check_connection(self) -> bool:
        try:
            response = requests.get(
                "http://127.0.0.1:18789/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False


openclaw_trigger = OpenClawTrigger()