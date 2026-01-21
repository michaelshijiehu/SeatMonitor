import sqlite3
import datetime
from prettytable import PrettyTable  # 如果没有安装，会降级使用简单打印

DB_FILE = "seat_monitor.db"

def view_data():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    print("\n=== 1. 静态绑定关系 (Mappings) ===")
    print("此表记录显示器 SN 与工位的对应关系")
    try:
        c.execute("SELECT * FROM mappings")
        rows = c.fetchall()
        if not rows:
            print("(暂无数据)")
        else:
            try:
                t = PrettyTable(['Monitor SN', 'Vendor', 'Product', 'Seat ID', 'Bound At'])
                for r in rows: t.add_row(r)
                print(t)
            except ImportError:
                # Fallback if prettytable not installed
                print(f"{ 'Monitor SN':<20} | { 'Seat ID':<10} | { 'Bound At'}")
                print("-" * 50)
                for r in rows:
                    print(f"{r[0]:<20} | {r[3]:<10} | {r[4]}")
    except Exception as e:
        print(f"Error reading mappings: {e}")

    print("\n=== 2. 实时在线状态 (Live Status) ===")
    print("此表记录当前的活跃用户心跳")
    try:
        c.execute("SELECT * FROM live_status")
        rows = c.fetchall()
        if not rows:
            print("(暂无活跃用户)")
        else:
            try:
                t = PrettyTable(['Seat ID', 'User', 'Host', 'Last Heartbeat'])
                for r in rows: t.add_row(r)
                print(t)
            except ImportError:
                for r in rows: print(r)
    except Exception as e:
        print(f"Error reading live_status: {e}")

    conn.close()

if __name__ == "__main__":
    # 尝试自动安装 prettytable 以便更好看，失败也没关系
    import subprocess, sys
    try:
        import prettytable
    except ImportError:
        print("Installing prettytable for better output...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "prettytable"])
        print("Done.\n")
    
    view_data()
