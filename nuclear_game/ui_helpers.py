"""中文 UI 排版、字体兼容与绘图基础工具。

重要说明：
不要使用 pygame.font.match_font 或 pygame.font.SysFont。
在部分 Windows + Python/Pygame 环境中，pygame 扫描系统字体时可能读到异常注册项，
导致 TypeError: expected str, bytes or os.PathLike object, not int。
因此本文件只使用明确字体文件路径 + pygame.font.Font(None, size) 兜底。
"""
import os
from functools import lru_cache
from typing import List, Optional, Tuple
import pygame

# 字号增益：正文小字在原值基础上增加 5px。
# 说明：不再继续放大到 10px，主要通过行距、按钮间距和卡片留白保证可读性。
UI_FONT_BOOST = 5

try:
    from .asset_manager import first_font_path
except Exception:  # 兼容工具脚本单独导入
    first_font_path = None

_FONT_FILES_REGULAR = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
    r"C:\Windows\Fonts\Deng.ttf",
    r"C:\Windows\Fonts\simkai.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]

_FONT_FILES_BOLD = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\Dengb.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]


@lru_cache(maxsize=2)
def _font_path(bold: bool) -> Optional[str]:
    # 项目 assets/fonts 中的字体优先，便于发布包自带字体。
    if first_font_path:
        names = (
            ("NotoSansCJKsc-Bold.otf", "NotoSansSC-Bold.ttf", "NotoSansCJK-Bold.ttc", "msyhbd.ttc", "simhei.ttf")
            if bold else
            ("NotoSansCJKsc-Regular.otf", "NotoSansSC-Regular.ttf", "NotoSansCJK-Regular.ttc", "msyh.ttc", "simhei.ttf")
        )
        bundled = first_font_path(*names)
        if bundled:
            return bundled
    candidates = _FONT_FILES_BOLD if bold else _FONT_FILES_REGULAR
    for path in candidates:
        try:
            if path and os.path.exists(path):
                return path
        except (TypeError, ValueError, OSError):
            continue
    return None


@lru_cache(maxsize=128)
def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    """安全加载字体，不调用 pygame.font.match_font / SysFont。"""
    if not pygame.font.get_init():
        pygame.font.init()
    path = _font_path(bold)
    try:
        base_size = int(size)
        # 只把原本偏小的正文/说明文字显著放大；标题类字号不继续暴涨，避免顶部和侧栏挤压。
        if base_size <= 14:
            boost = UI_FONT_BOOST
        elif base_size <= 18:
            boost = 4
        elif base_size <= 24:
            boost = 2
        else:
            boost = 0
        effective_size = max(1, base_size + boost)
        loaded = pygame.font.Font(path, effective_size) if path else pygame.font.Font(None, effective_size)
    except Exception:
        base_size = int(size)
        boost = UI_FONT_BOOST if base_size <= 14 else 4 if base_size <= 18 else 2 if base_size <= 24 else 0
        loaded = pygame.font.Font(None, max(1, base_size + boost))
    # 不再对已加载的中文字体强制 pygame 伪粗体。
    # 伪粗体会让大字号中文边缘发糊；系统/项目自带粗体文件优先由 _font_path(bold) 选择。
    if not path:
        loaded.set_bold(bold)
    return loaded


# 保留 F10/F30，兼容 engine.py 中可能存在的旧导入；不用也不会影响运行。
F10 = get_font(10)
F11 = get_font(11)
F12 = get_font(12)
F13 = get_font(13)
F14 = get_font(14)
F15 = get_font(15)
F16 = get_font(16)
F18 = get_font(18)
F20 = get_font(20, True)
F24 = get_font(24, True)
F28 = get_font(28, True)
F30 = get_font(30, True)
F34 = get_font(34, True)


