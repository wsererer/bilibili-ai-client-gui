from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from database import database


class SummaryTableModel(QAbstractTableModel):
    COLUMNS = ["BV号", "发送者", "摘要预览", "时间"]

    BV_ID_ROLE = Qt.UserRole + 1
    SUMMARY_ID_ROLE = Qt.UserRole + 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []

    def refresh(self):
        self.beginResetModel()
        self._data = database.get_summaries(200)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if row >= len(self._data):
            return None
        item = self._data[row]

        if role == Qt.DisplayRole:
            if col == 0:
                return item.get("bv_id", "")
            elif col == 1:
                return item.get("sender_name", "")
            elif col == 2:
                text = item.get("summary_text", "") or item.get("subtitle_text", "")
                return text[:50] + "..." if len(text) > 50 else text
            elif col == 3:
                return item.get("created_at", "")
        elif role == self.BV_ID_ROLE:
            return item.get("bv_id", "")
        elif role == self.SUMMARY_ID_ROLE:
            return item.get("id", "")

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]
        return None
