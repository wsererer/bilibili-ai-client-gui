# 详细设计：Bilibili AI Client GUI 现代化改造

## 1. 架构总览

### 1.1 核心原则：不影响现有功能

GUI 改造必须保证**零影响**现有功能，遵守以下规则：

| 原则 | 具体要求 |
|------|---------|
| **后端零改动** | `config.py`、`database.py`、`message_poller.py`、`openclaw_trigger.py`、`mcp_server.py`、`bilibili_login.py`、`utils/` 下的文件**一行不改** |
| **CLI 模式不变** | `--mode mcp`、`--mode webhook` 的行为和输出必须与改造前完全一致 |
| **测试不失效** | 现有 170+ 非网络测试**无需修改**即全部通过。新增 GUI 测试通过 `pytest-qt` mock，不依赖实际显示 |
| **数据库兼容** | 数据库 schema 和文件路径不变，新旧 GUI 可切换回退 |
| **增量替换** | 新 `gui/` 模块与旧 `gui/main_window.py` 并存。验证全部功能后，再删除旧文件 |
| **可回退** | 改造期间保留旧 tkinter 版本入口，若新 GUI 出问题可快速切回 |

**验证手段**：
- CI 中运行全部现有测试：`python -m pytest tests/ -m "not network" -v`
- 分别测试 `--mode gui` / `--mode mcp` / `--mode webhook` / `--mode all` 四种模式
- 对比新旧 GUI 相同操作后的数据库状态

```
┌──────────────────────────────────────────────────────────────────┐
│                         main.py (入口)                           │
│  asyncio.run(qasync.run(main()))                                 │
└──────────────┬───────────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────────────────┐
│  gui/app.py                                                      │
│  QApplication 初始化 + 主题加载 + qasync 启动                     │
└──────────────┬───────────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────────────────┐
│  gui/main_window.py                                              │
│  MainWindow (QMainWindow)                                        │
│  ├── menuBar: QMenuBar                                           │
│  ├── central: QSplitter(H)                                       │
│  │   ├── sidebar: SidebarWidget (navigation)                     │
│  │   └── content: QStackedWidget (pages)                         │
│  ├── logPanel: LogPanel (底部折叠面板)                            │
│  ├── statusBar: QStatusBar                                       │
│  └── trayIcon: QSystemTrayIcon                                   │
└──────────────────────────────────────────────────────────────────┘

其他后端模块（完全独立，不依赖 GUI）：
  config.py / database.py / message_poller.py
  openclaw_trigger.py / mcp_server.py / bilibili_login.py
  utils/subtitle_extractor.py / utils/logger.py
```

### 1.2 模块依赖关系

```
gui/  ───→  signal_bus (SignalBus)  ─emit→  各种 Signal
  │                                            │
  │  ┌─────────────────────────────────────────┘
  │  ▼
  ├──→  config.py        (读/写配置)
  ├──→  database.py      (查消息、摘要、白名单、统计)
  ├──→  message_poller   (启停轮询)
  ├──→  openclaw_trigger (手动触发)
  └──→  bilibili_login   (扫码登录)

gui/  ←──  main.py  ──→  gui/app.py (qasync 启动)
```

**核心原则**：后端模块不 import gui/ 下的任何内容，保持完全解耦。

---

## 2. 启动速度优化

GUI 改造后软件启动速度**不降反升**（相比 tkinter），通过以下策略保证：

### 2.1 懒加载页面

```
启动时只创建首页（消息记录页）的实例
其余页面在用户首次点击导航时创建
```

```python
class MainWindow(QMainWindow):
    _PAGE_CLASSES = [
        MessagesPage, HistoryPage,
        StatsPage, LogsPage, SettingsPage,
    ]

    def __init__(self):
        # 只创建首页
        self._pages = [None] * len(self._PAGE_CLASSES)
        self._pages[0] = MessagesPage(self)    # 首页立即创建
        self.content_stack.addWidget(self._pages[0])

    def switch_page(self, index: int):
        if self._pages[index] is None:
            # 首次访问才创建
            self._pages[index] = self._PAGE_CLASSES[index](self)
            self.content_stack.addWidget(self._pages[index])
        self.content_stack.setCurrentIndex(index)
```

### 2.2 延迟导入重模块

`faster-whisper`、`yt-dlp`、`bilibili-api` 等重型模块在 GUI 启动时**不 import**，仅在首次使用时按需加载：

```python
# 禁止在 gui/ 模块顶层 import 重型库
# ✅ 正确：在方法内部按需导入
def _do_process(self, bv_id):
    from utils.subtitle_extractor import subtitle_extractor  # 延迟导入
    ...
```

### 2.3 异步初始化非关键组件

