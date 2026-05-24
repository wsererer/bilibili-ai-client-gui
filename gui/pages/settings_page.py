from PySide6.QtCore import QObject, QThread, QTimer, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QScrollArea, QWidget, QFormLayout, QGroupBox, QLineEdit,
    QPushButton, QSpinBox, QCheckBox, QRadioButton, QButtonGroup,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox,
    QDialog, QTextEdit, QDialogButtonBox, QLabel,
)

from config import config
from gui.signal_bus import signal_bus
from utils.app_data import APP_DATA_DIR

_login_shutdown_added = False


def _ensure_login_shutdown():
    global _login_shutdown_added
    if _login_shutdown_added:
        return
    from bilibili_login import app as _login_flask_app
    import flask as _flask

    @_login_flask_app.route('/shutdown', methods=['POST'])
    def _shutdown():
        func = _flask.request.environ.get('werkzeug.server.shutdown')
        if func:
            func()
        return 'ok'
    _login_shutdown_added = True


class _LoginWorker(QObject):
    @Slot()
    def run(self):
        from bilibili_login import run_login_server
        run_login_server(51888)


class SettingsPage(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsPage")
        self.setWidgetResizable(True)

        self._login_thread = None
        self._login_timer = None

        container = QWidget()
        self.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        self._build_auth_group(layout)
        self._build_polling_group(layout)
        self._build_openclaw_group(layout)
        self._build_webhook_group(layout)
        self._build_push_group(layout)

        self.btn_save = QPushButton("保存设置")
        self.btn_save.clicked.connect(self._on_save)
        layout.addWidget(self.btn_save)
        layout.addStretch()

        self._update_push_enabled()

        signal_bus.login_status_changed.connect(lambda logged_in: self._update_auth_status())

    def _build_auth_group(self, parent: QVBoxLayout):
        group = QGroupBox("B站认证")
        form = QFormLayout(group)

        self.auth_status = QLineEdit()
        self.auth_status.setReadOnly(True)
        self._update_auth_status()
        form.addRow("Cookie状态:", self.auth_status)

        btn_row = QHBoxLayout()
        self.btn_web_login = QPushButton("网页登录")
        self.btn_web_login.clicked.connect(self._on_web_login)
        self.btn_manual_cookie = QPushButton("手动输入Cookie")
        self.btn_manual_cookie.clicked.connect(self._on_manual_cookie)
        self.btn_clear_cookie = QPushButton("清除登录")
        self.btn_clear_cookie.clicked.connect(self._on_clear_cookie)
        btn_row.addWidget(self.btn_web_login)
        btn_row.addWidget(self.btn_manual_cookie)
        btn_row.addWidget(self.btn_clear_cookie)
        form.addRow(btn_row)

        parent.addWidget(group)

    def _build_polling_group(self, parent: QVBoxLayout):
        group = QGroupBox("轮询设置")
        form = QFormLayout(group)

        self.polling_interval = QSpinBox()
        self.polling_interval.setRange(5, 300)
        self.polling_interval.setSuffix(" 秒")
        self.polling_interval.setValue(config.get("polling_interval", 30))
        form.addRow("轮询间隔:", self.polling_interval)

        self.auto_start = QCheckBox("启动时自动轮询")
        self.auto_start.setChecked(config.get("auto_start", True))
        form.addRow(self.auto_start)

        parent.addWidget(group)

    def _build_openclaw_group(self, parent: QVBoxLayout):
        group = QGroupBox("OpenClaw")
        form = QFormLayout(group)

        path_row = QHBoxLayout()
        self.openclaw_path = QLineEdit()
        self.openclaw_path.setText(config.get("openclaw_path", "openclaw"))
        self.btn_browse_openclaw = QPushButton("浏览")
        self.btn_browse_openclaw.clicked.connect(self._on_browse_openclaw)
        path_row.addWidget(self.openclaw_path)
        path_row.addWidget(self.btn_browse_openclaw)
        form.addRow("OpenClaw路径:", path_row)

        parent.addWidget(group)

    def _build_webhook_group(self, parent: QVBoxLayout):
        group = QGroupBox("Webhook")
        form = QFormLayout(group)

        self.webhook_port = QSpinBox()
        self.webhook_port.setRange(1024, 65535)
        self.webhook_port.setValue(config.get("webhook_port", 18792))
        form.addRow("Webhook端口:", self.webhook_port)

        parent.addWidget(group)

    def _build_push_group(self, parent: QVBoxLayout):
        group = QGroupBox("摘要推送")
        form = QFormLayout(group)

        self.auto_send = QCheckBox("启用自动推送")
        self.auto_send.setChecked(config.get("auto_send", False))
        self.auto_send.toggled.connect(self._update_push_enabled)
        form.addRow(self.auto_send)

        channel_row = QHBoxLayout()
        self.send_channel_group = QButtonGroup(self)
        self.rb_wechat = QRadioButton("微信")
        self.rb_feishu = QRadioButton("飞书")
        self.rb_both = QRadioButton("两者")
        self.send_channel_group.addButton(self.rb_wechat, 0)
        self.send_channel_group.addButton(self.rb_feishu, 1)
        self.send_channel_group.addButton(self.rb_both, 2)
        channel_row.addWidget(self.rb_wechat)
        channel_row.addWidget(self.rb_feishu)
        channel_row.addWidget(self.rb_both)

        channel = config.get("send_channel", "wechat")
        if channel == "wechat":
            self.rb_wechat.setChecked(True)
        elif channel == "feishu":
            self.rb_feishu.setChecked(True)
        elif channel == "both":
            self.rb_both.setChecked(True)

        form.addRow("推送渠道:", channel_row)

        self.wechat_target = QLineEdit()
        self.wechat_target.setText(config.get("wechat_target", ""))
        form.addRow("微信目标:", self.wechat_target)

        self.feishu_target = QLineEdit()
        self.feishu_target.setText(config.get("feishu_target", ""))
        form.addRow("飞书目标:", self.feishu_target)

        parent.addWidget(group)

    def _update_auth_status(self):
        cookie = config.get("bili_auth", "")
        self.auth_status.setText("已登录(加密存储)" if cookie else "未登录")

    def _update_push_enabled(self):
        enabled = self.auto_send.isChecked()
        self.rb_wechat.setEnabled(enabled)
        self.rb_feishu.setEnabled(enabled)
        self.rb_both.setEnabled(enabled)
        self.wechat_target.setEnabled(enabled)
        self.feishu_target.setEnabled(enabled)

    def _check_login_result(self):
        cookie = config.get("bili_auth", "")
        if cookie and "SESSDATA" in cookie:
            signal_bus.login_status_changed.emit(True)
            if self._login_timer:
                self._login_timer.stop()
                self._login_timer = None
            try:
                import httpx
                httpx.post("http://127.0.0.1:51888/shutdown", timeout=1)
            except Exception:
                pass

    def _on_web_login(self):
        if config.get("bili_auth", ""):
            QMessageBox.information(self, "提示", "已登录")
            return
        _ensure_login_shutdown()
        self._login_thread = QThread()
        self._login_worker = _LoginWorker()
        self._login_worker.moveToThread(self._login_thread)
        self._login_thread.started.connect(self._login_worker.run)
        self._login_thread.finished.connect(self._login_worker.deleteLater)
        self._login_thread.finished.connect(self._login_thread.deleteLater)
        self._login_thread.start()
        QTimer.singleShot(1000, lambda: QDesktopServices.openUrl(QUrl("http://127.0.0.1:51888")))
        self._login_timer = QTimer(self)
        self._login_timer.timeout.connect(self._check_login_result)
        self._login_timer.start(1000)

    def _on_manual_cookie(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("手动输入Cookie")
        vbox = QVBoxLayout(dialog)

        current_cookie = config.get("bili_auth", "")
        if current_cookie:
            vbox.addWidget(QLabel("当前Cookie:"))
            masked = QLineEdit("********")
            masked.setReadOnly(True)
            vbox.addWidget(masked)

        vbox.addWidget(QLabel("请输入新的Cookie:"))
        editor = QTextEdit()
        vbox.addWidget(editor)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        vbox.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            cookie_text = editor.toPlainText().strip()
            if cookie_text:
                config.set("bili_auth", cookie_text)
                self._update_auth_status()
                signal_bus.login_status_changed.emit(True)

    def _on_clear_cookie(self):
        config.set("bili_auth", "")
        cookie_file = APP_DATA_DIR / "login_cookie.txt"
        if cookie_file.exists():
            cookie_file.unlink()
        self._update_auth_status()
        signal_bus.login_status_changed.emit(False)

    def _on_browse_openclaw(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择OpenClaw可执行文件")
        if path:
            self.openclaw_path.setText(path)

    def _on_save(self):
        config.set("polling_interval", self.polling_interval.value())
        config.set("auto_start", self.auto_start.isChecked())
        config.set("openclaw_path", self.openclaw_path.text())
        config.set("webhook_port", self.webhook_port.value())
        config.set("auto_send", self.auto_send.isChecked())

        channel_id = self.send_channel_group.checkedId()
        channel_map = {0: "wechat", 1: "feishu", 2: "both"}
        config.set("send_channel", channel_map.get(channel_id, "wechat"))

        config.set("wechat_target", self.wechat_target.text())
        config.set("feishu_target", self.feishu_target.text())

        QMessageBox.information(self, "保存成功", "设置已保存")
