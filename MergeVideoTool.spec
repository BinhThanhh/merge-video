# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [
    ('static', 'static'),
    ('templates', 'templates'),
    ('ffmpeg.exe', '.'),
    ('realesrgan', 'realesrgan'),
    ('obf_build/pyarmor_runtime_000000', 'pyarmor_runtime_000000')
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
    'pythonnet',
    'clr_loader',
    'clr',
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

# Collect all resources and submodules for all packages
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
    'pythonnet',
    'clr_loader'
]

for pkg in packages_to_collect:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

a = Analysis(
    ['obf_build/app.py'],
    pathex=['obf_build', '.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MergeVideoTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
