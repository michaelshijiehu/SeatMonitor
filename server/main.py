import sqlite3
import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager

DB_FILE = "seat_monitor.db"
templates = Jinja2Templates(directory="templates")

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Table 1: 绑定关系 (显示器 SN -> 工位号)
    c.execute('''CREATE TABLE IF NOT EXISTS mappings
                 (monitor_sn TEXT PRIMARY KEY, 
                  vendor_id TEXT, 
                  product_id TEXT, 
                  seat_id TEXT, 
                  created_at TIMESTAMP)''')
    
    # Table 2: 实时状态 (工位号 -> 当前用户)
    c.execute('''CREATE TABLE IF NOT EXISTS live_status
                 (seat_id TEXT PRIMARY KEY, 
                  user_name TEXT, 
                  host_name TEXT, 
                  last_heartbeat TIMESTAMP,
                  machine_serial TEXT)''')
    
    # 自动迁移：尝试添加 machine_serial 列 (如果老数据库只有4列)
    try:
        c.execute("ALTER TABLE live_status ADD COLUMN machine_serial TEXT")
    except sqlite3.OperationalError:
        pass # 列可能已存在
        
    conn.commit()
    conn.close()

# 确保如果文件被删了，能在请求时恢复 (针对开发环境的容错)
def get_db_cursor():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 简单的探针：检查 mappings 表是否存在
    try:
        c.execute("SELECT 1 FROM mappings LIMIT 1")
    except sqlite3.OperationalError:
        # 如果表不存在，重新初始化
        conn.close()
        init_db()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
    return conn, c

# 使用 lifespan 确保启动时初始化
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# 挂载静态文件 (用于地图图片和 JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Models ---
class MonitorInfo(BaseModel):
    serial_number: str
    vendor_id: str
    product_id: str

class BindRequest(BaseModel):
    monitor: MonitorInfo
    seat_id: str

class HeartbeatRequest(BaseModel):
    seat_id: str
    monitor_sn: str
    user_name: str
    host_name: str
    machine_serial: str

# --- Routes ---

@app.get("/")
def read_root():
    return {"status": "SeatMonitor Server Running"}

@app.post("/check_monitor")
def check_monitor(info: MonitorInfo):
    """客户端查询显示器是否已绑定工位"""
    conn, c = get_db_cursor()
    c.execute("SELECT seat_id FROM mappings WHERE monitor_sn=?", (info.serial_number,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {"status": "bound", "seat_id": result[0]}
    else:
        return {"status": "unbound", "seat_id": None}

@app.post("/bind_seat")
def bind_seat(req: BindRequest):
    """首次使用，绑定显示器到工位"""
    conn, c = get_db_cursor()
    try:
        c.execute("INSERT OR REPLACE INTO mappings VALUES (?, ?, ?, ?, ?)",
                  (req.monitor.serial_number, req.monitor.vendor_id, 
                   req.monitor.product_id, req.seat_id, datetime.datetime.now()))
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
    return {"status": "success", "message": f"Bound {req.monitor.serial_number} to {req.seat_id}"}

@app.post("/heartbeat")
def heartbeat(req: HeartbeatRequest):
    """客户端定期上报在线状态"""
    conn, c = get_db_cursor()
    c.execute("INSERT OR REPLACE INTO live_status VALUES (?, ?, ?, ?, ?)",
              (req.seat_id, req.user_name, req.host_name, datetime.datetime.now(), req.machine_serial))
    conn.commit()
    conn.close()
    return {"status": "ok"}

def get_all_mappings_data():
    conn, c = get_db_cursor()
    query = """
        SELECT m.monitor_sn, m.seat_id, m.created_at,
               l.user_name, l.host_name, l.last_heartbeat, l.machine_serial
        FROM mappings m
        LEFT JOIN live_status l ON m.seat_id = l.seat_id
        ORDER BY m.seat_id ASC
    """
    c.execute(query)
    rows = c.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        monitor_sn, seat_id, bound_at, user, host, last_seen, machine_sn = r
        is_active = False
        if last_seen:
            dt_last = datetime.datetime.fromisoformat(str(last_seen))
            if (datetime.datetime.now() - dt_last).total_seconds() < 300:
                is_active = True

        results.append({
            "seat_id": seat_id,
            "monitor_sn": monitor_sn,
            "bound_at": bound_at,
            "last_user": {
                "user_name": user,
                "host_name": host,
                "machine_serial": machine_sn,
                "last_seen": last_seen,
                "is_active": is_active
            } if user else None
        })
    return results

@app.get("/api/mappings")
def get_mappings_api():
    """查看完整详情 (JSON API)"""
    return get_all_mappings_data()

@app.get("/mappings", response_class=HTMLResponse)
def get_mappings_html(request: Request):
    """查看完整详情 (Web 页面)"""
    data = get_all_mappings_data()
    return templates.TemplateResponse("mappings.html", {"request": request, "mappings": data})

@app.get("/map/editor", response_class=HTMLResponse)
def get_map_editor(request: Request):
    """地图坐标编辑器"""
    return templates.TemplateResponse("editor.html", {"request": request})

@app.get("/map/view", response_class=HTMLResponse)
def get_map_view(request: Request):
    """地图可视化展示 (旧版 Image Map)"""
    return templates.TemplateResponse("map.html", {"request": request})

@app.get("/map/svg", response_class=HTMLResponse)
def get_map_svg(request: Request):
    """地图可视化展示 (新版 SVG)"""
    return templates.TemplateResponse("map_svg.html", {"request": request})

@app.get("/dashboard")
def get_dashboard():
    """简单的管理员查看接口"""
    conn, c = get_db_cursor()
    c.execute("SELECT * FROM live_status ORDER BY last_heartbeat DESC")
    rows = c.fetchall()
    conn.close()
    
    data = []
    for r in rows:
        # r 结构: seat_id, user, host, last_heartbeat, machine_serial
        seat_id = r[0]
        user = r[1]
        host = r[2]
        last_seen = r[3]
        # machine_serial = r[4] # 暂不展示

        dt_last = datetime.datetime.fromisoformat(str(last_seen)) if last_seen else datetime.datetime.min
        is_online = (datetime.datetime.now() - dt_last).total_seconds() < 300
        
        data.append({
            "seat_id": seat_id,
            "user": user,
            "host": host,
            "last_seen": last_seen,
            "status": "online" if is_online else "offline"
        })
    return data
