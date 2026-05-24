# 任务清单：Bilibili AI Client GUI 现代化改造

## 任务概览

```
Phase 1: 框架搭建 ──→ Phase 2: 核心页面 ──→ Phase 3: 设置与日志 ──→ Phase 4: 增强 ──→ Phase 5: 收尾
  (2天)                  (3天)                  (2天)                  (2天)                  (2天)
                                                                                                │
                                                                                         测试贯穿全流程
                                                                                         (每个 Phase 含测试)
```

**总预计：11 天**  
**红线**：任何阶段不得修改后端模块（`config.py` / `database.py` / `message_poller.py` / `openclaw_trigger.py` / `mcp_server.py` / `bilibili_login.py` / `utils/`）

---

## Phase 1：框架搭建（2 天）

### T-01 项目初始化与依赖安装

| 字段 | 内容 |
|------|------|
| **描述** | 安装 PySide6 + qasync，更新 `pyproject.toml`，创建 `gui/` 新目录结构 |
| **文件** | `pyproject.toml`, `gui/__init__.py`, `gui/app.py` |
| **验收** | `pip install PySide6 qasync` 成功；`gui/` 目录结构创建完毕 |
| **测试** | T-TC-01: 验证新依赖可正常 import，不破坏现有 `pytest` 运行 |

### T-02 SignalBus 信号总线

| 字段 | 内容 |
|------|------|
| **描述** | 实现 `gui/signal_bus.py`，定义全部信号（含 `log_message`） |
| **文件** | `gui/signal_bus.py` |
| **验收** | 所有信号定义完整；全局单例 `signal_bus` 可 import；emit/connect 正常工作 |
| **测试** | T-TC-02: 单元测试 SignalBus 所有信号的 emit → connect 链路 |

### T-03 MainWindow 主窗口骨架

| 字段 | 内容 |
|------|------|
| **描述** | 实现 `gui/main_window.py`：QMainWindow + 菜单栏 + QSplitter + QStackedWidget 骨架 |
| **文件** | `gui/main_window.py` |
| **验收** | 窗口可显示，菜单栏三个菜单（文件/视图/帮助）完整，分割器可拖动 |
| **测试** | T-TC-03: 通过 `QTest` 模拟菜单点击，验证信号触发 |

### T-04 SidebarWidget 侧边导航栏

| 字段 | 内容 |
|------|------|
| **描述** | 实现 `gui/widgets/sidebar.py`：5 个导航按钮（消息记录/摘要历史/统计/系统日志/设置）+ 主题切换按钮 |
| **文件** | `gui/widgets/sidebar.py` |
| **验收** | 5 个按钮点击正确切换 QStackedWidget 页面；选中状态高亮；主题切换按钮工作 |
| **测试** | T-TC-04: 模拟按钮点击，验证 `page_changed` 信号参数正确 |

### T-05 qasync 集成与 main.py 适配

| 字段 | 内容 |
|------|------|
| **描述** | 实现 `gui/app.py` 入口函数；改造 `main.py` 使用 qasync；验证 asyncio + Qt 共存 |
| **文件** | `gui/app.py`, `main.py` |
| **验收** | `python main.py --mode gui` 正常启动；`--mode mcp` / `--mode webhook` 行为不变 |
| **测试** | T-TC-05: 运行 `--mode mcp` 验证输出与改造前完全一致；运行 `--mode webhook` 验证相同 |

### T-06 懒加载机制

| 字段 | 内容 |
|------|------|
| **描述** | 实现页面懒加载：启动时只创建 MessagesPage，其余页面首次访问时创建 |
| **文件** | `gui/main_window.py` |
| **验收** | 启动后内存中只有 MessagesPage 实例；切换到各页面后实例逐一创建 |
| **测试** | T-TC-06: 启动后检查 `_pages` 数组非空索引只有 [0]；逐个切换后验证 |

---

## Phase 2：核心页面（3 天）

### T-07 WhitelistModel + 白名单面板

| 字段 | 内容 |
|------|------|
| **描述** | 实现 `gui/models/whitelist_model.py`（QAbstractListModel）+ 侧边栏白名单 UI 集成 |
| **文件** | `gui/models/whitelist_model.py`, `gui/main_window.py`（集成） |
| **验收** | 白名单列表正确显示 UID + 用户名；添加/删除功能通过数据库操作正常 |
| **测试** | T-TC-07: 单元测试 WhitelistModel 的 refresh/data/rowCount；集成测试添加/删除流程 |

