import sys
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import config
from database import database
from utils.logger import logger
from message_poller import message_poller
from webhook_server import webhook_receiver
from mcp_server import main as mcp_main
from openclaw_trigger import openclaw_trigger
from utils.subtitle_extractor import subtitle_extractor


def parse_args():
    parser = argparse.ArgumentParser(description="Bilibili AI Client")
    parser.add_argument("--mode", choices=["gui", "mcp", "webhook", "all"], default="all",
                        help="运行模式: gui=仅GUI, mcp=仅MCP服务, webhook=Webhook接收, all=全部")
    parser.add_argument("--config", type=str, default=None,
                        help="配置文件路径")
    parser.add_argument("--port", type=int, default=None,
                        help="Webhook服务端口")
    return parser.parse_args()


def on_openclaw_complete(bv_id: str, success: bool, summary_text: str, error_msg: str):
    """OpenClaw 处理完成回调"""
    if success and summary_text:
        logger.info(f"OpenClaw 处理完成: {bv_id}, 摘要长度: {len(summary_text)}")

        messages = database.get_messages_by_bv_id(bv_id)
        sender_uid = ""
        sender_name = ""
        subtitle_text = ""
        for msg in messages:
            sender_uid = msg.get("sender_uid", "")
            sender_name = msg.get("sender_name", "")
            subtitle_text = msg.get("content", "")
            break

        database.add_summary(
            bv_id=bv_id,
            sender_uid=sender_uid,
            sender_name=sender_name,
            subtitle_text=subtitle_text,
            summary_text=summary_text
        )

        triggered_messages = database.get_messages_by_bv_id(bv_id, "triggered")
        for msg in triggered_messages:
            database.update_message_status(msg["id"], "processed")
            break

        logger.info(f"摘要已保存到数据库: {bv_id}")
    else:
        logger.error(f"OpenClaw 处理失败: {bv_id}, 错误: {error_msg}")

        triggered_messages = database.get_messages_by_bv_id(bv_id, "triggered")
        for msg in triggered_messages:
            database.update_message_status(msg["id"], "openclaw_failed")
            break


async def process_new_message(msg: dict):
    logger.info(f"process_new_message called with: {msg}")
    bv_id = msg.get("bv_id", "")
    sender_uid = msg.get("sender_uid", "")

    if not bv_id and not msg.get("content"):
        logger.info("No bv_id and no content, skipping")
        return

    msg_id = msg.get("msg_id", f"{bv_id}_{sender_uid}" if bv_id else msg.get("content", "")[:20])

    existing = database.get_message(msg_id)
    if existing and existing.get("status") not in ("pending", "not_whitelisted"):
        logger.info(f"消息 {msg_id} 已处理过 (status={existing.get('status')})，跳过")
        return

    is_whitelisted = database.is_whitelist(sender_uid)
    logger.info(f"sender_uid: {sender_uid}, is_whitelisted: {is_whitelisted}")

    database.add_message(
        msg_id=msg_id,
        sender_uid=sender_uid,
        sender_name=msg.get("sender_name", ""),
        bv_id=bv_id or "unknown",
        content=msg.get("content", "")
    )

    if not sender_uid:
        database.update_message_status(msg_id, "no_sender_uid")
        logger.info(f"消息 {msg_id} 无发送者UID，已记录")
        return

    if not is_whitelisted:
        database.update_message_status(msg_id, "not_whitelisted")
        logger.info(f"用户 {sender_uid} 不在白名单，已记录")
        return
    logger.info(f"Message added to DB: {msg_id}")

    logger.info(f"处理消息: {bv_id or 'N/A'} from {msg.get('sender_name', sender_uid)}")

    if bv_id and bv_id != "unknown":
        subtitle_text = subtitle_extractor.extract_text(f"https://www.bilibili.com/video/{bv_id}")

        if subtitle_text:
            openclaw_trigger.set_openclaw_path(config.get("openclaw_path", "openclaw"))
            openclaw_trigger.set_callback(on_openclaw_complete)
            success = openclaw_trigger.trigger(
                bv_id=bv_id,
                subtitle_text=subtitle_text,
                sender_uid=sender_uid,
                sender_name=msg.get("sender_name", "")
            )
            if success:
                database.update_message_status(msg_id, "triggered")
                logger.info(f"已触发OpenClaw处理: {bv_id}")
            else:
                database.update_message_status(msg_id, "trigger_failed")
        else:
            database.update_message_status(msg_id, "no_subtitle")
            logger.warning(f"无法获取字幕: {bv_id}")


async def reprocess_blocked_messages(uid=None):
    blocked = database.get_not_whitelisted_messages()
    if not blocked:
        return
    logger.info(f"重新处理 {len(blocked)} 条被拦截的消息")
    for msg in blocked:
        msg_id = msg.get("id", "")
        sender_uid = msg.get("sender_uid", "")
        if uid and sender_uid != uid:
            continue
        if database.is_whitelist(sender_uid):
            database.update_message_status(msg_id, "pending")
            logger.info(f"消息 {msg_id} 用户 {sender_uid} 已加入白名单，重新处理")
            await process_new_message({
                "msg_id": msg_id,
                "bv_id": msg.get("bv_id", ""),
                "sender_uid": sender_uid,
                "sender_name": msg.get("sender_name", ""),
                "content": msg.get("content", ""),
            })


async def run_gui_with_services():
    from gui.main_window import MainWindow

    async_loop = asyncio.get_running_loop()
    logger.info(f"Got event loop: {async_loop}")

    if config.get("auto_start", True):
        logger.info(f"auto_start is True, config.bili_auth: {config.get('bili_auth', '')[:30] if config.get('bili_auth') else 'EMPTY'}...")
        def wrapped_callback(msg):
            logger.info(f"Callback triggered for msg: {msg.get('msg_id')}")
            try:
                future = asyncio.run_coroutine_threadsafe(process_new_message(msg), async_loop)
                future.result(timeout=300)
            except Exception as e:
                logger.error(f"Error processing message: {e}")
        message_poller.set_callback(wrapped_callback)
        logger.info("Starting message_poller...")
        message_poller.start()
        logger.info(f"message_poller.running = {message_poller.running}")
    else:
        logger.info("auto_start is False, skipping message_poller start")

    mcp_task = asyncio.create_task(mcp_main())

    app = MainWindow()
    app.run()

    mcp_task.cancel()
    try:
        await mcp_task
    except asyncio.CancelledError:
        pass
    message_poller.stop()


def main():
    args = parse_args()

    logger.info(f"启动 Bilibili AI Client，模式: {args.mode}")

    port = args.port or config.get("webhook_port", 18792)

    try:
        if args.mode == "mcp":
            asyncio.run(mcp_main())
        elif args.mode == "webhook":
            webhook_receiver.set_callback(lambda msg: asyncio.create_task(process_new_message(msg)))
            asyncio.run(webhook_receiver.start(port=port))
        elif args.mode == "gui" or args.mode == "all":
            asyncio.run(run_gui_with_services())
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    except Exception as e:
        logger.error(f"运行错误: {e}")
    finally:
        message_poller.stop()


if __name__ == "__main__":
    main()