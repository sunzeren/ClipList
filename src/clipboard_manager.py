from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                           QListWidget, QListWidgetItem, QLabel, 
                           QPushButton, QApplication,
                           QSystemTrayIcon, QMenu, QAction, QCheckBox)
from PyQt5.QtCore import Qt, QPoint, QMimeData, QTimer, QSize, QMetaObject, Q_ARG, pyqtSlot
from PyQt5.QtGui import (QFont, QIcon, QDrag, QPainter, QPixmap,
                        QColor)
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
from functools import partial

class ClipboardManager(QWidget):
    def __init__(self):
        super().__init__()
        # 添加图标路径
        self.icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'icons')
        if hasattr(sys, '_MEIPASS'):  # 如果是打包后的exe
            self.icon_path = os.path.join(sys._MEIPASS, 'icons')
        
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
        
        # 添加快捷键监听
        self.setup_shortcuts()

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
        
        # 修改自动删除复选框的样式和图标
        self.auto_delete = QCheckBox('使用后删除')
        self.auto_delete.setObjectName('autoDeleteCheckBox')
        self.auto_delete.setChecked(True)
        self.auto_delete.setFixedWidth(90)

        # 添加最小化按钮
        min_btn = QPushButton('─')
        min_btn.setObjectName('minButton')
        min_btn.setFixedSize(30, 30)
        min_btn.clicked.connect(self.showMinimized)

        # 修改置顶按钮样式
        pin_btn = QPushButton()
        pin_btn.setObjectName('pinButton')
        pin_btn.setFixedSize(30, 30)
        pin_btn.setCheckable(True)
        pin_btn.setChecked(True)
        
        # 设置初始图标
        top_icon = QIcon(os.path.join(self.icon_path, 'top.png'))
        untop_icon = QIcon(os.path.join(self.icon_path, 'untop.png'))
        pin_btn.setIcon(top_icon)
        pin_btn.setIconSize(QSize(20, 20))  # 设置图标大小
        
        # 连接信号并传递图标
        pin_btn.clicked.connect(lambda checked: self.toggle_always_on_top(checked, pin_btn, top_icon, untop_icon))

        # 关闭按钮
        close_btn = QPushButton('×')
        close_btn.setObjectName('closeButton')
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(QApplication.quit)
        
        title_layout.addWidget(title)
        title_layout.addStretch()
        title_layout.addWidget(self.auto_delete)
        title_layout.addWidget(pin_btn)
        title_layout.addWidget(min_btn)
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
        
        # 构建复选框图标的完整路径
        checkbox_path = os.path.join(self.icon_path, 'checkbox.png').replace('\\', '/')
        checkbox_checked_path = os.path.join(self.icon_path, 'checkbox-checked.png').replace('\\', '/')
        
        self.setStyleSheet(f'''
            #container {{
                background-color: #2c3e50;
                border-radius: 10px;
                border: 1px solid #34495e;
            }}
            #titleBar {{
                background-color: #34495e;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }}
            #titleLabel {{
                color: #ecf0f1;
            }}
            #pinButton {{
                background-color: transparent;
                border: none;
                padding: 5px;
            }}
            #pinButton:hover {{
                background-color: rgba(52, 73, 94, 0.5);
            }}
            #minButton {{
                background-color: transparent;
                color: #ecf0f1;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }}
            #minButton:hover {{
                background-color: rgba(52, 73, 94, 0.5);
            }}
            #closeButton {{
                background-color: transparent;
                color: #ecf0f1;
                border: none;
                font-size: 20px;
            }}
            #closeButton:hover {{
                background-color: #e74c3c;
            }}
            QListWidget {{
                background-color: #2c3e50;
                border: none;
                color: #ecf0f1;
                padding: 5px;
            }}
            QListWidget::item {{
                background-color: #34495e;
                border-radius: 5px;
                margin: 2px 5px;
                padding: 8px;
            }}
            QListWidget::item:hover {{
                background-color: #3498db;
            }}
            QListWidget::item:selected {{
                background-color: #2980b9;
            }}
            #clearButton {{
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
            }}
            #clearButton:hover {{
                background-color: #2980b9;
            }}
            #bottomBar {{
                background-color: #2c3e50;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }}
            #autoDeleteCheckBox {{
                color: #ecf0f1;
                spacing: 2px;
                padding: 1px 2px;
            }}
            
            #autoDeleteCheckBox::indicator {{
                width: 25px;
                height: 25px;
                border: none;
                background-color: transparent;
                image: url({checkbox_path});
            }}
            
            #autoDeleteCheckBox::indicator:checked {{
                image: url({checkbox_checked_path});
                background-color: transparent;
                border: none;
            }}
            
            #autoDeleteCheckBox::indicator:hover {{
                opacity: 0.8;
            }}
            
            #autoDeleteCheckBox:hover {{
                color: #3498db;
            }}
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
            self.clip_history.insert(0, text)  # 在开头插入新项目
            self.update_list()  # 使用新的更新方法替代直接插入

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
        # 在关闭程序前取消注册快捷键
        keyboard.unhook_all()
        event.accept()

    def toggle_always_on_top(self, checked, btn, top_icon, untop_icon):
        """切换窗口置顶状态"""
        self.always_on_top = checked
        # 保存当前位置
        current_pos = self.pos()
        
        # 设置窗口标志
        flags = self.windowFlags()
        if checked:
            flags |= Qt.WindowStaysOnTopHint
            btn.setIcon(top_icon)
        else:
            flags &= ~Qt.WindowStaysOnTopHint
            btn.setIcon(untop_icon)
            
        # 在更改标志之前隐藏窗口
        self.hide()
        self.setWindowFlags(flags)
        
        # 恢复位置并显示
        self.move(current_pos)
        self.show()

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
                    
                    # 删除后更新列表以重新编号
                    self.update_list()
            
            print(f"After removal: list count={self.list_widget.count()}")
            print(f"Current history: {self.clip_history}")
            
        except Exception as e:
            print(f"Error removing item: {str(e)}")

    def create_list_item(self, text, index):
        item = QListWidgetItem()
        
        # 存储原始文本
        item.setData(Qt.UserRole, text)
        
        # 设置显示文本
        item.setText(f"[{index}] · {text}")
        
        # 设置字体
        font = QFont("Arial", 9)
        item.setFont(font)
        
        # 设置编号的颜色（浅蓝色）
        brush = item.foreground()
        brush.setColor(QColor("#7fb3d5"))
        item.setForeground(brush)
        
        # 设置项目的样式
        item.setSizeHint(QSize(self.list_widget.width() - 20, 32))
        
        return item

    def update_list(self):
        self.list_widget.clear()
        for index, text in enumerate(self.clip_history, 1):
            item = self.create_list_item(text, index)
            self.list_widget.addItem(item)

    def list_mouseMoveEvent(self, event):
        try:
            if not (event.buttons() & Qt.LeftButton):
                return
            
            if not hasattr(self, 'drag_start_position'):
                return
            
            if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
                return

            # 获取当前项
            current_item = self.list_widget.itemAt(self.drag_start_position)
            if not current_item:
                return

            # 获取原始文本（不含编号）
            text = current_item.data(Qt.UserRole)
            
            # 创建拖拽对象
            drag = QDrag(self.list_widget)
            mimedata = QMimeData()
            mimedata.setText(text)
            drag.setMimeData(mimedata)

            # 执行拖拽
            result = drag.exec_(Qt.CopyAction)
            
            # 如果拖拽成功
            if result == Qt.CopyAction:
                row = self.list_widget.row(current_item)
                # 设置剪贴板
                self._internal_copy = True
                self.clipboard.setText(text)
                
                # 如果启用了自动删除，删除该项
                if self.auto_delete.isChecked():
                    QTimer.singleShot(0, lambda: self.remove_item(text, row))
            
        except Exception as e:
            print(f"Drag error: {str(e)}")
        finally:
            if hasattr(self, '_internal_copy'):
                delattr(self, '_internal_copy')

    def handle_paste(self, text, row):
        """统一处理粘贴操作"""
        try:
            # 获取原始文本（不含编号）
            original_text = self.list_widget.item(row).data(Qt.UserRole)
            
            # 设置剪贴板
            self._internal_copy = True
            self.clipboard.setText(original_text)
            
            # 如果用了自动删除，删除该项
            if self.auto_delete.isChecked():
                self.remove_item(original_text, row)  # remove_item 现在会自动更新列表
            else:
                # 显示复制成功提示
                current_item = self.list_widget.item(row)
                if current_item:
                    # 使用相同的字体显示复制成功提示
                    font = QFont("Arial", 9)  # 使用相同的字体大小
                    current_item.setFont(font)
                    current_item.setText("✓ 已复制")
                    QTimer.singleShot(500, lambda: self.update_list())
                
        except Exception as e:
            print(f"Error in handle_paste: {str(e)}")
        finally:
            if hasattr(self, '_internal_copy'):
                delattr(self, '_internal_copy')

    def copy_selected_text(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            label = self.list_widget.itemWidget(current_item)
            # 获取原始文本（不包含编号）
            text = self.clip_history[self.list_widget.row(current_item)]
            self.clipboard.setText(text)

    def setup_shortcuts(self):
        """设置快捷键"""
        # 为数字 1-9 设置快捷键
        for i in range(1, 10):
            keyboard.add_hotkey(f'alt+{i}', self.handle_number_shortcut, args=(i,))

    def handle_number_shortcut(self, number):
        """处理数字快捷键"""
        try:
            # 因为列表索引从0开始，而显示的编号从1开始，所以这里需要减1
            index = number - 1
            if index < len(self.clip_history):
                text = self.clip_history[index]
                print(f"\n=== 剪贴板项目 [{number}] ===")
                print(text)
                print("=" * 30)
                
                try:
                    # 使用 win32clipboard 来设置剪贴板
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardText(text)
                    win32clipboard.CloseClipboard()
                    
                    # 模拟粘贴操作
                    def wait_for_keys_release():
                        # 等待 alt 和数字键释放
                        while any(keyboard.is_pressed(key) for key in ['alt'] + [str(i) for i in range(10)]):
                            time.sleep(0.05)
                    
                    # 等待按键释放后执行粘贴
                    wait_for_keys_release()
                    keyboard.send('ctrl+v')
                    
                    # 如果启用了自动删除，删除该项
                    if self.auto_delete.isChecked():
                        # 使用 QMetaObject.invokeMethod 在主线程中执行删除操作
                        QMetaObject.invokeMethod(self, "delayed_remove_item",
                                               Qt.QueuedConnection,
                                               Q_ARG(str, text),
                                               Q_ARG(int, index))
                finally:
                    # 确保剪贴板被关闭
                    try:
                        win32clipboard.CloseClipboard()
                    except:
                        pass
            else:
                print(f"没有找到编号为 {number} 的剪贴板项目")
        except Exception as e:
            print(f"处理快捷键时出错: {str(e)}")

    # 添加一个新的槽函数来处理延迟删除
    @pyqtSlot(str, int)
    def delayed_remove_item(self, text, index):
        """在主线程中安全地删除项目"""
        self.remove_item(text, index)

    def get_item_by_number(self, number):
        """根据编号获取剪贴板项目"""
        try:
            # 编号从1开始，所以需要减1来获取正确的索引
            index = number - 1
            if 0 <= index < len(self.clip_history):
                return self.clip_history[index]
            return None
        except Exception as e:
            print(f"获取剪贴板项目时出错: {str(e)}")
            return None