### T-08 MessageTableModel + MessagesPage

| 字段 | 内容 |
|------|------|
| **描述** | 实现 `gui/models/message_model.py` + `gui/pages/messages_page.py` |
| **文件** | `gui/models/message_model.py`, `gui/pages/messages_page.py` |
| **验收** | 消息列表分页显示（LIMIT 200）；状态图标（✅/○/❌）正确；双击触发处理流程；右键菜单完整；状态筛选 + 搜索过滤有效 |
| **测试** | T-TC-08: 单元测试 MessageTableModel 的数据绑定；测试筛选/搜索代理逻辑 |

### T-09 MessageFilterProxy 搜索与过滤

| 字段 | 内容 |
|------|------|
| **描述** | 实现 `MessageFilterProxy`（QSortFilterProxyModel）：文本搜索 + 状态筛选叠加 |
| **文件** | `gui/pages/messages_page.py` |
| **验收** | 搜索框输入过滤所有列；状态下拉框叠加过滤；组合使用正确 |
| **测试** | T-TC-09: 单元测试 filterAcceptsRow 的各种组合（纯文本/纯状态/组合） |

### T-10 SummaryTableModel + HistoryPage

| 字段 | 内容 |
|------|------|
| **描述** | 实现 `gui/models/summary_model.py` + `gui/pages/history_page.py` |
| **文件** | `gui/models/summary_model.py`, `gui/pages/history_page.py` |
| **验收** | 摘要列表显示 BV 号/发送者/摘要预览/时间；搜索过滤有效；双击或点击"查看详情"打开弹窗 |
| **测试** | T-TC-10: 单元测试 SummaryTableModel；测试搜索过滤；测试弹窗数据正确 |

### T-11 SummaryDetailDialog 摘要详情弹窗

| 字段 | 内容 |
|------|------|
| **描述** | 实现 `gui/widgets/summary_dialog.py`：显示 BV 号/发送者/时间/字幕原文/摘要全文 |
| **文件** | `gui/widgets/summary_dialog.py` |
| **验收** | 弹窗显示完整信息；字幕和摘要区域只读；关闭按钮正常 |
| **测试** | T-TC-11: 通过 mock 数据验证弹窗各字段正确显示 |

### T-12 StatCard + StatsPage

| 字段 | 内容 |
|------|------|
| **描述** | 实现 `gui/widgets/stat_card.py` + `gui/pages/stats_page.py`：3 张统计卡片 |
| **文件** | `gui/widgets/stat_card.py`, `gui/pages/stats_page.py` |
| **验收** | 今日处理/总处理量/成功率三张卡片显示正确；数据随 `signal_bus.stats_updated` 自动刷新 |
| **测试** | T-TC-12: 单元测试 StatCard 值更新；测试 signal_bus.stats_updated 驱动 UI 更新 |

---

## Phase 3：设置与日志（2 天）

### T-13 SettingsPage 设置页

| 字段 | 内容 |
|------|------|
| **描述** | 实现 `gui/pages/settings_page.py`：5 个设置分组（B站认证/轮询/OpenClaw/Webhook/摘要推送）+ 保存按钮 |
| **文件** | `gui/pages/settings_page.py` |
| **验收** | 所有控件读取 `config.py` 正确显示；修改后点"保存"写入配置；Cookie 显示为 `********` |
| **测试** | T-TC-13: 单元测试配置读写；测试 Cookie 遮蔽显示；测试"保存"后配置文件实际改变 |

### T-14 Cookie 登录流程集成

| 字段 | 内容 |
|------|------|
| **描述** | 集成网页登录（QDesktopServices + QThread）、手动输入 Cookie、清除登录 |
| **文件** | `gui/pages/settings_page.py`, `gui/main_window.py` |
| **验收** | 网页登录打开浏览器并检测结果；手动输入保存加密；清除删除 Cookie；状态实时更新 |
| **测试** | T-TC-14: 模拟登录流程，验证 `signal_bus.login_status_changed` 触发；验证 Cookie 加密存储 |

### T-15 LogsPage 系统日志页

