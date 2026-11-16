# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all

datas = [
    ('static', 'static'),
    ('templates', 'templates'),
]

binaries = []
hiddenimports = [
    'flask',
    'flask_cors',
    'jinja2',
    'werkzeug',
    'itsdangerous',
    'click',
    'markupsafe',
    'PIL',
    'PIL.Image',
    'PIL.ImageDraw',
    'PIL.ImageFont',
    'imageio_ffmpeg',
    'webview',
    'uuid',
    'socket',
    'threading',
    'subprocess',
    'json',
    'urllib',
    'urllib.request',
    'webbrowser',
    'logging',
    'pathlib',
    'time'
]

packages_to_collect = [
    'flask',
    'flask_cors',
    'werkzeug',
    'jinja2',
    'itsdangerous',
    'click',
    'markupsafe',
    'PIL',
    'imageio_ffmpeg',
    'webview',
]

for pkg in packages_to_collect:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pythonnet', 'clr', 'clr_loader'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MergeVideoTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MergeVideoTool',
)

app = BUNDLE(
    coll,
    name='MergeVideoTool.app',
    icon=None,
    bundle_identifier='com.mergevideotool.app',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
        'CFBundleDisplayName': 'MergeVideoTool',
        'CFBundleName': 'MergeVideoTool',
        'CFBundleShortVersionString': '1.0.0',
    }
)
