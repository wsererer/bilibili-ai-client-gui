from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt

from gui.signal_bus import signal_bus
from gui.widgets.stat_card import StatCard
from database import database


class StatsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatsPage")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        row = QHBoxLayout()
        row.setAlignment(Qt.AlignCenter)
        row.setSpacing(24)

        self.today_card = StatCard("📨", "今日处理")
        self.total_card = StatCard("📊", "总处理量")
        self.rate_card = StatCard("✅", "成功率")

        row.addWidget(self.today_card)
        row.addWidget(self.total_card)
        row.addWidget(self.rate_card)
        layout.addLayout(row)

        self._refresh()
        signal_bus.stats_updated.connect(self._on_stats_updated)

    def _refresh(self):
        today = database.get_today_count()
        total = database.get_total_count()
        failed = len(database.get_failed_messages())
        rate = f"{(total / (total + failed)) * 100:.0f}%" if (total + failed) > 0 else "0%"
        self.today_card.set_value(str(today))
        self.total_card.set_value(str(total))
        self.rate_card.set_value(rate)

    def _on_stats_updated(self, stats: dict):
        if "today" in stats:
            self.today_card.set_value(str(stats["today"]))
        if "total" in stats:
            self.total_card.set_value(str(stats["total"]))
        if "success_rate" in stats:
            rate = stats["success_rate"]
            if isinstance(rate, float) and 0 <= rate <= 1:
                rate = f"{rate * 100:.0f}%"
            self.rate_card.set_value(str(rate))