| 字段 | 内容 |
|------|------|
| **描述** | 实现 `gui/pages/logs_page.py`：挂接 loguru，实时显示日志，支持级别过滤 + 搜索 + 自动滚动 |
| **文件** | `gui/pages/logs_page.py` |
| **验收** | 启动后日志实时追加；级别过滤（ALL/DEBUG/INFO/WARNING/ERROR）正确；搜索过滤有效；自动滚动开关正常；清屏功能正常；最大 10000 条不溢出 |
| **测试** | T-TC-15: 通过 logger 写入不同级别日志，验证过滤器行为；测试 10000 条溢出行为 |

---

## Phase 4：增强（2 天）

### T-16 LogPanel 底部折叠日志面板

| 字段 | 内容 |
|------|------|
| **描述** | 实现 `gui/widgets/log_panel.py`：与 LogsPage 共用 loguru sink，折叠式快捷视图，保留最近 200 条 |
| **文件** | `gui/widgets/log_panel.py` |
| **验收** | 折叠/展开正常；显示最近 200 条日志；双击跳转到 LogsPage；"打开完整日志"按钮切换页面 |
| **测试** | T-TC-16: 验证 LogPanel 与 LogsPage 共用同一 sink；验证 200 条截断 |

### T-17 QSS 主题系统

| 字段 | 内容 |
|------|------|
| **描述** | 实现 `gui/theme.py` + `gui/themes/light.qss` + `gui/themes/dark.qss`：完整明/暗两套主题 |
| **文件** | `gui/theme.py`, `gui/themes/light.qss`, `gui/themes/dark.qss` |
| **验收** | 启动默认加载配置主题；运行时切换（菜单或侧边栏按钮）；全部控件主题一致；切换流畅 |
| **测试** | T-TC-17: 验证两套 QSS 文件语法正确；切换后验证关键控件的样式生效 |

### T-18 QSystemTrayIcon 系统托盘

| 字段 | 内容 |
|------|------|
| **描述** | 实现 TrayManager：系统托盘图标 + 右键菜单（显示/隐藏/暂停轮询/退出）+ 通知推送 |
| **文件** | `gui/main_window.py` |
| **验收** | 最小化到托盘；托盘双击恢复；右键菜单功能完整；处理完成发送通知 |
| **测试** | T-TC-18: 模拟托盘操作，验证菜单项信号触发正确 |

### T-19 状态栏增强

| 字段 | 内容 |
|------|------|
| **描述** | 实现状态栏：状态文本 + 轮询指示器（● 轮询中/○ 已停止）+ 今日处理量常驻显示 |
| **文件** | `gui/main_window.py` |
| **验收** | 状态文本随操作更新；轮询指示器跟随 `signal_bus.poller_status_changed`；今日处理量自动更新 |
| **测试** | T-TC-19: 验证状态栏各标签通过信号驱动更新 |

### T-20 窗口状态持久化

| 字段 | 内容 |
|------|------|
| **描述** | 保存/恢复窗口大小、位置、分割器位置到 QSettings |
| **文件** | `gui/main_window.py` |
| **验收** | 关闭窗口时保存 geometry + splitter state；重新打开恢复上次状态 |
| **测试** | T-TC-20: 手动验证窗口状态跨会话保持 |

---

## Phase 5：收尾（2 天）

### T-21 PyInstaller 打包适配

| 字段 | 内容 |
|------|------|
| **描述** | 更新 `bilibili_ai_client_gui.spec`，添加 PySide6 plugins 和 QSS 资源文件 |
| **文件** | `bilibili_ai_client_gui.spec` |
| **验收** | `pyinstaller bilibili_ai_client_gui.spec --clean --noconfirm` 成功；生成的 .exe 可正常启动 |
| **测试** | T-TC-21: 验证打包后 exe 启动速度 < 5s；全部功能正常 |

### T-22 全面回归测试

| 字段 | 内容 |
|------|------|
| **描述** | 运行全部现有测试 + 新增 GUI 测试；4 种模式验证 |
| **文件** | — |
| **验收** | 170+ 非网络测试全部通过；GUI 测试全部通过；4 种模式均正常 |
| **测试** | 见下方"测试计划"章节 |

### T-23 旧 tkinter 代码清理

| 字段 | 内容 |
|------|------|
| **描述** | 确认新 GUI 全部功能验证通过后，删除 `gui/main_window.py`（旧 tkinter 版） |
| **文件** | `gui/main_window.py`（删除旧文件） |
| **验收** | 旧文件删除后软件运行正常；git 可回退恢复 |
| **测试** | 删除后完整运行一遍验收用例 |

