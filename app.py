"""Hugging Face Space 入口點"""
import sys
from pathlib import Path

# 把項目根目錄加入 Python 路徑
sys.path.append(str(Path(__file__).parent))

from ui.app import run_app

if __name__ == "__main__":
    run_app()