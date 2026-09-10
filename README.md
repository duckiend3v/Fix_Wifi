<div align="center">

  <img src="icon.png" width="130" height="130" alt="Fix Wifi Logo" />

  # Fix Wifi - Android Phone Farm
  
  <p><b>Công cụ tự động gỡ lỗi mạng Wi-Fi, kẹt Proxy, xóa app College Proxy & kết nối Wi-Fi hàng loạt cho Phone Farm</b></p>

</div>

---

## 🌟 Tính Năng Chính
1. **Xóa sạch HTTP Proxy hệ thống:** Xóa toàn bộ cấu hình `http_proxy`, `global_http_proxy_host`, `global_http_proxy_port` gây mất mạng trên Android.
2. **Xóa dữ liệu app College Proxy:** Tự động `am force-stop` và `pm clear` package `com.cell47.College_Proxy` / `collegeproxy`.
3. **Quên cấu hình Wi-Fi cũ:** Quên toàn bộ mạng Wi-Fi lưu trước đó (`cmd wifi forget-network 0..15`).
4. **Tắt & Ngắt kết nối app ADBJoinWiFi cũ:** Đảm bảo không bị kẹt socket kết nối cũ.
5. **Khởi động lại Wi-Fi:** Tắt (`svc wifi disable`) và bật lại (`svc wifi enable`).
6. **Kết nối Wi-Fi mới tự động:** Kết nối vào Wi-Fi mới định dạng `SSID|Mật_khẩu` qua app ADBJoinWiFi.
7. **Xử lý đa luồng (Multi-threading):** Chạy đồng thời 10 - 50 máy cùng lúc, hoàn tất trong vài giây.
8. **Tự Động Cập Nhật (Auto-Update qua GitHub):** Nhấp nút "Kiểm tra Cập nhật" trên tool để tự tải và nâng cấp phiên bản mới nhất từ GitHub Releases.

---

## 🚀 Hướng Dẫn Cài Đặt & Sử Dụng

### Cách 1: Chạy trực tiếp file EXE (Không cần cài Python)
- Chạy file `Fix_Wifi.exe`.

### Cách 2: Chạy bằng mã nguồn Python
- Cài đặt Python 3.10+
- Nhấp đúp vào file `chay_tool_fix_wifi.bat` hoặc chạy lệnh:
  ```bash
  python fix_wifi_tool.py
  ```

---

## 📦 Cách Đóng Gói (Build file EXE)
- Nhấp đúp vào file `dong_goi_tool.bat`
- Hệ thống sẽ tự động đóng gói ra file `Fix_Wifi.exe` và `Fix_Wifi.zip`.

---

## 🔄 Tự Động Cập Nhật
- Khi có bản phát hành mới trên [GitHub Releases](https://github.com/duckiend3v/Fix_Wifi/releases), người dùng chỉ cần mở tool và ấn **[ 🔄 Kiểm tra Cập nhật ]** -> **[ ⚡ CẬP NHẬT NGAY ]**.