---

## 测试计划

### 测试层级

```
层级 1: 单元测试（Unit Test）
  └── 每个 Model/Widget/Page 独立测试，mock 外部依赖
  └── 工具: pytest + pytest-qt

层级 2: 集成测试（Integration Test）
  └── SignalBus 信号链路 → 后端模块联动
  └── 页面切换 → 数据加载联动
  └── 设置保存 → config.py 联动

层级 3: 系统测试（System Test）
  └── 4 种运行模式验证
  └── 与旧 tkinter GUI 功能对标
  └── 打包后功能验证

层级 4: 回归测试（Regression Test）
  └── 现有 170+ 非网络测试全部通过
  └── 非 GUI 模式（mcp/webhook）行为不变
```

### 测试环境

| 项目 | 要求 |
|------|------|
| Python | >= 3.11 |
| 操作系统 | Windows 11（主），Linux/macOS 可选 |
| 显示器 | 至少 1920x1080（支持高 DPI 缩放验证） |
| 数据库 | 测试用独立 SQLite（`tmp_path` fixture） |
| 网络 | 非网络测试不依赖网络，网络测试标记 `@pytest.mark.network` |

### 测试工具

| 工具 | 用途 | 安装 |
|------|------|------|
| `pytest` | 测试框架 | 已有 |
| `pytest-qt` | Qt GUI 测试（mock QApplication） | `pip install pytest-qt` |
| `pytest-mock` | 强化 mock 能力 | `pip install pytest-mock` |
| `ruff` | 代码规范检查 | 已有 |

### 测试用例清单

#### T-TC-01: 依赖安装验证
```
前提: 新环境
步骤: pip install PySide6 qasync pytest-qt
验证: import PySide6, import qasync, import pytest_qt 均无报错
```

#### T-TC-02: SignalBus 信号链路
```
前提: signal_bus 单例
步骤: 每个信号 connect 一个 spy → emit → 验证 spy 被调用且参数正确
验证: 15 个信号（含 log_message）均通过
文件: tests/gui/test_signal_bus.py
```

#### T-TC-03: MainWindow 菜单栏
```
前提: QApplication 已创建（pytest-qt qtbot fixture）
步骤: 遍历菜单 Action → 触发 → 验证对应 signal 被 emit
验证: "刷新"/"退出"/"显示日志面板"/"清空日志"/"切换深色主题"/"关于" 各触发正确信号
文件: tests/gui/test_main_window.py
```

#### T-TC-04: SidebarWidget 导航
```
前提: qtbot + MainWindow
步骤: 点击 5 个导航按钮 → 验证 QStackedWidget 当前索引
验证: 点击顺序 0-4 对应页面索引 0-4；选中状态仅当前按钮 active
文件: tests/gui/test_sidebar.py
```

#### T-TC-05: CLI 模式兼容
```
前提: 原始 main.py + 改造后 main.py
步骤: python main.py --mode mcp （对比新旧输出）
      python main.py --mode webhook （对比新旧行为）
验证: 输出完全一致；webhook 请求处理相同
文件: tests/test_cli_modes.py
备注: 此测试最为关键，确保非 GUI 模式零影响
```

#### T-TC-06: 懒加载验证
```
前提: qtbot + MainWindow
步骤: 启动后检查 self._pages → 仅 [0] 非 None
      逐个切换到索引 1,2,3,4 → 每切换后检查对应索引从 None 变为对象
验证: 始终只有当前页 + 历史访问页占用内存
文件: tests/gui/test_lazy_loading.py
```

#### T-TC-07: 白名单模型 + 操作
```
前提: test_db fixture（空数据库）
步骤: 1. 调用 database.add_whitelist("123", "test_user")
      2. WhitelistModel.refresh() → 验证 rowCount=1, data 显示 "123 (test_user)"
      3. 调用 database.remove_whitelist("123")
      4. WhitelistModel.refresh() → 验证 rowCount=0
验证: 数据与 UI 同步
文件: tests/gui/test_whitelist_model.py
```

#### T-TC-08: 消息表格模型
```
前提: test_db fixture + 3 条测试消息
步骤: MessageTableModel.refresh() → 验证行数/列数/各列数据
验证: status 字段映射为 ✅/○/❌；UserRole 返回 msg_id
文件: tests/gui/test_message_model.py
```

