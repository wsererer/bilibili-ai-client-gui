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


async def process_new_message(msg: dict):
    logger.info(f"process_new_message called with: {msg}")
    bv_id = msg.get("bv_id", "")
    sender_uid = msg.get("sender_uid", "")

    if not bv_id and not msg.get("content"):
        logger.info("No bv_id and no content, skipping")
        return

    is_whitelisted = database.is_whitelist(sender_uid)
    logger.info(f"sender_uid: {sender_uid}, is_whitelisted: {is_whitelisted}")

    if sender_uid and not is_whitelisted:
        logger.info(f"用户 {sender_uid} 不在白名单，跳过")
        return

    msg_id = msg.get("msg_id", f"{bv_id}_{sender_uid}" if bv_id else msg.get("content", "")[:20])

    existing = database.get_message(msg_id)
    if existing and existing.get("status") != "pending":
        logger.info(f"消息 {msg_id} 已处理过 (status={existing.get('status')})，跳过")
        return

    database.add_message(
        msg_id=msg_id,
        sender_uid=sender_uid,
        sender_name=msg.get("sender_name", ""),
        bv_id=bv_id or "unknown",
        content=msg.get("content", "")
    )
    logger.info(f"Message added to DB: {msg_id}")

    logger.info(f"处理消息: {bv_id or 'N/A'} from {msg.get('sender_name', sender_uid)}")

    if bv_id and bv_id != "unknown":
        subtitle_text = subtitle_extractor.extract_text(f"https://www.bilibili.com/video/{bv_id}")

        if subtitle_text:
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


async def run_gui_with_services():
    from gui.main_window import MainWindow

    async_loop = asyncio.get_running_loop()
    logger.info(f"Got event loop: {async_loop}")

    if config.get("auto_start", True):
        logger.info(f"auto_start is True, config.bili_auth: {config.get('bili_auth', '')[:30] if config.get('bili_auth') else 'EMPTY'}...")
        def wrapped_callback(msg):
            logger.info(f"Callback triggered for msg: {msg.get('msg_id')}")
            # Process message synchronously since we're calling from a non-async thread
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(process_new_message(msg))
                loop.close()
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