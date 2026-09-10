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


APP_VERSION = "v1.2.3"
DEFAULT_GITHUB_REPO = "duckiend3v/Fix_Wifi"


def get_app_dir():
    """Trả về thư mục gốc chứa ứng dụng (chuẩn xác cho cả file .py và .exe PyInstaller)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path):
    """Trả về đường dẫn tài nguyên (hỗ trợ cả chạy script .py và khi giải nén trong .exe PyInstaller)"""
    base_path = getattr(sys, '_MEIPASS', None)
    if base_path:
        cand = os.path.join(base_path, relative_path)
        if os.path.exists(cand):
            return cand
    cand = os.path.join(get_app_dir(), relative_path)
    return cand


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


def make_hover_button(btn, normal_bg, hover_bg, normal_fg="#ffffff", hover_fg="#ffffff"):
    """Tạo hiệu ứng hover đổi màu mượt mà cho nút bấm Tkinter"""
    def _on_enter(e):
        try:
            if str(btn["state"]) != tk.DISABLED:
                btn.config(bg=hover_bg, fg=hover_fg)
        except Exception:
            pass

    def _on_leave(e):
        try:
            if str(btn["state"]) != tk.DISABLED:
                btn.config(bg=normal_bg, fg=normal_fg)
        except Exception:
            pass

    btn.bind("<Enter>", _on_enter)
    btn.bind("<Leave>", _on_leave)


class DarkDialog:
    """Hệ thống hộp thoại thông báo Dark Slate Theme hiện đại, thay thế messagebox Windows cổ điển"""
    
    @classmethod
    def show(cls, parent, title, message, dialog_type="info", input_default=""):
        dlg = tk.Toplevel(parent) if parent else tk.Toplevel()
        dlg.title(title)
        dlg.configure(bg="#0d1117")
        dlg.resizable(False, False)
        if parent:
            dlg.transient(parent)
            dlg.grab_set()

        # Icon cho hộp thoại
        ico_file = get_resource_path("icon.ico")
        if os.path.exists(ico_file):
            try:
                dlg.iconbitmap(ico_file)
            except Exception:
                pass

        type_configs = {
            "success": {
                "tag": "✓ THÀNH CÔNG",
                "tag_bg": "#238636",
                "tag_fg": "#ffffff",
                "border": "#238636",
                "title_fg": "#3fb950"
            },
            "info": {
                "tag": "ℹ THÔNG BÁO",
                "tag_bg": "#1f6feb",
                "tag_fg": "#ffffff",
                "border": "#1f6feb",
                "title_fg": "#58a6ff"
            },
            "warning": {
                "tag": "⚠ CẢNH BÁO",
                "tag_bg": "#d29922",
                "tag_fg": "#0d1117",
                "border": "#d29922",
                "title_fg": "#d29922"
            },
            "error": {
                "tag": "✖ LỖI",
                "tag_bg": "#da3633",
                "tag_fg": "#ffffff",
                "border": "#da3633",
                "title_fg": "#f85149"
            },
            "confirm": {
                "tag": "? XÁC NHẬN",
                "tag_bg": "#8957e5",
                "tag_fg": "#ffffff",
                "border": "#8957e5",
                "title_fg": "#bc8cff"
            },
            "input": {
                "tag": "⚙ CẤU HÌNH",
                "tag_bg": "#1f6feb",
                "tag_fg": "#ffffff",
                "border": "#1f6feb",
                "title_fg": "#58a6ff"
            }
        }
        cfg = type_configs.get(dialog_type, type_configs["info"])
        res = {"value": None}

        # Khung viền sắc nét phong cách Cyber Dark
        frame = tk.Frame(dlg, bg="#161b22", highlightbackground=cfg["border"], highlightthickness=1, padx=18, pady=16)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Header: Tag badge + Title
        hdr = tk.Frame(frame, bg="#161b22")
        hdr.pack(fill=tk.X, pady=(0, 10))

        badge = tk.Label(
            hdr, 
            text=f" {cfg['tag']} ", 
            font=("Segoe UI", 9, "bold"), 
            bg=cfg["tag_bg"], 
            fg=cfg["tag_fg"], 
            padx=6, 
            pady=2
        )
        badge.pack(side=tk.LEFT, padx=(0, 8))

        title_lbl = tk.Label(
            hdr, 
            text=title, 
            font=("Segoe UI", 11, "bold"), 
            fg=cfg["title_fg"], 
            bg="#161b22"
        )
        title_lbl.pack(side=tk.LEFT, anchor=tk.W)

        # Body: Message text
        msg_frame = tk.Frame(frame, bg="#161b22")
        msg_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 14))

        msg_lbl = tk.Label(
            msg_frame, 
            text=message, 
            font=("Segoe UI", 10), 
            fg="#e6edf3", 
            bg="#161b22", 
            justify=tk.LEFT, 
            wraplength=440
        )
        msg_lbl.pack(anchor=tk.W)

        ent = None
        if dialog_type == "input":
            ent_frame = tk.Frame(frame, bg="#0d1117", highlightbackground="#30363d", highlightthickness=1, padx=6, pady=4)
            ent_frame.pack(fill=tk.X, pady=(0, 14))
            ent = tk.Entry(
                ent_frame, 
                font=("Consolas", 10), 
                bg="#0d1117", 
                fg="#58a6ff", 
                insertbackground="#58a6ff", 
                relief=tk.FLAT
            )
            ent.insert(0, input_default)
            ent.select_range(0, tk.END)
            ent.pack(fill=tk.X)
            ent.focus_set()

        # Footer: Action Buttons
        btn_box = tk.Frame(frame, bg="#161b22")
        btn_box.pack(fill=tk.X)

        def on_ok(e=None):
            if dialog_type == "confirm":
                res["value"] = True
            elif dialog_type == "input":
                res["value"] = ent.get().strip()
            else:
                res["value"] = True
            dlg.destroy()

        def on_cancel(e=None):
            if dialog_type == "confirm":
                res["value"] = False
            elif dialog_type == "input":
                res["value"] = None
            else:
                res["value"] = False
            dlg.destroy()

        if dialog_type == "confirm":
            b_ok = tk.Button(
                btn_box, text="✓ Đồng ý", font=("Segoe UI", 9, "bold"),
                bg="#238636", fg="#ffffff", relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                command=on_ok
            )
            b_ok.pack(side=tk.RIGHT, padx=(6, 0))
            b_cancel = tk.Button(
                btn_box, text="✕ Hủy bỏ", font=("Segoe UI", 9),
                bg="#21262d", fg="#c9d1d9", relief=tk.FLAT, padx=12, pady=5, cursor="hand2",
                command=on_cancel
            )
            b_cancel.pack(side=tk.RIGHT)
            make_hover_button(b_ok, "#238636", "#2ea043")
            make_hover_button(b_cancel, "#21262d", "#30363d")
        elif dialog_type == "input":
            b_ok = tk.Button(
                btn_box, text="💾 Lưu cấu hình", font=("Segoe UI", 9, "bold"),
                bg="#238636", fg="#ffffff", relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                command=on_ok
            )
            b_ok.pack(side=tk.RIGHT, padx=(6, 0))
            b_cancel = tk.Button(
                btn_box, text="✕ Hủy bỏ", font=("Segoe UI", 9),
                bg="#21262d", fg="#c9d1d9", relief=tk.FLAT, padx=12, pady=5, cursor="hand2",
                command=on_cancel
            )
            b_cancel.pack(side=tk.RIGHT)
            make_hover_button(b_ok, "#238636", "#2ea043")
            make_hover_button(b_cancel, "#21262d", "#30363d")
        else:
            btn_color = "#238636" if dialog_type == "success" else ("#da3633" if dialog_type == "error" else ("#d29922" if dialog_type == "warning" else "#1f6feb"))
            btn_hover = "#2ea043" if dialog_type == "success" else ("#f85149" if dialog_type == "error" else ("#e3b341" if dialog_type == "warning" else "#388bfd"))
            btn_fg = "#0d1117" if dialog_type == "warning" else "#ffffff"
            
            b_close = tk.Button(
                btn_box, text="✓ Đã hiểu", font=("Segoe UI", 9, "bold"),
                bg=btn_color, fg=btn_fg, relief=tk.FLAT, padx=16, pady=5, cursor="hand2",
                command=on_ok
            )
            b_close.pack(side=tk.RIGHT)
            make_hover_button(b_close, btn_color, btn_hover, btn_fg, btn_fg)

        # Phím tắt Enter và Escape
        dlg.bind("<Return>", on_ok)
        dlg.bind("<Escape>", on_cancel)

        # Canh giữa cửa sổ theo cha
        dlg.update_idletasks()
        w = max(dlg.winfo_reqwidth(), 460)
        h = max(dlg.winfo_reqheight(), 180)
        if parent and parent.winfo_viewable():
            px = parent.winfo_x()
            py = parent.winfo_y()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw - w) // 2
            y = py + (ph - h) // 2
        else:
            sw = dlg.winfo_screenwidth()
            sh = dlg.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 2
        dlg.geometry(f"{w}x{h}+{max(x, 20)}+{max(y, 20)}")

        if parent:
            parent.wait_window(dlg)
        else:
            dlg.wait_window()
        return res["value"]


def notify_info(title, message, parent=None):
    return DarkDialog.show(parent, title, message, dialog_type="info")

def notify_success(title, message, parent=None):
    return DarkDialog.show(parent, title, message, dialog_type="success")

def notify_warning(title, message, parent=None):
    return DarkDialog.show(parent, title, message, dialog_type="warning")

def notify_error(title, message, parent=None):
    return DarkDialog.show(parent, title, message, dialog_type="error")

def notify_confirm(title, message, parent=None):
    return DarkDialog.show(parent, title, message, dialog_type="confirm")

def notify_input(title, prompt, default_val="", parent=None):
    return DarkDialog.show(parent, title, prompt, dialog_type="input", input_default=default_val)


class WifiFixerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Fix Wifi")
        self.root.geometry("880x740")
        self.root.minsize(800, 640)
        
        # Thiết lập Icon cho ứng dụng
        self._setup_app_icon()
        
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
        
    def _setup_app_icon(self):
        """Thiết lập icon cửa sổ và thanh tác vụ Windows"""
        ico_file = get_resource_path("icon.ico")
        png_file = get_resource_path("icon.png")
        if not os.path.exists(ico_file) and not getattr(sys, 'frozen', False):
            try:
                import tao_icon
                tao_icon.make_icons()
                ico_file = get_resource_path("icon.ico")
                png_file = get_resource_path("icon.png")
            except Exception:
                pass
                
        if os.path.exists(ico_file):
            try:
                self.root.iconbitmap(ico_file)
            except Exception:
                pass
                
        if os.path.exists(png_file):
            try:
                img = tk.PhotoImage(file=png_file)
                self.root.iconphoto(True, img)
            except Exception:
                pass

    def _setup_styles(self):
        self.root.configure(bg="#0d1117")
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure(".", background="#0d1117", foreground="#f0f6fc")
        self.style.configure("TFrame", background="#0d1117")
        self.style.configure("Card.TFrame", background="#161b22")
        self.style.configure("TLabel", background="#0d1117", foreground="#f0f6fc", font=("Segoe UI", 10))
        self.style.configure("Card.TLabel", background="#161b22", foreground="#f0f6fc", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", background="#161b22", font=("Segoe UI", 15, "bold"), foreground="#58a6ff")
        self.style.configure("SubHeader.TLabel", background="#161b22", font=("Segoe UI", 9), foreground="#8b949e")
        self.style.configure("CardHeader.TLabel", background="#161b22", font=("Segoe UI", 10, "bold"), foreground="#58a6ff")
        
        self.style.configure(
            "TProgressbar", 
            thickness=8, 
            troughcolor="#0d1117", 
            background="#238636", 
            bordercolor="#30363d", 
            lightcolor="#2ea043", 
            darkcolor="#238636"
        )

    def _build_ui(self):
        main_container = tk.Frame(self.root, bg="#0d1117", padx=12, pady=10)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 1. HEADER CARD (Banner công cụ & Nút cập nhật)
        header_card = tk.Frame(main_container, bg="#161b22", highlightbackground="#30363d", highlightthickness=1, padx=12, pady=10)
        header_card.pack(fill=tk.X, pady=(0, 8))

        header_left = tk.Frame(header_card, bg="#161b22")
        header_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Logo phát sáng
        logo_path = get_resource_path("icon_48.png")
        if not os.path.exists(logo_path):
            logo_path = get_resource_path("icon.png")
            
        if os.path.exists(logo_path):
            try:
                self._logo_img = tk.PhotoImage(file=logo_path)
                logo_lbl = tk.Label(header_left, image=self._logo_img, bg="#161b22")
                logo_lbl.pack(side=tk.LEFT, padx=(0, 12))
            except Exception:
                pass

        header_text_frame = tk.Frame(header_left, bg="#161b22")
        header_text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        title_row = tk.Frame(header_text_frame, bg="#161b22")
        title_row.pack(anchor=tk.W, fill=tk.X)

        title_lbl = tk.Label(title_row, text="FIX WIFI", font=("Segoe UI", 15, "bold"), fg="#58a6ff", bg="#161b22")
        title_lbl.pack(side=tk.LEFT)

        ver_badge = tk.Label(
            title_row, 
            text=f" {APP_VERSION} ", 
            font=("Segoe UI", 9, "bold"), 
            bg="#238636", 
            fg="#ffffff", 
            padx=6, 
            pady=1
        )
        ver_badge.pack(side=tk.LEFT, padx=(8, 0))

        sub_lbl = tk.Label(
            header_text_frame, 
            text="Gỡ lỗi kẹt Proxy, clear app College Proxy, không bắt được Wi-Fi, tự động kết nối Wi-Fi mới qua app ADBJoinWiFi.", 
            font=("Segoe UI", 9), 
            fg="#8b949e", 
            bg="#161b22"
        )
        sub_lbl.pack(anchor=tk.W, pady=(2, 0))

        # Cụm nút Cập nhật GitHub góc phải
        header_right = tk.Frame(header_card, bg="#161b22")
        header_right.pack(side=tk.RIGHT, anchor=tk.E, padx=(10, 0))

        self.lbl_adb_badge = tk.Label(
            header_right, 
            text="● ADB: Đang quét...", 
            font=("Segoe UI", 9, "bold"), 
            fg="#8b949e", 
            bg="#161b22"
        )
        self.lbl_adb_badge.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_update = tk.Button(
            header_right, 
            text="🔄 Kiểm tra Cập nhật", 
            font=("Segoe UI", 9, "bold"), 
            bg="#238636", 
            fg="#ffffff", 
            activebackground="#2ea043", 
            activeforeground="#ffffff",
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=12, 
            pady=5,
            command=lambda: self.check_github_update(silent=False)
        )
        self.btn_update.pack(side=tk.LEFT, padx=(0, 6))
        make_hover_button(self.btn_update, "#238636", "#2ea043")

        btn_repo_cfg = tk.Button(
            header_right, 
            text="⚙ Repo", 
            font=("Segoe UI", 9), 
            bg="#21262d", 
            fg="#c9d1d9", 
            activebackground="#30363d", 
            activeforeground="#ffffff",
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=8, 
            pady=5, 
            command=self.configure_repo
        )
        btn_repo_cfg.pack(side=tk.LEFT)
        make_hover_button(btn_repo_cfg, "#21262d", "#30363d")

        # 2. KHUNG NHẬP DANH SÁCH UID
        uid_card = tk.Frame(main_container, bg="#161b22", highlightbackground="#30363d", highlightthickness=1, padx=10, pady=8)
        uid_card.pack(fill=tk.BOTH, expand=False, pady=(0, 8))

        btn_row = tk.Frame(uid_card, bg="#161b22")
        btn_row.pack(fill=tk.X, pady=(0, 6))

        tk.Label(btn_row, text="📱 Danh Sách Thiết Bị Android (UID / Serial):", font=("Segoe UI", 10, "bold"), fg="#58a6ff", bg="#161b22").pack(side=tk.LEFT, padx=(0, 10))

        self.btn_scan = tk.Button(
            btn_row, 
            text="🔍 Quét thiết bị ADB", 
            font=("Segoe UI", 9, "bold"), 
            bg="#1f6feb", 
            fg="#ffffff", 
            activebackground="#388bfd", 
            activeforeground="#ffffff",
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=10, 
            pady=3,
            command=self.scan_adb_devices
        )
        self.btn_scan.pack(side=tk.LEFT, padx=(0, 6))
        make_hover_button(self.btn_scan, "#1f6feb", "#388bfd")

        self.btn_paste = tk.Button(
            btn_row, 
            text="📋 Dán từ Clipboard", 
            font=("Segoe UI", 9), 
            bg="#21262d", 
            fg="#c9d1d9", 
            activebackground="#30363d", 
            activeforeground="#ffffff",
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=8, 
            pady=3,
            command=self.paste_from_clipboard
        )
        self.btn_paste.pack(side=tk.LEFT, padx=(0, 6))
        make_hover_button(self.btn_paste, "#21262d", "#30363d")

        self.btn_clear = tk.Button(
            btn_row, 
            text="🗑 Xóa ô nhập", 
            font=("Segoe UI", 9), 
            bg="#21262d", 
            fg="#c9d1d9", 
            activebackground="#30363d", 
            activeforeground="#ffffff",
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=8, 
            pady=3,
            command=self.clear_uids
        )
        self.btn_clear.pack(side=tk.LEFT, padx=(0, 6))
        make_hover_button(self.btn_clear, "#21262d", "#30363d")

        self.lbl_uid_count = tk.Label(
            btn_row, 
            text=" 0 UID ", 
            font=("Segoe UI", 9, "bold"), 
            bg="#21262d", 
            fg="#3fb950", 
            padx=8, 
            pady=2
        )
        self.lbl_uid_count.pack(side=tk.RIGHT, padx=2)

        # Ô Text nhập UIDs
        self.txt_uids = scrolledtext.ScrolledText(
            uid_card, 
            height=4, 
            font=("Consolas", 10), 
            wrap=tk.WORD, 
            bg="#090d13", 
            fg="#e6edf3", 
            insertbackground="#58a6ff", 
            selectbackground="#1f6feb", 
            relief=tk.FLAT
        )
        self.txt_uids.pack(fill=tk.BOTH, expand=True)
        self.txt_uids.bind("<KeyRelease>", self._update_uid_count)

        # 3. TÙY CHỌN GỠ LỖI & KẾT NỐI WI-FI MỚI
        opt_card = tk.Frame(main_container, bg="#161b22", highlightbackground="#30363d", highlightthickness=1, padx=10, pady=8)
        opt_card.pack(fill=tk.X, pady=(0, 8))

        tk.Label(opt_card, text="⚡ Các Bước Xử Lý Gỡ Lỗi & Kết Nối Wi-Fi:", font=("Segoe UI", 10, "bold"), fg="#58a6ff", bg="#161b22").pack(anchor=tk.W, pady=(0, 6))

        cb_grid = tk.Frame(opt_card, bg="#161b22")
        cb_grid.pack(fill=tk.X)

        self.var_clear_proxy = tk.BooleanVar(value=True)
        self.var_clear_college = tk.BooleanVar(value=True)
        self.var_forget_wifi = tk.BooleanVar(value=True)
        self.var_stop_app = tk.BooleanVar(value=True)
        self.var_disable_wifi = tk.BooleanVar(value=True)
        self.var_enable_wifi = tk.BooleanVar(value=True)

        cb_style = {
            "bg": "#161b22", 
            "fg": "#e6edf3", 
            "selectcolor": "#090d13", 
            "activebackground": "#161b22", 
            "activeforeground": "#58a6ff", 
            "font": ("Segoe UI", 9)
        }

        cb1 = tk.Checkbutton(cb_grid, text="1. Xóa sạch HTTP Proxy (settings delete proxy)", variable=self.var_clear_proxy, **cb_style)
        cb1.grid(row=0, column=0, sticky=tk.W, pady=2, padx=4)

        cb2 = tk.Checkbutton(cb_grid, text="2. Xóa dữ liệu app College Proxy (pm clear & stop)", variable=self.var_clear_college, **cb_style)
        cb2.grid(row=0, column=1, sticky=tk.W, pady=2, padx=15)

        cb3 = tk.Checkbutton(cb_grid, text="3. Quên toàn bộ Wi-Fi cũ (forget-network 0..15)", variable=self.var_forget_wifi, **cb_style)
        cb3.grid(row=1, column=0, sticky=tk.W, pady=2, padx=4)

        cb4 = tk.Checkbutton(cb_grid, text="4. Tắt & Ngắt app ADBJoinWiFi cũ", variable=self.var_stop_app, **cb_style)
        cb4.grid(row=1, column=1, sticky=tk.W, pady=2, padx=15)

        cb5 = tk.Checkbutton(cb_grid, text="5. Tắt Wi-Fi (svc wifi disable)", variable=self.var_disable_wifi, **cb_style)
        cb5.grid(row=2, column=0, sticky=tk.W, pady=2, padx=4)

        cb6 = tk.Checkbutton(cb_grid, text="6. Tự động BẬT LẠI Wi-Fi (svc wifi enable)", variable=self.var_enable_wifi, command=self._on_enable_wifi_toggle, **cb_style)
        cb6.grid(row=2, column=1, sticky=tk.W, pady=2, padx=15)

        # Bước 7: Khung kết nối Wi-Fi mới
        self.var_connect_wifi = tk.BooleanVar(value=True)
        wifi_conn_frame = tk.Frame(opt_card, bg="#0d1117", highlightbackground="#30363d", highlightthickness=1, padx=8, pady=6)
        wifi_conn_frame.pack(fill=tk.X, pady=(6, 4))

        self.cb7 = tk.Checkbutton(
            wifi_conn_frame, 
            text="7. Kết nối lại Wi-Fi mới qua ADBJoinWiFi:", 
            variable=self.var_connect_wifi,
            command=self._on_connect_wifi_toggle,
            bg="#0d1117", fg="#58a6ff", selectcolor="#161b22", activebackground="#0d1117", activeforeground="#58a6ff", font=("Segoe UI", 9, "bold")
        )
        self.cb7.pack(side=tk.LEFT, padx=(0, 6))

        self.ent_wifi = tk.Entry(
            wifi_conn_frame, 
            width=28, 
            font=("Consolas", 10, "bold"), 
            bg="#161b22", 
            fg="#58a6ff", 
            insertbackground="#58a6ff", 
            relief=tk.FLAT
        )
        self.ent_wifi.insert(0, "Aruba3.2|66668888")
        self.ent_wifi.pack(side=tk.LEFT, padx=(0, 8), ipady=3)

        tk.Label(wifi_conn_frame, text="(Định dạng: Tên_Wifi|Mật_khẩu)", font=("Segoe UI", 9, "italic"), fg="#8b949e", bg="#0d1117").pack(side=tk.LEFT)

        # Cấu hình đa luồng
        thread_frame = tk.Frame(opt_card, bg="#161b22")
        thread_frame.pack(fill=tk.X, pady=(4, 0))
        
        tk.Label(thread_frame, text="⚡ Số luồng xử lý song song (Threads):", font=("Segoe UI", 9), fg="#e6edf3", bg="#161b22").pack(side=tk.LEFT, padx=(0, 5))
        self.spn_threads = ttk.Spinbox(thread_frame, from_=1, to=50, width=5)
        self.spn_threads.set(10)
        self.spn_threads.pack(side=tk.LEFT, padx=(0, 12))
        tk.Label(thread_frame, text="(Xử lý đồng thời 50-100 máy trong vài giây)", font=("Segoe UI", 9, "italic"), fg="#8b949e", bg="#161b22").pack(side=tk.LEFT)

        # 4. ĐIỀU KHIỂN & TIẾN TRÌNH
        ctl_card = tk.Frame(main_container, bg="#161b22", highlightbackground="#30363d", highlightthickness=1, padx=10, pady=8)
        ctl_card.pack(fill=tk.X, pady=(0, 8))

        ctl_left = tk.Frame(ctl_card, bg="#161b22")
        ctl_left.pack(side=tk.LEFT)

        self.btn_start = tk.Button(
            ctl_left, 
            text="▶ BẮT ĐẦU GỠ LỖI & SỬA WI-FI", 
            font=("Segoe UI", 11, "bold"), 
            bg="#238636", 
            fg="#ffffff", 
            activebackground="#2ea043", 
            activeforeground="#ffffff", 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=18, 
            pady=8, 
            command=self.start_fixing
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))
        make_hover_button(self.btn_start, "#238636", "#2ea043")

        self.btn_stop = tk.Button(
            ctl_left, 
            text="⏹ DỪNG LẠI", 
            font=("Segoe UI", 11, "bold"), 
            bg="#21262d", 
            fg="#8b949e", 
            activebackground="#da3633", 
            activeforeground="#ffffff", 
            relief=tk.FLAT, 
            padx=14, 
            pady=8, 
            state=tk.DISABLED, 
            command=self.stop_fixing
        )
        self.btn_stop.pack(side=tk.LEFT)
        make_hover_button(self.btn_stop, "#21262d", "#da3633", "#8b949e", "#ffffff")

        self.lbl_status = tk.Label(ctl_card, text="● Sẵn sàng...", font=("Segoe UI", 10, "bold"), fg="#3fb950", bg="#161b22")
        self.lbl_status.pack(side=tk.RIGHT, padx=6)

        # Thanh tiến trình
        self.progress_bar = ttk.Progressbar(main_container, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        # 5. NHẬT KÝ / LOG TERMINAL
        log_card = tk.Frame(main_container, bg="#161b22", highlightbackground="#30363d", highlightthickness=1, padx=10, pady=8)
        log_card.pack(fill=tk.BOTH, expand=True)

        log_btn_row = tk.Frame(log_card, bg="#161b22")
        log_btn_row.pack(fill=tk.X, pady=(0, 4))

        tk.Label(log_btn_row, text="📜 Nhật Ký Hoạt Động (Live Terminal):", font=("Segoe UI", 10, "bold"), fg="#58a6ff", bg="#161b22").pack(side=tk.LEFT, padx=(0, 10))

        btn_clr_log = tk.Button(
            log_btn_row, 
            text="🧹 Xóa Log", 
            font=("Segoe UI", 8), 
            bg="#21262d", 
            fg="#c9d1d9", 
            activebackground="#30363d", 
            activeforeground="#ffffff", 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=8, 
            pady=2,
            command=self.clear_log
        )
        btn_clr_log.pack(side=tk.LEFT, padx=(0, 6))
        make_hover_button(btn_clr_log, "#21262d", "#30363d")

        btn_sav_log = tk.Button(
            log_btn_row, 
            text="💾 Lưu Log ra file", 
            font=("Segoe UI", 8), 
            bg="#21262d", 
            fg="#c9d1d9", 
            activebackground="#30363d", 
            activeforeground="#ffffff", 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=8, 
            pady=2,
            command=self.save_log_file
        )
        btn_sav_log.pack(side=tk.LEFT)
        make_hover_button(btn_sav_log, "#21262d", "#30363d")

        self.txt_log = scrolledtext.ScrolledText(
            log_card, 
            height=10, 
            font=("Consolas", 9), 
            bg="#070a11", 
            fg="#e6edf3", 
            relief=tk.FLAT, 
            insertbackground="#58a6ff"
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        # Cấu hình màu cho log
        self.txt_log.tag_configure("INFO", foreground="#58a6ff")
        self.txt_log.tag_configure("SUCCESS", foreground="#3fb950", font=("Consolas", 9, "bold"))
        self.txt_log.tag_configure("WARNING", foreground="#d29922")
        self.txt_log.tag_configure("ERROR", foreground="#f85149", font=("Consolas", 9, "bold"))
        self.txt_log.tag_configure("CMD", foreground="#8b949e")

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
            notify_info("Nhật ký", "Nhật ký hiện đang trống.", self.root)
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
                notify_success("Lưu thành công", f"Đã lưu nhật ký hoạt động tại:\n{filepath}", self.root)
            except Exception as e:
                notify_error("Lỗi lưu file", f"Không thể lưu file nhật ký:\n{e}", self.root)

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
                if hasattr(self, 'lbl_adb_badge'):
                    self.lbl_adb_badge.config(text="● ADB Sẵn sàng", fg="#3fb950")
            else:
                self.log("Cảnh báo: ADB trả về mã lỗi. Kiểm tra biến môi trường PATH.", "WARNING")
                if hasattr(self, 'lbl_adb_badge'):
                    self.lbl_adb_badge.config(text="● Lỗi ADB", fg="#d29922")
        except FileNotFoundError:
            self.log("LỖI: Không tìm thấy ADB trên máy tính!", "ERROR")
            if hasattr(self, 'lbl_adb_badge'):
                self.lbl_adb_badge.config(text="● Chưa có ADB", fg="#f85149")
            notify_warning("Cảnh báo ADB", "Không tìm thấy ADB trong hệ thống.\nHãy chắc chắn ADB đã được cài đặt hoặc đặt adb.exe vào thư mục tool.", self.root)

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
        self.lbl_uid_count.config(text=f" {len(uids)} UID ")

    def paste_from_clipboard(self):
        try:
            cb_text = self.root.clipboard_get()
            self.txt_uids.insert(tk.END, "\n" + cb_text.strip() + "\n")
            self._update_uid_count()
        except Exception:
            notify_info("Bộ nhớ tạm", "Clipboard trống hoặc không chứa văn bản.", self.root)

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
                notify_info("Kết quả quét ADB", "Không tìm thấy thiết bị nào đang kết nối.\nKiểm tra cáp kết nối và USB Debugging trên máy.", self.root)
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
            notify_warning("Thiếu thiết bị", "Vui lòng nhập hoặc quét ít nhất 1 UID/Serial thiết bị!", self.root)
            return

        wifi_ssid = None
        wifi_pass = None
        if self.var_connect_wifi.get():
            raw_wifi = self.ent_wifi.get().strip()
            if not raw_wifi:
                notify_warning("Sai định dạng Wi-Fi", "Vui lòng nhập thông tin Wi-Fi theo định dạng user|pass\n(Ví dụ: Aruba3.2|66668888)", self.root)
                return
            if "|" in raw_wifi:
                parts = raw_wifi.split("|", 1)
                wifi_ssid = parts[0].strip()
                wifi_pass = parts[1].strip()
            else:
                wifi_ssid = raw_wifi
                wifi_pass = ""

            if not wifi_ssid:
                notify_warning("Thiếu tên Wi-Fi", "Tên Wi-Fi (SSID) không được để trống!", self.root)
                return

        try:
            num_threads = int(self.spn_threads.get())
            if num_threads < 1:
                num_threads = 1
        except ValueError:
            num_threads = 10

        self.is_running = True
        self.stop_requested = False

        self.btn_start.config(state=tk.DISABLED, bg="#21262d", fg="#8b949e")
        self.btn_stop.config(state=tk.NORMAL, bg="#da3633", fg="#ffffff")
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
        self.btn_start.config(state=tk.NORMAL, bg="#238636", fg="#ffffff")
        self.btn_stop.config(state=tk.DISABLED, bg="#21262d", fg="#8b949e")
        self.btn_scan.config(state=tk.NORMAL)
        
        msg = f"Đã xử lý xong {total} thiết bị!\n- Thành công: {success}\n- Lỗi/Hủy: {fail}"
        if fail == 0:
            notify_success("Hoàn tất xử lý", msg, self.root)
        else:
            notify_warning("Hoàn tất có lỗi", msg, self.root)

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
        new_val = notify_input(
            "Cấu hình GitHub Repo",
            "Nhập địa chỉ repository GitHub dạng username/repo-name:\n(Ví dụ: duckiend3v/Fix_Wifi)",
            default_val=curr,
            parent=self.root
        )
        if new_val:
            new_val = new_val.strip().replace("https://github.com/", "").strip("/")
            if new_val:
                save_github_repo(new_val)
                self.log(f"Đã lưu GitHub Repo cập nhật: {new_val}", "SUCCESS")
                notify_success("Thành công", f"Đã cấu hình GitHub Repo:\n{new_val}", self.root)

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
                notify_info("Cập nhật Tool", f"Bạn đang sử dụng phiên bản mới nhất ({APP_VERSION})!\n\nGitHub Repo: {repo}", self.root)

    def _handle_update_error(self, err_msg, silent):
        self.btn_update.config(text="🔄 Kiểm tra Cập nhật", state=tk.NORMAL)
        if not silent:
            notify_warning("Kiểm tra Cập nhật", err_msg, self.root)

    def _show_update_modal(self, tag_name, release_name, body, assets, html_url):
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Cập nhật Fix Wifi - {tag_name}")
        dlg.configure(bg="#0d1117")
        dlg.transient(self.root)
        dlg.grab_set()

        ico_file = get_resource_path("icon.ico")
        if os.path.exists(ico_file):
            try:
                dlg.iconbitmap(ico_file)
            except Exception:
                pass

        content = tk.Frame(dlg, bg="#0d1117", padx=16, pady=14)
        content.pack(fill=tk.BOTH, expand=True)

        # Header banner
        hdr_banner = tk.Frame(content, bg="#161b22", highlightbackground="#238636", highlightthickness=1, padx=14, pady=12)
        hdr_banner.pack(fill=tk.X, pady=(0, 10))

        lbl_top = tk.Label(hdr_banner, text=f"🎉 PHÁT HIỆN BẢN CẬP NHẬT MỚI: {tag_name}", font=("Segoe UI", 12, "bold"), fg="#3fb950", bg="#161b22")
        lbl_top.pack(anchor=tk.W, pady=(0, 4))

        sub_info_frame = tk.Frame(hdr_banner, bg="#161b22")
        sub_info_frame.pack(anchor=tk.W, fill=tk.X)

        tk.Label(sub_info_frame, text=f"Bản hiện tại: {APP_VERSION}", font=("Segoe UI", 9), fg="#8b949e", bg="#161b22").pack(side=tk.LEFT)
        tk.Label(sub_info_frame, text=" ➔ ", font=("Segoe UI", 9, "bold"), fg="#58a6ff", bg="#161b22").pack(side=tk.LEFT)
        tk.Label(sub_info_frame, text=f" {tag_name} (KHUYÊN DÙNG) ", font=("Segoe UI", 9, "bold"), bg="#238636", fg="#ffffff", padx=6, pady=1).pack(side=tk.LEFT)

        if release_name and release_name != tag_name:
            tk.Label(hdr_banner, text=f"Tiêu đề: {release_name}", font=("Segoe UI", 9, "italic"), fg="#c9d1d9", bg="#161b22").pack(anchor=tk.W, pady=(4, 0))

        # Changelog card
        log_card = tk.Frame(content, bg="#161b22", highlightbackground="#30363d", highlightthickness=1, padx=12, pady=10)
        log_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        tk.Label(log_card, text="📝 Nội dung cập nhật & Cải tiến (Changelog):", font=("Segoe UI", 9, "bold"), fg="#58a6ff", bg="#161b22").pack(anchor=tk.W, pady=(0, 4))
        
        txt_changelog = scrolledtext.ScrolledText(log_card, height=8, font=("Consolas", 9), bg="#070a11", fg="#e6edf3", insertbackground="#58a6ff", relief=tk.FLAT, wrap=tk.WORD)
        txt_changelog.insert(tk.END, body if body.strip() else "Không có ghi chú thay đổi chi tiết.")
        txt_changelog.config(state=tk.DISABLED)
        txt_changelog.pack(fill=tk.BOTH, expand=True)

        lbl_dl_status = tk.Label(content, text="", font=("Segoe UI", 9, "italic"), fg="#58a6ff", bg="#0d1117")
        lbl_dl_status.pack(anchor=tk.W, pady=(0, 2))

        prog_dl = ttk.Progressbar(content, orient="horizontal", mode="determinate")
        prog_dl.pack(fill=tk.X, pady=(0, 10))

        btn_box = tk.Frame(content, bg="#0d1117")
        btn_box.pack(fill=tk.X)

        btn_do_update = tk.Button(
            btn_box, 
            text="⚡ CẬP NHẬT NGAY", 
            font=("Segoe UI", 10, "bold"),
            bg="#238636", 
            fg="#ffffff", 
            activebackground="#2ea043", 
            activeforeground="#ffffff",
            relief=tk.FLAT, 
            padx=18, 
            pady=7, 
            cursor="hand2"
        )
        btn_do_update.pack(side=tk.LEFT)
        make_hover_button(btn_do_update, "#238636", "#2ea043")

        btn_web = tk.Button(
            btn_box, 
            text="🌐 Xem trên GitHub", 
            font=("Segoe UI", 9),
            bg="#21262d", 
            fg="#c9d1d9", 
            activebackground="#30363d", 
            activeforeground="#ffffff",
            relief=tk.FLAT, 
            padx=12, 
            pady=7, 
            cursor="hand2",
            command=lambda: webbrowser.open(html_url)
        )
        btn_web.pack(side=tk.LEFT, padx=(8, 0))
        make_hover_button(btn_web, "#21262d", "#30363d")

        btn_close = tk.Button(
            btn_box, 
            text="✕ Để sau", 
            font=("Segoe UI", 9),
            bg="#21262d", 
            fg="#8b949e", 
            activebackground="#30363d", 
            activeforeground="#ffffff",
            relief=tk.FLAT, 
            padx=12, 
            pady=7, 
            cursor="hand2",
            command=dlg.destroy
        )
        btn_close.pack(side=tk.RIGHT)
        make_hover_button(btn_close, "#21262d", "#30363d")

        btn_do_update.config(command=lambda: self._execute_download_and_install(
            tag_name, assets, dlg, btn_do_update, btn_close, lbl_dl_status, prog_dl, html_url
        ))

        # Canh giữa cửa sổ theo ứng dụng chính
        dlg.update_idletasks()
        w = 600
        h = 500
        x = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
        dlg.geometry(f"{w}x{h}+{max(x, 30)}+{max(y, 30)}")

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
                notify_warning(
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

        btn_update.config(state=tk.DISABLED, bg="#30363d", text="⏳ Đang tải...")
        btn_close.config(state=tk.DISABLED)
        lbl_status.config(text=f"Đang chuẩn bị tải {file_name}...", fg="#58a6ff")

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
        lbl_status.config(text=f"Đang tải: {pct}% ({downloaded // (1024*1024):.1f} MB / {total_bytes // (1024*1024):.1f} MB)...", fg="#58a6ff")

    def _handle_dl_error(self, err_text, btn_update, btn_close, lbl_status, dlg):
        btn_update.config(state=tk.NORMAL, bg="#238636", text="⚡ CẬP NHẬT NGAY")
        btn_close.config(state=tk.NORMAL)
        lbl_status.config(text=f"Lỗi tải: {err_text}", fg="#f85149")
        notify_error("Lỗi tải cập nhật", f"Không thể tải file cập nhật:\n{err_text}", parent=dlg)

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
                notify_success("Cập nhật thành công", "Đã giải nén phiên bản mới thành công!\nVui lòng khởi động lại tool để áp dụng.", parent=dlg)
                dlg.destroy()
                return

            # 2. Nếu là file .EXE (chạy dạng đóng gói PyInstaller)
            if is_frozen:
                curr_exe = os.path.abspath(sys.executable)
                bat_path = os.path.join(app_dir, "apply_update.bat")
                pid = os.getpid()

                bat_content = f"""@echo off
