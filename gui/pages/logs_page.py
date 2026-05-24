from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QComboBox, QLineEdit, QCheckBox, QPushButton,
)
from PySide6.QtGui import QFont, QTextCursor

from gui.signal_bus import signal_bus
from utils.logger import logger


class LogsPage(QWidget):
    LEVELS = ["全部", "DEBUG", "INFO", "WARNING", "ERROR"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LogsPage")

        self._level_filter = ""
        self._search_text = ""
        self._messages = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 4, 8, 4)
        toolbar.setSpacing(8)

        self.level_combo = QComboBox()
        self.level_combo.addItems(self.LEVELS)
        self.level_combo.currentTextChanged.connect(self._on_filter_changed)
        toolbar.addWidget(self.level_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索日志关键字...")
        self.search_input.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.search_input)

        toolbar.addStretch()

        self.auto_scroll_cb = QCheckBox("自动滚动")
        self.auto_scroll_cb.setChecked(True)
        toolbar.addWidget(self.auto_scroll_cb)

        self.clear_btn = QPushButton("清屏")
        self.clear_btn.clicked.connect(self._on_clear)
        toolbar.addWidget(self.clear_btn)

        layout.addLayout(toolbar)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(10000)
        self.log_view.setFont(QFont("Consolas", 10))
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.log_view)

        signal_bus.log_message.connect(self._on_log_message)

        self._sink_id = logger.add(
            self._log_sink,
            format="{time:HH:mm:ss} [{level}] {module}:{line} - {message}",
        )

    def _log_sink(self, msg: str):
        signal_bus.log_message.emit(msg)

    def _on_log_message(self, msg: str):
        self._messages.append(msg)
        if len(self._messages) > 10000:
            self._messages = self._messages[-5000:]
        self._append_if_matches(msg)

    def _append_if_matches(self, msg: str):
        if not self._passes_filter(msg):
            return
        self.log_view.appendPlainText(msg)
        if self.auto_scroll_cb.isChecked():
            self.log_view.moveCursor(QTextCursor.MoveOperation.End)

    def _passes_filter(self, msg: str) -> bool:
        if self._level_filter:
            level = self._parse_level(msg)
            if level != self._level_filter:
                return False
        if self._search_text and self._search_text not in msg.lower():
            return False
        return True

    @staticmethod
    def _parse_level(msg: str) -> str:
        first_open = msg.find("[")
        first_close = msg.find("]")
        if first_open != -1 and first_close != -1 and first_close > first_open:
            return msg[first_open + 1:first_close]
        return ""

    def _on_filter_changed(self, text: str):
        self._level_filter = "" if text == "全部" else text
        self._reapply_filter()

    def _on_search_changed(self, text: str):
        self._search_text = text.lower() if text else ""
        self._reapply_filter()

    def _reapply_filter(self):
        self.log_view.setUpdatesEnabled(False)
        self.log_view.clear()
        for msg in self._messages:
            self._append_if_matches(msg)
        self.log_view.setUpdatesEnabled(True)

    def _on_clear(self):
        self._messages.clear()
        self.log_view.clear()

    def cleanup(self):
        logger.remove(self._sink_id)
