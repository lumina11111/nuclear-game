# -*- coding: utf-8 -*-
"""核境造物启动入口。"""
import os
from pathlib import Path
import traceback
import asyncio
import sys
import pygame

from nuclear_game.engine import NuclearGame


def user_data_dir() -> Path:
    if sys.platform == "emscripten":
        path = Path("/data/核境造物")
    else:
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home()
        path = root / "核境造物"
    path.mkdir(parents=True, exist_ok=True)
    return path


async def launch():
    try:
        await NuclearGame().run()
    except Exception:
        error_text = traceback.format_exc()
        log_path = user_data_dir() / "核境造物_错误日志.txt"
        try:
            log_path.write_text(error_text, encoding="utf-8")
        except OSError:
            pass
        if sys.platform != "emscripten":
            try:
                pygame.quit()
            except pygame.error:
                pass
        print("程序运行出错：")
        print(error_text)
        print(f"错误日志已保存到：{log_path}")
        if sys.platform != "emscripten":
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("核境造物运行错误", f"错误日志已保存到：\n{log_path}")
                root.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(launch())
