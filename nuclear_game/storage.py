# -*- coding: utf-8 -*-
"""存档目录工具。

把用户数据写入用户目录，避免 PyInstaller onefile 临时目录导致存档丢失。
"""

import os
import sys
from pathlib import Path


def user_data_dir() -> Path:
    if sys.platform == "emscripten":
        # Pygbag 的 /data 使用浏览器文件系统，适合保存节点、设置和成绩。
        path = Path("/data/核境造物")
    else:
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home()
        path = root / "核境造物"
    path.mkdir(parents=True, exist_ok=True)
    return path
