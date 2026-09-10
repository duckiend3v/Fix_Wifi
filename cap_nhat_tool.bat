@echo off
cd /d "%~dp0"
title Cap Nhat Fix Wifi qua GitHub
chcp 65001 >nul

echo ========================================================
echo          KIỂM TRA VÀ CẬP NHẬT FIX WIFI QUA GITHUB
echo ========================================================
echo.

echo [*] Đang kiểm tra phiên bản mới nhất trên GitHub...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; " ^
  "$repo = 'duckiend3v/Fix_Wifi'; " ^
  "if (Test-Path 'updater_config.json') { try { $cfg = Get-Content 'updater_config.json' | ConvertFrom-Json; if ($cfg.github_repo) { $repo = $cfg.github_repo } } catch {} } " ^
  "Write-Host ('[*] Repo: ' + $repo); " ^
  "$api = 'https://api.github.com/repos/' + $repo + '/releases/latest'; " ^
  "try { " ^
  "    $rel = Invoke-RestMethod -Uri $api -Headers @{'User-Agent'='FixWifi-CLI-Updater'}; " ^
  "    Write-Host ('[OK] Phiên bản mới nhất trên GitHub: ' + $rel.tag_name); " ^
  "    $asset = $rel.assets | Where-Object { $_.name -like '*.exe' -or $_.name -like '*.zip' } | Select-Object -First 1; " ^
  "    if ($asset) { " ^
  "        Write-Host ('[*] Đang tải: ' + $asset.name + ' (' + [math]::Round($asset.size / 1MB, 2) + ' MB)...'); " ^
  "        $outFile = $asset.name; " ^
  "        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $outFile -UseBasicParsing; " ^
  "        Write-Host ('[OK] Đã tải xong: ' + $outFile); " ^
  "        if ($outFile.EndsWith('.zip')) { " ^
  "            Write-Host '[*] Đang giải nén file ZIP...'; " ^
  "            Expand-Archive -Path $outFile -DestinationPath . -Force; " ^
  "            Remove-Item $outFile -Force; " ^
  "            Write-Host '[OK] Cập nhật thành công!'; " ^
  "        } " ^
  "    } else { " ^
  "        Write-Host '[*] Đang cập nhật fix_wifi_tool.py...'; " ^
  "        Invoke-WebRequest -Uri ('https://raw.githubusercontent.com/' + $repo + '/' + $rel.tag_name + '/fix_wifi_tool.py') -OutFile 'fix_wifi_tool.py' -UseBasicParsing; " ^
  "        Write-Host '[OK] Đã cập nhật file fix_wifi_tool.py thành công!'; " ^
  "    } " ^
  "} catch { " ^
  "    Write-Host ('[!] Không thể lấy bản cập nhật: ' + $_.Exception.Message) -ForegroundColor Yellow; " ^
  "}"

echo.
echo ========================================================
echo Nhấn phím bất kỳ để đóng...
pause >nul
