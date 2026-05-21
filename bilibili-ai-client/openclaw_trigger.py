import subprocess
import threading
import re
import json
from pathlib import Path
from typing import Optional, Callable, Dict
from utils.logger import logger


class OpenClawTrigger:
    def __init__(self):
        self.openclaw_path = "openclaw"
        self._callback: Optional[Callable] = None
        self._running_tasks: Dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def set_openclaw_path(self, path: str):
        self.openclaw_path = path

    def set_callback(self, callback: Callable):
        """设置完成回调，签名: callback(bv_id, success, summary_text, error_msg)"""
        self._callback = callback

    def trigger(self, bv_id: str, subtitle_text: str, sender_uid: str, sender_name: str = "") -> bool:
        message = self._build_message(bv_id, subtitle_text, sender_uid, sender_name)
        return self._trigger_async(bv_id, message, sender_uid, sender_name)

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

    def _trigger_async(self, bv_id: str, message: str, sender_uid: str, sender_name: str) -> bool:
        try:
            session_id = f"bilibili-{bv_id}"
            cmd = [
                self.openclaw_path, "agent",
                "--message", message,
                "--session-id", session_id,
                "--json"
            ]
            logger.info(f"Triggering OpenClaw async: {self.openclaw_path} agent --session-id {session_id}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            self._running_tasks[bv_id] = process

            thread = threading.Thread(
                target=self._monitor_process,
                args=(bv_id, process, sender_uid, sender_name),
                daemon=True
            )
            thread.start()

            logger.info(f"OpenClaw process started for {bv_id}, PID: {process.pid}")
            return True

        except FileNotFoundError:
            logger.error(f"openclaw not found at: {self.openclaw_path}")
            self._notify_callback(bv_id, False, None, "openclaw 未找到")
            return False
        except Exception as e:
            logger.error(f"OpenClaw command error: {e}")
            self._notify_callback(bv_id, False, None, str(e))
            return False

    def _monitor_process(self, bv_id: str, process: subprocess.Popen, sender_uid: str, sender_name: str):
        """监控 OpenClaw 进程，处理完成后回调"""
        try:
            stdout, stderr = process.communicate(timeout=600)

            with self._lock:
                if bv_id in self._running_tasks:
                    del self._running_tasks[bv_id]

            if process.returncode == 0:
                logger.info(f"OpenClaw completed successfully for {bv_id}")
                if stdout:
                    logger.info(f"OpenClaw output: {stdout[:500]}")

                summary_text = self._extract_summary_from_output(stdout)
                if summary_text:
                    self._notify_callback(bv_id, True, summary_text, None)
                else:
                    summary_from_file = self._try_read_summary_file(bv_id)
                    if summary_from_file:
                        self._notify_callback(bv_id, True, summary_from_file, None)
                    else:
                        self._notify_callback(bv_id, True, stdout[:2000] if stdout else "处理完成", None)
            else:
                logger.error(f"OpenClaw failed for {bv_id} (rc={process.returncode}): {stderr}")
                self._notify_callback(bv_id, False, None, stderr or "处理失败")

        except subprocess.TimeoutExpired:
            logger.error(f"OpenClaw timeout for {bv_id}")
            process.kill()
            with self._lock:
                if bv_id in self._running_tasks:
                    del self._running_tasks[bv_id]
            self._notify_callback(bv_id, False, None, "处理超时")
        except Exception as e:
            logger.error(f"OpenClaw monitor error for {bv_id}: {e}")
            with self._lock:
                if bv_id in self._running_tasks:
                    del self._running_tasks[bv_id]
            self._notify_callback(bv_id, False, None, str(e))

    def _extract_summary_from_output(self, output: str) -> Optional[str]:
        """从 OpenClaw 输出中提取摘要内容（支持 JSON 和纯文本）"""
        if not output:
            return None

        # 尝试 JSON 解析
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                for key in ("summary", "content", "text", "message", "result"):
                    if data.get(key):
                        return str(data[key]).strip()
        except (json.JSONDecodeError, TypeError):
            pass

        # fallback: 正则匹配纯文本格式
        patterns = [
            r'摘要[：:]\s*\n(.*?)(?=\n={10}|\Z)',
            r'Summary[：:]\s*\n(.*?)(?=\n={10}|\Z)',
            r'## 摘要\s*\n(.*?)(?=\n##|\Z)',
            r'---\s*\n(.*?)(?=\n---|\Z)',
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _try_read_summary_file(self, bv_id: str) -> Optional[str]:
        """尝试读取 OpenClaw 生成的摘要文件"""
        try:
            summary_dir = Path.home() / ".openclaw" / "workspace" / "bilibili-summaries"
            if not summary_dir.exists():
                return None

            for file in summary_dir.rglob("*.md"):
                if bv_id in file.name:
                    return file.read_text(encoding='utf-8').strip()

            return None
        except Exception as e:
            logger.warning(f"Failed to read summary file for {bv_id}: {e}")
            return None

    def _notify_callback(self, bv_id: str, success: bool, summary_text: Optional[str], error_msg: Optional[str]):
        """通知回调"""
        if self._callback:
            try:
                self._callback(bv_id, success, summary_text, error_msg)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def cancel_task(self, bv_id: str):
        """取消正在运行的任务"""
        with self._lock:
            if bv_id in self._running_tasks:
                process = self._running_tasks[bv_id]
                process.kill()
                del self._running_tasks[bv_id]
                logger.info(f"Cancelled OpenClaw task for {bv_id}")

    def get_running_tasks(self) -> list:
        """获取正在运行的任务列表"""
        with self._lock:
            return list(self._running_tasks.keys())


openclaw_trigger = OpenClawTrigger()
