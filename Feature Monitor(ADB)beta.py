import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import os
import sys
import requests
import json  
import adbutils
import socket
import struct
from winotify import Notification
import cv2
import numpy as np

def resource_path(relative_path):
    """取得資源的絕對路徑，支援開發環境與 PyInstaller 打包後的環境"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

class ImageMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("特徵監測器 (ADB 版)")

        try:
            self.root.iconbitmap(resource_path("icon.ico"))
        except:
            pass

        # 增加視窗高度以容納新增的欄位
        self.root.geometry("650x680")
        self.root.resizable(False, False)
        
        self.is_monitoring = False
        self.monitor_thread = None
        self.image_rows = []
        
        self.setup_ui()
        self.load_preset()

        # 綁定視窗關閉事件，以確保程式關閉時能發送停止通知
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def setup_ui(self):
        # --- ADB 欄位 ---
        adb_frame = tk.Frame(self.root, pady=5)
        adb_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
        
        tk.Label(adb_frame, text="ADB 連線位置 (必填):", font=("Arial", 10, "bold"), width=25, anchor="e").pack(side=tk.LEFT)
        self.adb_var = tk.StringVar(value="127.0.0.1:5555")
        self.entry_adb = tk.Entry(adb_frame, textvariable=self.adb_var, width=40)
        self.entry_adb.pack(side=tk.LEFT, padx=5)

        # --- 偵測 Discord 欄位 ---
        discord_frame = tk.Frame(self.root, pady=5) 
        discord_frame.pack(fill=tk.X, padx=10)
        
        tk.Label(discord_frame, text="偵測 Discord Webhook:", font=("Arial", 10, "bold"), width=25, anchor="e").pack(side=tk.LEFT)
        self.discord_var = tk.StringVar()
        self.entry_discord = tk.Entry(discord_frame, textvariable=self.discord_var, width=40)
        self.entry_discord.pack(side=tk.LEFT, padx=5)

        # --- 狀態 Discord 欄位 (獨立) ---
        discord_status_frame = tk.Frame(self.root, pady=5) 
        discord_status_frame.pack(fill=tk.X, padx=10)
        
        tk.Label(discord_status_frame, text="狀態 Discord Webhook:", font=("Arial", 10, "bold"), width=25, anchor="e").pack(side=tk.LEFT)
        self.discord_status_var = tk.StringVar()
        self.entry_discord_status = tk.Entry(discord_status_frame, textvariable=self.discord_status_var, width=40)
        self.entry_discord_status.pack(side=tk.LEFT, padx=5)

        # --- Bark 欄位 ---
        bark_frame = tk.Frame(self.root, pady=5)
        bark_frame.pack(fill=tk.X, padx=10)
        
        tk.Label(bark_frame, text="Bark URL (選填):", font=("Arial", 10, "bold"), width=25, anchor="e").pack(side=tk.LEFT)
        self.bark_var = tk.StringVar()
        self.entry_bark = tk.Entry(bark_frame, textvariable=self.bark_var, width=40)
        self.entry_bark.pack(side=tk.LEFT, padx=5)

        # --- 包名 欄位 ---
        package_frame = tk.Frame(self.root, pady=5)
        package_frame.pack(fill=tk.X, padx=10)

        tk.Label(package_frame, text="遊戲包名 (防護用):", font=("Arial", 10, "bold"), width=25, anchor="e").pack(side=tk.LEFT)
        self.package_var = tk.StringVar(value="com.gamespark.topking.gp")
        self.entry_package = tk.Entry(package_frame, textvariable=self.package_var, width=40)
        self.entry_package.pack(side=tk.LEFT, padx=5)
        
        tk.Frame(self.root, height=2, bd=1, relief=tk.SUNKEN).pack(fill=tk.X, padx=10, pady=5)

        # --- 按鈕區塊 ---
        btn_add_frame = tk.Frame(self.root)
        btn_add_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.btn_add_row = tk.Button(btn_add_frame, text="➕ 添加新提示", command=self.add_image_row, bg="#dcedc1")
        self.btn_add_row.pack(side=tk.LEFT)

        # --- 新增：信心指數輸入 ---
        tk.Label(btn_add_frame, text="  信心指數:").pack(side=tk.LEFT)
        self.confidence_var = tk.StringVar(value="0.9")
        self.entry_confidence = tk.Entry(btn_add_frame, textvariable=self.confidence_var, width=5)
        self.entry_confidence.pack(side=tk.LEFT, padx=2)

        # --- 通知相關 Checkbox ---
        chk_frame = tk.Frame(btn_add_frame)
        chk_frame.pack(side=tk.LEFT, padx=10)

        self.bark_critical_var = tk.BooleanVar(value=False)
        self.chk_bark_critical = tk.Checkbutton(chk_frame, text="Bark 重要提示", variable=self.bark_critical_var)
        self.chk_bark_critical.pack(side=tk.TOP, anchor="w")

        self.status_notif_var = tk.BooleanVar(value=False)
        self.chk_status_notif = tk.Checkbutton(chk_frame, text="發送啟動/停止通知", variable=self.status_notif_var)
        self.chk_status_notif.pack(side=tk.TOP, anchor="w")

        self.show_similarity_var = tk.BooleanVar(value=False)
        self.chk_show_similarity = tk.Checkbutton(chk_frame, text="通知附帶相似度", variable=self.show_similarity_var)
        self.chk_show_similarity.pack(side=tk.TOP, anchor="w")
        
        self.btn_save_preset = tk.Button(btn_add_frame, text="💾 儲存設定", command=self.save_preset, bg="#ffd3b6")
        self.btn_save_preset.pack(side=tk.RIGHT)

        # --- 清單區塊 ---
        list_container = tk.Frame(self.root, bd=2, relief=tk.GROOVE)
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.canvas = tk.Canvas(list_container, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        
        self.scrollable_frame = tk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas.bind('<Enter>', self._bind_mouse_scroll)
        self.canvas.bind('<Leave>', self._unbind_mouse_scroll)

        tk.Frame(self.root, height=2, bd=1, relief=tk.SUNKEN).pack(fill=tk.X, padx=10, pady=5)

        # --- 啟動與狀態區塊 ---
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(pady=10)
        
        self.lbl_status = tk.Label(bottom_frame, text="狀態：已停止", font=("Arial", 12, "bold"))
        self.lbl_status.pack(pady=5)
        
        self.btn_start = tk.Button(bottom_frame, text="▶ 開始監測", command=self.start_monitoring, width=12, bg="#a8e6cf")
        self.btn_start.pack(side=tk.LEFT, padx=10, ipady=5)
        
        self.btn_stop = tk.Button(bottom_frame, text="⏹ 停止", command=self.stop_monitoring, state=tk.DISABLED, width=12, bg="#ffaaa5")
        self.btn_stop.pack(side=tk.LEFT, padx=10, ipady=5)

    def save_preset(self):
        data = {
            "adb_address": self.adb_var.get(),
            "discord_webhook": self.discord_var.get(),
            "discord_status_webhook": self.discord_status_var.get(),
            "bark_url": self.bark_var.get(),
            "package_name": self.package_var.get(),
            "bark_critical": self.bark_critical_var.get(),
            "status_notif": self.status_notif_var.get(),
            "show_similarity": self.show_similarity_var.get(),
            "confidence_level": self.confidence_var.get(),
            "rows": []
        }
        
        for row in self.image_rows:
            if row['path']: 
                data["rows"].append({
                    "path": row['path'],
                    "message": row['msg_var'].get()
                })
                
        try:
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("成功", "設定已成功儲存！\n下次開啟程式時將自動載入。")
        except Exception as e:
            messagebox.showerror("錯誤", f"儲存設定失敗：\n{str(e)}")

    def load_preset(self):
        if not os.path.exists("config.json"):
            self.add_image_row()
            return
            
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.adb_var.set(data.get("adb_address", "127.0.0.1:16384"))
            self.discord_var.set(data.get("discord_webhook", ""))
            self.discord_status_var.set(data.get("discord_status_webhook", ""))
            self.bark_var.set(data.get("bark_url", ""))
            self.package_var.set(data.get("package_name", "com.gamespark.topking.gp"))
            self.bark_critical_var.set(data.get("bark_critical", False))
            self.status_notif_var.set(data.get("status_notif", False))
            self.show_similarity_var.set(data.get("show_similarity", False))
            self.confidence_var.set(data.get("confidence_level", "0.9"))
            
            saved_rows = data.get("rows", [])
            if saved_rows:
                for row in list(self.image_rows):
                    self.delete_row(row)
                    
                for row_data in saved_rows:
                    self.add_image_row()
                    current_row = self.image_rows[-1]
                    
                    current_row['path'] = row_data["path"]
                    current_row['msg_var'].set(row_data["message"])
                    
                    filename = os.path.basename(row_data["path"])
                    if len(filename) > 10: 
                        filename = filename[:8] + "..."
                    current_row['path_var'].set(filename)
            else:
                self.add_image_row()
                
        except Exception as e:
            print(f"讀取設定失敗: {e}")
            if not self.image_rows:
                self.add_image_row()

    def _bind_mouse_scroll(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
    def _unbind_mouse_scroll(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        
    def _on_mousewheel(self, event):
        content_height = self.scrollable_frame.winfo_height()
        canvas_height = self.canvas.winfo_height()
        if content_height > canvas_height:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def add_image_row(self):
        row_frame = tk.Frame(self.scrollable_frame, pady=5)
        row_frame.pack(fill=tk.X, padx=5)
        
        path_var = tk.StringVar(value="尚未選擇")
        msg_var = tk.StringVar(value="偵測到目標出現！")
        
        row_data = {
            'frame': row_frame,
            'path': '',
            'path_var': path_var,
            'msg_var': msg_var,
            'btn_select': None,
            'entry_msg': None,
            'btn_delete': None
        }
        
        btn_select = tk.Button(row_frame, text="📁 圖片", command=lambda: self.select_image(row_data), width=8)
        btn_select.pack(side=tk.LEFT, padx=5)
        row_data['btn_select'] = btn_select
        
        lbl_path = tk.Label(row_frame, textvariable=path_var, width=12, anchor="w", fg="gray")
        lbl_path.pack(side=tk.LEFT, padx=5)
        
        tk.Label(row_frame, text="提示:").pack(side=tk.LEFT)
        
        entry_msg = tk.Entry(row_frame, textvariable=msg_var, width=22)
        entry_msg.pack(side=tk.LEFT, padx=5)
        row_data['entry_msg'] = entry_msg
        
        btn_delete = tk.Button(row_frame, text="❌", fg="red", command=lambda: self.delete_row(row_data))
        btn_delete.pack(side=tk.RIGHT, padx=5)
        row_data['btn_delete'] = btn_delete
        
        self.image_rows.append(row_data)

    def delete_row(self, row_data):
        row_data['frame'].destroy()         
        self.image_rows.remove(row_data)    

    def select_image(self, row_data):
        file_path = filedialog.askopenfilename(
            title="選擇要監測的圖片",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")]
        )
        if file_path:
            # 轉換為相對路徑（如果圖片與程式在同一個磁碟機且路徑允許）
            try:
                rel_path = os.path.relpath(file_path, os.getcwd())
                # 若相對路徑沒有跳出太多層，則優先使用相對路徑
                if not rel_path.startswith("..\\.."):
                    file_path = rel_path
            except ValueError:
                pass # 若位在不同磁碟機等無法轉換的情況，則保持原絕對路徑
            
            row_data['path'] = file_path
            filename = os.path.basename(file_path)
            if len(filename) > 10: 
                filename = filename[:8] + "..."
            row_data['path_var'].set(filename)

    def send_status_notification(self, is_start=True):
        """發送開始/停止的狀態通知"""
        if not self.status_notif_var.get():
            return
            
        status_text = "🟢 系統通知：特徵監測器已開始運行" if is_start else "🔴 系統通知：特徵監測器已停止運行"
        discord_url = self.discord_status_var.get().strip()
        bark_url = self.bark_var.get().strip()
        is_bark_critical = self.bark_critical_var.get()
        
        # 1. 獨立的 Discord 狀態通知
        if discord_url:
            try:
                requests.post(discord_url, json={"content": status_text}, timeout=5)
            except Exception as e:
                print(f"發送 Discord 狀態通知失敗: {e}")
                
        # 2. 共用 Bark 進行狀態通知
        if bark_url:
            try:
                clean_bark_url = bark_url.rstrip('/')
                payload = {
                    "title": "運作狀態更新",
                    "body": status_text,
                    "group": "特徵監測器",
                    "sound": "rooster-sound"
                }
                if is_bark_critical:
                    payload["level"] = "critical"
                    
                requests.post(clean_bark_url, json=payload, timeout=5)
            except Exception as e:
                print(f"發送 Bark 狀態通知失敗: {e}")

    def on_closing(self):
        """處理直接關閉視窗的事件"""
        if self.is_monitoring:
            self.send_status_notification(is_start=False)
        self.root.destroy()

    def _get_raw_screenshot_socket(self, serial):
        """透過本機 Socket 直接與 ADB Server 溝通，取得無壓縮二進位截圖流"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 設定逾時避免卡死
        s.settimeout(5.0) 
        s.connect(('127.0.0.1', 5037))
        
        # 1. 綁定指定的 ADB 設備
        transport_cmd = f"host:transport:{serial}"
        s.sendall(f"{len(transport_cmd):04x}{transport_cmd}".encode('utf-8'))
        if s.recv(4) != b"OKAY":
            s.close()
            raise ConnectionError(f"無法綁定設備: {serial}")

        # 2. 發送截圖指令 (使用 exec 避免 shell 模式帶來的 \r\n 換行符號污染)
        cmd = "exec:screencap"
        s.sendall(f"{len(cmd):04x}{cmd}".encode('utf-8'))
        if s.recv(4) != b"OKAY":
            s.close()
            raise ConnectionError("截圖指令執行失敗 (如果你的模擬器是 Android 7 以下舊版，可能不支援 exec)")

        # 3. 讀取原始二進位資料
        data = bytearray()
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            data.extend(chunk)
        s.close()

        # 4. 解析 Raw RGBA 標頭 (通常為 12 bytes：width, height, pixel_format)
        if len(data) < 12:
            raise ValueError("截圖資料長度異常")
            
        width, height, pixel_format = struct.unpack_from('<III', data, 0)
        
        # 5. 計算實際像素資料的起始偏移量
        pixel_data_size = width * height * 4
        header_size = len(data) - pixel_data_size
        
        if header_size < 12 or len(data) != header_size + pixel_data_size:
            raise ValueError("截圖尺寸解析與檔案大小不符")

        # 6. 直接映射為 NumPy Array (極速零拷貝)
        pixels = np.frombuffer(data, dtype=np.uint8, offset=header_size).reshape((height, width, 4))
        
        # 7. 轉為 OpenCV 的 BGR 格式 (捨棄 Alpha 通道)
        return cv2.cvtColor(pixels, cv2.COLOR_RGBA2BGR)

    def start_monitoring(self):
        has_valid_image = any(row['path'] != '' for row in self.image_rows)
        if not has_valid_image:
            messagebox.showwarning("警告", "請至少選擇一張目標圖片！")
            return

        try:
            conf_val = float(self.confidence_var.get().strip())
            if not (0.1 <= conf_val <= 1.0):
                raise ValueError
        except ValueError:
            messagebox.showwarning("警告", "信心指數請輸入 0.1 到 1.0 之間的有效數字！")
            return
            
        adb_addr = self.adb_var.get().strip()
        if not adb_addr:
            messagebox.showwarning("警告", "請輸入 ADB 連線位置！")
            return
            
        try:
            # 嘗試連線至模擬器
            adbutils.adb.connect(adb_addr)
        except Exception as e:
            messagebox.showerror("錯誤", f"無法連線至指定的 ADB 裝置！\n請確認模擬器是否開啟，並檢查位址。\n詳細錯誤：{str(e)}")
            return

        for row in self.image_rows:
            if row['path']:
                try:
                    # 使用 np.fromfile 支援中文路徑讀取
                    img_data = np.fromfile(row['path'], dtype=np.uint8)
                    template = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                    if template is None:
                        raise ValueError("無效的影像格式")
                    row['template'] = template  # 存入記憶體
                except Exception as e:
                    messagebox.showerror("錯誤", f"無法讀取圖片：{row['path']}\n錯誤：{str(e)}")
                    return
            
        self.is_monitoring = True
        self.update_ui_state(running=True)
        self.send_status_notification(is_start=True)
        
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.is_monitoring = False
        self.send_status_notification(is_start=False)
        self.update_ui_state(running=False)

    def update_ui_state(self, running):
        state = tk.DISABLED if running else tk.NORMAL
        
        self.entry_adb.config(state=state)
        self.entry_discord.config(state=state)
        self.entry_discord_status.config(state=state)
        self.entry_bark.config(state=state)
        self.entry_package.config(state=state)
        self.chk_bark_critical.config(state=state)
        self.chk_status_notif.config(state=state)
        self.chk_show_similarity.config(state=state)
        self.entry_confidence.config(state=state)
        self.btn_add_row.config(state=state)
        self.btn_save_preset.config(state=state) 
        
        for row in self.image_rows:
            row['btn_select'].config(state=state)
            row['entry_msg'].config(state=state)
            row['btn_delete'].config(state=state)
            
        if running:
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            self.lbl_status.config(text="狀態：監測中", fg="green")
        else:
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            self.lbl_status.config(text="狀態：已停止", fg="black")

    def monitor_loop(self):
        try:
            confidence_level = float(self.confidence_var.get().strip())
        except:
            confidence_level = 0.9 # 防呆預設值
        interval = 0.5            
        webhook_url = self.discord_var.get().strip()
        discord_status_url = self.discord_status_var.get().strip()
        bark_url = self.bark_var.get().strip() 
        is_bark_critical = self.bark_critical_var.get()
        adb_addr = self.adb_var.get().strip()

        # 防卡當變數初始化
        package_name = self.package_var.get().strip() or "com.gamespark.topking.gp"
        last_screenshot = None
        static_count = 0
        max_static_limit = 120  # 以 0.5 秒間隔計算，120 次約為 1 分鐘毫無任何像素變化

        # 新增：ADB 連線失敗計數器
        reconnect_fails = 0
        max_reconnect_fails = 3  # 連續失敗 3 次即判定斷線
        
        # 新增：PID 檢查冷卻與通知冷卻機制
        last_pid_check_time = 0
        self.last_alert_times = {}

        while self.is_monitoring:
            try:
                # --- ADB 截圖與斷線偵測 ---
                try:
                    # 純 Socket 方法取得 OpenCV BGR 畫面
                    screen_cv = self._get_raw_screenshot_socket(adb_addr)
                    reconnect_fails = 0  # 成功截圖，重置計數器
                except Exception as e:
                    print(f"Socket 截圖失敗，嘗試透過 adbutils 重啟連線至 {adb_addr}... 錯誤: {e}")
                    try:
                        adbutils.adb.connect(adb_addr)
                    except Exception as reconnect_e:
                        print(f"重連執行失敗: {reconnect_e}")
                        
                    reconnect_fails += 1
                    
                    # 如果連續失敗達到上限，發送推播並停止監測
                    if reconnect_fails >= max_reconnect_fails:
                        err_msg = f"❌ 系統錯誤：ADB 連線中斷或模擬器已關閉！({adb_addr})"
                        
                        if discord_status_url:
                            try: requests.post(discord_status_url, json={"content": err_msg}, timeout=5)
                            except: pass
                            
                        if bark_url:
                            try:
                                payload = {
                                    "title": "🚨 ADB 斷線警告",
                                    "body": err_msg,
                                    "group": "特徵監測器",
                                    "sound": "telegraph"
                                }
                                if is_bark_critical: payload["level"] = "critical"
                                requests.post(bark_url.rstrip('/'), json=payload, timeout=5)
                            except: pass
                            
                        # 停止程式運行狀態
                        self.is_monitoring = False
                        self.root.after(0, self.update_ui_state, False)
                        break
                        
                    time.sleep(interval + 2)
                    continue
                
                # --- 第一重防護：PID 進程崩潰偵測 ---
                current_time = time.time()
                # 每 10 秒才查一次 PID，降低對 ADB 的負載
                if current_time - last_pid_check_time > 10:
                    try:
                        # 向 Android 系統查詢該遊戲的 PID
                        device = adbutils.adb.device(adb_addr)
                        pid = device.shell(f"pidof {package_name}").strip()
                        last_pid_check_time = current_time
                        
                        if not pid:
                            freeze_msg = "⚠️ 系統警告：遊戲進程已消失，遊戲可能已經崩潰閃退或被手動關閉！"
                            
                            if discord_status_url: # 將警告發送至狀態 Webhook
                                try: requests.post(discord_status_url, json={"content": freeze_msg}, timeout=5)
                                except: pass
                                
                            if bark_url:
                                try:
                                    payload = {
                                        "title": "🚨 遊戲崩潰警告",
                                        "body": freeze_msg,
                                        "group": "特徵監測器",
                                        "sound": "telegraph"
                                    }
                                    if is_bark_critical: payload["level"] = "critical"
                                    requests.post(bark_url.rstrip('/'), json=payload, timeout=5)
                                except: pass
                                
                            time.sleep(10) # 暫停 10 秒避免通知洗版
                            continue # 跳過下方的圖片比對，直接進入下一個迴圈
                            
                    except Exception as pid_err:
                        print(f"查詢 PID 失敗: {pid_err}")
                
                # --- 第二重防護：連續靜止畫面偵測 (假死) ---
                if last_screenshot is not None:
                    # 改用誤差平均值計算，允許極微小的浮動(平均誤差小於1視同靜止)
                    diff = cv2.absdiff(screen_cv, last_screenshot)
                    if np.mean(diff) < 1.0:
                        static_count += 1
                    else:
                        static_count = 0  # 畫面有動靜，重置計數器

                # 拷貝當前畫面給下一輪比對用
                last_screenshot = screen_cv.copy()
				
                # 觸發卡當警報
                if static_count >= max_static_limit:
                    freeze_msg = "⚠️ 警告：偵測到模擬器畫面已連續 1 分鐘完全靜止，遊戲可能已崩潰或卡死！"
                    
                    if discord_status_url:
                        try: requests.post(discord_status_url, json={"content": freeze_msg}, timeout=5)
                        except: pass
                        
                    if bark_url:
                        try:
                            payload = {"title": "畫面卡死警告", "body": freeze_msg, "group": "特徵監測器", "sound": "telegraph"}
                            if is_bark_critical: payload["level"] = "critical"
                            requests.post(bark_url.rstrip('/'), json=payload, timeout=5)
                        except: pass
                    
                    static_count = 0 # 重置計數器避免瘋狂洗版
                    time.sleep(10)
                    continue # 跳過下方的特徵比對，直接進入下一回合               

                # --- 圖片特徵比對 ---
                show_sim = self.show_similarity_var.get()
                found_messages = []

                for row in self.image_rows:
                    if not row.get('path') or 'template' not in row: 
                        continue
                        
                    try:
                        template = row['template']
                        # 執行 OpenCV 模板匹配
                        result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(result)
                        
                        if max_val >= confidence_level:
                            custom_message = row['msg_var'].get().strip() or "偵測到目標圖片！"
                            # 檢查該提示訊息是否還在 20 秒冷卻期內
                            if current_time - self.last_alert_times.get(custom_message, 0) > 20:
                                if show_sim:
                                    # 附加相似度資訊 (例如：95.2%)
                                    custom_message += f" (相似度: {max_val*100:.1f}%)"
                                found_messages.append(custom_message)
                                self.last_alert_times[custom_message] = current_time
                    except Exception as match_err:
                        print(f"OpenCV 比對錯誤: {match_err}")
                        continue
                
                if found_messages:
                    combined_message = "\n".join(found_messages)
                    
                    toast = Notification(
                        app_id="Feature Monitor",
                        title="影像偵測通知",
                        msg=combined_message,
                        duration="short"
                    )
                    toast.show()
                    
                    if webhook_url:
                        try: requests.post(webhook_url, json={"content": f"🚨 系統通知：\n{combined_message}"}, timeout=5)
                        except Exception as req_e: print(f"Discord 發送失敗: {req_e}")
                            
                    if bark_url:
                        try:
                            clean_bark_url = bark_url.rstrip('/')
                            payload = {
                                "title": "🚨 影像偵測通知",
                                "body": combined_message,
                                "group": "特徵監測器",
                                "sound": "rooster-sound"
                            }
                            if is_bark_critical: payload["level"] = "critical"
                            requests.post(clean_bark_url, json=payload, timeout=5)
                        except Exception as req_e: print(f"Bark 發送失敗: {req_e}")
                    
                time.sleep(interval)
                    
            except Exception as e:
                # --- 最外層未預期錯誤，同步發送推播 ---
                self.is_monitoring = False
                err_msg = f"❌ 嚴重錯誤：程式發生未預期崩潰，已停止監測！\n錯誤訊息：{str(e)}"
                
                if discord_status_url:
                    try: requests.post(discord_status_url, json={"content": err_msg}, timeout=5)
                    except: pass
                    
                if bark_url:
                    try:
                        payload = {
                            "title": "🚨 系統崩潰警告",
                            "body": err_msg,
                            "group": "特徵監測器",
                            "sound": "telegraph"
                        }
                        if is_bark_critical: payload["level"] = "critical"
                        requests.post(bark_url.rstrip('/'), json=payload, timeout=5)
                    except: pass
                
                self.root.after(0, self.update_ui_state, False)
                self.root.after(0, lambda: messagebox.showerror("錯誤", err_msg))
                break

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageMonitorApp(root)
    root.attributes('-topmost', False) 
    root.mainloop()