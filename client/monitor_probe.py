import platform
import subprocess
import hashlib
import sys

def get_edid_serial(edid_hex):
    """通用工具：尝试从 EDID Hex 中解析 ASCII 序列号"""
    if not edid_hex: return None
    try:
        edid_bytes = bytes.fromhex(edid_hex)
    except ValueError: return None
    
    # 查找 Descriptor Blocks (Tag FF)
    descriptor_offsets = [54, 72, 90, 108]
    for offset in descriptor_offsets:
        if offset + 18 > len(edid_bytes): break
        block = edid_bytes[offset:offset+18]
        if block[0:3] == b'\x00\x00\x00' and block[3] == 0xFF:
            return block[5:].decode('ascii', errors='ignore').strip().replace('\n', '')
    return None

def get_monitors():
    """跨平台获取外接显示器信息"""
    system = platform.system()
    monitors = []

    if system == "Darwin":
        monitors = _get_monitors_mac()
    elif system == "Windows":
        monitors = _get_monitors_win()
    
    # 统一过滤逻辑：如果完全没有序列号，生成一个基于 Hash 的 ID
    for m in monitors:
        if m['serial_number'] in ["UNKNOWN", "0", ""]:
            # 使用 Vendor+Product+Hash 作为唯一标识
            raw = f"{m['vendor_id']}-{m['product_id']}-{m.get('edid_hash', '')}"
            m['serial_number'] = "GEN-" + hashlib.md5(raw.encode()).hexdigest()[:12]
            
    return monitors

def _get_monitors_mac():
    import plistlib
    
    # 递归查找函数
    def find_keys(node, key, results):
        if isinstance(node, dict):
            if key in node: results.append(node)
            for k, v in node.items(): find_keys(v, key, results)
        elif isinstance(node, list):
            for item in node: find_keys(item, key, results)

    cmd = ["ioreg", "-l", "-w0", "-r", "-c", "IODisplayConnect", "-a"]
    try:
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0: return []
        root = plistlib.loads(result.stdout)
        
        display_nodes = []
        find_keys(root, "IODisplayEDID", display_nodes)
        
        monitors = []
        for node in display_nodes:
            vendor = node.get("DisplayVendorID", 0)
            
            # 过滤 Apple 内置屏幕 (通常是 1552 / 0x610)
            if vendor == 1552: 
                continue

            product = node.get("DisplayProductID", 0)
            sys_serial = node.get("DisplaySerialNumber", 0)
            
            edid_bytes = node.get("IODisplayEDID", b"")
            edid_hex = edid_bytes.hex() if edid_bytes else ""
            edid_parsed_sn = get_edid_serial(edid_hex)
            
            final_sn = "UNKNOWN"
            if edid_parsed_sn: final_sn = edid_parsed_sn
            elif sys_serial: final_sn = str(sys_serial)
            
            monitors.append({
                "vendor_id": str(vendor),
                "product_id": str(product),
                "serial_number": final_sn,
                "edid_hash": hashlib.md5(edid_bytes).hexdigest() if edid_bytes else ""
            })
        return monitors
        
    except Exception as e:
        print(f"Mac Probe Error: {e}")
        return []

def _get_monitors_win():
    try:
        import wmi
        c = wmi.WMI(namespace="wmi")
        monitors = []
        for item in c.WmiMonitorID():
            def decode_arr(arr):
                if not arr: return ""
                return "".join([chr(x) for x in arr if x != 0]).strip()

            vendor = decode_arr(item.ManufacturerName)
            product = decode_arr(item.ProductCodeID)
            serial = decode_arr(item.SerialNumberID)
            
            monitors.append({
                "vendor_id": vendor,
                "product_id": product,
                "serial_number": serial,
                "edid_hash": "WIN_NO_HASH" # WMI 不容易直接拿原始 EDID，这里简化
            })
        return monitors
    except ImportError:
        print("Missing 'wmi' library. Run: pip install wmi pywin32")
        return []
    except Exception as e:
        print(f"Win Probe Error: {e}")
        return []
