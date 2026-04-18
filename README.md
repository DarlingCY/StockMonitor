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
- pywin32 扩展样式：`WS_EX_NOACTIVATE` / `WS_EX_TOOLWINDOW`
- 系统托盘：二级菜单内输入增加股票代码、删除股票代码、退出
- 增加股票代码时会先校验代码是否真实存在，再加入监控列表
- 右键菜单支持直接配置位置：水平为“左 / 中 / 右”，垂直为“上 / 中 / 下”
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
horizontal_align=left
vertical_align=top
auto_topmost=true
background_color=rgba(24, 24, 24, 220)
```

说明：

- `symbols`: 逗号分隔 A 股代码（如 `600519,000001,300750`）
- `refresh_interval_seconds`: 数据刷新间隔秒数（轮播固定每 3 秒）
- `horizontal_align`: 水平位置，支持 `left / center / right`
- `vertical_align`: 垂直位置，支持 `top / center / bottom`
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
- 保存内容包括：窗口位置、股票代码列表、位置模式、锚点位置配置
