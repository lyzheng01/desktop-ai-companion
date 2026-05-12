"""
测试显示 - 查看 Live2D 纹理的实际内容
"""
import sys

# 检查纹理文件
texture_path = "E:/python/desktop-ai-companion/assets/live2d/kei_en/kei_basic_free/runtime/kei_basic_free.2048/texture_00.png"

try:
    from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QPixmap

    app = QApplication(sys.argv)

    # 创建窗口
    window = QWidget()
    window.setWindowTitle("Live2D 纹理预览")
    window.setGeometry(100, 100, 600, 600)

    layout = QVBoxLayout()
    window.setLayout(layout)

    # 加载纹理
    pixmap = QPixmap(texture_path)
    print(f"纹理大小：{pixmap.width()}x{pixmap.height()}")
    print(f"纹理是否有效：{not pixmap.isNull()}")

    if not pixmap.isNull():
        # 缩放显示
        scaled = pixmap.scaled(512, 512, Qt.AspectRatioMode.KeepAspectRatio)

        label = QLabel()
        label.setPixmap(scaled)
        layout.addWidget(label)

        window.show()
        print("窗口已打开，请查看 Live2D 纹理图片")
        print("提示：这张图是'展开图'，所有部件分散排列，需要 Live2D 渲染器组装")
    else:
        print("无法加载纹理图片")

    sys.exit(app.exec())

except Exception as e:
    print(f"错误：{e}")
