# -*- coding: utf-8 -*-
"""由 gameplay.py 拆分出的模块。

本文件只存放一类玩法逻辑，避免单个 gameplay.py 过大。
"""

import pygame

from .theme import *
from .catalog import *
from .story_data import STORY_STAGE_NAMES

STAGE_NAMES = STORY_STAGE_NAMES

COMMISSIONING_ORDER = ["flush", "seal", "diesel_a_test", "diesel_b_test"]
COMMISSIONING_LABELS = {
    "flush": "管路冲洗",
    "seal": "密封性试验",
    "diesel_a_test": "A列电源试验",
    "diesel_b_test": "B列电源试验",
}
COMMISSIONING_TOOL_NAMES = {
    "flush": "冲洗泵车",
    "seal": "压力试验仪",
    "diesel_a_test": "A列试验电缆",
    "diesel_b_test": "B列试验电缆",
}

CRITICAL_ORDER = ["fuel_load", "rod_check", "pump_start", "zero_power_test"]
CRITICAL_LABELS = {
    "fuel_load": "装载燃料",
    "rod_check": "确认控制棒棒位",
    "pump_start": "启动主泵",
    "zero_power_test": "零功率物理试验",
}
CRITICAL_TOOL_NAMES = {
    "fuel_load": "燃料吊具",
    "rod_check": "棒位校验器",
    "pump_start": "主泵启动盘",
    "zero_power_test": "中子计数仪",
}
CRITICAL_OPTIONS = {
    "fuel_load": [("低速分区装载", True), ("快速一次装入", False)],
    "rod_check": [("全插/全提出校验", True), ("跳过棒位核对", False)],
    "pump_start": [("低速升流启动", True), ("满速冲击启动", False)],
    "zero_power_test": [("分步临界测量", True), ("直接提升功率", False)],
}
CRITICAL_FEEDBACK = {
    "fuel_load": ("剂量 +0.05", "燃料装载完成"),
    "rod_check": ("安全 +1", "棒位校验通过"),
    "pump_start": ("一回路流量 +1.0%", "主泵低速升流完成"),
    "zero_power_test": ("调试质量 +1", "零功率物理试验完成"),
}


