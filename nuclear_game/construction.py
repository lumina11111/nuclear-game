# -*- coding: utf-8 -*-
"""由 gameplay.py 拆分出的模块。

本文件只存放一类玩法逻辑，避免单个 gameplay.py 过大。
"""

import random
from typing import Dict, List, Optional, Tuple

import pygame

from .theme import *
from .catalog import *
from .story_data import STORY_STAGE_NAMES
from .models import Module
from .ui_helpers import clamp

STAGE_NAMES = STORY_STAGE_NAMES

class ConstructionMixin:
    def is_starter_mode(self) -> bool:
        return self.play_mode == "starter"

    def next_install_key(self) -> Optional[str]:
        if self.stage == 0:
            order = ["foundation", "containment", "turbine_hall", "cooling_base"]
        elif self.stage == 1:
            order = ["vessel", "core", "crdm", "pressurizer", "steam_gen", "primary_pump",
                     "turbine", "generator", "condenser", "secondary_pump", "cooling",
                     "tertiary_pump", "diesel_a", "diesel_b", "spray", "efw"]
            if not self.is_starter_mode():
                order += list(PROTECTION_KEYS)
        else:
            return None
        return next((key for key in order if key not in self.placed), None)

    def recommended_work_plan(self) -> dict:
        if not self.dose_task:
            return {"route": None, "staff": None, "equipment": None}
        recommended = {
            "speed": {"route": "near", "staff": "rp_team", "equipment": "dosimeter"},
            "dose": {"route": "shield_corridor", "staff": "robot_operator", "equipment": "temp_shield"},
            "economy": {"route": "shield_corridor", "staff": "maintainer", "equipment": "dosimeter"},
        }
        return recommended[self.dose_task["priority"]].copy()

    def apply_recommended_plan(self):
        if not self.dose_task:
            return
        self.work_plan_selection = self.recommended_work_plan()
        self.audio.play("click")
        self.set_message("已应用推荐方案；请检查预计剂量、耗时与经济影响后执行。", BLUE)

    def generate_side_goals(self) -> List[dict]:
        if self.is_starter_mode():
            return []
        pool = list(GOAL_POOL)
        # 根据主任务固定带入一个更贴合的目标，其余随机抽取。
        forced = {
            "protection": "low_dose",
            "economy": "rich_finish",
            "guided": "stable_run",
        }.get(self.mission_key)
        goals = []
        if forced:
            goal = next((g for g in pool if g["key"] == forced), None)
            if goal:
                goals.append(dict(goal))
                pool = [g for g in pool if g["key"] != forced]
        random.shuffle(pool)
        goals.extend(dict(g) for g in pool[:max(0, 3 - len(goals))])
        return goals[:3]

    def goal_completed(self, goal_key: str) -> bool:
        if goal_key == "low_dose":
            return self.collective_dose < 8
        if goal_key == "safe_run":
            return self.safety >= 90
        if goal_key == "rich_finish":
            return self.funds >= 2500
        if goal_key == "stable_run":
            return self.runtime >= 45 and not self.scrammed
        if goal_key == "maintenance":
            return self.service_count >= 1
        if goal_key == "dispatch":
            return self.completed_dispatch >= 1
        if goal_key == "no_red":
            return not self.scrammed
        return False

    def side_goal_results(self) -> List[Tuple[dict, bool]]:
        return [(goal, self.goal_completed(goal["key"])) for goal in self.side_goals]

    def side_goal_bonus(self) -> int:
        return sum(goal.get("bonus", 0) for goal, done in self.side_goal_results() if done)

    def variant_meta(self, key: str) -> Optional[dict]:
        variant_key = self.equipment_variants.get(key, "standard")
        return EQUIPMENT_VARIANTS.get(key, {}).get(variant_key)

    def set_variant(self, key: str, variant: str):
        if key not in EQUIPMENT_VARIANTS or variant not in EQUIPMENT_VARIANTS[key]:
            return
        if key in self.placed:
            self.set_message("该设备已安装，不能再更改品质；如需更改请先拆除。", WARNING)
            return
        self.equipment_variants[key] = variant
        meta = EQUIPMENT_VARIANTS[key][variant]
        self.set_message(f"已选择：{ALL_MODULES[key].name}｜{meta['name']}。{meta['desc']}。", BLUE)
        self.audio.play("click")

    def visible_dashboard_pages(self) -> Dict[str, str]:
        """极简模式只显示状态页，避免玩家看到不可用或不需要的高级页面。"""
        if self.is_starter_mode():
            return {"status": "状态"}
        return {"status": "状态", "trend": "趋势", "barrier": "屏障", "maintenance": "维护", "atlas": "图鉴", "log": "日志"}

    def term_help_text(self, term: str) -> str:
        tips = {
            "一回路热段": "从反应堆流向蒸汽发生器的高温冷却剂管段。",
            "冷端换热能力": "冷凝器把汽轮机排汽冷却成水的能力，受冷却水流量和设备健康影响。",
            "冷凝器绝对压力": "单位 kPa(a)。数值升高表示冷端真空变差，通常需要关注循环冷却水系统（CRF）和冷却水流量。",
            "冷却水流量": "冷却水越多通常越有利于真空，但过高也会增加辅机消耗并影响经济性。",
            "蒸汽发生器水位": "蒸汽发生器内水位。过低或过高都会影响热量传递和安全裕度。",
            "ALARA": "辐射防护原则：合理可行尽量低。游戏采用 20/50/100 mSv 分级剂量机制：20 mSv 是职业参考线，100 mSv 是事故教学红线。",
            "模拟秒": "游戏内作业耗时单位，会影响专项时限和发电收益损失。",
            "稳定运行": "本游戏中指本局并网后的累计运行时间达到目标且未自动停堆。",
        }
        return tips.get(term, "")

    def show_term_tip(self, term: str, rect: pygame.Rect):
        text = self.term_help_text(term)
        self.tooltip_box = (term, text, rect.copy()) if text else None

    def can_click_install(self) -> bool:
        return (self.play_mode != "challenge" and self.stage in (0, 1)
                and not getattr(self, "site_selection_open", False))

    def click_install_at(self, pos: Tuple[int, int]) -> bool:
        """支持“单击设备 + 单击槽位”安装，降低精确拖拽压力。"""
        if not self.pending_install or not self.can_click_install():
            return False
        key = self.pending_install
        if key in self.placed or key not in ALL_MODULES:
            self.pending_install = None
            return False
        module = ALL_MODULES[key]
        if module.slot.inflate(40, 40).collidepoint(pos):
            self.install(key)
            self.pending_install = None
            self.snap_target = None
            return True
        stage_modules = CIVIL if self.stage == 0 else EQUIPMENT
        wrong = next((other for other, data in stage_modules.items()
                      if other != key and data.slot.inflate(10, 10).collidepoint(pos)), None)
        if wrong:
            self.set_message(f"放置位置错误：当前目标是“{module.name}”，不能放到“{stage_modules[wrong].name}”槽位。", WARNING)
            self.audio.play("warning")
            return True
        return False

    def open_info_card(self, key: str):
        if hasattr(self, "close_transient_overlays"):
            self.close_transient_overlays(keep="info")
        self.info_card = key
        self.card_scroll = 0
        self.audio.play("click")

    def equipment_complete(self) -> bool:
        """检查发电与反应堆主体设备；安全和防护设施分别进行专项验收。"""
        normal_keys = [key for key, module in EQUIPMENT.items()
                       if module.category not in ("安全", "防护")]
        return all(key in self.placed for key in normal_keys)

    def civil_complete(self) -> bool:
        return all(key in self.placed for key in CIVIL)

    def safety_complete(self) -> bool:
        return all(key in self.placed for key in ("diesel_a", "diesel_b", "spray", "efw"))

    def protection_complete(self) -> bool:
        return self.is_starter_mode() or all(key in self.placed for key in PROTECTION_KEYS)

    def missing_protection_names(self) -> List[str]:
        return [EQUIPMENT[key].name for key in PROTECTION_KEYS if key not in self.placed]

    def reduce_protection_score(self, amount: int, message: str):
        marker = f"{self.stage}:{message}"
        if marker in self.validation_penalties:
            self.set_message(message + " 问题尚未整改，本次不重复扣分。", WARNING)
            return
        self.validation_penalties.add(marker)
        if self.tutorial and self.mission_key == "guided" and self.stage not in self.grace_used:
            self.grace_used.add(self.stage)
            self.set_message("新手保护：" + message + " 本阶段首次验收失误不扣分，请补齐配置后重试。", WARNING)
            return
        self.protection_score = max(0, self.protection_score - amount)
        self.set_message(message + f" 防护评分 -{amount}。", DANGER)

    def set_message(self, msg, color=BLACK):
        self.message = msg
        self.message_color = color

    def penalty(self, amount: int, msg: str):
        if (self.tutorial and self.mission_key == "guided" and self.stage not in self.grace_used
                and not self.menu and not self.challenge_finished):
            self.grace_used.add(self.stage)
            self.set_message("新手保护：" + msg + " 本阶段首次失误不扣分，请按操作指引重试。", WARNING)
            return
        self.safety = max(0, self.safety - amount)
        self.mistakes += 1
        self.set_message(msg, DANGER)

    def installation_cost(self, key: str) -> int:
        module = ALL_MODULES[key]
        surcharge = 130 if key == "primary_pump" and self.pump_choice == "监测强化" else 0
        if key in EQUIPMENT_VARIANTS:
            meta = self.variant_meta(key)
            surcharge += int(meta.get("cost_delta", 0)) if meta else 0
        return module.cost + surcharge

    def can_install(self, module: Module) -> Tuple[bool, str]:
        missing = [ALL_MODULES[k].name for k in module.needs if k not in self.placed]
        if missing:
            return False, f"安装顺序错误：请先完成{'、'.join(missing)}。"
        total_cost = self.installation_cost(module.key)
        if self.funds < total_cost:
            return False, f"资金不足：安装{module.name}需要 {total_cost} 币。"
        return True, ""

    def install(self, key: str):
        module = ALL_MODULES[key]
        ok, reason = self.can_install(module)
        if not ok:
            self.penalty(3, reason)
            return
        if key in self.placed:
            return
        total_cost = self.installation_cost(key)
        self.placed[key] = module.slot.copy()
        self.installed_costs[key] = total_cost
        if key == "primary_pump":
            before = self.safety
            # CPR1000 采用带轴封主泵；这里不再提供“屏蔽泵”选型，
            # 而是在标准轴封维护与监测强化之间做经营取舍。
            if self.pump_choice == "监测强化":
                self.safety = min(100, self.safety + 3)
            self.primary_pump_safety_delta = self.safety - before
        self.funds -= total_cost
        self.days += module.days
        note = f"（{self.pump_choice}）" if key == "primary_pump" else ""
        self.selected = key
        self.set_message(f"安装成功：{module.name}{note}，消耗资金 {total_cost}，工期 +{module.days:g} 天。", GOOD)
        self.spawn_feedback(module.slot, module.color)
        if hasattr(self, "mark_param_change"):
            self.mark_param_change("资金", DANGER)
            self.mark_param_change("工期", WARNING)
        # 浮动反馈分层显示，避免窄设备槽位上“资金”和“工期”互相压住。
        self.add_float_text(f"资金 -{total_cost}", module.slot.centerx - 48, module.slot.y - 18, DANGER)
        self.add_float_text(f"工期 +{module.days:g}天", module.slot.centerx + 54, module.slot.y + 10, WARNING)
        if key == "primary_pump" and self.primary_pump_safety_delta:
            delta = self.primary_pump_safety_delta
            self.add_float_text(f"安全 {delta:+d}", module.slot.centerx, module.slot.y - 44, GOOD if delta > 0 else DANGER)
        self.audio.play("place")

    def remove(self, key: str):
        if self.stage not in (0, 1) or key not in self.placed:
            return
        # 已通过土建验收进入设备安装后，不允许拆除前一阶段建筑导致流程无法继续。
        if self.stage == 0 and key not in CIVIL:
            return
        if self.stage == 1 and key in CIVIL:
            self.set_message("土建模块已通过验收，若需重建请点击“返回节点”。", WARNING)
            return
        module = ALL_MODULES[key]
        dependent = [k for k in self.placed if k != key and key in ALL_MODULES[k].needs]
        if dependent:
            self.set_message(f"不能拆除：{ALL_MODULES[dependent[0]].name}依赖{module.name}。", WARNING)
            return
        del self.placed[key]
        paid_cost = self.installed_costs.pop(key, self.installation_cost(key))
        refund = int(paid_cost * 0.55)
        self.funds += refund
        if key == "primary_pump":
            self.safety = int(clamp(self.safety - self.primary_pump_safety_delta, 0, 100))
            self.primary_pump_safety_delta = 0
        self.days += 5
        self.set_message(f"已拆除{module.name}，退回部分资金 {refund}，返工增加 5 天。", WARNING)
        self.add_float_text(f"资金 +{refund}", module.slot.centerx - 48, module.slot.y - 18, GOOD)
        self.add_float_text("工期 +5天", module.slot.centerx + 54, module.slot.y + 10, WARNING)