```
启动时间线（目标 < 2 秒）：
  t=0    main.py 开始
  t=0.1  QApplication 创建完毕
  t=0.3  MainWindow 骨架显示（侧边栏 + 空内容区 + 状态栏）
  t=0.5  消息数据异步加载完成 → MessagesPage 填充
  t=1.0  MCP server 启动完成（后台任务，不阻塞 UI）
  t=1.5  轮询启动完成（后台任务，不阻塞 UI）
  t=2.0  所有后台服务就绪
```

关键点：
- `MainWindow.show()` 在数据加载前调用，用户**立即看到窗口骨架**
- 数据加载通过 `QTimer.singleShot(0, self._load_initial_data)` 延后到事件循环启动后
- MCP server 和 poller 通过 `asyncio.create_task()` 启动，不阻塞 GUI

### 2.4 QSS 优化

- QSS 文件按组件拆分（但合并为一个文件分发），减少样式计算
- 避免在 QSS 中使用通用选择器（`* { ... }`），改用具体类名
- 主题切换时仅更新 `app.setStyleSheet()`，不清空重建

### 2.5 数据库查询优化

- 首次数据加载使用 LIMIT 200，避免全表扫描
- 统计数据使用 SQLite 聚合查询（`COUNT`、`SUM`），不在 Python 层计算
- 分页加载：消息历史超过 200 条时提供"加载更多"按钮

### 2.6 启动速度验收标准

| 指标 | 目标 | 对比 tkinter 现状 |
|------|------|------------------|
| 窗口可见时间 | < 0.5 秒 | ≈ tkinter 水平 |
| 数据加载完成 | < 2 秒 | 优于 tkinter（tkinter 同步加载） |
| 全部服务就绪 | < 3 秒 | 不差于当前 |
| PyInstaller 打包后首次启动 | < 5 秒 | — |

---

## 3. 目录结构

```
gui/
├── __init__.py
├── app.py                  # QApplication 工厂、主题加载、qasync 入口
├── main_window.py          # MainWindow (QMainWindow 主窗口)
├── signal_bus.py           # SignalBus 单例（全局信号总线）
├── theme.py                # QSS 暗/亮主题字符串 + 主题管理器
│
├── pages/                  # 每个页面一个独立模块
│   ├── __init__.py
│   ├── messages_page.py    # 消息记录页
│   ├── history_page.py     # 摘要历史页
│   ├── stats_page.py       # 统计面板页
│   ├── logs_page.py        # 系统日志页
│   └── settings_page.py    # 设置页
│
├── widgets/                # 可复用控件
│   ├── __init__.py
│   ├── sidebar.py          # 侧边导航栏
│   ├── stat_card.py        # 统计卡片控件
│   ├── log_panel.py        # 底部折叠日志面板
│   └── summary_dialog.py   # 摘要详情弹窗
│
└── models/                 # Qt Model/View 数据模型
    ├── __init__.py
    ├── message_model.py    # QAbstractTableModel — 消息列表
    ├── summary_model.py    # QAbstractTableModel — 摘要历史
    └── whitelist_model.py  # QAbstractListModel — 白名单
```

---

## 4. 组件树