class CommissioningMixin:
    def proceed_stage(self):
        completed_stage = self.stage
        advanced = False
        if self.stage == 0:
            if self.civil_complete():
                self.stage = 1
                self.active_tab = "反应堆"
                if self.is_starter_mode():
                    self.set_message("土建验收完成。开始安装反应堆、常规系统和安全设施。", GOOD)
                else:
                    self.set_message("土建验收完成。开始安装反应堆、常规系统、安全与防护设施。", GOOD)
                advanced = True
            else:
                self.penalty(2, "土建验收未通过：需要完成全部建筑模块。")
        elif self.stage == 1:
            if not self.equipment_complete():
                missing = [m.name for k, m in EQUIPMENT.items()
                           if m.category not in ("安全", "防护") and k not in self.placed]
                self.penalty(3, "设备验收未通过，缺少：" + "、".join(missing[:4]) + ("等。" if len(missing) > 4 else "。"))
            elif not self.safety_complete():
                self.penalty(15, "安全检查失败：必须配置两列应急供电、安全壳喷淋系统和辅助给水系统（ASG）。")
            elif not self.protection_complete():
                missing = "、".join(self.missing_protection_names())
                self.reduce_protection_score(8, "辐射防护配置不完整：" + missing + "。进入调试前需完成配置。")
            else:
                self.stage = 2
                self.selected_quiz = None
                self.commissioning_tool_ready = {key: False for key in COMMISSIONING_ORDER}
                if self.is_starter_mode():
                    self.set_message("设备与安全设施配置完成，进入系统调试。", GOOD)
                else:
                    self.set_message("设备、安全及防护设施配置完成，进入系统调试；装料前将进行防护专项验收。", GOOD)
                advanced = True
        elif self.stage == 2:
            if not self.quiz_complete():
                self.set_message("请按顺序完成调试操作链：选择任务 → 拖拽工具 → 确认结果。", WARNING)
            elif not self.protection_complete():
                self.reduce_protection_score(15, "装料前辐射防护验收失败：防护设备配置不完整。")
            else:
                self.protection_verified = True
                self.stage = 3
                self.critical_step = 0
                self.selected_critical = None
                self.critical_tool_ready = {key: False for key in CRITICAL_ORDER}
                self.critical_option_rects = []
                self.critical_tool_rects = {}
                if self.is_starter_mode():
                    self.set_message("调试验收通过：可以进入装料与临界教学步骤。", GOOD)
                else:
                    self.set_message("装料前辐射防护验收通过：屏蔽、监测、剂量管理和排放监测就绪。", GOOD)
                advanced = True
        elif self.stage == 3:
            if not self.protection_verified:
                self.reduce_protection_score(20, "未取得辐射防护验收许可，禁止装料与并网。")
            elif self.critical_step >= 4:
                self.stage = 4
                self.runtime = 0
                self.next_fault = self.first_warning_time()
                self.next_dose_task = self.first_dose_time()
                if self.is_starter_mode():
                    self.set_message("首次并网成功：接下来只练习一次基础预警处置。", GOOD)
                else:
                    self.set_message("首次并网成功：辐射监测已启用，注意完成运行剂量任务。", GOOD)
                advanced = True
            else:
                self.set_message("请严格按照左侧启动步骤依次完成操作。", WARNING)
        if advanced:
            if hasattr(self, "level_manager"):
                self.level_manager.set_current(self.stage)
            self.tip_index = 0
            self.save_checkpoint()
            self.audio.play("success")
            self.show_banner("阶段通过", f"已进入：{STAGE_NAMES[self.stage]}", GOOD, 2.8)
            self.stage_guide_open = False
            self.open_level_popup(completed_stage)

    def quiz_complete(self):
        return (self.quiz["flush"] is True and self.quiz["seal"] is True and
                self.quiz["diesel_a_test"] and self.quiz["diesel_b_test"])

    def commissioning_task_done(self, key: str) -> bool:
        if key in ("flush", "seal"):
            return self.quiz.get(key) is True
        return bool(self.quiz.get(key))

    def next_commissioning_key(self):
        for key in COMMISSIONING_ORDER:
            if not self.commissioning_task_done(key):
                return key
        return None

    def commissioning_target_rect(self, key: str) -> pygame.Rect:
        target_map = {
            "flush": "steam_gen",
            "seal": "containment",
            "diesel_a_test": "diesel_a",
            "diesel_b_test": "diesel_b",
        }
        module_key = target_map.get(key, "steam_gen")
        if module_key in ALL_MODULES:
            return ALL_MODULES[module_key].slot.copy()
        return pygame.Rect(520, 320, 140, 80)

    def select_commissioning_task(self, key: str):
        if key not in COMMISSIONING_ORDER:
            self.set_message("调试任务不存在。", WARNING)
            return
        if self.commissioning_task_done(key):
            self.set_message("该调试任务已合格，请继续下一项。", TEXT_MUTED)
            return
        expected = self.next_commissioning_key()
        if key != expected:
            expected_name = COMMISSIONING_LABELS.get(expected, "当前任务")
            self.penalty(2, f"调试顺序错误：请先完成“{expected_name}”。")
            self.commissioning_quality = max(70.0, float(getattr(self, "commissioning_quality", 100.0)) - 2.0)
            self.record_choice_effect("调试顺序错误", ["安全评分 -2", "调试质量 -2", "请按联锁顺序执行"])
            return
        self.selected_quiz = key
        self.commissioning_tool_ready.setdefault(key, False)
        self.set_message(f"已选择：{COMMISSIONING_LABELS[key]}。请拖拽“{COMMISSIONING_TOOL_NAMES[key]}”到中央高亮区域。", BLUE)
        self.audio.play("click")

    def start_commissioning_drag(self, key: str, pos):
        if key != getattr(self, "selected_quiz", None):
            self.set_message("请先在左侧选择当前调试任务。", WARNING)
            self.audio.play("warning")
            return
        rect = pygame.Rect(0, 0, 132, 42)
        rect.center = pos
        self.dragging = {
            "key": key,
            "rect": rect,
            "offset": (rect.width // 2, rect.height // 2),
            "commissioning": True,
            "start_pos": pos,
            "moved": True,
        }

    def finish_commissioning_drag(self, key: str):
        if key != getattr(self, "selected_quiz", None):
            self.set_message("当前调试工具与任务不匹配。", WARNING)
            self.audio.play("warning")
            return
        self.commissioning_tool_ready[key] = True
        self.spawn_feedback(self.commissioning_target_rect(key), GOOD)
        self.audio.play("success")
        if key in ("diesel_a_test", "diesel_b_test"):
            self.answer_quiz(key, True)
        else:
            self.set_message(f"{COMMISSIONING_TOOL_NAMES[key]}已就位，请在底部控制台确认调试结果。", GOOD)
            self.record_choice_effect("调试工具就位", [COMMISSIONING_LABELS[key], "下一步：确认结果"])

    def answer_quiz(self, key, correct):
        if key not in self.quiz:
            self.set_message("调试项目不存在，请按界面按钮操作。", WARNING)
            return
        expected = self.next_commissioning_key()
        if key != expected and not self.commissioning_task_done(key):
            expected_name = COMMISSIONING_LABELS.get(expected, "当前任务")
            self.penalty(2, f"调试顺序错误：请先完成“{expected_name}”。")
            return
        already_done = self.commissioning_task_done(key)
        if already_done:
            self.set_message("该调试项目已经合格，无需重复执行。", TEXT_MUTED)
            return
        if not getattr(self, "commissioning_tool_ready", {}).get(key, False):
            self.set_message(f"请先把“{COMMISSIONING_TOOL_NAMES[key]}”拖到中央高亮区域。", WARNING)
            self.audio.play("warning")
            return
        if key in ("flush", "seal"):
            if correct:
                self.quiz[key] = True
                self.days += 4
                self.commissioning_quality = min(105.0, float(getattr(self, "commissioning_quality", 100.0)) + 2.0)
                self.apply_parameter_delta("primary_flow", 0.4)
                self.apply_parameter_delta("condenser_pressure", -0.2)
                self.add_float_text("调试质量 +2", 1000, 176, GOOD)
                self.record_choice_effect("调试正确", ["调试质量 +2", "一回路流量 +0.4%", "冷凝器绝对压力 -0.2 kPa(a)"])
                self.log_event("commissioning", f"调试正确：{COMMISSIONING_LABELS[key]}，调试质量 {self.commissioning_quality:.0f}", cause="commissioning")
                self.audio.play("success")
                self.set_message("调试链完成：工具就位、结果判断正确，后续参数更稳定。", GOOD)
                self.selected_quiz = None
            else:
                self.quiz[key] = False
                self.days += 8
                self.commissioning_quality = max(65.0, float(getattr(self, "commissioning_quality", 100.0)) - 10.0)
                self.apply_parameter_delta("primary_flow", -0.8)
                self.apply_parameter_delta("condenser_pressure", 0.4)
                self.add_float_text("调试质量 -10", 1000, 176, DANGER)
                self.record_choice_effect("调试错误", ["调试质量 -10", "一回路流量 -0.8%", "冷凝器绝对压力 +0.4 kPa(a)"])
                self.log_event("commissioning", f"调试错误：{COMMISSIONING_LABELS[key]}，调试质量 {self.commissioning_quality:.0f}", cause="commissioning")
                self.penalty(5, "调试结果判断错误：工期增加，调试质量下降，后续运行裕度降低。")
                self.commissioning_tool_ready[key] = False
        elif key in ("diesel_a_test", "diesel_b_test"):
            self.quiz[key] = True
            self.days += 2
            self.commissioning_quality = min(105.0, float(getattr(self, "commissioning_quality", 100.0)) + 1.0)
            self.apply_parameter_delta("primary_flow", 0.2)
            self.add_float_text("调试质量 +1", 1000, 176, GOOD)
            self.record_choice_effect("应急电源试验合格", ["调试质量 +1", "外电源异常处置裕度提高"])
            self.log_event("commissioning", f"应急电源试验合格：{COMMISSIONING_LABELS[key]}", cause="commissioning")
            self.audio.play("success")
            self.set_message("应急供电列切换试验成功：后续外电源异常处置裕度提高。", GOOD)
            self.selected_quiz = None
        self.commissioning_tool_ready[key] = False

    def critical_task_done(self, key: str) -> bool:
        """装料与临界阶段：每个步骤必须完成“选择步骤 → 拖拽工具 → 判断操作”。"""
        try:
            index = CRITICAL_ORDER.index(key)
        except ValueError:
            return False
        return self.critical_step > index

    def next_critical_key(self):
        if self.critical_step < len(CRITICAL_ORDER):
            return CRITICAL_ORDER[self.critical_step]
        return None

    def critical_target_rect(self, key: str) -> pygame.Rect:
        target_map = {
            "fuel_load": "core",
            "rod_check": "crdm",
            "pump_start": "primary_pump",
            "zero_power_test": "vessel",
        }
        module_key = target_map.get(key, "vessel")
        if module_key in ALL_MODULES:
            return ALL_MODULES[module_key].slot.copy()
        return pygame.Rect(480, 255, 150, 90)

    def select_critical_task(self, key: str):
        if key not in CRITICAL_ORDER:
            self.set_message("启动步骤不存在，请按界面顺序操作。", WARNING)
            return
        if self.critical_task_done(key):
            self.set_message("该启动步骤已完成，请继续下一步。", TEXT_MUTED)
            return
        expected = self.next_critical_key()
        if key != expected:
            expected_name = CRITICAL_LABELS.get(expected, "当前步骤")
            self.penalty(3, f"启动联锁提示：请先完成“{expected_name}”。")
            self.apply_parameter_delta("primary_flow", -0.2)
            self.record_choice_effect("启动顺序误操作", ["安全评分 -3", "一回路流量 -0.2%", "按顺序完成联锁"])
            return
        self.selected_critical = key
        self.critical_tool_ready.setdefault(key, False)
        self.set_message(f"已选择：{CRITICAL_LABELS[key]}。请拖拽“{CRITICAL_TOOL_NAMES[key]}”到中央高亮区域。", BLUE)
        self.audio.play("click")

    def start_critical_drag(self, key: str, pos):
        if key != getattr(self, "selected_critical", None):
            self.set_message("请先在左侧选择当前启动步骤。", WARNING)
            self.audio.play("warning")
            return
        rect = pygame.Rect(0, 0, 132, 42)
        rect.center = pos
        self.dragging = {
            "key": key,
            "rect": rect,
            "offset": (rect.width // 2, rect.height // 2),
            "critical": True,
            "start_pos": pos,
            "moved": True,
        }

    def finish_critical_drag(self, key: str):
        if key != getattr(self, "selected_critical", None):
            self.set_message("当前启动工具与步骤不匹配。", WARNING)
            self.audio.play("warning")
            return
        self.critical_tool_ready[key] = True
        self.spawn_feedback(self.critical_target_rect(key), GOOD)
        self.audio.play("success")
        self.set_message(f"{CRITICAL_TOOL_NAMES[key]}已就位，请在底部控制台选择正确操作。", GOOD)
        self.record_choice_effect("启动工具就位", [CRITICAL_LABELS[key], "下一步：选择正确操作"])

    def answer_critical_option(self, key: str, correct: bool):
        if key not in CRITICAL_ORDER:
            self.set_message("启动步骤不存在，请按界面按钮顺序操作。", WARNING)
            return
        expected = self.next_critical_key()
        if key != expected:
            expected_name = CRITICAL_LABELS.get(expected, "当前步骤")
            self.penalty(3, f"启动联锁提示：请先完成“{expected_name}”。")
            return
        if not getattr(self, "critical_tool_ready", {}).get(key, False):
            self.set_message(f"请先把“{CRITICAL_TOOL_NAMES[key]}”拖到中央高亮区域。", WARNING)
            self.audio.play("warning")
            return
        if correct:
            self.critical_step += 1
            self.days += 1
            if key == "fuel_load":
                self.collective_dose += 0.05
                self.mark_param_change("个人剂量", WARNING)
                self.add_float_text("剂量 +0.05", 1010, 176, WARNING)
            elif key == "rod_check":
                self.safety = min(100, self.safety + 1)
                self.mark_param_change("安全评分", GOOD)
                self.add_float_text("安全 +1", 1010, 176, GOOD)
            elif key == "pump_start":
                self.apply_parameter_delta("primary_flow", 1.0)
            elif key == "zero_power_test":
                self.commissioning_quality = min(106.0, float(getattr(self, "commissioning_quality", 100.0)) + 1.0)
            effect, message = CRITICAL_FEEDBACK.get(key, ("启动条件确认", CRITICAL_LABELS[key] + "完成"))
            self.record_choice_effect("启动步骤正确", [message, effect])
            self.log_event("critical", f"启动步骤完成：{CRITICAL_LABELS[key]}", cause="critical")
            self.set_message(message + "。", GOOD)
            self.audio.play("success")
            self.selected_critical = None
            self.critical_tool_ready[key] = False
        else:
            self.days += 2
            self.safety = max(0, self.safety - 4)
            self.mistakes += 1
            self.critical_tool_ready[key] = False
            self.apply_parameter_delta("primary_flow", -0.4)
            self.mark_param_change("安全评分", DANGER)
            self.add_float_text("安全 -4", 1010, 176, DANGER)
            self.record_choice_effect("启动误操作", ["安全评分 -4", "工期 +2天", "一回路流量 -0.4%"])
            self.log_event("critical", f"启动误操作：{CRITICAL_LABELS[key]}", cause="critical")
            self.set_message("启动操作判断错误：联锁提示已触发，请重新拖拽工具后再确认。", WARNING)
            self.audio.play("warning")

    def critical_action(self, index):
        """兼容旧点击路径：点击步骤只负责选择，不直接完成。"""
        if index < 0 or index >= len(CRITICAL_ORDER):
            self.set_message("启动步骤不存在，请按界面按钮顺序操作。", WARNING)
            return
        self.select_critical_task(CRITICAL_ORDER[index])
