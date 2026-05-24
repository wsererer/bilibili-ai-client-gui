import sys
import asyncio
import qasync
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import config
from utils.logger import logger
from message_poller import message_poller
from webhook_server import webhook_receiver
from mcp_server import main as mcp_main
from services import process_new_message


def parse_args():
    parser = argparse.ArgumentParser(description="Bilibili AI Client")
    parser.add_argument("--mode", choices=["gui", "mcp", "webhook", "all"], default="all",
                        help="运行模式: gui=仅GUI, mcp=仅MCP服务, webhook=Webhook接收, all=全部")
    parser.add_argument("--config", type=str, default=None,
                        help="配置文件路径")
    parser.add_argument("--port", type=int, default=None,
                        help="Webhook服务端口")
    return parser.parse_args()


async def run_gui_with_services():
    from gui.app import run_gui
    await run_gui()


def main():
    args = parse_args()
    logger.info(f"启动 Bilibili AI Client，模式: {args.mode}")
    port = args.port or config.get("webhook_port", 18792)

    try:
        if args.mode == "mcp":
            asyncio.run(mcp_main())
        elif args.mode == "webhook":
            webhook_receiver.set_callback(process_new_message)
            asyncio.run(webhook_receiver.start(port=port))
        elif args.mode == "all":
            webhook_receiver.set_callback(process_new_message)
            qasync.run(run_gui_with_services())
        else:
            qasync.run(run_gui_with_services())
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    except Exception as e:
        logger.error(f"运行错误: {e}")
    finally:
        message_poller.stop()


if __name__ == "__main__":
    main()
