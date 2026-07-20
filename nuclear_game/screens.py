# -*- coding: utf-8 -*-
"""所有主要界面绘制方法。

把绘制代码集中到 screens.py，engine.py 只负责主循环和输入分发。
"""

import math
import random

import pygame

from .theme import *
from .catalog import *
from .reference_content import SYSTEM_TECHNICAL_NOTES, DATA_SOURCE_NOTE, format_measures, ACCIDENT_CASE_LIBRARY
from .advanced_features import ACCIDENT_ATLAS_PAGE_SIZE, chain_text, format_term
from .story_data import STORY_STAGE_NAMES, STORY_STAGE_HELP, get_stage_script, BEGINNER_OBJECTIVE
from .commissioning import CRITICAL_ORDER, CRITICAL_LABELS, CRITICAL_TOOL_NAMES, CRITICAL_OPTIONS
from .ui_helpers import (
    F11, F12, F13, F14, F15, F16, F18, F24, F28, F34,
    write, write_fit, write_wrapped, rounded, clamp, money, wrap_lines, get_font,
)
from .ui.components import Button, Tooltip

STAGE_NAMES = STORY_STAGE_NAMES
STAGE_HELP = STORY_STAGE_HELP
STAGE_SHORT_NAMES = ["厂址与土建", "主回路安装", "常规岛并网", "专设安全设施", "辐射防护复盘"]

# 经营化重点界面：默认只显示当前必须处理的目标，不再把工具箱、状态、说明全部摊开。
FOCUS_UI_DEFAULT = True
CIVIL_INSTALL_ORDER = ["foundation", "containment", "turbine_hall", "cooling_base"]
EQUIPMENT_INSTALL_ORDER = [
    "vessel", "core", "crdm", "pressurizer", "steam_gen", "primary_pump",
    "turbine", "generator", "condenser", "secondary_pump", "cooling", "tertiary_pump",
    "diesel_a", "diesel_b", "spray", "efw", "bio_shield", "area_monitor",
    "dosimetry", "decon", "effluent_monitor",
]

UI_PANEL_PAD = 20
UI_CARD_PAD = 16
UI_SECTION_GAP = 16
UI_ROW_GAP = 12
UI_CARD_RADIUS = 10
UI_PILL_RADIUS = 7
UI_TAB_HEIGHT = 32
UI_SMALL_CARD_HEIGHT = 56
UI_MEDIUM_CARD_HEIGHT = 84

PARAMETER_EXPLANATIONS = {
    "一回路平均温度": "正常运行时约 310℃ 附近，随功率变化较小。本游戏用它帮助理解一回路热工状态。",
    "冷凝器绝对压力": "单位 kPa(a)。数值升高表示冷端真空变差，通常需要关注循环冷却水系统（CRF）和冷却水流量。",
    "堆芯核功率": "相对功率参数，单位 %FP，用于表示当前反应堆功率水平。",
    "个人剂量": "分级剂量机制：20 mSv 职业参考线，50 mSv 橙色警戒，100 mSv 事故教学红线。",
}