```
MainWindow (QMainWindow)
│
├── menuBar (QMenuBar)
│   ├── QMenu("文件")
│   │   ├── QAction("刷新")          → signal_bus.refresh_requested
│   │   ├── QSeparator
│   │   └── QAction("退出")          → close()
│   ├── QMenu("视图")
│   │   ├── QAction("显示日志面板")   → toggle LogPanel
│   │   ├── QAction("清空日志")       → clear system log buffer
│   │   └── QAction("切换深色主题")   → theme.toggle()
│   └── QMenu("帮助")
│       └── QAction("关于")          → QMessageBox.about()
│
├── centralSplitter (QSplitter, horizontal)
│   │
│   ├── sidebar (SidebarWidget, fixed width ~200px)
│   │   └── QVBoxLayout
│   │       ├── appLogo: QLabel (图标 + 应用名称)
│   │       ├── QVBoxLayout (导航按钮组)
│       │   │   ├── navMessages:  QPushButton("📋 消息记录")
│       │   │   ├── navHistory:   QPushButton("📄 摘要历史")
│       │   │   ├── navStats:     QPushButton("📊 统计")
│       │   │   ├── navLogs:      QPushButton("📝 系统日志")
│       │   │   └── navSettings:  QPushButton("⚙ 设置")
│   │       └── spacer: QSpacerItem (stretch)
│   │
│   └── contentStack (QStackedWidget)
│       ├── [0] MessagesPage  (QWidget)
│       │   ├── toolbar (QWidget, horizontal layout)
│       │   │   ├── btnProcess:    QPushButton("处理选中")
│       │   │   ├── btnFailure:    QPushButton("失败管理")
│       │   │   ├── spacer (stretch)
│       │   │   ├── statusFilter:  QComboBox (全部/待处理/已处理/失败)
│       │   │   └── searchInput:   QLineEdit (placeholder="搜索 BV 号或发送者...")
│       │   ├── tableView: QTableView
│       │   │   model: MessageTableModel
│       │   │   proxy: QSortFilterProxyModel (搜索/过滤)
│       │   │   selection: QItemSelectionModel (可多选)
│       │   └── (columns: 状态|BV号|发送者|内容预览|时间|操作按钮)
│       │
│       ├── [1] HistoryPage  (QWidget)
│       │   ├── toolbar
│       │   │   ├── btnViewDetail: QPushButton("查看详情")
│       │   │   ├── spacer
│       │   │   └── searchInput:  QLineEdit
│       │   └── tableView: QTableView
│       │       model: SummaryTableModel
│       │       proxy: QSortFilterProxyModel
│       │
│       ├── [2] StatsPage  (QWidget)
│       │   └── statsRow: QHBoxLayout
│       │       ├── StatCard("今日处理", value, icon)
│       │       ├── StatCard("总处理量", value, icon)
│       │       └── StatCard("成功率", value, icon)
│       │
│       ├── [3] LogsPage  (QWidget)
│       │   ├── toolbar: QHBoxLayout
│       │   │   ├── levelFilter: QComboBox (全部/DEBUG/INFO/WARNING/ERROR)
│       │   │   ├── searchInput: QLineEdit (placeholder="搜索日志...")
│       │   │   └── btnClear: QPushButton("清屏")
│       │   ├── logView: QPlainTextEdit (readonly, maxBlock=10000)
│       │   └── autoScroll: QCheckBox("自动滚动")
│       │
│       └── [5] SettingsPage  (QScrollArea)
│           └── QFormLayout (分组)
│               ├── "B站认证" section
│               │   ├── authStatus: QLineEdit (readonly, 显示"已登录" or "未登录")
│               │   ├── btnWebLogin: QPushButton("网页登录")
│               │   ├── btnManualCookie: QPushButton("手动输入Cookie")
│               │   └── btnClearCookie: QPushButton("清除登录")
│               ├── "轮询" section
│               │   └── pollingInterval: QSpinBox (秒)
│               ├── "OpenClaw" section
│               │   └── openclawPath: QLineEdit + QPushButton("浏览...")
│               ├── "Webhook" section
│               │   └── webhookPort: QSpinBox
│               ├── "启动" section
│               │   └── autoStart: QCheckBox("启动时自动轮询")
│               ├── separator
│               ├── "摘要推送" section
│               │   ├── autoSend: QCheckBox("启用自动推送")
│               │   ├── sendChannel: QButtonGroup (微信|飞书|两者)
│               │   ├── wechatTarget: QLineEdit
│               │   └── feishuTarget: QLineEdit
│               └── btnSave: QPushButton("保存设置")
│
├── logPanel (LogPanel, 底部折叠面板)
│   ├── toggleBtn: QPushButton("📋 日志")  (点击展开/折叠)
│   └── logView: QPlainTextEdit (readonly, maxBlock=1000)
│
├── statusBar (QStatusBar)
│   ├── statusLabel: QLabel ("就绪")
│   ├── pollIndicator: QLabel ("● 轮询中..." / "○ 已停止")
│   ├── permanentWidgets:
│   │   └── todayLabel: QLabel ("今日: 12")
│
└── trayIcon (QSystemTrayIcon)
    ├── icon: app icon
    ├── tooltip: "Bilibili AI Client"
    └── contextMenu: QMenu
        ├── QAction("显示主窗口")
        ├── QAction("暂停轮询" / "恢复轮询")
        ├── QSeparator
        └── QAction("退出")
```

---

## 5. 信号总线 (SignalBus)

`gui/signal_bus.py` — 单例 QObject，全局信号中枢：

```python
from PySide6.QtCore import QObject, Signal

class SignalBus(QObject):
    # ── 后端 → UI 的信号 ──
    message_added = Signal(dict)           # 新消息入库
    message_status_changed = Signal(str)   # msg_id → new status
    summary_added = Signal(dict)           # 新摘要
    stats_updated = Signal(dict)           # {today: N, total: N, success_rate: N}
    whitelist_changed = Signal()           # 白名单增删
    poller_status_changed = Signal(bool)   # True=Running, False=Stopped
    login_status_changed = Signal(bool)    # True=Logged in
    openclaw_status = Signal(str, bool)    # (bv_id, success)

    # ── UI → 后端的信号 ──
    process_message = Signal(str)          # bv_id 手动处理
    retry_messages = Signal(list)          # [msg_id, ...]
    refresh_requested = Signal(str)        # 页面名或 "all"
    poller_toggle = Signal(bool)           # 启停轮询

    # ── UI 内部信号 ──
    page_changed = Signal(int)             # 当前页面索引
    theme_changed = Signal(str)            # "light" | "dark"
    log_message = Signal(str)              # 日志行文本（驱动 LogsPage + LogPanel）


# 全局单例
signal_bus = SignalBus()
```

