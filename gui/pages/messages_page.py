from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QTableView, QComboBox, QDialog, QListWidget, QListWidgetItem,
    QMenu,
)
from PySide6.QtCore import Qt, QSortFilterProxyModel

from gui.signal_bus import signal_bus
from gui.models.message_model import MessageTableModel
from database import database


class MessageFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterKeyColumn(-1)
        self._status_filter = ""

    def set_status_filter(self, status: str):
        self._status_filter = status
        self.invalidate()

    def filterAcceptsRow(self, source_row, source_parent):
        if not super().filterAcceptsRow(source_row, source_parent):
            return False
        if self._status_filter:
            idx = self.sourceModel().index(source_row, 0)
            status = self.sourceModel().data(idx, MessageTableModel.STATUS_ROLE)
            if self._status_filter == "failed":
                if status not in ("failed", "trigger_failed", "openclaw_failed", "no_subtitle"):
                    return False
            elif status != self._status_filter:
                return False
        return True


class FailureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("失败管理")
        self.setMinimumSize(500, 400)
        layout = QVBoxLayout(self)
        self._list = QListWidget()
        layout.addWidget(self._list)
        btn_layout = QHBoxLayout()
        self._retry_btn = QPushButton("重试选中")
        self._retry_all_btn = QPushButton("重试全部")
        btn_layout.addWidget(self._retry_btn)
        btn_layout.addWidget(self._retry_all_btn)
        btn_layout.addStretch()
        self._close_btn = QPushButton("关闭")
        btn_layout.addWidget(self._close_btn)
        layout.addLayout(btn_layout)
        self._connect_signals()
        self._load_failed()

    def _connect_signals(self):
        self._retry_btn.clicked.connect(self._on_retry_selected)
        self._retry_all_btn.clicked.connect(self._on_retry_all)
        self._close_btn.clicked.connect(self.accept)

    def _load_failed(self):
        self._list.clear()
        self._failed_items = database.get_failed_messages()
        for item in self._failed_items:
            text = f"[{item.get('bv_id', '')}] {item.get('sender_name', '')} - {item.get('status', '')}"
            list_item = QListWidgetItem(text)
            list_item.setData(Qt.UserRole, item.get("id", ""))
            self._list.addItem(list_item)

    def _on_retry_selected(self):
        items = self._list.selectedItems()
        if not items:
            return
        msg_ids = [item.data(Qt.UserRole) for item in items]
        for msg_id in msg_ids:
            database.reset_message_status(msg_id, "pending")
            signal_bus.message_status_changed.emit(msg_id)
        signal_bus.retry_messages.emit(msg_ids)
        self._load_failed()

    def _on_retry_all(self):
        msg_ids = [item.get("id", "") for item in self._failed_items]
        for msg_id in msg_ids:
            database.reset_message_status(msg_id, "pending")
            signal_bus.message_status_changed.emit(msg_id)
        signal_bus.retry_messages.emit(msg_ids)
        self._load_failed()


class MessagesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MessagesPage")
        self._model = MessageTableModel(self)
        self._proxy = MessageFilterProxy(self)
        self._proxy.setSourceModel(self._model)
        self._setup_ui()
        self._connect_signals()
        self._model.refresh()
        self._setup_context_menu()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self._btn_process = QPushButton("处理选中")
        self._btn_process.setEnabled(False)
        toolbar.addWidget(self._btn_process)
        self._btn_failure = QPushButton("失败管理")
        toolbar.addWidget(self._btn_failure)
        toolbar.addStretch()
        self._status_filter = QComboBox()
        self._status_filter.addItems(["全部", "待处理", "已处理", "失败"])
        toolbar.addWidget(self._status_filter)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索 BV 号或发送者...")
        toolbar.addWidget(self._search_input)
        layout.addLayout(toolbar)
        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableView.ExtendedSelection)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().hide()
        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        layout.addWidget(self._table)

    def _connect_signals(self):
        self._search_input.textChanged.connect(self._on_search)
        self._status_filter.currentTextChanged.connect(self._on_status_filter_changed)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._btn_process.clicked.connect(self.process_selected)
        self._table.doubleClicked.connect(self.process_selected)
        self._btn_failure.clicked.connect(self._on_failure_management)
        signal_bus.message_added.connect(self._on_message_added)
        signal_bus.message_status_changed.connect(self._on_message_status_changed)
        signal_bus.summary_added.connect(lambda _: self._model.refresh())

    def _setup_context_menu(self):
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_context_menu)

    def _on_context_menu(self, pos):
        index = self._table.indexAt(pos)
        if not index.isValid():
            return
        source_index = self._proxy.mapToSource(index)
        row = source_index.row()
        if row < 0 or row >= len(self._model._data):
            return
        item = self._model._data[row]
        menu = QMenu(self)
        act_process = menu.addAction("处理")
        act_reset = menu.addAction("重置")
        act_detail = menu.addAction("详情")
        act_delete = menu.addAction("删除")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == act_process:
            msg_id = item.get("id", "")
            bv_id = item.get("bv_id", "")
            if bv_id and bv_id != "unknown" and msg_id:
                signal_bus.retry_messages.emit([msg_id])
        elif action == act_reset:
            msg_id = item.get("id", "")
            database.reset_message_status(msg_id, "pending")
            self._model.refresh()
        elif action == act_detail:
            self._show_detail(item)
        elif action == act_delete:
            msg_id = item.get("id", "")
            if msg_id:
                database.delete_message(msg_id)
                self._model.refresh()

    def _on_search(self, text):
        self._proxy.setFilterFixedString(text)

    def _on_status_filter_changed(self, text):
        mapping = {"全部": "", "待处理": "pending", "已处理": "processed", "失败": "failed"}
        self._proxy.set_status_filter(mapping.get(text, ""))

    def _on_selection_changed(self):
        self._btn_process.setEnabled(len(self._table.selectionModel().selectedRows()) > 0)

    def _on_message_added(self, msg):
        self._model.refresh()

    def _on_message_status_changed(self, msg_id):
        self._model.refresh()

    def _on_failure_management(self):
        dlg = FailureDialog(self)
        dlg.exec()

    def process_selected(self):
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return
        msg_ids = []
        for idx in indexes:
            source_idx = self._proxy.mapToSource(idx)
            msg_id = self._model.data(source_idx, MessageTableModel.MSG_ID_ROLE)
            bv_id = self._model.data(source_idx, MessageTableModel.BV_ID_ROLE)
            if bv_id and bv_id != "unknown" and msg_id:
                msg_ids.append(msg_id)
        if msg_ids:
            signal_bus.retry_messages.emit(msg_ids)

    def _show_detail(self, item):
        from gui.pages.history_page import SummaryDetailDialog
        dlg = SummaryDetailDialog({
            "bv_id": item.get("bv_id", ""),
            "sender_name": item.get("sender_name", ""),
            "created_at": item.get("received_at", ""),
            "subtitle_text": item.get("content", ""),
            "summary_text": "",
        }, self)
        dlg.exec()