#### T-TC-09: 消息筛选/搜索代理
```
前提: MessageTableModel 含 5 条不同状态的消息
步骤: 1. 设置文本过滤 "BV1" → 验证 rowCount
      2. 设置状态过滤 "processed" → 验证 rowCount
      3. 组合过滤 → 验证两者叠加
验证: filterAcceptsRow 逻辑正确
文件: tests/gui/test_message_proxy.py
```

#### T-TC-10: 摘要模型 + 页面
```
前提: test_db fixture + 2 条摘要
步骤: SummaryTableModel.refresh() → 验证行列数据
      搜索过滤 → 验证结果
验证: 摘要列表功能正常
文件: tests/gui/test_summary_model.py
```

#### T-TC-11: 摘要详情弹窗
```
前提: qtbot + mock 摘要数据
步骤: SummaryDetailDialog(data) → 验证各字段显示
验证: BV 号/发送者/时间/字幕原文/摘要全文 均正确显示
文件: tests/gui/test_summary_dialog.py
```

#### T-TC-12: 统计卡片自动更新
```
前提: qtbot + StatsPage
步骤: signal_bus.stats_updated.emit({today:5, total:100, success_rate:"95%"})
      验证 StatCard 文本更新为对应值
文件: tests/gui/test_stats_page.py
```

#### T-TC-13: 设置页配置读写
```
前提: config_backup fixture
步骤: 1. 修改 polling_interval → 保存 → 验证 config.get 值
      2. Cookie 遮蔽显示 "********"
      3. 修改推送渠道 → 保存 → 验证
验证: 所有设置控件读写正确
文件: tests/gui/test_settings_page.py
```

#### T-TC-14: Cookie 登录流程
```
前提: mock bilibili_login server
步骤: 模拟网页登录 → 检测 config.bili_auth 变化 → login_status_changed 触发
      手动输入 Cookie → 验证加密存储
      清除 → 验证 config.bili_auth == ""
验证: 三种登录方式均工作；Cookie 不可见
文件: tests/gui/test_cookie_login.py
```

#### T-TC-15: 系统日志页
```
前提: qtbot + LogsPage
步骤: 1. logger.info("test info") → 验证日志显示
      2. 切换到 ERROR 级别过滤 → logger.warning 不显示 → logger.error 显示
      3. 搜索框输入关键字 → 验证过滤
      4. 填充 10001 条日志 → 验证最多 10000 条
验证: 日志显示/过滤/搜索/截断均正常
文件: tests/gui/test_logs_page.py
```

#### T-TC-16: LogPanel 底部日志
```
前提: qtbot + MainWindow
步骤: 1. 点击展开 LogPanel → 验证可见
      2. 写入 250 条日志 → 验证仅保留 200 条
      3. 双击某日志 → 验证切换到 LogsPage
      4. 点击"打开完整日志" → 验证切换到索引 3
验证: 快捷面板与完整页共用资源
文件: tests/gui/test_log_panel.py
```

#### T-TC-17: QSS 主题切换
```
前提: qtbot + MainWindow
步骤: 1. 启动验证 light 主题加载
      2. 切换 dark → 验证背景色/文字色改变
      3. 切回 light → 验证恢复
验证: 主题切换不丢样式；全部控件受 QSS 控制
文件: tests/gui/test_theme.py
```

#### T-TC-18: 系统托盘
```
前提: qtbot + MainWindow（QSystemTrayIcon 可用）
步骤: 模拟双击托盘 → 验证窗口显示/隐藏
      右键菜单各选项 → 验证信号触发
验证: 托盘功能完整
文件: tests/gui/test_tray.py
```

#### T-TC-19: 状态栏更新
```
前提: qtbot + MainWindow
步骤: 1. signal_bus.poller_status_changed.emit(True) → 状态栏显示"● 轮询中"
      2. signal_bus.stats_updated.emit({today: 10, ...}) → 今日: 10
验证: 状态栏信号驱动正确
文件: tests/gui/test_statusbar.py
```

#### T-TC-20: 窗口状态持久化
```
前提: qtbot + QSettings 使用临时路径
步骤: 1. 设置窗口大小 → 关闭 → 重新创建 MainWindow → 验证恢复
      2. 拖动分割器 → 关闭 → 重新创建 → 验证恢复
验证: Geometry + Splitter state 跨会话保持
文件: tests/gui/test_window_state.py
```

