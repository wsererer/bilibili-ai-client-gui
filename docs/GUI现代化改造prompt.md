# GUI 现代化改造 — Vibe Coding Prompt

## 1. 目标

将 Bilibili AI Client 的 GUI 从 **tkinter** 迁移到 **PySide6 (Qt6)**，按照 `docs/design-GUI现代化改造-详细设计.md` 实现全部页面和功能，保持后端零改动。

---

## 2. Agent 角色分工

### 2.1 主 Agent（OpenCode Zen / deep-seek-v4-flash-free）

**职责**：
- 阅读全部输入文档，理解架构和设计
- 按任务依赖关系排序，逐一分配任务给子 Agent
- 验证子 Agent 的产出（pytest 通过、ruff 通过）
- 跟踪全局进度，更新任务状态文件
- 处理异常和阻塞

**行为规则**：
- 一次只分配 **1 个任务** 给子 Agent
- 子 Agent 完成后验证测试和 lint，通过后再分配下一个
- 若子 Agent 失败，补充说明后重新分配
- 不要修改后端模块（`config.py` / `database.py` / `message_poller.py` / `openclaw_trigger.py` / `mcp_server.py` / `bilibili_login.py` / `utils/` 下的任何文件）

### 2.2 子 Agent（MiniMax2.7 / general）

**职责**：
- 读取主 Agent 分配的任务文件
- 实现代码和测试
- 运行 pytest 确保测试通过
- 运行 ruff 确保代码规范
- 将结果写回结果文件

**行为规则**：
- 只修改任务指定范围内的文件
- 不得修改后端模块
- 完成后必须运行 `ruff check . && python -m pytest tests/ -m "not network" -v` 验证

---

## 3. 通信协议：文件交换

主 Agent 和子 Agent 通过 `.task/` 目录下的文件交换信息。

### 3.1 目录结构

```
.task/
├── queue.md              # 全局任务队列和状态（由主 Agent 维护）
├── T-001.md              # 任务定义文件
├── T-001-result.md       # 任务结果文件
├── T-002.md
├── T-002-result.md
└── ...
```

### 3.2 任务队列文件 `.task/queue.md`

主 Agent 维护此文件，反映全局进度。

```markdown
# 任务队列

| ID | 名称 | 状态 | 子Agent | 结果 |
|----|------|------|---------|------|
| T-01 | 项目初始化 | ✅ done | minimax2.7 | 通过 |
| T-02 | SignalBus | ✅ done | minimax2.7 | 通过 |
| T-03 | MainWindow | 🔄 in_progress | minimax2.7 | — |
| T-04 | Sidebar | ⏳ pending | — | — |
| ... | ... | ... | ... | ... |

状态: pending → in_progress → done / failed
```

### 3.3 任务定义文件格式

```markdown
# 任务: T-03 MainWindow 主窗口骨架
## 阶段: Phase 1
## 依赖: T-02 SignalBus

## 说明
实现 MainWindow(QMainWindow)，包含菜单栏、QSplitter、QStackedWidget 骨架等。

## 需要创建的文件
- gui/main_window.py

## 实现要求
1. QMenuBar: 文件(刷新/退出) + 视图(显示日志面板/清空日志/切换深色主题) + 帮助(关于)
2. 中央区域: QSplitter(H) → 左侧 SidebarWidget 占位 + 右侧 QStackedWidget 占位
3. QStatusBar: statusLabel + pollIndicator + todayLabel
4. QSystemTrayIcon: 右键菜单(显示主窗口/暂停轮询/退出)
5. 窗口关闭时隐藏到托盘（closeEvent 拦截）
6. 懒加载: 只创建首页 MessagesPage，其余在 switch_page 时创建

## 验收标准
- [ ] 窗口显示，菜单栏三个菜单完整
- [ ] QSplitter 可拖动
- [ ] 系统托盘图标显示，右键菜单工作
- [ ] 关闭窗口隐藏到托盘
- [ ] ruff check . 无报错
- [ ] pytest 测试通过

## 测试要求
- tests/gui/test_main_window.py
- 使用 pytest-qt (qtbot fixture)
- 测试菜单 Action 触发正确信号
- 测试关闭窗口 → 隐藏到托盘（mock QSystemTrayIcon）
```

