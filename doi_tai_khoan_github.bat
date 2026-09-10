@echo off
setlocal
cd /d "%~dp0"
title Doi Tai Khoan GitHub Sang duckiend3v

echo ========================================================
echo       DOI TAI KHOAN GITHUB SANG: duckiend3v
echo ========================================================
echo.

echo [*] Dang xoa thong tin dang nhap cu khoi Windows...

REM Xoa credential lien quan den github bang cmdkey va powershell
cmdkey /delete:git:https://github.com >nul 2>&1
cmdkey /delete:LegacyGeneric:target=git:https://github.com >nul 2>&1

powershell -NoProfile -Command "cmdkey /list | Select-String 'github' | ForEach-Object { $line = $_.Line; if ($line -match 'Target:\s*(.+)') { $t = $matches[1].Trim(); cmdkey /delete:$t } }" >nul 2>&1

REM Cau hinh Git user thanh duckiend3v
git config --global user.name "duckiend3v" >nul 2>&1
git config --global user.email "duckien200tb#gmail.com" >nul 2>&1
git config user.name "duckiend3v" >nul 2>&1
git config user.email "duckien2002tb@gmail.com" >nul 2>&1

echo [OK] Da xoa thong tin dang nhap cu thanh cong!
echo.
echo ========================================================
echo TIEP THEO:
echo 1. Mo file: push_len_github.bat
echo 2. Khi trinh duyet bat len, hay dang nhap: duckiend3v
echo 3. Bam "Authorize GitCredentialManager" de push thanh cong!
echo ========================================================
echo.
pause
