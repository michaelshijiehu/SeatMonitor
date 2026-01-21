import tkinter as tk

def prompt_for_seat_id(monitor_sn):
    """
    弹出一个自定义窗口，要求用户输入工位号。
    使用显式的主循环，比 simpledialog 更稳定。
    """
    root = tk.Tk()
    root.title("工位绑定")
    
    # 1. 设置窗口大小和位置 (居中)
    window_width = 320
    window_height = 180
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width // 2) - (window_width // 2)
    y = (screen_height // 2) - (window_height // 2)
    root.geometry(f'{window_width}x{window_height}+{int(x)}+{int(y)}')
    
    # 2. 强制置顶并获取焦点
    root.lift()
    root.attributes('-topmost', True)
    # 稍后取消置顶，避免一直遮挡其他窗口，但保持在前方
    root.after_idle(root.attributes, '-topmost', False)
    
    # 结果容器
    user_data = {"seat_id": None}
    
    def on_confirm(event=None):
        val = entry.get().strip()
        if val:
            user_data["seat_id"] = val
            root.withdraw()  # 1. 立即从屏幕上移除
            root.update()    # 2. 强制刷新显示状态
            root.destroy()   # 3. 销毁实例

    def on_cancel():
        root.withdraw()
        root.update()
        root.destroy()

    # 3. UI 布局
    tk.Label(root, text="检测到新显示器", font=("Arial", 14, "bold")).pack(pady=(15, 5))
    tk.Label(root, text=f"SN: {monitor_sn}", font=("Arial", 10), fg="gray").pack(pady=(0, 10))
    tk.Label(root, text="请输入当前工位号 (如 A-101):").pack()
    
    entry = tk.Entry(root, width=20)
    entry.pack(pady=5)
    entry.focus_set() # 强制聚焦输入框
    
    # 绑定回车键确认
    root.bind('<Return>', on_confirm)
    
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=15)
    
    tk.Button(btn_frame, text="确认绑定", command=on_confirm, bg="#007AFF", fg="black").pack(side=tk.LEFT, padx=10)
    tk.Button(btn_frame, text="忽略", command=on_cancel).pack(side=tk.LEFT, padx=10)
    
    # 处理点击窗口关闭按钮的情况
    root.protocol("WM_DELETE_WINDOW", on_cancel)
    
    root.mainloop()
    
    return user_data["seat_id"]
