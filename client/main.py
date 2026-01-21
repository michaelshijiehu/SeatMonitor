import time
import requests
import platform
import socket
import getpass
import sys
import subprocess
from monitor_probe import get_monitors
from ui import prompt_for_seat_id

import os
# ... imports ...

# --- 配置区 ---
# 生产环境部署时，请将下方 localhost 改为服务器的局域网 IP (例如 http://192.168.1.100:8000)
# 或者在运行客户端前设置环境变量: export SEAT_MONITOR_URL="http://192.168.1.100:8000"
SERVER_URL = os.getenv("SEAT_MONITOR_URL", "http://localhost:8000")

def get_machine_info():
    info = {
        "user_name": getpass.getuser(),
        "host_name": socket.gethostname(),
        "machine_serial": "UNKNOWN"
    }
    system = platform.system()
    
    if system == "Darwin":
        try:
            cmd = "ioreg -l | grep IOPlatformSerialNumber"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if '"' in res.stdout:
                info["machine_serial"] = res.stdout.split('"')[-2]
        except: pass
        
    elif system == "Windows":
        try:
            # 使用 wmic 获取 Windows BIOS 序列号
            cmd = "wmic bios get serialnumber"
            res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            # 输出通常是: SerialNumber \n XXXXXXX \n
            lines = [line.strip() for line in res.stdout.split('\n') if line.strip()]
            if len(lines) > 1:
                info["machine_serial"] = lines[1]
        except: pass
        
    return info

def check_and_report():
    print(f"[{time.strftime('%X')}] Scanning monitors...")
    monitors = get_monitors()
    
    if not monitors:
        print("No external monitors detected.")
        return

    # 只处理第一个发现的外接显示器 (简化逻辑，支持多显示器需循环)
    monitor = monitors[0]
    print(f"Found monitor: {monitor['serial_number']}")

    # 1. Check if bound
    try:
        resp = requests.post(f"{SERVER_URL}/check_monitor", json=monitor)
        data = resp.json()
    except requests.exceptions.ConnectionError:
        print("Server unreachable.")
        return

    seat_id = data.get("seat_id")

    # 2. Bind if unbound
    if data["status"] == "unbound":
        print("Monitor not bound. Prompting user...")
        user_input_seat = prompt_for_seat_id(monitor['serial_number'])
        
        if user_input_seat:
            bind_payload = {
                "monitor": monitor,
                "seat_id": user_input_seat
            }
            requests.post(f"{SERVER_URL}/bind_seat", json=bind_payload)
            seat_id = user_input_seat
            print(f"Bound to {seat_id}")
        else:
            print("User cancelled binding.")
            return

    # 3. Heartbeat
    if seat_id:
        machine = get_machine_info()
        heartbeat_payload = {
            "seat_id": seat_id,
            "monitor_sn": monitor['serial_number'],
            "user_name": machine['user_name'],
            "host_name": machine['host_name'],
            "machine_serial": machine['machine_serial']
        }
        requests.post(f"{SERVER_URL}/heartbeat", json=heartbeat_payload)
        print(f"Heartbeat sent for Seat {seat_id}")

def main():
    print("--- SeatMonitor Client Started ---")
    while True:
        try:
            check_and_report()
        except Exception as e:
            print(f"Error in loop: {e}")
        
        # 每 5 分钟 (300秒) 检查一次
        # 调试模式改为 10 秒
        time.sleep(10)

if __name__ == "__main__":
    main()