### 5.1 连接模式

所有组件通过 `signal_bus` 通信，不直接引用对方。示例：

```python
# MessagesPage 监听新消息
signal_bus.message_added.connect(self._on_message_added)

# 后台线程处理完成发信号
signal_bus.summary_added.emit({"bv_id": "...", "summary_text": "..."})

# MainWindow 监听页面切换
signal_bus.page_changed.connect(self._on_page_changed)
```

---

## 6. 数据模型 (Model/View)

### 6.1 MessageTableModel

```python
class MessageTableModel(QAbstractTableModel):
    COLUMNS = ["状态", "BV号", "发送者", "内容预览", "时间"]

    def __init__(self):
        super().__init__()
        self._data: list[dict] = []

    def refresh(self):
        self.beginResetModel()
        self._data = database.get_messages(200)
        self.endResetModel()

    # 实现 data(), rowCount(), columnCount(), headerData()
    # 自定义角色: STATUS_ROLE, BV_ID_ROLE, MSG_ID_ROLE
```

### 6.2 SummaryTableModel

```python
class SummaryTableModel(QAbstractTableModel):
    COLUMNS = ["BV号", "发送者", "摘要预览", "时间"]

    def refresh(self):
        self.beginResetModel()
        self._data = database.get_summaries(200)
        self.endResetModel()
```

### 6.3 WhitelistModel

```python
class WhitelistModel(QAbstractListModel):
    def refresh(self):
        self.beginResetModel()
        self._data = database.get_whitelist()
        self.endResetModel()

    def data(self, index, role):
        item = self._data[index.row()]
        if role == Qt.DisplayRole:
            return f"{item['uid']} ({item.get('username', '')})"
        elif role == Qt.UserRole:
            return item["uid"]
```

### 6.4 QSortFilterProxyModel

消息列表、摘要列表使用 `QSortFilterProxyModel` 实现搜索和过滤：

```python
class MessageFilterProxy(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterKeyColumn(-1)  # search all columns

    # 可叠加状态过滤
    _status_filter = ""
    def set_status_filter(self, status: str):
        self._status_filter = status
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        # 先按文本过滤
        if not super().filterAcceptsRow(source_row, source_parent):
            return False
        # 再按状态过滤
        if self._status_filter:
            idx = self.sourceModel().index(source_row, 0)
            status = self.sourceModel().data(idx, Qt.UserRole)
            if status != self._status_filter:
                return False
        return True
```

---

## 7. 主题系统

`gui/theme.py` — QSS 明/暗主题管理器：

### 7.1 设计思路

- 两套完整 QSS 字符串（light / dark）
- 统一色板变量命名规范（在 QSS 中使用精确色值）
- 支持运行时无缝切换（`app.setStyleSheet(theme_qss)`）
- 切换时同时更新托盘图标颜色

### 7.2 色板定义

| Token | Light | Dark |
|-------|-------|------|
| `bg_primary` | `#FFFFFF` | `#1E1E1E` |
| `bg_secondary` | `#F5F5F5` | `#252526` |
| `bg_sidebar` | `#2C2C2C` | `#1A1A2E` |
| `text_primary` | `#333333` | `#E0E0E0` |
| `text_secondary` | `#888888` | `#A0A0A0` |
| `accent` | `#0078D4` | `#0078D4` |
| `success` | `#4CAF50` | `#4CAF50` |
| `warning` | `#FF9800` | `#FF9800` |
| `error` | `#F44336` | `#F44336` |
| `border` | `#E0E0E0` | `#3E3E3E` |
| `card_bg` | `#FFFFFF` | `#2D2D2D` |
| `hover` | `#E8E8E8` | `#3A3A3A` |
| `selected` | `#E1F0FB` | `#264F78` |

### 7.3 QSS 加载方式

```python
class ThemeManager:
    _current = "light"

    @classmethod
    def load_theme(cls, app: QApplication, theme: str):
        cls._current = theme
        qss_path = Path(__file__).parent / f"themes/{theme}.qss"
        if qss_path.exists():
            with open(qss_path) as f:
                app.setStyleSheet(f.read())
        signal_bus.theme_changed.emit(theme)

    @classmethod
    def toggle(cls, app: QApplication):
        new = "dark" if cls._current == "light" else "light"
        cls.load_theme(app, new)
```

