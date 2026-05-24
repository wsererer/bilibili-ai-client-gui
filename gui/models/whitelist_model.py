from PySide6.QtCore import QAbstractListModel, Qt

from database import database


class WhitelistModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self.refresh()

    def refresh(self):
        self.beginResetModel()
        self._data = database.get_whitelist()
        self.endResetModel()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        item = self._data[index.row()]
        if role == Qt.DisplayRole:
            username = item.get("username") or ""
            return f"{item['uid']} ({username})" if username else item["uid"]
        if role == Qt.UserRole:
            return item["uid"]
        return None

    def rowCount(self, parent=None):
        return len(self._data)
