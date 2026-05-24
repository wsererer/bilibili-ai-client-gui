from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from database import database


class MessageTableModel(QAbstractTableModel):
    COLUMNS = ["状态", "BV号", "发送者", "内容预览", "时间"]

    STATUS_ROLE = Qt.UserRole + 1
    BV_ID_ROLE = Qt.UserRole + 2
    MSG_ID_ROLE = Qt.UserRole + 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []

    def refresh(self):
        self.beginResetModel()
        self._data = database.get_messages(200)
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
                return self._status_icon(item.get("status", ""))
            elif col == 1:
                return item.get("bv_id", "")
            elif col == 2:
                return item.get("sender_name", "") or item.get("sender_uid", "")
            elif col == 3:
                text = item.get("content", "") or ""
                return text[:50] + "..." if len(text) > 50 else text
            elif col == 4:
                return item.get("received_at", "")
        elif role == self.STATUS_ROLE:
            return item.get("status", "")
        elif role == self.BV_ID_ROLE:
            return item.get("bv_id", "")
        elif role == self.MSG_ID_ROLE:
            return item.get("id", "")
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]
        return None

    @staticmethod
    def _status_icon(status: str) -> str:
        mapping = {
            "processed": "✅ 已处理",
            "pending": "○ 待处理",
            "failed": "❌ 失败",
            "trigger_failed": "❌ 触发失败",
            "openclaw_failed": "❌ 生成失败",
            "no_subtitle": "❌ 无字幕",
            "not_whitelisted": "⚠ 未在白名单",
            "no_sender_uid": "⚠ 无发送者UID",
            "triggered": "⏳ 生成中",
        }
        return mapping.get(status, "○ 未知")
