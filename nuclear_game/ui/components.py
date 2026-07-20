# -*- coding: utf-8 -*-
"""轻量 Pygame UI 组件。

这些组件不接管主循环，只封装常见绘制：按钮、卡片、进度条、弹窗、关卡节点、参数卡，
以及设置页/演示页常用的开关、标签页、滚动文本、资质章、提示条等。
后续如果继续改界面，优先复用这里，减少到处手写坐标和重复圆角绘制。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence, Tuple

import pygame

from ..theme import BLACK, BLUE, BORDER, GOOD, GRID, TEXT_MUTED, WARNING, WHITE
from .theme_tokens import (
    BUTTON_RADIUS, CARD_RADIUS, POPUP_RADIUS, BUTTON_TEXT_SIZE, SMALL_TEXT_SIZE,
    SURFACE_ALT, SURFACE_INFO, SURFACE_WARN, SURFACE_GOOD,
    TEXT_MAIN, TEXT_MUTED_TOKEN, BORDER_MUTED, ALARM_BLUE, ALARM_GREEN,
    ALARM_YELLOW, ALARM_RED, CARD_PADDING, SECTION_SIZE, TEXT_SIZE,
)
from ..ui_helpers import rounded, write_fit, write_wrapped

Color = Tuple[int, int, int]


def _state_color(state: str) -> Color:
    return {
        "normal": ALARM_GREEN,
        "good": ALARM_GREEN,
        "warn": ALARM_YELLOW,
        "warning": ALARM_YELLOW,
        "danger": ALARM_RED,
        "error": ALARM_RED,
        "info": ALARM_BLUE,
    }.get(state, ALARM_BLUE)


def _state_fill(state: str) -> Color:
    return {
        "normal": SURFACE_GOOD,
        "good": SURFACE_GOOD,
        "warn": SURFACE_WARN,
        "warning": SURFACE_WARN,
        "danger": (254, 242, 242),
        "error": (254, 242, 242),
        "info": SURFACE_INFO,
    }.get(state, SURFACE_INFO)


@dataclass
class Button:
    rect: pygame.Rect
    text: str
    fill: Color = WHITE
    border: Color = BLUE
    text_color: Color = BLUE
    radius: int = BUTTON_RADIUS
    font_size: int = BUTTON_TEXT_SIZE
    disabled: bool = False

    def draw(self, surface: pygame.Surface) -> None:
        fill = SURFACE_ALT if self.disabled else self.fill
        border = BORDER_MUTED if self.disabled else self.border
        color = TEXT_MUTED_TOKEN if self.disabled else self.text_color
        rounded(surface, self.rect, fill, border, 1, self.radius)
        write_fit(surface, self.text, self.font_size, color, self.rect.inflate(-8, -5), align="center", min_size=9)

    def hit(self, pos) -> bool:
        return (not self.disabled) and self.rect.collidepoint(pos)


@dataclass
class Card:
    rect: pygame.Rect
    title: str = ""
    fill: Color = WHITE
    border: Color = BORDER
    radius: int = CARD_RADIUS

    def draw(self, surface: pygame.Surface, body: Optional[str] = None) -> None:
        rounded(surface, self.rect, self.fill, self.border, 1, self.radius)
        if self.title:
            write_fit(surface, self.title, BUTTON_TEXT_SIZE, BLACK, pygame.Rect(self.rect.x + 12, self.rect.y + 8, self.rect.width - 24, 20), bold=True, min_size=10)
        if body:
            y0 = self.rect.y + (34 if self.title else 12)
            write_wrapped(surface, body, SMALL_TEXT_SIZE, TEXT_MUTED, pygame.Rect(self.rect.x + 12, y0, self.rect.width - 24, self.rect.bottom - y0 - 10), min_size=10, max_lines=2)


@dataclass
class ProgressBar:
    rect: pygame.Rect
    value: float
    maximum: float = 100.0
    fill: Color = BLUE
    back: Color = GRID
    label: str = ""

    def draw(self, surface: pygame.Surface) -> None:
        rounded(surface, self.rect, self.back, None, 0, max(3, self.rect.height // 2))
        ratio = 0 if self.maximum <= 0 else max(0.0, min(1.0, self.value / self.maximum))
        filled = pygame.Rect(self.rect.x, self.rect.y, int(self.rect.width * ratio), self.rect.height)
        if filled.width > 0:
            rounded(surface, filled, self.fill, None, 0, max(3, self.rect.height // 2))
        if self.label:
            write_fit(surface, self.label, 10, WHITE if ratio > 0.45 else BLACK, self.rect.inflate(-4, -1), align="center", min_size=7)


@dataclass
class Popup:
    rect: pygame.Rect
    title: str
    subtitle: str = ""
    border: Color = BLUE

    def draw_frame(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((15, 24, 30, 150))
        surface.blit(overlay, (0, 0))
        rounded(surface, self.rect, WHITE, self.border, 2, POPUP_RADIUS)
        write_fit(surface, self.title, 24, BLACK, pygame.Rect(self.rect.x + 28, self.rect.y + 24, self.rect.width - 56, 34), bold=True, min_size=16)
        if self.subtitle:
            write_fit(surface, self.subtitle, 13, TEXT_MUTED, pygame.Rect(self.rect.x + 28, self.rect.y + 62, self.rect.width - 56, 22), min_size=10)


@dataclass
class LevelNode:
    center: Tuple[int, int]
    label: str
    status: str
    stars: int = 0

    def draw(self, surface: pygame.Surface) -> None:
        cx, cy = self.center
        if self.status == "已完成":
            color, fill = GOOD, (234, 249, 240)
        elif self.status == "当前关":
            color, fill = WARNING, (255, 249, 235)
        elif self.status == "已解锁":
            color, fill = BLUE, (239, 247, 252)
        else:
            color, fill = TEXT_MUTED, (247, 250, 251)
        pygame.draw.circle(surface, fill, (cx, cy), 48)
        pygame.draw.circle(surface, color, (cx, cy), 48, 3)
        mark = "已" if self.status == "已完成" else "现" if self.status == "当前关" else "开" if self.status == "已解锁" else "锁"
        write_fit(surface, mark, 24, color, pygame.Rect(cx - 28, cy - 29, 56, 42), align="center", min_size=18)
        write_fit(surface, self.status, 11, color, pygame.Rect(cx - 50, cy + 14, 100, 20), align="center", min_size=9)
        write_fit(surface, self.label, 11, BLACK if self.status != "未解锁" else TEXT_MUTED, pygame.Rect(cx - 86, cy + 63, 172, 22), align="center", min_size=8)
        write_fit(surface, "★" * self.stars + "☆" * (3 - self.stars), 13, WARNING if self.stars else BORDER, pygame.Rect(cx - 56, cy + 88, 112, 22), align="center", min_size=10)


@dataclass
class ParameterCard:
    rect: pygame.Rect
    name: str
    value: str
    state: str = "normal"

    def draw(self, surface: pygame.Surface) -> None:
        color, fill = _state_color(self.state), _state_fill(self.state)
        rounded(surface, self.rect, fill, color, 1, 8)
        write_fit(surface, self.name, 10, TEXT_MUTED, pygame.Rect(self.rect.x + 10, self.rect.y + 8, self.rect.width - 20, 16), min_size=8)
        write_fit(surface, self.value, 15, color, pygame.Rect(self.rect.x + 10, self.rect.y + 27, self.rect.width - 20, 22), bold=True, align="right", min_size=10)


@dataclass
class Tooltip:
    """悬浮提示框。pos 通常传鼠标坐标；会自动避免超出画布。"""
    title: str
    text: str
    width: int = 280
    state: str = "info"

    def draw(self, surface: pygame.Surface, pos: Tuple[int, int]) -> pygame.Rect:
        width = min(self.width, max(120, surface.get_width() - 32))
        x = max(16, min(pos[0] + 18, surface.get_width() - width - 16))
        y = max(16, min(pos[1] + 18, surface.get_height() - 128))
        rect = pygame.Rect(x, y, width, 112)
        color = _state_color(self.state)
        rounded(surface, rect, WHITE, color, 2, 10)
        write_fit(surface, self.title, 13, color, pygame.Rect(rect.x + 12, rect.y + 9, rect.width - 24, 19), bold=True, min_size=10)
        write_wrapped(surface, self.text, 10, TEXT_MUTED_TOKEN, pygame.Rect(rect.x + 12, rect.y + 34, rect.width - 24, rect.height - 44), min_size=8, max_lines=4)
        return rect


@dataclass
class ToggleSwitch:
    rect: pygame.Rect
    value: bool
    label_on: str = "开"
    label_off: str = "关"
    disabled: bool = False

    def draw(self, surface: pygame.Surface) -> None:
        color = BORDER_MUTED if self.disabled else (ALARM_GREEN if self.value else TEXT_MUTED_TOKEN)
        fill = SURFACE_ALT if self.disabled else ((224, 245, 235) if self.value else (235, 240, 243))
        rounded(surface, self.rect, fill, color, 1, self.rect.height // 2)
        knob_size = max(18, self.rect.height - 8)
        knob_x = self.rect.right - knob_size - 4 if self.value else self.rect.x + 4
        knob = pygame.Rect(knob_x, self.rect.y + 4, knob_size, knob_size)
        rounded(surface, knob, WHITE, color, 1, knob_size // 2)
        label = self.label_on if self.value else self.label_off
        area = pygame.Rect(self.rect.x + 6, self.rect.y, self.rect.width - 12, self.rect.height)
        write_fit(surface, label, 10, color, area, align="center", min_size=8)

    def hit(self, pos) -> bool:
        return (not self.disabled) and self.rect.collidepoint(pos)


@dataclass
class TabView:
    rect: pygame.Rect
    tabs: Sequence[str]
    active: str
    button_rects: Dict[str, pygame.Rect] = field(default_factory=dict)

    def draw(self, surface: pygame.Surface) -> Dict[str, pygame.Rect]:
        self.button_rects = {}
        count = max(1, len(self.tabs))
        tab_w = max(1, self.rect.width // count)
        for idx, tab in enumerate(self.tabs):
            # 不强制最小宽度，避免标签数量多时越过容器右边界。
            tab_rect = pygame.Rect(self.rect.x + idx * tab_w, self.rect.y, max(1, tab_w - 4), self.rect.height)
            selected = tab == self.active
            rounded(surface, tab_rect, ALARM_BLUE if selected else SURFACE_ALT, ALARM_BLUE if selected else BORDER_MUTED, 1, 8)
            write_fit(surface, tab, 11, WHITE if selected else TEXT_MUTED_TOKEN, tab_rect.inflate(-8, -4), align="center", min_size=8)
            self.button_rects[tab] = tab_rect
        return self.button_rects

    def tab_at(self, pos) -> Optional[str]:
        for tab, rect in self.button_rects.items():
            if rect.collidepoint(pos):
                return tab
        return None


@dataclass
class ScrollBox:
    rect: pygame.Rect
    title: str = ""
    lines: Sequence[str] = field(default_factory=list)
    scroll: int = 0
    line_height: int = 28
    border: Color = BORDER

    def draw(self, surface: pygame.Surface) -> None:
        rounded(surface, self.rect, WHITE, self.border, 1, CARD_RADIUS)
        y = self.rect.y + CARD_PADDING
        if self.title:
            write_fit(surface, self.title, SECTION_SIZE, TEXT_MAIN, pygame.Rect(self.rect.x + CARD_PADDING, y, self.rect.width - 2 * CARD_PADDING, 22), bold=True, min_size=11)
            y += 28
        content = pygame.Rect(self.rect.x + CARD_PADDING, y, self.rect.width - 2 * CARD_PADDING - 6, self.rect.bottom - y - CARD_PADDING)
        max_count = max(1, content.height // self.line_height)
        safe_scroll = max(0, min(self.scroll, max(0, len(self.lines) - max_count)))
        visible = list(self.lines)[safe_scroll:safe_scroll + max_count]
        for index, line in enumerate(visible):
            write_fit(surface, str(line), TEXT_SIZE, TEXT_MUTED_TOKEN, pygame.Rect(content.x, content.y + index * self.line_height, content.width, self.line_height), min_size=8)
        if len(self.lines) > max_count:
            track = pygame.Rect(self.rect.right - 12, content.y, 4, content.height)
            rounded(surface, track, GRID, None, 0, 2)
            ratio = max_count / max(1, len(self.lines))
            knob_h = max(18, int(track.height * ratio))
            max_scroll = max(1, len(self.lines) - max_count)
            knob_y = track.y + int((track.height - knob_h) * safe_scroll / max_scroll)
            rounded(surface, pygame.Rect(track.x, knob_y, track.width, knob_h), BORDER_MUTED, None, 0, 2)

    def handle_wheel(self, delta_y: int, pos=None) -> bool:
        if pos is not None and not self.rect.collidepoint(pos):
            return False
        title_space = 28 if self.title else 0
        content_height = max(1, self.rect.height - 2 * CARD_PADDING - title_space)
        max_count = max(1, content_height // self.line_height)
        max_scroll = max(0, len(self.lines) - max_count)
        self.scroll = max(0, min(max_scroll, self.scroll - int(delta_y)))
        return True


@dataclass
class Badge:
    rect: pygame.Rect
    text: str
    state: str = "info"
    icon: str = "★"

    def draw(self, surface: pygame.Surface) -> None:
        color, fill = _state_color(self.state), _state_fill(self.state)
        rounded(surface, self.rect, fill, color, 1, self.rect.height // 2)
        write_fit(surface, self.icon, 12, color, pygame.Rect(self.rect.x + 8, self.rect.y + 2, 18, self.rect.height - 4), align="center", min_size=9)
        write_fit(surface, self.text, 11, color, pygame.Rect(self.rect.x + 28, self.rect.y + 2, self.rect.width - 36, self.rect.height - 4), align="center", min_size=8)


@dataclass
class AlertBanner:
    rect: pygame.Rect
    title: str
    detail: str
    state: str = "info"
    footer: str = ""

    def draw(self, surface: pygame.Surface) -> None:
        color, fill = _state_color(self.state), _state_fill(self.state)
        rounded(surface, self.rect, fill, color, 2, 10)
        title_w = min(180, max(72, self.rect.width // 3))
        detail_x = self.rect.x + 16 + title_w + 10
        detail_w = max(40, self.rect.right - detail_x - 16)
        write_fit(surface, self.title, 17, color, pygame.Rect(self.rect.x + 16, self.rect.y + 7, title_w, 25), bold=True, min_size=12)
        write_fit(surface, self.detail, 12, TEXT_MAIN, pygame.Rect(detail_x, self.rect.y + 8, detail_w, 21), min_size=9)
        if self.footer:
            write_fit(surface, self.footer, 10, color, pygame.Rect(detail_x, self.rect.y + 33, detail_w, 16), min_size=8)
