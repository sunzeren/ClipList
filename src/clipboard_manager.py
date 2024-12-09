from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                           QListWidget, QLabel, QPushButton, QApplication,
                           QSystemTrayIcon, QMenu, QAction, QStyleOptionViewItem)
from PyQt5.QtCore import Qt, QPoint, QMimeData, QTimer
from PyQt5.QtGui import (QFont, QColor, QPalette, QIcon, QDrag, QPainter,
                        QPixmap)
import win32gui
import win32api
import win32con
import time
from win32gui import GetForegroundWindow, GetWindowText
import win32clipboard
from ctypes import windll
import keyboard

class ClipboardManager(QWidget):
    def __init__(self):
        super().__init__()
        # 设置窗口标志：无边框、置顶、不获取焦点
        self.setWindowFlags(
            Qt.Window |  # 基本窗口
            Qt.FramelessWindowHint |  # 无边框
            Qt.WindowStaysOnTopHint |  # 置顶
            Qt.Tool |  # 工具窗口
            Qt.WindowDoesNotAcceptFocus  # 不获取焦点
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)  # 显示时不激活
        
        self.always_on_top = True
        self.init_ui()
        self.setup_clipboard()
        self.clip_history = []
        
        # 用于窗口拖动
        self.dragging = False
        self.drag_position = None
        
        # 添加系统托盘
        self.setup_tray()

    def init_ui(self):
        self.setFixedSize(400, 600)
        
        # 主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建主容器
        container = QWidget()
        container.setObjectName('container')
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(1, 1, 1, 1)
        
        # 标题栏
        title_bar = QWidget()
        title_bar.setObjectName('titleBar')
        title_bar.setFixedHeight(40)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        
        # 标题
        title = QLabel('ClipList')
        title.setObjectName('titleLabel')
        title.setFont(QFont('Arial', 12, QFont.Bold))
        
        # 置顶按钮
        pin_btn = QPushButton('📌')  # 使用 Unicode 图标
        pin_btn.setObjectName('pinButton')
        pin_btn.setFixedSize(30, 30)
        pin_btn.setCheckable(True)
        pin_btn.setChecked(True)
        pin_btn.clicked.connect(self.toggle_always_on_top)
        
        # 关闭按钮
        close_btn = QPushButton('×')
        close_btn.setObjectName('closeButton')
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(QApplication.quit)
        
        title_layout.addWidget(title)
        title_layout.addStretch()
        title_layout.addWidget(pin_btn)
        title_layout.addWidget(close_btn)
        
        # 列表区域
        self.list_widget = QListWidget()
        self.list_widget.setObjectName('clipList')
        self.list_widget.itemEntered.connect(self.on_item_hover)
        self.list_widget.setMouseTracking(True)
        self.list_widget.setDragEnabled(True)  # 启用拖拽
        self.list_widget.setDragDropMode(QListWidget.DragOnly)  # 只允许拖出
        
        # 自定义拖拽的开始
        self.list_widget.mousePressEvent = self.list_mousePressEvent
        self.list_widget.mouseMoveEvent = self.list_mouseMoveEvent
        
        # 底部按钮
        bottom_bar = QWidget()
        bottom_bar.setObjectName('bottomBar')
        bottom_layout = QHBoxLayout(bottom_bar)
        
        clear_btn = QPushButton('清空历史')
        clear_btn.setObjectName('clearButton')
        clear_btn.clicked.connect(self.clear_history)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(clear_btn)
        bottom_layout.addStretch()
        
        # 添加所有组件
        container_layout.addWidget(title_bar)
        container_layout.addWidget(self.list_widget)
        container_layout.addWidget(bottom_bar)
        
        layout.addWidget(container)
        self.setLayout(layout)
        
        # 设置样式
        self.setStyleSheet('''
            #container {
                background-color: #2c3e50;
                border-radius: 10px;
                border: 1px solid #34495e;
            }
            #titleBar {
                background-color: #34495e;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            #titleLabel {
                color: #ecf0f1;
            }
            #pinButton {
                background-color: transparent;
                color: #ecf0f1;
                border: none;
                font-size: 16px;
            }
            #pinButton:checked {
                color: #3498db;
            }
            #pinButton:hover {
                background-color: #34495e;
            }
            #closeButton {
                background-color: transparent;
                color: #ecf0f1;
                border: none;
                font-size: 20px;
            }
            #closeButton:hover {
                background-color: #e74c3c;
            }
            QListWidget {
                background-color: #2c3e50;
                border: none;
                color: #ecf0f1;
                padding: 5px;
            }
            QListWidget::item {
                background-color: #34495e;
                border-radius: 5px;
                margin: 2px 5px;
                padding: 8px;
            }
            QListWidget::item:hover {
                background-color: #3498db;
            }
            QListWidget::item:selected {
                background-color: #2980b9;
            }
            #clearButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
            }
            #clearButton:hover {
                background-color: #2980b9;
            }
            #bottomBar {
                background-color: #2c3e50;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        ''')

    def setup_clipboard(self):
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_change)
        # 初始化时尝试访问一次剪贴板
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.CloseClipboard()
        except:
            pass

    def on_clipboard_change(self):
        text = self.clipboard.text().strip()
        if text and text not in self.clip_history:
            self.clip_history.append(text)
            self.list_widget.insertItem(0, text)

    def on_item_hover(self, item):
        # 当鼠标悬停时，只选中项目但不触发粘贴
        self.list_widget.setCurrentItem(item)

    def on_item_paste(self, item):
        try:
            # 只更新剪贴板内容
            self.clipboard.setText(item.text())
            print(f"Content copied to clipboard: {item.text()}")
            
            # 可以添加一个临时的状态提示
            current_text = item.text()
            item.setText("✓ 已复制")
            QApplication.processEvents()
            
            # 0.5秒后恢复原文本
            def restore_text():
                item.setText(current_text)
            QTimer.singleShot(500, restore_text)
            
        except Exception as e:
            print(f"Error while copying: {str(e)}")

    def clear_history(self):
        self.list_widget.clear()
        self.clip_history.clear()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if event.pos().y() <= 40:  # 标题栏高度
                self.dragging = True
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()

    def setup_tray(self):
        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        
        # 创建一个默认图标
        icon = QIcon()
        icon.addFile(':/icons/clipboard.png')  # 首先尝试使用资源文件
        if icon.isNull():
            # 如果资源文件不存在，使用系统图标
            icon = self.style().standardIcon(QStyle.SP_DialogSaveButton)
        
        self.tray_icon.setIcon(icon)
        
        # 创建托盘菜单
        tray_menu = QMenu()
        show_action = QAction("显示", self)
        quit_action = QAction("退出", self)
        
        show_action.triggered.connect(self.toggle_window)
        quit_action.triggered.connect(QApplication.quit)
        
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
    
    def toggle_window(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()
    
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # 单击托盘图标
            self.toggle_window()
    
    def closeEvent(self, event):
        # 移除托盘最小化的行为，直接接受关闭事件
        event.accept()  # 这将导致应用程序关闭

    def toggle_always_on_top(self, checked):
        self.always_on_top = checked
        # 保存当前位置
        current_pos = self.pos()
        
        # 设置窗口标志
        flags = self.windowFlags()
        if checked:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
            
        # 在更改标志之前隐藏窗口
        self.hide()
        self.setWindowFlags(flags)
        
        # 恢复位置并显示
        self.move(current_pos)
        self.show()
        self.activateWindow()  # 确保窗口获得焦点

    def list_mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
        QListWidget.mousePressEvent(self.list_widget, event)

    def list_mouseMoveEvent(self, event):
        try:
            if not (event.buttons() & Qt.LeftButton):
                return
                
            if not hasattr(self, 'drag_start_position'):
                return
                
            # 检查是否达到拖动的最小距离
            if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
                return

            # 获取当前项
            item = self.list_widget.itemAt(self.drag_start_position)
            if not item:
                return

            # 创建拖拽对象
            drag = QDrag(self.list_widget)
            mimedata = QMimeData()
            mimedata.setText(item.text())
            drag.setMimeData(mimedata)

            # 设置简单的拖拽预览图
            pixmap = QPixmap(100, 30)  # 使用固定大小
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setPen(Qt.white)
            painter.drawText(pixmap.rect(), Qt.AlignCenter, item.text()[:20] + "...")
            painter.end()
            drag.setPixmap(pixmap)
            
            # 设置热点为中心
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
            
            # 开始拖拽
            result = drag.exec_(Qt.CopyAction)
            
            # 拖拽结束后，更新剪贴板
            if result == Qt.CopyAction:
                self.clipboard.setText(item.text())
                # 显示复制成功提示
                current_text = item.text()
                item.setText("✓ 已复制")
                QTimer.singleShot(500, lambda: item.setText(current_text))
                
        except Exception as e:
            print(f"Drag error: {str(e)}")