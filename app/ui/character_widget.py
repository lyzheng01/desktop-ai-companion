"""
二次元角色组件 - 使用完整角色图片

说明：Live2D 模型需要专业渲染器，这里用单张完整图片代替
"""
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QTransform, QIcon, QBitmap, QFont
import math
import os


class AnimeCharacter(QWidget):
    """
    二次元角色组件

    显示完整的二次元角色图片
    """

    clicked = pyqtSignal()
    drag_started = pyqtSignal()
    drag_finished = pyqtSignal()

    # 内置的二次元角色图片（Base64 编码的简单角色）
    CHARACTERS = {
        "sakura": """
            <!-- 粉色短发少女 -->
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 300">
                <!-- 头发 -->
                <ellipse cx="100" cy="80" rx="70" ry="60" fill="#FFB6C1"/>
                <ellipse cx="100" cy="60" rx="75" ry="40" fill="#FF69B4"/>
                <!-- 脸 -->
                <ellipse cx="100" cy="90" rx="50" ry="55" fill="#FFE4E1"/>
                <!-- 眼睛 -->
                <ellipse cx="80" cy="85" rx="12" ry="15" fill="#4A4A4A"/>
                <ellipse cx="120" cy="85" rx="12" ry="15" fill="#4A4A4A"/>
                <circle cx="83" cy="80" r="5" fill="white"/>
                <circle cx="123" cy="80" r="5" fill="white"/>
                <!-- 嘴巴 -->
                <path d="M 90 105 Q 100 112 110 105" stroke="#FF69B4" stroke-width="2" fill="none"/>
                <!-- 身体 -->
                <ellipse cx="100" cy="180" rx="45" ry="70" fill="#FFB6C1"/>
                <!-- 腮红 -->
                <ellipse cx="70" cy="100" rx="8" ry="5" fill="#FFB6C1" opacity="0.6"/>
                <ellipse cx="130" cy="100" rx="8" ry="5" fill="#FFB6C1" opacity="0.6"/>
            </svg>
        """,
        "shiro": """
            <!-- 白发少年 -->
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 300">
                <!-- 头发 -->
                <ellipse cx="100" cy="70" rx="65" ry="50" fill="#E8E8E8"/>
                <!-- 脸 -->
                <ellipse cx="100" cy="90" rx="50" ry="55" fill="#FFF8DC"/>
                <!-- 眼镜 -->
                <rect x="65" y="80" width="25" height="18" rx="3" stroke="#666" stroke-width="2" fill="rgba(200,230,255,0.3)"/>
                <rect x="110" y="80" width="25" height="18" rx="3" stroke="#666" stroke-width="2" fill="rgba(200,230,255,0.3)"/>
                <line x1="90" y1="89" x2="110" y2="89" stroke="#666" stroke-width="2"/>
                <!-- 眼睛 -->
                <ellipse cx="77" cy="88" rx="8" ry="10" fill="#2C3E50"/>
                <ellipse cx="122" cy="88" rx="8" ry="10" fill="#2C3E50"/>
                <circle cx="79" cy="84" r="3" fill="white"/>
                <circle cx="124" cy="84" r="3" fill="white"/>
                <!-- 嘴巴 -->
                <path d="M 92 110 Q 100 113 108 110" stroke="#CC8899" stroke-width="2" fill="none"/>
                <!-- 身体 -->
                <ellipse cx="100" cy="180" rx="45" ry="70" fill="#D3D3D3"/>
            </svg>
        """,
        "nana": """
            <!-- 猫耳少女 -->
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 300">
                <!-- 猫耳 -->
                <polygon points="50,50 70,20 90,50" fill="#2A2A2A"/>
                <polygon points="110,50 130,20 150,50" fill="#2A2A2A"/>
                <polygon points="55,48 70,28 85,48" fill="#FFB6C1"/>
                <polygon points="115,48 130,28 145,48" fill="#FFB6C1"/>
                <!-- 头发 -->
                <ellipse cx="100" cy="75" rx="70" ry="55" fill="#2A2A2A"/>
                <!-- 脸 -->
                <ellipse cx="100" cy="90" rx="50" ry="55" fill="#FFE4E1"/>
                <!-- 眼睛（大） -->
                <ellipse cx="75" cy="85" rx="15" ry="18" fill="#FFA500"/>
                <ellipse cx="125" cy="85" rx="15" ry="18" fill="#FFA500"/>
                <circle cx="78" cy="80" r="7" fill="white"/>
                <circle cx="128" cy="80" r="7" fill="white"/>
                <circle cx="75" cy="90" r="3" fill="#2A2A2A"/>
                <circle cx="125" cy="90" r="3" fill="#2A2A2A"/>
                <!-- 嘴巴 -->
                <path d="M 90 110 Q 100 118 110 110" stroke="#FF69B4" stroke-width="2" fill="none"/>
                <!-- 胡须 -->
                <line x1="55" y1="100" x2="40" y2="95" stroke="#FFB6C1" stroke-width="2"/>
                <line x1="55" y1="105" x2="40" y2="105" stroke="#FFB6C1" stroke-width="2"/>
                <line x1="145" y1="100" x2="160" y2="95" stroke="#FFB6C1" stroke-width="2"/>
                <line x1="145" y1="105" x2="160" y2="105" stroke="#FFB6C1" stroke-width="2"/>
                <!-- 身体 -->
                <ellipse cx="100" cy="180" rx="45" ry="70" fill="#1A1A1A"/>
            </svg>
        """,
    }

    def __init__(self, parent=None, character_type="sakura"):
        super().__init__(parent)
        self.character_type = character_type
        self.is_blinking = False
        self.original_pixmap = None
        self.current_pixmap = None

        # 拖动状态
        self._dragging = False
        self._drag_start_pos = QPoint()

        self.setup_ui()
        self.setup_timers()
        self.load_character(character_type)

    def setup_ui(self):
        """设置 UI"""
        self.setFixedSize(250, 350)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        # 角色图片标签
        self.image_label = QLabel(self)
        self.image_label.setGeometry(0, 0, 250, 350)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background: transparent;")

        # 启用鼠标跟踪
        self.setMouseTracking(True)
        self.image_label.setMouseTracking(True)

    def setup_timers(self):
        """设置定时器"""
        # 眨眼定时器
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.do_blink)
        self.blink_timer.start(3000)

        # 呼吸动画
        self.breath_timer = QTimer(self)
        self.breath_timer.timeout.connect(self.do_breath)
        self.breath_timer.start(1500)
        self.breath_offset = 0

    def load_character(self, character_type: str):
        """加载角色"""
        self.character_type = character_type

        svg_data = self.CHARACTERS.get(character_type, self.CHARACTERS["sakura"])

        # 从 SVG 创建 QPixmap
        pixmap = QPixmap()
        pixmap.loadFromData(svg_data.encode('utf-8'), 'SVG')

        if pixmap.isNull():
            # SVG 加载失败，用 emoji
            self.image_label.setText("🤖")
            self.image_label.setStyleSheet("font-size: 150px; background: transparent;")
            return

        self.original_pixmap = pixmap

        # 缩放
        scaled = pixmap.scaled(
            200, 300,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.current_pixmap = scaled
        self.image_label.setPixmap(scaled)
        self.image_label.setText("")

    # ============ 动画 ============

    def do_breath(self):
        """呼吸动画"""
        self.breath_offset = (self.breath_offset + 1) % 100
        scale = 1.0 + 0.02 * math.sin(self.breath_offset * math.pi / 50)

        if self.original_pixmap:
            scaled = self.original_pixmap.scaled(
                int(200 * scale), int(300 * scale),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)

    def do_blink(self):
        """眨眼动画"""
        import random
        if random.random() < 0.5 and not self.is_blinking:
            self.is_blinking = True
            self.image_label.setStyleSheet("opacity: 0.8;")
            QTimer.singleShot(150, self.open_eyes)

    def open_eyes(self):
        """睁开眼睛"""
        self.is_blinking = False
        self.image_label.setStyleSheet("background: transparent;")

    def wave(self):
        """挥手"""
        print("👋 挥手")

    # ============ 鼠标交互 ============

    def mousePressEvent(self, event):
        """鼠标按下"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_pos = event.globalPosition().toPoint() - self.pos()
            self.clicked.emit()
            self.wave()

    def mouseMoveEvent(self, event):
        """拖动"""
        if self._dragging:
            new_pos = event.globalPosition().toPoint() - self._drag_start_pos
            self.move(new_pos)

    def mouseReleaseEvent(self, event):
        """释放"""
        if self._dragging:
            self._dragging = False
            self.drag_finished.emit()
            # 保存位置
            try:
                from .config import config, save_config
                config.window_x = self.x()
                config.window_y = self.y()
                save_config()
            except:
                pass


if __name__ == "__main__":
    app = QApplication([])

    character = AnimeCharacter("sakura")
    character.show()

    app.exec()
