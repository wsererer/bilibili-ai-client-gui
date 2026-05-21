import subprocess
from utils.logger import logger

class OpenClawTrigger:
    def __init__(self):
        self.openclaw_path = "openclaw"

    def set_openclaw_path(self, path: str):
        self.openclaw_path = path

    def trigger(self, bv_id: str, subtitle_text: str, sender_uid: str, sender_name: str = "") -> bool:
        message = self._build_message(bv_id, subtitle_text, sender_uid, sender_name)
        return self._trigger_command(bv_id, message)

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

    def _trigger_command(self, bv_id: str, message: str) -> bool:
        try:
            session_id = f"bilibili-{bv_id}"
            cmd = [
                self.openclaw_path, "agent",
                "--message", message,
                "--session-id", session_id
            ]
            logger.info(f"Triggering OpenClaw: {self.openclaw_path} agent --session-id {session_id}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode == 0:
                logger.info("OpenClaw command trigger successful")
                if result.stdout:
                    logger.info(f"OpenClaw output: {result.stdout[:500]}")
                return True
            else:
                logger.error(f"OpenClaw command failed (rc={result.returncode}): {result.stderr}")
                return False

        except FileNotFoundError:
            logger.error(f"openclaw not found at: {self.openclaw_path}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("OpenClaw command timeout (120s)")
            return False
        except Exception as e:
            logger.error(f"OpenClaw command error: {e}")
            return False


openclaw_trigger = OpenClawTrigger()
