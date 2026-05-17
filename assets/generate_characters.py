"""
角色图片生成脚本
生成简单的二次元风格角色占位图（后续可替换为精美图片）
"""
from PIL import Image, ImageDraw, ImageFilter
import os


def create_character_base(size=(200, 300), color="#FFB6C1", name="sakura"):
    """创建角色基础图形（占位用）"""
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 身体（简单的椭圆形）
    body_color = color
    draw.ellipse([50, 100, 150, 280], fill=body_color, outline="#333", width=2)

    # 头部
    head_color = "#FFE4E1"
    draw.ellipse([60, 40, 140, 120], fill=head_color, outline="#333", width=2)

    # 眼睛（两个椭圆）
    eye_color = "#4A4A4A"
    draw.ellipse([75, 65, 90, 80], fill=eye_color)
    draw.ellipse([110, 65, 125, 80], fill=eye_color)

    # 眼睛高光
    draw.ellipse([80, 68, 86, 74], fill="white")
    draw.ellipse([115, 68, 121, 74], fill="white")

    # 嘴巴（小弧线）
    draw.arc([90, 85, 110, 95], 0, 180, fill="#FF69B4", width=2)

    # 头发（根据角色不同）
    if name == "sakura":
        # 粉色短发
        draw.ellipse([55, 30, 145, 80], fill="#FFB6C1")
        # 刘海
        for i in range(5):
            x = 65 + i * 15
            draw.polygon([(x, 50), (x + 10, 65), (x + 20, 50)], fill="#FFB6C1")
    elif name == "shiro":
        # 白色短发
        draw.ellipse([55, 30, 145, 75], fill="#E8E8E8")
        # 眼镜
        draw.rectangle([70, 68, 92, 78], outline="#666", width=2)
        draw.rectangle([108, 68, 130, 78], outline="#666", width=2)
        draw.line([92, 73, 108, 73], fill="#666", width=2)
    elif name == "nana":
        # 双马尾 + 猫耳
        draw.ellipse([55, 30, 145, 75], fill="#2A2A2A")
        # 猫耳
        draw.polygon([(60, 45), (75, 20), (90, 45)], fill="#2A2A2A")
        draw.polygon([(110, 45), (125, 20), (140, 45)], fill="#2A2A2A")
        # 双马尾
        draw.ellipse([35, 60, 65, 120], fill="#2A2A2A")
        draw.ellipse([135, 60, 165, 120], fill="#2A2A2A")

    return img


