#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script đóng gói Tool Gỡ Lỗi Wi-Fi:
1. Nén toàn bộ thư mục thành file Tool_Fix_Wifi.zip
2. Tự động biên dịch thành file Tool_Fix_Wifi.exe độc lập (nếu có PyInstaller)
"""

import os
import sys
import shutil
import zipfile
import subprocess

def create_zip():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    zip_path = os.path.join(parent_dir, "Fix_Wifi.zip")
    
    print(f"[*] Đang nén thư mục thành file ZIP: {zip_path}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(script_dir):
            # Bỏ qua các thư mục tạm build, dist, __pycache__
            if any(x in root for x in ["build", "dist", "__pycache__"]):
                continue
            for file in files:
                if file.endswith(".zip") or file.endswith(".spec"):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, parent_dir)
                zipf.write(file_path, arcname)
    print(f"[OK] Đã tạo file nén thành công: {zip_path}")
    try:
        shutil.copy2(zip_path, os.path.join(script_dir, "Fix_Wifi.zip"))
    except Exception:
        pass
    return zip_path

def build_exe():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(script_dir, "fix_wifi_tool.py")
    
    print("\n[*] Kiểm tra PyInstaller để đóng gói thành file .EXE độc lập...")
    try:
        import PyInstaller
        print("[OK] Đã tìm thấy PyInstaller.")
    except ImportError:
        print("[*] Chưa có PyInstaller, đang tự động cài đặt...")
        res = subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=False)
        if res.returncode != 0:
            print("[CANH BAO] Không thể tự cài PyInstaller. Bỏ qua bước đóng gói .exe.")
            return

    print("[*] Đang biên dịch fix_wifi_tool.py thành Fix_Wifi.exe...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "Fix_Wifi",
        "--clean",
        main_py
    ]
    res = subprocess.run(cmd, cwd=script_dir)
    if res.returncode == 0:
        exe_src = os.path.join(script_dir, "dist", "Fix_Wifi.exe")
        exe_dst = os.path.join(script_dir, "Fix_Wifi.exe")
        if os.path.exists(exe_src):
            shutil.copy2(exe_src, exe_dst)
            print(f"\n[OK] ĐÃ ĐÓNG GÓI THÀNH CÔNG FILE EXE:")
            print(f" -> {exe_dst}")
            
            # Dọn dẹp thư mục tạm
            for folder in ["build", "dist"]:
                p = os.path.join(script_dir, folder)
                if os.path.exists(p):
                    try:
                        shutil.rmtree(p)
                    except Exception:
                        pass
            spec_file = os.path.join(script_dir, "Fix_Wifi.spec")
            if os.path.exists(spec_file):
                try:
                    os.remove(spec_file)
                except Exception:
                    pass
    else:
        print("[LỖI] Quá trình đóng gói EXE gặp lỗi.")

def main():
    print("=" * 60)
    print("          TIẾN HÀNH ĐÓNG GÓI FIX WIFI")
    print("=" * 60)
    
    # 1. Tạo file zip
    zip_file = create_zip()
    
    # 2. Tạo file exe nếu muốn
    build_exe()
    
    # 3. Cập nhật lại zip chứa cả file exe vừa build (nếu có)
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Fix_Wifi.exe")):
        print("\n[*] Cập nhật lại file ZIP bao gồm file .EXE...")
        create_zip()

    print("\n" + "=" * 60)
    print("ĐÃ HOÀN TẤT ĐÓNG GÓI!")
    print("=" * 60)

if __name__ == "__main__":
    main()
