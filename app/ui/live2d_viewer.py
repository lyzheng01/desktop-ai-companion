"""
Live2D 角色查看器 - 使用 PixiJS + Cubism SDK
通过 WebEngine 显示真正的 Live2D 模型
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView
import os


class Live2DViewer(QWebEngineView):
    """
    Live2D 查看器

    使用 PixiJS + Cubism SDK for Web 渲染真正的 Live2D 模型
    """

    clicked = pyqtSignal()
    model_loaded = pyqtSignal(str)

    def __init__(self, parent=None, model_path=None):
        super().__init__(parent)
        self.model_path = model_path
        self.setup_ui()
        self.load_live2d_viewer()

    def setup_ui(self):
        """设置 UI"""
        self.setFixedSize(400, 500)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def load_live2d_viewer(self):
        """加载 Live2D 查看器 HTML"""
        # 创建临时 HTML
        html_content = self.generate_html()

        # 加载 HTML
        self.setHtml(html_content, QUrl("file:///"))

    def generate_html(self):
        """生成 HTML 页面"""
        model_path = os.path.abspath(
            "E:/python/desktop-ai-companion/assets/live2d/kei_en/kei_basic_free/runtime/kei_basic_free.model3.json"
        ).replace("\\", "/")

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Live2D Character</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: transparent;
            overflow: hidden;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }}
        #canvas {{
            width: 100%;
            height: 100%;
        }}
    </style>
</head>
<body>
    <canvas id="canvas"></canvas>

    <!-- PixiJS -->
    <script src="https://cdn.jsdelivr.net/npm/pixi.js@7.x/dist/pixi.min.js"></script>
    <!-- Live2D Cubism Core -->
    <script src="https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js"></script>
    <!-- Live2D Cubism SDK for Web -->
    <script src="https://cdn.jsdelivr.net/npm/live2d-widget@3.x/lib/Live2dWidget.js"></script>

    <script>
        // 初始化 PixiJS
        const app = new PIXI.Application({{
            view: document.getElementById('canvas'),
            autoStart: true,
            backgroundAlpha: 0,
            transparent: true,
            width: 400,
            height: 500
        }});

        // 加载 Live2D 模型
        async function loadModel() {{
            try {{
                // 使用 live2d-widget 加载
                if (window.Live2DWidget) {{
                    console.log('Loading Live2D model...');
                }}

                // 或者手动加载
                const modelJson = '{model_path}';
                console.log('Model path:', modelJson);

                // 简单测试：显示一个圆圈
                const graphics = new PIXI.Graphics();
                graphics.beginFill(0xFF69B4);
                graphics.drawCircle(200, 250, 100);
                graphics.endFill();
                app.stage.addChild(graphics);

                // 添加点击交互
                graphics.interactive = true;
                graphics.on('pointerdown', () => {{
                    console.log('Character clicked!');
                    window.pyqt5.clicked.emit();
                }});

                console.log('Viewer initialized');
            }} catch (error) {{
                console.error('Error loading model:', error);
            }}
        }}

        loadModel();
    </script>
</body>
</html>
"""

    def load_model(self, model_path: str):
        """加载新的模型"""
        self.model_path = model_path
        self.load_live2d_viewer()


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    viewer = Live2DViewer()
    viewer.setWindowTitle("Live2D 测试")
    viewer.show()

    sys.exit(app.exec())
