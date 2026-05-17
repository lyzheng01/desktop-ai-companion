"""
直接显示 Live2D 纹理图片
"""
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
import sys

app = QApplication(sys.argv)

# 纹理路径
texture_path = "E:/python/desktop-ai-companion/assets/live2d/kei_en/kei_basic_free/runtime/kei_basic_free.2048/texture_00.png"

# 创建窗口
window = QWidget()
window.setWindowTitle("Live2D 纹理查看器 - Kei")
window.setGeometry(100, 100, 800, 600)

layout = QVBoxLayout()
window.setLayout(layout)

# 加载纹理
pixmap = QPixmap(texture_path)
print(f"纹理大小：{pixmap.width()}x{pixmap.height()}")

# 缩放显示
scaled = pixmap.scaled(600, 600, Qt.AspectRatioMode.KeepAspectRatio)

label = QLabel()
label.setPixmap(scaled)
label.setAlignment(Qt.AlignmentFlag.AlignCenter)
layout.addWidget(label)

# 说明
info = QLabel("""
<b>Live2D 纹理说明：</b><br>
这是一张"展开图"，包含所有分散的部件（眼睛、头发、身体等）。<br>
需要 Live2D 渲染器按照 .moc3 文件的指示来组装这些部件。<br>
<br>
<b>问题：</b>PyQt6 无法读取 .moc3 模型文件，所以无法正确组装部件。<br>
<b>解决：</b>需要使用 Live2D Cubism SDK for Web 或 Native 渲染器。
""")
info.setWordWrap(True)
layout.addWidget(info)

# 按钮
btn_layout = QHBoxLayout()

btn1 = QPushButton("显示原始大小")
btn1.clicked.connect(lambda: label.setPixmap(pixmap.scaled(800, 800, Qt.AspectRatioMode.KeepAspectRatio)))
btn_layout.addWidget(btn1)

btn2 = QPushButton("显示缩放 (512x512)")
btn2.clicked.connect(lambda: label.setPixmap(pixmap.scaled(512, 512, Qt.AspectRatioMode.KeepAspectRatio)))
btn_layout.addWidget(btn2)

btn3 = QPushButton("显示实际大小")
btn3.clicked.connect(lambda: label.setPixmap(pixmap))
btn_layout.addWidget(btn3)

layout.addLayout(btn_layout)

window.show()
print("窗口已打开")
print("观察纹理图片：所有五官、头发、身体部件都是分散排列的")

sys.exit(app.exec())
