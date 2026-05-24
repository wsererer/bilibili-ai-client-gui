from PySide6.QtWidgets import QApplication
from gui.signal_bus import signal_bus

LIGHT_QSS = """
QMainWindow { background-color: #FFFFFF; }

QMenuBar { background-color: #FFFFFF; border-bottom: 1px solid #E0E0E0; padding: 2px 0px; }
QMenuBar::item { background-color: transparent; padding: 4px 12px; color: #333333; }
QMenuBar::item:selected { background-color: #E8E8E8; }

QMenu { background-color: #FFFFFF; border: 1px solid #E0E0E0; padding: 4px 0px; }
QMenu::item { padding: 6px 24px; color: #333333; }
QMenu::item:selected { background-color: #E1F0FB; color: #333333; }
QMenu::separator { height: 1px; background-color: #E0E0E0; margin: 4px 8px; }

QStatusBar { background-color: #FFFFFF; border-top: 1px solid #E0E0E0; color: #888888; font-size: 12px; }

QSplitter::handle { background-color: #E0E0E0; width: 1px; }

#sidebar { background-color: #F5F5F5; border-right: 1px solid #E0E0E0; }
#appLogo { color: #333333; font-size: 14px; font-weight: bold; padding: 10px; border-bottom: 1px solid #E0E0E0; }

#navButton { color: #333333; text-align: left; padding: 0px 16px; border: none; border-radius: 0px; background-color: transparent; font-size: 13px; }
#navButton:hover { background-color: #E8E8E8; color: #333333; }
#navButton:checked { background-color: #E1F0FB; color: #0078D4; border-left: 3px solid #0078D4; }

#themeToggle { color: #333333; text-align: left; padding: 0px 16px; border: none; border-radius: 0px; background-color: transparent; font-size: 13px; }
#themeToggle:hover { background-color: #E8E8E8; color: #333333; }

#sidebarContentArea { background-color: transparent; }

QPushButton { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 6px 16px; color: #333333; font-size: 13px; }
QPushButton:hover { background-color: #E8E8E8; border-color: #CCCCCC; }
QPushButton:pressed { background-color: #D0D0D0; }
QPushButton:disabled { background-color: #F5F5F5; color: #AAAAAA; }

QLabel { color: #333333; background-color: transparent; }
#whitelistLabel { color: #333333; font-weight: bold; padding: 4px 0px; }

QLineEdit { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 4px 8px; color: #333333; font-size: 13px; }
QLineEdit:focus { border-color: #0078D4; }

QComboBox { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 4px 8px; color: #333333; font-size: 13px; }
QComboBox:hover { border-color: #0078D4; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #888888; margin-right: 6px; }
QComboBox QAbstractItemView { background-color: #FFFFFF; border: 1px solid #E0E0E0; selection-background-color: #E1F0FB; selection-color: #333333; color: #333333; }

QListView { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; color: #333333; }
QListView::item:selected { background-color: #E1F0FB; color: #333333; }

QTableView { background-color: #FFFFFF; border: 1px solid #E0E0E0; gridline-color: #E0E0E0; color: #333333; font-size: 13px; selection-background-color: #E1F0FB; selection-color: #333333; }
QTableView::item:hover { background-color: #F0F0F0; }
QTableView::item:selected { background-color: #E1F0FB; color: #333333; }

QHeaderView::section { background-color: #F5F5F5; color: #333333; padding: 6px 8px; border: none; border-bottom: 1px solid #E0E0E0; border-right: 1px solid #E0E0E0; font-weight: bold; font-size: 12px; }
QHeaderView::section:hover { background-color: #E8E8E8; }

QScrollBar:vertical { background-color: #F5F5F5; width: 12px; border: none; }
QScrollBar::handle:vertical { background-color: #CCCCCC; border-radius: 6px; min-height: 30px; margin: 2px; }
QScrollBar::handle:vertical:hover { background-color: #AAAAAA; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar:horizontal { background-color: #F5F5F5; height: 12px; border: none; }
QScrollBar::handle:horizontal { background-color: #CCCCCC; border-radius: 6px; min-width: 30px; margin: 2px; }
QScrollBar::handle:horizontal:hover { background-color: #AAAAAA; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

QCheckBox { spacing: 6px; color: #333333; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #E0E0E0; border-radius: 3px; background-color: #FFFFFF; }
QCheckBox::indicator:checked { background-color: #0078D4; border-color: #0078D4; }

QRadioButton { spacing: 6px; color: #333333; }
QRadioButton::indicator { width: 16px; height: 16px; border: 1px solid #E0E0E0; border-radius: 8px; background-color: #FFFFFF; }
QRadioButton::indicator:checked { background-color: #0078D4; border-color: #0078D4; }

QGroupBox { font-weight: bold; border: 1px solid #E0E0E0; border-radius: 6px; margin-top: 12px; padding: 16px 12px 12px 12px; color: #333333; background-color: #FFFFFF; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0px 6px; color: #333333; }

QScrollArea { border: none; background-color: #FFFFFF; }
QScrollArea > QWidget { background-color: #FFFFFF; }
QScrollArea::corner { background-color: #FFFFFF; }
QWidget#SettingsPage { background-color: #FFFFFF; }
QWidget#SettingsPage QWidget { background-color: #FFFFFF; }

QFrame { border: none; }

QFrame { border: none; }

QTextEdit, QPlainTextEdit { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; color: #333333; font-size: 13px; }
#logPanelLogView { background-color: #FFFFFF; color: #333333; }
#logPanelInfoLabel { color: #888888; font-size: 12px; }
#logPanelOpenBtn { padding: 4px 12px; }

QDialog { background-color: #FFFFFF; }

QSpinBox { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 4px; padding: 4px 8px; color: #333333; font-size: 13px; }
QSpinBox:focus { border-color: #0078D4; }

#statCard { background-color: #FFFFFF; border: 1px solid #E0E0E0; border-radius: 12px; padding: 16px; }
#statTitle { font-size: 12px; color: #888888; }
#statValue { font-size: 28px; font-weight: bold; color: #333333; }
"""

