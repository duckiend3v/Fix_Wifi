@echo off
setlocal
cd /d "%~dp0"
title Push Du An Len GitHub - Fix Wifi
chcp 65001 >nul

echo ========================================================
echo       TIEN HANH DAY DU AN LEN GITHUB (FIRST PUSH)
echo ========================================================
echo.

REM 1. Don dep file thua trong thu muc
echo [*] Dang don dep cac file rac va file thua...
del /f /q wifi_loi.bat >nul 2>&1
del /f /q Fix_Wifi.zip >nul 2>&1

REM 2. Kiem tra Git trong he thong hoac cac thu muc cai dat mac dinh
where git >nul 2>&1
if %errorlevel% neq 0 (
    if exist "C:\Program Files\Git\cmd\git.exe" (
        set "PATH=C:\Program Files\Git\cmd;%PATH%"
    ) else if exist "C:\Program Files\Git\bin\git.exe" (
        set "PATH=C:\Program Files\Git\bin;%PATH%"
    ) else if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\Git\cmd;%PATH%"
    ) else (
        echo [LOI] Khong tim thay Git tren may tinh cua ban!
        echo.
        echo Vui long tai va cai dat Git tai: https://git-scm.com/
        echo (Sau khi cai dat Git xong, chay lai file nay la duoc)
        echo.
        pause
        exit /b 1
    )
)

set "REPO=duckiend3v/Fix_Wifi"

echo [*] Dia chi GitHub Repo: https://github.com/%REPO%
echo.
echo --------------------------------------------------------
echo [LUU Y QUAN TRONG TRUOC KHI PUSH]:
echo  1. Hay dam bao ban da tao repository rong tren GitHub:
echo     https://github.com/new
echo  2. Dat ten repository la: Fix_Wifi
echo  3. Chon Public (hoac Private tuy ban)
echo  4. KHONG tich chon vao "Add a README file" (de trong)
echo  5. Bam "Create repository" tren GitHub.
echo --------------------------------------------------------
echo.
echo Sau khi da tao xong repo tren web, nhan phim bat ky de bat dau push code...
pause

echo.
echo [*] Khoi tao Git repository local...
if not exist ".git" (
    git init
)
git branch -M main

REM Tu dong thiet lap user.name va user.email cho Git
echo [*] Thiet lap thong tin tac gia Git (duckiend3v)...
git config --global user.name "duckiend3v" 2>nul
git config --global user.email "duckien2002tb@gmail.com" 2>nul
git config user.name "duckiend3v"
git config user.email "duckien2002tb@gmail.com"

REM Cau hinh remote origin dung voi tai khoan duckiend3v
git remote remove origin >nul 2>&1
git remote add origin https://duckiend3v@github.com/%REPO%.git

echo [*] Lam moi chi muc Git theo .gitignore moi...
git rm -r --cached . >nul 2>&1
git add .

echo [*] Dang tao commit...
git commit -m "Khoi tao Fix Wifi v1.2.0 (Toi uu thu muc va .gitignore)" >nul 2>&1

echo.
echo [*] Dang day code len GitHub voi tai khoan duckiend3v...
git push -u origin main

echo.
if %errorlevel% equ 0 (
    echo ========================================================
    echo [THANH CONG] DA DAY DU AN LEN GITHUB HOAN TAT!
    echo ========================================================
    echo Link repo: https://github.com/%REPO%
    echo.
    echo BUOC TIEP THEO DE MAY KHAC TU DONG CAP NHAT:
    echo 1. Vao: https://github.com/%REPO%/releases/new
    echo 2. Tag: v1.2.0
    echo 3. Keo tha file Fix_Wifi.exe vao muc dinh kem
    echo 4. Bam "Publish release" la xong!
    echo ========================================================
) else (
    echo ========================================================
    echo [!] PUSH THAT BAI HOAC BI XUNG DOT TAI KHOAN:
    echo  - Neu bi loi tai khoan DoMinhQuan2002:
    echo    Hay chay file: "doi_tai_khoan_github.bat" de xoa dang nhap cu.
    echo  - Sau do dang nhap vao: duckiend3v tren trinh duyet khi duoc hoi.
    echo ========================================================
)

echo.
echo Nhan phim bat ky de thoat...
pause
