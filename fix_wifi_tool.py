#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Công cụ Gỡ Lỗi Wi-Fi Cho Nhiều Thiết Bị (Android Phone Farm)
Dựa trên script wifi_loi.bat
Hỗ trợ tự động kết nối Wi-Fi mới qua app ADBJoinWiFi
"""

import os
import sys
import time
import re
import json
import shutil
import zipfile
import webbrowser
import urllib.request
import urllib.error
import subprocess
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
except Exception as e:
    print(f"[LỖI] Không thể khởi động Tkinter: {e}")
    traceback.print_exc()
    input("Nhấn Enter để thoát...")
    sys.exit(1)


APP_VERSION = "v1.2.0"
DEFAULT_GITHUB_REPO = "duckiend3v/Fix_Wifi"


def get_app_dir():
    """Trả về thư mục gốc chứa ứng dụng (chuẩn xác cho cả file .py và .exe PyInstaller)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def load_github_repo():
    """Đọc tên repo GitHub từ file cấu hình updater_config.json nếu có"""
    cfg_file = os.path.join(get_app_dir(), "updater_config.json")
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                repo = data.get("github_repo", "").strip()
                if repo:
                    return repo
        except Exception:
            pass
    return DEFAULT_GITHUB_REPO


def save_github_repo(repo):
    """Lưu tên repo GitHub vào updater_config.json"""
    cfg_file = os.path.join(get_app_dir(), "updater_config.json")
    try:
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump({"github_repo": repo.strip()}, f, indent=2)
    except Exception:
        pass


def is_newer_version(latest_tag, current_ver):
    """So sánh 2 version xem latest_tag có mới hơn current_ver không (ví dụ: v1.2.0 > v1.1.0)"""
    try:
        nums_latest = [int(x) for x in re.findall(r"\d+", latest_tag)]
        nums_current = [int(x) for x in re.findall(r"\d+", current_ver)]
        max_len = max(len(nums_latest), len(nums_current))
        nums_latest.extend([0] * (max_len - len(nums_latest)))
        nums_current.extend([0] * (max_len - len(nums_current)))
        return nums_latest > nums_current
    except Exception:
        return latest_tag != current_ver


def find_adb_executable():
    """Tự động tìm đường dẫn file adb.exe trên máy"""
    candidates = [
        "adb",
        r"C:\TLCHelper\sdk\platform-tools\adb.exe",
        r"C:\platform-tools\adb.exe",
        r"D:\platform-tools\adb.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Android\platform-tools\adb.exe"),
    ]
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    for c in candidates:
        try:
            res = subprocess.run([c, "version"], capture_output=True, text=True, startupinfo=startupinfo)
            if res.returncode == 0:
                return c
        except Exception:
            continue
    return "adb"


class WifiFixerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Fix Wifi")
        self.root.geometry("880x740")
        self.root.minsize(800, 640)
        
        # Đường dẫn adb
        self.adb_bin = find_adb_executable()

        # Biến trạng thái
        self.is_running = False
        self.stop_requested = False
        self.executor = None
        
        # Cấu hình giao diện
        self._setup_styles()
        self._build_ui()
        self._check_adb_status()
        
        # Tự động kiểm tra cập nhật ngầm sau 2 giây
        self.root.after(2000, lambda: self.check_github_update(silent=True))
        
    def _setup_styles(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
            
        self.style.configure("TLabel", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"), foreground="#0d47a1")
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 9), foreground="#555555")
        self.style.configure("TCheckbutton", font=("Segoe UI", 9))
        self.style.configure("TLabelframe", font=("Segoe UI", 10, "bold"))
        self.style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"), foreground="#1565c0")

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Header & Thanh nút Cập nhật GitHub
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 8))

        header_left = ttk.Frame(header_frame)
        header_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        title_lbl = ttk.Label(header_left, text=f"FIX WIFI  [{APP_VERSION}]", style="Header.TLabel")
        title_lbl.pack(anchor=tk.W)
        sub_lbl = ttk.Label(header_left, text="Gỡ lỗi kẹt Proxy, clear app College Proxy, không bắt được Wi-Fi, tự động kết nối lại Wi-Fi mới qua app ADBJoinWiFi.", style="SubHeader.TLabel")
        sub_lbl.pack(anchor=tk.W)

        # Cụm nút Cập nhật GitHub góc phải
        header_right = ttk.Frame(header_frame)
        header_right.pack(side=tk.RIGHT, anchor=tk.E, padx=(10, 0))

        self.btn_update = tk.Button(
            header_right, 
            text="🔄 Kiểm tra Cập nhật", 
            font=("Segoe UI", 9, "bold"), 
            bg="#2e7d32", 
            fg="white", 
            activebackground="#1b5e20", 
            activeforeground="white",
            relief=tk.RAISED, 
            cursor="hand2", 
            padx=10, 
            pady=4,
            command=lambda: self.check_github_update(silent=False)
        )
        self.btn_update.pack(side=tk.LEFT, padx=(0, 5))

        btn_repo_cfg = ttk.Button(header_right, text="⚙ Repo", width=7, command=self.configure_repo)
        btn_repo_cfg.pack(side=tk.LEFT)

        # 2. Khung nhập danh sách UID
        uid_frame = ttk.LabelFrame(main_frame, text=" Danh sách UID / Serial thiết bị ", padding=8)
        uid_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 8))

        btn_row = ttk.Frame(uid_frame)
        btn_row.pack(fill=tk.X, pady=(0, 5))

        self.btn_scan = ttk.Button(btn_row, text="Quét thiết bị ADB đang cắm", command=self.scan_adb_devices)
        self.btn_scan.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_paste = ttk.Button(btn_row, text="Dán từ Clipboard", command=self.paste_from_clipboard)
        self.btn_paste.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_clear = ttk.Button(btn_row, text="Xóa ô nhập", command=self.clear_uids)
        self.btn_clear.pack(side=tk.LEFT, padx=(0, 6))

        self.lbl_uid_count = ttk.Label(btn_row, text="Tổng: 0 UID", font=("Segoe UI", 9, "italic"), foreground="#2e7d32")
        self.lbl_uid_count.pack(side=tk.RIGHT, padx=6)

        # Ô Text nhập UIDs
        self.txt_uids = scrolledtext.ScrolledText(uid_frame, height=4, font=("Consolas", 10), wrap=tk.WORD)
        self.txt_uids.pack(fill=tk.BOTH, expand=True)
        self.txt_uids.bind("<KeyRelease>", self._update_uid_count)

        # 3. Tùy chọn gỡ lỗi & Kết nối Wi-Fi mới
        opt_frame = ttk.LabelFrame(main_frame, text=" Các bước xử lý gỡ lỗi & Kết nối Wi-Fi ", padding=10)
        opt_frame.pack(fill=tk.X, pady=(0, 8))

        # Checkboxes 1 - 6
        self.var_clear_proxy = tk.BooleanVar(value=True)
        self.var_clear_college = tk.BooleanVar(value=True)
        self.var_forget_wifi = tk.BooleanVar(value=True)
        self.var_stop_app = tk.BooleanVar(value=True)
        self.var_disable_wifi = tk.BooleanVar(value=True)
        self.var_enable_wifi = tk.BooleanVar(value=True)

        cb1 = ttk.Checkbutton(opt_frame, text="1. Xóa sạch HTTP Proxy (settings put/delete http_proxy, host, port)", variable=self.var_clear_proxy)
        cb1.grid(row=0, column=0, sticky=tk.W, pady=2, padx=5)

        cb2 = ttk.Checkbutton(opt_frame, text="2. Xóa dữ liệu app College Proxy (pm clear & force-stop package)", variable=self.var_clear_college)
        cb2.grid(row=0, column=1, sticky=tk.W, pady=2, padx=15)

        cb3 = ttk.Checkbutton(opt_frame, text="3. Quên toàn bộ cấu hình Wi-Fi đã lưu (forget-network 0..15)", variable=self.var_forget_wifi)
        cb3.grid(row=1, column=0, sticky=tk.W, pady=2, padx=5)

        cb4 = ttk.Checkbutton(opt_frame, text="4. Tắt và ngắt kết nối app ADBJoinWiFi cũ", variable=self.var_stop_app)
        cb4.grid(row=1, column=1, sticky=tk.W, pady=2, padx=15)

        cb5 = ttk.Checkbutton(opt_frame, text="5. Tắt Wi-Fi (svc wifi disable)", variable=self.var_disable_wifi)
        cb5.grid(row=2, column=0, sticky=tk.W, pady=2, padx=5)

        cb6 = ttk.Checkbutton(opt_frame, text="6. Tự động BẬT LẠI Wi-Fi sau khi xử lý (svc wifi enable)", variable=self.var_enable_wifi, command=self._on_enable_wifi_toggle)
        cb6.grid(row=2, column=1, sticky=tk.W, pady=2, padx=15)

        # Bước 7: Kết nối Wi-Fi mới qua ADBJoinWiFi
        self.var_connect_wifi = tk.BooleanVar(value=True)
        wifi_conn_frame = ttk.Frame(opt_frame)
        wifi_conn_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(4, 4), padx=5)

        self.cb7 = ttk.Checkbutton(
            wifi_conn_frame, 
            text="7. Kết nối lại Wi-Fi mới qua app ADBJoinWiFi (định dạng user|pass):", 
            variable=self.var_connect_wifi,
            command=self._on_connect_wifi_toggle
        )
        self.cb7.pack(side=tk.LEFT, padx=(0, 6))

        self.ent_wifi = ttk.Entry(wifi_conn_frame, width=32, font=("Consolas", 10))
        self.ent_wifi.insert(0, "Aruba3.2|66668888")
        self.ent_wifi.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(wifi_conn_frame, text="(Tên Wi-Fi|Mật khẩu)", font=("Segoe UI", 9, "italic"), foreground="#666666").pack(side=tk.LEFT)

        # Cấu hình đa luồng
        thread_frame = ttk.Frame(opt_frame)
        thread_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=(6, 0), padx=5)
        
        ttk.Label(thread_frame, text="Số luồng chạy song song (Threads):").pack(side=tk.LEFT, padx=(0, 5))
        self.spn_threads = ttk.Spinbox(thread_frame, from_=1, to=50, width=5)
        self.spn_threads.set(10)
        self.spn_threads.pack(side=tk.LEFT, padx=(0, 15))
        ttk.Label(thread_frame, text="(Xử lý song song 50-100 máy cùng lúc trong vài giây)", font=("Segoe UI", 9, "italic"), foreground="#666").pack(side=tk.LEFT)

        # 4. Điều khiển & Tiến trình
        ctl_frame = ttk.Frame(main_frame)
        ctl_frame.pack(fill=tk.X, pady=(0, 8))

        self.btn_start = tk.Button(ctl_frame, text="BẮT ĐẦU GỠ LỖI WI-FI", font=("Segoe UI", 11, "bold"), bg="#1976d2", fg="white", activebackground="#1565c0", activeforeground="white", relief=tk.RAISED, cursor="hand2", padx=15, pady=8, command=self.start_fixing)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_stop = tk.Button(ctl_frame, text="DỪNG LẠI", font=("Segoe UI", 11, "bold"), bg="#e0e0e0", fg="#888888", relief=tk.RAISED, padx=15, pady=8, state=tk.DISABLED, command=self.stop_fixing)
        self.btn_stop.pack(side=tk.LEFT)

        self.lbl_status = ttk.Label(ctl_frame, text="Sẵn sàng...", font=("Segoe UI", 10, "bold"), foreground="#333333")
        self.lbl_status.pack(side=tk.RIGHT, padx=10)

        # Thanh tiến trình
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        # 5. Nhật ký / Log
        log_frame = ttk.LabelFrame(main_frame, text=" Nhật ký thực thi (Live Log) ", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_btn_row = ttk.Frame(log_frame)
        log_btn_row.pack(fill=tk.X, pady=(0, 4))

        ttk.Button(log_btn_row, text="Xóa Log", command=self.clear_log).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(log_btn_row, text="Lưu Log ra file", command=self.save_log_file).pack(side=tk.LEFT)

        self.txt_log = scrolledtext.ScrolledText(log_frame, height=10, font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4")
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        # Cấu hình màu cho log
        self.txt_log.tag_configure("INFO", foreground="#4fc3f7")
        self.txt_log.tag_configure("SUCCESS", foreground="#81c784", font=("Consolas", 9, "bold"))
        self.txt_log.tag_configure("WARNING", foreground="#ffb74d")
        self.txt_log.tag_configure("ERROR", foreground="#e57373", font=("Consolas", 9, "bold"))
        self.txt_log.tag_configure("CMD", foreground="#b0bec5")

    def _on_enable_wifi_toggle(self):
        if not self.var_enable_wifi.get():
            self.var_connect_wifi.set(False)
            self.ent_wifi.config(state=tk.DISABLED)
        else:
            self.ent_wifi.config(state=tk.NORMAL)

    def _on_connect_wifi_toggle(self):
        if self.var_connect_wifi.get():
            self.var_enable_wifi.set(True)
            self.ent_wifi.config(state=tk.NORMAL)
        else:
            self.ent_wifi.config(state=tk.DISABLED)

    def log(self, text, tag="INFO"):
        """Ghi log an toàn giữa các luồng"""
        now = time.strftime("%H:%M:%S")
        log_entry = f"[{now}] {text}\n"
        self.root.after(0, self._append_log, log_entry, tag)

    def _append_log(self, text, tag):
        self.txt_log.insert(tk.END, text, tag)
        self.txt_log.see(tk.END)

    def clear_log(self):
        self.txt_log.delete("1.0", tk.END)

    def save_log_file(self):
        content = self.txt_log.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Thông báo", "Log hiện đang trống.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt", 
            filetypes=[("Text file", "*.txt"), ("All files", "*.*")], 
            initialfile=f"wifi_fix_log_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Thành công", f"Đã lưu log tại:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")

    def _check_adb_status(self):
        """Kiểm tra adb có khả dụng trong hệ thống không"""
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            res = subprocess.run([self.adb_bin, "version"], capture_output=True, text=True, startupinfo=startupinfo)
            if res.returncode == 0:
                self.log(f"Kết nối ADB thành công: {self.adb_bin}", "SUCCESS")
            else:
                self.log("Cảnh báo: ADB trả về mã lỗi. Kiểm tra biến môi trường PATH.", "WARNING")
        except FileNotFoundError:
            self.log("LỖI: Không tìm thấy ADB trên máy tính!", "ERROR")
            messagebox.showwarning("Cảnh báo", "Không tìm thấy ADB trong hệ thống. Hãy chắc chắn ADB đã được cài đặt.")

    def get_parsed_uids(self):
        """Lấy danh sách các UID từ ô nhập, loại bỏ trùng lặp và khoảng trắng"""
        raw_text = self.txt_uids.get("1.0", tk.END).strip()
        if not raw_text:
            return []
        items = re.split(r"[\r\n,;\s]+", raw_text)
        uids = []
        for it in items:
            cleaned = it.strip()
            if cleaned and cleaned not in uids:
                uids.append(cleaned)
        return uids

    def _update_uid_count(self, event=None):
        uids = self.get_parsed_uids()
        self.lbl_uid_count.config(text=f"Tổng: {len(uids)} UID")

    def paste_from_clipboard(self):
        try:
            cb_text = self.root.clipboard_get()
            self.txt_uids.insert(tk.END, "\n" + cb_text.strip() + "\n")
            self._update_uid_count()
        except Exception:
            messagebox.showinfo("Thông báo", "Clipboard trống hoặc không có văn bản.")

    def clear_uids(self):
        self.txt_uids.delete("1.0", tk.END)
        self._update_uid_count()

    def scan_adb_devices(self):
        """Quét các thiết bị ADB đang kết nối"""
        self.log("Đang quét các thiết bị ADB kết nối...", "INFO")
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            res = subprocess.run([self.adb_bin, "devices"], capture_output=True, text=True, timeout=8, startupinfo=startupinfo)
            lines = res.stdout.strip().splitlines()
            found_devices = []
            for line in lines[1:]:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == "device":
                    found_devices.append(parts[0])
                    
            if not found_devices:
                self.log("Không tìm thấy thiết bị nào đang ở trạng thái 'device'!", "WARNING")
                messagebox.showinfo("Kết quả", "Không tìm thấy thiết bị nào đang kết nối.\nKiểm tra cáp kết nối và USB Debugging.")
                return
                
            existing_uids = self.get_parsed_uids()
            for dev in found_devices:
                if dev not in existing_uids:
                    existing_uids.append(dev)
            
            self.txt_uids.delete("1.0", tk.END)
            self.txt_uids.insert(tk.END, "\n".join(existing_uids))
            self._update_uid_count()
            self.log(f"Đã phát hiện {len(found_devices)} thiết bị: {', '.join(found_devices)}", "SUCCESS")
        except Exception as e:
            self.log(f"Lỗi khi quét thiết bị ADB: {e}", "ERROR")

    def execute_adb(self, uid, cmd_list, timeout=10):
        """Chạy 1 lệnh adb với timeout an toàn"""
        if self.stop_requested:
            return False, "Bị hủy bởi người dùng"
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            full_cmd = [self.adb_bin, "-s", uid] + cmd_list
            res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout, startupinfo=startupinfo)
            return True, res.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Timeout quá thời gian chờ"
        except Exception as e:
            return False, str(e)

    def fix_single_device(self, uid, wifi_ssid=None, wifi_pass=None):
        """Quy trình gỡ lỗi Wi-Fi cho 1 thiết bị theo script wifi_loi.bat + kết nối Wi-Fi mới"""
        if self.stop_requested:
            return uid, False, "Đã hủy"

        self.log(f"[{uid}] Bắt đầu quy trình gỡ lỗi...", "INFO")
        
        # 1. Sleep khởi động
        self.execute_adb(uid, ["shell", "sleep 1"], timeout=5)

        # 2. Xóa cấu hình HTTP Proxy
        if self.var_clear_proxy.get():
            self.log(f"[{uid}] Xóa cấu hình HTTP Proxy...", "CMD")
            self.execute_adb(uid, ["shell", "settings put global http_proxy :0"])
            self.execute_adb(uid, ["shell", "settings delete global http_proxy"])
            self.execute_adb(uid, ["shell", "settings delete global global_http_proxy_host"])
            self.execute_adb(uid, ["shell", "settings delete global global_http_proxy_port"])

        if self.stop_requested:
            return uid, False, "Đã hủy"

        # 2b. Xóa dữ liệu app College Proxy (pm clear & force-stop)
        if self.var_clear_college.get():
            self.log(f"[{uid}] Đang xóa dữ liệu & tắt app College Proxy...", "CMD")
            ok_pm, out_pm = self.execute_adb(uid, ["shell", "pm list packages college"], timeout=5)
            target_pkgs = []
            if ok_pm and out_pm:
                for line in out_pm.splitlines():
                    line = line.strip()
                    if line.startswith("package:"):
                        p = line.replace("package:", "").strip()
                        if p and p not in target_pkgs:
                            target_pkgs.append(p)

            if not target_pkgs:
                target_pkgs = ["com.cell47.College_Proxy", "com.cell47.collegeproxy"]

            cleared_any = False
            for pkg in target_pkgs:
                self.execute_adb(uid, ["shell", "am", "force-stop", pkg], timeout=5)
                ok_clr, res_clr = self.execute_adb(uid, ["shell", "pm", "clear", pkg], timeout=8)
                if ok_clr and "Success" in res_clr:
                    self.log(f"[{uid}] Đã clear dữ liệu College Proxy ({pkg})", "SUCCESS")
                    cleared_any = True
                else:
                    self.execute_adb(uid, ["shell", "am", "force-stop", pkg], timeout=5)

            if not cleared_any:
                self.log(f"[{uid}] Hoàn tất xử lý College Proxy (app không có dữ liệu hoặc đã dừng)", "INFO")

        if self.stop_requested:
            return uid, False, "Đã hủy"

        # 3. Quên mạng Wi-Fi đã lưu (0 đến 15)
        if self.var_forget_wifi.get():
            self.log(f"[{uid}] Quên danh sách mạng Wi-Fi cũ...", "CMD")
            forget_cmd = "for i in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do cmd wifi forget-network $i 2>/dev/null; done"
            ok, _ = self.execute_adb(uid, ["shell", forget_cmd], timeout=8)
            if not ok:
                for net_id in range(9):
                    self.execute_adb(uid, ["shell", f"cmd wifi forget-network {net_id}"], timeout=3)

        if self.stop_requested:
            return uid, False, "Đã hủy"

        # 4. Tắt & ngắt kết nối app ADBJoinWiFi
        if self.var_stop_app.get():
            self.log(f"[{uid}] Ngắt kết nối app ADBJoinWiFi cũ...", "CMD")
            self.execute_adb(uid, ["shell", "am force-stop com.steinwurf.adbjoinwifi"])
            self.execute_adb(uid, ["shell", "sleep 1"], timeout=5)
            self.execute_adb(uid, ["shell", "am start -n com.steinwurf.adbjoinwifi/.MainActivity -e disconnect true"])
            self.execute_adb(uid, ["shell", "sleep 1"], timeout=5)

        if self.stop_requested:
            return uid, False, "Đã hủy"

        # 5. Tắt Wi-Fi
        if self.var_disable_wifi.get():
            self.log(f"[{uid}] Tắt Wi-Fi (svc wifi disable)...", "CMD")
            self.execute_adb(uid, ["shell", "svc wifi disable"])
            self.execute_adb(uid, ["shell", "sleep 1"], timeout=5)

        # 6. Bật lại Wi-Fi
        if self.var_enable_wifi.get():
            self.log(f"[{uid}] Bật lại Wi-Fi (svc wifi enable)...", "CMD")
            self.execute_adb(uid, ["shell", "svc wifi enable"])
            self.execute_adb(uid, ["shell", "sleep 2"], timeout=5)

        if self.stop_requested:
            return uid, False, "Đã hủy"

        # 7. Kết nối Wi-Fi mới qua app ADBJoinWiFi (Nếu được chọn)
        if self.var_connect_wifi.get() and wifi_ssid:
            self.log(f"[{uid}] Đang kết nối vào Wi-Fi: '{wifi_ssid}' qua ADBJoinWiFi...", "CMD")
            if wifi_pass:
                join_cmd = [
                    "shell", "am", "start", "-n", "com.steinwurf.adbjoinwifi/.MainActivity",
                    "-e", "ssid", wifi_ssid,
                    "-e", "password_type", "WPA",
                    "-e", "password", wifi_pass
                ]
            else:
                join_cmd = [
                    "shell", "am", "start", "-n", "com.steinwurf.adbjoinwifi/.MainActivity",
                    "-e", "ssid", wifi_ssid,
                    "-e", "password_type", "open"
                ]
            ok_join, res_join = self.execute_adb(uid, join_cmd, timeout=8)
            if ok_join:
                self.log(f"[{uid}] Đã gửi lệnh kết nối Wi-Fi thành công!", "SUCCESS")
            else:
                self.log(f"[{uid}] Cảnh báo: Không thể gửi lệnh kết nối Wi-Fi: {res_join}", "WARNING")

        self.log(f"[{uid}] [OK] HOÀN TẤT GỠ LỖI VÀ KẾT NỐI WI-FI!", "SUCCESS")
        return uid, True, "Thành công"

    def start_fixing(self):
        uids = self.get_parsed_uids()
        if not uids:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập hoặc quét ít nhất 1 UID thiết bị!")
            return

        wifi_ssid = None
        wifi_pass = None
        if self.var_connect_wifi.get():
            raw_wifi = self.ent_wifi.get().strip()
            if not raw_wifi:
                messagebox.showwarning("Cảnh báo", "Vui lòng nhập thông tin Wi-Fi theo định dạng user|pass (VD: Aruba3.2|66668888)!")
                return
            if "|" in raw_wifi:
                parts = raw_wifi.split("|", 1)
                wifi_ssid = parts[0].strip()
                wifi_pass = parts[1].strip()
            else:
                wifi_ssid = raw_wifi
                wifi_pass = ""

            if not wifi_ssid:
                messagebox.showwarning("Cảnh báo", "Tên Wi-Fi (SSID) không được để trống!")
                return

        try:
            num_threads = int(self.spn_threads.get())
            if num_threads < 1:
                num_threads = 1
        except ValueError:
            num_threads = 10

        self.is_running = True
        self.stop_requested = False

        self.btn_start.config(state=tk.DISABLED, bg="#9e9e9e")
        self.btn_stop.config(state=tk.NORMAL, bg="#d32f2f", fg="white")
        self.btn_scan.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.progress_bar["maximum"] = len(uids)

        self.log("==================================================", "INFO")
        log_msg = f"BẮT ĐẦU XỬ LÝ: {len(uids)} thiết bị với {num_threads} luồng song song"
        if wifi_ssid:
            log_msg += f" | Kết nối Wi-Fi: '{wifi_ssid}'"
        self.log(log_msg, "INFO")
        self.log("==================================================", "INFO")

        worker_thread = threading.Thread(target=self._run_batch, args=(uids, num_threads, wifi_ssid, wifi_pass), daemon=True)
        worker_thread.start()

    def _run_batch(self, uids, num_threads, wifi_ssid, wifi_pass):
        total = len(uids)
        success_count = 0
        fail_count = 0

        self.executor = ThreadPoolExecutor(max_workers=num_threads)
        futures = {self.executor.submit(self.fix_single_device, uid, wifi_ssid, wifi_pass): uid for uid in uids}

        completed = 0
        for fut in as_completed(futures):
            if self.stop_requested:
                break
            uid = futures[fut]
            try:
                res_uid, ok, msg = fut.result()
                if ok:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                self.log(f"[{uid}] Lỗi ngoại lệ: {e}", "ERROR")

            completed += 1
            progress_percent = int((completed / total) * 100)
            self.root.after(0, self._update_progress, completed, total, success_count, fail_count, progress_percent)

        if self.stop_requested:
            self.log("[!] Tiến trình đã được dừng bởi người dùng!", "WARNING")

        self.log("==================================================", "INFO")
        self.log(f"KẾT THÚC: Hoàn thành {completed}/{total} máy. Thành công: {success_count}, Lỗi/Hủy: {fail_count}", "SUCCESS" if fail_count == 0 else "WARNING")
        self.log("==================================================", "INFO")

        self.root.after(0, self._finish_batch, success_count, fail_count, total)

    def _update_progress(self, completed, total, success, fail, percent):
        self.progress_bar["value"] = completed
        self.lbl_status.config(text=f"Tiến độ: {completed}/{total} ({percent}%) | Thành công: {success} | Lỗi: {fail}")

    def _finish_batch(self, success, fail, total):
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL, bg="#1976d2")
        self.btn_stop.config(state=tk.DISABLED, bg="#e0e0e0", fg="#888888")
        self.btn_scan.config(state=tk.NORMAL)
        
        msg = f"Đã xử lý xong {total} thiết bị!\n- Thành công: {success}\n- Lỗi/Hủy: {fail}"
        if fail == 0:
            messagebox.showinfo("Hoàn tất", msg)
        else:
            messagebox.showwarning("Hoàn tất có lỗi", msg)

    def stop_fixing(self):
        if self.is_running:
            self.stop_requested = True
            self.log("Đang yêu cầu dừng... Vui lòng đợi các luồng hoàn tất.", "WARNING")
            self.lbl_status.config(text="Đang dừng...")

    # ==========================================================
    # CÁC HÀM XỬ LÝ TỰ ĐỘNG CẬP NHẬT QUA GITHUB (AUTO-UPDATER)
    # ==========================================================

    def configure_repo(self):
        """Mở hộp thoại cho phép người dùng xem hoặc đổi GitHub Repo"""
        curr = load_github_repo()
        new_val = simpledialog.askstring(
            "Cấu hình GitHub Repo",
            "Nhập địa chỉ repository GitHub dạng username/repo-name:\n(Ví dụ: duckiend3v/Tool_Fix_Wifi)",
            initialvalue=curr,
            parent=self.root
        )
        if new_val:
            new_val = new_val.strip().replace("https://github.com/", "").strip("/")
            if new_val:
                save_github_repo(new_val)
                self.log(f"Đã lưu GitHub Repo cập nhật: {new_val}", "SUCCESS")
                messagebox.showinfo("Thành công", f"Đã cấu hình GitHub Repo:\n{new_val}")

    def check_github_update(self, silent=False):
        """Kiểm tra phiên bản mới từ GitHub Release trong luồng riêng"""
        repo = load_github_repo()
        self.btn_update.config(text="Đang kiểm tra...", state=tk.DISABLED)

        def _worker():
            try:
                api_url = f"https://api.github.com/repos/{repo}/releases/latest"
                req = urllib.request.Request(
                    api_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ToolFixWifi-AutoUpdater",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                with urllib.request.urlopen(req, timeout=12) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                
                tag_name = res_data.get("tag_name", "").strip()
                release_name = res_data.get("name", tag_name)
                body = res_data.get("body", "Không có thông tin thay đổi.")
                assets = res_data.get("assets", [])
                html_url = res_data.get("html_url", f"https://github.com/{repo}/releases")

                self.root.after(0, self._handle_update_result, tag_name, release_name, body, assets, html_url, repo, silent)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    err_msg = f"Chưa tìm thấy bản phát hành (Release) nào trên GitHub:\nhttps://github.com/{repo}/releases\n\nHãy đảm bảo bạn đã tạo ít nhất 1 Release trên GitHub (kèm file .exe hoặc .zip)."
                elif e.code == 403:
                    err_msg = "GitHub giới hạn lượt truy cập tạm thời (403). Vui lòng thử lại sau vài phút."
                else:
                    err_msg = f"Lỗi kết nối GitHub (HTTP {e.code}): {e.reason}"
                self.root.after(0, self._handle_update_error, err_msg, silent)
            except Exception as e:
                self.root.after(0, self._handle_update_error, f"Không thể kết nối tới máy chủ GitHub:\n{e}", silent)

        threading.Thread(target=_worker, daemon=True).start()

    def _handle_update_result(self, tag_name, release_name, body, assets, html_url, repo, silent):
        self.btn_update.config(text="🔄 Kiểm tra Cập nhật", state=tk.NORMAL)
        if is_newer_version(tag_name, APP_VERSION):
            self.log(f"Phát hiện bản cập nhật mới: {tag_name} (Hiện tại: {APP_VERSION})", "INFO")
            self._show_update_modal(tag_name, release_name, body, assets, html_url)
        else:
            self.log(f"Bạn đang dùng phiên bản mới nhất ({APP_VERSION}).", "INFO")
            if not silent:
                messagebox.showinfo("Cập nhật Tool", f"Bạn đang sử dụng phiên bản mới nhất ({APP_VERSION})!\n\nGitHub Repo: {repo}")

    def _handle_update_error(self, err_msg, silent):
        self.btn_update.config(text="🔄 Kiểm tra Cập nhật", state=tk.NORMAL)
        if not silent:
            messagebox.showwarning("Kiểm tra Cập nhật", err_msg)

    def _show_update_modal(self, tag_name, release_name, body, assets, html_url):
        dlg = tk.Toplevel(self.root)
        dlg.title("Cập nhật phiên bản mới")
        dlg.geometry("540x440")
        dlg.minsize(460, 360)
        dlg.transient(self.root)
        dlg.grab_set()

        content = ttk.Frame(dlg, padding=15)
        content.pack(fill=tk.BOTH, expand=True)

        lbl_top = ttk.Label(content, text=f"🎉 ĐÃ CÓ PHIÊN BẢN MỚI: {tag_name}", font=("Segoe UI", 12, "bold"), foreground="#2e7d32")
        lbl_top.pack(anchor=tk.W, pady=(0, 4))

        lbl_sub = ttk.Label(content, text=f"Phiên bản hiện tại: {APP_VERSION}  ➔  Mới nhất: {tag_name}\nTên bản phát hành: {release_name}", font=("Segoe UI", 9))
        lbl_sub.pack(anchor=tk.W, pady=(0, 8))

        ttk.Label(content, text="Nội dung cập nhật / Changelog:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(0, 4))
        
        txt_changelog = scrolledtext.ScrolledText(content, height=8, font=("Consolas", 9), wrap=tk.WORD)
        txt_changelog.insert(tk.END, body if body.strip() else "Không có ghi chú thay đổi chi tiết.")
        txt_changelog.config(state=tk.DISABLED)
        txt_changelog.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        lbl_dl_status = ttk.Label(content, text="", font=("Segoe UI", 9, "italic"), foreground="#1565c0")
        lbl_dl_status.pack(anchor=tk.W)

        prog_dl = ttk.Progressbar(content, orient="horizontal", mode="determinate")
        prog_dl.pack(fill=tk.X, pady=(4, 10))

        btn_box = ttk.Frame(content)
        btn_box.pack(fill=tk.X)

        btn_do_update = tk.Button(
            btn_box, text="⚡ CẬP NHẬT NGAY", font=("Segoe UI", 10, "bold"),
            bg="#1976d2", fg="white", activebackground="#1565c0", activeforeground="white",
            relief=tk.RAISED, padx=14, pady=6, cursor="hand2"
        )
        btn_do_update.pack(side=tk.LEFT)

        btn_web = ttk.Button(btn_box, text="Xem trên GitHub", command=lambda: webbrowser.open(html_url))
        btn_web.pack(side=tk.LEFT, padx=(8, 0))

        btn_close = ttk.Button(btn_box, text="Để sau", command=dlg.destroy)
        btn_close.pack(side=tk.RIGHT)

        btn_do_update.config(command=lambda: self._execute_download_and_install(
            tag_name, assets, dlg, btn_do_update, btn_close, lbl_dl_status, prog_dl, html_url
        ))

    def _execute_download_and_install(self, tag_name, assets, dlg, btn_update, btn_close, lbl_status, progress_bar, html_url):
        is_frozen = getattr(sys, 'frozen', False)
        target_asset = None

        if is_frozen:
            # Chạy file .exe: Ưu tiên tìm file .exe trong Release assets
            for a in assets:
                name = a.get("name", "").lower()
                if name.endswith(".exe"):
                    target_asset = a
                    break
            if not target_asset:
                for a in assets:
                    if a.get("name", "").lower().endswith(".zip"):
                        target_asset = a
                        break
        else:
            # Chạy file .py: Tìm file .zip hoặc file fix_wifi_tool.py
            for a in assets:
                name = a.get("name", "").lower()
                if name.endswith(".zip") or name == "fix_wifi_tool.py":
                    target_asset = a
                    break

        repo = load_github_repo()
        if not target_asset:
            if not is_frozen:
                download_url = f"https://raw.githubusercontent.com/{repo}/{tag_name}/fix_wifi_tool.py"
                file_name = "fix_wifi_tool.py"
            else:
                messagebox.showwarning(
                    "Chưa có file thực thi",
                    f"Bản phát hành {tag_name} trên GitHub chưa đính kèm file .exe hoặc .zip!\n\n"
                    "Tool sẽ mở trang GitHub để bạn kiểm tra.",
                    parent=dlg
                )
                webbrowser.open(html_url)
                return
        else:
            download_url = target_asset.get("browser_download_url")
            file_name = target_asset.get("name")

        btn_update.config(state=tk.DISABLED, bg="#9e9e9e")
        btn_close.config(state=tk.DISABLED)
        lbl_status.config(text=f"Đang chuẩn bị tải {file_name}...")

        def _download_thread():
            app_dir = get_app_dir()
            temp_file = os.path.join(app_dir, f"update_temp_{file_name}")
            try:
                req = urllib.request.Request(download_url, headers={"User-Agent": "Tool-Fix-Wifi-Updater"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    total_len = resp.getheader("Content-Length")
                    total_bytes = int(total_len) if total_len else None
                    downloaded = 0
                    chunk_size = 65536
                    with open(temp_file, "wb") as f:
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_bytes:
                                pct = int((downloaded / total_bytes) * 100)
                                self.root.after(0, lambda d=downloaded, t=total_bytes, p=pct: self._update_dl_progress(d, t, p, lbl_status, progress_bar))
                            else:
                                self.root.after(0, lambda d=downloaded: lbl_status.config(text=f"Đã tải {d // 1024} KB..."))

                self.root.after(0, lambda: self._apply_update(temp_file, file_name, dlg))
            except Exception as e:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
                self.root.after(0, lambda err=str(e): self._handle_dl_error(err, btn_update, btn_close, lbl_status, dlg))

        threading.Thread(target=_download_thread, daemon=True).start()

    def _update_dl_progress(self, downloaded, total_bytes, pct, lbl_status, progress_bar):
        progress_bar["value"] = pct
        lbl_status.config(text=f"Đang tải: {pct}% ({downloaded // 1024} KB / {total_bytes // 1024} KB)...")

    def _handle_dl_error(self, err_text, btn_update, btn_close, lbl_status, dlg):
        btn_update.config(state=tk.NORMAL, bg="#1976d2")
        btn_close.config(state=tk.NORMAL)
        lbl_status.config(text=f"Lỗi tải: {err_text}", foreground="#d32f2f")
        messagebox.showerror("Lỗi tải cập nhật", f"Không thể tải file cập nhật:\n{err_text}", parent=dlg)

    def _apply_update(self, temp_file, file_name, dlg):
        app_dir = get_app_dir()
        is_frozen = getattr(sys, 'frozen', False)

        try:
            # 1. Nếu là file .ZIP
            if file_name.lower().endswith(".zip"):
                with zipfile.ZipFile(temp_file, "r") as z:
                    z.extractall(app_dir)
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
                messagebox.showinfo("Cập nhật thành công", "Đã giải nén phiên bản mới thành công!\nVui lòng khởi động lại tool để áp dụng.", parent=dlg)
                dlg.destroy()
                return

            # 2. Nếu là file .EXE (chạy dạng đóng gói PyInstaller)
            if is_frozen:
                curr_exe = os.path.abspath(sys.executable)
                bat_path = os.path.join(app_dir, "apply_update.bat")
                pid = os.getpid()

                bat_content = f"""@echo off
chcp 65001 >nul
title Dang cap nhat Tool Fix Wi-Fi...
echo ========================================================
echo   DANG TIEN HANH NANG CAP PHIEN BAN MOI
echo   Vui long cho trong giay lat...
echo ========================================================
timeout /t 2 /nobreak >nul

:WAIT_LOOP
taskkill /F /PID {pid} >nul 2>&1
timeout /t 1 /nobreak >nul
move /Y "{temp_file}" "{curr_exe}" >nul 2>&1
if exist "{temp_file}" (
    echo Dang cho giai phong file cu...
    timeout /t 1 /nobreak >nul
    goto WAIT_LOOP
)

echo [OK] Nang cap thanh cong! Dang khoi dong lai tool...
start "" "{curr_exe}"
del "%~f0"
"""
                with open(bat_path, "w", encoding="utf-8") as bf:
                    bf.write(bat_content)

                subprocess.Popen(["cmd.exe", "/c", bat_path], cwd=app_dir, creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
                self.root.destroy()
                sys.exit(0)

            # 3. Nếu là file .PY
            else:
                target_py = os.path.join(app_dir, "fix_wifi_tool.py")
                if os.path.exists(target_py):
                    backup_py = os.path.join(app_dir, "fix_wifi_tool.py.bak")
                    try:
                        shutil.copy2(target_py, backup_py)
                    except Exception:
                        pass
                shutil.move(temp_file, target_py)
                messagebox.showinfo("Thành công", "Đã cập nhật xong phiên bản mới! Ứng dụng sẽ tự khởi động lại.", parent=dlg)
                subprocess.Popen([sys.executable, target_py] + sys.argv[1:], cwd=app_dir)
                self.root.destroy()
                sys.exit(0)

        except Exception as e:
            messagebox.showerror("Lỗi áp dụng bản cập nhật", f"Không thể hoàn tất cập nhật:\n{e}", parent=dlg)


def main():
    try:
        root = tk.Tk()
        app = WifiFixerApp(root)
        root.mainloop()
    except Exception as e:
        print("[LỖI KHỞI CHẠY]:")
        traceback.print_exc()
        try:
            messagebox.showerror("Lỗi", f"Không thể mở tool:\n{e}\n\n{traceback.format_exc()}")
        except Exception:
            pass
        input("\nNhấn Enter để thoát...")


if __name__ == "__main__":
    main()
