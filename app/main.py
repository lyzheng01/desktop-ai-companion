"""
Desktop AI Companion - 桌面 AI 伙伴
主程序入口 - 支持二次元角色动画和拖动
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QMenu
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QCursor

from .config import config, save_config
from .db import init_db
from .ui.chat_window import ChatWindow
from .ui.character_widget import AnimeCharacter


class DesktopRole(QMainWindow):
    """桌面角色窗口 - 透明背景，常驻桌面"""

    def __init__(self):
        super().__init__()
        self.chat_window = None
        self.setup_window()
        self.setup_ui()

    def setup_window(self):
        """设置窗口属性"""
        # 无边框 + 透明背景 + 置顶
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 窗口大小和位置 (从配置加载)
        self.setGeometry(
            config.window_x,
            config.window_y,
            300,
            500
        )

        # 拖动状态
        self._dragging = False
        self._drag_pos = QPoint()

    def setup_ui(self):
        """设置 UI - 使用二次元角色组件"""
        container = QWidget()
        self.setCentralWidget(container)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        container.setLayout(layout)

        # 二次元角色组件（支持图片纹理）
        self.character = AnimeCharacter(self)
        self.character.load_character("live2d")  # 加载 Live2D 模型纹理
        layout.addWidget(self.character)

        # 点击角色呼出聊天窗口
        self.character.clicked.connect(self.show_chat_window)

    def show_chat_window(self):
        """显示聊天窗口"""
        if self.chat_window is None:
            self.chat_window = ChatWindow()
            # 在角色窗口右侧显示
            pos = self.pos()
            self.chat_window.move(pos.x() + 320, pos.y())

        self.chat_window.show()
        self.chat_window.activateWindow()
        self.chat_window.raise_()

    def contextMenuEvent(self, event):
        """右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 8px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #f0f0f0;
            }
        """)

        # 菜单项
        hide_action = menu.addAction("🙈 隐藏")
        hide_action.triggered.connect(self.hide)

        menu.addSeparator()

        # 角色切换子菜单
        char_menu = menu.addMenu("🎭 切换角色")
        live2d_action = char_menu.addAction("📦 Live2D 模型")
        live2d_action.triggered.connect(lambda: self.switch_character("live2d"))

        sakura_action = char_menu.addAction("🌸 小樱 (Sakura)")
        sakura_action.triggered.connect(lambda: self.switch_character("sakura"))

        shiro_action = char_menu.addAction("👓 阿白 (Shiro)")
        shiro_action.triggered.connect(lambda: self.switch_character("shiro"))

        nana_action = char_menu.addAction("🐱 奈奈 (Nana)")
        nana_action.triggered.connect(lambda: self.switch_character("nana"))

        menu.addSeparator()

        settings_action = menu.addAction("⚙️ 设置")
        settings_action.triggered.connect(self.open_settings)

        menu.addSeparator()

        quit_action = menu.addAction("❌ 退出")
        quit_action.triggered.connect(QApplication.instance().quit)

        # 在鼠标位置显示
        menu.exec(QCursor.pos())

    def switch_character(self, name: str):
        """切换角色"""
        self.character.load_character(name)
        print(f"🎭 切换到角色：{name}")

    def open_settings(self, event):
        """打开设置"""
        print("⚙️ 打开设置")

    # ============== 拖动支持 ==============

    def mousePressEvent(self, event):
        """鼠标按下 - 开始拖动"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动 - 拖动窗口"""
        if self._dragging:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        """鼠标释放 - 结束拖动"""
        self._dragging = False
        # 保存新位置到配置
        config.window_x = self.x()
        config.window_y = self.y()
        save_config()
        print(f"💾 保存位置：({self.x()}, {self.y()})")

    def closeEvent(self, event):
        """关闭窗口"""
        # 如果有聊天窗口，一起关闭
        if self.chat_window:
            self.chat_window.close()
        event.accept()


def main():
    # 初始化数据库
    init_db()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)

    # 设置应用信息
    app.setApplicationName("Desktop AI Companion")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("AI Companion Lab")

    # 创建桌面角色窗口
    desktop_role = DesktopRole()
    desktop_role.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
