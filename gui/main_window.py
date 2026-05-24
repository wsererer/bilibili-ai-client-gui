from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QStackedWidget,
    QLabel, QMenu, QMessageBox, QSystemTrayIcon,
    QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListView,
)
from PySide6.QtCore import Qt, QSettings, QCoreApplication
from PySide6.QtGui import QAction, QIcon, QPixmap, QColor

from config import config

from gui.signal_bus import signal_bus
from gui.theme import ThemeManager
from gui.widgets.sidebar import SidebarWidget
from gui.models.whitelist_model import WhitelistModel
from gui.pages.stats_page import StatsPage
from gui.pages.history_page import HistoryPage
from gui.pages.logs_page import LogsPage
from gui.pages.messages_page import MessagesPage
from gui.pages.settings_page import SettingsPage


class MainWindow(QMainWindow):
    _PAGE_CLASSES = [MessagesPage, HistoryPage, StatsPage, LogsPage, SettingsPage]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bilibili AI Client")
        self.setMinimumSize(900, 600)

        self._settings = QSettings("BilibiliAI", "Client")
        self._pages = [None] * len(self._PAGE_CLASSES)
        ThemeManager.load_theme(theme=config.get("theme", "light"))

        self._setup_menu_bar()
        self._setup_central_widget()
        self._setup_status_bar()

        self._tray = None
        if self._tray_available():
            self._setup_tray()

        self._setup_whitelist()
        self._connect_signals()
        self._restore_window_state()

    @staticmethod
    def _tray_available():
        return QSystemTrayIcon.isSystemTrayAvailable()

    def _setup_menu_bar(self):
        menu_bar = self.menuBar()

        self._file_menu = menu_bar.addMenu("文件")
        act_refresh = QAction("刷新", self)
        act_refresh.triggered.connect(lambda: signal_bus.refresh_requested.emit("all"))
        self._file_menu.addAction(act_refresh)
        self._file_menu.addSeparator()
        act_exit = QAction("退出", self)
        act_exit.triggered.connect(self.close)
        self._file_menu.addAction(act_exit)

        self._view_menu = menu_bar.addMenu("视图")
        act_toggle_theme = QAction("切换深色主题", self)
        act_toggle_theme.triggered.connect(self._on_toggle_theme)
        self._view_menu.addAction(act_toggle_theme)

        self._help_menu = menu_bar.addMenu("帮助")
        act_about = QAction("关于", self)
        act_about.triggered.connect(self._on_about)
        self._help_menu.addAction(act_about)

    def _setup_central_widget(self):
        self.sidebar = SidebarWidget(self)
        self.content_stack = QStackedWidget()
        self._pages[0] = self._PAGE_CLASSES[0](self)
        self.content_stack.addWidget(self._pages[0])

        self._splitter = QSplitter(Qt.Horizontal, self)
        self._splitter.addWidget(self.sidebar)
        self._splitter.addWidget(self.content_stack)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([200, 700])
        self.setCentralWidget(self._splitter)

    def _setup_status_bar(self):
        status_bar = self.statusBar()
        self.status_label = QLabel("就绪")
        status_bar.addWidget(self.status_label)
        self.poll_indicator = QLabel("○ 已停止")
        status_bar.addWidget(self.poll_indicator)
        self.today_label = QLabel("今日: 0")
        status_bar.addPermanentWidget(self.today_label)

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor("#00A1D6"))
        self._tray.setIcon(QIcon(pixmap))
        self._tray.setToolTip("Bilibili AI Client")

        tray_menu = QMenu()
        tray_menu.addAction("显示主窗口", self.show)
        self._poller_running = True
        self._tray_pause_action = tray_menu.addAction("暂停轮询")
        self._tray_pause_action.triggered.connect(self._on_tray_toggle_poller)
        tray_menu.addSeparator()
        tray_menu.addAction("退出", lambda: QCoreApplication.instance().quit())

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()
        QCoreApplication.instance().lastWindowClosed.connect(
            lambda: QCoreApplication.instance().quit()
        )

    def _connect_signals(self):
        signal_bus.page_changed.connect(self.switch_page)
        signal_bus.poller_status_changed.connect(self._on_poller_status_changed)
        signal_bus.stats_updated.connect(self._on_stats_updated)
        signal_bus.theme_changed.connect(self._on_theme_changed)

    def switch_page(self, index: int):
        if not 0 <= index < len(self._PAGE_CLASSES):
            return
        if self._pages[index] is None:
            self._pages[index] = self._PAGE_CLASSES[index](self)
            self.content_stack.addWidget(self._pages[index])
        self.content_stack.setCurrentWidget(self._pages[index])

    def _setup_whitelist(self):
        wl_layout = QVBoxLayout(self.sidebar.content_area)
        wl_layout.setContentsMargins(8, 4, 8, 4)
        wl_layout.setSpacing(4)

        wl_label = QLabel("白名单管理")
        wl_label.setObjectName("whitelistLabel")
        wl_layout.addWidget(wl_label)

        self.wl_uid_input = QLineEdit()
        self.wl_uid_input.setPlaceholderText("UID")
        wl_layout.addWidget(self.wl_uid_input)

        self.wl_name_input = QLineEdit()
        self.wl_name_input.setPlaceholderText("用户名（可选）")
        wl_layout.addWidget(self.wl_name_input)

        btn_row = QHBoxLayout()
        self.wl_add_btn = QPushButton("添加")
        self.wl_add_btn.clicked.connect(self._on_add_whitelist)
        btn_row.addWidget(self.wl_add_btn)

        self.wl_del_btn = QPushButton("删除")
        self.wl_del_btn.clicked.connect(self._on_remove_whitelist)
        btn_row.addWidget(self.wl_del_btn)
        wl_layout.addLayout(btn_row)

        self.whitelist_model = WhitelistModel()
        self.wl_list_view = QListView()
        self.wl_list_view.setModel(self.whitelist_model)
        wl_layout.addWidget(self.wl_list_view)

        signal_bus.whitelist_changed.connect(self.whitelist_model.refresh)

    def _on_add_whitelist(self):
        from database import database

        uid = self.wl_uid_input.text().strip()
        if not uid:
            return
        username = self.wl_name_input.text().strip() or None
        database.add_whitelist(uid, username)
        self.whitelist_model.refresh()
        self.wl_uid_input.clear()
        self.wl_name_input.clear()
        signal_bus.whitelist_changed.emit()
        from services import reprocess_blocked_messages
        reprocess_blocked_messages()

    def _on_remove_whitelist(self):
        from database import database

        indexes = self.wl_list_view.selectedIndexes()
        if not indexes:
            return
        uid = indexes[0].data(Qt.UserRole)
        database.remove_whitelist(uid)
        self.whitelist_model.refresh()
        signal_bus.whitelist_changed.emit()

    def _on_toggle_theme(self):
        ThemeManager.toggle()

    def _on_theme_changed(self, theme: str):
        actions = self._view_menu.actions()
        actions[0].setText("切换深色主题" if theme == "light" else "切换浅色主题")
        config.set("theme", theme)

    def _on_about(self):
        QMessageBox.about(self, "关于", "Bilibili AI Client\n版本 1.1.0")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()

    def _on_tray_toggle_poller(self):
        running = self._tray_pause_action.text() == "暂停轮询"
        signal_bus.poller_toggle.emit(not running)
        self._tray_pause_action.setText("恢复轮询" if running else "暂停轮询")

    def _on_poller_status_changed(self, running: bool):
        self._poller_running = running
        self.poll_indicator.setText("● 轮询中..." if running else "○ 已停止")
        if hasattr(self, '_tray_pause_action'):
            self._tray_pause_action.setText("恢复轮询" if running else "暂停轮询")

    def _on_stats_updated(self, stats: dict):
        self.today_label.setText(f"今日: {stats.get('today', 0)}")

    def _save_window_state(self):
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("splitter", self._splitter.saveState())

    def _restore_window_state(self):
        if self._settings.contains("geometry"):
            self.restoreGeometry(self._settings.value("geometry"))
        if self._settings.contains("splitter"):
            self._splitter.restoreState(self._settings.value("splitter"))

    def closeEvent(self, event):
        if self._tray and self._tray.isVisible():
            self.hide()
            event.ignore()
        else:
            self._save_window_state()
            QCoreApplication.instance().quit()
