# -*- coding: utf-8 -*-
"""由 gameplay.py 拆分出的模块。

本文件只存放一类玩法逻辑，避免单个 gameplay.py 过大。
"""

import random
from typing import List, Optional

import pygame

from .theme import *
from .catalog import *
from .reference_content import accident_cases_for_event, accident_case_for_event, format_measures, accident_decision_options, accident_case_by_id
from .advanced_features import DERIVED_ACCIDENT_MAP
from .story_data import STORY_STAGE_NAMES
from .ui_helpers import write_fit, rounded
from .models import FaultEvent

STAGE_NAMES = STORY_STAGE_NAMES

class AccidentSystemMixin:
    def mark_accident_gallery(self, case: Optional[dict], state: str):
        """记录事故图鉴解锁状态：locked/unlocked/mastered/review。"""
        if not case:
            return
        case_id = case.get("id")
        if not isinstance(case_id, int):
            return
        gallery = getattr(self, "accident_gallery_state", None)
        if not isinstance(gallery, dict):
            self.accident_gallery_state = {i: "locked" for i in range(1, 21)}
            gallery = self.accident_gallery_state
        old = gallery.get(case_id, "locked")
        rank = {"locked": 0, "unlocked": 1, "review": 2, "mastered": 3}
        changed = False
        if rank.get(state, 0) >= rank.get(old, 0) or old == "locked":
            gallery[case_id] = state
            changed = old != state
        if changed and old == "locked" and state in ("unlocked", "review", "mastered"):
            self.show_banner("新事故已收录", f"事故 {case_id:02d}/20｜" + case.get("name", ""), BLUE, 3.0)
            self.log_event("atlas", f"事故图鉴收录：{case.get('name', '')}", cause=case.get("event_key", "safety"))
        mastered_count = sum(1 for i in range(1, 21) if gallery.get(i) == "mastered")
        title_map = {5: "见习运行员", 10: "事故处置员", 20: "运行安全官"}
        for count, title in title_map.items():
            if mastered_count >= count and title not in getattr(self, "achievements_unlocked", []):
                self.achievements_unlocked.append(title)
                self.show_banner("称号解锁", f"正确掌握 {count} 个事故｜{title}", GOOD, 4.0)
        if mastered_count >= 1 and getattr(self, "mistakes", 0) == 0 and "稳健运行专家" not in getattr(self, "achievements_unlocked", []):
            # 先收录成就，结算时若全程无错误会继续保留。
            self.achievements_unlocked.append("稳健运行专家")

    def set_derived_accident_from_case(self, case: Optional[dict]):
        if not case:
            return
        derived = DERIVED_ACCIDENT_MAP.get(case.get("id"))
        if derived:
            self.pending_derived_case_id = derived
            try:
                nxt = accident_case_by_id(derived)
                self.log_event("evolution", "事故演化预告：" + nxt.get("name", ""), cause=nxt.get("event_key", "safety"))
            except Exception:
                pass

    def pick_reference_accident_case(self, key: str) -> dict:
        """按当前事故类型选择一个资料事故案例，供事故卡和结算复盘使用。"""
        cases = accident_cases_for_event(key)
        if not cases:
            return accident_case_for_event(key)
        counter = int(getattr(self, "reference_accident_counter", 0))
        self.reference_accident_counter = counter + 1
        return cases[counter % len(cases)]

    def current_reference_accident_case(self) -> Optional[dict]:
        case = getattr(self, "active_reference_accident", None)
        if case:
            return case
        key = self.current_accident_key() if hasattr(self, "current_accident_key") else None
        if key:
            return accident_case_for_event(key)
        return None

    def diagnose_warning(self, choice: str):
        if not self.warning_event or self.diagnosis_resolved:
            return
        case = DIAGNOSTIC_CASES[self.warning_event["key"]]
        self.diagnosis_attempts += 1
        if choice == case["cause"]:
            self.diagnosis_resolved = True
            self.warning_left = min(self.warning_duration(), self.warning_left + 4.0)
            self.log_event("diagnosis", f"正确诊断：{choice}", cause=self.warning_event["key"])
            self.audio.play("success")
            self.set_message("诊断正确。现在请按照处置区域提示完成设备接入。", GOOD)
        else:
            self.warning_left = max(1.0, self.warning_left - 3.0)
            self.safety = max(0, self.safety - 3)
            self.mark_param_change("安全评分", DANGER)
            self.add_float_text("安全 -3", RIGHT.centerx, 184, DANGER)
            self.affect_barrier("safety", -3, "误诊导致安全系统响应延迟")
            self.log_event("diagnosis", f"误诊：选择了{choice}", cause=self.warning_event["key"])
            self.audio.play("warning")
            self.set_message("诊断不正确：参数仍在恶化，剩余处置时间减少。", DANGER)

    def review_case_key(self) -> str:
        for entry in reversed(self.event_log):
            if entry.get("cause") in REVIEW_LIBRARY:
                return entry["cause"]
            if entry.get("kind") == "dose":
                return "dose"
        return "general"

    def current_accident_key(self) -> Optional[str]:
        if self.warning_event:
            return self.warning_event["key"]
        if self.fault:
            return self.fault.key
        return None

    def answer_accident_choice(self, option_index: int):
        """事故处置判断题：正确后解锁实际处置，错误会造成明确后果。"""
        key = self.current_accident_key()
        if not key:
            return
        ref_case = self.current_reference_accident_case()
        options = accident_decision_options(key, ref_case) or ACCIDENT_DECISION_OPTIONS.get(key, [])
        if option_index < 0 or option_index >= len(options):
            return
        option = options[option_index]
        self.accident_choice_feedback = option.get("feedback", "")
        if option.get("correct"):
            self.mark_accident_gallery(ref_case, "mastered")
            self.accident_choice_resolved = True
            self.safety = min(100, self.safety + 1)
            if key == "vacuum":
                self.cooling_flow = max(float(getattr(self, "cooling_flow", 75.0)), 86.0)
            param = option.get("parameter")
            if param:
                self.apply_parameter_delta(param, option.get("delta", 0.0))
            if self.warning_event:
                self.warning_left = min(self.warning_duration(), self.warning_left + 3.0)
            elif self.fault:
                self.fault_left = min(self.fault.duration, self.fault_left + 2.0)
            self.affect_barrier({"vacuum": "fuel", "water": "primary", "power": "safety", "safety": "safety", "dose": "environment"}.get(key, "safety"), 1, "事故处置判断正确，屏障状态稳定")
            lines = [option.get("feedback", "")] + option.get("effects", [])
            if ref_case:
                lines.append("对应资料事故：" + ref_case.get("name", ""))
                lines.append("资料处置：" + format_measures(ref_case, 2))
            self.record_choice_effect("事故判断正确", lines, duration_ms=7600)
            self.set_message(option.get("feedback", "判断正确") + " 现在完成应急接入。", GOOD)
            self.audio.play("success")
            if hasattr(self, "mark_param_change"):
                self.mark_param_change({"vacuum": "冷凝器绝对压力", "water": "蒸汽发生器水位", "power": "一回路流量", "safety": "安全评分", "dose": "个人剂量"}.get(key, "安全评分"), GOOD)
        else:
            self.mark_accident_gallery(ref_case, "review")
            self.set_derived_accident_from_case(ref_case)
            if ref_case and ref_case.get("id") == 16:
                self.show_banner("事故链恶化", "由于 EDG 未能及时启动，后续更容易演化为 SBO。", DANGER, 4.0)
            elif ref_case:
                self.show_banner("事故链恶化", "错误处置会提高后续关联事故触发概率。", DANGER, 3.5)
            self.safety = max(0, self.safety - 5)
            self.funds -= 80
            self.mark_param_change("安全评分", DANGER)
            self.add_float_text("安全 -5", RIGHT.centerx, 184, DANGER)
            self.add_float_text("资金 -80", RIGHT.centerx, 214, DANGER)
            if self.warning_event:
                self.warning_left = max(1.0, self.warning_left - 4.0)
            elif self.fault:
                self.fault_left = max(1.0, self.fault_left - 3.0)
            param = option.get("parameter")
            if param:
                self.apply_parameter_delta(param, option.get("delta", 0.0))
            self.affect_barrier("safety", -4, "事故处置判断错误，安全系统响应被削弱")
            self.mistakes += 1
            lines = [option.get("feedback", "")] + option.get("effects", [])
            if ref_case:
                lines.append("对应资料事故：" + ref_case.get("name", ""))
            self.record_choice_effect("事故判断错误", lines, duration_ms=8200)
            self.set_message(option.get("feedback", "判断错误") + " 请重新选择处置方案。", DANGER)
            self.audio.play("warning")
            if hasattr(self, "mark_param_change"):
                self.mark_param_change("安全评分", DANGER)

    def open_review(self):
        if hasattr(self, "close_transient_overlays"):
            self.close_transient_overlays(keep="review")
        self.review_key = self.review_case_key()
        self.review_answer = None
        self.review_feedback = ""
        self.review_open = True
        self.audio.play("click")

    def answer_review(self, answer: str):
        case = REVIEW_LIBRARY[self.review_key]
        self.review_answer = answer
        if answer == case["answer"]:
            self.review_score = 100
            self.review_feedback = "判断正确：" + case["improvement"]
            self.audio.play("success")
        else:
            self.review_score = 45
            self.review_feedback = "正确答案：" + case["answer"] + "。改进建议：" + case["improvement"]
            self.audio.play("warning")

    def trigger_warning(self, forced_key: Optional[str] = None):
        keys = ["vacuum", "water", "power", "safety", "dose"]
        if forced_key in EVENT_RULES:
            key = forced_key
        else:
            if self.is_starter_mode():
                key = "vacuum"
            else:
                bias = self.site.get("warning_bias", "vacuum")
                quality = float(getattr(self, "commissioning_quality", 100.0))
                aggressive = self.route_count("激进") if hasattr(self, "route_count") else 0
                safe = self.route_count("安全") if hasattr(self, "route_count") else 0
                bias_chance = 0.48 if quality < 85 else 0.38
                complex_chance = 0.28 + aggressive * 0.06 - safe * 0.04
                if quality < 78 and random.random() < max(0.12, min(0.52, complex_chance)):
                    key = random.choice(["water", "power", "safety", "dose"])
                else:
                    key = bias if random.random() < bias_chance else random.choice(keys)
        derived_case = None
        if forced_key is None and getattr(self, "pending_derived_case_id", None):
            try:
                derived_case = accident_case_by_id(int(self.pending_derived_case_id))
                key = derived_case.get("event_key", key)
                self.pending_derived_case_id = None
            except Exception:
                derived_case = None
        rule = EVENT_RULES[key]
        case = DIAGNOSTIC_CASES[key]
        self.active_reference_accident = derived_case or self.pick_reference_accident_case(key)
        self.mark_accident_gallery(self.active_reference_accident, "unlocked")
        display_title = rule["warning"] if self.is_guided_mode() else "黄色预警：运行参数趋势异常"
        self.warning_event = {"key": key, "title": display_title, "rule": rule, "symptoms": case["symptoms"]}
        self.warning_left = self.warning_duration()
        self.operation_done = []
        self.diagnosis_resolved = self.is_guided_mode()
        self.diagnosis_attempts = 0
        self.accident_choice_resolved = False
        self.accident_choice_feedback = ""
        self.dashboard_page = "status"
        self.audio.play("warning")
        if self.is_starter_mode():
            self.show_banner("基础预警练习", "冷凝器绝对压力升高（真空变差）｜把冷却流量调到 85% 以上", WARNING)
            self.set_message("基础预警：请拖动右侧冷却水滑块到 85% 以上。", WARNING)
        elif self.is_guided_mode():
            self.show_banner("黄色预警", rule["warning"].replace("黄色预警：", "") + "｜倒计时内处理可避免升级", WARNING)
            self.set_message("事故链一级预警：" + rule["guide"] + " 倒计时结束将升级为红色故障。", WARNING)
        else:
            self.show_banner("参数异常", "请根据趋势与症状先判断原因", WARNING)
            self.set_message("挑战模式：异常原因已隐藏，请查看症状/趋势并在左侧完成诊断。", WARNING)
        ref_case = getattr(self, "active_reference_accident", None)
        if ref_case:
            self.record_choice_effect("资料事故触发", [f"{ref_case['category']}：{ref_case['name']}", "现象：" + ref_case['phenomenon'][:42]], duration_ms=6200)
        self.log_event("warning", display_title, cause=key)

    def event_required_tools(self) -> List[str]:
        if self.warning_event:
            key = self.warning_event.get("key")
            rule = self.warning_event.get("rule") or EVENT_RULES.get(key, {})
            return list(rule.get("tools", []))
        if self.fault:
            return list(EVENT_RULES.get(self.fault.key, {}).get("tools", []))
        return []

    def event_next_tool(self) -> Optional[str]:
        for tool in self.event_required_tools():
            if tool not in self.operation_done:
                return tool
        return None

    def escalate_warning(self):
        if not self.warning_event:
            return
        key = self.warning_event["key"]
        rule = EVENT_RULES[key]
        damage_map = {"vacuum": ("fuel", -7), "water": ("primary", -9), "power": ("safety", -13), "safety": ("safety", -14), "dose": ("environment", -12)}
        barrier_key, damage = damage_map[key]
        self.affect_barrier(barrier_key, damage, "黄色预警未及时解除，屏障完整性下降")
        self.fault = FaultEvent(rule["fault"], rule["guide"], "拖拽应急设备到目标槽位",
                                self.fault_duration(), rule["penalty"], key)
        self.fault_left = self.fault.duration
        self.warning_event = None
        self.diagnosis_resolved = True
        self.accident_choice_resolved = False
        self.accident_choice_feedback = ""
        self.dashboard_page = "status"
        self.audio.play("alarm")
        self.show_banner("红色故障", rule["fault"].replace("红色故障：", ""), DANGER, 5.0)
        self.set_message("事故链二级故障：预警未解除，已升级为红色故障；倒计时结束将自动停堆。" + rule["guide"], DANGER)
        self.log_event("fault", rule["fault"], cause=key)

    def clear_operating_event(self, from_warning: bool):
        key = self.warning_event["key"] if self.warning_event else self.fault.key
        rule = EVENT_RULES[key]
        reward = 80 if from_warning else 35
        barrier_map = {"vacuum": "fuel", "water": "primary", "power": "safety", "safety": "safety", "dose": "environment"}
        if from_warning:
            self.safety = min(100, self.safety + 1)
            self.protection_score = min(100, self.protection_score + 1)
            self.affect_barrier(barrier_map[key], 1, "预警阶段及时纠正，屏障保持稳定")
            if key == "vacuum":
                self.apply_parameter_delta("condenser_pressure", -0.7)
                self.cooling_flow = max(self.cooling_flow, 86.0)
            elif key == "water":
                self.apply_parameter_delta("sg_level", 2.5)
            elif key == "power":
                self.apply_parameter_delta("primary_flow", 1.8)
            elif key == "safety":
                self.protection_score = min(100, self.protection_score + 2)
            elif key == "dose":
                self.collective_dose = max(0.0, self.collective_dose - 0.2)
            self.record_choice_effect("预警处置成功", ["安全评分 +1", "防护评分 +1", "相关参数恢复更明显"])
            if hasattr(self, "mark_param_change"):
                self.mark_param_change("冷凝器绝对压力", GOOD)
                self.mark_param_change("安全评分", GOOD)
        else:
            self.affect_barrier(barrier_map[key], 2, "故障处置完成，屏障状态部分恢复")
            if key == "vacuum":
                self.apply_parameter_delta("condenser_pressure", -0.25)
            elif key == "water":
                self.apply_parameter_delta("sg_level", 1.0)
            elif key == "power":
                self.apply_parameter_delta("primary_flow", 0.7)
            elif key == "safety":
                self.protection_score = min(100, self.protection_score + 1)
            elif key == "dose":
                self.collective_dose = max(0.0, self.collective_dose - 0.1)
            self.record_choice_effect("故障处置完成", ["屏障状态部分恢复", "参数恢复较预警阶段偏弱"])
            if hasattr(self, "mark_param_change"):
                self.mark_param_change("安全评分", WARNING)
        self.funds += reward
        self.add_float_text(f"资金 +{reward}", RIGHT.centerx, 184, GOOD)
        self.mark_param_change("安全评分", GOOD if from_warning else WARNING)
        choice_was_resolved = bool(getattr(self, "accident_choice_resolved", False))
        self.last_reference_accident = getattr(self, "active_reference_accident", None)
        if choice_was_resolved:
            self.mark_accident_gallery(self.last_reference_accident, "mastered")
        self.warning_event = None
        self.fault = None
        self.operation_done = []
        self.diagnosis_resolved = True
        self.accident_choice_resolved = False
        self.accident_choice_feedback = ""
        self.active_reference_accident = None
        self.audio.play("success")
        status = "预警" if from_warning else "故障"
        self.show_banner("处置成功", f"{rule['fault'].replace('红色故障：', '')}已恢复", GOOD, 3.0)
        self.set_message(f"{status}处置完成：{rule['fault'].replace('红色故障：', '')}已恢复，奖励资金 {reward}。", GOOD)
        self.log_event("resolution", status + "处置成功", cause=key)

    def activate_operation_tool(self, tool_key: str):
        if self.warning_event and not self.diagnosis_resolved:
            self.set_message("请先根据参数症状完成诊断，再进行应急接入。", WARNING)
            return
        if not getattr(self, "accident_choice_resolved", False):
            self.set_message("请先在事故卡中选择处置方案，系统会显示正确/错误后果。", WARNING)
            self.audio.play("warning")
            return
        next_tool = self.event_next_tool()
        if not next_tool:
            return
        if tool_key != next_tool:
            self.penalty(5, "应急操作顺序错误，请按目标顺序重新拖拽。")
            self.affect_barrier("safety", -2, "应急操作顺序错误")
            self.apply_parameter_delta("primary_flow", -0.4)
            self.record_choice_effect("错误处置", ["安全评分 -5", "一回路流量 -0.4%", "屏障完整性下降"])
            return
        required = RUN_OPERATION_TOOLS[tool_key]["requires"]
        if required not in self.placed:
            self.penalty(12, "建设阶段未配置对应备用系统，处置无法完成。")
            self.affect_barrier("safety", -10, "备用系统未配置，安全系统可用性下降")
            return
        self.operation_done.append(tool_key)
        self.spawn_feedback(RUN_OPERATION_TOOLS[tool_key]["target"], GOOD)
        self.add_float_text("接入完成", RUN_OPERATION_TOOLS[tool_key]["target"].centerx, RUN_OPERATION_TOOLS[tool_key]["target"].y - 10, GOOD)
        if self.event_next_tool() is None:
            self.clear_operating_event(self.warning_event is not None)
        else:
            self.set_message("第一步已完成，请继续拖入：" +
                             RUN_OPERATION_TOOLS[self.event_next_tool()]["name"] + "。", WARNING)

    def start_operation_drag(self, tool_key: str, pos):
        rect = pygame.Rect(0, 0, 118, 42)
        rect.center = pos
        self.dragging = {
            "key": tool_key, "rect": rect,
            "offset": (rect.width // 2, rect.height // 2),
            "operation": True
        }

    def draw_operation_targets(self):
        if self.stage != 4 or (not self.warning_event and not self.fault):
            return
        if self.warning_event and not self.diagnosis_resolved:
            return
        for tool in self.event_required_tools():
            data = RUN_OPERATION_TOOLS[tool]
            rect = data["target"]
            complete = tool in self.operation_done
            current = tool == self.event_next_tool()
            color = GOOD if complete else (DANGER if self.fault and current else WARNING)
            blink = int(pygame.time.get_ticks() / 280) % 2 == 0
            fill = (235, 249, 240) if complete else ((255, 246, 224) if current and blink else (248, 250, 251))
            rounded(self.screen, rect, fill, color, 2 if current else 1, 7)
            label = "已接入" if complete else data["target_name"]
            write_fit(self.screen, label, 11, color, rect.inflate(-8, -5), align="center", min_size=9)

    def fail_fault(self, reason: str):
        if not self.fault:
            return
        key = self.fault.key
        loss = self.fault.penalty
        barrier_map = {"vacuum": "fuel", "water": "primary", "power": "safety", "safety": "safety", "dose": "environment"}
        self.safety = max(0, self.safety - loss)
        self.affect_barrier(barrier_map[key], -20, "故障超时导致自动停堆")
        self.slider_drag = False
        self.dragging = None
        self.audio.play("alarm")
        self.show_banner("自动停堆", f"{reason}｜安全评分 -{loss}", DANGER, 5.0)
        self.set_message(f"{reason} 安全评分 -{loss}，机组自动停堆。", DANGER)
        self.log_event("scram", "故障未处置导致自动停堆", cause=key)
        self.last_reference_accident = getattr(self, "active_reference_accident", None)
        if getattr(self, "accident_choice_resolved", False):
            self.mark_accident_gallery(self.last_reference_accident, "mastered")
        self.active_reference_accident = None
        self.fault = None
        self.scrammed = True

