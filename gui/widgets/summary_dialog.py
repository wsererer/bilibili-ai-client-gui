from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit,
    QDialogButtonBox, QFrame,
)


class SummaryDetailDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        bv_id = data.get("bv_id", "")
        self.setWindowTitle(f"摘要详情 - {bv_id}")
        self.setMinimumSize(500, 400)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"BV号: {bv_id}"))
        layout.addWidget(QLabel(f"发送者: {data.get('sender_name', '')}"))
        layout.addWidget(QLabel(f"时间: {data.get('created_at', '')}"))

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        layout.addWidget(QLabel("字幕内容:"))
        subtitle = QTextEdit()
        subtitle.setReadOnly(True)
        subtitle.setText(data.get("subtitle_text", ""))
        layout.addWidget(subtitle)

        layout.addWidget(QLabel("摘要:"))
        summary = QTextEdit()
        summary.setReadOnly(True)
        summary.setText(data.get("summary_text", ""))
        layout.addWidget(summary)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