QSS 文件存放在 `gui/themes/` 目录下：

```
gui/
├── themes/
│   ├── light.qss
│   └── dark.qss
```

---

## 8. qasync 集成

### 8.1 入口改造 (`gui/app.py`)

```python
import qasync
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow
from gui.theme import ThemeManager

async def async_main():
    app = QApplication(sys.argv)
    app.setApplicationName("Bilibili AI Client")

    # 加载主题
    ThemeManager.load_theme(app, config.get("theme", "light"))

    # 创建主窗口
    window = MainWindow()
    window.show()

    # 启动后台协程
    mcp_task = asyncio.create_task(mcp_main())

    # 如果 auto_start 则启动轮询
    if config.get("auto_start", True):
        message_poller.set_callback(_on_message)
        message_poller.start()

    # 进入 qasync 事件循环
    await app.exec()

    # 清理
    mcp_task.cancel()
    message_poller.stop()
```

### 8.2 main.py 改造

```python
def main():
    args = parse_args()

    if args.mode in ("gui", "all"):
        from gui.app import async_main
        asyncio.run(qasync.run(async_main()))
    elif args.mode == "mcp":
        asyncio.run(mcp_main())
    elif args.mode == "webhook":
        ...
```

### 8.3 后台协程的安全更新

使用 `qasync` 后，协程中的 UI 更新可以直接写，无需特殊处理：

```python
# 在协程中安全更新 UI
async def _on_openclaw_complete(bv_id, success, summary_text):
    if success:
        database.add_summary(...)
        signal_bus.summary_added.emit({...})
        signal_bus.stats_updated.emit(database.get_stats())
```

---

## 9. 页面详细设计

### 9.1 MessagesPage

**设计原则**：数据自动同步，不设手动刷新按钮。消息列表通过 `SignalBus` 信号实时更新，无需用户手动刷新。

```
工具栏:  QHBoxLayout
  ├── QPushButton("处理选中")     → self.process_selected()
  ├── QPushButton("失败管理")     → open FailureDialog（包含查看+重试）
  ├── QSpacerItem (stretch)
  ├── QComboBox (状态筛选)        → proxy.set_status_filter()
  │     ["全部", "待处理", "已处理", "失败"]
  └── QLineEdit (搜索框)          → proxy.setFilterFixedString()

QTableView
  ├── model: MessageTableModel
  ├── proxy: MessageFilterProxy
  ├── selectionBehavior: SelectRows
  ├── selectionMode: ExtendedSelection
  ├── setSortingEnabled: True
  ├── horizontalHeader: stretchLastSection + sortIndicator
  ├── 双击行 → 触发 process_selected()
  └── 右键菜单 → QMenu (处理/重置详情)
```

**交互流程 — 处理选中消息：**
1. 用户点击"处理选中"或双击行
2. 获取选中行的 `bv_id`（从 `UserRole` 获取）
3. 调用 `subtitle_extractor.extract_text(url)`（在 QThread 中执行以免阻塞 UI）
4. 调用 `openclaw_trigger.trigger(...)` → 设置回调
5. 回调触发 → `signal_bus.message_status_changed.emit(...)`
6. 表格自动更新（通过 `signal_bus` 信号驱动，无需手动刷新）

### 9.2 HistoryPage

**设计原则**：摘要列表通过 `signal_bus.summary_added` 信号自动更新，不设手动刷新按钮。

```
工具栏:  QHBoxLayout
  ├── QPushButton("查看详情")     → open SummaryDetailDialog
  ├── QSpacerItem (stretch)
  └── QLineEdit (搜索框)

QTableView
  ├── model: SummaryTableModel
  ├── proxy: QSortFilterProxyModel
  └── 双击行 → open SummaryDetailDialog
```

**SummaryDetailDialog** (`gui/widgets/summary_dialog.py`):

```
QDialog
├── QVBoxLayout
│   ├── QLabel("BV号: {bv_id}")
│   ├── QLabel("发送者: {sender}")
│   ├── QLabel("时间: {created_at}")
│   ├── QSeparator
│   ├── QLabel("字幕内容:") + QTextEdit (readonly)
│   └── QLabel("摘要:") + QTextEdit (readonly)
└── QDialogButtonBox(Close)
```

### 9.3 StatsPage

**设计原则**：统计数据通过 `signal_bus.stats_updated` 信号自动更新，无需手动刷新。

```
QVBoxLayout (centered)
└── QHBoxLayout (stat cards row)
    ├── StatCard(icon="📨", title="今日处理", value="0", color=accent)
    ├── StatCard(icon="📊", title="总处理量", value="0", color=primary)
    └── StatCard(icon="✅", title="成功率", value="0%", color=success)
```

**StatCard** (`gui/widgets/stat_card.py`):

