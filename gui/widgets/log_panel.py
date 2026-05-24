from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QPlainTextEdit, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor

from gui.signal_bus import signal_bus


class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LogPanel")
        self._expanded = False
        self._messages = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toggle_btn = QPushButton("📝 系统日志  ▶")
        self.toggle_btn.setObjectName("logPanelToggle")
        self.toggle_btn.setFlat(True)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setFixedHeight(28)
        self.toggle_btn.clicked.connect(self._on_toggle)
        layout.addWidget(self.toggle_btn)

        self._content = QWidget()
        self._content.setObjectName("logPanelContent")
        self._content.setVisible(False)
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(8, 4, 8, 4)
        content_layout.setSpacing(4)

        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logPanelLogView")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(200)
        self.log_view.setFont(QFont("Consolas", 10))
        self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_view.setMaximumHeight(180)
        self.log_view.mouseDoubleClickEvent = self._on_double_click
        content_layout.addWidget(self.log_view)

        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 0, 0, 0)
        bottom_bar.setSpacing(8)
        self.info_label = QLabel("显示最近 200 条，完整日志见系统日志页")
        self.info_label.setObjectName("logPanelInfoLabel")
        bottom_bar.addWidget(self.info_label)
        bottom_bar.addStretch()
        open_btn = QPushButton("打开完整日志")
        open_btn.setObjectName("logPanelOpenBtn")
        open_btn.setFixedHeight(24)
        open_btn.clicked.connect(lambda: signal_bus.page_changed.emit(3))
        bottom_bar.addWidget(open_btn)
        content_layout.addLayout(bottom_bar)

        layout.addWidget(self._content)

        signal_bus.log_message.connect(self._on_log_message)

    def _on_toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self.toggle_btn.setText("📝 系统日志  ▼" if self._expanded else "📝 系统日志  ▶")

    def _on_log_message(self, msg: str):
        self._messages.append(msg)
        if len(self._messages) > 200:
            self._messages.pop(0)
        self.log_view.appendPlainText(msg)
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)

    def _on_double_click(self, event):
        signal_bus.page_changed.emit(3)

    def clear(self):
        self._messages.clear()
        self.log_view.clear()

    def cleanup(self):
        try:
            signal_bus.log_message.disconnect(self._on_log_message)
        except TypeError:
            pass