class ScreenMixin:
    def left_content_top(self):
        """返回左侧功能区顶部；阶段路径采用紧凑节距，给卡片留出更多留白。"""
        start_y = 92
        step_gap = 44
        return start_y + step_gap * len(STAGE_NAMES) + 18

    def term_label(self, system_key: str) -> str:
        mode = getattr(self, "term_mode", "normal")
        return format_term(system_key, mode)

    def slot_display_label(self, key: str) -> str:
        """中央蓝图槽位使用短标签，避免长设备名互相覆盖。"""
        short = {
            "foundation": "地基",
            "containment": "安全壳",
            "turbine_hall": "汽轮机厂房",
            "cooling_base": "取排水",
            "vessel": "压力容器",
            "core": "堆芯",
            "crdm": "控制棒驱动机构",
            "pressurizer": "稳压器",
            "steam_gen": "蒸汽发生器",
            "primary_pump": "主泵",
            "turbine": "汽轮机",
            "generator": "发电机",
            "condenser": "冷凝器",
            "secondary_pump": "给水泵",
            "cooling": "循环冷却水系统（CRF）",
            "tertiary_pump": "循环水泵",
            "diesel_a": "A列EDG",
            "diesel_b": "B列EDG",
            "spray": "安全壳喷淋系统",
            "efw": "辅助给水系统（ASG）",
            "bio_shield": "生物屏蔽",
            "area_monitor": "区域辐射监测（KRT）",
            "dosimetry": "个人剂量",
            "decon": "污染检查与去污站",
            "effluent_monitor": "排放监测仪",
        }
        return short.get(key, ALL_MODULES[key].name if key in ALL_MODULES else str(key))

    def is_challenge_mode(self) -> bool:
        return getattr(self, "play_mode", "") == "challenge"

    def should_show_blueprint_text(self) -> bool:
        """中央背景文字默认关闭；需要时由画布右上角按钮临时打开。"""
        return bool(getattr(self, "show_blueprint_labels", False))

    def should_show_center_markers(self) -> bool:
        """挑战模式默认隐藏中央槽位图标和名称；点击按钮后临时显示。"""
        return (not self.is_challenge_mode()) or self.should_show_blueprint_text()

    def draw_blueprint_label_toggle(self):
        """中央画布标识开关。挑战模式默认隐藏图标/名称，普通模式只控制背景文字。"""
        self.blueprint_label_button = pygame.Rect(CENTER.right - 126, CENTER.y + 12, 106, 30)
        active = self.should_show_blueprint_text()
        challenge = self.is_challenge_mode()
        rounded(self.screen, self.blueprint_label_button,
                (239, 247, 252) if not active else (234, 249, 240),
                GOOD if active else BORDER, 1, 7)
        label = ("隐藏标识" if active else "显示标识") if challenge else ("隐藏文字" if active else "显示文字")
        write_fit(self.screen, label, 12,
                  GOOD if active else TEXT_MUTED,
                  self.blueprint_label_button.inflate(-8, -4), align="center", min_size=9)

    def draw_slot_label(self, key: str, rect: pygame.Rect, selected: bool = False):
        """在槽位内部绘制不越界的标签。

        当前目标被高亮时优先完整显示名称，不再把图标压到文字上；
        普通空槽位继续显示淡化小图标，保证画面不空。
        """
        if not self.should_show_center_markers():
            return
        label = self.slot_display_label(key)
        color = BLUE if selected else TEXT_MUTED
        max_w = max(52, rect.width - 6)
        if selected:
            # 选中槽位已经有外框高亮，内部不再绘制小图标，避免“取排水构筑物”等长名被遮挡。
            label_rect = pygame.Rect(rect.x + 4, rect.centery - 13, rect.width - 8, 26)
            write_fit(self.screen, label, 11, color, label_rect,
                      align="center", bold=True, min_size=7)
            return
        # 较大的虚线槽位以前只有文字，画面显得空；这里补一个弱化的小图标。
        # 但长名称优先完整显示，避免图标压住“取排水构筑物”等文字。
        long_label = len(label) >= 7 or "（" in label or key in {"cooling_base", "cooling", "area_monitor", "spray", "efw", "decon"}
        if rect.width >= 58 and rect.height >= 46 and not long_label:
            icon_size = 24 if min(rect.width, rect.height) < 70 else 28
            icon_y = rect.y + 7 if rect.height < 76 else rect.y + 12
            icon_rect = pygame.Rect(rect.centerx - icon_size // 2, icon_y, icon_size, icon_size)
            self.draw_device_icon(key, icon_rect, tiny=True)
            label_y = min(rect.bottom - 24, icon_rect.bottom + 3)
            label_rect = pygame.Rect(rect.centerx - max_w // 2, label_y, max_w, 22)
        else:
            label_rect = pygame.Rect(rect.x + 4, rect.centery - 12, rect.width - 8, 24)
        write_fit(self.screen, label, 10, color, label_rect,
                  align="center", bold=False, min_size=7)

    def compact_event_summary(self):
        if self.dose_task:
            return ("KRT 报警", "受控区作业", "制定方案控剂量")
        case = getattr(self, "active_reference_accident", None) or getattr(self, "last_reference_accident", None)
        if self.warning_event or self.fault:
            title = case.get("name") if case else "运行异常"
            phenomenon = case.get("phenomenon") if case else "关键参数偏离正常范围"
            key = self.current_accident_key() if hasattr(self, "current_accident_key") else None
            if key == "power" and getattr(self, "accident_choice_resolved", False):
                action = "拖 A列，再拖 B列"
            elif key == "vacuum" and getattr(self, "diagnosis_resolved", False):
                action = "拖动冷却水滑块到 85% 以上"
            elif case:
                action = format_measures(case, 1)
            else:
                action = {"power": "确认 EDG/应急供电", "water": "确认 ASG 辅助给水", "vacuum": "提高 CRF 冷却水流量", "safety": "投入 EAS/RIS", "dose": "制定防护方案"}.get(key, "按操作提示处置")
            return (title, phenomenon, action)
        if self.mission_complete():
            return ("目标已达成", "运行目标满足要求", "结束挑战查看复盘")
        return ("当前无事故", "参数稳定，继续按目标运行", "关注风险或升级系统")

    def rebuild_toolbar_rects(self):
        self.toolbar_rects = {}
        focus_ui = getattr(self, "focus_ui", FOCUS_UI_DEFAULT)
        if focus_ui and self.stage in (0, 1):
            key = self.next_install_key()
            if key:
                self.toolbar_rects[key] = pygame.Rect(12, self.left_content_top() + 68, 214, 64)
            return
        if self.stage == 0:
            keys = list(CIVIL.keys())
            y = self.left_content_top() + 64 if getattr(self, "play_mode", "") == "challenge" else self.left_content_top() + 27
        elif self.stage == 1:
            keys = list(EQUIP_TABS[self.active_tab])
            y = self.left_content_top() + 39
        else:
            return
        if getattr(self, "play_mode", "") == "challenge" and getattr(self, "challenge_shuffle_modules", False):
            rng = random.Random(f"{self.stage}:{self.active_tab}:module-order")
            rng.shuffle(keys)
        for key in keys:
            self.toolbar_rects[key] = pygame.Rect(12, y, 214, 44)
            y += 49


    def dashed_rect(self, rect, color, width=2, dash=8):
        for start, end in [(rect.topleft, rect.topright), (rect.topright, rect.bottomright),
                           (rect.bottomright, rect.bottomleft), (rect.bottomleft, rect.topleft)]:
            length = math.hypot(end[0] - start[0], end[1] - start[1])
            if length == 0:
                continue
            dx, dy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
            d = 0
            while d < length:
                e = min(length, d + dash)
                pygame.draw.line(self.screen, color, (start[0] + dx * d, start[1] + dy * d),
                                 (start[0] + dx * e, start[1] + dy * e), width)
                d += dash + 5

    def arrow(self, start, end, color, width=3):
        pygame.draw.line(self.screen, color, start, end, width)
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        size = 9
        a = (end[0] - size * math.cos(angle - .45), end[1] - size * math.sin(angle - .45))
        b = (end[0] - size * math.cos(angle + .45), end[1] - size * math.sin(angle + .45))
        pygame.draw.polygon(self.screen, color, [end, a, b])

    def poly_point(self, points, offset):
        total = sum(math.hypot(points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1])
                    for i in range(len(points) - 1))
        if total == 0:
            return points[0]
        d = offset % total
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            seg = math.hypot(x2 - x1, y2 - y1)
            if d <= seg:
                t = d / seg if seg else 0
                return int(x1 + (x2 - x1) * t), int(y1 + (y2 - y1) * t)
            d -= seg
        return points[-1]

    def draw_device_icon(self, key, rect, tiny=False):
        module = ALL_MODULES[key]
        color = module.color
        if tiny:
            rounded(self.screen, rect, (245, 249, 250), color, 1, 6)
            inner = rect.inflate(-8, -8)
            cx, cy = inner.center
            w, h = inner.width, inner.height
            # 左侧工具卡和空槽位都复用这一套“微型设备图标”。
            # 这些不是装饰点，而是按设备实际用途区分：建筑、泵、换热、发电、监测、防护等。
            if key == "foundation":
                pygame.draw.rect(self.screen, (200, 211, 216), inner, 1, border_radius=2)
                for x in range(inner.x + 2, inner.right, 7):
                    pygame.draw.line(self.screen, color, (x, inner.y + 2), (x - 5, inner.bottom - 2), 1)
            elif key == "containment":
                dome = inner.inflate(2, 2)
                pygame.draw.arc(self.screen, color, dome, math.pi, 2 * math.pi, 2)
                pygame.draw.line(self.screen, color, (dome.x, dome.centery), (dome.x, dome.bottom), 2)
                pygame.draw.line(self.screen, color, (dome.right, dome.centery), (dome.right, dome.bottom), 2)
                pygame.draw.line(self.screen, color, dome.bottomleft, dome.bottomright, 2)
            elif key == "turbine_hall":
                pygame.draw.rect(self.screen, color, (inner.x + 2, inner.y + 7, inner.width - 4, inner.height - 8), 2, border_radius=2)
                pygame.draw.line(self.screen, color, (inner.x + 1, inner.y + 8), (cx, inner.y + 2), 2)
                pygame.draw.line(self.screen, color, (cx, inner.y + 2), (inner.right - 1, inner.y + 8), 2)
            elif key == "cooling_base":
                for i in range(3):
                    yy = inner.y + 3 + i * 6
                    pygame.draw.arc(self.screen, color, (inner.x + 1, yy, inner.width - 2, 8), 0, math.pi, 2)
                pygame.draw.line(self.screen, color, (inner.x + 2, inner.bottom - 2), (inner.right - 2, inner.bottom - 2), 2)
            elif key in ("vessel", "pressurizer"):
                vessel = pygame.Rect(cx - max(4, w // 4), inner.y + 1, max(8, w // 2), h - 2)
                rounded(self.screen, vessel, (245, 249, 250), color, 2, 5)
                if key == "pressurizer":
                    pygame.draw.line(self.screen, color, (vessel.centerx, vessel.y + 3), (vessel.centerx, vessel.bottom - 3), 1)
            elif key == "steam_gen":
                vessel = pygame.Rect(cx - max(5, w // 4), inner.y + 1, max(10, w // 2), h - 2)
                rounded(self.screen, vessel, (245, 249, 250), color, 2, 5)
                pygame.draw.arc(self.screen, color, vessel.inflate(-4, -4), -1.5, 1.5, 1)
            elif key == "core":
                for x in range(inner.x + 3, inner.right - 1, 5):
                    pygame.draw.line(self.screen, RED, (x, inner.y + 2), (x, inner.bottom - 2), 2)
            elif key == "crdm":
                pygame.draw.line(self.screen, color, (inner.x + 2, inner.y + 3), (inner.right - 2, inner.y + 3), 2)
                for x in range(inner.x + 4, inner.right - 2, 6):
                    pygame.draw.line(self.screen, color, (x, inner.y + 5), (x, inner.bottom - 2), 2)
            elif key in ("primary_pump", "secondary_pump", "tertiary_pump", "efw"):
                pygame.draw.circle(self.screen, color, (cx, cy), max(5, min(w, h) // 3), 2)
                self.arrow((cx - 6, cy), (cx + 7, cy), color, 1)
            elif key == "turbine":
                pts = [(inner.x + 2, cy), (cx, inner.y + 2), (inner.right - 2, cy), (cx, inner.bottom - 2)]
                pygame.draw.polygon(self.screen, color, pts)
            elif key == "generator":
                pygame.draw.rect(self.screen, (247, 239, 207), inner, 1, border_radius=3)
                write_fit(self.screen, "G", 10, color, inner, align="center", bold=True, min_size=8)
            elif key == "condenser":
                pygame.draw.rect(self.screen, color, inner, 1, border_radius=2)
                for x in range(inner.x + 4, inner.right - 2, 7):
                    pygame.draw.line(self.screen, color, (x, inner.y + 2), (x, inner.bottom - 2), 1)
            elif key == "cooling":
                for i in range(3):
                    yy = inner.y + 2 + i * 6
                    pygame.draw.arc(self.screen, color, (inner.x + 1, yy, inner.width - 2, 8), 0, math.pi, 2)
            elif key in ("diesel_a", "diesel_b"):
                pygame.draw.rect(self.screen, color, inner, 1, border_radius=3)
                write_fit(self.screen, "DG", 7, color, inner.inflate(6, 0), align="center", bold=True, min_size=6)
            elif key == "spray":
                pygame.draw.line(self.screen, color, (inner.x + 2, inner.y + 3), (inner.right - 2, inner.y + 3), 2)
                for x in range(inner.x + 5, inner.right - 2, 6):
                    pygame.draw.line(self.screen, color, (x, inner.y + 6), (x - 2, inner.bottom - 2), 1)
                    pygame.draw.circle(self.screen, CYAN, (x - 2, inner.bottom - 1), 1)
            elif key == "bio_shield":
                pygame.draw.rect(self.screen, color, inner, 1, border_radius=2)
                for yy in range(inner.y + 5, inner.bottom - 1, 6):
                    pygame.draw.line(self.screen, color, (inner.x + 2, yy), (inner.right - 2, yy), 1)
                pygame.draw.line(self.screen, color, (cx, inner.y + 2), (cx, inner.bottom - 2), 1)
            elif key in ("area_monitor", "effluent_monitor"):
                pygame.draw.rect(self.screen, color, (inner.x + 2, inner.y + 4, inner.width - 4, inner.height - 7), 1, border_radius=2)
                pygame.draw.circle(self.screen, color, (cx, cy), 2)
                for angle in (0, 2.09, 4.18):
                    pt = (int(cx + math.cos(angle) * 7), int(cy + math.sin(angle) * 7))
                    pygame.draw.line(self.screen, color, (cx, cy), pt, 1)
            elif key == "dosimetry":
                pygame.draw.rect(self.screen, color, (cx - 5, inner.y + 3, 10, inner.height - 5), 1, border_radius=2)
                pygame.draw.circle(self.screen, color, (cx, cy), 2)
                pygame.draw.line(self.screen, color, (cx - 3, inner.bottom - 4), (cx + 3, inner.bottom - 4), 1)
            elif key == "decon":
                pygame.draw.line(self.screen, color, (inner.x + 3, inner.y + 4), (inner.right - 3, inner.y + 4), 2)
                for x in range(inner.x + 5, inner.right - 2, 6):
                    pygame.draw.circle(self.screen, CYAN, (x, inner.y + 10), 2)
                pygame.draw.lines(self.screen, GOOD, False, [(inner.x + 6, inner.bottom - 6), (cx - 1, inner.bottom - 2), (inner.right - 3, inner.y + 9)], 2)
            else:
                pygame.draw.circle(self.screen, color, (cx, cy), max(5, min(w, h) // 3), 2)
                self.arrow((inner.x + 2, cy), (inner.right - 2, cy), color, 1)
            return

        # 图形只作示意，保持简洁
        if key == "foundation":
            pygame.draw.rect(self.screen, (182, 194, 200), rect, border_radius=4)
            for x in range(rect.x + 10, rect.right, 24):
                pygame.draw.line(self.screen, STEEL, (x, rect.y + 4), (x - 10, rect.bottom - 4), 2)
        elif key == "containment":
            pygame.draw.arc(self.screen, PURPLE, rect, math.pi, 2 * math.pi, 4)
            pygame.draw.line(self.screen, PURPLE, (rect.x, rect.centery), (rect.x, rect.bottom), 4)
            pygame.draw.line(self.screen, PURPLE, (rect.right, rect.centery), (rect.right, rect.bottom), 4)
            pygame.draw.line(self.screen, PURPLE, rect.bottomleft, rect.bottomright, 4)
            if self.should_show_blueprint_text():
                label_rect = pygame.Rect(rect.centerx - 42, rect.y + 44, 84, 24)
                rounded(self.screen, label_rect, WHITE, PURPLE, 1, 6)
                write_fit(self.screen, "安全壳", 11, PURPLE, label_rect.inflate(-6, -2), align="center", bold=True, min_size=9)
        elif key in ("turbine_hall", "cooling_base"):
            # 土建大矩形与设备槽位距离很近。进入设备安装/运行阶段后，
            # 土建名称移到角标位置，避免压住 CRF、循环水泵、去污站等设备标签。
            rounded(self.screen, rect, (239, 245, 247), color, 3, 6)
            label = "取排水构筑物" if key == "cooling_base" and self.stage > 0 else self.slot_display_label(key)
            if self.should_show_blueprint_text():
                if self.stage > 0:
                    label_w = 126 if key == "cooling_base" else 118
                    # 取排水构筑物内有多组设备槽位，名称放到框体上方；
                    # 汽机厂房保持在框体内部上方，避免压住“常规岛/冷却水系统”分区标题。
                    label_y = max(154, rect.y - 28) if key == "cooling_base" else rect.y + 28
                    label_rect = pygame.Rect(rect.x + 12, label_y, label_w, 24)
                    rounded(self.screen, label_rect, (255, 255, 255), color, 1, 6)
                    write_fit(self.screen, label, 11, color, label_rect.inflate(-6, -2), align="center", bold=True, min_size=9)
                else:
                    label_rect = rect.inflate(-18, -18)
                    write_fit(self.screen, label, 13, color, label_rect, align="center", bold=True, min_size=10)
        else:
            rounded(self.screen, rect, WHITE, color, 2, 7)
            inner = rect.inflate(-9, -9)
            if key in ("vessel", "pressurizer", "steam_gen"):
                vessel = pygame.Rect(inner.centerx - min(26, inner.width // 3), inner.y + 5,
                                     min(52, inner.width - 10), inner.height - 10)
                rounded(self.screen, vessel, (239, 245, 246), color, 3, min(18, vessel.width // 2))
                if key == "steam_gen":
                    pygame.draw.arc(self.screen, color, vessel.inflate(-12, -15), -1.5, 1.5, 2)
            elif key == "core":
                for x in range(inner.x + 8, inner.right - 3, 12):
                    pygame.draw.line(self.screen, RED, (x, inner.y + 9), (x, inner.bottom - 10), 3)
            elif key == "crdm":
                for x in range(inner.x + 12, inner.right - 8, 16):
                    pygame.draw.line(self.screen, YELLOW, (x, inner.y + 4), (x, inner.bottom - 6), 3)
            elif key in ("primary_pump", "secondary_pump", "tertiary_pump", "efw"):
                pygame.draw.circle(self.screen, color, inner.center, min(inner.width, inner.height) // 3, 3)
                self.arrow((inner.centerx - 10, inner.centery), (inner.centerx + 12, inner.centery), color, 2)
            elif key == "turbine":
                pts = [(inner.x + 8, inner.centery), (inner.centerx, inner.y + 7),
                       (inner.right - 8, inner.centery), (inner.centerx, inner.bottom - 7)]
                pygame.draw.polygon(self.screen, color, pts)
            elif key == "generator":
                pygame.draw.rect(self.screen, (247, 239, 207), inner, border_radius=5)
                write(self.screen, "G", F28, color, inner.center, "center")
            elif key == "condenser":
                for x in range(inner.x + 15, inner.right - 7, 25):
                    pygame.draw.rect(self.screen, color, (x, inner.y + 5, 11, inner.height - 10), 2)
            elif key == "cooling":
                for i in range(3):
                    y = inner.y + 12 + i * 14
                    pygame.draw.arc(self.screen, color, (inner.x + 10, y, inner.width - 20, 13), 0, math.pi, 2)
            elif key in ("diesel_a", "diesel_b"):
                pygame.draw.rect(self.screen, (223, 243, 233), inner, border_radius=4)
                write(self.screen, "DG", F18, color, inner.center, "center")
            elif key == "spray":
                pygame.draw.line(self.screen, color, (inner.x + 9, inner.y + 10), (inner.right - 9, inner.y + 10), 3)
                for x in range(inner.x + 18, inner.right - 10, 20):
                    pygame.draw.line(self.screen, color, (x, inner.y + 13), (x - 5, inner.bottom - 6), 2)
                    pygame.draw.circle(self.screen, CYAN, (x - 6, inner.bottom - 6), 3)
            elif key == "bio_shield":
                # 生物屏蔽：砖墙式屏蔽块。
                pygame.draw.rect(self.screen, (236, 242, 240), inner, border_radius=4)
                for yy in range(inner.y + 8, inner.bottom - 4, 14):
                    pygame.draw.line(self.screen, color, (inner.x + 6, yy), (inner.right - 6, yy), 2)
                for x in range(inner.x + 16, inner.right - 6, 28):
                    pygame.draw.line(self.screen, color, (x, inner.y + 6), (x, inner.bottom - 6), 2)
                pygame.draw.rect(self.screen, color, inner, 2, border_radius=4)
            elif key in ("area_monitor", "effluent_monitor"):
                # 区域/排放监测：监测屏 + 辐射符号，避免空白框。
                monitor = pygame.Rect(inner.x + 8, inner.y + 8, inner.width - 16, inner.height - 16)
                pygame.draw.rect(self.screen, (239, 247, 252), monitor, border_radius=4)
                pygame.draw.rect(self.screen, color, monitor, 2, border_radius=4)
                cx, cy = monitor.center
                pygame.draw.circle(self.screen, color, (cx, cy), 4)
                for angle in (0, 2.09, 4.18):
                    pt = (int(cx + math.cos(angle) * 15), int(cy + math.sin(angle) * 15))
                    pygame.draw.line(self.screen, color, (cx, cy), pt, 3)
                if key == "effluent_monitor":
                    pygame.draw.line(self.screen, DEEP_BLUE, (monitor.x + 8, monitor.bottom - 10), (monitor.right - 8, monitor.bottom - 10), 2)
            elif key == "dosimetry":
                # 个人剂量：剂量计。
                meter = pygame.Rect(inner.centerx - 16, inner.y + 7, 32, inner.height - 14)
                pygame.draw.rect(self.screen, (239, 247, 252), meter, border_radius=5)
                pygame.draw.rect(self.screen, color, meter, 2, border_radius=5)
                pygame.draw.circle(self.screen, color, meter.center, 5)
                pygame.draw.line(self.screen, color, (meter.x + 8, meter.y + 8), (meter.right - 8, meter.y + 8), 2)
                pygame.draw.line(self.screen, GOOD, (meter.x + 8, meter.bottom - 8), (meter.right - 8, meter.bottom - 8), 2)
            elif key == "decon":
                # 去污站：喷淋/冲洗 + 勾选。
                pygame.draw.line(self.screen, color, (inner.x + 10, inner.y + 10), (inner.right - 10, inner.y + 10), 3)
                for x in range(inner.x + 18, inner.right - 8, 18):
                    pygame.draw.circle(self.screen, CYAN, (x, inner.y + 25), 4)
                pygame.draw.lines(self.screen, GOOD, False, [(inner.x + 18, inner.bottom - 18), (inner.x + 32, inner.bottom - 7), (inner.right - 14, inner.y + 23)], 4)
            else:
                # 兜底图标：即使后续新增设备，也不要出现空白拖拽块。
                self.draw_device_icon(key, pygame.Rect(inner.centerx - 18, inner.centery - 18, 36, 36), tiny=True)


    def tool_theme(self, key: str):
        """拖拽工具的小图标主题：不同工具使用不同颜色与形状。"""
        color_map = {
            "flush": DEEP_BLUE,
            "seal": WARNING,
            "diesel_a_test": GREEN,
            "diesel_b_test": GREEN,
            "fuel_load": RED,
            "rod_check": YELLOW,
            "pump_start": BLUE,
            "zero_power_test": PURPLE,
            "backup_cooling": DEEP_BLUE,
            "quick_feed": BLUE,
            "dg_a_action": GREEN,
            "dg_b_action": GREEN,
            "spray_action": GREEN,
            "radiation_sample": PURPLE,
        }
        return color_map.get(key, BLUE)

    def draw_tool_icon(self, key: str, rect: pygame.Rect, color=None, fill=None):
        """绘制拖拽工具图标。

        这些图标不追求复杂拟真，但要与真实对象含义对应：泵、压力表、电缆、燃料吊具、
        棒位校验、主泵启动、中子计数、应急给水、柴油机、喷淋、取样监测等各不相同。
        """
        color = color or self.tool_theme(key)
        fill = fill or (239, 247, 252)
        rounded(self.screen, rect, fill, color, 1, 6)
        inner = rect.inflate(-8, -8)
        cx, cy = inner.center

        if key in ("flush", "backup_cooling"):
            # 泵 + 水流
            pygame.draw.circle(self.screen, color, (inner.x + 11, cy), 9, 2)
            self.arrow((inner.x + 4, cy), (inner.x + 17, cy), color, 2)
            for i in range(3):
                yy = inner.y + 4 + i * 7
                pygame.draw.arc(self.screen, color, (inner.x + 20, yy, inner.width - 22, 8), 0, math.pi, 2)
        elif key in ("seal",):
            # 压力表
            pygame.draw.circle(self.screen, color, (cx, cy), 10, 2)
            pygame.draw.line(self.screen, color, (cx, cy), (cx + 6, cy - 6), 2)
            pygame.draw.line(self.screen, color, (cx - 7, cy + 11), (cx + 7, cy + 11), 2)
        elif key in ("diesel_a_test", "diesel_b_test", "dg_a_action", "dg_b_action"):
            # 电缆 / 柴油机供电
            pygame.draw.rect(self.screen, color, (inner.x + 4, inner.y + 7, 13, 14), 2, border_radius=3)
            pygame.draw.line(self.screen, color, (inner.x + 17, inner.y + 14), (inner.right - 8, inner.y + 14), 2)
            pts = [(inner.right - 10, inner.y + 5), (inner.right - 17, inner.y + 16),
                   (inner.right - 9, inner.y + 16), (inner.right - 16, inner.bottom - 3)]
            pygame.draw.lines(self.screen, WARNING, False, pts, 2)
        elif key == "fuel_load":
            # 燃料吊具 + 燃料棒
            pygame.draw.line(self.screen, color, (cx, inner.y + 1), (cx, inner.y + 9), 2)
            pygame.draw.arc(self.screen, color, (cx - 6, inner.y + 6, 12, 12), 0, math.pi, 2)
            for x in range(inner.x + 5, inner.right - 4, 6):
                pygame.draw.line(self.screen, RED, (x, inner.y + 14), (x, inner.bottom - 2), 2)
        elif key == "rod_check":
            # 控制棒组 + 校验勾
            for x in range(inner.x + 5, inner.right - 8, 7):
                pygame.draw.line(self.screen, color, (x, inner.y + 3), (x, inner.bottom - 4), 2)
            pygame.draw.lines(self.screen, GOOD, False,
                              [(inner.right - 11, cy), (inner.right - 6, cy + 5), (inner.right + 2, cy - 5)], 2)
        elif key == "pump_start":
            # 主泵启动：叶轮 + 箭头
            pygame.draw.circle(self.screen, color, (cx, cy), 10, 2)
            for angle in (0, 2.1, 4.2):
                end = (int(cx + math.cos(angle) * 9), int(cy + math.sin(angle) * 9))
                pygame.draw.line(self.screen, color, (cx, cy), end, 2)
            self.arrow((inner.x + 2, inner.bottom - 3), (inner.right - 2, inner.bottom - 3), color, 2)
        elif key == "zero_power_test":
            # 中子计数仪：探头 + 计数点
            pygame.draw.rect(self.screen, color, (inner.x + 4, inner.y + 5, 13, inner.height - 7), 2, border_radius=3)
            for dx, dy in [(20, 5), (25, 10), (21, 17), (30, 16)]:
                pygame.draw.circle(self.screen, color, (inner.x + dx, inner.y + dy), 2)
        elif key == "quick_feed":
            # 应急给水：水滴 + 接口管
            pts = [(cx, inner.y + 2), (cx - 8, cy + 3), (cx, inner.bottom - 2), (cx + 8, cy + 3)]
            pygame.draw.polygon(self.screen, color, pts, 2)
            pygame.draw.line(self.screen, color, (inner.x + 2, inner.bottom - 4), (inner.right - 2, inner.bottom - 4), 2)
        elif key == "spray_action":
            # EAS 喷淋：喷头 + 水滴
            pygame.draw.line(self.screen, color, (inner.x + 4, inner.y + 5), (inner.right - 4, inner.y + 5), 3)
            for x in range(inner.x + 8, inner.right - 3, 8):
                pygame.draw.line(self.screen, color, (x, inner.y + 9), (x - 3, inner.bottom - 4), 2)
                pygame.draw.circle(self.screen, CYAN, (x - 4, inner.bottom - 2), 2)
        elif key == "radiation_sample":
            # 取样监测：样品瓶 + 辐射三叶符号
            pygame.draw.rect(self.screen, color, (inner.x + 4, inner.y + 7, 12, inner.height - 8), 2, border_radius=3)
            pygame.draw.line(self.screen, color, (inner.x + 7, inner.y + 4), (inner.x + 13, inner.y + 4), 2)
            pygame.draw.circle(self.screen, color, (inner.x + 26, cy), 3)
            for angle in (0, 2.09, 4.18):
                pt = (int(inner.x + 26 + math.cos(angle) * 9), int(cy + math.sin(angle) * 9))
                pygame.draw.line(self.screen, color, (inner.x + 26, cy), pt, 2)
        else:
            pygame.draw.circle(self.screen, color, (cx, cy), 9, 2)
            self.arrow((inner.x + 4, cy), (inner.right - 4, cy), color, 2)

    def draw_kpi_icon(self, kind: str, rect: pygame.Rect, color):
        """顶部经营状态图标：统一无深色描边，文字严格居中。"""
        cx, cy = rect.center
        r = max(18, min(rect.width, rect.height) // 2 - 2)
        font = get_font(21, True)
        if kind == "fund":
            # 资金：金币底色，不再画黑色外描边，保持与其他 KPI 图标一致。
            pygame.draw.circle(self.screen, color, (cx, cy), r)
            text = font.render("资", True, WHITE)
        elif kind == "shield":
            pts = [
                (cx, rect.y + 1), (rect.right - 2, rect.y + 9),
                (rect.right - 7, rect.bottom - 13), (cx, rect.bottom - 1),
                (rect.x + 7, rect.bottom - 13), (rect.x + 2, rect.y + 9),
            ]
            pygame.draw.polygon(self.screen, color, pts)
            text = font.render("防", True, WHITE)
        else:
            pts = [(cx, rect.y + 1), (rect.right - 1, cy), (cx, rect.bottom - 1), (rect.x + 1, cy)]
            pygame.draw.polygon(self.screen, color, pts)
            text = font.render("剂", True, WHITE)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def draw_top(self):
        self.screen.fill(BG)
        pygame.draw.rect(self.screen, WHITE, (LEFT.width, 0, WIDTH - LEFT.width, 60))

        # 顶部改成“经营状态条”：小图标 + 数字，不再堆中文标签。
        title_rect = pygame.Rect(258, 8, 280, 43)
        write_fit(self.screen, "核境造物｜安全并网挑战", 24, BLACK, title_rect,
                  bold=True, min_size=18)

        stage_text = f"{self.stage + 1}/5  {STAGE_SHORT_NAMES[self.stage]}"
        write_fit(self.screen, stage_text, 13, BLUE, pygame.Rect(546, 16, 130, 28), min_size=10)

        # 关键状态只给结论：图标加大，数字与按钮分区，避免右上角互相遮挡。
        alert = self.safety < 65 or self.collective_dose >= DOSE_REFERENCE_LINE
        protection_value = self.safety if self.is_starter_mode() else self.protection_score
        gold = (218, 161, 36)
        kpis = [
            ("fund", money(self.funds), gold if self.funds >= 0 else DANGER, 720),
            ("shield", str(protection_value), BLUE if protection_value >= 80 else WARNING, 860),
            (
                "dose",
                f"{self.collective_dose:.1f}/{TEACHING_DOSE_REDLINE:.0f}",
                GOOD if self.collective_dose < DOSE_REFERENCE_LINE else WARNING if self.collective_dose < DOSE_ORANGE_LINE else ORANGE if self.collective_dose < TEACHING_DOSE_REDLINE else DANGER,
                1000,
            ),
        ]
        for kind, value, color, kpi_x in kpis:
            badge = pygame.Rect(kpi_x, 7, 46, 46)
            self.draw_kpi_icon(kind, badge, color)
            value_rect = pygame.Rect(kpi_x + 60, 8, 96, 40)
            write_fit(self.screen, value, 18 if not alert else 19, color, value_rect,
                      bold=alert and color == DANGER, min_size=13)

        # 右侧只放按钮，不再叠加“运行稳定/重点风险”胶囊，避免遮住音效和设置。
        self.sound_button = pygame.Rect(1180, 13, 62, 36)
        self.settings_button = pygame.Rect(1250, 13, 62, 36)
        self.level_map_button = pygame.Rect(1320, 13, 62, 36)
        # 挑战模式不提供实时指引入口，避免误以为会出现答案式提示。
        self.guide_toggle_button = pygame.Rect(1390, 13, 70, 36) if self.play_mode != "challenge" else pygame.Rect(0, 0, 0, 0)
        self.guide_button = pygame.Rect(0, 0, 0, 0)

        rounded(self.screen, self.sound_button, (247, 250, 251), BORDER, 1, 7)
        sound_text = "音效" if self.audio.enabled and self.audio.available else "静音"
        write_fit(self.screen, sound_text, 13, TEXT_MUTED, self.sound_button.inflate(-7, -4),
                  align="center", min_size=8)
        rounded(self.screen, self.settings_button,
                (239, 247, 252) if getattr(self, "settings_open", False) else (247, 250, 251),
                BLUE if getattr(self, "settings_open", False) else BORDER, 1, 7)
        write_fit(self.screen, "设置", 13, BLUE if getattr(self, "settings_open", False) else TEXT_MUTED,
                  self.settings_button.inflate(-7, -4), align="center", min_size=8)
        rounded(self.screen, self.level_map_button,
                (255, 249, 235) if getattr(self, "level_map_open", False) else (247, 250, 251),
                WARNING if getattr(self, "level_map_open", False) else BORDER, 1, 7)
        write_fit(self.screen, "地图", 13, WARNING if getattr(self, "level_map_open", False) else TEXT_MUTED,
                  self.level_map_button.inflate(-7, -4), align="center", min_size=9)
        if self.play_mode != "challenge":
            rounded(self.screen, self.guide_toggle_button, (234, 249, 240) if self.tutorial else (247, 250, 251),
                    GOOD if self.tutorial else BORDER, 1, 7)
            write_fit(self.screen, "指引" if self.tutorial else "无指引", 13,
                      GOOD if self.tutorial else TEXT_MUTED,
                      self.guide_toggle_button.inflate(-7, -4), align="center", min_size=8)

    def draw_left(self):
        pygame.draw.rect(self.screen, DARK_PANEL, LEFT)
        write(self.screen, "生产链 + 目标", F24, WHITE, (16, 16))
        pygame.draw.line(self.screen, (71, 91, 104), (13, 62), (LEFT.right - 13, 62), 1)

        y = 78
        stage_font = get_font(15, True)
        for index, name in enumerate(STAGE_SHORT_NAMES):
            complete = index < self.stage
            active = index == self.stage
            color = GOOD if complete else BLUE if active else (109, 126, 138)
            pygame.draw.circle(self.screen, color, (26, y + 11), 10)
            if index < len(STAGE_SHORT_NAMES) - 1:
                pygame.draw.line(self.screen, (92, 111, 124), (26, y + 23), (26, y + 39), 3)
            img = stage_font.render(name, True, WHITE if active else (205, 218, 226))
            self.screen.blit(img, (49, y - 3))
            y += 44

        content_top = self.left_content_top()
        pygame.draw.line(self.screen, (63, 82, 97), (12, content_top - 7), (LEFT.right - 12, content_top - 7), 1)

        self.challenge_shuffle_button = pygame.Rect(0, 0, 0, 0)
        self.rebuild_toolbar_rects()
        focus_ui = getattr(self, "focus_ui", FOCUS_UI_DEFAULT)

        if self.stage in (0, 1) and focus_ui:
            next_key = self.next_install_key()
            write_fit(self.screen, "当前目标", 18, (205, 224, 235),
                      pygame.Rect(12, content_top, 120, 28), bold=True, min_size=14)
            if next_key:
                m = ALL_MODULES[next_key]
                step_total = len(CIVIL_INSTALL_ORDER) if self.stage == 0 else len(EQUIPMENT_INSTALL_ORDER)
                installed_count = sum(1 for key in (CIVIL_INSTALL_ORDER if self.stage == 0 else EQUIPMENT_INSTALL_ORDER) if key in self.placed)
                step_text = f"{installed_count + 1}/{step_total}"
                write_fit(self.screen, "拖拽下方推荐设备到中央目标槽位", 11, (177, 202, 214),
                          pygame.Rect(12, content_top + 28, 214, 19), min_size=9)
                for key, rect in self.toolbar_rects.items():
                    rounded(self.screen, rect, (36, 68, 83), WARNING, 2, 10)
                    icon_rect = pygame.Rect(rect.x + 9, rect.y + 10, 42, 42)
                    self.draw_device_icon(key, icon_rect, tiny=True)
                    write_fit(self.screen, m.name, 17, WHITE,
                              pygame.Rect(rect.x + 60, rect.y + 7, rect.width - 70, 23),
                              bold=True, min_size=12)
                    sub_text = f"{m.cost}币 / {m.days:g}天"
                    if key == "primary_pump":
                        sub_text = f"选型：{self.pump_choice} / {m.days:g}天"
                    write_fit(self.screen, sub_text, 12, (205, 224, 235),
                              pygame.Rect(rect.x + 60, rect.y + 37, rect.width - 122, 17), min_size=9)
                    step_badge = pygame.Rect(rect.right - 56, rect.y + 34, 48, 22)
                    rounded(self.screen, step_badge, WARNING, WARNING, 1, 6)
                    write_fit(self.screen, step_text, 10, WHITE, step_badge.inflate(-3, -2),
                              align="center", min_size=8)
                tip = pygame.Rect(12, content_top + 146, 214, 86)
                rounded(self.screen, tip, CARD, (78, 100, 114), 1, 8)
                write_fit(self.screen, "操作提示", 13, (205, 224, 235), pygame.Rect(tip.x + 10, tip.y + 8, 100, 20),
                          bold=True, min_size=10)
                write(self.screen, "拖当前目标", get_font(12), (184, 205, 217), (tip.x + 12, tip.y + 36))
                write(self.screen, "到中央目标槽位", get_font(12), (184, 205, 217), (tip.x + 12, tip.y + 60))
            else:
                done = pygame.Rect(12, content_top + 42, 214, 86)
                rounded(self.screen, done, (36, 82, 67), GOOD, 2, 10)
                write_fit(self.screen, "本阶段目标已完成", 18, WHITE, done.inflate(-14, -18),
                          align="center", bold=True, min_size=13)
        elif self.stage == 0:
            write(self.screen, "本关建筑", F18, (205, 224, 235), (12, content_top))
            if getattr(self, "play_mode", "") == "challenge":
                self.challenge_shuffle_button = pygame.Rect(132, content_top + 1, 94, 26)
                active = bool(getattr(self, "challenge_shuffle_modules", False))
                rounded(self.screen, self.challenge_shuffle_button, BLUE if active else CARD, BLUE, 1, 6)
                write_fit(self.screen, "固定顺序" if active else "随机顺序", 10, WHITE if active else BLUE,
                          self.challenge_shuffle_button.inflate(-5, -3), align="center", min_size=8)
                write_fit(self.screen, "挑战：可自行判断安装顺序", 11, (177, 202, 214),
                          pygame.Rect(12, content_top + 29, 214, 20), min_size=9)
            else:
                write_fit(self.screen, "挑战模式：自行判断安装顺序", 11, (177, 202, 214),
                          pygame.Rect(12, content_top + 27, 214, 20), min_size=9)
            for key, rect in self.toolbar_rects.items():
                installed = key in self.placed
                module = ALL_MODULES[key]
                fill = (37, 83, 67) if installed else CARD
                rounded(self.screen, rect, fill, GOOD if installed else (74, 95, 110), 1, 8)
                icon_rect = pygame.Rect(rect.x + 7, rect.y + 6, 32, 32)
                self.draw_device_icon(key, icon_rect, tiny=True)
                reserve = 24 if installed else 4
                write_fit(self.screen, module.name, 13, WHITE,
                          pygame.Rect(rect.x + 48, rect.y + 5, rect.width - 54 - reserve, 19),
                          min_size=10)
                write_fit(self.screen, f"{module.cost}币 / {module.days:g}天", 11,
                          (173, 206, 189) if installed else (173, 194, 207),
                          pygame.Rect(rect.x + 48, rect.y + 26, rect.width - 58, 16), min_size=9)
                if installed:
                    write_fit(self.screen, "√", 16, GOOD,
                              pygame.Rect(rect.right - 28, rect.y + 10, 20, 22), align="center", bold=True, min_size=12)
        elif self.stage == 1:
            tab_x = 12
            visible_tabs = ["反应堆", "常规", "安全"] if self.is_starter_mode() else list(EQUIP_TABS.keys())
            tab_w = 38 if getattr(self, "play_mode", "") == "challenge" and len(visible_tabs) >= 4 else 50
            tab_gap = 4 if tab_w == 42 else 4
            for tab in visible_tabs:
                rect = pygame.Rect(tab_x, content_top + 3, tab_w, 28)
                self.tab_rects[tab] = rect
                fill = BLUE if tab == self.active_tab else CARD
                rounded(self.screen, rect, fill, (88, 110, 124), 1, 6)
                if tab == "反应堆" and getattr(self, "play_mode", "") == "challenge":
                    tab_label = "基础"
                elif tab == "反应堆" and len(visible_tabs) >= 4:
                    tab_label = "反应"
                else:
                    tab_label = tab
                write_fit(self.screen, tab_label, 10 if tab_w == 42 else 11, WHITE, rect.inflate(-4, -3), align="center", min_size=8)
                tab_x += tab_w + tab_gap
            if getattr(self, "play_mode", "") == "challenge":
                self.challenge_shuffle_button = pygame.Rect(182, content_top + 3, 44, 28)
                active = bool(getattr(self, "challenge_shuffle_modules", False))
                rounded(self.screen, self.challenge_shuffle_button, BLUE if active else CARD, BLUE, 1, 6)
                write_fit(self.screen, "乱序" if active else "固定", 10, WHITE if active else BLUE,
                          self.challenge_shuffle_button.inflate(-3, -3), align="center", min_size=8)
            for key, rect in self.toolbar_rects.items():
                installed = key in self.placed
                fill = (37, 83, 67) if installed else CARD
                rounded(self.screen, rect, fill, GOOD if installed else (74, 95, 110), 1, 8)
                icon_rect = pygame.Rect(rect.x + 7, rect.y + 6, 32, 32)
                self.draw_device_icon(key, icon_rect, tiny=True)
                display = ALL_MODULES[key].name
                reserve = 24 if installed else 4
                write_fit(self.screen, display, 13, WHITE,
                          pygame.Rect(rect.x + 48, rect.y + 5, rect.width - 54 - reserve, 19),
                          min_size=9)
                sub_text = f"{ALL_MODULES[key].cost}币 / {ALL_MODULES[key].days:g}天"
                if key == "primary_pump":
                    sub_text = f"选型：{self.pump_choice} / {ALL_MODULES[key].days:g}天"
                write_fit(self.screen, sub_text, 11,
                          (173, 206, 189) if installed else (173, 194, 207),
                          pygame.Rect(rect.x + 48, rect.y + 26, rect.width - 58, 16), min_size=8)
                if installed:
                    write_fit(self.screen, "√", 16, GOOD,
                              pygame.Rect(rect.right - 28, rect.y + 10, 20, 22), align="center", bold=True, min_size=12)
        elif self.stage == 2:
            self.draw_quiz_left()
        elif self.stage == 3:
            self.draw_critical_left()
        elif self.stage == 4:
            self.draw_running_left()

        pygame.draw.line(self.screen, (63, 82, 97), (12, 790), (LEFT.right - 12, 790), 1)
        write(self.screen, "安全评分", F13, (184, 205, 217), (12, 800))
        score_color = GOOD if self.safety >= 85 else WARNING if self.safety >= 65 else DANGER
        write(self.screen, str(self.safety), F28, score_color, (14, 820))
        if self.stage < 2:
            required = len(CIVIL) if self.stage == 0 else len(EQUIPMENT)
            have = sum(1 for key in (CIVIL if self.stage == 0 else EQUIPMENT) if key in self.placed)
            bar = pygame.Rect(76, 827, 146, 12)
            pygame.draw.rect(self.screen, (70, 89, 103), bar, border_radius=6)
            pygame.draw.rect(self.screen, GOOD, (bar.x, bar.y, int(bar.width * have / required), bar.height),
                             border_radius=6)
            write(self.screen, f"{have}/{required}", F11, WHITE, bar.center, "center")

    def draw_quiz_left(self):
        top = self.left_content_top()
        write(self.screen, "调试任务", F16, WHITE, (12, top + 2))
        tasks = [
            ("flush", "1. 管路冲洗", self.quiz["flush"] is True),
            ("seal", "2. 密封性试验", self.quiz["seal"] is True),
            ("diesel_a_test", "3. A列电源试验", self.quiz["diesel_a_test"]),
            ("diesel_b_test", "4. B列电源试验", self.quiz["diesel_b_test"]),
        ]
        next_key = self.next_commissioning_key() if hasattr(self, "next_commissioning_key") else None
        selected = getattr(self, "selected_quiz", None)
        y = top + 34
        self.action_rects = {}
        for key, name, done in tasks:
            current = key == next_key
            active = key == selected
            locked = (not done) and (not current)
            fill = (37, 83, 67) if done else (42, 86, 105) if active else CARD
            border = GOOD if done else BLUE if active else WARNING if current else (84, 105, 119)
            rect = pygame.Rect(12, y, 214, 42)
            rounded(self.screen, rect, fill, border, 2 if active or current else 1, 7)
            prefix = "√ " if done else "当前 " if current else "锁 "
            color = WHITE if not locked else (155, 177, 189)
            write_fit(self.screen, prefix + name, 12, color, rect.inflate(-10, -5), min_size=9)
            self.action_rects[key] = rect
            y += 48
        tip = "顺序链：选任务 → 拖工具 → 判结果。跳步会轻微扣分。"
        write_wrapped(self.screen, tip, 12,
                      (181, 205, 216), pygame.Rect(12, y + 8, 212, 56), min_size=9, max_lines=3, line_gap=14)

    def draw_critical_left(self):
        top = self.left_content_top()
        write(self.screen, "启动步骤", F16, WHITE, (12, top + 2))
        self.critical_buttons = []
        self.critical_tool_rects = {}
        selected = getattr(self, "selected_critical", None)
        y = top + 36
        for i, key in enumerate(CRITICAL_ORDER):
            name = CRITICAL_LABELS[key]
            done = i < self.critical_step
            current = i == self.critical_step
            selected_now = key == selected
            rect = pygame.Rect(12, y, 214, 40)
            self.critical_buttons.append(rect)
            fill = GOOD if done else (BLUE if selected_now else CARD)
            border = GOOD if done else (WARNING if current else (82, 104, 117))
            rounded(self.screen, rect, fill, border, 2 if current else 1, 7)
            prefix = "√ " if done else ("▶ " if current else f"{i + 1}. ")
            write_fit(self.screen, prefix + name, 12, WHITE if done or current or selected_now else (166, 187, 198),
                      rect.inflate(-10, -5), min_size=9)
            y += 46

        key = selected if selected in CRITICAL_ORDER and not self.critical_task_done(selected) else None
        if key:
            tool_rect = pygame.Rect(12, y + 6, 214, 48)
            self.critical_tool_rects[key] = tool_rect
            ready = getattr(self, "critical_tool_ready", {}).get(key, False)
            rounded(self.screen, tool_rect, (36, 68, 83) if not ready else (36, 82, 67),
                    GOOD if ready else WARNING, 2, 8)
            icon_rect = pygame.Rect(tool_rect.x + 10, tool_rect.y + 8, 32, 32)
            self.draw_tool_icon(key, icon_rect, GOOD if ready else WARNING, fill=(245, 249, 250))
            write_fit(self.screen, CRITICAL_TOOL_NAMES[key], 13, WHITE,
                      pygame.Rect(tool_rect.x + 50, tool_rect.y + 8, 144, 18), bold=True, min_size=10)
            write_fit(self.screen, "拖到中央高亮区" if not ready else "已就位，选底部操作",
                      10, (184, 205, 217), pygame.Rect(tool_rect.x + 50, tool_rect.y + 29, 144, 15), min_size=8)
            y += 62

        hint = "按顺序拖工具到高亮区。"
        write_wrapped(self.screen, hint, 11, (183, 206, 217),
                      pygame.Rect(12, min(y + 8, 742), 212, 46), min_size=9, max_lines=2, line_gap=13)

    def draw_running_left(self):
        top = self.left_content_top()
        self.operation_tool_rects = {}
        self.diagnostic_buttons = {}
        self.upgrade_buttons = {}
        self.maintenance_button = pygame.Rect(0, 0, 0, 0)
        self.repair_button = pygame.Rect(0, 0, 0, 0)

        if self.scrammed:
            write(self.screen, "机组已自动停堆", F16, DANGER, (12, top + 2))
            rounded(self.screen, pygame.Rect(12, top + 37, 214, 116), CARD, DANGER, 2, 7)
            write_wrapped(self.screen, "运行状态已冻结。请点击底部“结束挑战”，查看屏障损伤、事件时间线与事故复盘。",
                          12, WHITE, pygame.Rect(23, top + 51, 190, 65), min_size=10, max_lines=4)
            write_fit(self.screen, "停堆后不再执行检修任务", 11, WARNING,
                      pygame.Rect(23, top + 125, 190, 18), min_size=9)
            return

        if self.is_starter_mode() and not (self.warning_event or self.fault):
            write(self.screen, "极简运行练习", F16, WHITE, (12, top + 2))
            rounded(self.screen, pygame.Rect(12, top + 37, 214, 130), CARD, BLUE, 1, 7)
            write_fit(self.screen, "目标：稳定运行 18 秒", 13, BLUE,
                      pygame.Rect(23, top + 49, 190, 20), bold=True, min_size=10)
            write_wrapped(self.screen, "出现预警时，调高右侧冷却水滑块。",
                          12, WHITE, pygame.Rect(23, top + 81, 190, 62), min_size=10, max_lines=4)
            progress = clamp(self.runtime / 18.0, 0, 1)
            bar = pygame.Rect(23, top + 146, 188, 8)
            pygame.draw.rect(self.screen, (70, 89, 103), bar, border_radius=4)
            pygame.draw.rect(self.screen, GOOD, (bar.x, bar.y, int(bar.width * progress), bar.height), border_radius=4)
            write_wrapped(self.screen, "完成后可尝试完整引导。",
                          11, (184, 205, 217), pygame.Rect(12, top + 187, 212, 52), min_size=9, max_lines=3)
            return

        if getattr(self, "minor_event", None):
            event = self.minor_event
            write(self.screen, "随机运行小事件", F16, WARNING, (12, top + 2))
            box = pygame.Rect(12, top + 34, 214, 120)
            rounded(self.screen, box, CARD, WARNING, 2, 7)
            write_fit(self.screen, event.get("title", "运行小事件"), 13, WHITE,
                      pygame.Rect(box.x + 12, box.y + 10, box.width - 24, 22), bold=True, min_size=10)
            write_wrapped(self.screen, event.get("desc", "请限时判断处理。"), 11, (183, 211, 222),
                          pygame.Rect(box.x + 12, box.y + 39, box.width - 24, 38), min_size=9, max_lines=2)
            left = max(0, int(getattr(self, "minor_event_left", 0) + 0.99))
            write_fit(self.screen, f"剩余 {left}s", 13, WARNING, pygame.Rect(box.x + 12, box.y + 86, 190, 20), bold=True, min_size=10)
            self.minor_event_buttons = {}
            y = top + 170
            for idx, option in enumerate(event.get("choices", [])[:2]):
                rect = pygame.Rect(12, y, 214, 42)
                self.minor_event_buttons[idx] = rect
                rounded(self.screen, rect, WHITE, BLUE, 1, 7)
                write_fit(self.screen, option.get("text", "处理"), 13, BLUE, rect.inflate(-10, -5), align="center", min_size=10)
                y += 50
            write_wrapped(self.screen, "随机事件会影响资金、安全、剂量或关键参数。",
                          10, (184, 205, 217), pygame.Rect(12, y + 6, 212, 40), min_size=8, max_lines=2)
            return

        if self.dose_task:
            write(self.screen, "受控区作业策划", F16, WARNING, (12, top + 2))
            rounded(self.screen, pygame.Rect(12, top + 34, 214, 110), CARD, WARNING, 1, 7)
            write_fit(self.screen, self.dose_task["title"], 13, WHITE,
                      pygame.Rect(22, top + 45, 194, 22), bold=True, min_size=10)
            priority_name = {"dose": "低剂量优先", "speed": "时限优先", "economy": "经济优先"}[self.dose_task["priority"]]
            write_fit(self.screen, f"{priority_name}｜≤{self.dose_task['deadline']}模拟秒",
                      11, WARNING, pygame.Rect(22, top + 74, 194, 17), min_size=9)
            write_fit(self.screen, f"专项预算≤{self.dose_task['budget_limit']}币",
                      11, (183, 211, 222), pygame.Rect(22, top + 98, 194, 17), min_size=9)
            self.plan_open_button = pygame.Rect(12, top + 158, 214, 42)
            rounded(self.screen, self.plan_open_button, BLUE, BLUE, 1, 7)
            write_fit(self.screen, "制定作业方案", 14, WHITE, self.plan_open_button.inflate(-10, -5),
                      align="center", min_size=11)
            write_wrapped(self.screen, "用时越长收益越低。",
                          11, (184, 205, 217), pygame.Rect(12, top + 218, 212, 43), min_size=9, max_lines=2)
            return

        active_event = self.warning_event or self.fault
        if active_event:
            title = "黄色预警诊断" if self.warning_event and not self.diagnosis_resolved else (
                "黄色预警处置" if self.warning_event else "红色故障处置"
            )
            title_color = WARNING if self.warning_event else DANGER
            write(self.screen, title, F16, title_color, (12, top + 2))
            if self.warning_event and not self.diagnosis_resolved:
                case = DIAGNOSTIC_CASES[self.warning_event["key"]]
                write_wrapped(self.screen, "根据右侧症状与趋势，选择最可能原因：",
                              12, WHITE, pygame.Rect(12, top + 33, 214, 38), min_size=10, max_lines=2)
                y = top + 82
                for choice in case["choices"]:
                    rect = pygame.Rect(12, y, 214, 40)
                    self.diagnostic_buttons[choice] = rect
                    rounded(self.screen, rect, CARD, WARNING, 1, 7)
                    write_fit(self.screen, choice, 12, WHITE, rect.inflate(-8, -5),
                              align="center", min_size=9)
                    y += 47
                write_wrapped(self.screen, "误诊会压缩处置时间并影响安全屏障。",
                              11, (184, 205, 217), pygame.Rect(12, y + 8, 212, 40), min_size=9, max_lines=2)
                return
            event_key = active_event["key"] if self.warning_event else self.fault.key
            rule = EVENT_RULES[event_key]
            if not getattr(self, "accident_choice_resolved", False):
                self.accident_choice_buttons = {}
                try:
                    from .reference_content import accident_decision_options
                    ref_case = getattr(self, "active_reference_accident", None) or getattr(self, "last_reference_accident", None)
                    options = accident_decision_options(event_key, ref_case) or ACCIDENT_DECISION_OPTIONS.get(event_key, [])
                except Exception:
                    options = ACCIDENT_DECISION_OPTIONS.get(event_key, [])
                write_wrapped(self.screen, "先选方案；错扣资源。",
                              12, WHITE, pygame.Rect(12, top + 31, 214, 42), min_size=10, max_lines=2)
                y = top + 80
                for idx, option in enumerate(options):
                    rect = pygame.Rect(12, y, 214, 42)
                    self.accident_choice_buttons[idx] = rect
                    rounded(self.screen, rect, CARD, title_color, 1, 7)
                    write_fit(self.screen, option["text"], 11, WHITE, rect.inflate(-8, -5),
                              align="center", min_size=8)
                    y += 70
                feedback = getattr(self, "accident_choice_feedback", "")
                if feedback:
                    write_wrapped(self.screen, feedback, 10, WARNING, pygame.Rect(12, y + 5, 214, 44), min_size=8, max_lines=2)
                return

            instruction = rule["guide"] if self.is_guided_mode() or self.fault else "判断正确，请完成设备接入。"
            if event_key == "power":
                instruction = "拖 A列，再拖 B列。\n放入目标母线槽位。"
            write_wrapped(self.screen, instruction, 12, WHITE,
                          pygame.Rect(12, top + 31, 214, 62), min_size=10, max_lines=3, line_gap=15)
            y = top + 104
            for tool in self.event_required_tools():
                data = RUN_OPERATION_TOOLS[tool]
                rect = pygame.Rect(12, y, 214, 48)
                self.operation_tool_rects[tool] = rect
                done = tool in self.operation_done
                needed = tool == self.event_next_tool()
                border = GOOD if done else (title_color if needed else (84, 105, 119))
                rounded(self.screen, rect, (37, 83, 67) if done else CARD, border, 2 if needed else 1, 7)
                icon_rect = pygame.Rect(rect.x + 8, rect.y + 8, 32, 32)
                self.draw_tool_icon(tool, icon_rect, data["color"], fill=(245, 249, 250))
                label = "已接入 " + data["name"] if done else "拖拽 " + data["name"]
                write_fit(self.screen, label, 13, WHITE, pygame.Rect(rect.x + 48, rect.y + 7, 150, 19), min_size=10)
                write_fit(self.screen, "放入图中目标槽位", 11, (183, 211, 222),
                          pygame.Rect(rect.x + 48, rect.y + 27, 150, 15), min_size=9)
                y += 56
            return

        issue = self.barrier_repair_required()
        if self.service_job or issue:
            job = self.service_job or issue
            title = "维护执行中" if self.service_job else "屏障恢复要求"
            write(self.screen, title, F16, WARNING, (12, top + 2))
            rounded(self.screen, pygame.Rect(12, top + 35, 214, 108), CARD, WARNING, 1, 7)
            write_fit(self.screen, job["title"] if self.service_job else job["name"], 13, WHITE,
                      pygame.Rect(22, top + 46, 192, 20), bold=True, min_size=10)
            if self.service_job:
                write_fit(self.screen, f"剩余 {self.service_job['remaining']:.1f}s｜功率限制 {self.current_power_cap()*100:.0f}%",
                          11, WARNING, pygame.Rect(22, top + 78, 192, 17), min_size=9)
                write_wrapped(self.screen, "任务完成后自动恢复相应状态。",
                              11, (183, 211, 222), pygame.Rect(22, top + 104, 190, 28), min_size=9, max_lines=2)
            else:
                write_wrapped(self.screen, issue["why"], 11, (183, 211, 222),
                              pygame.Rect(22, top + 73, 190, 42), min_size=9, max_lines=2)
                self.repair_button = pygame.Rect(12, top + 157, 214, 42)
                rounded(self.screen, self.repair_button, WARNING, WARNING, 1, 7)
                repair_cost = self.service_cost(issue["cost"]) if hasattr(self, "service_cost") else issue["cost"]
                write_fit(self.screen, f"启动恢复任务｜{repair_cost}币", 13, WHITE,
                          self.repair_button.inflate(-10, -5), align="center", min_size=10)
            return

        write(self.screen, "运行维护与升级", F16, WHITE, (12, top + 2))
        weak_key, weak_value = self.weakest_equipment()
        weak = HEALTH_META[weak_key]
        health_box = pygame.Rect(12, top + 40, 214, 112)
        rounded(self.screen, health_box, CARD, WARNING if weak_value < 88 else (78, 100, 114), 1, 7)
        write_fit(self.screen, "最低健康度设备", 13, WHITE,
                  pygame.Rect(22, top + 50, 180, 20), min_size=11)
        write_fit(self.screen, weak['name'], 13,
                  (183, 211, 222),
                  pygame.Rect(22, top + 76, 120, 20), min_size=11)
        write_fit(self.screen, f"{weak_value:.0f}%", 20,
                  WARNING if weak_value < 90 else GOOD,
                  pygame.Rect(142, top + 68, 60, 30), align="right", bold=True, min_size=16)
        self.maintenance_button = pygame.Rect(22, top + 112, 190, 24)
        rounded(self.screen, self.maintenance_button, BLUE if weak_value < 98 else CARD,
                BLUE if weak_value < 98 else BORDER, 1, 5)
        maintenance_cost = self.service_cost(weak["cost"]) if hasattr(self, "service_cost") else weak["cost"]
        write_fit(self.screen, f"安排计划检修｜{maintenance_cost}币", 10,
                  WHITE if weak_value < 98 else TEXT_MUTED,
                  self.maintenance_button.inflate(-5, -2), align="center", min_size=8)

        y = health_box.bottom + 14
        self.upgrade_buttons = {}
        # 优先展示 CPR1000 专业系统升级；传统性能升级仍保留在列表末尾。
        preferred = ["asg", "ris", "eas"]
        for key in preferred:
            if key not in self.upgrades:
                continue
            up = self.upgrades[key]
            rect = pygame.Rect(12, y, 214, 56)
            self.upgrade_buttons[key] = rect
            complete = up.level >= 1
            rounded(self.screen, rect, (36, 82, 67) if complete else CARD,
                    GOOD if complete else (78, 100, 114), 1, 6)
            state = "完成" if complete else f"{up.remaining:.1f}s" if up.in_progress else f"{up.cost}币"
            write_fit(self.screen, up.name, 13, WHITE, pygame.Rect(rect.x + 14, rect.y + 11, 126, 26), min_size=11)
            write_fit(self.screen, state, 12, GOOD if complete else WARNING if up.in_progress else (183, 211, 222),
                      pygame.Rect(rect.right - 76, rect.y + 11, 62, 26), align="right", min_size=10)
            y += 68
        write_fit(self.screen, "更多系统：右侧维护页查看", 10, (183, 211, 222), pygame.Rect(14, y + 6, 210, 20), min_size=8)

    def draw_center(self):
        rounded(self.screen, CENTER, WHITE, BORDER, 2, 9)
        script = get_stage_script(self.stage)
        write_fit(self.screen, f"{script['chapter']}｜{script['title']}", 20, BLACK, pygame.Rect(270, 80, 760, 30), bold=True, min_size=13)
        write_wrapped(self.screen, script["main_task"], 13, TEXT_MUTED, pygame.Rect(270, 112, 700, 34), min_size=10, max_lines=2, line_gap=19)
        self.draw_blueprint_label_toggle()
        self.draw_site_outline()
        self.draw_pipes()
        self.draw_flow_animation()
        self.draw_slots_and_installed()
        self.draw_commissioning_targets()
        self.draw_critical_targets()
        self.draw_operation_targets()
        self.draw_feedback()
        if self.tutorial and getattr(self, "play_mode", "") != "challenge":
            self.draw_tutorial_hint()

    def draw_site_outline(self):
        # 核岛 / 常规岛 / 电网背景
        pygame.draw.rect(self.screen, (249, 251, 252), (279, 182, 392, 506), border_radius=8)
        pygame.draw.rect(self.screen, (249, 251, 252), (683, 182, 430, 506), border_radius=8)
        # 区域标题下移，给章节标题和任务描述留出足够空间。
        nuclear_tab = pygame.Rect(292, 164, 76, 24)
        conventional_tab = pygame.Rect(698, 164, 168, 24)
        rounded(self.screen, nuclear_tab, (255, 255, 255), GRID, 1, 6)
        rounded(self.screen, conventional_tab, (255, 255, 255), GRID, 1, 6)
        if self.should_show_blueprint_text():
            write_fit(self.screen, "核岛", 13, TEXT_MUTED, nuclear_tab.inflate(-8, -2), align="center", min_size=11)
            write_fit(self.screen, "常规岛 / 冷却水系统", 13, TEXT_MUTED, conventional_tab.inflate(-8, -2), align="center", min_size=10)
        pygame.draw.line(self.screen, GRID, (676, 184), (676, 688), 2)
        # 电网城市
        for x, h in [(1042, 32), (1058, 49), (1077, 27), (1093, 59), (1112, 39)]:
            pygame.draw.rect(self.screen, (119, 135, 145), (x, 157 - h, 13, h))
            pygame.draw.rect(self.screen, YELLOW, (x + 4, 157 - h + 8, 3, 5))
        # 标签默认隐藏，点击“显示文字”后再显示，避免压住设备图标。
        if self.should_show_blueprint_text():
            write(self.screen, "城市电网", F12, TEXT_MUTED, (1000, 144), "center")
        pygame.draw.line(self.screen, STEEL, (1028, 159), (1125, 159), 2)

    def draw_professional_system_flow(self):
        """右侧专业系统关系图。

        不再叠加在中央电站画面上，避免遮挡设备；采用更大字号和分行显示。
        """
        x = RIGHT.x + 20
        w = RIGHT.width - 40
        box = pygame.Rect(x, 648, w, 116)
        rounded(self.screen, box, (248, 252, 253), (189, 204, 211), 1, 9)
        write_fit(self.screen, "系统流程（三回路分离）", 13, BLUE, pygame.Rect(box.x + 12, box.y + 8, box.width - 24, 20), bold=True, min_size=10)
        write_fit(self.screen, "一回路：堆芯 → 蒸汽发生器 → 主泵 → 堆芯", 10, BLACK, pygame.Rect(box.x + 12, box.y + 31, box.width - 24, 18), bold=True, min_size=8)
        write_fit(self.screen, "二回路：蒸汽发生器 → 汽轮机 → 冷凝器 → 给水泵", 10, BLACK, pygame.Rect(box.x + 12, box.y + 51, box.width - 24, 18), bold=True, min_size=8)
        write_fit(self.screen, "三回路：海水/循环水 → 冷凝器 → 排海", 10, BLACK, pygame.Rect(box.x + 12, box.y + 71, box.width - 24, 18), bold=True, min_size=8)
        write_fit(self.screen, "安全：RIS｜ASG｜EAS｜EDG｜剂量监测", 10, TEXT_MUTED,
                  pygame.Rect(box.x + 12, box.y + 93, box.width - 24, 16), min_size=8)

    def draw_flow_animation(self):
        """中央画面流动/闪烁动画：让设备运行状态更像游戏。"""
        now = pygame.time.get_ticks()
        phase = (now // 120) % 16
        # 三回路链路：循环冷却水系统（CRF）与冷凝器之间，用蓝色流点表现流动。
        flow_paths = []
        if "cooling" in self.placed:
            r = self.placed["cooling"]
            flow_paths.append(((r.left - 40, r.centery), (r.left - 140, r.centery), BLUE))
        if "condenser" in self.placed and "cooling" in self.placed:
            a, b = self.placed["condenser"], self.placed["cooling"]
            flow_paths.append(((b.left, b.centery), (a.centerx, a.bottom + 18), CYAN))
        if "primary_pump" in self.placed and "steam_gen" in self.placed:
            a, b = self.placed["primary_pump"], self.placed["steam_gen"]
            flow_paths.append(((a.centerx, a.centery), (b.centerx, b.centery), ORANGE))
        if "turbine" in self.placed and "generator" in self.placed:
            a, b = self.placed["turbine"], self.placed["generator"]
            flow_paths.append(((a.right, a.centery), (b.left, b.centery), YELLOW))
        for start, end, color in flow_paths:
            pygame.draw.line(self.screen, color, start, end, 2)
            sx, sy = start
            ex, ey = end
            for i in range(4):
                t = ((phase + i * 4) % 16) / 16
                x = int(sx + (ex - sx) * t)
                y = int(sy + (ey - sy) * t)
                pygame.draw.circle(self.screen, color, (x, y), 4)

        # 故障状态：对应设备红色脉冲；停堆状态：全场压暗并出现扫描线。
        active_key = self.fault.key if self.fault else (self.warning_event["key"] if self.warning_event else None)
        event_devices = {
            "vacuum": ["condenser", "cooling", "tertiary_pump"],
            "water": ["steam_gen", "secondary_pump", "efw"],
            "power": ["generator", "diesel_a", "diesel_b"],
        }.get(active_key, [])
        if event_devices:
            pulse_color = DANGER if self.fault else WARNING
            pulse_w = 2 + int((math.sin(now / 95) + 1) * 2)
            for key in event_devices:
                if key in self.placed:
                    pygame.draw.rect(self.screen, pulse_color, self.placed[key].inflate(12, 12), pulse_w, border_radius=10)
        if self.scrammed:
            overlay = pygame.Surface((CENTER.width, CENTER.height), pygame.SRCALPHA)
            overlay.fill((18, 24, 30, 68))
            scan_y = int(CENTER.y + 40 + (now // 18) % max(1, CENTER.height - 80))
            self.screen.blit(overlay, CENTER.topleft)
            pygame.draw.line(self.screen, DANGER, (CENTER.x + 12, scan_y), (CENTER.right - 12, scan_y), 2)

        # 当前推荐槽位闪烁，减少玩家找不到目标；挑战模式禁用答案式高亮。
        if self.stage in (0, 1) and getattr(self, "play_mode", "") != "challenge":
            key = self.next_install_key()
            if key and key in ALL_MODULES:
                target = ALL_MODULES[key].slot
                if (now // 350) % 2 == 0:
                    pygame.draw.rect(self.screen, WARNING, target.inflate(10, 10), 3, border_radius=8)

    def draw_slots_and_installed(self):
        relevant = CIVIL if self.stage == 0 else ALL_MODULES
        for key, module in relevant.items():
            if self.stage == 0 and key not in CIVIL:
                continue
            if self.stage > 0 and key in CIVIL and key not in self.placed:
                continue
            if key in self.placed:
                if self.should_show_center_markers():
                    self.draw_device_icon(key, self.placed[key])
                else:
                    # 挑战模式默认只显示“已占位”的外框，不显示设备图标和名称，避免答案式提示。
                    rounded(self.screen, self.placed[key], (249, 251, 252), module.color, 2, 7)
                self.draw_device_status_light(key, self.placed[key])
                # 设备名称默认不压在图上；挑战模式关闭中央标识时也不显示选中标签。
                if self.selected == key and self.should_show_center_markers():
                    label_text = self.slot_display_label(key)
                    label_w = min(190, max(104, len(label_text) * 13 + 18))
                    label = pygame.Rect(module.slot.centerx - label_w // 2, module.slot.bottom + 3, label_w, 20)
                    label.clamp_ip(CENTER.inflate(-10, -10))
                    rounded(self.screen, label, (255, 255, 255), BORDER, 1, 6)
                    write_fit(self.screen, label_text, 10, BLACK, label.inflate(-5, -2),
                              align="center", min_size=8)
            elif (self.stage == 0 and key in CIVIL) or (self.stage == 1 and key in EQUIPMENT):
                self.dashed_rect(module.slot, (153, 170, 180), 2)
                self.draw_slot_label(key, module.slot)
                self.draw_device_status_light(key, module.slot, installed=False)

        if (not self.is_challenge_mode()
                and self.pending_install and self.pending_install in ALL_MODULES
                and self.pending_install not in self.placed):
            target = ALL_MODULES[self.pending_install].slot
            pulse = 2 + int((math.sin(pygame.time.get_ticks() / 140) + 1) * 1.2)
            pygame.draw.rect(self.screen, BLUE, target.inflate(18, 18), pulse, border_radius=10)
            write_fit(self.screen, "点击此处安装", 11, BLUE,
                      pygame.Rect(target.x, max(151, target.y - 24), max(92, target.width), 18),
                      align="center", min_size=9)

        if not self.is_challenge_mode() and isinstance(self.snap_target, pygame.Rect):
            pulse = 3 + int((math.sin(pygame.time.get_ticks() / 120) + 1) * 1.5)
            pygame.draw.rect(self.screen, GOOD, self.snap_target.inflate(14, 14), pulse, border_radius=10)
            write_fit(self.screen, "松开即可安装", 11, GOOD,
                      pygame.Rect(self.snap_target.x, max(151, self.snap_target.y - 24),
                                  max(82, self.snap_target.width), 18), align="center", min_size=9)

        if self.dragging:
            ghost = pygame.Surface((self.dragging["rect"].width, self.dragging["rect"].height), pygame.SRCALPHA)
            ghost.fill((80, 150, 190, 50))
            pygame.draw.rect(ghost, (45, 123, 182), ghost.get_rect(), 2, border_radius=6)
            self.screen.blit(ghost, self.dragging["rect"])
            if self.dragging.get("commissioning") or self.dragging.get("critical") or self.dragging.get("operation"):
                icon_rect = pygame.Rect(self.dragging["rect"].x + 6, self.dragging["rect"].y + 6, 30, 30)
                self.draw_tool_icon(self.dragging["key"], icon_rect, self.tool_theme(self.dragging["key"]), fill=(245, 249, 250))
            if self.dragging.get("commissioning"):
                name = {
                    "flush": "冲洗泵车", "seal": "压力试验仪",
                    "diesel_a_test": "A列试验电缆", "diesel_b_test": "B列试验电缆",
                }.get(self.dragging["key"], "调试工具")
            elif self.dragging.get("critical"):
                name = {
                    "fuel_load": "燃料吊具",
                    "rod_check": "棒位校验器",
                    "pump_start": "主泵启动盘",
                    "zero_power_test": "中子计数仪",
                }.get(self.dragging["key"], "启动工具")
            elif self.dragging.get("operation"):
                tool = RUN_OPERATION_TOOLS.get(self.dragging["key"], {})
                name = tool.get("name", "运行工具")
            else:
                name = ALL_MODULES.get(self.dragging["key"], ALL_MODULES["vessel"]).name
            text_rect = self.dragging["rect"].inflate(-6, -6)
            if self.dragging.get("commissioning") or self.dragging.get("critical") or self.dragging.get("operation"):
                text_rect = pygame.Rect(self.dragging["rect"].x + 40, self.dragging["rect"].y + 5,
                                        max(40, self.dragging["rect"].width - 46), self.dragging["rect"].height - 10)
            write_fit(self.screen, name, 12, BLACK, text_rect,
                      align="center", min_size=9)

    def draw_device_status_light(self, key: str, rect: pygame.Rect, installed: bool = True):
        """设备角标状态灯：绿=正常，黄=预警，红=故障，灰=未安装。"""
        important = {
            "vessel", "core", "crdm", "steam_gen", "primary_pump", "turbine", "generator",
            "condenser", "secondary_pump", "cooling", "tertiary_pump", "diesel_a", "diesel_b",
            "spray", "efw", "bio_shield", "area_monitor", "dosimetry", "effluent_monitor",
        }
        if key not in important and installed:
            return
        color = (150, 160, 166)
        if installed:
            color = GOOD
            event_key = self.fault.key if self.fault else (self.warning_event["key"] if self.warning_event else None)
            event_devices = {
                "vacuum": {"condenser", "cooling", "tertiary_pump"},
                "water": {"steam_gen", "secondary_pump", "efw"},
                "power": {"generator", "diesel_a", "diesel_b"},
            }.get(event_key, set())
            if key in event_devices:
                color = DANGER if self.fault else WARNING
            elif key in getattr(self, "equipment_health", {}) and self.equipment_health.get(key, 100) < 72:
                color = DANGER
            elif key in getattr(self, "equipment_health", {}) and self.equipment_health.get(key, 100) < 88:
                color = WARNING
        cx, cy = rect.right - 8, rect.y + 8
        pygame.draw.circle(self.screen, WHITE, (cx, cy), 7)
        pygame.draw.circle(self.screen, color, (cx, cy), 5)

    def draw_commissioning_targets(self):
        if self.stage != 2:
            return
        key = getattr(self, "selected_quiz", None)
        if not key or self.commissioning_task_done(key):
            return
        target = self.commissioning_target_rect(key)
        ready = getattr(self, "commissioning_tool_ready", {}).get(key, False)
        color = GOOD if ready else WARNING
        blink = int(pygame.time.get_ticks() / 260) % 2 == 0
        box = target.inflate(18, 18)
        rounded(self.screen, box, (234, 249, 240) if ready else (255, 248, 232), color, 3 if blink else 2, 10)
        label = "工具已就位" if ready else "拖拽调试工具到这里"
        label_rect = pygame.Rect(box.x, max(151, box.y - 32), max(184, box.width), 28)
        rounded(self.screen, label_rect, WHITE, color, 1, 6)
        icon_rect = pygame.Rect(label_rect.x + 6, label_rect.y + 4, 20, 20)
        self.draw_tool_icon(key, icon_rect, color, fill=(245, 249, 250))
        write_fit(self.screen, label, 11, color, pygame.Rect(label_rect.x + 31, label_rect.y + 3, label_rect.width - 37, label_rect.height - 6), align="center", min_size=9)

    def draw_critical_targets(self):
        if self.stage != 3:
            return
        key = getattr(self, "selected_critical", None)
        if not key or self.critical_task_done(key):
            return
        target = self.critical_target_rect(key)
        ready = getattr(self, "critical_tool_ready", {}).get(key, False)
        color = GOOD if ready else WARNING
        blink = int(pygame.time.get_ticks() / 260) % 2 == 0
        box = target.inflate(20, 20)
        rounded(self.screen, box, (234, 249, 240) if ready else (255, 248, 232), color, 3 if blink else 2, 10)
        label = "启动工具已就位" if ready else "拖拽启动工具到这里"
        label_rect = pygame.Rect(box.x, max(151, box.y - 32), max(184, box.width), 28)
        rounded(self.screen, label_rect, WHITE, color, 1, 6)
        icon_rect = pygame.Rect(label_rect.x + 6, label_rect.y + 4, 20, 20)
        self.draw_tool_icon(key, icon_rect, color, fill=(245, 249, 250))
        write_fit(self.screen, label, 11, color, pygame.Rect(label_rect.x + 31, label_rect.y + 3, label_rect.width - 37, label_rect.height - 6), align="center", min_size=9)

    def draw_pipes(self):
        if self.stage < 1:
            return
        for required, color, points, label, style in PIPES:
            complete = all(k in self.placed for k in required)
            pipe_color = color if complete else (207, 216, 220)
            pygame.draw.lines(self.screen, pipe_color, False, points, 5 if complete else 3)
            if complete:
                mid = max(0, len(points) // 2 - 1)
                self.arrow(points[mid], points[mid + 1], color, 3)
                if self.stage == 4 and not self.scrammed and style != "shaft":
                    particles = 4 if style == "steam" else 3
                    for i in range(particles):
                        point = self.poly_point(points, self.anim + i * 42)
                        radius = 5 if style == "steam" else 4
                        pcolor = WHITE if style == "steam" else color
                        pygame.draw.circle(self.screen, pcolor, point, radius)
                        if style == "steam":
                            pygame.draw.circle(self.screen, (176, 194, 202), point, radius, 1)
            else:
                if any(k in self.placed for k in required):
                    px, py = points[len(points) // 2]
                    pygame.draw.line(self.screen, DANGER, (px - 12, py - 8), (px + 12, py + 8), 3)
                    pygame.draw.line(self.screen, DANGER, (px - 12, py + 8), (px + 12, py - 8), 3)
            if self.stage == 4 and complete and label in ("一回路热段", "二回路给水", "冷却水回水"):
                write(self.screen, label, F12, color, (points[0][0] + 5, points[0][1] - 19))

    def draw_tutorial_hint(self):
        guide = self.current_instruction()
        rect = pygame.Rect(272, 684, 854, 64)
        rounded(self.screen, rect, (239, 247, 252), (196, 218, 228), 1, 7)
        rounded(self.screen, pygame.Rect(rect.x + 10, rect.y + 12, 82, 32), BLUE, BLUE, 1, 6)
        write_fit(self.screen, "下一步", 12, WHITE,
                  pygame.Rect(rect.x + 16, rect.y + 17, 70, 22), align="center", min_size=9)
        write_fit(self.screen, guide["title"], 16, BLUE,
                  pygame.Rect(rect.x + 108, rect.y + 8, rect.width - 126, 22), bold=True, min_size=12)
        write_wrapped(self.screen, guide["detail"], 12, TEXT_MUTED,
                  pygame.Rect(rect.x + 108, rect.y + 32, rect.width - 126, 30), min_size=10, max_lines=2, line_gap=16)
        # 阶段教程弹窗已取消；这里不再放按钮，避免误导玩家。
        self.tip_next_button = pygame.Rect(0, 0, 0, 0)

    def draw_bottom(self):
        # 底部改为“浮动抽屉式控制台”：默认只保留当前反馈 + 关键按钮。
        rounded(self.screen, BOTTOM, WHITE, BORDER, 2, 9)
        self.variant_buttons = {}
        # 返回/验收按钮放到底部同一排，避免覆盖调试/启动阶段的选项按钮。
        self.reset_button = pygame.Rect(892, 856, 110, 24)
        self.stage_button = pygame.Rect(1014, 856, 110, 24)
        self.report_button = pygame.Rect(1014, 856, 110, 24)

        drawer_label = pygame.Rect(270, 770, 102, 28)
        rounded(self.screen, drawer_label, (239, 247, 252), BLUE, 1, 7)
        write_fit(self.screen, "控制台", 14, BLUE, drawer_label.inflate(-8, -4), align="center", bold=True, min_size=10)

        # 当前反馈独立成一句话，不再堆“安全评分/消息/影响”等多行信息。
        feedback = pygame.Rect(384, 770, 520, 28)
        rounded(self.screen, feedback, (247, 250, 251), BORDER, 1, 7)
        feedback_text = str(self.message)
        if len(feedback_text) > 34:
            feedback_text = feedback_text.split("。")[0].strip()
            if len(feedback_text) > 34:
                feedback_text = "详见左侧操作区和右侧状态面板"
        write_fit(self.screen, "反馈：" + feedback_text, 11, self.message_color,
                  feedback.inflate(-10, -4), min_size=9)

        # 核心操作按钮始终醒目，其余细节进入右侧 Tab 或设置页。
        rounded(self.screen, self.reset_button, WHITE, DANGER, 2, 7)
        write_fit(self.screen, "返回节点", 13, DANGER, self.reset_button.inflate(-8, -4),
                  align="center", min_size=12)
        if self.stage < 4:
            rounded(self.screen, self.stage_button, BLUE, BLUE, 2, 7)
            labels = ["土建验收", "设备验收", "调试验收", "申请并网"]
            write_fit(self.screen, labels[self.stage], 13, WHITE, self.stage_button.inflate(-8, -4),
                      align="center", min_size=12)
        else:
            reached_goal = self.mission_complete() or self.calculate_total_score() >= 100
            button_color = ORANGE if reached_goal else GREEN
            rounded(self.screen, self.report_button, button_color, button_color, 2, 7)
            write_fit(self.screen, "结束挑战", 13, WHITE, self.report_button.inflate(-8, -4),
                      align="center", min_size=12)

        variant_key = self.selected if self.selected in EQUIPMENT_VARIANTS and self.selected not in self.placed else None

        # 底部二级安装按钮已删除，避免占用空间。

        if self.stage == 1:
            # 主泵保障方案只在设备安装阶段出现，是二级操作，不再挤在首行核心反馈区。
            write_fit(self.screen, "主泵保障方案", 11, TEXT_MUTED, pygame.Rect(270, 812, 78, 22), min_size=8)
            for name, rect in self.primary_choice_buttons.items():
                compact = pygame.Rect(rect.x, 812, 82, 28)
                active = name == self.pump_choice
                fill = BLUE if active else WHITE
                rounded(self.screen, compact, fill, BLUE, 1, 6)
                write_fit(self.screen, name, 11, WHITE if active else BLUE, compact.inflate(-6, -4),
                          align="center", min_size=8)
                self.primary_choice_buttons[name] = compact

            if variant_key:
                write_fit(self.screen, f"{ALL_MODULES[variant_key].name}品质", 11, TEXT_MUTED,
                          pygame.Rect(620, 812, 92, 22), min_size=8)
                x0 = 712
                for v_key, meta in EQUIPMENT_VARIANTS[variant_key].items():
                    rect = pygame.Rect(x0, 812, 78, 28)
                    self.variant_buttons[(variant_key, v_key)] = rect
                    active = self.equipment_variants.get(variant_key) == v_key
                    rounded(self.screen, rect, BLUE if active else WHITE, BLUE, 1, 6)
                    write_fit(self.screen, meta["name"], 9, WHITE if active else BLUE,
                              rect.inflate(-4, -3), align="center", min_size=7)
                    x0 += 82

        elif self.stage == 2:
            self.draw_quiz_console()
        elif self.stage == 3:
            self.draw_critical_console()
        elif self.stage == 4:
            write_fit(self.screen, f"输出 {self.output_mw:.0f} MWe｜运行 {self.runtime:.1f}s", 14, BLUE,
                      pygame.Rect(270, 812, 300, 30), min_size=11)

        # 最后一行只在有选择影响时短暂显示，避免常驻占屏。
        active = pygame.time.get_ticks() < getattr(self, "choice_effect_until", 0)
        if active:
            effect_rect = pygame.Rect(384, 846, 488, 28)
            rounded(self.screen, effect_rect, (255, 249, 235), WARNING, 1, 7)
            lines = getattr(self, "choice_effect_lines", []) or [getattr(self, "last_choice_effect", "暂无选择影响。")]
            effect_text = "；".join(str(x) for x in lines[:2])
            write_fit(self.screen, "影响：" + effect_text, 10, BLACK, effect_rect.inflate(-10, -4), min_size=8)


    def ordered_choice_options(self, cache_key: str, options):
        """返回稳定随机顺序的选项，避免正确答案永远出现在同一侧。"""
        options = list(options)
        if len(options) <= 1:
            return options
        cache = getattr(self, "choice_order_cache", None)
        if not isinstance(cache, dict):
            cache = {}
            self.choice_order_cache = cache
        signature = tuple((str(title), bool(correct)) for title, correct in options)
        item = cache.get(cache_key)
        if not item or item.get("signature") != signature:
            order = list(range(len(options)))
            if len(order) == 2:
                # 二选一题按任务键交错左右位置，保证不同任务的正确项不会固定在同一侧。
                reverse = (sum(ord(ch) for ch in cache_key) % 2) == 1
                order = [1, 0] if reverse else [0, 1]
            else:
                random.shuffle(order)
            cache[cache_key] = {"signature": signature, "order": order}
        order = cache[cache_key]["order"]
        return [options[i] for i in order if i < len(options)]

    def choice_button_style(self, correct: bool):
        """选项颜色按评审意见统一：正确项黄色，错误项蓝色。"""
        return WARNING if correct else BLUE

    def draw_quiz_console(self):
        self.quiz_option_rects = []
        self.commissioning_tool_rects = {}
        selected_quiz = getattr(self, "selected_quiz", None)
        labels = {
            "flush": "管路冲洗",
            "seal": "密封性试验",
            "diesel_a_test": "A列电源试验",
            "diesel_b_test": "B列电源试验",
        }
        tools = {
            "flush": "冲洗泵车",
            "seal": "压力试验仪",
            "diesel_a_test": "A列试验电缆",
            "diesel_b_test": "B列试验电缆",
        }
        write_fit(self.screen, "调试控制台｜轻操作链", 12, TEXT_MUTED,
                  pygame.Rect(270, 792, 250, 24), min_size=10)
        if not selected_quiz:
            write_fit(self.screen, "先点击左侧标为“当前”的任务。", 14, BLUE,
                      pygame.Rect(270, 824, 440, 30), min_size=11)
            return
        ready = getattr(self, "commissioning_tool_ready", {}).get(selected_quiz, False)
        title = labels.get(selected_quiz, "调试任务")
        tool_name = tools.get(selected_quiz, "调试工具")
        write_fit(self.screen, title, 14, BLACK, pygame.Rect(270, 820, 125, 26), bold=True, min_size=11)
        tool_rect = pygame.Rect(405, 816, 150, 36)
        self.commissioning_tool_rects[selected_quiz] = tool_rect
        rounded(self.screen, tool_rect, (234, 249, 240) if ready else WHITE, GOOD if ready else BLUE, 1, 7)
        icon_rect = pygame.Rect(tool_rect.x + 6, tool_rect.y + 5, 26, 26)
        self.draw_tool_icon(selected_quiz, icon_rect, GOOD if ready else BLUE, fill=(245, 249, 250))
        write_fit(self.screen, ("已就位：" if ready else "拖拽：") + tool_name, 11, GOOD if ready else BLUE,
                  pygame.Rect(tool_rect.x + 36, tool_rect.y + 4, tool_rect.width - 42, tool_rect.height - 8), align="center", min_size=8)
        if not ready:
            write_fit(self.screen, "拖到中央高亮目标后再确认。", 12, TEXT_MUTED,
                      pygame.Rect(570, 821, 280, 24), min_size=9)
            return
        if selected_quiz == "flush":
            question = "冲洗方向"
            options = [("反应堆 → 蒸汽发生器", True), ("冷凝器 → 堆芯", False)]
        elif selected_quiz == "seal":
            question = "试验结果"
            options = [("压力稳定，泄漏率合格", True), ("压力快速下降仍通过", False)]
        else:
            question = "等待自动确认"
            options = []
        write_fit(self.screen, question + "：", 12, BLACK, pygame.Rect(570, 820, 110, 26), min_size=10)
        x = 680
        for title, correct in self.ordered_choice_options("quiz:" + str(selected_quiz), options):
            rect = pygame.Rect(x, 816, 198, 36)
            color = self.choice_button_style(correct)
            rounded(self.screen, rect, WHITE, color, 1, 7)
            write_fit(self.screen, title, 12, color, rect.inflate(-10, -5), align="center", min_size=9)
            self.quiz_option_rects.append((rect.inflate(8, 8), selected_quiz, correct))
            x += rect.width + 12

    def draw_critical_console(self):
        selected = getattr(self, "selected_critical", None)
        self.critical_option_rects = []
        if not selected:
            write_fit(self.screen, "装料与临界：左侧选择当前步骤，再拖拽工具到中央目标区。", 13, BLUE,
                      pygame.Rect(270, 812, 620, 30), min_size=10)
            return
        ready = getattr(self, "critical_tool_ready", {}).get(selected, False)
        label = CRITICAL_LABELS.get(selected, "当前步骤")
        if not ready:
            write_fit(self.screen, label + "：", 13, BLACK,
                      pygame.Rect(270, 812, 122, 30), min_size=10)
            tool_rect = pygame.Rect(398, 806, 170, 42)
            self.critical_tool_rects[selected] = tool_rect
            rounded(self.screen, tool_rect, WHITE, BLUE, 1, 7)
            self.draw_tool_icon(selected, pygame.Rect(tool_rect.x + 7, tool_rect.y + 6, 30, 30), BLUE, fill=(245, 249, 250))
            write_fit(self.screen, "拖拽：" + CRITICAL_TOOL_NAMES[selected], 11, BLUE,
                      pygame.Rect(tool_rect.x + 42, tool_rect.y + 7, tool_rect.width - 50, 28), align="center", min_size=8)
            write_fit(self.screen, "到中央高亮区", 12, TEXT_MUTED,
                      pygame.Rect(580, 812, 180, 30), min_size=9)
            return
        write_fit(self.screen, label + "：选择正确操作", 12, BLACK,
                  pygame.Rect(270, 800, 190, 24), min_size=10)
        x = 470
        for title, correct in self.ordered_choice_options("critical:" + str(selected), CRITICAL_OPTIONS[selected]):
            rect = pygame.Rect(x, 794, 188, 42)
            color = self.choice_button_style(correct)
            rounded(self.screen, rect, WHITE, color, 1, 7)
            write_fit(self.screen, title, 12, color,
                      rect.inflate(-10, -5), align="center", min_size=9)
            self.critical_option_rects.append((rect.inflate(8, 8), selected, correct))
            x += rect.width + 14

    def parameter_color(self, value, low, high):
        if value < low or value > high:
            blink = int(pygame.time.get_ticks() / 300) % 2 == 0
            return DANGER if blink else WARNING
        return GOOD

    def draw_right(self):
        rounded(self.screen, RIGHT, WHITE, BORDER, 2, 9)
        panel_x = RIGHT.x + 20
        panel_w = RIGHT.width - 40
        write_fit(self.screen, "监视与学习面板", 20, BLACK, pygame.Rect(panel_x, 86, panel_w, 31),
                  bold=True, min_size=14)
        pygame.draw.line(self.screen, GRID, (panel_x, 126), (RIGHT.right - 20, 126), 1)

        if self.stage == 4:
            self.draw_runtime_dashboard()
        else:
            # 默认只显示经营状态、当前事件和必要提示。
            # 系统流程、奖励、知识卡等移入二级 Tab，不再常驻占屏。
            self.draw_stage_checklist()

    def draw_runtime_dashboard(self):
        labels = self.visible_dashboard_pages()
        self.dashboard_buttons = {}
        label_items = list(labels.items())
        tab_y = 136
        tab_h = UI_TAB_HEIGHT
        if self.is_starter_mode():
            self.dashboard_buttons["status"] = pygame.Rect(1330, tab_y, 112, tab_h)
        else:
            start_x = 1175
            total_w = 268
            gap = 6
            bw = max(42, int((total_w - gap * (len(label_items) - 1)) / max(1, len(label_items))))
            for idx, (key, _label) in enumerate(label_items):
                self.dashboard_buttons[key] = pygame.Rect(start_x + idx * (bw + gap), tab_y, bw, tab_h)
        hard_event = self.fault or self.dose_task or (self.warning_event and self.diagnosis_resolved)
        if self.dashboard_page not in labels:
            self.dashboard_page = "status"
        for key, rect in self.dashboard_buttons.items():
            active = self.dashboard_page == key
            disabled = key != "status" and hard_event
            fill = BLUE if active else WHITE
            border = BORDER if disabled else BLUE
            rounded(self.screen, rect, fill, border, 1, UI_PILL_RADIUS)
            write_fit(self.screen, labels[key], 12, WHITE if active else TEXT_MUTED if disabled else BLUE,
                      rect.inflate(-6, -4), align="center", min_size=10)
        if hard_event:
            self.dashboard_page = "status"
        if self.dashboard_page == "trend" and not self.is_starter_mode():
            self.draw_runtime_trends()
        elif self.dashboard_page == "barrier" and not self.is_starter_mode():
            self.draw_barrier_dashboard()
        elif self.dashboard_page == "maintenance" and not self.is_starter_mode():
            self.draw_maintenance_dashboard()
        elif self.dashboard_page == "atlas" and not self.is_starter_mode():
            self.draw_accident_atlas_dashboard()
        elif self.dashboard_page == "log" and not self.is_starter_mode():
            self.draw_operation_log_dashboard()
        else:
            self.draw_runtime_status()

    def draw_maintenance_dashboard(self):
        """右侧维护页：统一卡片字号、边距与节距。"""
        x, w = 1175, 268
        write(self.screen, "维护与系统升级", F16, BLACK, (x, 173))
        write_fit(self.screen, "核心系统优先显示，完整效果在结算复盘展开。", 11, TEXT_MUTED,
                  pygame.Rect(x, 201, w, 24), min_size=9)

        weak_key, weak_value = self.weakest_equipment()
        weak = HEALTH_META[weak_key]
        summary = pygame.Rect(x, 236, w, 92)
        rounded(self.screen, summary, (247, 250, 251), WARNING if weak_value < 90 else GRID, 1, UI_CARD_RADIUS)
        write_fit(self.screen, "最低健康度设备", 12, TEXT_MUTED,
                  pygame.Rect(summary.x + UI_CARD_PAD, summary.y + 14, 128, 20), min_size=10)
        write_fit(self.screen, f"{weak_value:.0f}%", 24, WARNING if weak_value < 90 else GOOD,
                  pygame.Rect(summary.right - 100, summary.y + 10, 82, 30), align="right", bold=True, min_size=18)
        write_fit(self.screen, weak["name"], 14, BLACK,
                  pygame.Rect(summary.x + UI_CARD_PAD, summary.y + 48, summary.width - 32, 22), min_size=12)

        y = summary.bottom + UI_SECTION_GAP
        write_fit(self.screen, "常用升级", 14, BLACK, pygame.Rect(x, y, w, 24), bold=True, min_size=11)
        y += 30
        self.upgrade_buttons = {}
        for key in ["asg", "ris", "eas"]:
            if key not in self.upgrades:
                continue
            up = self.upgrades[key]
            rect = pygame.Rect(x, y, w, 88)
            self.upgrade_buttons[key] = rect
            complete = up.level >= 1
            rounded(self.screen, rect, (234, 249, 240) if complete else (248, 250, 251),
                    GOOD if complete else BLUE, 1, UI_CARD_RADIUS)
            state = "完成" if complete else f"{up.remaining:.1f}s" if up.in_progress else f"{up.cost} 币"
            write_fit(self.screen, up.name, 14, BLACK,
                      pygame.Rect(rect.x + UI_CARD_PAD, rect.y + 14, 150, 24), bold=True, min_size=12)
            write_fit(self.screen, state, 13, GOOD if complete else WARNING if up.in_progress else BLUE,
                      pygame.Rect(rect.right - 100, rect.y + 14, 84, 24), align="right", min_size=11)
            write_fit(self.screen, "点击升级", 11, TEXT_MUTED,
                      pygame.Rect(rect.x + UI_CARD_PAD, rect.y + 52, rect.width - 32, 18), min_size=9)
            y += 88 + UI_SECTION_GAP

        note = pygame.Rect(x, 698, w, 40)
        rounded(self.screen, note, (255, 249, 235), WARNING, 1, 8)
        write_fit(self.screen, "EDG / KRT / ETY 在结算和事故复盘中展示。", 10, WARNING,
                  note.inflate(-12, -6), min_size=8)

    def draw_barrier_dashboard(self):
        x, w = 1175, 268
        write(self.screen, "三道屏障 + 监测防线", F16, BLACK, (x, 173))
        write_fit(self.screen, f"综合完整性：{self.defense_score()} / 100", 14,
                  GOOD if self.defense_score() >= 85 else WARNING if self.defense_score() >= 65 else DANGER,
                  pygame.Rect(x, 199, w, 24), min_size=11)
        y = 240
        for key, (label, color) in BARRIER_META.items():
            value = self.barriers.get(key, 100)
            card = pygame.Rect(x, y, w, 52)
            rounded(self.screen, card, (247, 250, 251), BORDER, 1, 8)
            write_fit(self.screen, label, 12, TEXT_MUTED, pygame.Rect(card.x + 14, card.y + 10, 150, 18), min_size=10)
            write_fit(self.screen, f"{value:.0f}%", 13, color if value >= 70 else DANGER,
                      pygame.Rect(card.right - 70, card.y + 8, 56, 20), align="right", min_size=11)
            bar = pygame.Rect(card.x + 14, card.y + 31, card.width - 28, 8)
            pygame.draw.rect(self.screen, GRID, bar, border_radius=4)
            pygame.draw.rect(self.screen, color if value >= 70 else DANGER,
                             (bar.x, bar.y, int(bar.width * value / 100), bar.height), border_radius=4)
            y += 62
        log_box = pygame.Rect(x, 500, w, 232)
        rounded(self.screen, log_box, (247, 250, 251), BORDER, 1, UI_CARD_RADIUS)
        write(self.screen, "最近安全记录", F14, BLACK, (log_box.x + 14, log_box.y + 14))
        events = self.event_log[-3:] if self.event_log else []
        if not events:
            write(self.screen, "尚无运行事件。", F12, TEXT_MUTED, (log_box.x + 14, log_box.y + 48))
        else:
            yy = log_box.y + 48
            event_font = get_font(11)
            for entry in reversed(events):
                text = f"{entry.get('time', 0):>4.1f}s  {entry.get('text', '')}"
                write_wrapped(self.screen, text, 11, TEXT_MUTED,
                              pygame.Rect(log_box.x + 14, yy, log_box.width - 28, 24), min_size=11, max_lines=1)
                yy += 30
        pygame.draw.line(self.screen, GRID, (log_box.x + 14, log_box.y + 152), (log_box.right - 14, log_box.y + 152), 1)
        write_wrapped(self.screen, "屏障评分展示纵深防御状态；异常后优先维持多重屏障有效。",
                      11, BLUE, pygame.Rect(log_box.x + 14, log_box.y + 164, log_box.width - 28, 54), min_size=10, max_lines=3, line_gap=12)

    def draw_runtime_trends(self):
        x, w = 1175, 268
        write_wrapped(self.screen, "趋势图只用于观察变化方向；发生报警时，请切回“状态”查看操作指引。",
                      11, TEXT_MUTED, pygame.Rect(x, 166, w, 36), min_size=9, max_lines=2)
        self.draw_trend_chart(pygame.Rect(x, 216, w, 128), "一回路平均温度趋势",
                              self.history.get("temp", []), RED, "℃")
        self.draw_trend_chart(pygame.Rect(x, 360, w, 128), "一回路压力趋势",
                              self.history.get("pressure", []), ORANGE, "MPa")
        self.draw_trend_chart(pygame.Rect(x, 504, w, 128), "输出功率趋势",
                              self.history.get("power", []), BLUE, "MWe")
        mission = MISSION_TYPES[self.mission_key]
        box = pygame.Rect(x, 650, w, 82)
        rounded(self.screen, box, (245, 249, 251), BORDER, 1, UI_CARD_RADIUS)
        write(self.screen, "目标进度", F13, BLACK, (box.x + 12, box.y + 12))
        write_fit(self.screen, mission["goal"], 11, TEXT_MUTED,
                  pygame.Rect(box.x + 12, box.y + 36, box.width - 24, 18), min_size=9)
        status = "已达成目标" if self.mission_complete() else "继续稳定运行以达成目标"
        write_fit(self.screen, status, 12, GOOD if self.mission_complete() else WARNING,
                  pygame.Rect(box.x + 12, box.y + 57, box.width - 24, 18), min_size=9)

    def draw_accident_card(self, x: int, y: int, w: int) -> int:
        """主界面事故卡：只显示第一层信息，完整资料放入详情弹窗。"""
        if not (self.warning_event or self.fault or self.dose_task):
            return y
        title, phenomenon, action = self.compact_event_summary()
        case = getattr(self, "active_reference_accident", None) or getattr(self, "last_reference_accident", None)
        cooling_case = bool(self.warning_event and self.warning_event.get("key") == "vacuum" and getattr(self, "diagnosis_resolved", False))
        card = pygame.Rect(x, y, w, 248)
        color = DANGER if self.fault or self.dose_task else WARNING
        rounded(self.screen, card, (255, 245, 242), color, 2, 12)
        label = "当前事件"
        if case and isinstance(case.get("id"), int):
            label = f"事故 {case['id']:02d}/20"
        write_fit(self.screen, label, 13, color, pygame.Rect(card.x + 18, card.y + 14, 110, 24), bold=True, min_size=11)
        write_wrapped(self.screen, title, 17, BLACK, pygame.Rect(card.x + 18, card.y + 46, card.width - 36, 42), min_size=13, max_lines=2, line_gap=18)
        write_fit(self.screen, "现象", 12, TEXT_MUTED, pygame.Rect(card.x + 18, card.y + 98, 44, 22), min_size=10)
        write_wrapped(self.screen, phenomenon, 12, BLACK, pygame.Rect(card.x + 72, card.y + 100, card.width - 90, 36), min_size=10, max_lines=2, line_gap=16)
        write_fit(self.screen, "建议", 12, TEXT_MUTED, pygame.Rect(card.x + 18, card.y + 146, 44, 22), min_size=10)
        write_wrapped(self.screen, action, 12, BLUE, pygame.Rect(card.x + 72, card.y + 148, card.width - 90, 34), min_size=10, max_lines=2, line_gap=16)
        if cooling_case:
            # 真空恶化场景下，玩家要立刻拖动冷却水滑块；此时隐藏详情按钮，避免和滑块区域打架。
            self.detail_button = pygame.Rect(0, 0, 0, 0)
            return card.bottom + 18
        self.detail_button = pygame.Rect(card.x + 18, card.bottom - 40, card.width - 36, 28)
        rounded(self.screen, self.detail_button, BLUE, BLUE, 1, 7)
        write_fit(self.screen, "查看事故详情", 13, WHITE, self.detail_button.inflate(-8, -4), align="center", bold=True, min_size=10)
        return card.bottom + 20

    def draw_detail_modal(self):
        """二级详情弹窗：事故树、处置依据、系统说明集中在这里显示。"""
        mode = getattr(self, "detail_modal", None)
        if not mode:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 24, 30, 145))
        self.screen.blit(overlay, (0, 0))
        box = pygame.Rect(282, 82, 936, 716)
        self.detail_modal_rect = box
        rounded(self.screen, box, WHITE, BLUE, 3, 16)
        self.detail_close_button = pygame.Rect(box.right - 118, box.y + 24, 86, 34)
        rounded(self.screen, self.detail_close_button, WHITE, BLUE, 1, 8)
        write_fit(self.screen, "关闭", 14, BLUE, self.detail_close_button.inflate(-8, -4), align="center", min_size=11)
        write_fit(self.screen, "事故与系统详情", 27, BLACK, pygame.Rect(box.x + 34, box.y + 26, 360, 36), bold=True, min_size=20)
        write_fit(self.screen, "主界面只保留目标、事件、操作和风险；完整依据在这里展开。", 13, TEXT_MUTED,
                  pygame.Rect(box.x + 34, box.y + 68, box.width - 68, 24), min_size=10)
        case = getattr(self, "active_reference_accident", None) or getattr(self, "last_reference_accident", None)
        if not case:
            title, phenomenon, action = self.compact_event_summary()
            case = {"id": None, "name": title, "phenomenon": phenomenon, "category": "运行事件", "measures": [action], "wrong": "延误处置会扩大资金、安全或剂量损失。"}
        y = box.y + 112
        left = pygame.Rect(box.x + 34, y, 420, 520)
        right = pygame.Rect(box.x + 486, y, 386, 520)
        rounded(self.screen, left, (247, 250, 251), GRID, 1, 12)
        rounded(self.screen, right, (247, 250, 251), GRID, 1, 12)
        case_title = (f"事故 {case.get('id'):02d}/20｜" if isinstance(case.get('id'), int) else "") + case.get("name", "运行事件")
        write_wrapped(self.screen, case_title, 20, BLUE, pygame.Rect(left.x + 22, left.y + 20, left.width - 44, 58), min_size=15, max_lines=2, line_gap=24)
        write_fit(self.screen, "资料分类", 12, TEXT_MUTED, pygame.Rect(left.x + 22, left.y + 92, 90, 22), min_size=10)
        write_fit(self.screen, case.get("category", "运行事件"), 13, BLACK, pygame.Rect(left.x + 110, left.y + 92, 280, 22), min_size=10)
        write_fit(self.screen, "现象", 13, BLACK, pygame.Rect(left.x + 22, left.y + 132, 90, 22), bold=True, min_size=11)
        write_wrapped(self.screen, case.get("phenomenon", "关键参数异常。"), 13, BLACK, pygame.Rect(left.x + 22, left.y + 162, left.width - 44, 78), min_size=11, max_lines=3, line_gap=20)
        write_fit(self.screen, "正确处置", 13, BLACK, pygame.Rect(left.x + 22, left.y + 260, 120, 22), bold=True, min_size=11)
        measures = format_measures(case, 3) if isinstance(case, dict) else "按操作提示操作。"
        write_wrapped(self.screen, measures, 13, BLUE, pygame.Rect(left.x + 22, left.y + 292, left.width - 44, 96), min_size=11, max_lines=4, line_gap=18)
        write_fit(self.screen, "错误后果", 13, BLACK, pygame.Rect(left.x + 22, left.y + 400, 120, 22), bold=True, min_size=11)
        write_wrapped(self.screen, case.get("wrong", "错误处置会造成安全评分下降、资金损失或倒计时缩短。"), 13, DANGER,
                      pygame.Rect(left.x + 22, left.y + 430, left.width - 44, 70), min_size=11, max_lines=3, line_gap=16)

        write_fit(self.screen, "事故演化树", 15, BLACK, pygame.Rect(right.x + 22, right.y + 22, 180, 28), bold=True, min_size=12)
        chain = chain_text(case.get("id")) if isinstance(case.get("id"), int) else "当前异常 → 参数恶化 → 处置窗口缩短 → 安全/资金损失"
        steps = chain.split(" → ") if chain else ["当前事故", "系统响应", "恢复稳定"]
        yy = right.y + 68
        for idx, step in enumerate(steps[:5], 1):
            pygame.draw.circle(self.screen, BLUE if idx == 1 else WARNING if idx < len(steps) else DANGER, (right.x + 36, yy + 11), 9)
            write_fit(self.screen, str(idx), 10, WHITE, pygame.Rect(right.x + 29, yy + 4, 14, 14), align="center", min_size=8)
            write_wrapped(self.screen, step, 13, BLACK, pygame.Rect(right.x + 58, yy, right.width - 82, 36), min_size=11, max_lines=2, line_gap=18)
            if idx < len(steps[:5]):
                pygame.draw.line(self.screen, GRID, (right.x + 36, yy + 24), (right.x + 36, yy + 45), 2)
            yy += 58
        write_fit(self.screen, "对应系统", 15, BLACK, pygame.Rect(right.x + 22, right.y + 370, 180, 28), bold=True, min_size=12)
        systems = [self.term_label(k) for k in ("edg", "asg", "ris", "eas", "krt", "ety")]
        write_wrapped(self.screen, "｜".join(systems[:4]) + "\n" + "｜".join(systems[4:]), 13, TEXT_MUTED,
                      pygame.Rect(right.x + 22, right.y + 408, right.width - 44, 58), min_size=10, max_lines=2, line_gap=20)
        write_fit(self.screen, "资料依据：CPR1000 系统与设备、事故表、辐射防护资料。", 11, TEXT_MUTED,
                  pygame.Rect(box.x + 34, box.bottom - 48, box.width - 68, 22), min_size=9)

    def accident_state_label(self, state: str):
        if state == "mastered":
            return "已掌握", GOOD
        if state == "review":
            return "待复盘", DANGER
        if state == "unlocked":
            return "已触发", BLUE
        return "尚未解锁", TEXT_MUTED

    def draw_accident_atlas_dashboard(self):
        """事故图鉴：一页只展示一个事故，避免 20 项图鉴在右侧面板中拥挤。"""
        write(self.screen, "事故图鉴", F16, BLACK, (1175, 173))
        gallery = getattr(self, "accident_gallery_state", {i: "locked" for i in range(1, 21)})
        mastered = sum(1 for i in range(1, 21) if gallery.get(i) == "mastered")
        unlocked = sum(1 for i in range(1, 21) if gallery.get(i) in ("unlocked", "review", "mastered"))
        write_fit(self.screen, f"已触发 {unlocked}/20 ｜ 已掌握 {mastered}/20", 12, BLUE,
                  pygame.Rect(1175, 201, 266, 26), min_size=10)
        max_page = (len(ACCIDENT_CASE_LIBRARY) - 1) // ACCIDENT_ATLAS_PAGE_SIZE
        page = int(getattr(self, "accident_atlas_page", 0))
        page = max(0, min(max_page, page))
        self.accident_atlas_page = page
        case = ACCIDENT_CASE_LIBRARY[page * ACCIDENT_ATLAS_PAGE_SIZE]
        state = gallery.get(case["id"], "locked")
        label, color = self.accident_state_label(state)

        rect = pygame.Rect(1175, 250, 268, 360)
        fill = (238, 244, 247) if state == "locked" else (242, 250, 247) if state == "mastered" else (255, 248, 235) if state == "review" else (247, 250, 251)
        rounded(self.screen, rect, fill, color, 2, 12)
        write_fit(self.screen, f"事故 {case['id']:02d}/20", 13, color,
                  pygame.Rect(rect.x + 18, rect.y + 18, 108, 28), bold=True, min_size=11)
        write_fit(self.screen, label, 13, color,
                  pygame.Rect(rect.right - 92, rect.y + 18, 74, 28), align="right", bold=True, min_size=11)

        name = case["name"] if state != "locked" else "尚未解锁"
        write_wrapped(self.screen, name, 18, BLACK if state != "locked" else TEXT_MUTED,
                      pygame.Rect(rect.x + 18, rect.y + 62, rect.width - 36, 64), min_size=14, max_lines=2, line_gap=20)

        if state == "locked":
            desc = "该事故还没有在本局触发。\n进入并网运行后，由事故链逐步解锁。"
            action = "解锁后显示处置要点。"
        elif state == "review":
            desc = "曾出现错误处置，建议在结算复盘中查看原因。"
            action = "正确处置：" + format_measures(case, 1)
        elif state == "mastered":
            desc = "已正确处置过，图鉴标记为已掌握。"
            action = "正确处置：" + format_measures(case, 1)
        else:
            desc = "已触发。完整事故现象与演化树已收录。"
            action = "正确处置：" + format_measures(case, 1)

        write_fit(self.screen, "状态说明", 12, TEXT_MUTED, pygame.Rect(rect.x + 18, rect.y + 152, 100, 24), min_size=10)
        write_wrapped(self.screen, desc, 12, BLACK if state != "locked" else TEXT_MUTED,
                      pygame.Rect(rect.x + 18, rect.y + 184, rect.width - 36, 72), min_size=10, max_lines=3, line_gap=18)
        write_fit(self.screen, "处置要点", 12, TEXT_MUTED, pygame.Rect(rect.x + 18, rect.y + 274, 100, 24), min_size=10)
        write_wrapped(self.screen, action, 12, BLUE if state != "locked" else TEXT_MUTED,
                      pygame.Rect(rect.x + 18, rect.y + 305, rect.width - 36, 34), min_size=10, max_lines=1, line_gap=18)

        chain = chain_text(case.get("id"))
        # 演化树入口保留在事故详情弹窗与结算复盘中，图鉴主卡不再额外提示，减少文字密度。

        self.accident_atlas_prev = pygame.Rect(1175, 695, 86, 36)
        self.accident_atlas_next = pygame.Rect(1357, 695, 86, 36)
        rounded(self.screen, self.accident_atlas_prev, WHITE if page > 0 else (238, 242, 245), BLUE if page > 0 else BORDER, 1, 7)
        rounded(self.screen, self.accident_atlas_next, WHITE if page < max_page else (238, 242, 245), BLUE if page < max_page else BORDER, 1, 7)
        write_fit(self.screen, "上一项", 12, BLUE if page > 0 else TEXT_MUTED, self.accident_atlas_prev.inflate(-5, -2), align="center", min_size=10)
        write_fit(self.screen, f"{page+1}/{max_page+1}", 14, TEXT_MUTED, pygame.Rect(1265, 702, 86, 22), align="center", min_size=12)
        write_fit(self.screen, "下一项", 12, BLUE if page < max_page else TEXT_MUTED, self.accident_atlas_next.inflate(-5, -2), align="center", min_size=10)

    def draw_operation_log_dashboard(self):
        """运行日志：只显示最近两条，避免日志列表堆满右侧。"""
        write(self.screen, "运行日志", F16, BLACK, (1175, 173))
        write_wrapped(self.screen, "仅显示最近 2 条；完整记录在结算复盘中查看。", 11, TEXT_MUTED,
                  pygame.Rect(1175, 198, 266, 42), min_size=9, max_lines=2, line_gap=14)
        events = getattr(self, "event_log", [])[-2:]
        y = 258
        if not events:
            rounded(self.screen, pygame.Rect(1175, y, 268, 110), (247, 250, 251), GRID, 1, 10)
            write_fit(self.screen, "尚无运行事件", 14, TEXT_MUTED,
                      pygame.Rect(1175, y + 36, 268, 28), align="center", min_size=12)
            return
        for entry in reversed(events):
            color = DANGER if entry.get("kind") in ("scram", "failure") else WARNING if entry.get("kind") in ("fault", "warning", "evolution") else BLUE if entry.get("kind") in ("upgrade", "dose") else TEXT_MUTED
            rect = pygame.Rect(1175, y, 268, 138)
            rounded(self.screen, rect, (247, 250, 251), color if color != TEXT_MUTED else GRID, 1, 10)
            write_fit(self.screen, f"{entry.get('time', 0):>5.1f}s", 13, color,
                      pygame.Rect(rect.x + 16, rect.y + 16, 72, 26), bold=True, min_size=11)
            write_wrapped(self.screen, entry.get("text", ""), 13, BLACK,
                          pygame.Rect(rect.x + 16, rect.y + 56, rect.width - 32, 58), min_size=11, max_lines=2, line_gap=18)
            y += 162
        # 日志页只显示最近事件，避免底部文字拥挤。

    def draw_runtime_overview(self, x: int, y: int, w: int) -> int:
        """右侧第一层信息：目标、事件、操作、风险。"""
        title, phenomenon, action = self.compact_event_summary()
        mission = MISSION_TYPES[self.mission_key]
        target = "已达成，准备结算" if self.mission_complete() else mission["name"]
        if self.dose_task:
            risk = "剂量任务倒计时"
        elif self.fault:
            risk = "故障升级 / 自动停堆"
        elif self.warning_event:
            risk = "黄色预警正在升级"
        elif self.collective_dose >= DOSE_ORANGE_LINE:
            risk = "剂量橙色警戒"
        elif self.equipment_average_health() < 82:
            risk = "设备健康度偏低"
        else:
            risk = "暂无突出风险"
        rows = [
            ("目标", target, BLUE),
            ("事件", title, DANGER if self.fault or self.dose_task else WARNING if self.warning_event else GOOD),
            ("操作", action, BLUE),
            ("风险", risk, DANGER if self.fault or self.dose_task else WARNING if self.warning_event or risk != "暂无突出风险" else GOOD),
        ]
        row_h = 46
        gap = 10
        box = pygame.Rect(x, y, w, 18 + len(rows) * row_h + (len(rows) - 1) * gap + 18)
        rounded(self.screen, box, (247, 250, 251), BORDER, 1, UI_CARD_RADIUS)
        yy = box.y + 18
        for label, value, color in rows:
            tag = pygame.Rect(box.x + 14, yy, 74, row_h)
            rounded(self.screen, tag, (239, 247, 252), color, 2, 8)
            write_fit(self.screen, label, 18, color, tag.inflate(-8, -6), align="center", bold=True, min_size=14)
            write_wrapped(self.screen, value, 13, BLACK if label != "风险" else color,
                          pygame.Rect(box.x + 102, yy + 4, box.width - 118, row_h - 8), min_size=10, max_lines=2, line_gap=14)
            yy += row_h + gap
        return box.bottom + UI_SECTION_GAP

    def draw_cooling_slider_widget(self, control_y: int, compact: bool = False):
        """冷却水滑块统一绘制与命中区刷新。"""
        box_h = 72 if compact else 80
        box = pygame.Rect(1175, control_y, 268, box_h)
        rounded(self.screen, box, (247, 250, 251), DEEP_BLUE, 1, UI_CARD_RADIUS)
        write_fit(self.screen, "冷却水流量", 13, BLACK, pygame.Rect(box.x + 14, box.y + 10, 120, 22),
                  bold=True, min_size=11)
        write_fit(self.screen, f"{self.cooling_flow:.0f}%", 14, DEEP_BLUE, pygame.Rect(box.right - 80, box.y + 10, 64, 22),
                  align="right", bold=True, min_size=11)
        self.cool_minus_button = pygame.Rect(box.x + 14, box.y + box_h - 34, 32, 26)
        self.cool_plus_button = pygame.Rect(box.right - 46, box.y + box_h - 34, 32, 26)
        rounded(self.screen, self.cool_minus_button, WHITE, DEEP_BLUE, 1, 6)
        rounded(self.screen, self.cool_plus_button, WHITE, DEEP_BLUE, 1, 6)
        write_fit(self.screen, "−", 15, DEEP_BLUE, self.cool_minus_button.inflate(-4, -2), align="center", min_size=11)
        write_fit(self.screen, "+", 15, DEEP_BLUE, self.cool_plus_button.inflate(-4, -2), align="center", min_size=11)
        self.cool_slider_active = True
        self.cool_slider = pygame.Rect(box.x + 58, box.y + box_h - 23, box.width - 116, 8)
        pygame.draw.rect(self.screen, GRID, self.cool_slider, border_radius=4)
        knob_x = self.cool_slider.x + int(self.cool_slider.width * (self.cooling_flow - 40) / 60)
        pygame.draw.rect(self.screen, DEEP_BLUE, (self.cool_slider.x, self.cool_slider.y,
                                                   knob_x - self.cool_slider.x, self.cool_slider.height), border_radius=4)
        pygame.draw.circle(self.screen, DEEP_BLUE, (knob_x, self.cool_slider.centery), 9)

    def draw_runtime_status(self):
        # 每帧先关闭冷却水滑块命中区；只有真正绘制滑块时再开启，防止隐藏滑块抢鼠标事件。
        self.cool_slider_active = False
        self.cool_slider = pygame.Rect(0, 0, 0, 0)
        self.cool_minus_button = pygame.Rect(0, 0, 0, 0)
        self.cool_plus_button = pygame.Rect(0, 0, 0, 0)
        alarms = self.alarms()
        y = 166
        y = self.draw_runtime_overview(1175, y, 268)
        # 事故链倒计时：黄色预警 -> 红色故障 -> 自动停堆，用大号数字制造压迫感。
        if self.warning_event or self.fault:
            left = self.fault_left if self.fault else self.warning_left
            total = self.fault.duration if self.fault else self.warning_duration()
            ratio = clamp(left / max(0.01, total), 0, 1)
            color = DANGER if self.fault or left <= 5 else WARNING
            box = pygame.Rect(1175, y, 268, 58)
            fill = (255, 241, 240) if color == DANGER else (255, 249, 235)
            rounded(self.screen, box, fill, color, 2, 8)
            write_fit(self.screen, "距离升级" if self.warning_event else "自动停堆倒计时", 12, color,
                      pygame.Rect(box.x + 12, box.y + 8, 120, 18), bold=True, min_size=9)
            write_fit(self.screen, f"{max(0, int(left + 0.99))}s", 29, color,
                      pygame.Rect(box.x + 140, box.y + 5, 112, 36), align="right", bold=True, min_size=20)
            bar = pygame.Rect(box.x + 12, box.bottom - 12, box.width - 24, 6)
            rounded(self.screen, bar, GRID, GRID, 1, 3)
            rounded(self.screen, pygame.Rect(bar.x, bar.y, int(bar.width * ratio), bar.height), color, color, 1, 3)
            y += 72
            # 倒计时最后 5 秒每秒提示一次，答辩/游玩时更明显。
            sec = int(left + 0.99)
            if 0 < sec <= 5 and getattr(self, "countdown_audio_second", None) != sec:
                self.countdown_audio_second = sec
                if hasattr(self, "audio"):
                    self.audio.play("countdown")

        if alarms:
            alarm, color = alarms[0]
            alarm_box = pygame.Rect(1175, y, 268, 42)
            rounded(self.screen, alarm_box, (255, 241, 240), color, 1, 6)
            write_wrapped(self.screen, "警报：" + alarm, 12, color, pygame.Rect(1185, y + 4, 248, 32), min_size=9, max_lines=2, line_gap=12)
        else:
            alarm_box = pygame.Rect(1175, y, 268, 42)
            rounded(self.screen, alarm_box, (234, 249, 240), GOOD, 1, 6)
            write_wrapped(self.screen, "参数稳定，安全联锁正常", 12, GOOD,
                          pygame.Rect(1185, y + 4, 246, 30), min_size=9, max_lines=2, line_gap=12)

        y += 55
        active_card = bool(self.warning_event or self.fault or self.dose_task)
        y = self.draw_accident_card(1175, y, 268)
        if active_card:
            # 事故处置页不显示大参数表。冷凝器真空预警除外：玩家必须能拖动冷却水滑块。
            if self.warning_event and self.warning_event.get("key") == "vacuum" and getattr(self, "diagnosis_resolved", False):
                self.draw_cooling_slider_widget(min(max(y + 10, 674), 700), compact=True)
            return

        self.draw_cooling_slider_widget(y + 4)
        y += 92

        write(self.screen, "核心监控", F15, BLACK, (1175, y))
        y += 30
        core_items = ["堆芯核功率", "一回路平均温度", "冷凝器绝对压力", "个人剂量"]
        self.parameter_tooltip_regions = {}
        mouse_pos = pygame.mouse.get_pos()
        hovered_parameter = None
        for i, name in enumerate(core_items):
            value, unit, low, high = self.parameters[name]
            color = self.parameter_color(value, low, high)
            card = pygame.Rect(1175, y + i * 66, 268, 56)
            self.parameter_tooltip_regions[name] = card
            flash = getattr(self, "param_flash", {}).get(name) if isinstance(getattr(self, "param_flash", {}), dict) else None
            flashing = bool(flash and pygame.time.get_ticks() < flash.get("until", 0))
            fill = (255, 249, 235) if flashing else (247, 250, 251)
            border = flash.get("color", color) if flashing else color
            rounded(self.screen, card, fill, border, 3 if flashing else 1, 9)
            write_fit(self.screen, name, 11, TEXT_MUTED,
                      pygame.Rect(card.x + 14, card.y + 7, 150, 20), min_size=9)
            write_fit(self.screen, f"{value:.1f}", 20 if flashing else 19, border if flashing else color,
                      pygame.Rect(card.x + 14, card.y + 28, 108, 24), bold=True, min_size=16)
            write_fit(self.screen, unit, 11, TEXT_MUTED,
                      pygame.Rect(card.right - 76, card.y + 31, 58, 18), align="right", min_size=9)
            if card.collidepoint(mouse_pos) and name in PARAMETER_EXPLANATIONS:
                hovered_parameter = name
        self._runtime_param_hover = (hovered_parameter, mouse_pos) if hovered_parameter else None
        y += len(core_items) * 66

        # 非核心参数移入趋势/屏障/维护页，状态页不再额外显示提示卡。

        if getattr(self, "_runtime_param_hover", None):
            name, pos = self._runtime_param_hover
            Tooltip(name, PARAMETER_EXPLANATIONS[name], width=300, state="info").draw(self.screen, pos)

    def draw_menu(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((21, 34, 43, 150))
        self.screen.blit(overlay, (0, 0))
        box = pygame.Rect(335, 35, 816, 830)
        rounded(self.screen, box, WHITE, BLUE, 3, 18)
        write(self.screen, "核境造物", F34, BLACK, (743, 70), "center")
        write_fit(self.screen, BEGINNER_OBJECTIVE.get("玩家身份", "项目负责人") + "｜胜利：完成五阶段，安全/防护≥80，剂量分级可控", 13, TEXT_MUTED, pygame.Rect(384, 103, 720, 24), align="center", min_size=10)

        write(self.screen, "学习模式", F16, BLACK, (372, 149))
        self.menu_mode_buttons = {}
        modes = ["starter", "guided", "demo", "challenge"]
        for idx, key in enumerate(modes):
            info = PLAY_MODES[key]
            col = idx % 2
            row = idx // 2
            rect = pygame.Rect(372 + col * 374, 181 + row * 72, 364, 64)
            self.menu_mode_buttons[key] = rect
            active = self.selected_mode == key
            rounded(self.screen, rect, (232, 246, 251) if active else (247, 250, 251),
                    BLUE if active else BORDER, 2 if active else 1, 8)
            write_fit(self.screen, info["name"], 15, BLUE if active else BLACK,
                      pygame.Rect(rect.x + 14, rect.y + 9, rect.width - 28, 20), bold=True, min_size=12)
            write_wrapped(self.screen, info["brief"], 10, TEXT_MUTED,
                          pygame.Rect(rect.x + 14, rect.y + 33, rect.width - 28, 22), min_size=8, max_lines=2, line_gap=12)

        write(self.screen, "任务目标", F16, BLACK, (372, 319))
        self.mission_buttons = {}
        y = 352
        for key, mission in MISSION_TYPES.items():
            disabled = self.selected_mode == "starter" and key != "guided"
            rect = pygame.Rect(372, y, 742, 72)
            self.mission_buttons[key] = rect
            best = self.best_score_for_mission(key, self.selected_mode)
            fill = (248, 250, 251) if disabled else ((232, 246, 251) if key == "guided" else (247, 250, 251))
            border = BORDER if disabled else (BLUE if key == "guided" else BORDER)
            rounded(self.screen, rect, fill, border, 1, 9)
            title = mission["name"] + ("（极简模式固定任务）" if key == "guided" and self.selected_mode == "starter" else "")
            write_fit(self.screen, title, 16, TEXT_MUTED if disabled else BLUE if key == "guided" else BLACK,
                      pygame.Rect(rect.x + 18, rect.y + 10, 430, 22), bold=True, min_size=12)
            brief = "极简教学仅开放“教学并网”，先熟悉基本流程。" if disabled else mission["brief"]
            write_fit(self.screen, brief, 11, TEXT_MUTED, pygame.Rect(rect.x + 18, rect.y + 42, 540, 18), min_size=9)
            result = "暂不开放" if disabled else ("未挑战" if best is None else f"最高分 {best}")
            write_fit(self.screen, result, 13, TEXT_MUTED if disabled or best is None else GOOD,
                      pygame.Rect(rect.right - 154, rect.y + 22, 128, 23), align="right", min_size=10)
            y += 77

        mode_note = {
            "starter": "推荐初次玩家：隐藏防护策划、设备老化和屏障整改；运行阶段只练习一次基础预警。",
            "guided": "普通模式：开启防护验收、作业策划、纵深防御与维护管理，并提供明确提示。",
            "demo": "演示模式：自动完成主要流程，适合答辩或课堂快速展示。",
            "challenge": "进阶挑战：异常原因隐藏，倒计时不会因查看弹窗而暂停。",
        }[self.selected_mode]
        note = pygame.Rect(372, 585, 742, 66)
        rounded(self.screen, note, (255, 249, 235), WARNING, 1, 8)
        write(self.screen, "模式说明", F14, WARNING, (388, 598))
        write_wrapped(self.screen, mode_note, 12, TEXT_MUTED, pygame.Rect(388, 622, 707, 20), min_size=9, max_lines=1)

        latest = self.latest_saved_stage()
        if latest is not None:
            self.menu_continue = pygame.Rect(372, 662, 500, 42)
            rounded(self.screen, self.menu_continue, GREEN, GREEN, 1, 8)
            write_fit(self.screen, f"继续上次工程｜{STAGE_NAMES[latest]}", 14, WHITE,
                      self.menu_continue.inflate(-12, -6), align="center", min_size=10)
            self.menu_reset_save = pygame.Rect(886, 662, 228, 42)
            Button(self.menu_reset_save, "重置存档", WHITE, DANGER, DANGER, font_size=14).draw(self.screen)
        else:
            self.menu_continue = None
            self.menu_reset_save = pygame.Rect(886, 662, 228, 42)
            Button(self.menu_reset_save, "重置存档", WHITE, DANGER, DANGER, font_size=14).draw(self.screen)
        goal_card = pygame.Rect(372, 721, 742, 72)
        rounded(self.screen, goal_card, (239, 247, 252), BLUE, 1, 8)
        write_fit(self.screen, "本局目标", 12, BLUE, pygame.Rect(goal_card.x + 14, goal_card.y + 8, 70, 18), bold=True, min_size=9)
        write_fit(self.screen, BEGINNER_OBJECTIVE.get("总目标", "完成建设并安全并网。"), 11, BLACK, pygame.Rect(goal_card.x + 88, goal_card.y + 8, 630, 18), min_size=8)
        vc = "；".join(BEGINNER_OBJECTIVE.get("胜利条件", [])[:2])
        fc = "；".join(BEGINNER_OBJECTIVE.get("失败条件", [])[:2])
        write_fit(self.screen, "胜利：" + vc, 10, GOOD, pygame.Rect(goal_card.x + 14, goal_card.y + 31, 704, 15), min_size=8)
        write_fit(self.screen, "失败：" + fc, 10, DANGER, pygame.Rect(goal_card.x + 14, goal_card.y + 50, 704, 15), min_size=8)
        self.menu_settings = pygame.Rect(372, 805, 150, 32)
        Button(self.menu_settings, "设置", WHITE, BLUE, BLUE, font_size=12).draw(self.screen)
        write_fit(self.screen, "教学简化模型，不用于真实工程操作或辐射防护决策。",
                  10, TEXT_MUTED, pygame.Rect(535, 812, 579, 18), align="center", min_size=8)

    def draw_work_plan(self):
        if not self.work_plan_open or not self.dose_task:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 24, 30, 140))
        self.screen.blit(overlay, (0, 0))
        box = pygame.Rect(304, 72, 884, 764)
        self.work_plan_rect = box
        rounded(self.screen, box, WHITE, WARNING, 2, 15)
        priority_name = {"dose": "低剂量优先", "speed": "时限优先", "economy": "经济优先"}[self.dose_task["priority"]]
        write(self.screen, "受控区作业策划", F28, BLACK, (340, 101))
        write_fit(self.screen, f"{self.dose_task['title']}｜{priority_name}", 15, WARNING,
                  pygame.Rect(340, 143, 810, 24), min_size=12)
        constraint = (f"约束：≤{self.dose_task['deadline']} 模拟秒｜专项预算≤{self.dose_task['budget_limit']} 币｜"
                      f"每模拟秒发电损失 {self.dose_task['power_loss_per_second']} 币")
        write_fit(self.screen, constraint, 12, TEXT_MUTED, pygame.Rect(340, 176, 810, 21), min_size=9)
        # 说明文字移到操作说明文档，弹窗内只保留可操作信息。

        labels = {"route": "① 路线选择", "staff": "② 人员配置", "equipment": "③ 防护装备"}
        y_positions = {"route": 224, "staff": 357, "equipment": 490}
        self.work_plan_buttons = {}
        for group, title in labels.items():
            y = y_positions[group]
            write(self.screen, title, F15, BLACK, (340, y))
            x = 340
            for key, option in WORK_PLAN_OPTIONS[group].items():
                rect = pygame.Rect(x, y + 32, 255, 84)
                self.work_plan_buttons[(group, key)] = rect
                active = self.work_plan_selection.get(group) == key
                rounded(self.screen, rect, (232, 246, 251) if active else (248, 250, 251),
                        BLUE if active else BORDER, 2 if active else 1, 8)
                write_fit(self.screen, option["name"], 13, BLUE if active else BLACK,
                          pygame.Rect(rect.x + 12, rect.y + 10, rect.width - 24, 24), bold=True, min_size=12)
                write_fit(self.screen, f"{option['cost']}币 / {option['time']}模拟秒", 13,
                          GREEN if active else TEXT_MUTED, pygame.Rect(rect.x + 12, rect.y + 46, rect.width - 24, 24),
                          min_size=11)
                x += 266

        estimate = self.estimate_work_plan()
        summary = pygame.Rect(340, 623, 810, 91)
        rounded(self.screen, summary, (239, 247, 252), BLUE, 1, 8)
        write(self.screen, "方案预估与约束检查", F14, BLUE, (356, 635))
        if estimate["ready"]:
            dose_color = GOOD if estimate["dose"] < 2 else WARNING if estimate["dose"] < 5 else DANGER
            write_fit(self.screen, f"剂量 {estimate['dose']:.2f} mSv", 14, dose_color,
                      pygame.Rect(356, 660, 147, 26), bold=True, min_size=11)
            write_fit(self.screen, f"用时 {estimate['time']} 模拟秒", 13,
                      GOOD if estimate["deadline_ok"] else DANGER, pygame.Rect(517, 660, 152, 26), min_size=10)
            write_fit(self.screen, f"采购 {estimate['cost']} 币", 13,
                      GOOD if estimate["budget_ok"] else DANGER, pygame.Rect(685, 660, 144, 26), min_size=10)
            write_fit(self.screen, f"收益损失 {estimate['revenue_loss']} 币", 13, ORANGE,
                      pygame.Rect(844, 660, 194, 26), min_size=10)
            verdict = "满足专项要求" if estimate["fit"] else "不满足任务优先约束，将扣防护评分"
            write_fit(self.screen, verdict, 13, GOOD if estimate["fit"] else DANGER,
                      pygame.Rect(356, 684, 614, 24), min_size=10)
        else:
            write_fit(self.screen, "请选择三项配置后显示预计结果与是否达标。", 14, TEXT_MUTED,
                      pygame.Rect(356, 660, 560, 26), min_size=11)

        self.work_plan_cancel = pygame.Rect(340, 744, 166, 48)
        self.recommend_plan_button = pygame.Rect(530, 744, 196, 48)
        self.work_plan_confirm = pygame.Rect(957, 744, 193, 48)
        rounded(self.screen, self.work_plan_cancel, WHITE, TEXT_MUTED, 1, 8)
        rounded(self.screen, self.recommend_plan_button, (234, 249, 240), GOOD, 1, 8)
        write_fit(self.screen, "应用推荐方案", 14, GOOD, self.recommend_plan_button.inflate(-10, -5),
                  align="center", min_size=11)
        rounded(self.screen, self.work_plan_confirm, BLUE if estimate["ready"] else BORDER,
                BLUE if estimate["ready"] else BORDER, 1, 8)
        write_fit(self.screen, "返回监视", 15, TEXT_MUTED, self.work_plan_cancel.inflate(-10, -5),
                  align="center", min_size=11)
        write_fit(self.screen, "执行作业方案", 15, WHITE if estimate["ready"] else TEXT_MUTED,
                  self.work_plan_confirm.inflate(-10, -5), align="center", min_size=11)

    def draw_incident_review(self):
        if not self.review_open:
            return
        case = REVIEW_LIBRARY[self.review_key]
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 24, 30, 150))
        self.screen.blit(overlay, (0, 0))
        box = pygame.Rect(371, 130, 750, 635)
        self.review_rect = box
        rounded(self.screen, box, WHITE, PURPLE, 2, 15)
        write(self.screen, "事故复盘与改进", F28, BLACK, (407, 166))
        write_fit(self.screen, "复盘不改变已保存总分，用于理解事件因果链与改进措施。", 13, TEXT_MUTED,
                  pygame.Rect(407, 210, 670, 22), min_size=10)

        rounded(self.screen, pygame.Rect(407, 253, 675, 121), (247, 250, 251), BORDER, 1, 8)
        write(self.screen, "最近事件记录", F14, BLACK, (423, 267))
        history = self.event_log[-3:] if self.event_log else [{"time": 0, "text": "本局未出现显著事件。"}]
        y = 298
        for entry in history:
            write_fit(self.screen, f"{entry.get('time', 0):>5.1f}s  {entry['text']}", 12, TEXT_MUTED,
                      pygame.Rect(423, y, 638, 20), min_size=9)
            y += 24

        write(self.screen, "请选择最合理的判断", F15, PURPLE, (407, 402))
        write_wrapped(self.screen, case["question"], 15, BLACK, pygame.Rect(407, 432, 670, 40),
                      min_size=11, max_lines=2)
        self.review_buttons = {}
        y = 486
        for option in case["choices"]:
            rect = pygame.Rect(407, y, 675, 41)
            self.review_buttons[option] = rect
            active = self.review_answer == option
            color = GOOD if active and option == case["answer"] else DANGER if active else BORDER
            rounded(self.screen, rect, (234, 249, 240) if active and option == case["answer"] else
                    (255, 241, 240) if active else (248, 250, 251), color, 1, 7)
            write_fit(self.screen, option, 13, BLACK, rect.inflate(-12, -6), min_size=10)
            y += 49

        if self.review_feedback:
            rounded(self.screen, pygame.Rect(407, 637, 675, 52), (239, 247, 252), BLUE, 1, 7)
            write_wrapped(self.screen, self.review_feedback, 12, BLUE,
                          pygame.Rect(421, 648, 647, 32), min_size=10, max_lines=2)

        self.review_close = pygame.Rect(906, 710, 176, 39)
        rounded(self.screen, self.review_close, BLUE, BLUE, 1, 8)
        write_fit(self.screen, "返回报告", 14, WHITE, self.review_close.inflate(-10, -5),
                  align="center", min_size=11)

    def draw_info_card(self):
        if not self.info_card:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 24, 30, 125))
        self.screen.blit(overlay, (0, 0))
        key = self.info_card
        module = ALL_MODULES[key]
        title, fact = KNOWLEDGE.get(key, (module.name, module.fact))
        rect = pygame.Rect(382, 154, 724, 582)
        self.card_rect = rect
        rounded(self.screen, rect, WHITE, BLUE, 2, 15)

        write_fit(self.screen, title, 28, BLUE, pygame.Rect(414, 214, 500, 42), bold=True, min_size=20)
        self.card_close_button = pygame.Rect(948, 211, 118, 36)
        rounded(self.screen, self.card_close_button, WHITE, BLUE, 1, 7)
        write_fit(self.screen, "关闭", 14, BLUE, self.card_close_button.inflate(-8, -5), align="center", min_size=11)

        badges = [(f"系统：{module.category}", PURPLE), (f"造价：{module.cost} 币", BLUE), (f"工期：{module.days:g} 天", ORANGE)]
        x = 414
        for label, color in badges:
            width = max(116, min(168, get_font(13).size(label)[0] + 22))
            badge = pygame.Rect(x, 270, width, 29)
            rounded(self.screen, badge, (244, 248, 250), color, 1, 6)
            write_fit(self.screen, label, 13, color, badge.inflate(-8, -4), align="center", min_size=10)
            x += width + 9

        dependency = "无前置安装要求" if not module.needs else "需先完成：" + "、".join(ALL_MODULES[item].name for item in module.needs)
        note = SYSTEM_TECHNICAL_NOTES.get(key, {})
        sections = [
            ("设备作用", module.info),
            ("游戏转化", note.get("游戏转化", "该模块的安装状态将影响阶段验收、回路完整性或运行事件处置。")),
            ("安装约束", dependency),
            ("资料依据", fact),
        ]
        if key == "dosimetry":
            sections.append(("重要说明", "剂量采用 20/50/100 mSv 分级：20 为职业参考线，100 为事故教学红线。"))

        content_lines = []
        for heading, paragraph in sections:
            content_lines.append(("heading", heading))
            for line in wrap_lines(paragraph, F13, 568):
                content_lines.append(("body", line))
            content_lines.append(("gap", ""))
        viewport = pygame.Rect(414, 320, 642, 341)
        pygame.draw.rect(self.screen, (249, 251, 252), viewport, border_radius=8)
        self.card_max_scroll = max(0, len(content_lines) - 6)
        self.card_scroll = int(clamp(self.card_scroll, 0, self.card_max_scroll))
        visible = content_lines[self.card_scroll:self.card_scroll + 6]
        old_clip = self.screen.get_clip()
        self.screen.set_clip(viewport)
        y = viewport.y + 12
        for style, text in visible:
            if style == "heading":
                write(self.screen, text, F14, BLUE, (viewport.x + 13, y))
                y += 42
            elif style == "body":
                write(self.screen, text, F13, BLACK, (viewport.x + 19, y))
                y += 38
            else:
                y += 24
        self.screen.set_clip(old_clip)

        track = pygame.Rect(viewport.right - 11, viewport.y + 11, 5, viewport.height - 22)
        pygame.draw.rect(self.screen, GRID, track, border_radius=3)
        if self.card_max_scroll > 0:
            thumb_h = max(48, int(track.height * 6 / len(content_lines)))
            offset = int((track.height - thumb_h) * self.card_scroll / self.card_max_scroll)
            pygame.draw.rect(self.screen, BLUE, (track.x, track.y + offset, track.width, thumb_h), border_radius=3)
            write_fit(self.screen, "滚动鼠标滚轮查看更多内容", 12, TEXT_MUTED,
                      pygame.Rect(414, 678, 394, 23), min_size=10)
        else:
            write_fit(self.screen, "内容已完整显示", 12, TEXT_MUTED, pygame.Rect(414, 678, 394, 23), min_size=10)
        write_fit(self.screen, "右键设备可再次打开此卡片｜" + DATA_SOURCE_NOTE, 10, TEXT_MUTED,
                  pygame.Rect(625, 678, 431, 23), align="right", min_size=7)

    def draw_report(self):
        if not self.report:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((18, 28, 35, 150))
        self.screen.blit(overlay, (0, 0))

        # 结算页改成摘要式大卡片：先给结果，再给少量复盘，长日志/专业依据不再同屏显示。
        box = pygame.Rect(360, 118, 780, 650)
        self.report_rect = box
        rounded(self.screen, box, WHITE, GOOD if not self.scrammed else DANGER, 3, 16)
        score = self.calculate_total_score()
        stars = self.current_stars() if hasattr(self, "current_stars") else (3 if score >= 90 else 2 if score >= 75 else 1)
        write(self.screen, "建设与运行评价报告", F28, BLACK, (box.centerx, 154), "center")
        write_fit(self.screen, "★" * stars + "☆" * (3 - stars) + f"  总分 {score}",
                  20, WARNING, pygame.Rect(box.x + 70, 188, box.width - 140, 30), align="center", min_size=15)
        write_fit(self.screen, f"{PLAY_MODES[self.play_mode]['name']}｜{MISSION_TYPES[self.mission_key]['name']}｜{self.site['name']}",
                  13, BLUE, pygame.Rect(box.x + 70, 222, box.width - 140, 22), align="center", min_size=10)

        style = self.strategy_style() if hasattr(self, "strategy_style") else "平衡型"
        safe_count = self.route_count("安全") if hasattr(self, "route_count") else 0
        aggressive_count = self.route_count("激进") if hasattr(self, "route_count") else 0
        if self.scrammed:
            title_name = "事故复盘员"
        elif style == "稳健型":
            title_name = "稳健建设者"
        elif style == "进取型":
            title_name = "高效推进者"
        elif style == "成本控制型":
            title_name = "成本控制师"
        else:
            title_name = "均衡调度官"
        if self.stage >= 4 and not self.scrammed and self.safety >= 80:
            badge_name = "首次并网证明"
        elif safe_count >= 2:
            badge_name = "安全优先徽章"
        elif aggressive_count >= 2:
            badge_name = "工期压缩徽章"
        else:
            badge_name = "基础建设徽章"
        mistake_text = "无重大失误" if self.mistakes == 0 and not self.scrammed else f"{self.mistakes} 次错误 / {'停堆' if self.scrammed else '未停堆'}"
        if aggressive_count > safe_count:
            next_risk = "下一关：优先处理黄色预警"
        elif getattr(self, "funds", 0) < 2000:
            next_risk = "下一关：预算紧张，谨慎升级"
        elif self.equipment_average_health() < 85:
            next_risk = "下一关：先安排检修窗口"
        else:
            next_risk = "下一关：保持安全系统完整"
        upgrade_done = [key for key, up in getattr(self, "upgrades", {}).items() if getattr(up, "level", 0) >= 1]
        if "edg" in upgrade_done:
            build_line = "应急供电强化型"
        elif "asg" in upgrade_done:
            build_line = "辅助给水强化型"
        elif "krt" in upgrade_done or "ety" in upgrade_done:
            build_line = "辐射监测强化型"
        elif upgrade_done:
            build_line = "专设安全设施强化型"
        else:
            build_line = "基础运行型"

        cards = [
            ("本关称号", title_name, GOOD if not self.scrammed else DANGER),
            ("获得徽章", badge_name, PURPLE),
            ("建设倾向", build_line, BLUE),
            ("本关失误", mistake_text, GOOD if self.mistakes == 0 and not self.scrammed else WARNING),
            ("安全 / 防护", f"{self.safety} / {self.protection_score}", GOOD if min(self.safety, self.protection_score) >= 85 else WARNING),
            ("剂量 / 资金", f"{self.collective_dose:.2f} mSv / {money(self.funds)} 币", GOOD if self.collective_dose < DOSE_REFERENCE_LINE and self.funds >= 1000 else WARNING),
        ]
        card_w, card_h = 210, 78
        x0, y0 = box.x + 58, 270
        for idx, (label, value, color) in enumerate(cards):
            cx = x0 + (idx % 3) * (card_w + 20)
            cy = y0 + (idx // 3) * (card_h + 22)
            rect = pygame.Rect(cx, cy, card_w, card_h)
            rounded(self.screen, rect, (247, 250, 251), color, 1, 10)
            write_fit(self.screen, label, 13, TEXT_MUTED, pygame.Rect(rect.x + 14, rect.y + 10, rect.width - 28, 20), min_size=10)
            write_fit(self.screen, value, 17, color, pygame.Rect(rect.x + 14, rect.y + 38, rect.width - 28, 26), bold=True, min_size=12)

        # 复盘摘要聚焦两条关键记录；“下一关提示”单独放到下方蓝框里，避免重复且挤出边界。
        self.unlock_endgame_rewards()
        summary_box = pygame.Rect(box.x + 58, 470, box.width - 116, 126)
        rounded(self.screen, summary_box, (245, 249, 251), BORDER, 1, 10)
        write_fit(self.screen, "复盘摘要", 17, BLACK, pygame.Rect(summary_box.x + 18, summary_box.y + 14, 120, 26), bold=True, min_size=13)
        lines = []
        decisions = list(getattr(self, "decision_review", []) or [])[-1:]
        for item in decisions:
            effects = "；".join(str(v) for v in item.get("effects", [])[:1]) or "影响已记录"
            lines.append(f"决策：{item.get('title', '')} → {effects}")
        recent = getattr(self, "event_log", [])[-1:]
        for item in recent:
            lines.append(f"事件：{item.get('time', 0):.1f}s  {item.get('text', '')}")
        if not lines:
            lines.append("本局运行较稳，暂无重点复盘事件。")
        yy = summary_box.y + 48
        for line in lines[:2]:
            write_wrapped(self.screen, line, 12, TEXT_MUTED, pygame.Rect(summary_box.x + 18, yy, summary_box.width - 36, 28), min_size=9, max_lines=2, line_gap=12)
            yy += 34

        next_box = pygame.Rect(box.x + 58, 610, box.width - 116, 48)
        rounded(self.screen, next_box, (239, 247, 252), BLUE, 1, 8)
        write_fit(self.screen, next_risk, 14, BLUE,
                  next_box.inflate(-18, -10), min_size=11)

        self.report_restart = pygame.Rect(box.x + 160, 690, 150, 42)
        self.report_close = pygame.Rect(box.x + 318, 690, 150, 42)
        self.report_menu = pygame.Rect(box.x + 476, 690, 150, 42)
        rounded(self.screen, self.report_restart, BLUE, BLUE, 2, 8)
        rounded(self.screen, self.report_close, WHITE, BLUE, 2, 8)
        rounded(self.screen, self.report_menu, WHITE, TEXT_MUTED, 2, 8)
        write(self.screen, "重新挑战", F15, WHITE, self.report_restart.center, "center")
        write(self.screen, "继续观察", F15, BLUE, self.report_close.center, "center")
        write(self.screen, "返回菜单", F15, TEXT_MUTED, self.report_menu.center, "center")

    def draw_tooltip(self):
        if not self.tooltip_box:
            return
        term, text, source = self.tooltip_box
        if not text:
            return
        pos = (source.right + 8, max(120, source.y - 20)) if source.x > 900 else (940, 602)
        Tooltip(term, text, width=338 if source.x <= 900 else 360, state="warning").draw(self.screen, pos)


