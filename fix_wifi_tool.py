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


APP_VERSION = "v1.2.4b"
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


THEMES = {
    "Tokyo Night": {
        "name": "Tokyo Night",
        "bg": "#1a1b26",
        "card_bg": "#24283b",
        "card_border": "#414868",
        "header_bg": "#1f2335",
        "fg": "#c0caf5",
        "fg_muted": "#7aa2f7",
        "accent": "#7dcfff",
        "badge_bg": "#41a6b5",
        "badge_fg": "#15161e",
        "input_bg": "#16161e",
        "input_fg": "#7dcfff",
        "btn_primary_bg": "#73daca",
        "btn_primary_hover": "#41a6b5",
        "btn_primary_fg": "#15161e",
        "btn_secondary_bg": "#292e42",
        "btn_secondary_hover": "#3b4261",
        "btn_secondary_fg": "#c0caf5",
        "btn_action_bg": "#bb9af7",
        "btn_action_hover": "#7aa2f7",
        "btn_action_fg": "#15161e",
        "btn_stop_bg": "#292e42",
        "btn_stop_active": "#f7768e",
        "btn_stop_fg": "#9aa5ce",
        "log_bg": "#16161e",
        "log_fg": "#c0caf5",
        "log_info": "#7dcfff",
        "log_success": "#73daca",
        "log_warning": "#e0af68",
        "log_error": "#f7768e",
        "log_cmd": "#565f89",
        "status_ok": "#73daca",
        "status_warn": "#e0af68",
        "status_err": "#f7768e",
        "pb_bg": "#73daca",
        "pb_trough": "#16161e"
    },
    "Cyberpunk 2077": {
        "name": "Cyberpunk 2077",
        "bg": "#0c0d12",
        "card_bg": "#141721",
        "card_border": "#00f0ff",
        "header_bg": "#1a1e2b",
        "fg": "#fcee0a",
        "fg_muted": "#00f0ff",
        "accent": "#fcee0a",
        "badge_bg": "#fcee0a",
        "badge_fg": "#000000",
        "input_bg": "#07080b",
        "input_fg": "#00f0ff",
        "btn_primary_bg": "#fcee0a",
        "btn_primary_hover": "#ffe600",
        "btn_primary_fg": "#000000",
        "btn_secondary_bg": "#1e2333",
        "btn_secondary_hover": "#2a3147",
        "btn_secondary_fg": "#00f0ff",
        "btn_action_bg": "#00f0ff",
        "btn_action_hover": "#38f5ff",
        "btn_action_fg": "#000000",
        "btn_stop_bg": "#1e2333",
        "btn_stop_active": "#ff003c",
        "btn_stop_fg": "#ff003c",
        "log_bg": "#07080b",
        "log_fg": "#00f0ff",
        "log_info": "#00f0ff",
        "log_success": "#fcee0a",
        "log_warning": "#ff8800",
        "log_error": "#ff003c",
        "log_cmd": "#71798e",
        "status_ok": "#fcee0a",
        "status_warn": "#ff8800",
        "status_err": "#ff003c",
        "pb_bg": "#fcee0a",
        "pb_trough": "#07080b"
    },
    "Neon City": {
        "name": "Neon City",
        "bg": "#0d0417",
        "card_bg": "#19082e",
        "card_border": "#ff2a85",
        "header_bg": "#220b3f",
        "fg": "#f5e6ff",
        "fg_muted": "#05d9e8",
        "accent": "#ff2a85",
        "badge_bg": "#b026ff",
        "badge_fg": "#ffffff",
        "input_bg": "#090210",
        "input_fg": "#05d9e8",
        "btn_primary_bg": "#00ff9f",
        "btn_primary_hover": "#38ffb5",
        "btn_primary_fg": "#0d0417",
        "btn_secondary_bg": "#2c0e52",
        "btn_secondary_hover": "#3d1370",
        "btn_secondary_fg": "#05d9e8",
        "btn_action_bg": "#ff2a85",
        "btn_action_hover": "#ff4d9d",
        "btn_action_fg": "#ffffff",
        "btn_stop_bg": "#2c0e52",
        "btn_stop_active": "#ff2a85",
        "btn_stop_fg": "#ff2a85",
        "log_bg": "#090210",
        "log_fg": "#f5e6ff",
        "log_info": "#05d9e8",
        "log_success": "#00ff9f",
        "log_warning": "#ffd300",
        "log_error": "#ff2a85",
        "log_cmd": "#7b5e99",
        "status_ok": "#00ff9f",
        "status_warn": "#ffd300",
        "status_err": "#ff2a85",
        "pb_bg": "#ff2a85",
        "pb_trough": "#090210"
    },
    "Dark Slate": {
        "name": "Dark Slate",
        "bg": "#0d1117",
        "card_bg": "#161b22",
        "card_border": "#30363d",
        "header_bg": "#161b22",
        "fg": "#f0f6fc",
        "fg_muted": "#8b949e",
        "accent": "#58a6ff",
        "badge_bg": "#238636",
        "badge_fg": "#ffffff",
        "input_bg": "#090d13",
        "input_fg": "#58a6ff",
        "btn_primary_bg": "#238636",
        "btn_primary_hover": "#2ea043",
        "btn_primary_fg": "#ffffff",
        "btn_secondary_bg": "#21262d",
        "btn_secondary_hover": "#30363d",
        "btn_secondary_fg": "#c9d1d9",
        "btn_action_bg": "#1f6feb",
        "btn_action_hover": "#388bfd",
        "btn_action_fg": "#ffffff",
        "btn_stop_bg": "#21262d",
        "btn_stop_active": "#da3633",
        "btn_stop_fg": "#8b949e",
        "log_bg": "#070a11",
        "log_fg": "#e6edf3",
        "log_info": "#58a6ff",
        "log_success": "#3fb950",
        "log_warning": "#d29922",
        "log_error": "#f85149",
        "log_cmd": "#8b949e",
        "status_ok": "#3fb950",
        "status_warn": "#d29922",
        "status_err": "#f85149",
        "pb_bg": "#238636",
        "pb_trough": "#0d1117"
    }
}


def load_theme_preference():
    """Đọc cấu hình giao diện đã lưu (Tokyo Night, Cyberpunk 2077, Neon City, Dark Slate)"""
    cfg_file = os.path.join(get_app_dir(), "theme_config.json")
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                th = data.get("theme", "")
                if th in THEMES:
                    return th
        except Exception:
            pass
    return "Tokyo Night"


