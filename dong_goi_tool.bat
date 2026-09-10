@echo off
cd /d "%~dp0"
echo ========================================================
echo             TIEN HANH DONG GOI FIX WIFI
echo ========================================================
echo.

python dong_goi.py
if %errorlevel% neq 0 (
    py -3 dong_goi.py
)

echo.
pause
