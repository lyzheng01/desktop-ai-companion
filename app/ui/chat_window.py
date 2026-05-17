"""
聊天窗口模块
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ..db import get_messages, save_message


class ChatWindow(QWidget):
    """聊天窗口"""

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_window()
        self.setup_ui()
        self.load_history()

    def setup_window(self):
        """设置窗口属性"""
        self.setWindowTitle("AI 小伙伴")
        self.setGeometry(200, 200, 400, 500)

        # 保持在角色窗口上方
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )

    def setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # 顶部标题栏
        header = self.create_header()
        layout.addWidget(header)

        # 消息区域
        self.message_area = self.create_message_area()
        layout.addWidget(self.message_area)

        # 输入区域
        input_area = self.create_input_area()
        layout.addWidget(input_area)

    def create_header(self) -> QWidget:
        """创建头部"""
        header = QWidget()
        header.setFixedHeight(50)
        header.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
        """)

        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(15, 0, 15, 0)

        # 角色名字
        self.role_name = QLabel("小艾")
        self.role_name.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        h_layout.addWidget(self.role_name)

        h_layout.addStretch()

        # 状态指示
        self.status_label = QLabel("● 在线")
        self.status_label.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px;")
        h_layout.addWidget(self.status_label)

        return header

    def create_message_area(self) -> QWidget:
        """创建消息区域"""
        container = QWidget()
        container.setStyleSheet("background: #f5f7fa;")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none; background: transparent;")

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()

        scroll.setWidget(self.messages_container)
        layout.addWidget(scroll)

        return container

    def create_input_area(self) -> QWidget:
        """创建输入区域"""
        container = QWidget()
        container.setFixedHeight(80)
        container.setStyleSheet("""
            QWidget {
                background: white;
                border-top: 1px solid #e0e0e0;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 输入框
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("输入消息... (Shift+Enter 换行)")
        self.input_field.setMaximumHeight(60)
        self.input_field.setFont(QFont("Microsoft YaHei", 10))
        self.input_field.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                background: white;
            }
            QTextEdit:focus {
                border-color: #667eea;
            }
        """)
        layout.addWidget(self.input_field)

        # 发送按钮
        self.send_button = QPushButton("发送")
        self.send_button.setFixedWidth(70)
        self.send_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                opacity: 0.9;
            }
            QPushButton:pressed {
                opacity: 0.8;
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        layout.addWidget(self.send_button)

        # Enter 发送
        self.input_field.installEventFilter(self)

        return container

    def eventFilter(self, obj, event):
        """事件过滤 - Enter 发送"""
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent

        if obj == self.input_field and event.type() == QEvent.Type.KeyPress:
            key_event = event
            if key_event.key() == Qt.Key.Key_Return and not key_event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def send_message(self):
        """发送消息"""
        text = self.input_field.toPlainText().strip()
        if not text:
            return

        # 保存并显示用户消息
        save_message("user", text)
        self.add_message("user", text)
        self.input_field.clear()

        # TODO: 调用 AI 接口获取回复
        # 暂时显示占位回复
        self.add_message("assistant", "收到！我正在思考... 🤔")
        save_message("assistant", "收到！我正在思考... 🤔")

    def add_message(self, role: str, content: str):
        """添加消息到界面"""
        msg_widget = QWidget()
        msg_widget.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(msg_widget)
        layout.setContentsMargins(10, 8, 10, 8)

        # 角色标签
        role_label = QLabel("我" if role == "user" else "小艾")
        role_label.setStyleSheet(f"""
            QLabel {{
                color: {"#667eea" if role == "assistant" else "#666"};
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        layout.addWidget(role_label)

        # 消息内容
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content_label.setStyleSheet("color: #333; font-size: 14px;")
        layout.addWidget(content_label)

        # 添加到布局 (用户消息靠右，AI 消息靠左)
        if role == "user":
            self.messages_layout.addWidget(msg_widget, alignment=Qt.AlignmentFlag.AlignRight)
        else:
            self.messages_layout.addWidget(msg_widget, alignment=Qt.AlignmentFlag.AlignLeft)

        # 滚动到底部
        scroll_area = self.findChild(QScrollArea)
        if scroll_area:
            scrollbar = scroll_area.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    def load_history(self):
        """加载历史消息"""
        messages = get_messages(limit=20)
        for msg in messages:
            self.add_message(msg["role"], msg["content"])

    def closeEvent(self, event):
        """关闭窗口时触发"""
        self.closed.emit()
        event.accept()
