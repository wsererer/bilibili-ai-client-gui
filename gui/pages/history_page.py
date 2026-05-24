from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QTableView,
)
from PySide6.QtCore import Qt, QSortFilterProxyModel

from gui.signal_bus import signal_bus
from gui.models.summary_model import SummaryTableModel
from gui.widgets.summary_dialog import SummaryDetailDialog


class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HistoryPage")
        self._model = SummaryTableModel(self)
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)
        self._setup_ui()
        self._connect_signals()
        self._model.refresh()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self._btn_detail = QPushButton("查看详情")
        self._btn_detail.setEnabled(False)
        toolbar.addWidget(self._btn_detail)
        toolbar.addStretch()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索 BV 号或发送者...")
        toolbar.addWidget(self._search_input)
        layout.addLayout(toolbar)
        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setSelectionBehavior(QTableView.SelectRows)
        self._table.setSelectionMode(QTableView.SingleSelection)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().hide()
        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        layout.addWidget(self._table)

    def _connect_signals(self):
        self._search_input.textChanged.connect(self._on_search)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._btn_detail.clicked.connect(self._on_view_detail)
        self._table.doubleClicked.connect(self._on_view_detail)
        signal_bus.summary_added.connect(self._on_summary_added)

    def _on_search(self, text):
        self._proxy.setFilterFixedString(text)

    def _on_selection_changed(self):
        self._btn_detail.setEnabled(len(self._table.selectionModel().selectedRows()) > 0)

    def _on_summary_added(self, data):
        self._model.refresh()

    def _on_view_detail(self):
        index = self._table.currentIndex()
        if not index.isValid():
            return
        source_index = self._proxy.mapToSource(index)
        row = source_index.row()
        if row < 0 or row >= len(self._model._data):
            return
        dlg = SummaryDetailDialog(self._model._data[row], self)
        dlg.exec()