```
QFrame (固定宽度 200px, card-like)
├── QVBoxLayout
│   ├── QLabel(icon)     — 大号字体 emoji
│   ├── QLabel(title)    — 灰色小字
│   └── QLabel(value)    — 大号加粗数字
│   style: border-radius, shadow-ish via QSS
```

### 9.4 LogsPage

**设计原则**：实时显示系统运行日志，挂接 loguru，支持级别过滤和搜索。

```
工具栏: QHBoxLayout
  ├── levelFilter: QComboBox
  │     ["全部", "DEBUG", "INFO", "WARNING", "ERROR"]
  ├── searchInput: QLineEdit (placeholder="搜索日志关键字...")
  ├── QSpacerItem (stretch)
  ├── QCheckBox("自动滚动")
  └── QPushButton("清屏") → logView.clear()

QPlainTextEdit (readonly)
  ├── maxBlockCount: 10000 (防止内存溢出)
  ├── font: "Consolas", 10pt (等宽字体适合日志)
  ├── lineWrapMode: NoWrap (保持日志原始格式)
  ├── 右键菜单: QMenu
  │   ├── 复制选中
  │   ├── 复制全部
  │   └── 清屏
  └── 日志行格式: [HH:mm:ss] [LEVEL] module:line - message
```

**后台实现**：

```python
class LogsPage(QWidget):
    def __init__(self):
        # loguru sink 将日志发送到 LogsPage
        logger.add(self._log_sink, format="{time:HH:mm:ss} [{level}] {module}:{line} - {message}")

    def _log_sink(self, msg: str):
        # 所有线程的日志汇集到此，由 signal 桥接到主线程
        signal_bus.log_message.emit(msg)

    def _on_log_message(self, msg: str):
        level = self._parse_level(msg)
        if self._level_filter and level not in self._level_filter:
            return
        if self._search_text and self._search_text.lower() not in msg.lower():
            return
        self.log_view.appendPlainText(msg)
        if self.auto_scroll.isChecked():
            self.log_view.moveCursor(QTextCursor.End)
```

**SignalBus 新增信号**：

```python
class SignalBus(QObject):
    log_message = Signal(str)  # 日志行文本
```

### 9.5 SettingsPage

```
QScrollArea
└── QWidget → QFormLayout (两列: label | widget)

分组 1: "B站认证" (QGroupBox)
  ├── Cookie状态: QLineEdit(readonly, "已登录(加密存储)" / "未登录")
  ├── [网页登录] [手动输入Cookie] [清除登录]

分组 2: "轮询设置" (QGroupBox)
  ├── 轮询间隔: QSpinBox(range=5-300, suffix=" 秒")
  └── 启动时自动轮询: QCheckBox

分组 3: "OpenClaw" (QGroupBox)
  └── OpenClaw路径: QLineEdit + [浏览] QFileDialog

分组 4: "Webhook" (QGroupBox)
  └── Webhook端口: QSpinBox(range=1024-65535)

分组 5: "摘要推送" (QGroupBox)
  ├── 启用自动推送: QCheckBox
  ├── 推送渠道: QRadioButton(微信|飞书|两者)
  ├── 微信目标: QLineEdit
  └── 飞书目标: QLineEdit

底部:
  └── [保存设置] QPushButton(primary style)
```

**交互 — 网页登录：**
1. 点击"网页登录"按钮
2. 检查已有 Cookie → 已存在则提示"已登录"
3. 启动 `bilibili_login.run_login_server(51888)`（QThread）
4. 调用 `QDesktopServices.openUrl("http://127.0.0.1:51888")`
5. 启动定时器（`QTimer`，每秒检查 `config.get("bili_auth")`）
6. Cookie 出现 → `signal_bus.login_status_changed.emit(True)` → UI 更新
7. 发送请求关闭 Flask server

---

## 10. 侧边导航栏

`gui/widgets/sidebar.py`：

```
SidebarWidget (QFrame, fixed_width=200)
├── appLogo: QLabel (emoji + "Bilibili AI Client")
├── navButtons: QVBoxLayout
│   ├── btnMessages:  SidebarButton("📋 消息记录", 0)
│   ├── btnHistory:   SidebarButton("📄 摘要历史", 1)
│   ├── btnStats:     SidebarButton("📊 统计", 2)
│   ├── btnLogs:      SidebarButton("📝 系统日志", 3)
│   └── btnSettings:  SidebarButton("⚙ 设置", 4)
├── stretch
└── themeToggle: QPushButton("🌓 切换主题")

侧边栏按钮样式：
  - 固定高度 40px，左右 padding 16px
  - hover: 背景变浅
  - checked/选中: 左侧 3px accent 色条
  - 使用 QPushButton checkable + exclusive 行为
  - 点击时 emit clicked(index) → main_window switch page
```

