# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('icons/clipboard.png', 'icons')],
    hiddenimports=['win32api', 'win32gui', 'win32con', 'keyboard'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['unittest', 'email', 'html', 'http', 'xml', 'PyQt5.QtNetwork', 'PyQt5.QtQml', 'PyQt5.QtWebKit', 'PyQt5.QtMultimedia'],
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
    name='ClipList',
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
    version='version.txt',
    icon=['icons\\clipboard.png'],
)
