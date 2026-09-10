@echo off
setlocal enabledelayedexpansion
title Fix Wifi - Phone Farm (Multi-Device)
chcp 65001 >nul

echo ================================================================
echo                    FIX WIFI (PHONE FARM)
echo ================================================================
echo.
echo Huong dan:
echo  - Nhap 1 hoac nhieu UID thiet bi (cach nhau boi dau cach).
echo  - Hoac de trong va nhan [ENTER] de tu dong quet TAT CA may dang cam.
echo.

set /p "INPUT_UIDS=Nhap UID (de trong de tu quet tat ca): "

if "%INPUT_UIDS%"=="" (
    echo.
    echo [INFO] Dang quet toan bo thiet bi qua adb devices...
    set "DEVICE_LIST="
    for /f "skip=1 tokens=1,2" %%A in ('adb devices') do (
        if "%%B"=="device" (
            set "DEVICE_LIST=!DEVICE_LIST! %%A"
        )
    )
    if "!DEVICE_LIST!"=="" (
        echo [CANH BAO] Khong tim thay thiet bi nao dang ket noi!
        pause
        exit /b
    )
    set "TARGET_UIDS=!DEVICE_LIST!"
) else (
    set "TARGET_UIDS=%INPUT_UIDS%"
)

echo.
set /p "WIFI_CREDS=Nhap Wi-Fi can ket noi (dinh dang user|pass, de trong neu khong ket noi): "

echo.
echo [DANH SACH THIET BI SE XU LY]: %TARGET_UIDS%
if not "%WIFI_CREDS%"=="" (
    echo [WI-FI KET NOI SAU KHI SUA]: %WIFI_CREDS%
)
echo.
pause

for %%D in (%TARGET_UIDS%) do (
    echo -------------------------------------------------------------
    echo [*] Dang go loi cho thiet bi: %%D
    echo -------------------------------------------------------------
    
    echo   - [1/7] Xoa HTTP Proxy he thong...
    adb -s %%D shell settings put global http_proxy :0 >nul 2>&1
    adb -s %%D shell settings delete global http_proxy >nul 2>&1
    adb -s %%D shell settings delete global global_http_proxy_host >nul 2>&1
    adb -s %%D shell settings delete global global_http_proxy_port >nul 2>&1

    echo   - [2/7] Xoa du lieu app College Proxy...
    adb -s %%D shell am force-stop com.cell47.College_Proxy >nul 2>&1
    adb -s %%D shell pm clear com.cell47.College_Proxy >nul 2>&1
    adb -s %%D shell am force-stop com.cell47.collegeproxy >nul 2>&1
    adb -s %%D shell pm clear com.cell47.collegeproxy >nul 2>&1
    
    echo   - [3/7] Quen cac mang Wi-Fi da luu...
    for /L %%i in (0,1,10) do (
        adb -s %%D shell cmd wifi forget-network %%i >nul 2>&1
    )
    
    echo   - [4/7] Dung va ngat app ADBJoinWiFi cu...
    adb -s %%D shell am force-stop com.steinwurf.adbjoinwifi >nul 2>&1
    adb -s %%D shell am start -n com.steinwurf.adbjoinwifi/.MainActivity -e disconnect true >nul 2>&1
    
    echo   - [5/7] Tat Wi-Fi...
    adb -s %%D shell svc wifi disable >nul 2>&1
    
    echo   - [6/7] Bat lai Wi-Fi...
    adb -s %%D shell svc wifi enable >nul 2>&1
    
    if not "%WIFI_CREDS%"=="" (
        echo   - [7/7] Ket noi Wi-Fi moi qua ADBJoinWiFi...
        for /f "tokens=1,2 delims=|" %%a in ("%WIFI_CREDS%") do (
            set "W_SSID=%%a"
            set "W_PASS=%%b"
            if "!W_PASS!"=="" (
                adb -s %%D shell am start -n com.steinwurf.adbjoinwifi/.MainActivity -e ssid "!W_SSID!" -e password_type open >nul 2>&1
            ) else (
                adb -s %%D shell am start -n com.steinwurf.adbjoinwifi/.MainActivity -e ssid "!W_SSID!" -e password_type WPA -e password "!W_PASS!" >nul 2>&1
            )
        )
    )
    
    echo [*] HOAN TAT %%D!
    echo.
)

echo ================================================================
echo DA XU LY XONG TAT CA THIET BI!
echo ================================================================
pause
