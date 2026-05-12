# Live2D 角色系统使用说明

## 已完成的功能

### 1. 角色动画系统

#### 方案 A：骨骼动画版（推荐）
- **位置**: `app/ui/live2d_widget.py`
- **特点**: 
  - 部件分离（头、身体、手臂、眼睛、嘴巴）
  - 支持旋转、缩放、平移
  - 可播放预设动作

#### 方案 B：帧动画版
- **位置**: `app/ui/character_widget.py`
- **特点**:
  - 使用预渲染的 PNG 序列
  - 适合简单表情变化

---

## 动作系统

### 基础动作（已实现）

| 动作名称 | 触发方式 | 效果 |
|---------|---------|------|
| `idle` | 默认状态 | 呼吸动画（轻微上下浮动） |
| `wave` | 点击手臂 | 挥手打招呼 |
| `bow` | - | 弯腰鞠躬 |
| `smile` | 随机触发 | 微笑（嘴巴变弯） |
| `tilt_head` | 随机触发 | 偏头 |
| `surprised` | 鼠标移入 | 惊讶表情（眼睛变大） |
| `tap_head` | 点击头部 | 头部反应 |
| `tap_body` | 点击身体 | 身体反应 |

### 动作调用示例

```python
# 挥手
character.wave()

# 弯腰
character.bow()

# 微笑
character.smile()

# 偏头
character.tilt_head()

# 惊讶
character.surprised()
```

---

## 交互方式

### 鼠标交互
- **点击角色** → 挥手打招呼
- **点击头部** → 惊讶表情
- **点击身体** → 微笑
- **点击手臂** → 挥手
- **鼠标移入** → 惊讶
- **鼠标移出** → 恢复

### 自动行为
- **呼吸** (1 秒周期) - 身体轻微上下浮动
- **眨眼** (4 秒间隔，50% 概率) - 自动眨眼
- **随机动作** (5 秒间隔) - 随机播放动作

---

## Live2D 模型集成

### 当前模型
- **模型**: Kei (Live2D 官方免费样例)
- **位置**: `assets/live2d/kei_en/`
- **包含**:
  - `kei_basic_free` - 基础版本
  - `kei_vowels_pro` - 口型同步版本

### 模型文件结构
```
kei_en/
├── kei_basic_free/
│   ├── runtime/
│   │   ├── kei_basic_free.moc3      # 模型文件
│   │   ├── kei_basic_free.model3.json  # 模型配置
│   │   ├── kei_basic_free.physics3.json # 物理效果
│   │   ├── texture_00.png           # 纹理
│   │   ├── motions/                 # 动作文件
│   │   └── sounds/                  # 音效
│   └── kei_basic_free_t02.cmo3
```

### 加载 Live2D 模型
```python
from app.ui.live2d_widget import Live2DCharacter

# 创建角色
character = Live2DCharacter(model_path="assets/live2d/kei_en/kei_basic_free/runtime/kei_basic_free.model3.json")
```

---

## 技术原理

### 骨骼动画 vs 帧动画

| 方案 | 优点 | 缺点 |
|------|------|------|
| **骨骼动画** | 文件小、动作流畅、可组合 | 实现复杂、需要部件分离 |
| **帧动画** | 实现简单、效果好控制 | 文件多、动作僵硬 |

### 当前实现方案

采用**简化骨骼动画**：
1. 每个部件是独立的 `QLabel`
2. 通过 `setRotation()`, `setScale()`, `move()` 实现变形
3. 动作是一系列变换的组合

### 动作播放流程

```
1. 用户触发/随机触发
   ↓
2. 查找动作预设 (ACTIONS 字典)
   ↓
3. 应用变换 (旋转/缩放/平移)
   ↓
4. QTimer 延迟恢复
```

---

## 扩展新动作

### 步骤 1：定义动作预设

在 `Live2DCharacter.ACTIONS` 中添加：

```python
ACTIONS = {
    "jump": {  # 跳跃动作
        "body_offset_y": -30,
        "arm_l_rotation": -30,
        "arm_r_rotation": 30,
    },
    "cry": {  # 哭泣动作
        "eye_scale": 1.2,
        "mouth_rotation": 30,
    },
}
```

### 步骤 2：实现动作方法

```python
def jump(self):
    """跳跃"""
    self.play_action("jump", 500)

def cry(self):
    """哭泣"""
    self.play_action("cry", 2000)
```

### 步骤 3：添加触发方式

```python
# 在 mousePressEvent 或其他地方调用
if event.button() == Qt.MouseButton.RightButton:
    self.jump()
```

---

## 替换为自己的角色

### 方法 1：修改现有部件样式

编辑 `live2d_widget.py` 中的 `_create_parts()` 方法：

```python
# 修改头发颜色
self.hair_front.setStyleSheet("""
    background: qlineargradient(...);  # 改成你的颜色
""")

# 修改身体形状
self.body.setGeometry(...)  # 改成你的尺寸
```

### 方法 2：使用图片纹理

```python
# 加载图片
pixmap = QPixmap("path/to/your/texture.png")

# 设置为部件纹理
self.face.setPixmap(pixmap)
```

### 方法 3：加载 Live2D 模型

```python
def load_model(self, model_path):
    """加载 .moc3 模型"""
    # 解析 .model3.json
    # 加载纹理
    # 创建部件
```

---

## 常见问题

### Q: 为什么动作看起来僵硬？
A: 当前是简化实现，建议使用 `QPropertyAnimation` 做平滑过渡：

```python
from PyQt6.QtCore import QPropertyAnimation

anim = QPropertyAnimation(self.body, b"pos")
anim.setDuration(300)
anim.setEndValue(QPoint(50, 140))
anim.start()
```

### Q: 如何添加更多表情？
A: 在 `play_motion()` 中添加新表情：

```python
def angry(self):
    """生气表情"""
    self.mouth.setStyleSheet("...")  # 嘴巴变平
    self.eye_l.setStyleSheet("...")    # 眼睛变细
```

### Q: 如何支持语音同步？
A: 参考模型文件中的 `.motionsync3.json`，需要：
1. 解析音频文件
2. 提取音高/音量
3. 映射到 `ParamMouthOpenY` 参数

---

## 下一步优化

1. **平滑动画** - 使用 `QPropertyAnimation` 替代直接设置
2. **物理效果** - 添加头发/衣服摆动
3. **口型同步** - 播放声音时同步嘴巴开合
4. **鼠标跟踪** - 眼睛跟随鼠标移动
5. **更多动作** - 跑步、跳跃、坐下等

---

## 参考资源

- Live2D 官方样例：https://www.live2d.com/en/download/sample-data/
- Live2D 文档：https://docs.live2d.com/
- 免费模型：https://nizima.com/