def create_blink_frames(size=(200, 300), color="#FFB6C1", name="sakura", frames=4):
    """创建眨眼动画帧"""
    frames_list = []

    for i in range(frames):
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 身体
        draw.ellipse([50, 100, 150, 280], fill=color, outline="#333", width=2)

        # 头部
        head_color = "#FFE4E1"
        draw.ellipse([60, 40, 140, 120], fill=head_color, outline="#333", width=2)

        # 眼睛（眨眼时变细）
        progress = abs(i - frames / 2) / (frames / 2)
        eye_height = int(15 * progress)
        eye_y = 65 + int(7.5 * (1 - progress))

        if eye_height > 1:
            draw.ellipse([75, eye_y - eye_height // 2, 90, eye_y + eye_height // 2], fill="#4A4A4A")
            draw.ellipse([110, eye_y - eye_height // 2, 125, eye_y + eye_height // 2], fill="#4A4A4A")
            # 高光
            if progress > 0.5:
                draw.ellipse([80, eye_y - 2, 86, eye_y + 4], fill="white")
                draw.ellipse([115, eye_y - 2, 121, eye_y + 4], fill="white")

        # 嘴巴
        draw.arc([90, 85, 110, 95], 0, 180, fill="#FF69B4", width=2)

        # 头发
        if name == "sakura":
            draw.ellipse([55, 30, 145, 80], fill="#FFB6C1")
            for i in range(5):
                x = 65 + i * 15
                draw.polygon([(x, 50), (x + 10, 65), (x + 20, 50)], fill="#FFB6C1")
        elif name == "shiro":
            draw.ellipse([55, 30, 145, 75], fill="#E8E8E8")
            draw.rectangle([70, 68, 92, 78], outline="#666", width=2)
            draw.rectangle([108, 68, 130, 78], outline="#666", width=2)
            draw.line([92, 73, 108, 73], fill="#666", width=2)
        elif name == "nana":
            draw.ellipse([55, 30, 145, 75], fill="#2A2A2A")
            draw.polygon([(60, 45), (75, 20), (90, 45)], fill="#2A2A2A")
            draw.polygon([(110, 45), (125, 20), (140, 45)], fill="#2A2A2A")
            draw.ellipse([35, 60, 65, 120], fill="#2A2A2A")
            draw.ellipse([135, 60, 165, 120], fill="#2A2A2A")

        frames_list.append(img)

    return frames_list


def create_idle_frames(size=(200, 300), color="#FFB6C1", name="sakura", frames=6):
    """创建 idle 呼吸动画帧（轻微上下浮动）"""
    frames_list = []

    for i in range(frames):
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 呼吸偏移
        offset = int(3 * (1 - abs(i - frames / 2) / (frames / 2)))

        # 身体
        draw.ellipse([50, 100 - offset, 150, 280 - offset], fill=color, outline="#333", width=2)

        # 头部
        draw.ellipse([60, 40 - offset, 140, 120 - offset], fill="#FFE4E1", outline="#333", width=2)

        # 眼睛
        draw.ellipse([75, 65 - offset, 90, 80 - offset], fill="#4A4A4A")
        draw.ellipse([110, 65 - offset, 125, 80 - offset], fill="#4A4A4A")
        draw.ellipse([80, 68 - offset, 86, 74 - offset], fill="white")
        draw.ellipse([115, 68 - offset, 121, 74 - offset], fill="white")

        # 嘴巴
        draw.arc([90, 85 - offset, 110, 95 - offset], 0, 180, fill="#FF69B4", width=2)

        # 头发
        if name == "sakura":
            draw.ellipse([55, 30 - offset, 145, 80 - offset], fill="#FFB6C1")
            for j in range(5):
                x = 65 + j * 15
                draw.polygon([(x, 50 - offset), (x + 10, 65 - offset), (x + 20, 50 - offset)], fill="#FFB6C1")
        elif name == "shiro":
            draw.ellipse([55, 30 - offset, 145, 75 - offset], fill="#E8E8E8")
            draw.rectangle([70, 68 - offset, 92, 78 - offset], outline="#666", width=2)
            draw.rectangle([108, 68 - offset, 130, 78 - offset], outline="#666", width=2)
            draw.line([92, 73 - offset, 108, 73 - offset], fill="#666", width=2)
        elif name == "nana":
            draw.ellipse([55, 30 - offset, 145, 75 - offset], fill="#2A2A2A")
            draw.polygon([(60, 45 - offset), (75, 20 - offset), (90, 45 - offset)], fill="#2A2A2A")
            draw.polygon([(110, 45 - offset), (125, 20 - offset), (140, 45 - offset)], fill="#2A2A2A")
            draw.ellipse([35, 60 - offset, 65, 120 - offset], fill="#2A2A2A")
            draw.ellipse([135, 60 - offset, 165, 120 - offset], fill="#2A2A2A")

        frames_list.append(img)

    return frames_list


def save_frames(frames, output_dir, name, action):
    """保存动画帧"""
    os.makedirs(output_dir, exist_ok=True)
    for i, frame in enumerate(frames):
        path = os.path.join(output_dir, f"{name}_{action}_{i + 1:02d}.png")
        frame.save(path, 'PNG')
    print(f"[OK] Saved {len(frames)} frames to {output_dir}")


def main():
    """生成所有角色图片"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, "characters")

    characters = [
        {"name": "sakura", "color": "#FFB6C1", "label": "小樱"},
        {"name": "shiro", "color": "#E8E8E8", "label": "阿白"},
        {"name": "nana", "color": "#2A2A2A", "label": "奈奈"},
    ]

    for char in characters:
        print(f"\nGenerating character: {char['label']} ({char['name']})")

        # 生成 idle 动画（6 帧）
        idle_frames = create_idle_frames(color=char["color"], name=char["name"])
        save_frames(idle_frames, output_dir, char["name"], "idle")

        # 生成眨眼动画（4 帧）
        blink_frames = create_blink_frames(color=char["color"], name=char["name"])
        save_frames(blink_frames, output_dir, char["name"], "blink")

    print("\n[SUCCESS] All character images generated!")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