#### T-TC-21: PyInstaller 打包验证
```
前提: 完整项目
步骤: pyinstaller bilibili_ai_client_gui.spec --clean --noconfirm
      运行 dist/BilibiliAIClient.exe
验证: exe 启动速度 < 5s；窗口正常显示；QSS 主题生效
文件: —（手动测试）
```

#### T-TC-22: 全面回归 — 四种模式验证

```
前提: 全部开发和测试完成

--- 模式 1: --mode mcp ---
步骤: python main.py --mode mcp
验证: 输出与改造前完全一致（对比 git 中旧版输出）
      MCP 6 tools 全部可用

--- 模式 2: --mode webhook ---
步骤: python main.py --mode webhook
      发送测试 POST 请求到 webhook 端口
验证: 消息正常入库，行为同旧版

--- 模式 3: --mode gui ---
步骤: python main.py --mode gui
验证: 窗口 0.5s 内可见；所有页面完整；操作流畅

--- 模式 4: --mode all ---
步骤: python main.py --mode all
验证: GUI + MCP + Webhook + Poller 全部同时运行

--- 数据库兼容 ---
步骤: 将旧版 db 文件复制到新版目录
验证: 新版 GUI 可读取旧版数据库的全部消息和摘要

文件: tests/test_regression.py
备注: 此测试为底线，确保不破坏任何现有功能
```

### 现有测试保有策略

| 措施 | 说明 |
|------|------|
| **不删除** | 不删除、不修改任何现有测试文件 |
| **不动 conftest** | `tests/conftest.py` 的 fixture 保持不变 |
| **只新增** | GUI 测试文件放在 `tests/gui/` 目录下 |
| **CI 双重验证** | `python -m pytest tests/ -m "not network" -v`（不含 GUI 测试）→ 保障旧测试 |
| **CI 完整验证** | `python -m pytest tests/ -m "not network" -v` + `pytest tests/gui/ -v`（含 GUI） |

### GUI 测试目录结构

```
tests/
├── __init__.py
├── conftest.py              # 现有 fixture（不变）
├── test_cli_modes.py        # T-TC-05 CLI 模式兼容
├── test_regression.py       # T-TC-22 全面回归
└── gui/                     # 新增 GUI 测试
    ├── __init__.py
    ├── conftest.py           # GUI 测试专属 fixture（为 qtbot 创建 QApplication）
    ├── test_signal_bus.py    # T-TC-02
    ├── test_main_window.py   # T-TC-03
    ├── test_sidebar.py       # T-TC-04
    ├── test_lazy_loading.py  # T-TC-06
    ├── test_whitelist_model.py       # T-TC-07
    ├── test_message_model.py         # T-TC-08
    ├── test_message_proxy.py         # T-TC-09
    ├── test_summary_model.py         # T-TC-10
    ├── test_summary_dialog.py        # T-TC-11
    ├── test_stats_page.py            # T-TC-12
    ├── test_settings_page.py         # T-TC-13
    ├── test_cookie_login.py          # T-TC-14
    ├── test_logs_page.py             # T-TC-15
    ├── test_log_panel.py             # T-TC-16
    ├── test_theme.py                 # T-TC-17
    ├── test_tray.py                  # T-TC-18
    ├── test_statusbar.py             # T-TC-19
    └── test_window_state.py          # T-TC-20
```

### GUI 测试 conftest.py 示例

```python
# tests/gui/conftest.py
import pytest
from PySide6.QtWidgets import QApplication

@pytest.fixture(scope="session")
def qapp():
    """pytest-qt 需要 QApplication 实例"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

@pytest.fixture
def main_window(qapp, qtbot, test_db):
    from gui.main_window import MainWindow
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    yield window
    window.close()
```

### 验收检查清单

完成所有 Phase 后，逐项验收：

```
□ 170+ 现有非网络测试全部通过（python -m pytest tests/ -m "not network" -v）
□ 全部 GUI 测试通过（pytest tests/gui/ -v）
□ 4 种运行模式均正常（mcp / webhook / gui / all）
□ PyInstaller 打包成功，exe 运行正常
□ 启动速度：窗口可见 < 0.5s，数据加载 < 2s
□ 明/暗主题切换正常
□ 系统托盘完整功能
□ 窗口状态跨会话保持
□ 实时日志显示正常
□ 后端模块 0 行改动
□ 旧 GUI 可回退（保留旧文件直到全部验证通过）
```
