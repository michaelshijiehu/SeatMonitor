# SeatMonitor Project Context

## 1. 项目概述
SeatMonitor 是一个工位管理系统，利用外接显示器的唯一序列号 (SN) 来识别物理工位，并追踪员工的实时位置。
- **核心原理**: 客户端运行在员工电脑上，探测外接显示器 SN -> 上报服务端 -> 服务端判断该 SN 绑定的工位 -> 记录人员状态。
- **解决痛点**: 共享工位管理、人员去向查询。

## 2. 技术栈
- **Server**: Python 3.13+, FastAPI, SQLite, Jinja2 (服务端渲染)
- **Client**: Python 3.13+, Requests, Tkinter (GUI), IOKit (macOS), WMI (Windows)

## 3. 项目结构
```text
/
├── client/                 # 客户端代码 (运行在员工电脑)
│   ├── main.py             # 主程序：循环检测、心跳上报
│   ├── monitor_probe.py    # 硬件层：跨平台获取显示器 SN (含 EDID 解析)
│   ├── ui.py               # 交互层：Tkinter 弹窗 (工位绑定)
│   └── requirements.txt
├── server/                 # 服务端代码 (运行在服务器)
│   ├── main.py             # FastAPI 应用：API + 数据库逻辑
│   ├── seat_monitor.db     # SQLite 数据库
│   ├── static/             # 静态文件 (存放地图图片和坐标 JSON)
│   │   └── maps/           # 包含 floor1.png, floor1.svg, floor1_coords.json
│   ├── templates/          # HTML 模板
│   │   ├── mappings.html   # 列表管理页面
│   │   ├── editor.html     # 旧版坐标拾取工具
│   │   ├── map.html        # 旧版 Image Map 看板
│   │   └── map_svg.html    # 新版 SVG 交互看板 (Panzoom)
│   ├── view_data.py        # CLI 查看工具
│   └── requirements.txt
├── claude.md               # AI 上下文文件
└── README.md               # 用户文档
```

## 4. 关键逻辑说明

### 4.1 硬件探测 (monitor_probe.py)
- **macOS**: 使用 `ioreg -l -w0 -r -c IODisplayConnect -a` 获取数据，递归查找 `IODisplayEDID`。
    - *特殊处理*: 过滤 VendorID 为 `1552` (Apple) 的内置屏幕。
    - *SN获取*: 优先解析 EDID Hex 中的 ASCII Descriptor (Tag `0xFF`)，如果失败则使用系统注册表的 `DisplaySerialNumber`，如果都失败则生成 Hash。
- **Windows**: 使用 `WMI` (`WmiMonitorID`) 获取。
    - *依赖*: 需要 `wmi` 和 `pywin32` 库。

### 4.2 GUI 交互 (ui.py)
- **框架**: 使用 Python 内置的 `tkinter` 以避免引入大型 GUI 库。
- **macOS 兼容性修复**: 
    - 在 macOS 上，直接调用 `destroy()` 可能导致僵尸窗口。
    - **解决方案**: 采用 `root.withdraw()` (隐藏) -> `root.update()` (刷新事件) -> `root.destroy()` (销毁) 的顺序。**请勿修改此逻辑**。

### 4.3 服务端设计 (server/main.py)
- **数据库**: SQLite。启动时自动建表 (`mappings`, `live_status`)。
- **静态文件**: 挂载了 `/static` 目录。
- **地图逻辑 (SVG)**: 
    - 页面 `/map/svg` 采用 `@panzoom/panzoom` 库实现画布操作。
    - 前端通过 `fetch` 获取原始 SVG 并注入 DOM，随后根据 `/api/mappings` 返回的状态，动态查找 `data-id` 对应的元素并切换 `seat-free`/`seat-busy` 类名。
- **地图逻辑 (旧版)**: 
    - 用户通过 `/map/editor` 拾取坐标并下载 `floor1_coords.json`。
    - 看板页面 `/map/view` 加载该 JSON 并在前端渲染指示点。
- **API**:
    - `POST /check_monitor`: 检查 SN 是否绑定。
    - `POST /bind_seat`: 绑定 SN 到工位。
    - `POST /heartbeat`: 客户端定期发送心跳。
    - `GET /mappings`: (HTML) 表格管理看板。
    - `GET /api/mappings`: (JSON) 纯数据接口。
    - `GET /map/svg`: (HTML) 基于 SVG 的现代可视化看板。
- **容错**: 增加了 `get_db_cursor()`，每次请求检查表是否存在，防止文件误删导致服务崩溃。

## 5. 待优化项 (TODO)
- **安全**: 目前 API 无鉴权，内网环境尚可，公网需增加 Token 验证。
- **多屏支持**: 目前客户端逻辑只处理检测到的*第一个*外接显示器，多屏场景需优化逻辑。
- **打包**: 需要编写 GitHub Actions 脚本自动打包 `.exe` 和 `.app`。

## 6. 运行指南
```bash
# Server
cd server && pip install -r requirements.txt
python3 -m uvicorn main:app --reload --host 0.0.0.0

# Client
cd client && pip install -r requirements.txt
python main.py
```