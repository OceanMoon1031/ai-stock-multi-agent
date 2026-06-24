"""Hugging Face Space entry point for AI Stock Multi-Agent Analysis"""

import sys
from pathlib import Path

# 把項目根目錄加入 Python 路徑，確保可以 import ui.app
sys.path.insert(0, str(Path(__file__).parent))

from ui.app import run_app

if __name__ == "__main__":
    run_app()