### 3.4 任务结果文件格式

```markdown
# 结果: T-03 MainWindow 主窗口骨架
## 状态: ✅ completed

## 更改的文件
- gui/main_window.py (新增, 210行)

## 测试结果
```
tests/gui/test_main_window.py::test_menu_bar PASSED
tests/gui/test_main_window.py::test_tray_icon PASSED
tests/gui/test_main_window.py::test_close_to_tray PASSED
```

## Ruff 结果
```
All checks passed!
```

## 备注
- QSystemTrayIcon 在无桌面环境(headless)下不可用，测试中使用 mock
```

---

## 4. 任务清单（共 23 个任务）

按依赖关系排列。主 Agent 按此顺序分配。

### Phase 1：框架搭建（2 天）

| ID | 任务 | 依赖 | 核心产出 |
|----|------|------|---------|
| T-01 | 项目初始化与依赖安装 | — | 安装 PySide6 + qasync + pytest-qt；更新 pyproject.toml；创建 gui/ 目录结构 |
| T-02 | SignalBus 信号总线 | — | `gui/signal_bus.py` — 15 个信号定义 + 单例 |
| T-03 | MainWindow 主窗口骨架 | T-02 | `gui/main_window.py` — 菜单栏 + QSplitter + QStackedWidget + 状态栏 + 系统托盘 + 懒加载 |
| T-04 | SidebarWidget 侧边导航栏 | — | `gui/widgets/sidebar.py` — 5 个导航按钮 + 主题切换 |
| T-05 | qasync 集成与 main.py 适配 | T-03 | `gui/app.py` + 改造 `main.py` |
| T-06 | 懒加载机制验证 | T-03, T-04 | 在 MainWindow 中集成 Sidebar + 验证懒加载 |

### Phase 2：核心页面（3 天）

| ID | 任务 | 依赖 | 核心产出 |
|----|------|------|---------|
| T-07 | WhitelistModel + 白名单面板 | T-02 | `gui/models/whitelist_model.py` + 侧边栏集成 |
| T-08 | MessageTableModel + MessagesPage | T-07, T-06 | `gui/models/message_model.py` + `gui/pages/messages_page.py` |
| T-09 | MessageFilterProxy 搜索与过滤 | T-08 | `MessageFilterProxy` (在 messages_page.py 内) |
| T-10 | SummaryTableModel + HistoryPage | T-02, T-06 | `gui/models/summary_model.py` + `gui/pages/history_page.py` |
| T-11 | SummaryDetailDialog 摘要详情弹窗 | T-10 | `gui/widgets/summary_dialog.py` |
| T-12 | StatCard + StatsPage | T-02, T-06 | `gui/widgets/stat_card.py` + `gui/pages/stats_page.py` |

### Phase 3：设置与日志（2 天）

| ID | 任务 | 依赖 | 核心产出 |
|----|------|------|---------|
| T-13 | SettingsPage 设置页 | T-02, T-06 | `gui/pages/settings_page.py` |
| T-14 | Cookie 登录流程集成 | T-13 | 网页登录/手动Cookie/清除登录 交互 |
| T-15 | LogsPage 系统日志页 | T-02 | `gui/pages/logs_page.py` — loguru sink + 级别过滤 + 搜索 |

### Phase 4：增强（2 天）

| ID | 任务 | 依赖 | 核心产出 |
|----|------|------|---------|
| T-16 | LogPanel 底部折叠日志面板 | T-15 | `gui/widgets/log_panel.py` |
| T-17 | QSS 主题系统 | T-03 | `gui/theme.py` + `gui/themes/light.qss` + `gui/themes/dark.qss` |
| T-18 | QSystemTrayIcon 系统托盘 | T-03 | 托盘完整功能（含通知） |
| T-19 | 状态栏增强 | T-03 | 轮询指示器 + 今日处理量常驻 |
| T-20 | 窗口状态持久化 | T-03 | QSettings 保存/恢复 geometry + splitter |

### Phase 5：收尾（2 天）

| ID | 任务 | 依赖 | 核心产出 |
|----|------|------|---------|
| T-21 | PyInstaller 打包适配 | 全部 | 更新 `.spec` 文件 |
| T-22 | 全面回归测试 | T-21 | 4 种模式验证 + 数据库兼容 |
| T-23 | 旧 tkinter 代码清理 | T-22 | 删除旧 `gui/main_window.py` |

