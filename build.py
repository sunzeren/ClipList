import PyInstaller.__main__
import os

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 定义图标资源目录
icons_dir = os.path.join(current_dir, 'icons')

# 确保所有图标文件都被包含
icon_files = [
    ('icons/clipboard.png', 'icons'),
    ('icons/checkbox.png', 'icons'),
    ('icons/checkbox-checked.png', 'icons'),
    ('icons/top.png', 'icons'),
    ('icons/untop.png', 'icons')
]

# PyInstaller 参数配置
pyinstaller_args = [
    'src/main.py',  # 主程序入口
    '--name=ClipList',  # 生成的exe名称
    '--windowed',  # 无控制台窗口
    '--noconfirm',  # 覆盖已存在的构建目录
    '--clean',  # 清理临时文件
    '--onefile',  # 打包成单个exe文件
]

# 添加图标文件
for icon_file, icon_dir in icon_files:
    pyinstaller_args.extend(['--add-data', f'{icon_file};{icon_dir}'])

# 执行打包
PyInstaller.__main__.run(pyinstaller_args) 