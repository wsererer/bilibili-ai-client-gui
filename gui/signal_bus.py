from PySide6.QtCore import QObject, Signal


class SignalBus(QObject):
    message_added = Signal(dict)
    message_status_changed = Signal(str)
    summary_added = Signal(dict)
    stats_updated = Signal(dict)
    whitelist_changed = Signal()
    poller_status_changed = Signal(bool)
    login_status_changed = Signal(bool)
    openclaw_status = Signal(str, bool)
    process_message = Signal(str)
    retry_messages = Signal(list)
    refresh_requested = Signal(str)
    poller_toggle = Signal(bool)
    page_changed = Signal(int)
    theme_changed = Signal(str)
    log_message = Signal(str)


signal_bus = SignalBus()