def write(surface: pygame.Surface, value: str, fnt: pygame.font.Font, color: Tuple[int, int, int],
          pos: Tuple[int, int], anchor: str = "topleft") -> pygame.Rect:
    lines = str(value).split("\n")
    images = [fnt.render(line, True, color) for line in lines]
    if len(images) == 1:
        rect = images[0].get_rect()
        setattr(rect, anchor, pos)
        surface.blit(images[0], rect)
        return rect
    line_gap = 11
    width = max((image.get_width() for image in images), default=0)
    height = sum(image.get_height() for image in images) + line_gap * (len(images) - 1)
    rect = pygame.Rect(0, 0, width, height)
    setattr(rect, anchor, pos)
    y = rect.y
    for image in images:
        surface.blit(image, (rect.x, y))
        y += image.get_height() + line_gap
    return rect


def fit_font(value: str, size: int, max_width: int, bold: bool = False, min_size: int = 10) -> pygame.font.Font:
    value = str(value).replace("\n", " ")
    for current_size in range(size, min_size - 1, -1):
        font = get_font(current_size, bold)
        if font.size(value)[0] <= max_width:
            return font
    return get_font(min_size, bold)


def write_fit(surface: pygame.Surface, value: str, size: int, color: Tuple[int, int, int],
              rect: pygame.Rect, bold: bool = False, align: str = "left",
              min_size: int = 10) -> pygame.Rect:
    original = str(value).replace("\n", " ")
    font = fit_font(original, size, rect.width, bold, min_size)
    value = original
    if font.size(value)[0] > rect.width:
        while value and font.size(value + "…")[0] > rect.width:
            value = value[:-1]
        value = value + "…" if value else "…"
    image = font.render(value, True, color)
    anchors = {
        "center": ("center", rect.center),
        "right": ("midright", (rect.right, rect.centery)),
        "left": ("midleft", (rect.x, rect.centery)),
    }
    anchor, pos = anchors.get(align, ("midleft", (rect.x, rect.centery)))
    image_rect = image.get_rect()
    setattr(image_rect, anchor, pos)
    surface.blit(image, image_rect)
    return image_rect


def wrap_lines(value: str, font: pygame.font.Font, max_width: int) -> List[str]:
    result: List[str] = []
    for paragraph in str(value).split("\n"):
        if not paragraph:
            result.append("")
            continue
        line = ""
        for char in paragraph:
            candidate = line + char
            if line and font.size(candidate)[0] > max_width:
                result.append(line)
                line = char
            else:
                line = candidate
        if line:
            result.append(line)
    return result


def write_wrapped(surface: pygame.Surface, value: str, size: int, color: Tuple[int, int, int],
                  rect: pygame.Rect, bold: bool = False, min_size: int = 10,
                  line_gap: int = 14, max_lines: Optional[int] = None) -> pygame.Rect:
    selected_font = get_font(size, bold)
    selected_lines: List[str] = []
    max_visible = 1
    for current_size in range(size, min_size - 1, -1):
        candidate_font = get_font(current_size, bold)
        candidate_lines = wrap_lines(value, candidate_font, rect.width)
        line_height = candidate_font.get_height() + line_gap
        allowed_by_height = max(1, (rect.height + line_gap) // line_height)
        limit = allowed_by_height if max_lines is None else min(max_lines, allowed_by_height)
        if len(candidate_lines) <= limit or current_size == min_size:
            selected_font, selected_lines, max_visible = candidate_font, candidate_lines, limit
            break
    clipped = len(selected_lines) > max_visible
    selected_lines = selected_lines[:max_visible]
    if clipped and selected_lines:
        last = selected_lines[-1]
        while last and selected_font.size(last + "…")[0] > rect.width:
            last = last[:-1]
        selected_lines[-1] = last + "…"
    y = rect.y
    drawn_width = 0
    for line in selected_lines:
        image = selected_font.render(line, True, color)
        surface.blit(image, (rect.x, y))
        drawn_width = max(drawn_width, image.get_width())
        y += selected_font.get_height() + line_gap
    return pygame.Rect(rect.x, rect.y, drawn_width, max(0, y - rect.y - line_gap))


def rounded(surface, rect, color, border=None, width=1, radius=9):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surface, border, rect, width, border_radius=radius)


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def money(value: float) -> str:
    return f"{int(value):,}"
