import PyInstaller.__main__
import os

# 确保目录存在
if not os.path.exists('dist'):
    os.makedirs('dist')

PyInstaller.__main__.run([
    'src/main.py',
    '--name=ClipList',
    '--windowed',
    '--onefile',
    '--icon=icons/clipboard.png',
    '--add-data=icons/clipboard.png;icons',
    '--clean',
    '--noconfirm',
    # 只保留安全的优化选项
    '--exclude-module=unittest',
    '--exclude-module=email',
    '--exclude-module=html',
    '--exclude-module=http',
    '--exclude-module=xml',
    # 必要的模块
    '--hidden-import=win32api',
    '--hidden-import=win32gui',
    '--hidden-import=win32con',
    '--hidden-import=keyboard',
    # 排除不需要的 Qt 模块
    '--exclude-module=PyQt5.QtNetwork',
    '--exclude-module=PyQt5.QtQml',
    '--exclude-module=PyQt5.QtWebKit',
    '--exclude-module=PyQt5.QtMultimedia',
    '--version-file=version.txt',
]) 