def save_theme_preference(theme_name):
    """Lưu cấu hình giao diện người dùng chọn vào theme_config.json"""
    cfg_file = os.path.join(get_app_dir(), "theme_config.json")
    try:
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump({"theme": theme_name}, f, indent=2)
    except Exception:
        pass


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
    btn._hover_cfg = (normal_bg, hover_bg, normal_fg, hover_fg)


class DarkDialog:
    """Hệ thống hộp thoại thông báo phong cách Cyber / Dark hiện đại, thay thế messagebox Windows cổ điển"""
    
    @classmethod
    def show(cls, parent, title, message, dialog_type="info", input_default=""):
        dlg = tk.Toplevel(parent) if parent else tk.Toplevel()
        dlg.title(title)

        # Lấy màu theo theme đang kích hoạt nếu có
        curr_theme = None
        if parent:
            if hasattr(parent, "curr_theme"):
                curr_theme = parent.curr_theme
            elif hasattr(parent, "master") and hasattr(parent.master, "curr_theme"):
                curr_theme = parent.master.curr_theme

        win_bg = curr_theme["bg"] if curr_theme else "#1a1b26"
        card_bg = curr_theme["card_bg"] if curr_theme else "#24283b"
        text_fg = curr_theme["fg"] if curr_theme else "#c0caf5"
        accent_color = curr_theme["accent"] if curr_theme else "#7dcfff"
        input_bg = curr_theme["input_bg"] if curr_theme else "#16161e"
        input_fg = curr_theme["input_fg"] if curr_theme else "#7dcfff"

        dlg.configure(bg=win_bg)
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
                "tag_bg": "#238636" if not curr_theme else curr_theme["status_ok"],
                "tag_fg": "#ffffff" if not curr_theme else curr_theme["btn_primary_fg"],
                "border": "#238636" if not curr_theme else curr_theme["status_ok"],
                "title_fg": "#3fb950" if not curr_theme else curr_theme["status_ok"]
            },
            "info": {
                "tag": "ℹ THÔNG BÁO",
                "tag_bg": accent_color,
                "tag_fg": "#ffffff" if not curr_theme else curr_theme["btn_primary_fg"],
                "border": accent_color,
                "title_fg": accent_color
            },
            "warning": {
                "tag": "⚠ CẢNH BÁO",
                "tag_bg": "#e0af68" if not curr_theme else curr_theme["status_warn"],
                "tag_fg": "#1a1b26",
                "border": "#e0af68" if not curr_theme else curr_theme["status_warn"],
                "title_fg": "#e0af68" if not curr_theme else curr_theme["status_warn"]
            },
            "error": {
                "tag": "✖ LỖI",
                "tag_bg": "#f7768e" if not curr_theme else curr_theme["status_err"],
                "tag_fg": "#ffffff",
                "border": "#f7768e" if not curr_theme else curr_theme["status_err"],
                "title_fg": "#f7768e" if not curr_theme else curr_theme["status_err"]
            },
            "confirm": {
                "tag": "? XÁC NHẬN",
                "tag_bg": accent_color,
                "tag_fg": "#ffffff" if not curr_theme else curr_theme["btn_primary_fg"],
                "border": accent_color,
                "title_fg": accent_color
            },
            "input": {
                "tag": "⚙ CẤU HÌNH",
                "tag_bg": accent_color,
                "tag_fg": "#ffffff" if not curr_theme else curr_theme["btn_primary_fg"],
                "border": accent_color,
                "title_fg": accent_color
            }
        }
        cfg = type_configs.get(dialog_type, type_configs["info"])
        res = {"value": None}

        # Khung viền sắc nét phong cách Cyber Dark
        frame = tk.Frame(dlg, bg=card_bg, highlightbackground=cfg["border"], highlightthickness=1, padx=18, pady=16)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Header: Tag badge + Title
        hdr = tk.Frame(frame, bg=card_bg)
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
            bg=card_bg
        )
        title_lbl.pack(side=tk.LEFT, anchor=tk.W)

        # Body: Message text
        msg_frame = tk.Frame(frame, bg=card_bg)
        msg_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 14))

        msg_lbl = tk.Label(
            msg_frame, 
            text=message, 
            font=("Segoe UI", 10), 
            fg=text_fg, 
            bg=card_bg, 
            justify=tk.LEFT, 
            wraplength=440
        )
        msg_lbl.pack(anchor=tk.W)

        ent = None
        if dialog_type == "input":
            ent_frame = tk.Frame(frame, bg=input_bg, highlightbackground=cfg["border"], highlightthickness=1, padx=6, pady=4)
            ent_frame.pack(fill=tk.X, pady=(0, 14))
            ent = tk.Entry(
                ent_frame, 
                font=("Consolas", 10), 
                bg=input_bg, 
                fg=input_fg, 
                insertbackground=accent_color, 
                relief=tk.FLAT
            )
            ent.insert(0, input_default)
            ent.select_range(0, tk.END)
            ent.pack(fill=tk.X)
            ent.focus_set()

        # Footer: Action Buttons
        btn_box = tk.Frame(frame, bg=card_bg)
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

        sec_bg = curr_theme["btn_secondary_bg"] if curr_theme else "#21262d"
        sec_hover = curr_theme["btn_secondary_hover"] if curr_theme else "#30363d"
        sec_fg = curr_theme["btn_secondary_fg"] if curr_theme else "#c9d1d9"
        pri_bg = curr_theme["btn_primary_bg"] if curr_theme else "#238636"
        pri_hover = curr_theme["btn_primary_hover"] if curr_theme else "#2ea043"
        pri_fg = curr_theme["btn_primary_fg"] if curr_theme else "#ffffff"

        if dialog_type == "confirm":
            b_ok = tk.Button(
                btn_box, text="✓ Đồng ý", font=("Segoe UI", 9, "bold"),
                bg=pri_bg, fg=pri_fg, relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                command=on_ok
            )
            b_ok.pack(side=tk.RIGHT, padx=(6, 0))
            b_cancel = tk.Button(
                btn_box, text="✕ Hủy bỏ", font=("Segoe UI", 9),
                bg=sec_bg, fg=sec_fg, relief=tk.FLAT, padx=12, pady=5, cursor="hand2",
                command=on_cancel
            )
            b_cancel.pack(side=tk.RIGHT)
            make_hover_button(b_ok, pri_bg, pri_hover, pri_fg, pri_fg)
            make_hover_button(b_cancel, sec_bg, sec_hover, sec_fg, text_fg)
        elif dialog_type == "input":
            b_ok = tk.Button(
                btn_box, text="💾 Lưu cấu hình", font=("Segoe UI", 9, "bold"),
                bg=pri_bg, fg=pri_fg, relief=tk.FLAT, padx=14, pady=5, cursor="hand2",
                command=on_ok
            )
            b_ok.pack(side=tk.RIGHT, padx=(6, 0))
            b_cancel = tk.Button(
                btn_box, text="✕ Hủy bỏ", font=("Segoe UI", 9),
                bg=sec_bg, fg=sec_fg, relief=tk.FLAT, padx=12, pady=5, cursor="hand2",
                command=on_cancel
            )
            b_cancel.pack(side=tk.RIGHT)
            make_hover_button(b_ok, pri_bg, pri_hover, pri_fg, pri_fg)
            make_hover_button(b_cancel, sec_bg, sec_hover, sec_fg, text_fg)
        else:
            btn_color = pri_bg if dialog_type == "success" else ("#f7768e" if dialog_type == "error" else ("#e0af68" if dialog_type == "warning" else accent_color))
            btn_hover = pri_hover if dialog_type == "success" else ("#ff9e64" if dialog_type == "error" else ("#ffc777" if dialog_type == "warning" else pri_hover))
            btn_fg = "#1a1b26" if dialog_type in ("warning", "success", "info") else "#ffffff"
            
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
        self.root.geometry("920x760")
        self.root.minsize(760, 620)
        
        # Thiết lập Icon cho ứng dụng
        self._setup_app_icon()
        
        # Đường dẫn adb
        self.adb_bin = find_adb_executable()

        # Biến trạng thái
        self.is_running = False
        self.stop_requested = False
        self.executor = None
        
        # Tải cấu hình Theme (Tokyo Night, Cyberpunk 2077, Neon City, Dark Slate)
        self.curr_theme_name = load_theme_preference()
        self.curr_theme = THEMES.get(self.curr_theme_name, THEMES["Tokyo Night"])
        self.root.curr_theme = self.curr_theme
        
        # Cấu hình giao diện
        self._setup_styles()
        self._build_ui()
        self.apply_theme(self.curr_theme_name)
        self._check_adb_status()
        
        # Lắng nghe sự kiện co giãn cửa sổ để tự căn chỉnh responsive
        self.root.bind("<Configure>", self._on_window_resize)
        
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

    def _on_window_resize(self, event=None):
        """Tự động điều chỉnh độ ngắt dòng khi người dùng thu nhỏ / phóng to cửa sổ tool"""
        if event and event.widget == self.root:
            if hasattr(self, "sub_lbl"):
                cur_w = self.root.winfo_width()
                wrap_w = max(260, cur_w - 420)
                self.sub_lbl.config(wraplength=wrap_w)

    def _on_theme_change(self, event=None):
        """Xử lý khi người dùng chọn giao diện mới từ dropdown"""
        selected = self.cb_theme.get().strip()
        if selected in THEMES:
            self.apply_theme(selected)
            self.log(f"Đã chuyển sang phong cách giao diện: {selected}", "INFO")

    def apply_theme(self, theme_name):
        """Thay đổi toàn bộ màu sắc, hiệu ứng, widget trên toàn bộ ứng dụng sang theme mới"""
        if theme_name not in THEMES:
            theme_name = "Tokyo Night"
        self.curr_theme_name = theme_name
        self.curr_theme = THEMES[theme_name]
        self.root.curr_theme = self.curr_theme
        t = self.curr_theme
        save_theme_preference(theme_name)

        # 1. Cửa sổ và khung chứa chính
        self.root.configure(bg=t["bg"])
        if hasattr(self, "main_container"):
            self.main_container.configure(bg=t["bg"])

        # 2. Các Card
        for card in getattr(self, "card_frames", []):
            try:
                card.configure(bg=t["card_bg"], highlightbackground=t["card_border"])
            except Exception:
                pass

        for f in getattr(self, "inner_frames", []):
            try:
                f.configure(bg=t["card_bg"])
            except Exception:
                pass

        if hasattr(self, "wifi_conn_frame"):
            self.wifi_conn_frame.configure(bg=t["bg"], highlightbackground=t["card_border"])

        # 3. Các Nhãn & Tiêu đề
        if hasattr(self, "logo_lbl"):
            self.logo_lbl.configure(bg=t["card_bg"])
        if hasattr(self, "title_lbl"):
            self.title_lbl.configure(bg=t["card_bg"], fg=t["accent"])
        if hasattr(self, "ver_badge"):
            self.ver_badge.configure(bg=t["badge_bg"], fg=t["badge_fg"])
        if hasattr(self, "sub_lbl"):
            self.sub_lbl.configure(bg=t["card_bg"], fg=t["fg_muted"])
        if hasattr(self, "lbl_theme_icon"):
            self.lbl_theme_icon.configure(bg=t["card_bg"], fg=t["accent"])
        if hasattr(self, "lbl_uid_title"):
            self.lbl_uid_title.configure(bg=t["card_bg"], fg=t["accent"])
        if hasattr(self, "lbl_uid_count"):
            self.lbl_uid_count.configure(bg=t["btn_secondary_bg"], fg=t["status_ok"])
        if hasattr(self, "lbl_opt_title"):
            self.lbl_opt_title.configure(bg=t["card_bg"], fg=t["accent"])
        if hasattr(self, "lbl_wifi_hint"):
            self.lbl_wifi_hint.configure(bg=t["bg"], fg=t["fg_muted"])
        if hasattr(self, "lbl_threads"):
            self.lbl_threads.configure(bg=t["card_bg"], fg=t["fg"])
        if hasattr(self, "lbl_threads_hint"):
            self.lbl_threads_hint.configure(bg=t["card_bg"], fg=t["fg_muted"])
        if hasattr(self, "lbl_status"):
            st_color = t["status_ok"] if not self.is_running else t["status_warn"]
            self.lbl_status.configure(bg=t["card_bg"], fg=st_color)
        if hasattr(self, "lbl_log_title"):
            self.lbl_log_title.configure(bg=t["card_bg"], fg=t["accent"])
        if hasattr(self, "lbl_adb_badge"):
            cur_adb_text = self.lbl_adb_badge.cget("text")
            if "Sẵn sàng" in cur_adb_text:
                self.lbl_adb_badge.configure(bg=t["card_bg"], fg=t["status_ok"])
            elif "Chưa có" in cur_adb_text or "Lỗi" in cur_adb_text:
                self.lbl_adb_badge.configure(bg=t["card_bg"], fg=t["status_err"])
            else:
                self.lbl_adb_badge.configure(bg=t["card_bg"], fg=t["fg_muted"])

        # 4. Các nút bấm (cập nhật bảng màu hover tương ứng)
        if hasattr(self, "btn_update"):
            make_hover_button(self.btn_update, t["btn_primary_bg"], t["btn_primary_hover"], t["btn_primary_fg"], t["btn_primary_fg"])
        if hasattr(self, "btn_repo_cfg"):
            make_hover_button(self.btn_repo_cfg, t["btn_secondary_bg"], t["btn_secondary_hover"], t["btn_secondary_fg"], t["fg"])
        if hasattr(self, "btn_scan"):
            make_hover_button(self.btn_scan, t["btn_action_bg"], t["btn_action_hover"], t["btn_action_fg"], t["btn_action_fg"])
        if hasattr(self, "btn_paste"):
            make_hover_button(self.btn_paste, t["btn_secondary_bg"], t["btn_secondary_hover"], t["btn_secondary_fg"], t["fg"])
        if hasattr(self, "btn_clear"):
            make_hover_button(self.btn_clear, t["btn_secondary_bg"], t["btn_secondary_hover"], t["btn_secondary_fg"], t["fg"])
        if hasattr(self, "btn_start"):
            if not self.is_running:
                make_hover_button(self.btn_start, t["btn_primary_bg"], t["btn_primary_hover"], t["btn_primary_fg"], t["btn_primary_fg"])
            else:
                self.btn_start.configure(bg=t["btn_secondary_bg"], fg=t["fg_muted"])
        if hasattr(self, "btn_stop"):
            if self.is_running:
                make_hover_button(self.btn_stop, t["status_err"], t["btn_stop_active"], "#ffffff", "#ffffff")
            else:
                self.btn_stop.configure(bg=t["btn_secondary_bg"], fg=t["btn_stop_fg"])
        if hasattr(self, "btn_clr_log"):
            make_hover_button(self.btn_clr_log, t["btn_secondary_bg"], t["btn_secondary_hover"], t["btn_secondary_fg"], t["fg"])
        if hasattr(self, "btn_sav_log"):
            make_hover_button(self.btn_sav_log, t["btn_secondary_bg"], t["btn_secondary_hover"], t["btn_secondary_fg"], t["fg"])

        # 5. Checkbuttons
        for cb in getattr(self, "checkbuttons", []):
            try:
                cb.configure(
                    bg=t["card_bg"], 
                    fg=t["fg"], 
                    selectcolor=t["input_bg"], 
                    activebackground=t["card_bg"], 
                    activeforeground=t["accent"]
                )
            except Exception:
                pass

        if hasattr(self, "cb7"):
            self.cb7.configure(
                bg=t["bg"], 
                fg=t["accent"], 
                selectcolor=t["card_bg"], 
                activebackground=t["bg"], 
                activeforeground=t["accent"]
            )

        # 6. Ô nhập liệu Text / Entry
        if hasattr(self, "txt_uids"):
            self.txt_uids.configure(
                bg=t["input_bg"], 
                fg=t["input_fg"], 
                insertbackground=t["accent"], 
                selectbackground=t["btn_action_bg"]
            )

        if hasattr(self, "ent_wifi"):
            self.ent_wifi.configure(
                bg=t["input_bg"], 
                fg=t["input_fg"], 
                insertbackground=t["accent"]
            )

        # 7. Ô Terminal log & các thẻ màu
        if hasattr(self, "txt_log"):
            self.txt_log.configure(
                bg=t["log_bg"], 
                fg=t["log_fg"], 
                insertbackground=t["accent"]
            )
            self.txt_log.tag_configure("INFO", foreground=t["log_info"])
            self.txt_log.tag_configure("SUCCESS", foreground=t["log_success"])
            self.txt_log.tag_configure("WARNING", foreground=t["log_warning"])
            self.txt_log.tag_configure("ERROR", foreground=t["log_error"])
            self.txt_log.tag_configure("CMD", foreground=t["log_cmd"])

        # 8. TTK Styles
        try:
            self.style.configure(
                "TProgressbar", 
                thickness=8, 
                troughcolor=t["pb_trough"], 
                background=t["pb_bg"], 
                bordercolor=t["card_border"], 
                lightcolor=t["pb_bg"], 
                darkcolor=t["pb_bg"]
            )
        except Exception:
            pass

    def _setup_styles(self):
        t = self.curr_theme
        self.root.configure(bg=t["bg"])
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure(".", background=t["bg"], foreground=t["fg"])
        self.style.configure("TFrame", background=t["bg"])
        self.style.configure("Card.TFrame", background=t["card_bg"])
        self.style.configure("TLabel", background=t["bg"], foreground=t["fg"], font=("Segoe UI", 10))
        self.style.configure("Card.TLabel", background=t["card_bg"], foreground=t["fg"], font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", background=t["card_bg"], font=("Segoe UI", 15, "bold"), foreground=t["accent"])
        self.style.configure("SubHeader.TLabel", background=t["card_bg"], font=("Segoe UI", 9), foreground=t["fg_muted"])
        self.style.configure("CardHeader.TLabel", background=t["card_bg"], font=("Segoe UI", 10, "bold"), foreground=t["accent"])
        
        self.style.configure(
            "TProgressbar", 
            thickness=8, 
            troughcolor=t["pb_trough"], 
            background=t["pb_bg"], 
            bordercolor=t["card_border"], 
            lightcolor=t["pb_bg"], 
            darkcolor=t["pb_bg"]
        )

    def _build_ui(self):
        t = self.curr_theme
        self.card_frames = []
        self.inner_frames = []
        self.checkbuttons = []

        self.main_container = tk.Frame(self.root, bg=t["bg"], padx=12, pady=10)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # 1. HEADER CARD (Banner công cụ & Cụm chức năng góc phải)
        self.header_card = tk.Frame(self.main_container, bg=t["card_bg"], highlightbackground=t["card_border"], highlightthickness=1, padx=12, pady=10)
        self.header_card.pack(fill=tk.X, pady=(0, 8))
        self.card_frames.append(self.header_card)

        # CỤM BÊN PHẢI (Pack TRƯỚC để luôn hiển thị 100%, không bao giờ bị đè hay tràn khi co dãn cửa sổ)
        self.header_right = tk.Frame(self.header_card, bg=t["card_bg"])
        self.header_right.pack(side=tk.RIGHT, anchor=tk.E, padx=(10, 0))
        self.inner_frames.append(self.header_right)

        # Hộp chọn Theme
        self.theme_box = tk.Frame(self.header_right, bg=t["card_bg"])
        self.theme_box.pack(side=tk.LEFT, padx=(0, 8))
        self.inner_frames.append(self.theme_box)

        self.lbl_theme_icon = tk.Label(self.theme_box, text="🎨 Giao diện:", font=("Segoe UI", 9, "bold"), fg=t["accent"], bg=t["card_bg"])
        self.lbl_theme_icon.pack(side=tk.LEFT, padx=(0, 4))

        self.cb_theme = ttk.Combobox(
            self.theme_box,
            values=list(THEMES.keys()),
            state="readonly",
            width=13,
            font=("Segoe UI", 9)
        )
        self.cb_theme.set(self.curr_theme_name)
        self.cb_theme.bind("<<ComboboxSelected>>", self._on_theme_change)
        self.cb_theme.pack(side=tk.LEFT)

        self.btn_update = tk.Button(
            self.header_right, 
            text="🔄 Cập nhật", 
            font=("Segoe UI", 9, "bold"), 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=10, 
            pady=4,
            command=lambda: self.check_github_update(silent=False)
        )
        self.btn_update.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_repo_cfg = tk.Button(
            self.header_right, 
            text="⚙ Repo", 
            font=("Segoe UI", 9), 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=8, 
            pady=4, 
            command=self.configure_repo
        )
        self.btn_repo_cfg.pack(side=tk.LEFT)

        # CỤM BÊN TRÁI (Logo, Tên Tool, Version, ADB Status và Phụ đề)
        self.header_left = tk.Frame(self.header_card, bg=t["card_bg"])
        self.header_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.inner_frames.append(self.header_left)

        # Logo phát sáng
        logo_path = get_resource_path("icon_48.png")
        if not os.path.exists(logo_path):
            logo_path = get_resource_path("icon.png")
            
        if os.path.exists(logo_path):
            try:
                self._logo_img = tk.PhotoImage(file=logo_path)
                self.logo_lbl = tk.Label(self.header_left, image=self._logo_img, bg=t["card_bg"])
                self.logo_lbl.pack(side=tk.LEFT, padx=(0, 10))
            except Exception:
                pass

        self.header_text_frame = tk.Frame(self.header_left, bg=t["card_bg"])
        self.header_text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.inner_frames.append(self.header_text_frame)

        self.title_row = tk.Frame(self.header_text_frame, bg=t["card_bg"])
        self.title_row.pack(anchor=tk.W, fill=tk.X)
        self.inner_frames.append(self.title_row)

        self.title_lbl = tk.Label(self.title_row, text="FIX WIFI", font=("Segoe UI", 15, "bold"), fg=t["accent"], bg=t["card_bg"])
        self.title_lbl.pack(side=tk.LEFT)

        self.ver_badge = tk.Label(
            self.title_row, 
            text=f" {APP_VERSION} ", 
            font=("Segoe UI", 9, "bold"), 
            bg=t["badge_bg"], 
            fg=t["badge_fg"], 
            padx=6, 
            pady=1
        )
        self.ver_badge.pack(side=tk.LEFT, padx=(8, 0))

        # Đặt trạng thái ADB ngay cạnh tiêu đề phiên bản
        self.lbl_adb_badge = tk.Label(
            self.title_row, 
            text="● ADB: Đang quét...", 
            font=("Segoe UI", 9, "bold"), 
            fg=t["fg_muted"], 
            bg=t["card_bg"],
            padx=6
        )
        self.lbl_adb_badge.pack(side=tk.LEFT, padx=(8, 0))

        self.sub_lbl = tk.Label(
            self.header_text_frame, 
            text="Gỡ lỗi kẹt Proxy, clear College Proxy, reset Wi-Fi & kết nối tự động qua ADBJoinWiFi.", 
            font=("Segoe UI", 9), 
            fg=t["fg_muted"], 
            bg=t["card_bg"],
            anchor=tk.W,
            justify=tk.LEFT
        )
        self.sub_lbl.pack(anchor=tk.W, fill=tk.X, pady=(2, 0))

        # 2. KHUNG NHẬP DANH SÁCH UID
        self.uid_card = tk.Frame(self.main_container, bg=t["card_bg"], highlightbackground=t["card_border"], highlightthickness=1, padx=10, pady=8)
        self.uid_card.pack(fill=tk.BOTH, expand=False, pady=(0, 8))
        self.card_frames.append(self.uid_card)

        self.btn_row = tk.Frame(self.uid_card, bg=t["card_bg"])
        self.btn_row.pack(fill=tk.X, pady=(0, 6))
        self.inner_frames.append(self.btn_row)

        # Số lượng UID bên phải (pack trước)
        self.lbl_uid_count = tk.Label(
            self.btn_row, 
            text=" 0 UID ", 
            font=("Segoe UI", 9, "bold"), 
            bg=t["btn_secondary_bg"], 
            fg=t["status_ok"], 
            padx=8, 
            pady=2
        )
        self.lbl_uid_count.pack(side=tk.RIGHT, padx=2)

        self.lbl_uid_title = tk.Label(self.btn_row, text="📱 Thiết Bị Android (UID / Serial):", font=("Segoe UI", 10, "bold"), fg=t["accent"], bg=t["card_bg"])
        self.lbl_uid_title.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_scan = tk.Button(
            self.btn_row, 
            text="🔍 Quét ADB", 
            font=("Segoe UI", 9, "bold"), 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=8, 
            pady=3,
            command=self.scan_adb_devices
        )
        self.btn_scan.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_paste = tk.Button(
            self.btn_row, 
            text="📋 Dán Clipboard", 
            font=("Segoe UI", 9), 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=8, 
            pady=3,
            command=self.paste_from_clipboard
        )
        self.btn_paste.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_clear = tk.Button(
            self.btn_row, 
            text="🗑 Xóa ô", 
            font=("Segoe UI", 9), 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=8, 
            pady=3,
            command=self.clear_uids
        )
        self.btn_clear.pack(side=tk.LEFT, padx=(0, 5))

        # Ô Text nhập UIDs
        self.txt_uids = scrolledtext.ScrolledText(
            self.uid_card, 
            height=4, 
            font=("Consolas", 10), 
            wrap=tk.WORD, 
            bg=t["input_bg"], 
            fg=t["input_fg"], 
            insertbackground=t["accent"], 
            selectbackground=t["btn_action_bg"], 
            relief=tk.FLAT
        )
        self.txt_uids.pack(fill=tk.BOTH, expand=True)
        self.txt_uids.bind("<KeyRelease>", self._update_uid_count)

        # 3. TÙY CHỌN GỠ LỖI & KẾT NỐI WI-FI MỚI
        self.opt_card = tk.Frame(self.main_container, bg=t["card_bg"], highlightbackground=t["card_border"], highlightthickness=1, padx=10, pady=8)
        self.opt_card.pack(fill=tk.X, pady=(0, 8))
        self.card_frames.append(self.opt_card)

        self.lbl_opt_title = tk.Label(self.opt_card, text="⚡ Các Bước Xử Lý Gỡ Lỗi & Kết Nối Wi-Fi:", font=("Segoe UI", 10, "bold"), fg=t["accent"], bg=t["card_bg"])
        self.lbl_opt_title.pack(anchor=tk.W, pady=(0, 6))

        self.cb_grid = tk.Frame(self.opt_card, bg=t["card_bg"])
        self.cb_grid.pack(fill=tk.X)
        self.inner_frames.append(self.cb_grid)

        self.var_clear_proxy = tk.BooleanVar(value=True)
        self.var_clear_college = tk.BooleanVar(value=True)
        self.var_forget_wifi = tk.BooleanVar(value=True)
        self.var_stop_app = tk.BooleanVar(value=True)
        self.var_disable_wifi = tk.BooleanVar(value=True)
        self.var_enable_wifi = tk.BooleanVar(value=True)

        cb_style = {
            "bg": t["card_bg"], 
            "fg": t["fg"], 
            "selectcolor": t["input_bg"], 
            "activebackground": t["card_bg"], 
            "activeforeground": t["accent"], 
            "font": ("Segoe UI", 9)
        }

        self.cb1 = tk.Checkbutton(self.cb_grid, text="1. Xóa sạch HTTP Proxy (settings delete proxy)", variable=self.var_clear_proxy, **cb_style)
        self.cb1.grid(row=0, column=0, sticky=tk.W, pady=2, padx=4)

        self.cb2 = tk.Checkbutton(self.cb_grid, text="2. Xóa dữ liệu app College Proxy (pm clear & stop)", variable=self.var_clear_college, **cb_style)
        self.cb2.grid(row=0, column=1, sticky=tk.W, pady=2, padx=15)

        self.cb3 = tk.Checkbutton(self.cb_grid, text="3. Quên toàn bộ Wi-Fi cũ (forget-network 0..15)", variable=self.var_forget_wifi, **cb_style)
        self.cb3.grid(row=1, column=0, sticky=tk.W, pady=2, padx=4)

        self.cb4 = tk.Checkbutton(self.cb_grid, text="4. Tắt & Ngắt app ADBJoinWiFi cũ", variable=self.var_stop_app, **cb_style)
        self.cb4.grid(row=1, column=1, sticky=tk.W, pady=2, padx=15)

        self.cb5 = tk.Checkbutton(self.cb_grid, text="5. Tắt Wi-Fi (svc wifi disable)", variable=self.var_disable_wifi, **cb_style)
        self.cb5.grid(row=2, column=0, sticky=tk.W, pady=2, padx=4)

        self.cb6 = tk.Checkbutton(self.cb_grid, text="6. Tự động BẬT LẠI Wi-Fi (svc wifi enable)", variable=self.var_enable_wifi, command=self._on_enable_wifi_toggle, **cb_style)
        self.cb6.grid(row=2, column=1, sticky=tk.W, pady=2, padx=15)

        self.checkbuttons = [self.cb1, self.cb2, self.cb3, self.cb4, self.cb5, self.cb6]

        # Bước 7: Khung kết nối Wi-Fi mới
        self.var_connect_wifi = tk.BooleanVar(value=True)
        self.wifi_conn_frame = tk.Frame(self.opt_card, bg=t["bg"], highlightbackground=t["card_border"], highlightthickness=1, padx=8, pady=6)
        self.wifi_conn_frame.pack(fill=tk.X, pady=(6, 4))

        self.cb7 = tk.Checkbutton(
            self.wifi_conn_frame, 
            text="7. Kết nối lại Wi-Fi mới qua ADBJoinWiFi:", 
            variable=self.var_connect_wifi,
            command=self._on_connect_wifi_toggle,
            bg=t["bg"], fg=t["accent"], selectcolor=t["card_bg"], activebackground=t["bg"], activeforeground=t["accent"], font=("Segoe UI", 9, "bold")
        )
        self.cb7.pack(side=tk.LEFT, padx=(0, 6))

        self.ent_wifi = tk.Entry(
            self.wifi_conn_frame, 
            width=28, 
            font=("Consolas", 10, "bold"), 
            bg=t["input_bg"], 
            fg=t["input_fg"], 
            insertbackground=t["accent"], 
            relief=tk.FLAT
        )
        self.ent_wifi.insert(0, "Aruba3.2|66668888")
        self.ent_wifi.pack(side=tk.LEFT, padx=(0, 8), ipady=3)

        self.lbl_wifi_hint = tk.Label(self.wifi_conn_frame, text="(Định dạng: Tên_Wifi|Mật_khẩu)", font=("Segoe UI", 9, "italic"), fg=t["fg_muted"], bg=t["bg"])
        self.lbl_wifi_hint.pack(side=tk.LEFT)

        # Cấu hình đa luồng
        self.thread_frame = tk.Frame(self.opt_card, bg=t["card_bg"])
        self.thread_frame.pack(fill=tk.X, pady=(4, 0))
        self.inner_frames.append(self.thread_frame)
        
        self.lbl_threads = tk.Label(self.thread_frame, text="⚡ Số luồng xử lý song song (Threads):", font=("Segoe UI", 9), fg=t["fg"], bg=t["card_bg"])
        self.lbl_threads.pack(side=tk.LEFT, padx=(0, 5))

        self.spn_threads = ttk.Spinbox(self.thread_frame, from_=1, to=50, width=5)
        self.spn_threads.set(10)
        self.spn_threads.pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_threads_hint = tk.Label(self.thread_frame, text="(Xử lý đồng thời 50-100 máy trong vài giây)", font=("Segoe UI", 9, "italic"), fg=t["fg_muted"], bg=t["card_bg"])
        self.lbl_threads_hint.pack(side=tk.LEFT)

        # 4. ĐIỀU KHIỂN & TIẾN TRÌNH
        self.ctl_card = tk.Frame(self.main_container, bg=t["card_bg"], highlightbackground=t["card_border"], highlightthickness=1, padx=10, pady=8)
        self.ctl_card.pack(fill=tk.X, pady=(0, 8))
        self.card_frames.append(self.ctl_card)

        # Trạng thái góc phải (pack trước)
        self.lbl_status = tk.Label(self.ctl_card, text="● Sẵn sàng...", font=("Segoe UI", 10, "bold"), fg=t["status_ok"], bg=t["card_bg"])
        self.lbl_status.pack(side=tk.RIGHT, padx=6)

        self.ctl_left = tk.Frame(self.ctl_card, bg=t["card_bg"])
        self.ctl_left.pack(side=tk.LEFT)
        self.inner_frames.append(self.ctl_left)

        self.btn_start = tk.Button(
            self.ctl_left, 
            text="▶ BẮT ĐẦU GỠ LỖI & SỬA WI-FI", 
            font=("Segoe UI", 11, "bold"), 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=18, 
            pady=8, 
            command=self.start_fixing
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_stop = tk.Button(
            self.ctl_left, 
            text="⏹ DỪNG LẠI", 
            font=("Segoe UI", 11, "bold"), 
            relief=tk.FLAT, 
            padx=14, 
            pady=8, 
            state=tk.DISABLED, 
            command=self.stop_fixing
        )
        self.btn_stop.pack(side=tk.LEFT)

        # Thanh tiến trình
        self.progress_bar = ttk.Progressbar(self.main_container, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        # 5. NHẬT KÝ / LOG TERMINAL
        self.log_card = tk.Frame(self.main_container, bg=t["card_bg"], highlightbackground=t["card_border"], highlightthickness=1, padx=10, pady=8)
        self.log_card.pack(fill=tk.BOTH, expand=True)
        self.card_frames.append(self.log_card)

        self.log_btn_row = tk.Frame(self.log_card, bg=t["card_bg"])
        self.log_btn_row.pack(fill=tk.X, pady=(0, 4))
        self.inner_frames.append(self.log_btn_row)

        # Nút Lưu và Xóa bên phải (pack trước)
        self.btn_sav_log = tk.Button(
            self.log_btn_row, 
            text="💾 Lưu Log", 
            font=("Segoe UI", 8), 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=8, 
            pady=2, 
            command=self.save_log_file
        )
        self.btn_sav_log.pack(side=tk.RIGHT, padx=(4, 0))

        self.btn_clr_log = tk.Button(
            self.log_btn_row, 
            text="🧹 Xóa Log", 
            font=("Segoe UI", 8), 
            relief=tk.FLAT, 
            cursor="hand2", 
            padx=8, 
            pady=2, 
            command=self.clear_log
        )
        self.btn_clr_log.pack(side=tk.RIGHT)

        self.lbl_log_title = tk.Label(self.log_btn_row, text="📜 Nhật Ký Hoạt Động (Live Terminal):", font=("Segoe UI", 10, "bold"), fg=t["accent"], bg=t["card_bg"])
        self.lbl_log_title.pack(side=tk.LEFT)

        self.txt_log = scrolledtext.ScrolledText(
            self.log_card, 
            height=10, 
            font=("Consolas", 9), 
            bg=t["log_bg"], 
            fg=t["log_fg"], 
            relief=tk.FLAT, 
            insertbackground=t["accent"]
        )
        self.txt_log.pack(fill=tk.BOTH, expand=True)

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
                    self.lbl_adb_badge.config(text="● ADB Sẵn sàng", fg=self.curr_theme["status_ok"])
            else:
                self.log("Cảnh báo: ADB trả về mã lỗi. Kiểm tra biến môi trường PATH.", "WARNING")
                if hasattr(self, 'lbl_adb_badge'):
                    self.lbl_adb_badge.config(text="● Lỗi ADB", fg=self.curr_theme["status_warn"])
        except FileNotFoundError:
            self.log("LỖI: Không tìm thấy ADB trên máy tính!", "ERROR")
            if hasattr(self, 'lbl_adb_badge'):
                self.lbl_adb_badge.config(text="● Chưa có ADB", fg=self.curr_theme["status_err"])
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

        self.btn_start.config(state=tk.DISABLED, bg=self.curr_theme["btn_secondary_bg"], fg=self.curr_theme["fg_muted"])
        self.btn_stop.config(state=tk.NORMAL, bg=self.curr_theme["status_err"], fg="#ffffff")
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
        self.btn_start.config(state=tk.NORMAL, bg=self.curr_theme["btn_primary_bg"], fg=self.curr_theme["btn_primary_fg"])
        self.btn_stop.config(state=tk.DISABLED, bg=self.curr_theme["btn_secondary_bg"], fg=self.curr_theme["btn_stop_fg"])
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
        self.btn_update.config(text="⏳ Kiểm tra...", state=tk.DISABLED)

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
        self.btn_update.config(text="🔄 Cập nhật", state=tk.NORMAL)
        if is_newer_version(tag_name, APP_VERSION):
            self.log(f"Phát hiện bản cập nhật mới: {tag_name} (Hiện tại: {APP_VERSION})", "INFO")
            self._show_update_modal(tag_name, release_name, body, assets, html_url)
        else:
            self.log(f"Bạn đang dùng phiên bản mới nhất ({APP_VERSION}).", "INFO")
            if not silent:
                notify_info("Cập nhật Tool", f"Bạn đang sử dụng phiên bản mới nhất ({APP_VERSION})!\n\nGitHub Repo: {repo}", self.root)

    def _handle_update_error(self, err_msg, silent):
        self.btn_update.config(text="🔄 Cập nhật", state=tk.NORMAL)
        if not silent:
            notify_warning("Kiểm tra Cập nhật", err_msg, self.root)

    def _show_update_modal(self, tag_name, release_name, body, assets, html_url):
        t = self.curr_theme
        dlg = tk.Toplevel(self.root)
        dlg.title(f"Cập nhật Fix Wifi - {tag_name}")
        dlg.configure(bg=t["bg"])
        dlg.transient(self.root)
        dlg.grab_set()

        ico_file = get_resource_path("icon.ico")
        if os.path.exists(ico_file):
            try:
                dlg.iconbitmap(ico_file)
            except Exception:
                pass

        content = tk.Frame(dlg, bg=t["bg"], padx=16, pady=14)
        content.pack(fill=tk.BOTH, expand=True)

        # Header banner
        hdr_banner = tk.Frame(content, bg=t["card_bg"], highlightbackground=t["card_border"], highlightthickness=1, padx=14, pady=12)
        hdr_banner.pack(fill=tk.X, pady=(0, 10))

        lbl_top = tk.Label(hdr_banner, text=f"🎉 PHÁT HIỆN BẢN CẬP NHẬT MỚI: {tag_name}", font=("Segoe UI", 12, "bold"), fg=t["accent"], bg=t["card_bg"])
        lbl_top.pack(anchor=tk.W, pady=(0, 4))

        sub_info_frame = tk.Frame(hdr_banner, bg=t["card_bg"])
        sub_info_frame.pack(anchor=tk.W, fill=tk.X)

        tk.Label(sub_info_frame, text=f"Bản hiện tại: {APP_VERSION}", font=("Segoe UI", 9), fg=t["fg_muted"], bg=t["card_bg"]).pack(side=tk.LEFT)
        tk.Label(sub_info_frame, text=" ➔ ", font=("Segoe UI", 9, "bold"), fg=t["accent"], bg=t["card_bg"]).pack(side=tk.LEFT)
        tk.Label(sub_info_frame, text=f" {tag_name} (KHUYÊN DÙNG) ", font=("Segoe UI", 9, "bold"), bg=t["badge_bg"], fg=t["badge_fg"], padx=6, pady=1).pack(side=tk.LEFT)

        if release_name and release_name != tag_name:
            tk.Label(hdr_banner, text=f"Tiêu đề: {release_name}", font=("Segoe UI", 9, "italic"), fg=t["fg"], bg=t["card_bg"]).pack(anchor=tk.W, pady=(4, 0))

        # Changelog card
        log_card = tk.Frame(content, bg=t["card_bg"], highlightbackground=t["card_border"], highlightthickness=1, padx=12, pady=10)
        log_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        tk.Label(log_card, text="📝 Nội dung cập nhật & Cải tiến (Changelog):", font=("Segoe UI", 9, "bold"), fg=t["accent"], bg=t["card_bg"]).pack(anchor=tk.W, pady=(0, 4))
        
        txt_changelog = scrolledtext.ScrolledText(log_card, height=8, font=("Consolas", 9), bg=t["log_bg"], fg=t["log_fg"], insertbackground=t["accent"], relief=tk.FLAT, wrap=tk.WORD)
        txt_changelog.insert(tk.END, body if body.strip() else "Không có ghi chú thay đổi chi tiết.")
        txt_changelog.config(state=tk.DISABLED)
        txt_changelog.pack(fill=tk.BOTH, expand=True)

        lbl_dl_status = tk.Label(content, text="", font=("Segoe UI", 9, "italic"), fg=t["accent"], bg=t["bg"])
        lbl_dl_status.pack(anchor=tk.W, pady=(0, 2))

        prog_dl = ttk.Progressbar(content, orient="horizontal", mode="determinate")
        prog_dl.pack(fill=tk.X, pady=(0, 10))

        btn_box = tk.Frame(content, bg=t["bg"])
        btn_box.pack(fill=tk.X)

        btn_do_update = tk.Button(
            btn_box, 
            text="⚡ CẬP NHẬT NGAY", 
            font=("Segoe UI", 10, "bold"),
            bg=t["btn_primary_bg"], 
            fg=t["btn_primary_fg"], 
            relief=tk.FLAT, 
            padx=18, 
            pady=7, 
            cursor="hand2"
        )
        btn_do_update.pack(side=tk.LEFT)
        make_hover_button(btn_do_update, t["btn_primary_bg"], t["btn_primary_hover"], t["btn_primary_fg"], t["btn_primary_fg"])

        btn_web = tk.Button(
            btn_box, 
            text="🌐 Xem trên GitHub", 
            font=("Segoe UI", 9),
            bg=t["btn_secondary_bg"], 
            fg=t["btn_secondary_fg"], 
            relief=tk.FLAT, 
            padx=12, 
            pady=7, 
            cursor="hand2", 
            command=lambda: webbrowser.open(html_url)
        )
        btn_web.pack(side=tk.LEFT, padx=(8, 0))
        make_hover_button(btn_web, t["btn_secondary_bg"], t["btn_secondary_hover"], t["btn_secondary_fg"], t["fg"])

        btn_close = tk.Button(
            btn_box, 
            text="✕ Để sau", 
            font=("Segoe UI", 9), 
            bg=t["btn_secondary_bg"], 
            fg=t["fg_muted"], 
            relief=tk.FLAT, 
            padx=12, 
            pady=7, 
            cursor="hand2", 
            command=dlg.destroy
        )
        btn_close.pack(side=tk.RIGHT)
        make_hover_button(btn_close, t["btn_secondary_bg"], t["btn_secondary_hover"], t["fg_muted"], t["fg"])

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
set PYINSTALLER_RESET_ENVIRONMENT=1
set _MEIPASS2=
set _MEIPASS=
set _PYI_ARCHIVE_FILE=
set _PYI_APPLICATION_HOME_DIR=
set _PYI_PARENT_PID=
set _PYI_CHILD_PID=
set PYI_PARENT_PID=
set PYI_CHILD_PID=
timeout /t 1 /nobreak >nul
powershell -NoProfile -WindowStyle Hidden -Command "$env:PYINSTALLER_RESET_ENVIRONMENT='1'; Start-Process -FilePath '{curr_exe}'"
timeout /t 2 /nobreak >nul
del "%~f0"
exit
"""
                with open(bat_path, "w", encoding="utf-8") as bf:
                    bf.write(bat_content)

                clean_env = {k: v for k, v in os.environ.items() if not k.startswith("_MEI") and not k.startswith("_PYI") and not k.startswith("PYI_")}
                clean_env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"

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
