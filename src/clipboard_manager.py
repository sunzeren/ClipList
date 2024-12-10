from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                           QListWidget, QLabel, QPushButton, QApplication,
                           QSystemTrayIcon, QMenu, QAction, QCheckBox)
from PyQt5.QtCore import Qt, QPoint, QMimeData, QTimer
from PyQt5.QtGui import QFont, QIcon, QDrag, QPainter, QPixmap
import win32gui
import win32api
import win32con
import time
from win32gui import GetForegroundWindow, GetWindowText
import win32clipboard
from ctypes import windll
import keyboard
import os
import sys

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
        self.clip_history = []
        self.list_widget = None  # 初始化为 None
        self.init_ui()
        self.setup_clipboard()
        
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
        
        # 添加"使用后删除"复选框
        self.auto_delete = QCheckBox('使用后删除')
        self.auto_delete.setObjectName('autoDeleteCheckBox')
        self.auto_delete.setChecked(True)  # 默认选中
        
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
        title_layout.addWidget(self.auto_delete)  # 添加到标题栏
        title_layout.addWidget(pin_btn)
        title_layout.addWidget(close_btn)
        
        # 列表区域
        self.list_widget = QListWidget()
        self.list_widget.setObjectName('clipList')
        self.list_widget.itemEntered.connect(self.on_item_hover)
        self.list_widget.setMouseTracking(True)
        self.list_widget.setDragEnabled(True)
        self.list_widget.setDragDropMode(QListWidget.DragOnly)
        
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
            #autoDeleteCheckBox {
                color: #ecf0f1;
                spacing: 5px;
            }
            
            #autoDeleteCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 1px solid #7f8c8d;
            }
            
            #autoDeleteCheckBox::indicator:unchecked {
                background-color: transparent;
            }
            
            #autoDeleteCheckBox::indicator:checked {
                background-color: #3498db;
                border: 1px solid #2980b9;
            }
            
            #autoDeleteCheckBox::indicator:hover {
                border: 1px solid #3498db;
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
        # 只有当文本不在历史记录中，且不是我们自己触发的复制操作时才添加
        if text and text not in self.clip_history and not hasattr(self, '_internal_copy'):
            self.clip_history.append(text)
            self.list_widget.insertItem(0, text)

    def on_item_hover(self, item):
        # 当鼠标悬停时，只选中项目但不触发粘贴
        self.list_widget.setCurrentItem(item)

    def on_item_paste(self, item):
        try:
            text = item.text()
            row = self.list_widget.row(item)
            self.handle_paste(text, row)
        except Exception as e:
            print(f"Error in on_item_paste: {str(e)}")

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
        
        # 修改图标加载逻辑
        icon = QIcon()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'icons', 'clipboard.png')
        if hasattr(sys, '_MEIPASS'):  # 如果是打包后的exe
            icon_path = os.path.join(sys._MEIPASS, 'icons', 'clipboard.png')
        
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
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

    def remove_item(self, text, row):
        """统一处理删除项目的方法"""
        try:
            print(f"Removing item: text={text}, row={row}")
            print(f"Before removal: list count={self.list_widget.count()}")
            
            # 从列表控件中删除
            if row >= 0 and row < self.list_widget.count():
                removed_item = self.list_widget.takeItem(row)
                if removed_item:
                    # 从历史记录中删除
                    if text in self.clip_history:
                        self.clip_history.remove(text)
                    del removed_item
                    print(f"Successfully removed item at row {row}")
            
            print(f"After removal: list count={self.list_widget.count()}")
            print(f"Current history: {self.clip_history}")
            
        except Exception as e:
            print(f"Error removing item: {str(e)}")

    def list_mouseMoveEvent(self, event):
        try:
            if not (event.buttons() & Qt.LeftButton):
                return
                
            if not hasattr(self, 'drag_start_position'):
                return
                
            if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
                return

            # 获取当前项
            item = self.list_widget.itemAt(self.drag_start_position)
            if not item:
                print("No item found at drag position")
                return

            # 保存项目信息
            text = item.text()
            row = self.list_widget.row(item)
            print(f"Starting drag: text={text}, row={row}")

            # 创建拖拽对象
            drag = QDrag(self.list_widget)
            mimedata = QMimeData()
            mimedata.setText(text)
            drag.setMimeData(mimedata)

            # 设置拖拽预览图
            pixmap = QPixmap(100, 30)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setPen(Qt.white)
            painter.drawText(pixmap.rect(), Qt.AlignCenter, text[:20] + "...")
            painter.end()
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

            # 执行拖拽
            result = drag.exec_(Qt.CopyAction)
            
            # 如果拖拽成功
            if result == Qt.CopyAction:
                # 设置剪贴板
                self._internal_copy = True
                self.clipboard.setText(text)
                delattr(self, '_internal_copy')
                
                print(f"Content copied to clipboard: {text}")
                
                # 如果启用了自动删除，删除该项
                if self.auto_delete.isChecked():
                    QTimer.singleShot(0, lambda: self.remove_item(text, row))
                
        except Exception as e:
            print(f"Drag error: {str(e)}")
            if hasattr(self, '_internal_copy'):
                delattr(self, '_internal_copy')

    def handle_paste(self, text, row):
        """统一处理粘贴操作"""
        try:
            # 设置剪贴板
            self._internal_copy = True
            self.clipboard.setText(text)
            delattr(self, '_internal_copy')
            
            print(f"Content copied to clipboard: {text}")
            
            # 如果启用了自动删除，删除该项
            if self.auto_delete.isChecked():
                self.remove_item(text, row)
            else:
                # 显示复制成功提示
                current_item = self.list_widget.item(row)
                if current_item:
                    current_item.setText("✓ 已复制")
                    QTimer.singleShot(500, lambda: current_item.setText(text))
                    
        except Exception as e:
            print(f"Error in handle_paste: {str(e)}")
            if hasattr(self, '_internal_copy'):
                delattr(self, '_internal_copy')