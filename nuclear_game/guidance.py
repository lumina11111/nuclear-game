# -*- coding: utf-8 -*-
"""选址覆盖层、阶段任务面板与通关弹窗。

这些方法原先集中在 engine.py 中，拆出后主流程文件更短，
剧本和任务面板相关修改也更容易定位。
"""

from copy import deepcopy
from typing import List, Optional
import math

import pygame

from .theme import *
from .catalog import *
from .tutorial_content import STAGE_TUTORIALS
from .story_data import STORY_STAGE_NAMES, get_stage_script
from .commissioning import CRITICAL_ORDER, CRITICAL_LABELS, CRITICAL_TOOL_NAMES
from .ui_helpers import (
    F11, F12, F14, F15,
    write, write_fit, write_wrapped, rounded, money,
)

STAGE_NAMES = STORY_STAGE_NAMES

GUIDE_SHORT_NAMES = {
    "foundation": "地基",
    "containment": "安全壳",
    "turbine_hall": "厂房",
    "cooling_base": "取排水",
    "vessel": "压力容器",
    "core": "堆芯",
    "crdm": "控制棒驱动",
    "pressurizer": "稳压器",
    "steam_gen": "蒸汽发生器",
    "primary_pump": "主泵",
    "turbine": "汽轮机",
    "generator": "发电机",
    "condenser": "冷凝器",
    "secondary_pump": "给水泵",
    "cooling": "CRF",
    "tertiary_pump": "循环水泵",
    "diesel_a": "A列EDG",
    "diesel_b": "B列EDG",
    "spray": "EAS",
    "efw": "ASG",
    "bio_shield": "屏蔽",
    "area_monitor": "KRT",
    "dosimetry": "剂量计",
    "decon": "去污",
    "effluent_monitor": "ETY",
}


def guide_short_name(key: str) -> str:
    return GUIDE_SHORT_NAMES.get(key, ALL_MODULES[key].name if key in ALL_MODULES else str(key))


