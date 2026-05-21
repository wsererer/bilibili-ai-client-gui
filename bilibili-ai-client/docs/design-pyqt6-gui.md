# PyQt6 GUI 替换设计文档

## 1. 概述

### 1.1 目标

将现有的 tkinter GUI 替换为 PyQt6，以获得更现代化的界面和更好的用户体验。

### 1.2 背景

当前 GUI 使用 tkinter 实现，存在以下问题：

| 问题 | 说明 |
|------|------|
| 界面陈旧 | tkinter 默认样式较老，不够美观 |
| 功能有限 | 缺少现代 UI 组件（如表格、树视图） |
| 样式定制困难 | 难以实现现代化的界面设计 |
| README 不一致 | README 声称使用 PyQt6，实际是 tkinter |

### 1.3 收益

| 收益 | 说明 |
|------|------|
| 现代化界面 | 支持 CSS 样式、动画效果 |
| 丰富组件 | 表格、树视图、选项卡等 |
| 跨平台一致性 | Windows/Linux/macOS 外观一致 |
| 更好的性能 | 原生渲染，响应更快 |

---

## 2. 技术方案

### 2.1 技术栈

| 组件 | 当前 | 替换为 |
|------|------|--------|
| GUI 框架 | tkinter | PyQt6 |
| 布局管理 | pack/grid | QVBoxLayout/QHBoxLayout |
| 事件循环 | mainloop() | QApplication.exec() |
| 定时器 | after() | QTimer |
| 线程通信 | after() 回调 | QThread + Signal |

### 2.2 依赖

```txt
# requirements.txt
PyQt6>=6.6.0  # 已存在，但未使用
```

### 2.3 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     PyQt6 GUI 架构                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  MainWindow     │    │  ConfigPanel    │    │  MessagePanel   │
│  (QMainWindow)  │◄───│  (QWidget)      │    │  (QWidget)      │
└────────┬────────┘    └─────────────────┘    └─────────────────┘
         │
         ├─── WhitelistPanel (QWidget)
         │    └─── QTableWidget
         │
         ├─── SummaryPanel (QWidget)
         │    └─── QTableWidget
         │
         ├─── StatsPanel (QWidget)
         │    └─── QLabel
         │
         └─── SettingsPanel (QWidget)
              └─── QFormLayout
```

---

## 3. 代码设计

### 3.1 目录结构

```
gui/
├── __init__.py
├── main_window.py      # 主窗口（重写）
├── widgets/
│   ├── __init__.py
│   ├── whitelist_panel.py   # 白名单管理面板
│   ├── message_panel.py     # 消息列表面板
│   ├── summary_panel.py     # 摘要历史面板
│   ├── stats_panel.py       # 统计面板
│   └── settings_panel.py    # 设置面板
└── styles/
    └── main.qss        # QSS 样式表
```

### 3.2 主窗口

**`gui/main_window.py`**

```python
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QStatusBar, QMenuBar, QMenu
)
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QAction

from config import config
from database import database
from utils.logger import logger
from openclaw_trigger import openclaw_trigger
from utils.subtitle_extractor import subtitle_extractor

from .widgets.whitelist_panel import WhitelistPanel
from .widgets.message_panel import MessagePanel
from .widgets.summary_panel import SummaryPanel
from .widgets.stats_panel import StatsPanel
from .widgets.settings_panel import SettingsPanel


