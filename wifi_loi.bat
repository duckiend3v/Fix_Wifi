adb -s 52007266c0df2523 shell sleep 2
adb -s 52007266c0df2523 shell settings put global http_proxy :0
adb -s 52007266c0df2523 shell settings delete global http_proxy
adb -s 52007266c0df2523 shell settings delete global global_http_proxy_host
adb -s 52007266c0df2523 shell settings delete global global_http_proxy_port
adb -s 52007266c0df2523 shell cmd wifi forget-network 0
adb -s 52007266c0df2523 shell cmd wifi forget-network 1
adb -s 52007266c0df2523 shell cmd wifi forget-network 2
adb -s 52007266c0df2523 shell cmd wifi forget-network 3
adb -s 52007266c0df2523 shell cmd wifi forget-network 4
adb -s 52007266c0df2523 shell cmd wifi forget-network 5
adb -s 52007266c0df2523 shell cmd wifi forget-network 6
adb -s 52007266c0df2523 shell cmd wifi forget-network 7
adb -s 52007266c0df2523 shell cmd wifi forget-network 8
adb -s 52007266c0df2523 shell am force-stop com.steinwurf.adbjoinwifi
adb -s 52007266c0df2523 shell sleep 2
adb -s 52007266c0df2523 shell am start -n com.steinwurf.adbjoinwifi/.MainActivity -e disconnect true
adb -s 52007266c0df2523 shell sleep 2
adb -s 52007266c0df2523 shell svc wifi disable
adb -s 52007266c0df2523 shell sleep 2
