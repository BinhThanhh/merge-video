#!/bin/bash
cd "$(dirname "$0")"

echo "=================================================="
echo "   Khởi động MergeVideoTool trên macOS"
echo "=================================================="

# Kiểm tra Python 3
if ! command -v python3 &> /dev/null; then
    echo "[!] Không tìm thấy Python 3 trên máy của bạn."
    echo "[*] Vui lòng cài đặt Python 3 từ https://www.python.org hoặc chạy: brew install python"
    read -p "Nhấn Enter để thoát..."
    exit 1
fi

# Tạo Virtual Environment nếu chưa có
if [ ! -d "venv_mac" ]; then
    echo "[*] Đang tạo môi trường ảo Python (venv_mac)..."
    python3 -m venv venv_mac
fi

# Kích hoạt virtualenv
source venv_mac/bin/activate

# Cài đặt hoặc cập nhật thư viện
echo "[*] Đang kiểm tra và cài đặt thư viện macOS cần thiết..."
pip install -q --upgrade pip
pip install -q -r requirements_mac.txt

# Chạy ứng dụng cửa sổ native
echo "[*] Đang khởi chạy MergeVideoTool Native Desktop App..."
python3 app.py
