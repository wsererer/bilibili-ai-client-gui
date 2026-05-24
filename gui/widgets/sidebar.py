from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton, QButtonGroup, QWidget
from PySide6.QtCore import Qt

from gui.signal_bus import signal_bus
from gui.theme import ThemeManager


class SidebarButton(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(40)
        self.setObjectName("navButton")


class SidebarWidget(QFrame):
    NAV_ITEMS = [
        ("📋 消息记录", 0),
        ("📄 摘要历史", 1),
        ("📊 统计", 2),
        ("📝 系统日志", 3),
        ("⚙ 设置", 4),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.app_logo = QLabel("🎬 Bilibili AI Client")
        self.app_logo.setObjectName("appLogo")
        self.app_logo.setAlignment(Qt.AlignCenter)
        self.app_logo.setFixedHeight(60)
        layout.addWidget(self.app_logo)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self._nav_buttons = []

        for text, idx in self.NAV_ITEMS:
            btn = SidebarButton(text)
            self.btn_group.addButton(btn, idx)
            layout.addWidget(btn)
            self._nav_buttons.append(btn)

        self.btn_group.idClicked.connect(self._on_nav_clicked)
        self._nav_buttons[0].setChecked(True)

        self.content_area = QWidget()
        self.content_area.setObjectName("sidebarContentArea")
        layout.addWidget(self.content_area)

        layout.addStretch()

        self.theme_toggle = QPushButton("🌓 切换主题")
        self.theme_toggle.setObjectName("themeToggle")
        self.theme_toggle.setFixedHeight(40)
        self.theme_toggle.clicked.connect(self._on_theme_toggle)
        layout.addWidget(self.theme_toggle)

    def _on_nav_clicked(self, index: int):
        signal_bus.page_changed.emit(index)

    def _on_theme_toggle(self):
        ThemeManager.toggle()