class GuidanceMixin:
    def open_stage_guide(self):
        """阶段教程已取消。

        现在只保留“关卡地图”和“实时操作指引”，避免弹窗遮挡核电站设备。
        该方法保留为空实现，兼容旧调用路径。
        """
        self.stage_guide_open = False
        self.stage_guide_page = 0

    def advance_stage_guide(self):
        """阶段教程已取消；旧快捷键调用时只关闭弹窗状态。"""
        self.stage_guide_open = False
        self.stage_guide_page = 0
        self.audio.play("click")

    def current_instruction(self) -> dict:
        """根据当前实际进度，仅提供一个明确的下一步动作。"""
        if self.stage == 0:
            order = ["foundation", "containment", "turbine_hall", "cooling_base"]
            for index, key in enumerate(order):
                if key not in self.placed:
                    return {"step": f"{index + 1}/4", "title": f"安装：{guide_short_name(key)}",
                            "detail": "拖到中央高亮槽位。",
                            "why": "土建是后续安装基础。",
                            "targets": [self.toolbar_rects.get(key), CIVIL[key].slot]}
            return {"step": "完成", "title": "执行土建验收",
                    "detail": "进入设备安装阶段。",
                    "why": "验收后自动存档。", "targets": [self.stage_button]}

        if self.stage == 1:
            sequence = [
                ("反应堆", "vessel"), ("反应堆", "core"), ("反应堆", "crdm"),
                ("常规", "pressurizer"), ("常规", "steam_gen"), ("常规", "primary_pump"),
                ("常规", "turbine"), ("常规", "generator"), ("常规", "condenser"),
                ("常规", "secondary_pump"), ("常规", "cooling"), ("常规", "tertiary_pump"),
                ("安全", "diesel_a"), ("安全", "diesel_b"), ("安全", "spray"), ("安全", "efw"),
                ("防护", "bio_shield"), ("防护", "area_monitor"), ("防护", "dosimetry"),
                ("防护", "decon"), ("防护", "effluent_monitor"),
            ]
            if self.is_starter_mode():
                sequence = sequence[:16]
            completed = sum(key in self.placed for _, key in sequence)
            for tab, key in sequence:
                if key not in self.placed:
                    if self.active_tab != tab and not getattr(self, "focus_ui", False):
                        return {"step": f"{completed + 1}/{len(sequence)}", "title": f"切到{tab}",
                                "detail": f"下一项：{guide_short_name(key)}。",
                                "why": "按系统逐组安装。",
                                "targets": [self.tab_rects.get(tab)]}
                    return {"step": f"{completed + 1}/{len(sequence)}", "title": f"安装：{guide_short_name(key)}",
                            "detail": "拖到中央高亮槽位。",
                            "why": ("防护设备影响剂量任务。"
                                    if tab == "防护" else "装齐后才能验收。"),
                            "targets": [self.toolbar_rects.get(key), ALL_MODULES[key].slot]}
            return {"step": "完成", "title": "执行设备验收",
                    "detail": "进入系统调试。",
                    "why": "安全、防护均需验收。", "targets": [self.stage_button]}

        if self.stage == 2:
            tasks = [("flush", "管路冲洗"), ("seal", "密封性试验"),
                     ("diesel_a_test", "A列电源试验"), ("diesel_b_test", "B列电源试验")]
            completed = sum((self.quiz[key] is True if key in ("flush", "seal") else self.quiz[key])
                            for key, _ in tasks)
            for key, name in tasks:
                done = self.quiz[key] is True if key in ("flush", "seal") else self.quiz[key]
                if not done:
                    if getattr(self, "selected_quiz", None) == key:
                        if not getattr(self, "commissioning_tool_ready", {}).get(key, False):
                            return {"step": f"{completed + 1}/4", "title": f"拖工具：{name}",
                                    "detail": "把底部工具拖到中央高亮区。",
                                    "why": "调试从点击变为操作链。",
                                    "targets": [getattr(self, "commissioning_tool_rects", {}).get(key), self.commissioning_target_rect(key)]}
                        if key in ("flush", "seal"):
                            correct = next((rect for rect, qkey, ok in getattr(self, "quiz_option_rects", [])
                                            if qkey == key and ok), None)
                            return {"step": f"{completed + 1}/4", "title": f"确认：{name}",
                                    "detail": "点底部正确结果。",
                                    "why": "调试验证边界条件。", "targets": [correct]}
                    return {"step": f"{completed + 1}/4", "title": f"调试：{name}",
                            "detail": "点左侧当前任务。",
                            "why": "四项完成后才能验收。",
                            "targets": [self.action_rects.get(key)]}
            return {"step": "完成", "title": "执行调试验收",
                    "detail": "进入装料与临界。",
                    "why": "核验装料前条件。", "targets": [self.stage_button]}

        if self.stage == 3:
            if self.critical_step < len(CRITICAL_ORDER):
                key = CRITICAL_ORDER[self.critical_step]
                selected = getattr(self, "selected_critical", None)
                ready = getattr(self, "critical_tool_ready", {}).get(key, False)
                if selected != key:
                    return {"step": f"{self.critical_step + 1}/4", "title": CRITICAL_LABELS[key],
                            "detail": "先点左侧当前步骤。",
                            "why": "按联锁顺序执行。",
                            "targets": [self.critical_buttons[self.critical_step] if self.critical_buttons else None]}
                if not ready:
                    return {"step": f"{self.critical_step + 1}/4", "title": "拖拽：" + CRITICAL_TOOL_NAMES[key],
                            "detail": "拖到中央高亮区。",
                            "why": "工具到位后才能确认操作。",
                            "targets": [getattr(self, "critical_tool_rects", {}).get(key), self.critical_target_rect(key)]}
                return {"step": f"{self.critical_step + 1}/4", "title": "选择正确操作",
                        "detail": "在底部控制台选择。",
                        "why": "错误会触发轻微惩罚。",
                        "targets": [getattr(self, "critical_option_rects", [None])[0] if getattr(self, "critical_option_rects", []) else None]}
            return {"step": "完成", "title": "申请并网",
                    "detail": "进入运行阶段。",
                    "why": "并网后启用动态监测。", "targets": [self.stage_button]}

        if self.warning_event:
            key = self.warning_event["key"]
            if key == "vacuum" and self.cooling_flow < 85:
                return {"step": "预警", "title": "提高冷却水",
                        "detail": "滑块调到 85% 以上。",
                        "why": "冷端预警可先恢复冷却。",
                        "targets": [getattr(self, "cool_slider", None)]}
            tool = self.event_next_tool()
            return {"step": "预警", "title": f"拖拽：{RUN_OPERATION_TOOLS[tool]['name']}" if tool else "处置完成",
                    "detail": "拖入中央发光槽。",
                    "why": "尽早处理避免升级。",
                    "targets": [self.operation_tool_rects.get(tool), RUN_OPERATION_TOOLS[tool]["target"]] if tool else []}
        if self.fault:
            tool = self.event_next_tool()
            return {"step": "故障", "title": f"拖拽：{RUN_OPERATION_TOOLS[tool]['name']}" if tool else "处置中",
                    "detail": "倒计时前完成。",
                    "why": "超时会自动停堆。",
                    "targets": [self.operation_tool_rects.get(tool), RUN_OPERATION_TOOLS[tool]["target"]] if tool else []}
        if self.dose_task:
            return {"step": "策划", "title": "制定作业方案",
                    "detail": "选择路线、人员、装备。",
                    "why": "比较剂量、成本和时间。",
                    "targets": [getattr(self, "plan_open_button", None)]}
        if self.scrammed:
            return {"step": "停堆", "title": "结束本局",
                    "detail": "进入事故复盘。",
                    "why": "停堆后状态已冻结。",
                    "targets": [self.report_button]}
        if self.service_job:
            return {"step": "维护", "title": self.service_job["title"] + "执行中",
                    "detail": "等待维护完成；期间机组输出受限。",
                    "why": "维护完成后才能恢复正常决策流程。",
                    "targets": []}
        issue = self.barrier_repair_required()
        if issue:
            return {"step": "整改", "title": "启动：" + issue["name"],
                    "detail": "点击左侧恢复任务按钮，解除当前功率限制。",
                    "why": issue["why"],
                    "targets": [getattr(self, "repair_button", None)]}
        if self.mission_complete() or self.calculate_total_score() >= 100:
            return {"step": "完成", "title": "结束挑战",
                    "detail": "保存成绩并查看报告。",
                    "why": "报告汇总本局表现。",
                    "targets": [self.report_button]}
        return {"step": "运行", "title": "保持稳定运行",
                "detail": "关注右侧状态。",
                "why": f"目标：{MISSION_TYPES[self.mission_key]['goal']}。",
                "targets": [self.dashboard_buttons.get("status")]}

    def draw_guide_highlights(self):
        """绘制实时指引框。挑战模式直接禁用，避免出现答案式提示。"""
        if (getattr(self, "play_mode", "") == "challenge"
                or not self.tutorial or self.menu or self.report
                or self.info_card or getattr(self, "site_selection_open", False)
                or getattr(self, "level_map_open", False)
                or getattr(self, "demo_enabled", False)):
            return
        guide = self.current_instruction()
        targets = [r for r in guide.get("targets", []) if isinstance(r, pygame.Rect)]
        if not targets:
            return

        # 只把第一个可操作目标作为强制引导焦点，避免多个黄框造成视觉混乱。
        target = targets[0]
        pulse = 3 + int((math.sin(pygame.time.get_ticks() / 160) + 1) * 2)
        outer = target.inflate(14, 14)
        pygame.draw.rect(self.screen, WARNING, outer, pulse, border_radius=12)
        pygame.draw.rect(self.screen, (255, 241, 178), outer.inflate(7, 7), 2, border_radius=14)

        # 如果有第二目标，也以虚线方式轻提示。例如“设备卡片 -> 槽位”。
        if len(targets) > 1:
            second = targets[1]
            pygame.draw.rect(self.screen, (255, 217, 102), second.inflate(8, 8), 2, border_radius=10)

        # 左侧功能栏已有“当前目标”，若再画黄色提示标签会挡住中央内容，
        # 因此只保留高亮框，不再额外绘制悬浮标签和箭头。
        if target.right <= LEFT.right + 4:
            return

        # 小型提示标签：只显示当前动作，避免无用说明和省略号。
        tag_w, tag_h = 210, 34
        short_title = guide.get("title", "请按提示操作")
        if "：" in short_title:
            short_title = short_title.split("：", 1)[1]
        if target.centerx < WIDTH * 0.5:
            tag = pygame.Rect(min(target.right + 16, WIDTH - tag_w - 22), target.y + 2, tag_w, tag_h)
        else:
            tag = pygame.Rect(max(252, target.left - tag_w - 16), target.y + 2, tag_w, tag_h)
        # 避开顶部状态栏和底部工程控制台。
        tag.y = max(76, min(tag.y, HEIGHT - 176))
        # 如果标签仍然压到中心设备区上方，优先贴近目标上方或下方，而不是压到中央说明区。
        center_rect = pygame.Rect(279, 158, 834, 500)
        if tag.colliderect(center_rect):
            if target.top - tag_h - 14 >= center_rect.top:
                tag.y = target.top - tag_h - 14
            else:
                tag.y = min(center_rect.bottom - tag_h - 8, target.bottom + 10)
        rounded(self.screen, tag, (255, 252, 235), WARNING, 2, 10)
        rounded(self.screen, pygame.Rect(tag.x + 8, tag.y + 6, 54, 22), WARNING, WARNING, 1, 6)
        write_fit(self.screen, f"{guide.get('step', '')}", 10, WHITE,
                  pygame.Rect(tag.x + 11, tag.y + 8, 48, 17), align="center", min_size=8)
        write_fit(self.screen, short_title, 13, BLACK,
                  pygame.Rect(tag.x + 70, tag.y + 5, tag.width - 80, 24), bold=True, min_size=10)

        # 箭头从小标签指向目标中心。
        start_x = tag.left if target.centerx < tag.centerx else tag.right
        start = (start_x, tag.centery)
        end = target.center
        pygame.draw.line(self.screen, WARNING, start, end, 2)
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        arrow_len = 10
        p1 = (end[0] - arrow_len * math.cos(angle - 0.45), end[1] - arrow_len * math.sin(angle - 0.45))
        p2 = (end[0] - arrow_len * math.cos(angle + 0.45), end[1] - arrow_len * math.sin(angle + 0.45))
        pygame.draw.polygon(self.screen, WARNING, [end, p1, p2])

    def draw_stage_guide(self):
        if not self.stage_guide_open:
            return
        pages = STAGE_TUTORIALS[self.stage]
        page = pages[self.stage_guide_page]
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 24, 30, 125))
        self.screen.blit(overlay, (0, 0))
        rect = pygame.Rect(414, 178, 662, 535)
        self.stage_guide_rect = rect
        rounded(self.screen, rect, WHITE, BLUE, 2, 15)
        write(self.screen, f"阶段教程  {self.stage_guide_page + 1}/{len(pages)}", F14, TEXT_MUTED, (445, 203))
        write_fit(self.screen, page["title"], 27, BLUE, pygame.Rect(445, 238, 580, 42), bold=True, min_size=20)
        rounded(self.screen, pygame.Rect(445, 298, 598, 56), (239, 247, 252), (196, 218, 228), 1, 7)
        write(self.screen, "目标", F12, BLUE, (459, 308))
        write_fit(self.screen, page["goal"], 14, BLACK, pygame.Rect(500, 329, 525, 20), min_size=11)
        write(self.screen, "操作步骤", F15, BLACK, (445, 378))
        y = 410
        for index, line in enumerate(page["steps"], 1):
            pygame.draw.circle(self.screen, BLUE, (463, y + 10), 11)
            write(self.screen, str(index), F11, WHITE, (463, y + 10), "center")
            write_wrapped(self.screen, line, 14, BLACK, pygame.Rect(486, y, 530, 36), min_size=11, max_lines=2)
            y += 52
        rounded(self.screen, pygame.Rect(445, 566, 598, 52), (255, 249, 235), WARNING, 1, 7)
        write(self.screen, "提示", F12, WARNING, (459, 578))
        write_fit(self.screen, page["tip"], 12, TEXT_MUTED, pygame.Rect(500, 578, 525, 23), min_size=10)
        self.guide_prev = pygame.Rect(445, 647, 122, 39)
        self.guide_next = pygame.Rect(582, 647, 162, 39)
        self.guide_close = pygame.Rect(885, 647, 158, 39)
        rounded(self.screen, self.guide_prev, WHITE, BLUE, 1, 7)
        rounded(self.screen, self.guide_next, BLUE, BLUE, 1, 7)
        rounded(self.screen, self.guide_close, WHITE, TEXT_MUTED, 1, 7)
        write_fit(self.screen, "上一页", 14, BLUE, self.guide_prev.inflate(-8, -5), align="center", min_size=11)
        next_text = "进入操作" if self.stage_guide_page == len(pages) - 1 else "下一页"
        write_fit(self.screen, next_text, 14, WHITE, self.guide_next.inflate(-8, -5), align="center", min_size=11)
        write_fit(self.screen, "关闭教程", 14, TEXT_MUTED, self.guide_close.inflate(-8, -5), align="center", min_size=11)
        write_fit(self.screen, "也可按 Enter/Space/→ 继续，Esc 关闭教程", 11, TEXT_MUTED, pygame.Rect(445, 695, 598, 18), align="center", min_size=9)

    def objective_rows_for_stage(self, stage: Optional[int] = None, force_done: bool = False):
        """把真实玩法进度转换为右侧任务面板进度。

        剧本人员只负责写 objectives 文案；完成状态仍来自原游戏的拖拽、调试、启动、运行逻辑。
        """
        stage = self.stage if stage is None else stage
        script = get_stage_script(stage)
        scripted = script.get("objectives") or []

        if stage == 0:
            base = [(CIVIL[k].name, k in self.placed, "拖拽到中央蓝图对应槽位。")
                    for k in ("foundation", "containment", "turbine_hall", "cooling_base")]
        elif stage == 1:
            groups = [("反应堆组件", ("vessel", "core", "crdm"), "压力容器、堆芯、控制棒驱动机构按顺序安装。"),
                      ("常规发电系统", tuple(k for k, m in EQUIPMENT.items() if m.category == "常规"), "补齐传热、发电与冷源设备。"),
                      ("安全系统", ("diesel_a", "diesel_b", "spray", "efw"), "安全壳喷淋系统和辅助给水系统（ASG）都要配置。"),
                      ("辐射防护系统", PROTECTION_KEYS, "个人剂量、区域监测、排放监测等防护设备不能遗漏。")]
            base = []
            for label, keys, hint in groups:
                count = sum(k in self.placed for k in keys)
                base.append((f"{label}  {count}/{len(keys)}", count == len(keys), hint))
        elif stage == 2:
            base = [("管路冲洗", self.quiz["flush"] is True, "选择正确冲洗方向。"),
                    ("密封性试验", self.quiz["seal"] is True, "压力稳定、泄漏率合格。"),
                    ("A列电源试验", bool(self.quiz["diesel_a_test"]), "验证 A 列应急电源。"),
                    ("B列电源试验", bool(self.quiz["diesel_b_test"]), "验证 B 列应急电源。")]
        elif stage == 3:
            labels = [("装载燃料", "完成装料准备。"), ("确认控制棒棒位", "确认控制棒驱动机构状态。"),
                      ("主泵启动", "建立一回路流量。"), ("零功率物理试验", "验证反应堆物理参数。")]
            base = [(label, i < self.critical_step, hint) for i, (label, hint) in enumerate(labels)]
        else:
            base = [("稳定并网运行", self.runtime >= min(15, MISSION_TYPES[self.mission_key]["run_time"] * 0.5), "观察输出功率和累计运行时间。"),
                    ("处置运行异常", not self.fault and not self.warning_event, "黄色预警要尽早处理。"),
                    ("控制个人剂量", self.collective_dose < TEACHING_DOSE_REDLINE, "剂量分级：20 mSv 职业参考线，50 mSv 橙色警戒，100 mSv 事故教学红线。"),
                    ("完成挑战报告", self.challenge_finished or self.report, "点击结束挑战查看报告。")]

        rows = []
        for index, (label, done, hint) in enumerate(base):
            if index < len(scripted) and isinstance(scripted[index], dict):
                label = scripted[index].get("label", label)
                hint = scripted[index].get("hint", hint)
            rows.append((label, True if force_done else bool(done), hint))
        return rows

    def stage_progress_ratio(self, stage: Optional[int] = None) -> float:
        rows = self.objective_rows_for_stage(stage)
        if not rows:
            return 0.0
        return sum(1 for _, done, _ in rows if done) / len(rows)

    def site_choices(self) -> List[dict]:
        """第一关小地图只展示三种差异明显的厂址，避免信息过载。"""
        wanted = ("coast", "inland", "river")
        return [deepcopy(site) for key in wanted for site in SITE_TYPES if site.get("key") == key]

    def choose_site(self, site_key: str):
        for site in SITE_TYPES:
            if site.get("key") == site_key:
                self.site = deepcopy(site)
                self.site_selection_open = False
                feedback_lines = self.apply_site_parameter_effect(self.site)
                effect = self.site_effect_text(self.site)
                self.record_choice_effect("厂址选择｜" + self.site["name"], feedback_lines)
                self.log_event("site", "选择厂址：" + self.site["name"] + "｜" + effect, cause="site")
                goals = "；".join(g["name"] for g in self.side_goals)
                self.set_message(f"已选择{self.site['name']}：{effect}｜支线目标：{goals}", BLUE)
                self.show_banner("厂址确定", f"{self.site['name']}｜{effect}", BLUE, 3.6)
                self.audio.play("success")
                self.update_parameters(0)
                return
        self.set_message("厂址选项不存在，请选择界面上的厂址卡片。", WARNING)

    def site_effect_text(self, site: dict) -> str:
        delta = int(site.get("fund_delta", 0))
        cooling = float(site.get("cooling_bonus", 0))
        money_text = "资金不变" if delta == 0 else (f"资金+{delta}" if delta > 0 else f"资金{delta}")
        if cooling > 3:
            cool_text = "冷却水充足"
        elif cooling < -2:
            cool_text = "冷却水偏紧"
        else:
            cool_text = "冷却水稳定"
        return f"{cool_text}；{money_text}"


    def draw_site_selection_overlay(self):
        if not self.site_selection_open or self.menu:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((18, 30, 38, 125))
        self.screen.blit(overlay, (0, 0))
        rect = pygame.Rect(282, 104, 878, 590)
        rounded(self.screen, rect, WHITE, BLUE, 2, 18)
        write_fit(self.screen, "第一关｜全地图探索：选择核电厂址", 28, BLACK,
                  pygame.Rect(rect.x + 34, rect.y + 26, rect.width - 68, 42), bold=True, min_size=20)
        write_wrapped(self.screen, "不同厂址会影响资金、冷却水条件和后续运行预警倾向。选址后再开始拖拽建设。",
                      14, TEXT_MUTED, pygame.Rect(rect.x + 36, rect.y + 74, rect.width - 72, 42), min_size=11, max_lines=2)
        self.site_buttons = {}
        choices = self.site_choices()
        card_w, card_h = 258, 330
        gap = 22
        x0 = rect.x + 35
        y0 = rect.y + 140
        for index, site in enumerate(choices):
            card = pygame.Rect(x0 + index * (card_w + gap), y0, card_w, card_h)
            self.site_buttons[site["key"]] = card
            accent = DEEP_BLUE if site["key"] == "coast" else ORANGE if site["key"] == "inland" else GREEN
            rounded(self.screen, card, (247, 250, 251), accent, 2, 12)
            pygame.draw.rect(self.screen, (235, 244, 248), (card.x + 18, card.y + 18, card.width - 36, 92), border_radius=10)
            if site["key"] == "coast":
                pygame.draw.rect(self.screen, (116, 189, 222), (card.x + 28, card.y + 30, 94, 64), border_radius=8)
                pygame.draw.rect(self.screen, (225, 215, 158), (card.x + 116, card.y + 30, 108, 64), border_radius=8)
            elif site["key"] == "inland":
                pygame.draw.rect(self.screen, (226, 219, 182), (card.x + 28, card.y + 30, 196, 64), border_radius=8)
                pygame.draw.circle(self.screen, (143, 184, 118), (card.x + 76, card.y + 62), 23)
            else:
                pygame.draw.rect(self.screen, (226, 219, 182), (card.x + 28, card.y + 30, 196, 64), border_radius=8)
                pygame.draw.line(self.screen, (96, 174, 210), (card.x + 42, card.y + 82), (card.x + 214, card.y + 42), 12)
            write_fit(self.screen, site["name"], 21, accent,
                      pygame.Rect(card.x + 18, card.y + 124, card.width - 36, 30), bold=True, align="center", min_size=15)
            write_wrapped(self.screen, site["brief"], 12, BLACK,
                          pygame.Rect(card.x + 22, card.y + 164, card.width - 44, 66), min_size=10, max_lines=3, line_gap=18)
            effect = self.site_effect_text(site)
            effect_box = pygame.Rect(card.x + 20, card.y + 238, card.width - 40, 46)
            rounded(self.screen, effect_box, (255, 249, 235), WARNING, 1, 7)
            write_wrapped(self.screen, effect, 10, TEXT_MUTED,
                          pygame.Rect(effect_box.x + 10, effect_box.y + 8, effect_box.width - 20, effect_box.height - 12),
                          min_size=8, max_lines=2, line_gap=14)
            choose_btn = pygame.Rect(card.x + 55, card.bottom - 23, card.width - 110, 32)
            rounded(self.screen, choose_btn, accent, accent, 1, 7)
            write_fit(self.screen, "点击选择", 13, WHITE, choose_btn.inflate(-6, -3), align="center", min_size=10)
        write_fit(self.screen, "建议：第一次可以选临河厂址；想体验冷源挑战可选内陆厂址。", 12, TEXT_MUTED,
                  pygame.Rect(rect.x + 36, rect.bottom - 46, rect.width - 72, 20), align="center", min_size=10)


    def current_level_seconds(self) -> float:
        return max(0.0, (pygame.time.get_ticks() - getattr(self, "level_started_at", pygame.time.get_ticks())) / 1000.0)

    def current_stars(self) -> int:
        score = self.calculate_total_score() if hasattr(self, "calculate_total_score") else int((self.safety + self.protection_score) / 2)
        if score >= 90 and self.mistakes <= 1:
            return 3
        if score >= 75:
            return 2
        return 1

    def compact_challenge_module_list(self, names):
        """挑战模式右侧清单用短名，避免信息卡文字截断。"""
        mapping = {
            "核岛地基": "地基",
            "安全壳": "安全壳",
            "汽机厂房": "厂房",
            "取排水构筑物": "取排水",
            "压力容器": "压力容器",
            "堆芯": "堆芯",
            "控制棒驱动机构": "控制棒驱动",
            "稳压器": "稳压器",
            "蒸汽发生器": "SG",
            "主泵": "主泵",
            "汽轮机": "汽轮机",
            "发电机": "发电机",
            "冷凝器": "冷凝器",
            "给水泵": "给水泵",
            "循环冷却水系统（CRF）": "CRF",
            "循环水泵": "循环泵",
            "A列应急柴油机": "A列EDG",
            "B列应急柴油机": "B列EDG",
            "安全壳喷淋系统（EAS）": "EAS",
            "辅助给水系统（ASG）": "ASG",
            "生物屏蔽": "屏蔽",
            "区域辐射监测（KRT）": "KRT",
            "个人剂量系统": "剂量",
            "污染检查与去污站": "去污",
            "排放监测仪（ETY）": "ETY",
        }
        short = [mapping.get(str(name), str(name)) for name in names]
        return " / ".join(short[:5]) + (" …" if len(short) > 5 else "")

    def draw_stage_checklist(self):
        """右侧经营化二级菜单：统一字号、边距与卡片节距。"""
        x, width = RIGHT.x + 20, RIGHT.width - 40
        script = get_stage_script(self.stage)
        progress = self.stage_progress_ratio()
        guide = self.current_instruction()
        self.task_panel_buttons = {}

        write_fit(self.screen, "经营决策", 20, BLACK, pygame.Rect(x, 140, width, 30),
                  bold=True, min_size=15)

        status = pygame.Rect(x, 182, width, 146)
        status_color = DANGER if self.safety < 65 else WARNING if self.safety < 85 else GOOD
        status_fill = (255, 241, 240) if status_color == DANGER else (255, 249, 235) if status_color == WARNING else (234, 249, 240)
        rounded(self.screen, status, status_fill, status_color, 2, 12)
        rounded(self.screen, pygame.Rect(status.x + 14, status.y + 14, 68, 30), status_color, status_color, 1, 7)
        write_fit(self.screen, "状态", 13, WHITE, pygame.Rect(status.x + 18, status.y + 19, 60, 18),
                  align="center", bold=True, min_size=10)
        status_line = "高风险" if status_color == DANGER else "需关注" if status_color == WARNING else "稳定"
        write_fit(self.screen, status_line, 24 if status_color == DANGER else 22, status_color,
                  pygame.Rect(status.x + 92, status.y + 12, status.width - 108, 32),
                  bold=True, min_size=17)
        budget_label, budget_color, _ = self.budget_state() if hasattr(self, "budget_state") else ("正常", GOOD, "")
        style = self.strategy_style() if hasattr(self, "strategy_style") else "平衡型"
        write_fit(self.screen, style, 11, budget_color,
                  pygame.Rect(status.x + 92, status.y + 47, 92, 18), min_size=9)
        write_fit(self.screen, f"预算{budget_label}", 11, budget_color,
                  pygame.Rect(status.right - 94, status.y + 47, 80, 18), align="right", min_size=9)

        gold = (218, 161, 36)
        chip_data = [
            ("资", money(self.funds), gold if self.funds >= 0 else DANGER),
            ("防", str(self.safety), BLUE if self.safety >= 80 else WARNING),
        ]
        chip_x = status.x + 14
        chip_y = status.y + 76
        for label, value, color in chip_data:
            chip = pygame.Rect(chip_x, chip_y, 118, 26)
            rounded(self.screen, chip, WHITE, color, 1, 7)
            pygame.draw.circle(self.screen, color, (chip.x + 16, chip.centery), 8)
            write_fit(self.screen, label, 9, WHITE, pygame.Rect(chip.x + 8, chip.y + 6, 16, 14),
                      align="center", bold=True, min_size=7)
            write_fit(self.screen, value, 11, color, pygame.Rect(chip.x + 30, chip.y + 4, chip.width - 40, 18),
                      align="center", bold=True, min_size=8)
            chip_x += 128
        dose_color = GOOD if self.collective_dose < DOSE_REFERENCE_LINE else WARNING if self.collective_dose < DOSE_ORANGE_LINE else ORANGE if self.collective_dose < TEACHING_DOSE_REDLINE else DANGER
        dose_chip = pygame.Rect(status.x + 14, status.y + 110, status.width - 28, 24)
        rounded(self.screen, dose_chip, WHITE, dose_color, 1, 7)
        pygame.draw.circle(self.screen, dose_color, (dose_chip.x + 16, dose_chip.centery), 8)
        write_fit(self.screen, "剂", 9, WHITE, pygame.Rect(dose_chip.x + 8, dose_chip.y + 5, 16, 14),
                  align="center", bold=True, min_size=7)
        write_fit(self.screen, f"{self.collective_dose:.1f} / {TEACHING_DOSE_REDLINE:.0f} mSv", 11, dose_color,
                  pygame.Rect(dose_chip.x + 32, dose_chip.y + 4, dose_chip.width - 44, 16),
                  align="center", bold=True, min_size=8)

        event = pygame.Rect(x, 344, width, 144)
        rounded(self.screen, event, (255, 252, 244), WARNING, 2, 12)
        challenge_build = getattr(self, "play_mode", "") == "challenge" and self.stage in (0, 1)
        write_fit(self.screen, "本关清单" if challenge_build else "当前事件", 15, WARNING,
                  pygame.Rect(event.x + 14, event.y + 12, 100, 22), bold=True, min_size=12)
        if challenge_build:
            title = "自行规划"
            if self.stage == 0:
                names = [ALL_MODULES[k].name for k in CIVIL.keys()]
            else:
                keys = EQUIP_TABS.get(getattr(self, "active_tab", "反应堆"), list(EQUIPMENT.keys()))
                names = [ALL_MODULES[k].name for k in keys if k in EQUIPMENT]
            detail_text = self.compact_challenge_module_list(names)
            reason_text = "挑战：无答案提示、无高亮。"
        else:
            title = guide.get("title", script["title"])
            if "：" in title:
                title = title.split("：", 1)[1]
            detail_text = guide.get("detail", script["main_task"])
            reason_text = "原因：" + guide.get("why", "完成当前目标后进入下一阶段。")
        write_fit(self.screen, title, 20, BLACK, pygame.Rect(event.x + 14, event.y + 42, event.width - 28, 28),
                  bold=True, min_size=15)
        write_wrapped(self.screen, detail_text, 12, BLACK,
                      pygame.Rect(event.x + 14, event.y + 74, event.width - 28, 24),
                      min_size=10, max_lines=1, line_gap=12)
        write_wrapped(self.screen, reason_text,
                      11, TEXT_MUTED, pygame.Rect(event.x + 14, event.y + 104, event.width - 28, 28),
                      min_size=9, max_lines=2, line_gap=12)

        tab_y = 494
        tab_names = ("提示", "奖励", "数据", "系统")
        for i, mode in enumerate(tab_names):
            rect = pygame.Rect(x + i * 67, tab_y, 61, 30)
            self.task_panel_buttons[mode] = rect
            active = getattr(self, "task_detail_mode", "提示") == mode
            rounded(self.screen, rect, BLUE if active else WHITE, BLUE, 1, 6)
            write_fit(self.screen, mode, 12, WHITE if active else BLUE, rect.inflate(-6, -4),
                      align="center", min_size=9)

        detail = pygame.Rect(x, tab_y + 44, width, 250)
        rounded(self.screen, detail, (247, 250, 251), BORDER, 1, 8)
        mode = getattr(self, "task_detail_mode", "提示")
        if mode == "奖励":
            detail_lines = script.get("rewards") or ["完成本阶段后解锁下一阶段。"]
        elif mode == "数据":
            budget_label, _, budget_tip = self.budget_state() if hasattr(self, "budget_state") else ("正常", GOOD, "预算状态正常。")
            detail_lines = [
                f"进度：{int(progress * 100)}%",
                f"安全：{self.safety} / 防护：{self.protection_score}",
                f"资金：{money(self.funds)} / 剂量：{self.collective_dose:.1f}/{TEACHING_DOSE_REDLINE:.0f}",
                f"路线：{self.strategy_style() if hasattr(self, 'strategy_style') else '平衡型'} / 预算：{budget_label}",
            ]
        elif mode == "系统":
            detail_lines = [
                "一回路：堆芯→SG→主泵→堆芯",
                "二回路：SG→汽轮机→冷凝器→给水泵",
                "三回路：循环水→冷凝器→排海",
                "安全：RIS/ASG/EAS/EDG/KRT/ETY",
            ]
        else:
            if getattr(self, "play_mode", "") == "challenge" and self.stage in (0, 1):
                if self.stage == 0:
                    detail_lines = ["本关模块：地基 / 安全壳 / 厂房 / 取排水",
                                    "无推荐顺序；请自行判断。"]
                else:
                    keys = EQUIP_TABS.get(getattr(self, "active_tab", "反应堆"), [])
                    detail_lines = ["当前模块：" + self.compact_challenge_module_list([ALL_MODULES[k].name for k in keys if k in ALL_MODULES]),
                                    "切换标签查看全部设备。"]
            else:
                detail_lines = [guide.get("detail", ""), guide.get("why", "")]
        write_wrapped(self.screen, "\n".join(str(v) for v in detail_lines[:4]), 11, TEXT_MUTED,
                      pygame.Rect(detail.x + 14, detail.y + 14, detail.width - 28, detail.height - 24),
                      min_size=9, max_lines=6, line_gap=13)

    def toggle_level_map(self):
        """打开/关闭关卡地图。"""
        opening = not getattr(self, "level_map_open", False)
        if opening and hasattr(self, "close_transient_overlays"):
            self.close_transient_overlays(keep="level_map")
        self.level_map_open = opening
        if hasattr(self, "level_manager"):
            self.level_manager.map_open = self.level_map_open
        self.audio.play("click")

    def stage_map_status(self, index: int) -> str:
        if hasattr(self, "level_manager"):
            return self.level_manager.status(index)
        if index < self.stage:
            return "已完成"
        if index == self.stage:
            return "当前关"
        return "未解锁"

    def draw_level_map_overlay(self):
        """关卡地图：展示总流程、星级、证书和当前所在位置。"""
        if not getattr(self, "level_map_open", False):
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 24, 30, 150))
        self.screen.blit(overlay, (0, 0))
        box = pygame.Rect(212, 96, 1058, 706)
        self.level_map_rect = box
        rounded(self.screen, box, WHITE, BLUE, 2, 18)
        write_fit(self.screen, "关卡地图｜从选址到并网", 28, BLACK,
                  pygame.Rect(box.x + 34, box.y + 28, 520, 42), bold=True, min_size=20)
        write_fit(self.screen, "查看当前进度、已获资质章和下一关目标。按 M 或 Esc 关闭。", 13, TEXT_MUTED,
                  pygame.Rect(box.x + 34, box.y + 71, 740, 22), min_size=10)

        self.level_map_close = pygame.Rect(box.right - 134, box.y + 30, 96, 36)
        rounded(self.screen, self.level_map_close, WHITE, TEXT_MUTED, 1, 8)
        write_fit(self.screen, "关闭地图", 13, TEXT_MUTED, self.level_map_close.inflate(-8, -5),
                  align="center", min_size=10)

        # 路线节点
        node_y = box.y + 158
        left = box.x + 82
        gap = 218
        for i in range(len(STAGE_NAMES)):
            script = get_stage_script(i)
            cx = left + i * gap
            status = self.stage_map_status(i)
            if status == "已完成":
                color, fill = GOOD, (234, 249, 240)
            elif status == "当前关":
                color, fill = WARNING, (255, 249, 235)
            else:
                color, fill = TEXT_MUTED, (247, 250, 251)
            if i < len(STAGE_NAMES) - 1:
                line_color = GOOD if i < self.stage else GRID
                pygame.draw.line(self.screen, line_color, (cx + 42, node_y), (cx + gap - 42, node_y), 5)
            pygame.draw.circle(self.screen, fill, (cx, node_y), 48)
            pygame.draw.circle(self.screen, color, (cx, node_y), 48, 3)
            label = "已" if status == "已完成" else "现" if status == "当前关" else "锁"
            write_fit(self.screen, label, 24, color, pygame.Rect(cx - 28, node_y - 29, 56, 42),
                      align="center", min_size=18)
            write_fit(self.screen, status, 11, color, pygame.Rect(cx - 50, node_y + 14, 100, 20),
                      align="center", min_size=9)
            write_fit(self.screen, script.get("chapter", f"第{i+1}关"), 11, BLACK if i <= self.stage else TEXT_MUTED,
                      pygame.Rect(cx - 86, node_y + 63, 172, 22), align="center", min_size=8)
            stars = self.level_manager.stars_for(i) if hasattr(self, "level_manager") else (self.current_stars() if i < self.stage else 0)
            write_fit(self.screen, "★" * stars + "☆" * (3 - stars), 13, WARNING if stars else BORDER,
                      pygame.Rect(cx - 56, node_y + 88, 112, 22), align="center", min_size=10)

        detail = pygame.Rect(box.x + 52, box.y + 328, box.width - 104, 252)
        rounded(self.screen, detail, (247, 250, 251), BORDER, 1, 12)
        current = get_stage_script(self.stage)
        write_fit(self.screen, f"当前：{current.get('chapter', '')}｜{current.get('title', '')}", 19, BLUE,
                  pygame.Rect(detail.x + 24, detail.y + 22, detail.width - 48, 28), bold=True, min_size=13)
        write_wrapped(self.screen, "主线任务：" + current.get("main_task", "完成当前阶段目标。"), 13, BLACK,
                      pygame.Rect(detail.x + 24, detail.y + 64, detail.width - 48, 42), min_size=10, max_lines=2)

        write(self.screen, "当前目标", F14, BLACK, (detail.x + 24, detail.y + 126))
        yy = detail.y + 154
        for idx, (label, done, hint) in enumerate(self.objective_rows_for_stage(self.stage)[:4], 1):
            color = GOOD if done else WARNING if idx == 1 else TEXT_MUTED
            marker = "已" if done else "现" if idx == 1 else "待"
            write_fit(self.screen, marker + " " + label, 12, color, pygame.Rect(detail.x + 24, yy, 300, 18), min_size=9)
            write_fit(self.screen, hint, 10, TEXT_MUTED, pygame.Rect(detail.x + 338, yy, 560, 18), min_size=8)
            yy += 25

        badge = current.get("license_badge", "当前资质章")
        badge_rect = pygame.Rect(detail.right - 220, detail.y + 126, 175, 72)
        rounded(self.screen, badge_rect, (255, 249, 235), WARNING, 2, 22)
        write_fit(self.screen, "本关资质章", 11, WARNING, pygame.Rect(badge_rect.x + 12, badge_rect.y + 12, badge_rect.width - 24, 18),
                  align="center", min_size=8)
        write_fit(self.screen, badge, 12, WARNING, pygame.Rect(badge_rect.x + 16, badge_rect.y + 36, badge_rect.width - 32, 22),
                  align="center", min_size=8)

        footer = pygame.Rect(box.x + 52, box.bottom - 74, box.width - 104, 42)
        rounded(self.screen, footer, (239, 247, 252), BLUE, 1, 8)
        guide = self.current_instruction()
        next_title = guide.get("title", "按提示继续")
        if "：" in next_title:
            next_title = next_title.split("：", 1)[-1]
        write_fit(self.screen, "下一步：" + next_title, 14, BLUE, footer.inflate(-16, -7),
                  bold=True, min_size=10)

    def open_level_popup(self, completed_stage: int):
        if hasattr(self, "close_transient_overlays"):
            self.close_transient_overlays(keep="level_popup")
        script = get_stage_script(completed_stage)
        next_stage = min(completed_stage + 1, len(STAGE_NAMES) - 1)
        if hasattr(self, "level_manager"):
            self.level_manager.record_completion(completed_stage, self.current_stars(), script.get("license_badge", ""), script.get("rewards", []))
        self.level_popup = {"completed_stage": completed_stage, "next_stage": next_stage, "script": script,
                            "elapsed": self.current_level_seconds()}
        self.level_popup_continue = pygame.Rect(0, 0, 0, 0)

    def close_level_popup(self):
        self.level_popup = None
        self.level_popup_rect = pygame.Rect(0, 0, 0, 0)
        self.level_popup_continue = pygame.Rect(0, 0, 0, 0)
        self.level_started_at = pygame.time.get_ticks()
        self.stage_guide_open = False
        self.stage_guide_page = 0
        if hasattr(self, "clear_pointer_state"):
            self.clear_pointer_state()

    def draw_level_popup(self):
        """关卡完成弹窗：只保留结果、核心奖励和下一关入口。

        详细目标、完整复盘、专业依据移到结算页和关卡地图，避免弹窗拥挤。
        """
        if not self.level_popup:
            return
        popup = self.level_popup
        script = popup["script"]
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 24, 30, 150))
        self.screen.blit(overlay, (0, 0))

        rect = pygame.Rect(340, 118, 800, 620)
        self.level_popup_rect = rect
        rounded(self.screen, rect, WHITE, GOOD, 2, 18)

        # 顶部：状态 + 关卡名，两行显示，避免横向挤压。
        rounded(self.screen, pygame.Rect(rect.x + 34, rect.y + 28, 124, 34), GOOD, GOOD, 1, 9)
        write_fit(self.screen, "关卡完成", 15, WHITE,
                  pygame.Rect(rect.x + 43, rect.y + 34, 106, 22), align="center", bold=True, min_size=12)
        write_fit(self.screen, script["chapter"], 13, BLUE,
                  pygame.Rect(rect.x + 176, rect.y + 31, rect.width - 210, 24), min_size=10)
        write_wrapped(self.screen, script["title"], 25, BLACK,
                      pygame.Rect(rect.x + 34, rect.y + 80, rect.width - 68, 54),
                      bold=True, min_size=18, max_lines=2, line_gap=28)

        # 结果卡：星级与关键状态分离，避免把四项指标塞在一行。
        stars = self.current_stars()
        grade = "卓越" if stars == 3 else "合格" if stars == 2 else "待改进"
        stat = pygame.Rect(rect.x + 34, rect.y + 154, rect.width - 68, 116)
        rounded(self.screen, stat, (255, 249, 235), WARNING, 2, 12)
        write_fit(self.screen, "本关评价", 14, WARNING,
                  pygame.Rect(stat.x + 22, stat.y + 16, 110, 24), bold=True, min_size=11)
        write_fit(self.screen, "★" * stars + "☆" * (3 - stars), 34, WARNING,
                  pygame.Rect(stat.x + 22, stat.y + 50, 170, 44), align="center", bold=True, min_size=26)
        write_fit(self.screen, grade, 24, GOOD if stars >= 2 else DANGER,
                  pygame.Rect(stat.x + 220, stat.y + 40, 105, 38), align="center", bold=True, min_size=18)
        metric_lines = [
            f"用时 {popup.get('elapsed', self.current_level_seconds()):.0f}s",
            f"资金 {self.funds:.0f}币",
            f"安全 {self.safety}/100",
            f"防护 {self.protection_score}/100",
        ]
        mx = stat.x + 360
        for i, item in enumerate(metric_lines):
            write_fit(self.screen, item, 13, BLACK,
                      pygame.Rect(mx, stat.y + 18 + i * 23, stat.width - 385, 20), min_size=10)

        # 核心完成信息：只显示一句，不展开所有目标。
        done_box = pygame.Rect(rect.x + 34, rect.y + 296, rect.width - 68, 76)
        rounded(self.screen, done_box, (234, 249, 240), GOOD, 1, 9)
        write_fit(self.screen, "完成要点", 14, GOOD,
                  pygame.Rect(done_box.x + 18, done_box.y + 12, 110, 24), bold=True, min_size=11)
        msg = script.get("success_message", "本阶段关键目标已完成。")
        write_wrapped(self.screen, msg, 13, BLACK,
                      pygame.Rect(done_box.x + 18, done_box.y + 40, done_box.width - 36, 22),
                      min_size=10, max_lines=1)

        # 下一关预告：只保留下一关标题与一个短目标。
        next_script = get_stage_script(popup["next_stage"])
        next_box = pygame.Rect(rect.x + 34, rect.y + 392, rect.width - 68, 116)
        self.level_popup_next_box = next_box
        rounded(self.screen, next_box, (239, 247, 252), BLUE, 1, 9)
        write_fit(self.screen, "下一关", 14, BLUE,
                  pygame.Rect(next_box.x + 18, next_box.y + 12, 76, 24), bold=True, min_size=11)
        write_fit(self.screen, next_script["chapter"] + "｜" + next_script["title"], 14, BLACK,
                  pygame.Rect(next_box.x + 106, next_box.y + 12, next_box.width - 124, 24), bold=True, min_size=11)
        write_wrapped(self.screen, next_script["main_task"], 12, TEXT_MUTED,
                      pygame.Rect(next_box.x + 18, next_box.y + 48, next_box.width - 36, 48),
                      min_size=10, max_lines=2, line_gap=15)

        self.level_popup_continue = pygame.Rect(rect.right - 226, rect.bottom - 72, 190, 44)
        rounded(self.screen, self.level_popup_continue, BLUE, BLUE, 2, 9)
        button_text = "进入下一关" if popup.get("completed_stage", 0) < len(STAGE_NAMES) - 1 else "关闭"
        write_fit(self.screen, button_text, 16, WHITE, self.level_popup_continue.inflate(-10, -6),
                  align="center", min_size=12)
