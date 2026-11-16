# Hướng Dẫn Chạy & Đóng Gói MergeVideoTool Cho macOS

Bộ mã nguồn `MergeVideoTool` đã được cấu hình tương thích 100% với hệ điều hành macOS (hỗ trợ cả chip Apple Silicon M1/M2/M3/M4 lẫn Intel x86_64).

---

## Cách 1: Chạy trực tiếp 1-Click trên Mac (Không cần cài đặt phức tạp)
1. Copy thư mục dự án này sang máy Mac của bạn.
2. Mở Finder, tìm file:
   ```bash
   run_mac.command
   ```
3. Nhấp đúp chuột vào file `run_mac.command`.
   - File sẽ tự động kiểm tra Python 3, tạo virtualenv `venv_mac`, cài đặt thư viện cần thiết (`requirements_mac.txt`) và mở cửa sổ Native Window của ứng dụng lên ngay lập tức!
   - *(Lưu ý: Nếu Mac báo không có quyền thực thi, bạn chỉ cần mở Terminal tại thư mục và gõ: `chmod +x run_mac.command`)*

---

## Cách 2: Đóng gói thành file `MergeVideoTool.app` và `.dmg` trên Mac
Nếu bạn muốn đóng gói thành 1 ứng dụng Mac độc lập (`.app` hoặc file cài đặt `.dmg`):
1. Mở Terminal tại thư mục này trên máy Mac.
2. Chạy lệnh:
   ```bash
   chmod +x build_mac.sh
   ./build_mac.sh
   ```
3. Sau khi chạy xong, thư mục `dist/` sẽ có:
   - `dist/MergeVideoTool.app` (Ứng dụng macOS kéo thả vào Applications).
   - `dist/MergeVideoTool.dmg` (File cài đặt đĩa ảnh phân phối cho người dùng Mac khác).

---

## Cách 3: Tự động Build file `.dmg` từ đám mây (GitHub Actions)
Nếu bạn không muốn tự cài đặt môi trường trên Mac:
- Dự án đã được tạo sẵn workflow [`.github/workflows/build-mac.yml`](.github/workflows/build-mac.yml).
- Bạn chỉ cần push mã nguồn này lên kho lưu trữ GitHub của mình (hoặc bấm **Run workflow** trong tab Actions).
- GitHub sẽ tự động khởi tạo máy ảo macOS, biên dịch ra file `MergeVideoTool.dmg` và cho phép bạn tải về ngay trên web GitHub!
