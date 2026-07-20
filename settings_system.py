# -*- coding: utf-8 -*-
"""设置系统。

管理音效、背景音乐、文字速度、窗口大小、教学提示、演示模式和重置存档。
设置写入用户目录，和存档文件分开，避免版本更新互相影响。
"""
from __future__ import annotations

import json
import sys
from typing import Dict

import pygame

from .storage import user_data_dir
from .theme import BLACK, BLUE, BORDER, DANGER, TEXT_MUTED, WHITE, WIDTH, HEIGHT
from .ui_helpers import write_fit, rounded
from .ui.components import Button, ToggleSwitch, Badge

DEFAULT_SETTINGS = {
    "sound": True,
    "music": True,
    "text_speed": "普通",
    "window_size": "设计尺寸",
    "teaching_hints": True,
    "demo_mode": False,
    "term_mode": "normal",
}
TEXT_SPEEDS = ["慢", "普通", "快"]
TERM_MODES = ["normal", "professional", "defense"]
TERM_MODE_LABELS = {"normal": "新手模式", "professional": "专业模式", "defense": "答辩模式"}
WINDOW_SIZES = {
    "小窗口": (1100, 680),
    "设计尺寸": (WIDTH, HEIGHT),
    "大窗口": (1680, 1020),
    "全屏放大": None,
}


