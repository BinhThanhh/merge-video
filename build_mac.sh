#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=================================================="
echo "   Đóng gói MergeVideoTool.app cho macOS"
echo "=================================================="

# Kiểm tra Python 3
if ! command -v python3 &> /dev/null; then
    echo "[!] Không tìm thấy Python 3. Vui lòng cài đặt trước khi build."
    exit 1
fi

# Tạo virtualenv riêng cho build
if [ ! -d "venv_build" ]; then
    echo "[*] Tạo venv_build..."
    python3 -m venv venv_build
fi
source venv_build/bin/activate

echo "[1/3] Cài đặt dependencies..."
pip install --upgrade pip
pip install -r requirements_mac.txt

echo "[2/3] Biên dịch PyInstaller thành file MergeVideoTool.app..."
pyinstaller --noconfirm MergeVideoTool_mac.spec

echo "[3/3] Tạo file nén và DMG phân phối..."
cd dist
tar -czvf MergeVideoTool_mac.tar.gz MergeVideoTool.app

if command -v hdiutil &> /dev/null; then
    hdiutil create -volname "MergeVideoTool" -srcfolder MergeVideoTool.app -ov -format UDZO MergeVideoTool.dmg
    echo "[✓] Đã tạo thành công: dist/MergeVideoTool.dmg"
fi

echo "=================================================="
echo "[✓] Build hoàn tất thành công!"
echo "    App Bundle: dist/MergeVideoTool.app"
if [ -f "MergeVideoTool.dmg" ]; then
    echo "    DMG Installer: dist/MergeVideoTool.dmg"
fi
echo "=================================================="
