"""
测试角色显示
"""
import sys
from PyQt6.QtWidgets import QApplication
from app.ui.character_widget import AnimeCharacter

app = QApplication(sys.argv)

character = AnimeCharacter()
character.setWindowTitle("角色测试")
character.show()

print("角色窗口已打开")
print(f"窗口大小：{character.width()}x{character.height()}")

sys.exit(app.exec())