---

## 11. 系统托盘

```python
class TrayManager(QObject):
    def __init__(self, main_window: QMainWindow):
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(QIcon(":/icons/app.png"))
        self.tray.setToolTip("Bilibili AI Client")

        menu = QMenu()
        menu.addAction("显示主窗口", main_window.show)
        menu.addAction("显示/隐藏", self._toggle_visible)
        self.action_pause = menu.addAction("暂停轮询")
        self.action_pause.triggered.connect(self._toggle_poller)
        menu.addSeparator()
        menu.addAction("退出", main_window.close)
        self.tray.setContextMenu(menu)

        self.tray.activated.connect(self._on_activated)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            main_window.show()
            main_window.raise_()

    def _toggle_poller(self):
        ...

    def show_notification(self, title, message):
        self.tray.showMessage(title, message, QSystemTrayIcon.Information, 5000)
```

**实现要点：**
- 关闭窗口时默认隐藏到托盘（`closeEvent` 拦截）
- 托盘中双击恢复主窗口
- 处理完成后通过托盘发送通知

---

## 12. 折叠日志面板（底部快捷视图）

`gui/widgets/log_panel.py` — 与 LogsPage 共享同一 loguru sink，是系统日志的**快捷入口**（底部折叠面板），不是独立日志系统。

```
LogPanel (QWidget, 底部 dock 区域)
├── toggleBtn: QPushButton("📝 系统日志  ▼")
│   style: 无边框, 左对齐, hover 高亮
└── collapsed content (visible when toggled):
    ├── quickView: QPlainTextEdit (readonly, maxBlock=200)
    │   ├── 只显示最近 200 条日志
    │   ├── 等宽字体, 深色背景
    │   └── 双击行 → 自动跳转到 LogsPage 并定位该行
    ├── QHBoxLayout (底部操作栏)
    │   ├── QLabel("显示最近 200 条，完整日志见系统日志页")
    │   ├── QSpacerItem (stretch)
    │   └── QPushButton("打开完整日志") → switch to LogsPage(3)
    └── maxHeight: 180px
```

**实现要点**：
- 和 `LogsPage` 共用同一个 `loguru sink`，不重复创建
- `signal_bus.log_message` 信号同时驱动 LogPanel 和 LogsPage
- LogPanel 只保留最近 200 条作为快速预览，LogsPage 保留 10000 条
- 点击"打开完整日志"自动切换侧边栏到系统日志页

---

## 13. 线程模型

| 任务 | 运行位置 | 说明 |
|------|---------|------|
| GUI 事件循环 | 主线程 (qasync) | 所有 UI 更新在此 |
| MCP server | 主线程 (asyncio task) | 通过 qasync 在事件循环中调度 |
| message_poller | 主线程 (asyncio task) | 同上，协程轮询 |
| 字幕提取 + OpenClaw | QThread（独立线程） | 同步阻塞操作，不可在主线程执行 |
| QR 登录 Flask server | QThread | Flask 同步阻塞 |
| SQLite 查询 | 主线程（同步） | SQLite 查询极快，直接在主线程执行 |

**字幕提取 + OpenClaw 触发线程封装**：

```python
class ProcessWorker(QObject):
    finished = Signal(str, bool, str, str)  # bv_id, success, summary, error
    progress = Signal(str)                  # status text

    def __init__(self, bv_id, subtitle_text):
        super().__init__()
        self.bv_id = bv_id
        self.subtitle_text = subtitle_text

    @Slot()
    def run(self):
        try:
            self.progress.emit(f"正在处理: {self.bv_id}")
            success = openclaw_trigger.trigger(...)
            self.finished.emit(self.bv_id, success, ...)
        except Exception as e:
            self.finished.emit(self.bv_id, False, "", str(e))

# 使用方式
def process_message(self, bv_id):
    self.thread = QThread()
    self.worker = ProcessWorker(bv_id, subtitle_text)
    self.worker.moveToThread(self.thread)
    self.thread.started.connect(self.worker.run)
    self.worker.finished.connect(self._on_process_finished)
    self.worker.finished.connect(self.thread.quit)
    self.worker.finished.connect(self.worker.deleteLater)
    self.thread.finished.connect(self.thread.deleteLater)
    self.thread.start()
```

---

## 14. 配置管理

利用 QSettings 替代手动 JSON 读写（可选），或继续使用现有 `config.py`：

**推荐：继续使用 config.py**（避免重构）但额外将窗口状态持久化到 QSettings：

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._settings = QSettings("BilibiliAI", "Client")

    def _save_window_state(self):
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("splitter", self.splitter.saveState())

    def _restore_window_state(self):
        if self._settings.contains("geometry"):
            self.restoreGeometry(self._settings.value("geometry"))
        if self._settings.contains("splitter"):
            self.splitter.restoreState(self._settings.value("splitter"))