class MessageWorker(QThread):
    """消息处理工作线程"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, msg):
        super().__init__()
        self.msg = msg
    
    def run(self):
        try:
            # 处理消息逻辑
            self.finished.emit({"status": "success"})
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bilibili AI Client")
        self.setMinimumSize(900, 600)
        
        self._setup_ui()
        self._setup_menu()
        self._setup_status_bar()
        self._setup_timer()
        self._load_data()
    
    def _setup_ui(self):
        """设置主界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板 - 白名单
        self.whitelist_panel = WhitelistPanel()
        main_layout.addWidget(self.whitelist_panel, stretch=1)
        
        # 右侧面板 - 选项卡
        self.tab_widget = QTabWidget()
        
        self.message_panel = MessagePanel()
        self.summary_panel = SummaryPanel()
        self.stats_panel = StatsPanel()
        self.settings_panel = SettingsPanel()
        
        self.tab_widget.addTab(self.message_panel, "消息记录")
        self.tab_widget.addTab(self.summary_panel, "摘要历史")
        self.tab_widget.addTab(self.stats_panel, "统计")
        self.tab_widget.addTab(self.settings_panel, "设置")
        
        main_layout.addWidget(self.tab_widget, stretch=3)
    
    def _setup_menu(self):
        """设置菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self._refresh)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_status_bar(self):
        """设置状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
    
    def _setup_timer(self):
        """设置定时刷新"""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._auto_refresh)
        self.refresh_timer.start(5000)  # 5秒刷新一次
    
    def _load_data(self):
        """加载初始数据"""
        self.whitelist_panel.refresh()
        self.message_panel.refresh()
        self.summary_panel.refresh()
        self.stats_panel.refresh()
    
    def _auto_refresh(self):
        """自动刷新"""
        self.message_panel.refresh()
        self.summary_panel.refresh()
    
    def _refresh(self):
        """手动刷新"""
        self._load_data()
        self.status_bar.showMessage("已刷新")
    
    def _show_about(self):
        """显示关于对话框"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self,
            "关于",
            "Bilibili AI Client v1.0\n\n自动处理B站视频字幕并生成摘要"
        )
    
    def set_status(self, text: str):
        """设置状态栏文本"""
        self.status_bar.showMessage(text)
    
    def run(self):
        """运行应用"""
        # 注意：PyQt6 需要在 main.py 中使用 QApplication
        pass
```

### 3.3 白名单面板

**`gui/widgets/whitelist_panel.py`**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt

from database import database
from utils.logger import logger


class WhitelistPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("白名单管理")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # 输入框
        input_layout = QHBoxLayout()
        
        self.uid_input = QLineEdit()
        self.uid_input.setPlaceholderText("UID")
        input_layout.addWidget(QLabel("UID:"))
        input_layout.addWidget(self.uid_input)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("用户名")
        input_layout.addWidget(QLabel("用户名:"))
        input_layout.addWidget(self.username_input)
        
        layout.addLayout(input_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._add_whitelist)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("删除")
        remove_btn.clicked.connect(self._remove_whitelist)
        btn_layout.addWidget(remove_btn)
        
        layout.addLayout(btn_layout)
        
        # 白名单列表
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["UID", "用户名", "添加时间"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
    
    def refresh(self):
        """刷新白名单列表"""
        whitelist = database.get_whitelist()
        self.table.setRowCount(len(whitelist))
        
        for i, item in enumerate(whitelist):
            self.table.setItem(i, 0, QTableWidgetItem(str(item.get("uid", ""))))
            self.table.setItem(i, 1, QTableWidgetItem(item.get("username", "")))
            self.table.setItem(i, 2, QTableWidgetItem(str(item.get("added_at", ""))))
    
    def _add_whitelist(self):
        """添加白名单"""
        uid = self.uid_input.text().strip()
        username = self.username_input.text().strip()
        
        if not uid:
            QMessageBox.warning(self, "警告", "请输入UID")
            return
        
        if database.add_whitelist(uid, username or None):
            self.refresh()
            self.uid_input.clear()
            self.username_input.clear()
            self.window().set_status(f"已添加白名单: {uid}")
        else:
            QMessageBox.error(self, "错误", "添加失败")
    
    def _remove_whitelist(self):
        """删除白名单"""
        selected = self.table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        uid = self.table.item(row, 0).text()
        
        if database.remove_whitelist(uid):
            self.refresh()
            self.window().set_status(f"已删除白名单: {uid}")
        else:
            QMessageBox.error(self, "错误", "删除失败")
```

### 3.4 消息面板

**`gui/widgets/message_panel.py`**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt

from database import database


class MessagePanel(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 消息列表
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["状态", "BV号", "发送者", "内容", "时间"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.doubleClicked.connect(self._process_message)
        layout.addWidget(self.table)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(refresh_btn)
        
        process_btn = QPushButton("处理选中")
        process_btn.clicked.connect(self._process_message)
        btn_layout.addWidget(process_btn)
        
        layout.addLayout(btn_layout)
    
    def refresh(self):
        """刷新消息列表"""
        messages = database.get_messages(50)
        self.table.setRowCount(len(messages))
        
        for i, msg in enumerate(messages):
            status = msg.get("status", "")
            status_icon = "✓" if status == "processed" else "○"
            
            self.table.setItem(i, 0, QTableWidgetItem(status_icon))
            self.table.setItem(i, 1, QTableWidgetItem(msg.get("bv_id", "")))
            self.table.setItem(i, 2, QTableWidgetItem(msg.get("sender_name", msg.get("sender_uid", ""))))
            self.table.setItem(i, 3, QTableWidgetItem(msg.get("content", "")[:50]))
            self.table.setItem(i, 4, QTableWidgetItem(str(msg.get("received_at", ""))))
    
    def _process_message(self):
        """处理选中消息"""
        selected = self.table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        bv_id = self.table.item(row, 1).text()
        
        # 触发处理逻辑
        self.window().set_status(f"处理中: {bv_id}")
        
        # 在工作线程中处理
        import threading
        from openclaw_trigger import openclaw_trigger
        from utils.subtitle_extractor import subtitle_extractor
        from config import config
        
        def do_process():
            try:
                subtitle_text = subtitle_extractor.extract_text(f"https://www.bilibili.com/video/{bv_id}")
                if subtitle_text:
                    openclaw_trigger.set_openclaw_path(config.get("openclaw_path", "openclaw"))
                    success = openclaw_trigger.trigger(
                        bv_id=bv_id,
                        subtitle_text=subtitle_text,
                        sender_uid="",
                        sender_name=""
                    )
                    if success:
                        self.window().set_status(f"已触发: {bv_id}")
                    else:
                        self.window().set_status(f"触发失败: {bv_id}")
                else:
                    self.window().set_status(f"无字幕: {bv_id}")
            except Exception as e:
                self.window().set_status(f"错误: {e}")
        
        threading.Thread(target=do_process, daemon=True).start()
```

### 3.5 QSS 样式表

**`gui/styles/main.qss`**

```css
/* 主窗口 */
QMainWindow {
    background-color: #f5f5f5;
}

/* 选项卡 */
QTabWidget::pane {
    border: 1px solid #ddd;
    background-color: white;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #e0e0e0;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: white;
    border-bottom: 2px solid #00a1d6;
}

/* 按钮 */
QPushButton {
    background-color: #00a1d6;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 14px;
}

QPushButton:hover {
    background-color: #008ba9;
}

QPushButton:pressed {
    background-color: #007391;
}

/* 表格 */
QTableWidget {
    border: 1px solid #ddd;
    gridline-color: #eee;
    selection-background-color: #e3f2fd;
}

QTableWidget::item {
    padding: 8px;
}

QHeaderView::section {
    background-color: #f0f0f0;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #ddd;
    font-weight: bold;
}

/* 输入框 */
QLineEdit {
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
}

QLineEdit:focus {
    border-color: #00a1d6;
}

/* 标签 */
QLabel {
    color: #333;
    font-size: 14px;
}

/* 状态栏 */
QStatusBar {
    background-color: #f0f0f0;
    border-top: 1px solid #ddd;
}
```

---

## 4. 迁移步骤

### 4.1 阶段一：准备工作

1. **安装 PyQt6**
   ```bash
   pip install PyQt6>=6.6.0
   ```

2. **创建目录结构**
   ```
   gui/
   ├── widgets/
   │   └── __init__.py
   └── styles/
       └── main.qss
   ```

3. **备份现有代码**
   ```bash
   cp gui/main_window.py gui/main_window_tkinter.py.bak
   ```

### 4.2 阶段二：重写 GUI

1. **创建基础组件**
   - `WhitelistPanel`
   - `MessagePanel`
   - `SummaryPanel`
   - `StatsPanel`
   - `SettingsPanel`

2. **重写主窗口**
   - 使用 QMainWindow
   - 集成所有面板
   - 实现菜单和状态栏

3. **添加 QSS 样式**
   - 创建样式表
   - 应用到应用

### 4.3 阶段三：修改入口

**修改 `main.py`**

```python
# 旧代码
from gui.main_window import MainWindow
app = MainWindow()
app.run()

# 新代码
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())
```

### 4.4 阶段四：测试

1. **功能测试**
   - 白名单添加/删除
   - 消息列表刷新
   - 摘要历史查看
   - 设置保存/加载

2. **兼容性测试**
   - Windows 10/11
   - Linux (Ubuntu/Fedora)
   - macOS

3. **性能测试**
   - 大量消息时的响应速度
   - 内存占用

---

## 5. 风险与应对

### 5.1 风险

| 风险 | 影响 | 应对方案 |
|------|------|----------|
| 线程模型差异 | tkinter 用 `after`，PyQt6 用 `QThread` | 重写所有异步逻辑 |
| 样式兼容性 | QSS 在不同平台可能有差异 | 充分测试，使用基础样式 |
| 依赖问题 | PyQt6 安装可能失败 | 提供 tkinter 降级方案 |
| 学习成本 | 需要熟悉 PyQt6 API | 先实现基础功能，逐步优化 |

### 5.2 降级方案

如果 PyQt6 安装失败，保留 tkinter 作为备选：

```python
# gui/__init__.py
try:
    from .main_window import MainWindow  # PyQt6
except ImportError:
    from .main_window_tkinter import MainWindow  # tkinter 备选
```

---

## 6. 测试用例

### 6.1 单元测试

```python
def test_whitelist_panel_add():
    app = QApplication([])
    panel = WhitelistPanel()
    panel.uid_input.setText("123456")
    panel.username_input.setText("test_user")
    panel._add_whitelist()
    
    whitelist = database.get_whitelist()
    assert any(item["uid"] == "123456" for item in whitelist)
```

### 6.2 集成测试

```python
def test_main_window_startup():
    app = QApplication([])
    window = MainWindow()
    window.show()
    
    assert window.windowTitle() == "Bilibili AI Client"
    assert window.minimumSize().width() == 900
    assert window.minimumSize().height() == 600
```

---

## 7. 工作量估算

| 任务 | 时间 |
|------|------|
| 安装依赖和准备 | 30 分钟 |
| 创建基础组件 | 2 小时 |
| 重写主窗口 | 2 小时 |
| 添加样式和美化 | 1 小时 |
| 测试和调试 | 2 小时 |
| 文档更新 | 30 分钟 |
| **总计** | **8 小时** |

---

## 8. 决策点

在开始实现前，需要确认：

| 问题 | 选项 | 建议 |
|------|------|------|
| 是否真的需要 PyQt6？ | 是/否 | 如果 tkinter 功能正常，可延后 |
| 是否保留 tkinter 备选？ | 是/否 | 建议保留，作为降级方案 |
| 是否一次性重写？ | 是/否 | 建议分阶段，先核心功能 |
| 是否需要美化？ | 是/否 | 先实现功能，再优化样式 |

---

## 9. 替代方案

如果不想完全重写，可以考虑：

### 9.1 使用 ttkbootstrap（tkinter 美化）

```bash
pip install ttkbootstrap
```

```python
# 只需修改导入
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# 自动获得现代化样式
root = ttk.Window(themename="cosmo")
```

**优点**：
- 无需重写代码
- 获得现代化样式
- 学习成本低

**缺点**：
- 功能不如 PyQt6 丰富
- 样式定制有限

### 9.2 使用 customtkinter

```bash
pip install customtkinter
```

```python
import customtkinter as ctk

# 自动获得现代化样式
app = ctk.CTk()
```

**优点**：
- 现代化外观
- 无需大幅修改代码
- 支持深色模式

**缺点**：
- 功能不如 PyQt6 丰富
- 社区较小

---

## 10. 建议

### 短期（当前版本）

1. **使用 ttkbootstrap 或 customtkinter**
   - 快速获得现代化外观
   - 无需重写代码
   - 工作量：1-2 小时

### 中期（下一版本）

2. **考虑 PyQt6 重写**
   - 如果需要更丰富的功能
   - 如果 ttkbootstrap 无法满足需求
   - 工作量：8 小时

### 长期（未来版本）

3. **Web UI**
   - 使用 Electron 或 Tauri
   - 更现代化的界面
   - 更好的跨平台支持
