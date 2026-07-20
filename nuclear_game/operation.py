# -*- coding: utf-8 -*-
"""由 gameplay.py 拆分出的模块。

本文件只存放一类玩法逻辑，避免单个 gameplay.py 过大。
"""

import math
import random
from typing import List, Optional, Tuple

import pygame

from .theme import *
from .catalog import *
from .story_data import STORY_STAGE_NAMES
from .ui_helpers import F12, write, write_fit, rounded, clamp
from .models import Upgrade, RingEffect, ParticleEffect
from .ui.components import AlertBanner

STAGE_NAMES = STORY_STAGE_NAMES

MINOR_EVENT_LIBRARY = [
    {
        "title": "电网负荷微调",
        "desc": "调度中心要求 5 秒内小幅升负荷。",
        "choices": [
            {"text": "缓升功率", "ok": True, "effects": {"funds": 90, "safety": 1, "primary_flow": 0.2}},
            {"text": "快速满发", "ok": False, "effects": {"funds": 40, "safety": -4, "condenser_pressure": 0.4}},
        ],
    },
    {
        "title": "KRT 短时波动",
        "desc": "区域辐射监测出现短时尖峰。",
        "choices": [
            {"text": "复核并限入", "ok": True, "effects": {"protection_score": 2, "safety": 1}},
            {"text": "忽略尖峰", "ok": False, "effects": {"protection_score": -6, "safety": -2}},
        ],
    },
    {
        "title": "循环水泵振动",
        "desc": "三回路泵组振动略高。",
        "choices": [
            {"text": "降流量巡检", "ok": True, "effects": {"safety": 1, "condenser_pressure": -0.2}},
            {"text": "继续升流量", "ok": False, "effects": {"safety": -3, "condenser_pressure": 0.5}},
        ],
    },
]