class SettingsSystemMixin:
    def init_settings_system(self):
        self.settings_path = user_data_dir() / "核境造物_设置.json"
        self.settings: Dict[str, object] = DEFAULT_SETTINGS.copy()
        self.settings_open = False
        self.settings_button = pygame.Rect(0, 0, 0, 0)
        self.settings_close = pygame.Rect(0, 0, 0, 0)
        self.settings_controls: Dict[str, pygame.Rect] = {}
        self.load_settings_file()
        self.apply_settings()

    def load_settings_file(self):
        try:
            if self.settings_path.exists():
                payload = json.loads(self.settings_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    for key in DEFAULT_SETTINGS:
                        if key in payload:
                            self.settings[key] = payload[key]
        except Exception:
            self.settings = DEFAULT_SETTINGS.copy()

    def write_settings_file(self):
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def apply_settings(self):
        if hasattr(self, "audio"):
            if sys.platform == "emscripten":
                # 网页稳定版不在初始化阶段启用音频，避免浏览器自动播放限制
                # 导致 Pygbag 灰屏或不断输出 MEDIA USER ACTION REQUIRED。
                self.audio.enabled = False
                if hasattr(self.audio, "set_music_enabled"):
                    self.audio.set_music_enabled(False)
            else:
                self.audio.enabled = bool(self.settings.get("sound", True))
                if hasattr(self.audio, "set_music_enabled"):
                    self.audio.set_music_enabled(bool(self.settings.get("music", True)) and self.audio.enabled)
        # 挑战模式不显示答案式提示；其他模式才读取教学提示设置。
        if getattr(self, "play_mode", "guided") == "challenge":
            self.tutorial = False
        else:
            self.tutorial = bool(self.settings.get("teaching_hints", True))
        self.term_mode = str(self.settings.get("term_mode", "normal"))

    def toggle_settings(self):
        opening = not self.settings_open
        if opening and hasattr(self, "close_transient_overlays"):
            self.close_transient_overlays(keep="settings")
        self.settings_open = opening
        if hasattr(self, "audio"):
            self.audio.play("click")

    def cycle_text_speed(self):
        current = str(self.settings.get("text_speed", "普通"))
        idx = TEXT_SPEEDS.index(current) if current in TEXT_SPEEDS else 1
        self.settings["text_speed"] = TEXT_SPEEDS[(idx + 1) % len(TEXT_SPEEDS)]

    def cycle_term_mode(self):
        current = str(self.settings.get("term_mode", "normal"))
        idx = TERM_MODES.index(current) if current in TERM_MODES else 0
        self.settings["term_mode"] = TERM_MODES[(idx + 1) % len(TERM_MODES)]
        self.apply_settings()

    def cycle_window_size(self):
        keys = list(WINDOW_SIZES)
        current = str(self.settings.get("window_size", "设计尺寸"))
        idx = keys.index(current) if current in keys else 1
        new_key = keys[(idx + 1) % len(keys)]
        self.settings["window_size"] = new_key
        if hasattr(self, "resize_display"):
            if WINDOW_SIZES[new_key] is None:
                self.resize_display((0, 0), fullscreen=True)
            else:
                self.resize_display(WINDOW_SIZES[new_key], fullscreen=False)

    def handle_settings_click(self, pos, button=1) -> bool:
        if not self.settings_open or button != 1:
            return False
        if self.settings_close.collidepoint(pos):
            self.settings_open = False
            self.write_settings_file()
            return True
        for key, rect in self.settings_controls.items():
            if not rect.collidepoint(pos):
                continue
            if key in ("sound", "music", "teaching_hints", "demo_mode"):
                self.settings[key] = not bool(self.settings.get(key, False))
                if key == "demo_mode":
                    self.selected_mode = "demo" if self.settings[key] else "guided"
                    if not self.menu:
                        self.play_mode = self.selected_mode
                self.apply_settings()
            elif key == "text_speed":
                self.cycle_text_speed()
            elif key == "window_size":
                self.cycle_window_size()
            elif key == "term_mode":
                self.cycle_term_mode()
            elif key == "reset_save":
                self.reset_all_saved_data()
            self.write_settings_file()
            if hasattr(self, "audio"):
                self.audio.play("click")
            return True
        return True

    def draw_settings_overlay(self):
        if not self.settings_open:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 24, 30, 150))
        self.screen.blit(overlay, (0, 0))

        # 设置页改为两列，避免 8 个项目纵向堆叠后与关闭按钮重叠。
        box = pygame.Rect(340, 132, 800, 596)
        self.settings_rect = box
        rounded(self.screen, box, WHITE, BLUE, 3, 18)
        write_fit(self.screen, "设置", 26, BLACK, pygame.Rect(box.x + 30, box.y + 24, 180, 34), bold=True, min_size=18)
        write_fit(self.screen, "常用开关分两列显示，减少纵向拥挤。", 14, TEXT_MUTED,
                  pygame.Rect(box.x + 30, box.y + 64, box.width - 260, 22), min_size=10)
        Badge(pygame.Rect(box.right - 170, box.y + 28, 120, 26), "可随时关闭", "info", "i").draw(self.screen)

        self.settings_controls = {}
        items = [
            ("sound", "音效开关", "点击、成功、报警提示音"),
            ("music", "背景音乐", "循环播放内置 MP3"),
            ("text_speed", "文字速度", "当前：" + str(self.settings.get("text_speed", "普通"))),
            ("window_size", "窗口大小", "当前：" + str(self.settings.get("window_size", "设计尺寸"))),
            ("term_mode", "术语显示", "当前：" + TERM_MODE_LABELS.get(str(self.settings.get("term_mode", "normal")), "新手模式")),
            ("teaching_hints", "实时指引", "下一步提示与知识解释"),
            ("demo_mode", "演示模式", "主菜单默认选择演示"),
            ("reset_save", "重置存档", "自动备份后清除节点"),
        ]
        col_w = 350
        row_h = 74
        left_x = box.x + 38
        right_x = box.x + 412
        top_y = box.y + 118
        for idx, (key, title, desc) in enumerate(items):
            col = idx % 2
            row_idx = idx // 2
            x = left_x if col == 0 else right_x
            y = top_y + row_idx * 90
            row = pygame.Rect(x, y, col_w, row_h)
            rounded(self.screen, row, (247, 250, 251), BORDER, 1, 10)
            write_fit(self.screen, title, 16, DANGER if key == "reset_save" else BLACK,
                      pygame.Rect(row.x + 14, row.y + 10, 190, 22), bold=True, min_size=12)
            write_fit(self.screen, desc, 12, TEXT_MUTED, pygame.Rect(row.x + 14, row.y + 42, 210, 18), min_size=10)
            btn = pygame.Rect(row.right - 98, row.y + 21, 78, 32)
            self.settings_controls[key] = btn
            if key in ("sound", "music", "teaching_hints", "demo_mode"):
                ToggleSwitch(btn, bool(self.settings.get(key, False))).draw(self.screen)
            elif key == "reset_save":
                Button(btn, "执行", WHITE, DANGER, DANGER).draw(self.screen)
            else:
                Button(btn, "切换", WHITE, BLUE, BLUE).draw(self.screen)

        self.settings_close = pygame.Rect(box.right - 140, box.bottom - 62, 108, 38)
        Button(self.settings_close, "关闭", BLUE, BLUE, WHITE).draw(self.screen)
