# StockMonitor (Windows MVP)

基于 **Python + uv + PySide6 + pywin32 + httpx** 的 Windows 股票悬浮条 MVP。

## 功能

- 无边框、置顶（可配置）的可拖拽悬浮条
- 仅监控 A 股，默认示例代码：`600519,000001,300750`
- 使用腾讯行情接口（`https://qt.gtimg.cn/q=...`）批量获取：名称 / 现价 / 涨跌幅
- UI 每次只显示 1 只股票，并每 3 秒自动轮播到下一只
- 数据刷新频率可配置（`refresh_interval_seconds`），与轮播频率分离
- 请求失败时 UI 显示错误状态，不崩溃
- pywin32 扩展样式：`WS_EX_TOOLWINDOW`
- 系统托盘：增加/删除股票、位置偏移、显示模式、开机自启、检查更新、退出
- 自动更新：启动后及每天定时检查 GitHub Release 最新版本，发现新版本时托盘通知并支持一键下载安装（托盘菜单亦有“检查更新”手动项）
- 增加股票代码时会先校验代码是否真实存在，再加入监控列表
- 右键菜单支持直接配置位置偏移：横向偏移 / 纵向偏移
- 使用 `pydantic-settings` 读取配置（支持 `.env` 覆盖）
- 窗口位置持久化到本地 JSON
- `loguru` 日志输出

## 项目结构（src 布局）

```text
assets/
  icon.ico          # 应用/安装包/托盘图标
  icon.png          # 图标源图
src/stockmonitor/
  main.py
  app.py
  config/settings.py
  models/quote.py
  services/
    stock_api.py
    window_behavior.py
    state_store.py
  ui/
    floating_bar.py
    system_tray.py
```

## 运行

1. 安装依赖（首次）：

```bash
uv sync
```

2. 启动：

```bash
uv run stockmonitor
```

或：

```bash
uv run python -m stockmonitor.main
```

## 配置

可在 `~/.StockMonitor/.env` 创建配置文件：

```env
symbols=600519,000001,300750
refresh_interval_seconds=15
horizontal_offset=0
vertical_offset=0
auto_topmost=true
```

说明：

- `symbols`: 逗号分隔 A 股代码（如 `600519,000001,300750`）
- `refresh_interval_seconds`: 数据刷新间隔秒数（轮播固定每 3 秒）
- `horizontal_offset`: 横向偏移，正数向右，负数向左
- `vertical_offset`: 纵向偏移，正数向下，负数向上
- `auto_topmost`: 是否自动置顶

### A 股代码映射规则（腾讯接口）

- `6/5/9` 开头 -> `sh`（如 `600519` -> `sh600519`）
- `0/2/3` 开头 -> `sz`（如 `000001` -> `sz000001`）

## 本地目录

- 程序数据目录：`~/.StockMonitor`
- 配置文件：`~/.StockMonitor/.env`
- 状态文件：`~/.StockMonitor/state.json`
- 日志目录：`~/.StockMonitor/logs/`
- 日志文件：`~/.StockMonitor/logs/stockmonitor.log`
- 保存内容包括：窗口位置、股票代码列表、位置模式、偏移量配置

## 打包与发布

### 本地构建

#### 前置要求

1. 安装 [Inno Setup 6](https://jrsoftware.org/isinfo.php)
2. 安装项目依赖：`uv sync --group dev`

#### 构建步骤

```bash
# 1. 安装依赖（包含 PyInstaller）
uv sync --group dev

# 2. 使用 spec 文件构建（推荐）
uv run pyinstaller stockmonitor.spec --noconfirm

# 3. 构建 Inno Setup 安装包（需要先安装 Inno Setup）
# PowerShell:
$env:STOCKMONITOR_VERSION = "0.1.0"
ISCC.exe installer/stockmonitor.iss

# 或直接运行（使用默认版本号）：
ISCC.exe installer/stockmonitor.iss
```

构建产物：
- PyInstaller 输出：`dist/StockMonitor/`
- 安装包输出：`dist/StockMonitor-Setup.exe`

### GitHub Release 自动构建

项目配置了 GitHub Actions 自动构建流程：

1. **触发条件**：推送 `v*` 格式的 tag（如 `v0.1.0`），也支持手动触发 workflow
2. **构建环境**：`windows-latest`
3. **构建步骤**：
   - 安装 uv 和 Python 3.14
   - 安装项目依赖（含 dev 组中的 PyInstaller）
   - PyInstaller 打包
   - Inno Setup 生成安装包
   - 创建 GitHub Release 并上传安装包

#### 发布新版本

```bash
# 创建并推送 tag
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions 将自动构建并创建 Release。

> 发布流程会根据 tag 自动同步版本号到 `src/stockmonitor/__init__.py`、`pyproject.toml` 与安装包，确保应用内“检查更新”能正确比较版本。

### 自动更新

- 程序启动约 8 秒后自动检查一次，之后每 24 小时检查一次，亦可通过托盘菜单的“检查更新”手动触发。
- 检查来源：GitHub 仓库的 latest release 页面跳转（`https://github.com/DarlingCY/StockMonitor/releases/latest`），不走 REST API，避免未认证限流。
- 发现新版本时：自动检查会先弹出托盘通知，并打开确认对话框；可选择“下载并安装”（下载 `StockMonitor-Setup.exe` 后退出程序并启动安装程序）、“前往发布页”或“稍后”。
- 版本比较基于 `__version__`，发布时由 CI 从 tag 写入；本地源码运行时版本固定为源码中的 `__version__`。

### 打包配置说明

| 文件 | 说明 |
|------|------|
| `stockmonitor.spec` | PyInstaller 配置，定义入口、隐藏导入、数据文件 |
| `installer/stockmonitor.iss` | Inno Setup 安装器脚本 |
| `.github/workflows/release.yml` | GitHub Actions 自动构建流程 |