class OperationMixin:
    def record_choice_effect(self, title: str, lines=None, duration_ms: int = 6200):
        """记录一次选择/处置对参数的影响，并在底部控制台重点显示。

        同时写入“决策因果复盘”，结算页会把玩家关键选择与后续后果串起来，
        让胜负原因不只停留在分数上。
        """
        if lines is None:
            lines = []
        if isinstance(lines, str):
            lines = [lines]
        lines = [str(x) for x in lines if str(x).strip()]
        self.last_choice_effect = title + ("：" + "；".join(lines) if lines else "")
        self.choice_effect_lines = [title] + lines
        self.choice_effect_until = pygame.time.get_ticks() + duration_ms

        if not hasattr(self, "decision_review") or not isinstance(self.decision_review, list):
            self.decision_review = []
        if title and not title.startswith("反馈"):
            self.decision_review.append({
                "time": round(float(getattr(self, "runtime", 0.0)), 1),
                "stage": int(getattr(self, "stage", 0)),
                "title": title,
                "effects": lines[:4],
            })
            self.decision_review = self.decision_review[-18:]

    def route_count(self, level: str) -> int:
        """返回玩家已选择某类经营路线的次数。"""
        bias = getattr(self, "strategy_bias", {})
        try:
            return int(bias.get(level, 0))
        except Exception:
            return 0

    def strategy_style(self) -> str:
        """结算与右侧面板显示的全局经营风格。"""
        safe = self.route_count("安全")
        balanced = self.route_count("平衡")
        aggressive = self.route_count("激进")
        if aggressive > max(safe, balanced):
            return "激进型"
        if safe > max(balanced, aggressive):
            return "稳健型"
        if self.funds >= 2600 and self.mistakes <= 1:
            return "成本控制型"
        return "平衡型"

    def budget_state(self) -> tuple:
        """预算压力分级：用于按钮禁用、提示和结算复盘。"""
        if self.funds < 0:
            return "停工", DANGER, "资金耗尽，项目进入停工风险。"
        if self.funds < 1000:
            return "严重", DANGER, "资金低于1000币：维护费用上升，错误操作后果更重。"
        if self.funds < 2000:
            return "紧张", WARNING, "资金低于2000币：安全策略暂不可用。"
        return "正常", GOOD, "预算状态正常。"

    def route_safety_modifier(self) -> float:
        """安全路线降低事故压力，激进路线提高事故压力。"""
        return self.route_count("安全") * 1.0 + self.route_count("平衡") * 0.25 - self.route_count("激进") * 1.25

    def mark_param_change(self, name: str, color=WARNING, duration_ms: int = 1300):
        """参数卡短暂闪烁，配合浮动数字形成更强反馈。"""
        if not hasattr(self, "param_flash") or not isinstance(self.param_flash, dict):
            self.param_flash = {}
        self.param_flash[name] = {"until": pygame.time.get_ticks() + duration_ms, "color": color}

    def service_cost(self, base_cost: int) -> int:
        """预算低时维护更贵，形成经营压力。"""
        factor = 1.22 if self.funds < 1000 else 1.0
        return int(round(base_cost * factor))

    def defense_score(self) -> int:
        return int(sum(self.barriers.values()) / max(1, len(self.barriers)))

    def affect_barrier(self, key: str, amount: float, note: str = ""):
        if key in self.barriers:
            self.barriers[key] = clamp(self.barriers[key] + amount, 0, 100)
            if note:
                self.log_event("barrier", note, barrier=key, delta=amount)

    def log_event(self, kind: str, text: str, **extra):
        entry = {"time": round(self.runtime, 1), "kind": kind, "text": text}
        entry.update(extra)
        self.event_log.append(entry)
        self.event_log = self.event_log[-30:]

    def open_work_plan(self):
        if not self.dose_task:
            return
        if hasattr(self, "close_transient_overlays"):
            self.close_transient_overlays(keep="work_plan")
        self.work_plan_open = True
        if self.play_mode in ("guided", "demo"):
            recommended = {
                "speed": {"route": "near", "staff": "rp_team", "equipment": "dosimeter"},
                "dose": {"route": "shield_corridor", "staff": "robot_operator", "equipment": "temp_shield"},
                "economy": {"route": "shield_corridor", "staff": "maintainer", "equipment": "dosimeter"},
            }
            self.work_plan_selection = recommended[self.dose_task["priority"]].copy()
        else:
            self.work_plan_selection = {"route": None, "staff": None, "equipment": None}
        self.audio.play("click")

    def estimate_work_plan(self) -> dict:
        selected = self.work_plan_selection
        if not all(selected.values()) or not self.dose_task:
            return {"ready": False, "cost": 0, "time": 0, "dose": 0.0,
                    "revenue_loss": 0, "total_impact": 0, "fit": False, "grade": "未完成方案"}
        selections = [WORK_PLAN_OPTIONS[group][value] for group, value in selected.items()]
        cost = sum(item["cost"] for item in selections)
        work_time = sum(item["time"] for item in selections)
        dose_factor = 1.0
        for item in selections:
            dose_factor *= item["dose"]
        installed_factor = 1.0
        if "bio_shield" in self.placed:
            installed_factor *= 0.70
        if "area_monitor" in self.placed:
            installed_factor *= 0.92
        if "dosimetry" in self.placed:
            installed_factor *= 0.95
        if self.system_upgrade_level("krt"):
            installed_factor *= 0.86
        if self.system_upgrade_level("ety") and self.dose_task.get("priority") == "dose":
            installed_factor *= 0.94
        dose = self.dose_task["base_dose"] * dose_factor * installed_factor
        revenue_loss = int(work_time * self.dose_task["power_loss_per_second"] *
                           max(0.45, self.output_mw / 1000))
        total_impact = cost + revenue_loss
        deadline_ok = work_time <= self.dose_task["deadline"]
        budget_ok = cost <= self.dose_task["budget_limit"]
        priority = self.dose_task["priority"]
        priority_ok = ((priority == "dose" and dose <= 2.0) or
                       (priority == "speed" and deadline_ok) or
                       (priority == "economy" and budget_ok and total_impact <= self.dose_task["budget_limit"] + 80))
        fit = deadline_ok and budget_ok and priority_ok
        grade = "优秀" if fit and dose < 1.0 else "合格" if fit else "不满足任务约束"
        return {"ready": True, "cost": cost, "time": work_time, "dose": dose,
                "revenue_loss": revenue_loss, "total_impact": total_impact,
                "deadline_ok": deadline_ok, "budget_ok": budget_ok,
                "priority_ok": priority_ok, "fit": fit, "grade": grade}

    def execute_work_plan(self):
        estimate = self.estimate_work_plan()
        if not estimate["ready"]:
            self.set_message("请先完成路线、人员和装备三项作业策划。", WARNING)
            return
        if self.funds < estimate["total_impact"]:
            self.set_message("资金不足：还需考虑作业期间的发电收益损失。", WARNING)
            return
        labels = [WORK_PLAN_OPTIONS[group][value]["name"] for group, value in self.work_plan_selection.items()]
        self.funds -= estimate["total_impact"]
        self.lost_revenue += estimate["revenue_loss"]
        self.operation_seconds += estimate["time"]
        self.collective_dose += estimate["dose"]
        self.max_task_dose = max(self.max_task_dose, estimate["dose"])

        if estimate["fit"]:
            self.protection_score = min(100, self.protection_score + (4 if estimate["dose"] < 1.0 else 2))
            self.affect_barrier("environment", 1, "作业策划满足专项约束，KRT/剂量监测可信")
        else:
            self.work_plan_violations += 1
            self.protection_score = max(0, self.protection_score - 8)
            self.affect_barrier("environment", -8, "作业方案未满足时限或预算约束，监测防线承压")
            if not estimate["deadline_ok"]:
                self.safety = max(0, self.safety - 3)

        self.log_event("dose", "完成作业策划：" + " / ".join(labels),
                       dose=round(estimate["dose"], 2), cost=estimate["cost"],
                       lost=estimate["revenue_loss"], fit=estimate["fit"], cause="dose")
        status = "方案合格" if estimate["fit"] else "方案违规"
        color = GOOD if estimate["fit"] else WARNING
        self.audio.play("success" if estimate["fit"] else "warning")
        self.show_banner(status, f"剂量 {estimate['dose']:.2f} mSv｜经济影响 {estimate['total_impact']} 币", color, 3.3)
        self.set_message(f"{status}：新增剂量 {estimate['dose']:.2f} mSv，成本及收益损失合计 {estimate['total_impact']} 币。", color)
        self.dose_task = None
        self.work_plan_open = False
        self.work_plan_selection = {"route": None, "staff": None, "equipment": None}
        if self.collective_dose >= TEACHING_DOSE_REDLINE:
            self.protection_score = max(0, self.protection_score - 30)
            self.scrammed = True
            self.affect_barrier("environment", -25, "100 mSv 事故教学红线触发，停止人员作业")
            self.log_event("scram", "累计任务剂量达到 100 mSv 事故教学红线，机组停止运行", cause="dose")
            self.audio.play("alarm")
            self.set_message("累计剂量达到 100 mSv 事故教学红线：停止人员作业并停机复盘。", DANGER)
        elif self.collective_dose >= DOSE_ORANGE_LINE:
            self.protection_score = max(0, self.protection_score - 4)
            self.affect_barrier("environment", -4, "50 mSv 橙色警戒：限制人员进入并复核作业方案")
            self.set_message("剂量进入 50 mSv 橙色警戒：限制人员进入，优先远程作业和临时屏蔽。", WARNING)
        elif self.collective_dose >= DOSE_REFERENCE_LINE:
            self.set_message("剂量超过 20 mSv 职业参考线：需加强 ALARA 优化，不再作为失败红线。", WARNING)

    def equipment_average_health(self) -> int:
        values = list(self.equipment_health.values())
        return int(sum(values) / len(values)) if values else 100

    def weakest_equipment(self) -> Tuple[str, float]:
        return min(self.equipment_health.items(), key=lambda item: item[1])

    def barrier_repair_required(self) -> Optional[dict]:
        """返回当前最需要优先整改的屏障；极简教学暂不启用高级整改。"""
        if self.is_starter_mode():
            return None
        candidates = []
        for key, rule in BARRIER_RECOVERY.items():
            value = self.barriers.get(key, 100.0)
            if value < rule["threshold"]:
                result = dict(rule)
                result["key"] = key
                result["value"] = value
                result["severity"] = (rule["threshold"] - value) / max(1.0, rule["threshold"])
                candidates.append(result)
        return max(candidates, key=lambda item: item["severity"]) if candidates else None

    def current_power_cap(self) -> float:
        if self.is_starter_mode():
            return 1.0
        cap = 1.0
        for key, rule in BARRIER_RECOVERY.items():
            value = self.barriers.get(key, 100.0)
            if value < rule["threshold"]:
                cap = min(cap, rule["power_cap"])
                if value < 60:
                    cap = min(cap, 0.55)
        if self.service_job:
            cap = min(cap, self.service_job.get("power_cap", 0.60))
        return cap

    def active_upgrade(self) -> Optional[Tuple[str, Upgrade]]:
        for key, upgrade in self.upgrades.items():
            if upgrade.in_progress:
                return key, upgrade
        return None

    def start_barrier_repair(self):
        issue = self.barrier_repair_required()
        if self.stage != 4 or not issue or self.service_job:
            return
        if self.active_upgrade():
            self.set_message("当前有升级项目正在执行，请完成后再开展屏障恢复任务。", WARNING)
            return
        if self.scrammed or self.challenge_finished:
            self.set_message("机组已停堆或成绩已锁定，请进入评价报告查看复盘结果。", WARNING)
            return
        if self.warning_event or self.fault or self.dose_task:
            self.set_message("当前存在待处置事件，不能安排屏障恢复工作。", WARNING)
            return
        cost = self.service_cost(issue["cost"])
        if self.funds < cost:
            self.set_message("资金不足，无法开展屏障恢复任务。", WARNING)
            return
        self.funds -= cost
        self.service_job = {
            "kind": "barrier", "key": issue["key"], "title": issue["name"],
            "remaining": issue["seconds"], "restore": issue["restore"], "power_cap": issue["power_cap"],
        }
        self.service_count += 1
        self.log_event("service", "开始：" + issue["name"], cause=issue["key"])
        self.add_float_text(f"资金 -{cost}", RIGHT.centerx, 182, DANGER)
        self.mark_param_change("资金", DANGER)
        self.set_message(f"已开始{issue['name']}，期间将限制输出功率。", WARNING)
        self.audio.play("click")

    def start_maintenance(self, key: Optional[str] = None):
        if self.stage != 4 or self.service_job:
            return
        if self.active_upgrade():
            self.set_message("当前有升级项目正在执行，请完成后再安排计划检修。", WARNING)
            return
        if self.scrammed or self.challenge_finished:
            self.set_message("机组已停堆或成绩已锁定，无法再安排计划检修。", WARNING)
            return
        if self.warning_event or self.fault or self.dose_task:
            self.set_message("当前存在待处置事件，不能安排计划检修。", WARNING)
            return
        target_key, value = self.weakest_equipment() if key is None else (key, self.equipment_health.get(key, 100))
        if target_key not in HEALTH_META:
            return
        if value >= 98:
            self.set_message("设备健康状态良好，暂无安排检修的必要。", TEXT_MUTED)
            return
        rule = HEALTH_META[target_key]
        cost = self.service_cost(rule["cost"])
        if self.funds < cost:
            self.set_message("资金不足，无法安排计划检修。", WARNING)
            return
        self.funds -= cost
        self.service_job = {
            "kind": "maintenance", "key": target_key, "title": rule["name"] + "计划检修",
            "remaining": rule["seconds"], "restore": rule["restore"], "power_cap": 0.60,
        }
        self.service_count += 1
        self.log_event("maintenance", "开始检修：" + rule["name"])
        self.add_float_text(f"资金 -{cost}", RIGHT.centerx, 182, DANGER)
        self.mark_param_change("资金", DANGER)
        self.set_message(f"已安排{rule['name']}检修，检修期间功率受限。", WARNING)
        self.audio.play("click")

    def update_service_job(self, dt: float):
        if not self.service_job:
            return
        self.service_job["remaining"] -= dt
        if self.service_job["remaining"] > 0:
            return
        job = self.service_job
        if job["kind"] == "barrier":
            self.affect_barrier(job["key"], job["restore"], job["title"] + "完成")
        else:
            key = job["key"]
            self.equipment_health[key] = clamp(self.equipment_health[key] + job["restore"], 0, 100)
            if key == "effluent_monitor":
                self.affect_barrier("environment", 4, "排放监测仪检修完成")
        self.log_event("service_done", "完成：" + job["title"])
        self.show_banner("维护完成", job["title"] + "已结束，运行限制解除", GOOD, 3.0)
        self.set_message(job["title"] + "已完成，机组可根据屏障状态恢复功率。", GOOD)
        self.audio.play("success")
        self.service_job = None

    def update_equipment_aging(self, dt: float):
        if self.is_starter_mode() or self.stage != 4 or self.scrammed or self.challenge_finished:
            return
        self.health_clock += dt
        while self.health_clock >= 1.0:
            self.health_clock -= 1.0
            load = clamp(self.output_mw / 1000, 0.35, 1.15)
            site_factor = 1.10 if self.site.get("key") == "coast" else 1.0
            for key, meta in HEALTH_META.items():
                factor = site_factor if key in ("condenser", "effluent_monitor") else 1.0
                if key == "condenser":
                    factor *= (self.variant_meta("condenser") or {}).get("aging", 1.0)
                elif key == "turbine":
                    factor *= (self.variant_meta("turbine") or {}).get("aging", 1.0)
                self.equipment_health[key] = max(0.0, self.equipment_health[key] - meta["wear"] * load * factor)
            if self.equipment_health["effluent_monitor"] < 70 and int(self.runtime) % 10 == 0:
                self.affect_barrier("environment", -0.8, "排放监测仪老化影响环境监测可信度")

    def trigger_dispatch_task(self):
        if self.is_starter_mode() or self.dispatch_task or self.warning_event or self.fault or self.dose_task:
            return
        task = random.choice(DISPATCH_TASKS).copy()
        self.dispatch_task = task
        self.dispatch_left = float(task["duration"])
        self.dashboard_page = "status"
        self.log_event("dispatch", "电网调度：" + task["title"], cause="dispatch")
        self.show_banner("电网调度", task["desc"], BLUE, 3.0)
        self.set_message("收到电网调度：" + task["desc"], BLUE)
        self.audio.play("warning")

    def dispatch_condition_met(self) -> bool:
        if not self.dispatch_task:
            return False
        key = self.dispatch_task["key"]
        if key == "peak":
            return self.output_mw >= 900
        if key == "water_limit":
            return self.cooling_flow <= 80 and self.parameters.get("冷凝器绝对压力", (99,))[0] <= 13
        if key == "maintenance_window":
            return self.service_job is not None or self.cooling_flow <= 65
        return False

    def update_dispatch_task(self, dt: float):
        if not self.dispatch_task:
            return
        self.dispatch_left -= dt
        if self.dispatch_condition_met():
            reward = int(self.dispatch_task.get("reward", 120))
            self.funds += reward
            self.completed_dispatch += 1
            self.log_event("dispatch_done", "完成电网调度：" + self.dispatch_task["title"], cost=-reward)
            self.show_banner("调度完成", f"奖励资金 {reward} 币", GOOD, 2.8)
            self.set_message(f"电网调度完成：奖励资金 {reward} 币。", GOOD)
            self.audio.play("success")
            self.dispatch_task = None
            self.dispatch_left = 0
            self.next_dispatch = self.runtime + random.uniform(22, 34)
        elif self.dispatch_left <= 0:
            self.dispatch_failures += 1
            self.safety = max(0, self.safety - 3)
            self.funds = max(0, self.funds - 100)
            self.log_event("dispatch_fail", "电网调度未完成：" + self.dispatch_task["title"], cause="dispatch")
            self.show_banner("调度失败", "安全评分 -3，资金 -100", WARNING, 3.0)
            self.set_message("未满足电网调度要求，安全评分和资金下降。", WARNING)
            self.dispatch_task = None
            self.dispatch_left = 0
            self.next_dispatch = self.runtime + random.uniform(24, 38)

    def unlock_endgame_rewards(self):
        unlocked = set(self.achievements_unlocked)
        def add(key):
            if key in ACHIEVEMENTS:
                unlocked.add(key)
        if self.stage == 4:
            add("first_grid")
        if self.collective_dose < 5 and not self.scrammed:
            add("low_dose_master")
        if self.safety >= 95:
            add("safety_guard")
        if self.funds >= 3000:
            add("economy_master")
        if self.runtime >= 45 and not self.scrammed:
            add("steady_operator")
        if self.completed_dispatch >= 1:
            add("dispatch_responder")
        if self.side_goals and all(done for _, done in self.side_goal_results()):
            add("perfect_goals")
        self.achievements_unlocked = sorted(unlocked)
        self.gallery_unlocked = sorted(k for k in self.achievements_unlocked if k in GALLERY_ITEMS)

    def simulation_paused(self) -> bool:
        """引导模式允许阅读暂停；挑战模式仅终局/复盘暂停，防止冻结倒计时绕过挑战。"""
        if self.menu or self.report or self.review_open or self.level_popup or getattr(self, "site_selection_open", False):
            return True
        if self.is_guided_mode():
            return self.stage_guide_open or self.info_card or self.work_plan_open
        return False

    def is_guided_mode(self) -> bool:
        return self.play_mode in ("starter", "guided", "demo")

    def system_upgrade_level(self, key: str) -> int:
        up = getattr(self, "upgrades", {}).get(key)
        return int(getattr(up, "level", 0)) if up else 0

    def active_event_key_for_bonus(self) -> str:
        if getattr(self, "warning_event", None):
            return self.warning_event.get("key", "")
        if getattr(self, "fault", None):
            return self.fault.key
        return ""


    def warning_duration(self) -> float:
        """黄色预警改为短处置窗口：5–8 秒内完成，增加紧张感。"""
        if self.is_starter_mode():
            return 8.0
        quality = float(getattr(self, "commissioning_quality", 100.0))
        route_shift = self.route_safety_modifier() * 0.25
        key = self.active_event_key_for_bonus()
        upgrade_bonus = 0.0
        if key == "water":
            upgrade_bonus += 0.8 * self.system_upgrade_level("asg") + 0.4 * self.system_upgrade_level("ris")
        elif key == "safety":
            upgrade_bonus += 0.7 * self.system_upgrade_level("eas") + 0.4 * self.system_upgrade_level("ris")
        elif key == "power":
            upgrade_bonus += 0.8 * self.system_upgrade_level("edg")
        elif key == "dose":
            upgrade_bonus += 0.7 * self.system_upgrade_level("krt")
        raw = 6.4 + (quality - 100.0) * 0.015 + route_shift + upgrade_bonus
        if self.play_mode in ("guided", "demo"):
            return clamp(raw + 3.5, 8.0, 12.0)
        return clamp(raw, 5.0, 8.0)

    def fault_duration(self) -> float:
        if self.is_starter_mode():
            return 24.0
        base = BALANCE.guided_fault_seconds if self.is_guided_mode() else BALANCE.normal_fault_seconds
        quality = float(getattr(self, "commissioning_quality", 100.0))
        route_shift = self.route_safety_modifier() * 0.85
        key = self.active_event_key_for_bonus()
        upgrade_bonus = 0.0
        if key == "water":
            upgrade_bonus += 3.0 * self.system_upgrade_level("asg") + 1.5 * self.system_upgrade_level("ris")
        elif key == "safety":
            upgrade_bonus += 2.5 * self.system_upgrade_level("eas") + 2.0 * self.system_upgrade_level("ris") + 1.5 * self.system_upgrade_level("ety")
        elif key == "power":
            upgrade_bonus += 3.0 * self.system_upgrade_level("edg")
        elif key == "dose":
            upgrade_bonus += 2.0 * self.system_upgrade_level("krt")
        return max(6.0, base + (quality - 100.0) * 0.05 + route_shift + upgrade_bonus)

    def first_warning_time(self) -> float:
        if self.is_starter_mode():
            return 10.0
        base = BALANCE.guided_first_warning if self.is_guided_mode() else BALANCE.normal_first_warning
        quality = float(getattr(self, "commissioning_quality", 100.0))
        route_shift = self.route_safety_modifier() * 2.0
        return max(8.0, base + (quality - 100.0) * 0.08 + route_shift)

    def next_warning_time(self) -> float:
        if self.is_starter_mode():
            return float("inf")
        low, high = BALANCE.guided_warning_interval if self.is_guided_mode() else BALANCE.normal_warning_interval
        quality = float(getattr(self, "commissioning_quality", 100.0))
        shift = (quality - 100.0) * 0.06 + self.route_safety_modifier() * 3.4
        shift += 2.0 * self.system_upgrade_level("edg") + 1.5 * self.system_upgrade_level("krt")
        return self.runtime + max(10.0, random.uniform(low, high) + shift)

    def first_dose_time(self) -> float:
        if self.is_starter_mode():
            return float("inf")
        return BALANCE.guided_first_dose if self.is_guided_mode() else BALANCE.normal_first_dose

    def next_dose_time(self) -> float:
        if self.is_starter_mode():
            return float("inf")
        low, high = BALANCE.guided_dose_interval if self.is_guided_mode() else BALANCE.normal_dose_interval
        return self.runtime + random.uniform(low, high)

    def dose_task_duration(self) -> float:
        base = BALANCE.guided_dose_seconds if self.is_guided_mode() else BALANCE.normal_dose_seconds
        return base + 4.0 * self.system_upgrade_level("krt") + 2.0 * self.system_upgrade_level("ety")

    def show_banner(self, title: str, detail: str, color: Tuple[int, int, int], duration: float = None):
        self.banner = {
            "title": title, "detail": detail, "color": color,
            "remaining": BALANCE.banner_seconds if duration is None else duration,
        }

    def spawn_feedback(self, rect: pygame.Rect, color: Tuple[int, int, int]):
        self.feedback_rings.append(RingEffect(rect.center, color))
        for _ in range(12):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(36, 92)
            self.feedback_particles.append(
                ParticleEffect(rect.centerx, rect.centery, math.cos(angle) * speed,
                               math.sin(angle) * speed, color)
            )

    def add_float_text(self, text: str, x: float, y: float, color=GOOD):
        """数值变化浮动反馈。"""
        if not hasattr(self, "float_texts"):
            self.float_texts = []
        self.float_texts.append({"text": str(text), "x": float(x), "y": float(y),
                                 "color": color, "life": 1.15, "vy": -32.0})

    def update_feedback(self, dt: float):
        if self.banner:
            self.banner["remaining"] -= dt
            if self.banner["remaining"] <= 0:
                self.banner = None
        for ring in self.feedback_rings:
            ring.life -= dt
            ring.radius += 90 * dt
        self.feedback_rings = [item for item in self.feedback_rings if item.life > 0]
        for item in self.feedback_particles:
            item.life -= dt
            item.x += item.vx * dt
            item.y += item.vy * dt
            item.vy += 100 * dt
        self.feedback_particles = [item for item in self.feedback_particles if item.life > 0]
        for item in getattr(self, "float_texts", []):
            item["life"] -= dt
            item["y"] += item.get("vy", -30) * dt
        self.float_texts = [item for item in getattr(self, "float_texts", []) if item["life"] > 0]

    def draw_feedback(self):
        for ring in self.feedback_rings:
            alpha = clamp(ring.life / BALANCE.install_fx_seconds, 0, 1)
            color = tuple(int(channel * (0.55 + 0.45 * alpha)) for channel in ring.color)
            pygame.draw.circle(self.screen, color, ring.center, int(ring.radius), 2)
        for item in self.feedback_particles:
            radius = max(1, int(4 * clamp(item.life / BALANCE.install_fx_seconds, 0, 1)))
            pygame.draw.circle(self.screen, item.color, (int(item.x), int(item.y)), radius)
        for item in getattr(self, "float_texts", []):
            alpha = clamp(item["life"] / 1.15, 0, 1)
            rect = pygame.Rect(int(item["x"] - 58), int(item["y"] - 10), 116, 24)
            rounded(self.screen, rect, (255, 255, 255), item["color"], 1, 12)
            write_fit(self.screen, item["text"], 12, item["color"], rect.inflate(-8, -3),
                      align="center", bold=True, min_size=9)
        if self.banner and self.stage == 4:
            color = self.banner["color"]
            state = "danger" if color == DANGER else "warn" if color == WARNING else "good"
            footer = "请按左侧处置步骤操作" if color in (WARNING, DANGER) else "状态已恢复"
            AlertBanner(
                pygame.Rect(287, 145, 828, 58),
                self.banner["title"],
                self.banner["detail"],
                state=state,
                footer=footer,
            ).draw(self.screen)

    def trigger_minor_event(self):
        if getattr(self, "minor_event", None) or getattr(self, "scrammed", False):
            return
        event = random.choice(MINOR_EVENT_LIBRARY).copy()
        event["choices"] = [choice.copy() for choice in event.get("choices", [])]
        self.minor_event = event
        self.minor_event_left = random.uniform(9.0, 13.0) if self.is_guided_mode() else random.uniform(5.0, 8.0)
        self.minor_events_remaining = max(0, int(getattr(self, "minor_events_remaining", 0)) - 1)
        self.dashboard_page = "status"
        self.audio.play("warning")
        self.show_banner("随机运行小事件", event["title"] + "｜限时判断", WARNING, 3.0)
        self.set_message("随机小事件：请在左侧限时选择处理方式。", WARNING)
        self.log_event("minor", "随机小事件：" + event["title"], cause="minor")

    def answer_minor_event(self, option_index: int):
        event = getattr(self, "minor_event", None)
        if not event:
            return
        choices = event.get("choices", [])
        if option_index < 0 or option_index >= len(choices):
            return
        choice = choices[option_index]
        effects = choice.get("effects", {})
        lines = self.apply_parameter_effects(effects)
        if choice.get("ok"):
            self.show_banner("小事件处理正确", event["title"], GOOD, 2.8)
            self.set_message("处理正确：参数联动已反馈，继续稳定运行。", GOOD)
            self.record_choice_effect("随机小事件处理正确", lines or [choice.get("text", "")])
            self.audio.play("success")
        else:
            self.mistakes += 1
            self.show_banner("小事件处理失误", event["title"], WARNING, 3.0)
            self.set_message("处理失误：安全/防护或参数出现不利变化。", WARNING)
            self.record_choice_effect("随机小事件处理失误", lines or [choice.get("text", "")])
            self.audio.play("warning")
        self.log_event("minor", event["title"] + "｜" + choice.get("text", ""), cause="minor", ok=choice.get("ok"))
        self.minor_event = None
        self.minor_event_left = 0.0
        if getattr(self, "minor_events_remaining", 0) > 0:
            self.next_minor_event = self.runtime + random.uniform(9.0, 15.0)

    def fail_minor_event(self):
        event = getattr(self, "minor_event", None)
        if not event:
            return
        self.safety = max(0, self.safety - 3)
        self.funds -= 60
        self.apply_parameter_delta("condenser_pressure", 0.25)
        self.mark_param_change("安全评分", DANGER)
        self.add_float_text("安全 -3", RIGHT.centerx, 184, DANGER)
        self.add_float_text("资金 -60", RIGHT.centerx, 214, DANGER)
        self.record_choice_effect("随机小事件超时", [event["title"], "安全评分 -3", "资金 -60", "冷凝器绝对压力 +0.25 kPa(a)"])
        self.show_banner("小事件超时", event["title"] + "｜参数恶化", DANGER, 3.2)
        self.set_message("随机小事件未处理：安全评分、资金和冷端参数受到影响。", DANGER)
        self.log_event("minor_timeout", "随机小事件超时：" + event["title"], cause="minor")
        self.audio.play("warning")
        self.minor_event = None
        self.minor_event_left = 0.0
        if getattr(self, "minor_events_remaining", 0) > 0:
            self.next_minor_event = self.runtime + random.uniform(9.0, 15.0)

    def trigger_dose_task(self):
        self.dose_task = random.choice(DOSE_TASK_LIBRARY).copy()
        self.dose_task_left = self.dose_task_duration()
        self.dashboard_page = "status"
        self.audio.play("warning")
        self.show_banner("受控区作业任务", self.dose_task["title"] + "｜请先制定方案", WARNING)
        self.set_message("新的人员作业任务已出现：先制定路线、人员与装备方案，再执行。", WARNING)
        self.log_event("dose_task", "出现受控区作业任务：" + self.dose_task["title"], cause="dose")

    def fail_dose_task(self):
        if not self.dose_task:
            return
        added = self.dose_task["base_dose"] * 0.75
        self.collective_dose += added
        self.max_task_dose = max(self.max_task_dose, added)
        self.protection_score = max(0, self.protection_score - 12)
        self.affect_barrier("environment", -12, "作业未策划并超时，监测防线承压")
        self.audio.play("alarm")
        self.show_banner("作业任务超时", f"新增 {added:.2f} mSv，防护评分下降", DANGER)
        self.set_message(f"作业任务超时：新增任务剂量 {added:.2f} mSv，防护评分下降。", DANGER)
        self.log_event("dose", "作业任务超时", dose=round(added, 2), cause="dose")
        self.dose_task = None
        self.work_plan_open = False
        if self.collective_dose >= TEACHING_DOSE_REDLINE:
            self.scrammed = True
            self.output_mw = 0
            self.log_event("scram", "累计任务剂量达到 100 mSv 事故教学红线", cause="dose")
            self.set_message("累计剂量达到 100 mSv 事故教学红线：机组停止运行。", DANGER)
        elif self.collective_dose >= DOSE_ORANGE_LINE:
            self.affect_barrier("environment", -4, "50 mSv 橙色警戒：作业超时导致监测防线承压")
            self.set_message("剂量进入 50 mSv 橙色警戒：限制人员进入，重新制定作业方案。", WARNING)
        elif self.collective_dose >= DOSE_REFERENCE_LINE:
            self.set_message("剂量超过 20 mSv 职业参考线：需加强 ALARA 优化。", WARNING)

    def update_history(self, dt: float):
        if self.stage != 4:
            return
        self.history_clock += dt
        sample_period = 0.32
        while self.history_clock >= sample_period:
            self.history_clock -= sample_period
            for key, value in {
                "temp": self.parameters.get("一回路平均温度", (0,))[0],
                "pressure": self.parameters.get("一回路压力", (0,))[0],
                "power": self.output_mw,
            }.items():
                self.history.setdefault(key, []).append(float(value))
                self.history[key] = self.history[key][-BALANCE.history_samples:]

    def draw_trend_chart(self, rect: pygame.Rect, title: str, values: List[float],
                         color: Tuple[int, int, int], unit: str):
        rounded(self.screen, rect, (247, 250, 251), GRID, 1, 7)
        write(self.screen, title, F12, BLACK, (rect.x + 9, rect.y + 7))
        if not values:
            write(self.screen, "等待运行数据…", F12, TEXT_MUTED, (rect.x + 9, rect.y + 35))
            return
        write(self.screen, f"{values[-1]:.1f} {unit}", F12, color, (rect.right - 10, rect.y + 7), "topright")
        plot = pygame.Rect(rect.x + 10, rect.y + 29, rect.width - 20, rect.height - 40)
        pygame.draw.line(self.screen, GRID, plot.bottomleft, plot.bottomright, 1)
        low, high = min(values), max(values)
        if abs(high - low) < 0.001:
            low -= 1
            high += 1
        points = []
        for index, value in enumerate(values):
            x = plot.x + int(index * plot.width / max(1, len(values) - 1))
            y = plot.bottom - int((value - low) / (high - low) * plot.height)
            points.append((x, y))
        if len(points) > 1:
            pygame.draw.lines(self.screen, color, False, points, 2)
        pygame.draw.circle(self.screen, color, points[-1], 3)

    def stable_for_upgrade(self) -> bool:
        if self.stage != 4 or self.scrammed or self.fault:
            return False
        pressure = self.parameters["一回路压力"][0]
        return 15.3 <= pressure <= 15.7 and self.runtime > 7

    def start_upgrade(self, key):
        if key not in self.upgrades:
            return
        up = self.upgrades[key]
        if up.level >= 1 or up.in_progress:
            return
        current = self.active_upgrade()
        if current:
            self.set_message(f"升级项目“{current[1].name}”正在执行，完成后才能开始新的升级。", WARNING)
            return
        if self.service_job or self.barrier_repair_required():
            self.set_message("当前存在维护或屏障恢复限制，暂不能开展性能升级。", WARNING)
            return
        if not self.stable_for_upgrade():
            self.set_message("升级联锁未满足：需并网稳定且一回路压力正常、无当前报警。", WARNING)
            return
        if self.funds < up.cost:
            self.set_message("资金不足，无法开始升级项目。", WARNING)
            return
        self.funds -= up.cost
        up.in_progress = True
        up.remaining = up.build_time
        self.set_message(f"升级开始：{up.name}，预计 {up.build_time:g} 秒完成。", GOOD)
        self.audio.play("click")

    def update_running(self, dt):
        if self.menu or self.stage != 4 or self.scrammed or self.challenge_finished:
            return
        self.runtime += dt
        self.anim += dt * 120
        self.income_clock += dt
        self.update_history(dt)
        self.update_service_job(dt)
        self.update_equipment_aging(dt)
        self.update_dispatch_task(dt)

        while self.income_clock >= 1:
            # 激进路线提高收益但也让报警更频繁；安全路线收益略低但事故压力下降。
            income_factor = 1.0 + self.route_count("激进") * 0.018 - self.route_count("安全") * 0.006
            self.funds += max(0, self.output_mw) * 0.08 * max(0.90, income_factor)
            self.income_clock -= 1

        for key, up in self.upgrades.items():
            if up.in_progress:
                up.remaining -= dt
                if up.remaining <= 0:
                    up.in_progress = False
                    up.level = 1
                    if key == "monitor":
                        self.safety = min(100, self.safety + 6)
                        self.protection_score = min(100, self.protection_score + 5)
                    elif key in ("asg", "ris", "eas", "edg", "krt", "ety"):
                        if key in ("asg", "ris", "eas", "edg"):
                            self.safety = min(100, self.safety + 3)
                            self.affect_barrier("safety", 2, up.name + "升级完成，专设安全设施可用性提高")
                        if key in ("krt", "ety"):
                            self.protection_score = min(100, self.protection_score + 4)
                            self.affect_barrier("environment", 2, up.name + "升级完成，监测防线加强")
                        self.log_event("upgrade", "完成系统升级：" + up.name, cause=key)
                    self.audio.play("success")
                    self.show_banner("升级完成", f"{up.name}｜{up.effect}", GOOD, 3.0)
                    self.set_message(f"升级完成：{up.name}，{up.effect}。", GOOD)

        if self.warning_event:
            if (self.warning_event["key"] == "vacuum" and self.cooling_flow >= 85
                    and self.diagnosis_resolved):
                self.clear_operating_event(True)
                return
            self.warning_left -= dt
            if self.warning_left <= 0:
                self.escalate_warning()
        elif self.fault:
            self.fault_left -= dt
            if self.fault_left <= 0:
                self.fail_fault("未在限定时间内完成拖拽处置。")
        elif self.dose_task:
            self.dose_task_left -= dt
            if self.dose_task_left <= 0:
                self.fail_dose_task()
        elif self.minor_event:
            self.minor_event_left -= dt
            if self.minor_event_left <= 0:
                self.fail_minor_event()
        elif (not self.is_starter_mode() and not self.service_job and not self.dispatch_task
              and getattr(self, "minor_events_remaining", 0) > 0
              and self.runtime > getattr(self, "next_minor_event", float("inf"))):
            self.trigger_minor_event()
        elif not self.service_job and self.runtime > self.next_dispatch and not self.dispatch_task:
            self.trigger_dispatch_task()
            self.next_dispatch = self.runtime + random.uniform(28, 42)
        elif not self.service_job and self.runtime > self.next_fault:
            self.trigger_warning()
            self.next_fault = self.next_warning_time()
        elif not self.service_job and self.runtime > self.next_dose_task:
            self.trigger_dose_task()
            self.next_dose_task = self.next_dose_time()

        self.check_failure_conditions()

    # 失败入口统一由 result_system.ResultSystemMixin.trigger_failure 提供。
    # 本模块只负责判断失败条件，避免同名方法依赖 MRO 覆盖。

    def check_failure_conditions(self):
        """更清晰的失败机制：资金、安全、剂量和关键运行参数。"""
        if self.menu or self.report or self.challenge_finished or self.stage != 4:
            return
        if self.funds <= 0:
            self.trigger_failure("资金耗尽：项目停工。", "建议下局选择更稳妥的厂址，并避免频繁错误处置。")
        elif self.safety < 60:
            self.trigger_failure("安全评分过低：安全审查不通过。", "建议优先处置黄色预警，避免拖到红色故障。")
        elif self.protection_score < 60:
            self.trigger_failure("防护评分过低：辐射防护验收不通过。", "建议完善个人剂量系统、区域监测与作业方案。")
        elif self.collective_dose >= TEACHING_DOSE_REDLINE:
            self.trigger_failure("个人剂量达到 100 mSv 事故教学红线。", "建议按分级剂量机制控制作业：20 mSv 以上加强优化，50 mSv 以上限制进入，100 mSv 触发事故复盘。")
        else:
            condenser = self.parameters.get("冷凝器绝对压力") if isinstance(self.parameters, dict) else None
            if condenser and condenser[0] > 13.5 and self.runtime > 10:
                self.trigger_failure("冷凝器绝对压力长期异常：运行风险升级。", "建议提前增加冷却水流量，并在预警阶段完成诊断处置。")
