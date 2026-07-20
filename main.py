# -*- coding: utf-8 -*-
"""Pygbag/桌面通用入口。"""
import asyncio
import traceback
import sys

from nuclear_game.engine import NuclearGame

if sys.platform == "emscripten":
    try:
        import platform
        platform.document.body.style.background = "#1c2c3b"
        platform.window.canvas.style.touchAction = "none"
        platform.window.canvas.style.width = "100%"
        platform.window.canvas.style.height = "auto"
        platform.window.canvas.style.maxWidth = "1480px"
    except Exception:
        pass


async def main():
    try:
        await NuclearGame().run()
    except Exception:
        traceback.print_exc()
        if sys.platform != "emscripten":
            raise


asyncio.run(main())