chcp 65001 >nul
title Dang cap nhat Fix Wifi...
echo ========================================================
echo   DANG TIEN HANH NANG CAP FIX WIFI
echo   Vui long cho trong giay lat...
echo ========================================================
timeout /t 1 /nobreak >nul

:WAIT_LOOP
taskkill /F /PID {pid} >nul 2>&1
timeout /t 1 /nobreak >nul
move /Y "{temp_file}" "{curr_exe}" >nul 2>&1
if exist "{temp_file}" (
    echo Dang cho giai phong file cu de ghi de...
    timeout /t 1 /nobreak >nul
    goto WAIT_LOOP
)

echo [OK] Nang cap thanh cong! Dang khoi dong lai tool...
set _MEIPASS2=
set _MEIPASS=
set PYI_PARENT_PID=
timeout /t 1 /nobreak >nul
start "" "{curr_exe}"
timeout /t 2 /nobreak >nul
del "%~f0"
exit
"""
                with open(bat_path, "w", encoding="utf-8") as bf:
                    bf.write(bat_content)

                clean_env = {k: v for k, v in os.environ.items() if not k.startswith("_MEI") and not k.startswith("PYI_")}

                subprocess.Popen(
                    ["cmd.exe", "/c", bat_path], 
                    cwd=app_dir, 
                    env=clean_env, 
                    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                )
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
                notify_success("Thành công", "Đã cập nhật xong phiên bản mới! Ứng dụng sẽ tự khởi động lại.", parent=dlg)
                subprocess.Popen([sys.executable, target_py] + sys.argv[1:], cwd=app_dir)
                self.root.destroy()
                sys.exit(0)

        except Exception as e:
            notify_error("Lỗi áp dụng bản cập nhật", f"Không thể hoàn tất cập nhật:\n{e}", parent=dlg)


def main():
    try:
        root = tk.Tk()
        app = WifiFixerApp(root)
        root.mainloop()
    except Exception as e:
        print("[LỖI KHỞI CHẠY]:")
        traceback.print_exc()
        try:
            notify_error("Lỗi khởi động", f"Không thể mở ứng dụng:\n{e}\n\n{traceback.format_exc()}")
        except Exception:
            pass
        input("\nNhấn Enter để thoát...")


if __name__ == "__main__":
    main()
