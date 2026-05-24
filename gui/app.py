import sys
import asyncio
from PySide6.QtCore import QSharedMemory
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow
from gui.signal_bus import signal_bus
from message_poller import message_poller
from webhook_server import webhook_receiver
from mcp_server import main as mcp_main
from config import config
from services import process_new_message, reprocess_blocked_messages
from utils.logger import logger

_shared_memory = None
_exit_event = None


def _on_poller_toggle(running: bool):
    if running:
        message_poller.set_callback(process_new_message)
        message_poller.start()
    else:
        message_poller.stop()
    signal_bus.poller_status_changed.emit(running)


def _on_process_message(bv_id: str):
    process_new_message({"bv_id": bv_id})


def _on_retry_messages(msg_ids: list):
    from database import database
    for msg_id in msg_ids:
        msg = database.get_message(msg_id)
        if msg:
            process_new_message(msg)


def _on_refresh_requested(_scope: str):
    signal_bus.message_added.emit({"bv_id": ""})


def _cleanup():
    message_poller.stop()
    loop = asyncio.get_event_loop()
    if loop.is_running():
        for task in asyncio.all_tasks(loop):
            task.cancel()
    if _exit_event and not _exit_event.is_set():
        _exit_event.set()


async def run_gui():
    global _shared_memory, _exit_event

    app = QApplication.instance() or QApplication(sys.argv)

    _shared_memory = QSharedMemory("BilibiliAIClient-SingleInstance")
    if not _shared_memory.create(1, QSharedMemory.ReadWrite):
        logger.warning("检测到已有实例运行，退出")
        sys.exit(0)

    app.setStyle("Fusion")
    app.setApplicationName("Bilibili AI Client")
    app.aboutToQuit.connect(_cleanup)

    signal_bus.poller_toggle.connect(_on_poller_toggle)
    signal_bus.login_status_changed.connect(lambda ok: signal_bus.poller_toggle.emit(True) if ok else None)
    signal_bus.process_message.connect(_on_process_message)
    signal_bus.retry_messages.connect(_on_retry_messages)
    signal_bus.refresh_requested.connect(_on_refresh_requested)

    bili_auth = config.get("bili_auth", "")
    if bili_auth and "SESSDATA" in bili_auth:
        signal_bus.poller_toggle.emit(True)

    window = MainWindow()
    window.show()

    loop = asyncio.get_event_loop()
    loop.create_task(mcp_main())
    loop.create_task(webhook_receiver.start())

    _exit_event = asyncio.Event()
    try:
        await _exit_event.wait()
    except asyncio.CancelledError:
        pass
