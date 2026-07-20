# -*- coding: utf-8 -*-
"""素材资源统一管理。

不要在业务代码中直接拼写 assets 路径。后续替换图片、音效、字体时，优先通过
AssetManager 获取路径或加载资源。资源不存在时返回 None，不影响游戏运行。
"""
from __future__ import annotations

import sys
from pathlib import Path
from functools import lru_cache
from typing import Optional

import pygame


ASSET_DIRS = {
    "background": Path("assets/images/background"),
    "icons": Path("assets/images/icons"),
    "equipment": Path("assets/images/equipment"),
    "ui": Path("assets/images/ui"),
    "sounds": Path("assets/sounds"),
    "fonts": Path("assets/fonts"),
}


def project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def asset_path(category: str, filename: str) -> Optional[Path]:
    subdir = ASSET_DIRS.get(category)
    if subdir is None:
        return None
    path = project_root() / subdir / filename
    return path if path.exists() else None


@lru_cache(maxsize=128)
def load_image(category: str, filename: str, size: Optional[tuple[int, int]] = None) -> Optional[pygame.Surface]:
    path = asset_path(category, filename)
    if not path:
        return None
    try:
        image = pygame.image.load(str(path)).convert_alpha()
        if size:
            image = pygame.transform.smoothscale(image, size)
        return image
    except Exception:
        return None


def load_sound(filename: str):
    path = asset_path("sounds", filename)
    if not path:
        return None
    try:
        return pygame.mixer.Sound(str(path))
    except Exception:
        return None


def first_font_path(*filenames: str) -> Optional[str]:
    for filename in filenames:
        path = asset_path("fonts", filename)
        if path:
            return str(path)
    return None
