# SeatMonitor System Prototype

这是一个用于公司内部工位管理的简易原型系统。通过检测外接显示器来判断人员位置。

## 目录结构
- `server/`: 基于 Python FastAPI 的服务端，存储绑定关系。
- `client/`: 跨平台 Python 客户端，负责探测硬件和上报。

## 快速开始 (本地开发)

### 1. 启动服务端
你需要先安装依赖并启动服务：

```bash
cd server
pip install -r requirements.txt
uvicorn main:app --reload
```
服务默认运行在 `http://127.0.0.1:8000`。

### 2. 运行客户端
打开一个新的终端窗口：

```bash
cd client
pip install -r requirements.txt
# 注意：Windows 用户可能需要额外运行 pip install wmi pywin32
python3 main.py
```

## 真实环境部署指南 (多机部署)

当您准备在公司内部署时，请遵循以下步骤：

### 1. 服务端部署 (Server)
将 `server` 文件夹部署到一台固定 IP 的服务器上（假设 IP 为 `192.168.1.100`）。

```bash
cd server
pip install -r requirements.txt
# 关键：使用 --host 0.0.0.0 允许外部访问
uvicorn main:app --host 0.0.0.0 --port 8000
```
*提示：请确保服务器防火墙已开放 TCP 8000 端口。*

### 2. 客户端配置 (Client)
在打包分发给员工之前，必须修改客户端连接的服务器地址。

**方法 A：修改代码（推荐）**
打开 `client/main.py`，找到配置区：
```python
# 修改为您服务器的真实 IP 地址
SERVER_URL = "http://192.168.1.100:8000"
```

**方法 B：使用环境变量**
如果不希望修改代码，可以在员工电脑上设置环境变量 `SEAT_MONITOR_URL`，客户端会自动读取。

### 3. 客户端打包 (Packaging)
为了让员工无需安装 Python 即可运行，建议打包成独立的可执行文件。

**安装打包工具:**
```bash
pip install pyinstaller
```

**Windows 打包 (.exe):**
```bash
cd client
pyinstaller --noconfirm --onefile --windowed --name "SeatMonitor" main.py
```
生成文件位于 `dist/SeatMonitor.exe`。

**macOS 打包 (.app):**
```bash
cd client
pyinstaller --noconfirm --onefile --windowed --name "SeatMonitor" main.py
```
生成文件位于 `dist/SeatMonitor.app`。

### 4. 企业安全注意事项
*   **代码签名**: 打包出的 `.exe` 或 `.app` 未经签名，可能会被 Windows Defender 或 macOS Gatekeeper 拦截。在正式分发前，建议使用企业证书进行代码签名。
*   **白名单**: 如果无法签名，请联系 IT 部门将程序的 Hash 值加入防病毒软件的白名单。

## 功能说明

1.  **自动检测**: 客户端启动后会自动扫描外接显示器（通过 ioreg 或 WMI）。
2.  **首次绑定**: 如果该显示器是第一次出现在系统中，电脑上会弹出一个 GUI 输入框，要求输入当前的工位号（如 `A-001`）。
3.  **自动上报**: 输入并确认后，系统会记录绑定关系。之后每隔 10 秒（生产环境建议改为 5 分钟），客户端会自动发送心跳包。
4.  **查看状态**: 管理员可以访问 `http://192.168.1.100:8000/dashboard` 查看当前在线的工位列表。

## 可视化地图配置 (高级功能)

本系统支持通过楼层平面图直观展示工位状态（🔴占用 / 🟢空闲）。

### 1. 准备素材
*   找一张公司的平面图（推荐 PNG 格式），重命名为 `floor1.png`。
*   将图片放入服务端的 `server/static/maps/` 目录中。

### 2. 生成坐标数据
*   访问编辑器: `http://<server-ip>:8000/map/editor`
*   在网页上点击图片中的工位位置，并输入对应的工位号（如 `A-101`）。
*   标记完成后，点击 **"导出 JSON"** 按钮。
*   将下载的文件重命名为 `floor1_coords.json`。
*   将该 JSON 文件也放入 `server/static/maps/` 目录中。

### 3. 查看效果

*   访问: `http://<server-ip>:8000/map/view`

*   您将看到地图上覆盖了实时的状态指示点。



## SVG 可视化地图 (推荐)



新版 SVG 模式支持无限缩放、平滑拖拽，并提供更现代的 UI。



### 1. 准备素材

*   使用绘图工具（如 Inkscape, Figma）创建或导出您的楼层平面图为 `floor1.svg`。

*   **关键配置**: 在 SVG 中，将代表工位的图形（如矩形）进行编组，并设置属性 `class="seat"` 和 `data-id="工位号"`。

    ```xml

    <g class="seat" data-id="A-101">

        <rect ... />

    </g>

    ```

*   将文件放入 `server/static/maps/floor1.svg`。



### 2. 查看效果

*   访问: `http://<server-ip>:8000/map/svg`

*   支持鼠标滚轮缩放、左键拖拽平移。



## 目录结构说明
