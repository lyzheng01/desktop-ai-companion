"""
Live2D 角色组件 - 简化版
使用 PyQt6 加载 Live2D 模型的纹理和部件，实现基础动画
"""
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QTransform
import json
import os


class Live2DPart(QLabel):
    """Live2D 模型的一个部件"""

    def __init__(self, parent=None, name=""):
        super().__init__(parent)
        self.part_name = name
        self.setMouseTracking(True)

    def set_rotation(self, angle: float):
        """旋转部件"""
        transform = QTransform()
        transform.translate(self.width() / 2, self.height() / 2)
        transform.rotate(angle)
        transform.translate(-self.width() / 2, -self.height() / 2)
        self.setTransform(transform)


class Live2DCharacter(QWidget):
    """
    Live2D 角色组件

    加载 .moc3 模型文件并渲染
    """

    clicked = pyqtSignal()
    head_clicked = pyqtSignal()
    body_clicked = pyqtSignal()

    def __init__(self, parent=None, model_path=None):
        super().__init__(parent)
        self.model_path = model_path
        self.model_data = None
        self.parts = {}
        self.current_motion = "idle"

        self.setup_ui()
        self.setup_timers()

        if model_path:
            self.load_model(model_path)

    def setup_ui(self):
        """设置 UI"""
        self.setFixedSize(300, 500)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        # 主容器
        self.container = QWidget(self)
        self.container.setGeometry(50, 50, 200, 400)
        self.container.setStyleSheet("background: transparent;")

        # 创建角色部件（用占位图，后续加载真实纹理）
        self._create_parts()

    def _create_parts(self):
        """创建角色部件"""
        # 头发（后）
        self.hair_back = QLabel(self.container)
        self.hair_back.setGeometry(20, 50, 160, 100)
        self.hair_back.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4A3728, stop:1 #2C1810);
            border-radius: 80px 80px 40px 40px;
        """)

        # 身体
        self.body = QLabel(self.container)
        self.body.setGeometry(50, 150, 100, 180)
        self.body.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #6B8E23, stop:1 #556B2F);
            border-radius: 50px;
        """)

        # 头发（前）
        self.hair_front = QLabel(self.container)
        self.hair_front.setGeometry(30, 40, 140, 80)
        self.hair_front.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4A3728, stop:1 #2C1810);
            border-radius: 70px 70px 30px 30px;
        """)

        # 脸
        self.face = QLabel(self.container)
        self.face.setGeometry(40, 60, 120, 100)
        self.face.setStyleSheet("""
            background: #FFE4C4;
            border-radius: 60px;
        """)

        # 眼睛左
        self.eye_l = QLabel(self.container)
        self.eye_l.setGeometry(60, 90, 25, 30)
        self.eye_l.setStyleSheet("""
            background: #2C1810;
            border-radius: 15px;
        """)

        # 眼睛右
        self.eye_r = QLabel(self.container)
        self.eye_r.setGeometry(115, 90, 25, 30)
        self.eye_r.setStyleSheet("""
            background: #2C1810;
            border-radius: 15px;
        """)

        # 眼睛高光左
        self.eye_highlight_l = QLabel(self.container)
        self.eye_highlight_l.setGeometry(68, 95, 10, 10)
        self.eye_highlight_l.setStyleSheet("""
            background: white;
            border-radius: 5px;
        """)

        # 眼睛高光右
        self.eye_highlight_r = QLabel(self.container)
        self.eye_highlight_r.setGeometry(123, 95, 10, 10)
        self.eye_highlight_r.setStyleSheet("""
            background: white;
            border-radius: 5px;
        """)

        # 嘴巴
        self.mouth = QLabel(self.container)
        self.mouth.setGeometry(85, 135, 30, 10)
        self.mouth.setStyleSheet("""
            background: transparent;
            border: 2px solid #D2691E;
            border-top: none;
            border-radius: 0 0 15px 15px;
        """)

        # 左臂
        self.arm_l = QLabel(self.container)
        self.arm_l.setGeometry(10, 160, 45, 120)
        self.arm_l.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #6B8E23, stop:1 #556B2F);
            border-radius: 25px;
        """)

        # 右臂
        self.arm_r = QLabel(self.container)
        self.arm_r.setGeometry(145, 160, 45, 120)
        self.arm_r.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #6B8E23, stop:1 #556B2F);
            border-radius: 25px;
        """)

        # 设置鼠标交互
        self._setup_interactions()

    def _setup_interactions(self):
        """设置交互"""
        for part in [self.face, self.eye_l, self.eye_r, self.hair_front]:
            part.mousePressEvent = lambda e: self._on_head_click(e)

        self.body.mousePressEvent = lambda e: self._on_body_click(e)
        self.arm_l.mousePressEvent = lambda e: self._on_arm_click(e)
        self.arm_r.mousePressEvent = lambda e: self._on_arm_click(e)

    def _on_head_click(self, event):
        """点击头部"""
        self.head_clicked.emit()
        self.clicked.emit()
        self.play_motion("tap_head")

    def _on_body_click(self, event):
        """点击身体"""
        self.body_clicked.emit()
        self.clicked.emit()
        self.play_motion("tap_body")

    def _on_arm_click(self, event):
        """点击手臂"""
        self.clicked.emit()
        self.play_motion("wave")

    def setup_timers(self):
        """设置定时器"""
        # 呼吸动画
        self.breath_timer = QTimer(self)
        self.breath_timer.timeout.connect(self.do_breath)
        self.breath_timer.start(1000)
        self.breath_phase = 0

        # 眨眼
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self.do_blink)
        self.blink_timer.start(4000)

        # 随机动作
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.do_random_action)
        self.idle_timer.start(5000)

    def load_model(self, model_path: str):
        """加载 Live2D 模型"""
        self.model_path = model_path

        # 加载模型配置文件
        model_json = model_path
        if os.path.exists(model_json):
            with open(model_json, 'r', encoding='utf-8') as f:
                self.model_data = json.load(f)
            print(f"✓ Loaded model: {model_json}")

            # 加载纹理
            if 'FileReferences' in self.model_data:
                refs = self.model_data['FileReferences']
                if 'Textures' in refs:
                    texture_path = refs['Textures'][0]
                    texture_full_path = os.path.join(os.path.dirname(model_json), texture_path)
                    print(f"Texture path: {texture_full_path}")
                    # 后续加载纹理到部件

    def do_breath(self):
        """呼吸动画"""
        self.breath_phase = (self.breath_phase + 1) % 4
        offset = int(2 * (self.breath_phase % 2))

        # 轻微上下浮动
        self.container.move(self.container.x(), 50 + offset)

    def do_blink(self):
        """眨眼动画"""
        import random
        if random.random() < 0.5:
            # 闭眼
            self.eye_l.setStyleSheet("background: #2C1810; border-radius: 2px;")
            self.eye_r.setStyleSheet("background: #2C1810; border-radius: 2px;")
            self.eye_highlight_l.hide()
            self.eye_highlight_r.hide()

            # 0.2 秒后睁眼
            QTimer.singleShot(200, self.open_eyes)

    def open_eyes(self):
        """睁开眼睛"""
        self.eye_l.setStyleSheet("""
            background: #2C1810;
            border-radius: 15px;
        """)
        self.eye_r.setStyleSheet("""
            background: #2C1810;
            border-radius: 15px;
        """)
        self.eye_highlight_l.show()
        self.eye_highlight_r.show()

    def do_random_action(self):
        """随机动作"""
        import random
        actions = ["wave", "tilt_head", "smile", "surprised"]
        weights = [0.3, 0.2, 0.3, 0.1]

        action = random.choices(actions, weights=weights)[0]
        self.play_motion(action)

    def play_motion(self, motion_name: str):
        """播放动作"""
        motions = {
            "idle": self._motion_idle,
            "wave": self._motion_wave,
            "tilt_head": self._motion_tilt_head,
            "smile": self._motion_smile,
            "surprised": self._motion_surprised,
            "tap_head": self._motion_tap_head,
            "tap_body": self._motion_tap_body,
        }

        if motion_name in motions:
            motions[motion_name]()

    # ============ 动作实现 ============

    def _motion_idle(self):
        """待机动作"""
        pass  # 由呼吸定时器处理

    def _motion_wave(self):
        """挥手"""
        self.arm_r.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #6B8E23, stop:1 #556B2F);
            border-radius: 25px;
        """)
        # 0.5 秒后恢复
        QTimer.singleShot(500, lambda: self.arm_r.setStyleSheet(self.arm_l.styleSheet()))

    def _motion_tilt_head(self):
        """偏头"""
        self.face.setGeometry(42, 58, 120, 100)
        QTimer.singleShot(300, lambda: self.face.setGeometry(40, 60, 120, 100))

    def _motion_smile(self):
        """微笑"""
        self.mouth.setStyleSheet("""
            background: transparent;
            border: 3px solid #D2691E;
            border-top: none;
            border-radius: 0 0 20px 20px;
        """)
        QTimer.singleShot(1000, lambda: self.mouth.setStyleSheet("""
            background: transparent;
            border: 2px solid #D2691E;
            border-top: none;
            border-radius: 0 0 15px 15px;
        """))

    def _motion_surprised(self):
        """惊讶"""
        self.eye_l.setStyleSheet("background: #2C1810; border-radius: 20px;")
        self.eye_r.setStyleSheet("background: #2C1810; border-radius: 20px;")
        self.mouth.setStyleSheet("""
            background: #D2691E;
            border-radius: 10px;
        """)
        QTimer.singleShot(800, self.open_eyes)
        QTimer.singleShot(800, lambda: self.mouth.setStyleSheet("""
            background: transparent;
            border: 2px solid #D2691E;
            border-top: none;
            border-radius: 0 0 15px 15px;
        """))

    def _motion_tap_head(self):
        """点击头部反应"""
        self._motion_surprised()

    def _motion_tap_body(self):
        """点击身体反应"""
        self._motion_smile()

    def mousePressEvent(self, event):
        """点击角色"""
        self.clicked.emit()
        if event.button() == Qt.MouseButton.LeftButton:
            self.play_motion("wave")


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    character = Live2DCharacter()
    character.show()

    sys.exit(app.exec())
