import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QSystemTrayIcon
from PyQt5.QtGui import QCursor, QIcon
from PyQt5.QtCore import Qt
from clipboard_manager import ClipboardManager

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    manager = ClipboardManager()
    manager.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()