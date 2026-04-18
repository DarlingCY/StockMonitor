# StockMonitor (Windows MVP)

基于 **Python + uv + PySide6 + pywin32 + httpx** 的 Windows 股票悬浮条 MVP。

## 功能

- 无边框、置顶（可配置）的可拖拽悬浮条
- 仅监控 A 股，默认示例代码：`600519,000001,300750`
- 使用腾讯行情接口（`https://qt.gtimg.cn/q=...`）批量获取：名称 / 现价 / 涨跌幅
- UI 每次只显示 1 只股票，并每 3 秒自动轮播到下一只
- 数据刷新频率可配置（`refresh_interval_seconds`），与轮播频率分离
- 悬浮条背景色可配置（默认透明），透明背景下文字可读
- 请求失败时 UI 显示错误状态，不崩溃
- pywin32 扩展样式：`WS_EX_TOOLWINDOW`
- 系统托盘：二级菜单内输入增加股票代码、删除股票代码、退出
- 增加股票代码时会先校验代码是否真实存在，再加入监控列表
- 右键菜单支持直接配置位置偏移：横向偏移 / 纵向偏移
- 使用 `pydantic-settings` 读取配置（支持 `.env` 覆盖）
- 窗口位置持久化到本地 JSON
- `loguru` 日志输出

## 项目结构（src 布局）

```text
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
background_color=rgba(24, 24, 24, 220)
```

说明：

- `symbols`: 逗号分隔 A 股代码（如 `600519,000001,300750`）
- `refresh_interval_seconds`: 数据刷新间隔秒数（轮播固定每 3 秒）
- `horizontal_offset`: 横向偏移，正数向右，负数向左
- `vertical_offset`: 纵向偏移，正数向下，负数向上
- `auto_topmost`: 是否自动置顶
- `background_color`: 悬浮条背景色，默认 `rgba(24, 24, 24, 220)`（可填 `transparent` 或 `rgba(...)` 等）

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

### 打包配置说明

| 文件 | 说明 |
|------|------|
| `stockmonitor.spec` | PyInstaller 配置，定义入口、隐藏导入、数据文件 |
| `installer/stockmonitor.iss` | Inno Setup 安装器脚本 |
| `.github/workflows/release.yml` | GitHub Actions 自动构建流程 |
