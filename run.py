#!/usr/bin/env python
"""
Legacy PyQt prototype launcher.
Not part of the current production startup path.
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.main import main

if __name__ == "__main__":
    main()
