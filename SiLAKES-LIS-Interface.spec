# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec utk SiLAKES LIS Interface.
Mode onedir (bukan onefile) -- lebih stabil utk pywebview/WebView2 di Windows
(onefile sering lambat start & rawan masalah ekstraksi DLL native).
Distribusi: copy SELURUH folder dist/SiLAKES-LIS-Interface/, bukan cuma .exe-nya.
"""
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hidden = (
    collect_submodules("webview")
)

a = Analysis(
    ["gui_app.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("gui/dist", "gui/dist"),
    ],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SiLAKES-LIS-Interface",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # aplikasi GUI, tanpa jendela console hitam
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="gui/assets/app_icon.ico",  # aktifkan kalau sudah ada .ico
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SiLAKES-LIS-Interface",
)