DARK_QSS = """
QMainWindow { background-color: #252526; }

QMenuBar { background-color: #1E1E1E; border-bottom: 1px solid #3E3E3E; padding: 2px 0px; }
QMenuBar::item { background-color: transparent; padding: 4px 12px; color: #E0E0E0; }
QMenuBar::item:selected { background-color: #3A3A3A; }

QMenu { background-color: #1E1E1E; border: 1px solid #3E3E3E; padding: 4px 0px; }
QMenu::item { padding: 6px 24px; color: #E0E0E0; }
QMenu::item:selected { background-color: #264F78; color: #E0E0E0; }
QMenu::separator { height: 1px; background-color: #3E3E3E; margin: 4px 8px; }

QStatusBar { background-color: #1E1E1E; border-top: 1px solid #3E3E3E; color: #A0A0A0; font-size: 12px; }

QSplitter::handle { background-color: #3E3E3E; width: 1px; }

#sidebar { background-color: #1E1E1E; border-right: 1px solid #3E3E3E; }
#appLogo { color: #E0E0E0; font-size: 14px; font-weight: bold; padding: 10px; border-bottom: 1px solid #3E3E3E; }

#navButton { color: #A0A0A0; text-align: left; padding: 0px 16px; border: none; border-radius: 0px; background-color: transparent; font-size: 13px; }
#navButton:hover { background-color: rgba(255, 255, 255, 0.08); color: #E0E0E0; }
#navButton:checked { background-color: rgba(0, 120, 212, 0.35); color: #FFFFFF; border-left: 3px solid #0078D4; }

#themeToggle { color: #A0A0A0; text-align: left; padding: 0px 16px; border: none; border-radius: 0px; background-color: transparent; font-size: 13px; }
#themeToggle:hover { background-color: rgba(255, 255, 255, 0.08); color: #E0E0E0; }

#sidebarContentArea { background-color: transparent; }

QPushButton { background-color: #3E3E3E; border: 1px solid #555555; border-radius: 4px; padding: 6px 16px; color: #E0E0E0; font-size: 13px; }
QPushButton:hover { background-color: #4A4A4A; border-color: #0078D4; }
QPushButton:pressed { background-color: #555555; }
QPushButton:disabled { background-color: #2D2D2D; color: #666666; }

QLabel { color: #E0E0E0; background-color: transparent; }
#whitelistLabel { color: #E0E0E0; font-weight: bold; padding: 4px 0px; }

QLineEdit { background-color: #2D2D2D; border: 1px solid #3E3E3E; border-radius: 4px; padding: 4px 8px; color: #E0E0E0; font-size: 13px; }
QLineEdit:focus { border-color: #0078D4; }

QComboBox { background-color: #2D2D2D; border: 1px solid #3E3E3E; border-radius: 4px; padding: 4px 8px; color: #E0E0E0; font-size: 13px; }
QComboBox:hover { border-color: #0078D4; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #A0A0A0; margin-right: 6px; }
QComboBox QAbstractItemView { background-color: #2D2D2D; border: 1px solid #3E3E3E; selection-background-color: #264F78; selection-color: #E0E0E0; color: #E0E0E0; }

QListView { background-color: #2D2D2D; border: 1px solid #3E3E3E; border-radius: 4px; color: #E0E0E0; }
QListView::item:selected { background-color: #264F78; color: #E0E0E0; }

QTableView { background-color: #2D2D2D; border: 1px solid #3E3E3E; gridline-color: #3E3E3E; color: #E0E0E0; font-size: 13px; selection-background-color: #264F78; selection-color: #E0E0E0; }
QTableView::item:hover { background-color: #3A3A3A; }
QTableView::item:selected { background-color: #264F78; color: #E0E0E0; }

QHeaderView::section { background-color: #1E1E1E; color: #E0E0E0; padding: 6px 8px; border: none; border-bottom: 1px solid #3E3E3E; border-right: 1px solid #3E3E3E; font-weight: bold; font-size: 12px; }
QHeaderView::section:hover { background-color: #3A3A3A; }

QScrollBar:vertical { background-color: #252526; width: 12px; border: none; }
QScrollBar::handle:vertical { background-color: #555555; border-radius: 6px; min-height: 30px; margin: 2px; }
QScrollBar::handle:vertical:hover { background-color: #666666; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar:horizontal { background-color: #252526; height: 12px; border: none; }
QScrollBar::handle:horizontal { background-color: #555555; border-radius: 6px; min-width: 30px; margin: 2px; }
QScrollBar::handle:horizontal:hover { background-color: #666666; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }

QCheckBox { spacing: 6px; color: #E0E0E0; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #555555; border-radius: 3px; background-color: #2D2D2D; }
QCheckBox::indicator:checked { background-color: #0078D4; border-color: #0078D4; }

QRadioButton { spacing: 6px; color: #E0E0E0; }
QRadioButton::indicator { width: 16px; height: 16px; border: 1px solid #555555; border-radius: 8px; background-color: #2D2D2D; }
QRadioButton::indicator:checked { background-color: #0078D4; border-color: #0078D4; }

QGroupBox { font-weight: bold; border: 1px solid #3E3E3E; border-radius: 6px; margin-top: 12px; padding: 16px 12px 12px 12px; color: #E0E0E0; background-color: #1E1E1E; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0px 6px; color: #E0E0E0; }

QScrollArea { border: none; background-color: transparent; }
QScrollArea > QWidget { background-color: transparent; }
QScrollArea::corner { background-color: transparent; }
QWidget#SettingsPage { background-color: transparent; }
QWidget#SettingsPage QWidget { background-color: transparent; }

QFrame { border: none; }

QTextEdit, QPlainTextEdit { background-color: #2D2D2D; border: 1px solid #3E3E3E; border-radius: 4px; color: #E0E0E0; font-size: 13px; }
#logPanelLogView { background-color: #1E1E1E; color: #D4D4D4; }
#logPanelInfoLabel { color: #A0A0A0; font-size: 12px; }
#logPanelOpenBtn { padding: 4px 12px; }

QDialog { background-color: #252526; }

QSpinBox { background-color: #2D2D2D; border: 1px solid #3E3E3E; border-radius: 4px; padding: 4px 8px; color: #E0E0E0; font-size: 13px; }
QSpinBox:focus { border-color: #0078D4; }

#statCard { background-color: #1E1E1E; border: 1px solid #3E3E3E; border-radius: 12px; padding: 16px; }
#statTitle { font-size: 12px; color: #A0A0A0; }
#statValue { font-size: 28px; font-weight: bold; color: #E0E0E0; }
"""


class ThemeManager:
    _current = "light"

    @classmethod
    def load_theme(cls, app=None, theme=None):
        if app is None:
            app = QApplication.instance()
        if theme is None:
            theme = cls._current
        cls._current = theme
        qss = LIGHT_QSS if theme == "light" else DARK_QSS
        if app is not None:
            app.setStyleSheet(qss)
        signal_bus.theme_changed.emit(theme)

    @classmethod
    def toggle(cls, app=None):
        new = "dark" if cls._current == "light" else "light"
        cls.load_theme(app, new)

    @classmethod
    def reset(cls):
        cls._current = "light"
