# -*- coding: utf-8 -*-
"""演示模式系统。

把自动演示流程和讲解词从普通运行逻辑中拆出，方便课堂/答辩调整讲稿。
本版补充了答辩常用的暂停/继续、上一段/下一段、自动播放和操作指示。
"""
from __future__ import annotations

import pygame

from .demo_script import DEMO_STEPS
from .theme import BLUE, CENTER, RIGHT, TEXT_MUTED, WARNING, WHITE, GRID, GOOD, BORDER
from .ui_helpers import write_fit, write_wrapped, rounded
from .ui.components import AlertBanner, Badge, Button, TabView
from .advanced_features import DEMO_ROUTES


class DemoSystemMixin:
    def init_demo_system(self):
        self.demo_step_name = ""
        self.demo_title = "演示模式"
        self.demo_text = "演示模式会自动推进主要流程，并同步显示讲解词。"
        self.demo_action = ""
        self.demo_knowledge = ""
        self.demo_speech = ""
        self.demo_duration = ""
        self.demo_highlight = ""
        self.demo_timer = 0.0
        self.demo_autoplay = True
        self.demo_paused = False
        self.demo_forced_step = None
        self.demo_control_rects = {}
        self.demo_tab = "讲解"
        self.demo_route = "route_build"

    def _matched_demo_index(self):
        for index, step in enumerate(DEMO_STEPS):
            try:
                if step["condition"](self):
                    return index
            except Exception:
                continue
        return 0

    def _apply_demo_step(self, index: int, force_name: bool = False):
        index = max(0, min(index, len(DEMO_STEPS) - 1))
        step = DEMO_STEPS[index]
        if force_name or self.demo_step_name != step["name"]:
            self.demo_step_name = step["name"]
            self.demo_title = step["title"]
            self.demo_text = step["text"]
            self.demo_action = step["action"]
            self.demo_knowledge = step.get("knowledge", "")
            self.demo_speech = step.get("speech", step.get("text", ""))
            self.demo_duration = step.get("duration", "")
            self.demo_highlight = step.get("highlight", "")
            self.demo_timer = 0.0

    def refresh_demo_narration(self):
        if getattr(self, "play_mode", "") != "demo":
            return
        index = self.demo_forced_step if self.demo_forced_step is not None else self._matched_demo_index()
        self._apply_demo_step(index)

    def demo_next_step(self):
        base = self.demo_forced_step if self.demo_forced_step is not None else self._matched_demo_index()
        self.demo_forced_step = min(len(DEMO_STEPS) - 1, base + 1)
        self._apply_demo_step(self.demo_forced_step, force_name=True)
        self.demo_paused = True
        self.demo_timer = 0.0
        self.audio.play("click")

    def demo_prev_step(self):
        base = self.demo_forced_step if self.demo_forced_step is not None else self._matched_demo_index()
        self.demo_forced_step = max(0, base - 1)
        self._apply_demo_step(self.demo_forced_step, force_name=True)
        self.demo_paused = True
        self.demo_timer = 0.0
        self.audio.play("click")

    def demo_follow_flow(self):
        self.demo_forced_step = None
        self.demo_paused = False
        self.refresh_demo_narration()
        self.audio.play("click")


    def demo_jump_to(self, target: str):
        """答辩模式章节跳转：用于现场展示时快速定位关键段落。"""
        target_map = {"site": 0, "install": 2, "accident": 6, "report": len(DEMO_STEPS) - 1}
        self.demo_forced_step = target_map.get(target, self._matched_demo_index())
        self._apply_demo_step(self.demo_forced_step, force_name=True)
        self.demo_paused = True
        self.demo_timer = 0.0
        if target == "site":
            self.report = False
            if hasattr(self, "site_selection_open"):
                self.site_selection_open = True
            self.set_message("答辩跳转：展示选址逻辑与冷却水条件取舍。", BLUE)
        elif target == "install":
            self.report = False
            if self.stage < 1:
                self.stage = 1
            self.set_message("答辩跳转：展示设备安装与安全系统配置。", BLUE)
        elif target == "accident":
            self.report = False
            if self.stage != 4:
                self.stage = 4
                self.runtime = max(getattr(self, "runtime", 0.0), 22.0)
                self.protection_verified = True
                self.challenge_finished = False
                self.next_fault = 999.0
            if not getattr(self, "warning_event", None) and not getattr(self, "fault", None):
                try:
                    self.trigger_warning("vacuum")
                except Exception:
                    self.set_message("答辩跳转：事故演示需要进入并网运行后触发。", WARNING)
            self.set_message("答辩跳转：展示预警—故障—停堆事故链。", WARNING)
        elif target == "report":
            if self.stage != 4:
                self.stage = 4
                self.runtime = max(getattr(self, "runtime", 0.0), 30.0)
                self.protection_verified = True
            self.warning_event = None
            self.fault = None
            self.dose_task = None
            self.service_job = None
            if hasattr(self, "barriers"):
                for key in self.barriers:
                    self.barriers[key] = max(self.barriers[key], 90.0)
            self.challenge_finished = False
            self.finish_challenge()
        self.audio.play("click")

    def demo_start_route(self, route_key: str):
        """答辩固定路线：让现场演示不依赖随机游玩。"""
        self.demo_route = route_key
        self.demo_paused = False
        self.demo_autoplay = True
        self.demo_forced_step = None
        if route_key == "route_build":
            self.demo_jump_to("site")
            self.set_message("演示路线：基础建设演示。", BLUE)
        elif route_key == "route_accident":
            self.demo_jump_to("accident")
            try:
                self.trigger_warning("power")
            except Exception:
                pass
            self.set_message("演示路线：LOOP→EDG→ASG 的事故链演示。", WARNING)
        elif route_key == "route_radiation":
            if self.stage != 4:
                self.stage = 4
                self.protection_verified = True
            self.dose_task = {"title": "KRT 报警后的受控区作业", "description": "演示时间/距离/屏蔽三要素。", "base_dose": 13.0, "deadline": 24, "budget_limit": 360, "power_loss_per_second": 3, "priority": "dose"}
            self.dose_task_left = self.dose_task_duration()
            self.dashboard_page = "status"
            self.set_message("演示路线：KRT 报警→剂量分级→时间/距离/屏蔽作业方案。", WARNING)
        elif route_key == "route_atlas":
            if self.stage != 4:
                self.stage = 4
                self.protection_verified = True
            self.dashboard_page = "atlas"
            # 为答辩演示解锁几张示例卡，但不伪造全部掌握。
            for i, state in {12: "mastered", 16: "unlocked", 17: "review", 20: "unlocked"}.items():
                if hasattr(self, "accident_gallery_state"):
                    self.accident_gallery_state[i] = state
            self.set_message("演示路线：展示 20 个事故图鉴、解锁状态与复盘标记。", BLUE)
        self.audio.play("click")

    def toggle_demo_pause(self):
        self.demo_paused = not self.demo_paused
        self.audio.play("click")

    def toggle_demo_autoplay(self):
        self.demo_autoplay = not self.demo_autoplay
        if self.demo_autoplay:
            self.demo_paused = False
            self.demo_forced_step = None
        self.audio.play("click")

    def handle_demo_key(self, key) -> bool:
        if getattr(self, "play_mode", "") != "demo" or self.menu or self.report:
            return False
        if key in (pygame.K_SPACE, pygame.K_p):
            self.toggle_demo_pause()
            return True
        if key in (pygame.K_RIGHT, pygame.K_n):
            self.demo_next_step()
            return True
        if key in (pygame.K_LEFT, pygame.K_b):
            self.demo_prev_step()
            return True
        if key == pygame.K_a:
            self.toggle_demo_autoplay()
            return True
        if key == pygame.K_f:
            self.demo_follow_flow()
            return True
        return False

    def handle_demo_click(self, pos, button=1) -> bool:
        if button != 1 or getattr(self, "play_mode", "") != "demo" or self.menu or self.report:
            return False
        for key, rect in getattr(self, "demo_control_rects", {}).items():
            if rect.collidepoint(pos):
                if key == "pause":
                    self.toggle_demo_pause()
                elif key == "prev":
                    self.demo_prev_step()
                elif key == "next":
                    self.demo_next_step()
                elif key == "auto":
                    self.toggle_demo_autoplay()
                elif key == "follow":
                    self.demo_follow_flow()
                elif key == "jump_site":
                    self.demo_jump_to("site")
                elif key == "jump_install":
                    self.demo_jump_to("install")
                elif key == "jump_accident":
                    self.demo_jump_to("accident")
                elif key == "jump_report":
                    self.demo_jump_to("report")
                elif key in DEMO_ROUTES:
                    self.demo_start_route(key)
                elif key == "讲解":
                    self.demo_tab = "讲解"
                    self.audio.play("click")
                return True
        return False

    def update_demo_mode(self, dt):
        """自动演示主要流程，同时刷新讲解词。

        演示模式用于课堂/答辩，不应卡在通关弹窗上。
        因此弹窗出现时，如果自动播放未暂停，会短暂停留后自动关闭。
        """
        if self.play_mode != "demo" or self.menu or self.report:
            return
        self.refresh_demo_narration()
        if self.level_popup:
            if self.demo_paused or not self.demo_autoplay:
                return
            self.demo_timer += dt
            if self.demo_timer >= 1.2:
                self.demo_timer = 0.0
                self.close_level_popup()
            return
        if self.demo_paused or not self.demo_autoplay:
            return
        self.demo_timer += dt
        # 给观众保留短暂停顿，便于看清讲解词。
        if self.demo_timer < 0.65:
            return
        self.demo_timer = 0.0
        if getattr(self, "site_selection_open", False):
            self.choose_site("river")
            return
        if self.stage in (0, 1):
            key = self.next_install_key()
            if key:
                self.install(key)
            else:
                self.proceed_stage()
            return
        if self.stage == 2:
            for key in ("flush", "seal", "diesel_a_test", "diesel_b_test"):
                if self.quiz.get(key) is not True:
                    self.answer_quiz(key, True)
                    return
            self.proceed_stage()
            return
        if self.stage == 3:
            if self.critical_step < 4:
                self.critical_action(self.critical_step)
            else:
                self.proceed_stage()
            return
        if self.stage == 4 and self.runtime > 20 and not self.warning_event and not self.fault and not self.dose_task:
            self.finish_challenge()

    def _demo_highlight_rects(self):
        mode = self.demo_highlight
        rects = []
        if mode == "site" and getattr(self, "site_selection_open", False):
            rects.extend([r for r in getattr(self, "site_buttons", {}).values() if r.width and r.height])
        elif mode == "install" and self.stage in (0, 1):
            key = self.next_install_key()
            if key:
                if key in getattr(self, "toolbar_rects", {}):
                    rects.append(self.toolbar_rects[key])
                from .catalog import ALL_MODULES
                if key in ALL_MODULES:
                    rects.append(ALL_MODULES[key].slot)
        elif mode == "commissioning":
            rects.extend([r for r in getattr(self, "action_rects", {}).values() if r.width and r.height])
        elif mode == "critical":
            buttons = getattr(self, "critical_buttons", [])
            if buttons:
                idx = min(getattr(self, "critical_step", 0), len(buttons) - 1)
                rects.append(buttons[idx])
        elif mode == "parameters":
            rects.append(RIGHT)
        elif mode == "accident":
            rects.append(CENTER.inflate(-80, -80))
            rects.extend([r for r in getattr(self, "operation_tool_rects", {}).values() if r.width and r.height])
        return [r for r in rects if isinstance(r, pygame.Rect) and r.width > 0 and r.height > 0]

    def draw_demo_highlight(self):
        if getattr(self, "play_mode", "") != "demo" or self.menu or self.report:
            return
        self.refresh_demo_narration()
        for rect in self._demo_highlight_rects():
            pulse = int(4 + 2 * (1 + pygame.time.get_ticks() % 800 / 800))
            halo = rect.inflate(10, 10)
            pygame.draw.rect(self.screen, WARNING, halo, pulse, border_radius=10)
            pygame.draw.rect(self.screen, (255, 248, 210), halo.inflate(6, 6), 1, border_radius=12)

    def draw_demo_narration(self):
        # 答辩讲解只覆盖普通操作界面；关卡地图、设置页、报告、知识卡等
        # 已经是完整弹层，如果继续叠加讲解条会造成文字重叠。
        if (
            getattr(self, "play_mode", "") != "demo"
            or self.menu
            or self.report
            or getattr(self, "level_map_open", False)
            or getattr(self, "settings_open", False)
            or getattr(self, "info_card", None)
            or getattr(self, "work_plan_open", False)
            or getattr(self, "review_open", False)
        ):
            return
        self.refresh_demo_narration()

        # 演示栏改为“正文 / 路线 / 控制”三层；路线和控制分两行，避免按钮横向溢出。
        rect = pygame.Rect(250, 506, 900, 244)
        self.demo_control_rects = {}
        state = "warning" if self.demo_paused else "info"
        AlertBanner(
            pygame.Rect(rect.x, rect.y, rect.width, 34),
            "答辩演示",
            self.demo_title,
            state=state,
            footer="",
        ).draw(self.screen)
        body_rect = pygame.Rect(rect.x, rect.y + 38, rect.width, rect.height - 38)
        rounded(self.screen, body_rect, (255, 249, 235), WARNING, 2, 12)

        # 只保留“讲解”一个入口；讲解、知识、讲稿整理为一个三行表，避免三个页签分散信息。
        tabs = TabView(pygame.Rect(rect.x + 16, rect.y + 50, 64, 30), ["讲解"], "讲解")
        self.demo_control_rects.update(tabs.draw(self.screen))
        Badge(pygame.Rect(rect.x + 18, rect.y + 90, 88, 28), "自动" if self.demo_autoplay else "手动", "good" if self.demo_autoplay else "warn", "▶").draw(self.screen)
        Badge(pygame.Rect(rect.x + 114, rect.y + 90, 88, 28), "暂停" if self.demo_paused else "播放", "warn" if self.demo_paused else "info", "Ⅱ" if self.demo_paused else "▶").draw(self.screen)

        table_x = rect.x + 218
        table_y = rect.y + 48
        table_w = rect.width - 246
        rows = [("讲解", self.demo_text), ("知识", self.demo_knowledge), ("讲稿", self.demo_speech)]
        for i, (label, body) in enumerate(rows):
            row = pygame.Rect(table_x, table_y + i * 28, table_w, 24)
            rounded(self.screen, row, (255, 252, 244) if i == 0 else (247, 250, 251), WARNING if i == 0 else BORDER, 1, 5)
            write_fit(self.screen, label, 11, WARNING if i == 0 else TEXT_MUTED,
                      pygame.Rect(row.x + 8, row.y + 3, 42, 18), align="center", min_size=8)
            write_fit(self.screen, body, 11, TEXT_MUTED,
                      pygame.Rect(row.x + 56, row.y + 3, row.width - 64, 18), min_size=8)
        duration = ("｜预计用时：" + self.demo_duration) if self.demo_duration else ""
        write_fit(self.screen, "当前操作：" + self.demo_action + duration, 12, BLUE,
                  pygame.Rect(rect.x + 218, rect.y + 134, rect.width - 246, 22), min_size=9)

        progress = (self.stage + self.stage_progress_ratio()) / 5
        progress_bar = pygame.Rect(rect.x + 218, rect.y + 160, 312, 9)
        rounded(self.screen, progress_bar, GRID, GRID, 1, 4)
        if progress_bar.width > 0:
            rounded(self.screen, pygame.Rect(progress_bar.x, progress_bar.y, int(progress_bar.width * progress), progress_bar.height),
                    BLUE if not self.demo_paused else WARNING, BLUE if not self.demo_paused else WARNING, 1, 4)
        write_fit(self.screen, f"进度 {int(progress * 100)}%", 11, TEXT_MUTED,
                  pygame.Rect(progress_bar.right + 12, progress_bar.y - 5, 86, 20), min_size=9)

        # 第二层：固定演示路线。按钮统一宽度，单独一行，不再和播放控制混排。
        route_x = rect.x + 18
        route_y = rect.y + 184
        for rkey, (rlabel, _desc) in DEMO_ROUTES.items():
            short = rlabel.replace("演示", "")
            b = pygame.Rect(route_x, route_y, 104, 30)
            self.demo_control_rects[rkey] = b
            active = getattr(self, "demo_route", "") == rkey
            Button(b, short, WHITE if active else (255, 249, 235), GOOD if active else BLUE, GOOD if active else BLUE, font_size=11).draw(self.screen)
            route_x += 114

        # 第三层：播放控制。只保留高频按钮，按键说明移动到最右侧小提示。
        controls = [
            ("auto", "自动开" if self.demo_autoplay else "自动关", 72),
            ("pause", "继续" if self.demo_paused else "暂停", 62),
            ("jump_site", "选址", 56),
            ("jump_install", "安装", 56),
            ("jump_accident", "事故", 56),
            ("jump_report", "结算", 56),
            ("follow", "跟随", 62),
        ]
        x = rect.x + 18
        control_y = rect.y + 187
        for key, label, w in controls:
            b = pygame.Rect(x, control_y, w, 30)
            self.demo_control_rects[key] = b
            color = WARNING if key in ("pause", "jump_accident") else BLUE
            Button(b, label, WHITE, color, color, font_size=10).draw(self.screen)
            x += w + 8

        # 快捷键说明移入操作说明文档，演示面板内不再常驻小字。

