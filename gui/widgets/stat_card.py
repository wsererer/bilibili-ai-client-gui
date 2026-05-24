from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class StatCard(QFrame):
    def __init__(self, icon: str, title: str, value: str = "0", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setFixedWidth(200)
        self.setFixedHeight(140)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        self.icon_label = QLabel(icon)
        self.icon_label.setObjectName("statIcon")
        self.icon_label.setAlignment(Qt.AlignCenter)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("statTitle")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")
        self.value_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

        self._apply_styles()

    def set_value(self, text: str):
        self.value_label.setText(text)

    def _apply_styles(self):
        self.setObjectName("statCard")
