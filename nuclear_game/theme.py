# -*- coding: utf-8 -*-
"""界面尺寸与颜色常量。

本文件不创建窗口，只保存常量；engine.py 负责初始化 pygame 窗口。
"""

import pygame

WIDTH, HEIGHT = 1480, 900
MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT = 820, 500
FPS = 60

WHITE = (255, 255, 255)
BLACK = (28, 38, 48)
BG = (230, 240, 244)
DARK_PANEL = (28, 44, 59)
CARD = (44, 63, 79)
BORDER = (189, 204, 211)
TEXT_MUTED = (103, 121, 132)
GRID = (217, 228, 233)
GOOD = (38, 157, 101)
WARNING = (229, 157, 48)
DANGER = (214, 67, 67)
BLUE = (48, 141, 202)
DEEP_BLUE = (22, 98, 172)
CYAN = (82, 183, 211)
ORANGE = (239, 131, 51)
RED = (222, 73, 52)
YELLOW = (246, 194, 50)
STEEL = (107, 123, 135)
PURPLE = (123, 92, 174)
GREEN = (56, 150, 112)

LEFT = pygame.Rect(0, 0, 238, HEIGHT)
CENTER = pygame.Rect(250, 72, 893, 670)
BOTTOM = pygame.Rect(250, 756, 893, 129)
RIGHT = pygame.Rect(1155, 72, 312, 813)

__all__ = [name for name in globals() if name.isupper()]