```

---

## 15. 目录与文件清单

```
gui/
├── __init__.py
├── app.py                  # ~80 行 — QApplication 初始化、qasync 入口
├── main_window.py          # ~200 行 — MainWindow 主窗口 + 菜单栏 + 布局
├── signal_bus.py           # ~50 行 — SignalBus 单例
├── theme.py                # ~80 行 — ThemeManager + QSS 加载
├── themes/
│   ├── light.qss           # ~200 行 — 浅色主题 QSS
│   └── dark.qss            # ~200 行 — 深色主题 QSS
├── pages/
│   ├── __init__.py
│   ├── messages_page.py    # ~200 行 — 消息记录页（含 FilterProxy）
│   ├── history_page.py     # ~120 行 — 摘要历史页
│   ├── stats_page.py       # ~80 行 — 统计面板
│   ├── logs_page.py        # ~180 行 — 系统日志页（含过滤器 + loguru sink）
│   └── settings_page.py    # ~300 行 — 设置页（结构较长但逻辑简单）
├── widgets/
│   ├── __init__.py
│   ├── sidebar.py          # ~110 行 — 侧边导航栏（5 个按钮）
│   ├── stat_card.py        # ~50 行 — 统计卡片
│   ├── log_panel.py        # ~100 行 — 底部折叠日志面板（与 LogsPage 共用 sink）
│   └── summary_dialog.py   # ~100 行 — 摘要详情弹窗
└── models/
    ├── __init__.py
    ├── message_model.py    # ~100 行 — 消息表格模型
    ├── summary_model.py    # ~80 行 — 摘要表格模型
    └── whitelist_model.py  # ~60 行 — 白名单列表模型
```

**新增依赖**：
```
PySide6>=6.5
qasync>=0.27
```

**移除依赖**：无（tkinter 为标准库，不需显式移除）

---

## 16. main.py 适配

```python
import qasync

def main():
    args = parse_args()

    if args.mode in ("gui", "all"):
        from gui.app import run_gui  # run_gui 是 async def
        asyncio.run(qasync.run(run_gui()))
    elif args.mode == "mcp":
        asyncio.run(mcp_main())
    ...

async def run_gui():
    app = QApplication(sys.argv)
    ThemeManager.load_theme(app, config.get("theme", "light"))

    window = MainWindow()
    window.show()

    if config.get("auto_start", True):
        message_poller.set_callback(signal_bus.message_added.emit)
        message_poller.start()

    mcp_task = asyncio.create_task(mcp_main())

    try:
        await app.exec()
    finally:
        mcp_task.cancel()
        message_poller.stop()
```

---

## 17. PyInstaller 适配

更新 `bilibili_ai_client_gui.spec`：

```python
# 关键改动
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],  # QSS 主题文件可打包进 data
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'qasync',
    ],
    hookspath=[],
    hooksconfig={},
)

# PySide6 需要 --add-data 包含 Qt plugins
# 在 spec 中或命令行:
# --add-data "path_to_pyside6/Qt/plugins;PySide6/Qt/plugins"
```

---

## 18. 迁移路线

| Phase | 产出 | 预计 |
|-------|------|------|
| **P1: 框架搭建** | `app.py` + `main_window.py` + `sidebar.py` + QStackedWidget 骨架 + qasync 跑通 | 2天 |
| **P2: 消息与摘要** | `messages_page.py` + `message_model.py` + `history_page.py` + `summary_model.py` + `summary_dialog.py` | 2天 |
| **P3: 统计与设置** | `stats_page.py` + `stat_card.py` + `settings_page.py` + `whitelist_model.py` | 2天 |
| **P4: 增强** | `log_panel.py` + `theme.py` + QSS 主题 + `TrayManager` + 搜索/过滤 | 2天 |
| **P5: 收尾** | 更新 `main.py` + `spec` + 测试验证 + 修复 bug | 1-2天 |

**总计：9-10 天**

---

## 19. 未解决的问题 / 开放决策

| 问题 | 建议 |
|------|------|
| QSS 主题文件打包方式 | 建议用 `qrc` 资源文件或 `--add-data` 嵌入 exe |
| 图标资源（侧边栏、状态图标、托盘） | 使用 Unicode emoji 作为过渡，后续替换为 SVG 图标 |
| 与现存 170+ 测试的兼容性 | GUI 测试需 mock QApplication（`pytest-qt`），非 GUI 测试不变 |
| 旧 tkinter 代码处理 | 保留 `gui/main_window.py` 旧文件，标记 `@deprecated`，新代码完成后删除 |
