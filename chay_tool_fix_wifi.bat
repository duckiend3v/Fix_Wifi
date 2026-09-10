@echo off
cd /d "%~dp0"
title Fix Wifi - Phone Farm
echo ========================================================
echo          KHOI DONG FIX WIFI PHONE FARM
echo ========================================================
echo.

echo [1/2] Kiem tra Python...
python --version >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] Tim thay python. Dang mo giao dien...
    python fix_wifi_tool.py
    goto :DONE
)

py -3 --version >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] Tim thay py -3. Dang mo giao dien...
    py -3 fix_wifi_tool.py
    goto :DONE
)

if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe" (
    echo [OK] Tim thay Python312 trong AppData. Dang mo giao dien...
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe" fix_wifi_tool.py
    goto :DONE
)

if exist "C:\Program Files\Python312\python.exe" (
    echo [OK] Tim thay Python312 trong Program Files. Dang mo giao dien...
    "C:\Program Files\Python312\python.exe" fix_wifi_tool.py
    goto :DONE
)

echo [LOI] Khong tim thay Python tren may tinh!
echo Vui long kiem tra lai xem may da cai dat Python 3 chua.

:DONE
echo.
echo ========================================================
echo Nhan phim bat ky de thoat...
pause >nul