---

## 5. 子 Agent 实现规范

### 5.1 代码风格

- 遵循 `pyproject.toml` 配置：ruff line-length=120, target-version py311
- **不添加任何注释**（除非函数 docstring 极少数必要场景）
- 采用 Qt 的 `camelCase` 命名（`setCurrentIndex`、`_on_message_added`）
- 每个文件不超过 500 行
- 后端模块不得修改：`config.py` / `database.py` / `message_poller.py` / `openclaw_trigger.py` / `mcp_server.py` / `bilibili_login.py` / `utils/` 下全部文件

### 5.2 测试规范

- 使用 pytest + pytest-qt
- 测试文件放在 `tests/gui/` 目录下
- 每个测试函数使用 `qtbot` fixture
- 对 QAbstractTableModel 子类：测试 refresh()、rowCount()、data()、headerData()
- 对 QWidget 子类：测试构造不抛异常、信号连接正确
- 对 SignalBus：测试 emit → connect 链路
- 运行命令：`ruff check . && python -m pytest tests/ -m "not network" -v`

### 5.3 子 Agent 工作流程

```
1. 读取主 Agent 分配的任务文件 (.task/T-xxx.md)
2. 阅读相关设计文档（详细设计.md 中对应章节）
3. 创建/修改指定文件
4. 创建/修改测试文件（tests/gui/ 下）
5. 运行 ruff check . 修复格式问题
6. 运行 pytest tests/ -m "not network" -v 确保通过
7. 写入结果文件 (.task/T-xxx-result.md)
8. 通知主 Agent 完成（返回结果文件路径）
```

---

## 6. 约束与红线

| 红线 | 后果 |
|------|------|
| 修改后端模块（config/database/poller/trigger/mcp/login/utils） | 任务打回重做 |
| pytest 测试不通过 | 任务打回重做 |
| ruff 检查不通过 | 任务打回重做 |
| 不写测试就提交代码 | 任务打回重做 |
| 删除旧 tkinter 代码（Phase 5 之前） | 任务打回重做 |
| 单文件超过 500 行 | 任务打回重做 |

---

## 7. 依赖图

```
T-01 (项目初始化)
  │
  ├── T-02 (SignalBus) ──────────────────────────────────────────────┐
  │   │                                                              │
  │   ├── T-07 (WhitelistModel) ── T-08 (MessagesPage) ── T-09 (Proxy)│
  │   ├── T-10 (SummaryModel) ── T-11 (SummaryDialog)                │
  │   ├── T-12 (StatsPage)                                           │
  │   ├── T-13 (SettingsPage) ── T-14 (CookieLogin)                  │
  │   └── T-15 (LogsPage) ── T-16 (LogPanel)                        │
  │                                                                  │
  ├── T-04 (Sidebar) ──────── T-03 (MainWindow) ────────────────────┤
  │                               │                                  │
  │                               ├── T-05 (qasync)                 │
  │                               ├── T-06 (懒加载)                  │
  │                               ├── T-17 (QSS Theme)              │
  │                               ├── T-18 (TrayIcon)               │
  │                               ├── T-19 (StatusBar)              │
  │                               └── T-20 (WindowState)            │
  │                                                                  │
  └──── 全部完成后 ──── T-21 (PyInstaller) → T-22 (Regression) → T-23 (Cleanup)
```

---

## 8. 启动

```
主 Agent 启动步骤:
1.  .task/ 目录创建
2.  读取 docs/tasks-GUI现代化改造.md 了解全部任务
3.  读取 docs/design-GUI现代化改造-详细设计.md 了解架构细节
4.  创建 .task/queue.md 初始化全部任务为 pending
5.  从 T-01 开始，逐一:
    a. 创建 .task/T-xxx.md 任务定义文件
    b. 通过 Task tool 调用子 Agent (subagent_type=general)
       → prompt 中引用 .task/T-xxx.md 的内容
    c. 子 Agent 完成 → 读取 .task/T-xxx-result.md
    d. 验证结果（手动运行 ruff + pytest 确认）
    e. 更新 .task/queue.md
    f. 进入下一个任务
6.  全部完成后，输出最终总结
```
