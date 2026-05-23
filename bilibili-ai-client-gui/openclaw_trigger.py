import subprocess
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Optional, Callable
from utils.logger import logger
from config import config


class OpenClawTrigger:
    def __init__(self):
        self.openclaw_path = "openclaw"
        self._callback: Optional[Callable] = None
        self._temp_files: list[str] = []

    def set_openclaw_path(self, path: str):
        self.openclaw_path = path

    def set_callback(self, callback: Callable):
        """设置完成回调，签名: callback(bv_id, success, summary_text, error_msg)"""
        self._callback = callback

    def trigger(self, bv_id: str, subtitle_text: str, sender_uid: str, sender_name: str = "") -> bool:
        self._cleanup_temp_files()
        subtitle_path = self._save_subtitle_to_temp(bv_id, subtitle_text)
        message = self._build_message(bv_id, subtitle_path, sender_uid, sender_name)
        success = self._trigger_sync(bv_id, message)
        self._cleanup_temp_files()
        return success

    def _save_subtitle_to_temp(self, bv_id: str, subtitle_text: str) -> str:
        """字幕写入临时文件，返回文件路径，避免长文本含换行符传递到命令行参数"""
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', bv_id or "subtitle")
        fd, path = tempfile.mkstemp(suffix='.txt', prefix=f'{safe_name}_sub_')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(subtitle_text)
        self._temp_files.append(path)
        return path

    def _cleanup_temp_files(self):
        for path in self._temp_files:
            try:
                os.unlink(path)
            except Exception:
                pass
        self._temp_files.clear()

    def _build_message(self, bv_id: str, subtitle_path: str, sender_uid: str, sender_name: str) -> str:
        sender_info = f"发送者UID: {sender_uid}"
        if sender_name:
            sender_info += f" ({sender_name})"

        send_instruction = ""
        auto_send = config.get("auto_send", False)
        if auto_send:
            send_channel = config.get("send_channel", "wechat")
            wechat_target = config.get("wechat_target", "")
            feishu_target = config.get("feishu_target", "")
            if send_channel == "wechat":
                target = f"，目标账号: {wechat_target}" if wechat_target else ""
                send_instruction = f" | 【重要】处理完成后，通过微信发送摘要给用户{target}"
            elif send_channel == "feishu":
                target = f"，目标账号: {feishu_target}" if feishu_target else ""
                send_instruction = f" | 【重要】处理完成后，通过飞书发送摘要给用户{target}"
            elif send_channel == "both":
                target_w = f"，微信目标账号: {wechat_target}" if wechat_target else ""
                target_f = f"，飞书目标账号: {feishu_target}" if feishu_target else ""
                send_instruction = f" | 【重要】处理完成后，通过微信和飞书发送摘要给用户{target_w}{target_f}"

        return (f"处理视频任务 | BV号: {bv_id} | {sender_info} | "
                f"请使用 read 工具读取字幕文件，然后生成视频摘要并保存 | "
                f"字幕文件路径: {subtitle_path} | "
                f"请生成视频摘要并保存到 ~/.openclaw/workspace/bilibili-summaries/ 目录 | "
                f"格式: 日期/BV号.md{send_instruction}")

    def _trigger_sync(self, bv_id: str, message: str) -> bool:
        try:
            cmd = [
                self.openclaw_path, "agent",
                "--message", message,
                "--agent", "main",
                "--json"
            ]
            logger.info(f"Triggering OpenClaw: {self.openclaw_path} agent --agent main --json")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=600,
                cwd=str(Path.home())
            )

            if result.returncode == 0:
                logger.info("OpenClaw command trigger successful")
                if result.stdout:
                    logger.info(f"OpenClaw output: {result.stdout[:500]}")

                summary_text = self._extract_summary_from_output(result.stdout)
                if summary_text:
                    self._notify_callback(bv_id, True, summary_text, None)
                else:
                    summary_from_file = self._try_read_summary_file(bv_id)
                    if summary_from_file:
                        self._notify_callback(bv_id, True, summary_from_file, None)
                    else:
                        self._notify_callback(bv_id, True, result.stdout[:2000] if result.stdout else "处理完成", None)
                return True
            else:
                logger.error(f"OpenClaw command failed (rc={result.returncode}): {result.stderr}")
                self._notify_callback(bv_id, False, None, result.stderr or "处理失败")
                return False

        except FileNotFoundError:
            logger.error(f"openclaw not found at: {self.openclaw_path}")
            self._notify_callback(bv_id, False, None, "openclaw 未找到")
            return False
        except subprocess.TimeoutExpired:
            logger.error(f"OpenClaw timeout for {bv_id}")
            self._notify_callback(bv_id, False, None, "处理超时")
            return False
        except Exception as e:
            logger.error(f"OpenClaw command error: {e}")
            self._notify_callback(bv_id, False, None, str(e))
            return False

    def _extract_summary_from_output(self, output: str) -> Optional[str]:
        """从 OpenClaw 输出中提取摘要内容（支持 JSON 和纯文本）"""
        if not output:
            return None

        # 尝试 JSON 解析
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                # OpenClaw --json 输出格式: {"payloads": [{"text": "...", "mediaUrl": null}], "meta": {...}}
                payloads = data.get("payloads", [])
                if isinstance(payloads, list) and payloads:
                    text = payloads[0].get("text") or payloads[0].get("content")
                    if text:
                        return text.strip()
                # 再尝试顶层 key（兼容其他输出格式）
                for key in ("summary", "content", "text", "message", "result"):
                    val = data.get(key)
                    if val:
                        return str(val).strip()
        except (json.JSONDecodeError, TypeError):
            pass

        # fallback: 正则匹配纯文本格式
        import re
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


openclaw_trigger = OpenClawTrigger()
