# -*- coding: utf-8 -*-
"""存档、成绩与任务结算逻辑。

从 engine.py 拆出，避免主流程文件继续膨胀。
这些方法都以 mixin 形式工作，通过 self 访问 NuclearGame 的状态。
"""

import json
import math
import time
import shutil
from copy import deepcopy
from pathlib import Path
from typing import List, Optional

import pygame

from .theme import *
from .catalog import (
    SITE_TYPES, REVIEW_LIBRARY, MISSION_TYPES, PLAY_MODES, ALL_MODULES,
    EQUIP_TABS, EQUIPMENT_VARIANTS, HEALTH_META, ACHIEVEMENTS, GALLERY_ITEMS, BALANCE,
)
from .story_data import STORY_STAGE_NAMES
from .ui_helpers import clamp

STAGE_NAMES = STORY_STAGE_NAMES
SAVE_VERSION = 3
GAME_VERSION = "1.0.0-engineering"


class PersistenceMixin:
    def safe_float(self, value, default: float = 0.0,
                   minimum: Optional[float] = None, maximum: Optional[float] = None) -> float:
        """把外部 JSON 中的数值安全转换为有限浮点数。"""
        try:
            result = float(value)
        except (TypeError, ValueError):
            result = float(default)
        if not math.isfinite(result):
            result = float(default)
        if minimum is not None:
            result = max(minimum, result)
        if maximum is not None:
            result = min(maximum, result)
        return result

    def safe_int(self, value, default: int = 0,
                 minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
        result = int(round(self.safe_float(value, default)))
        if minimum is not None:
            result = max(minimum, result)
        if maximum is not None:
            result = min(maximum, result)
        return result

    def normalize_site(self, saved_site) -> dict:
        """旧存档仅可恢复到已定义场址，避免缺失参数破坏热工计算。"""
        if isinstance(saved_site, dict):
            key = saved_site.get("key")
            name = saved_site.get("name")
            for site in SITE_TYPES:
                if key == site.get("key") or name == site.get("name"):
                    return deepcopy(site)
        return deepcopy(SITE_TYPES[0])

    def normalize_event_log(self, entries) -> List[dict]:
        cleaned = []
        if not isinstance(entries, list):
            return cleaned
        for item in entries[-30:]:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", "未命名记录"))
            row = {"time": self.safe_float(item.get("time", 0), 0, 0), "kind": str(item.get("kind", "record")),
                   "text": text}
            cause = item.get("cause")
            if cause in REVIEW_LIBRARY:
                row["cause"] = cause
            for key in ("dose", "cost", "lost"):
                if key in item:
                    row[key] = self.safe_float(item.get(key), 0, 0)
            if "fit" in item:
                row["fit"] = bool(item.get("fit"))
            cleaned.append(row)
        return cleaned

    def normalize_record(self, item) -> Optional[dict]:
        if not isinstance(item, dict):
            return None
        mission = item.get("mission", "guided")
        mode = item.get("mode", "guided")
        if not isinstance(mission, str) or mission not in MISSION_TYPES:
            return None
        if not isinstance(mode, str) or mode not in PLAY_MODES:
            mode = "guided"
        return {
            "mission": mission,
            "mission_name": str(item.get("mission_name", MISSION_TYPES[mission]["name"])),
            "site": str(item.get("site", "未知场址")),
            "score": self.safe_int(item.get("score", 0), 0, 0, 100),
            "safety": self.safe_int(item.get("safety", 0), 0, 0, 100),
            "protection": self.safe_int(item.get("protection", 0), 0, 0, 100),
            "defense": self.safe_int(item.get("defense", 0), 0, 0, 100),
            "health": self.safe_int(item.get("health", 100), 100, 0, 100),
            "mode": mode,
            "dose": round(self.safe_float(item.get("dose", 0), 0, 0), 2),
            "operation_seconds": self.safe_int(item.get("operation_seconds", item.get("operation_minutes", 0)), 0, 0),
            "lost_revenue": round(self.safe_float(item.get("lost_revenue", 0), 0, 0), 1),
            "service_count": self.safe_int(item.get("service_count", 0), 0, 0),
            "violations": self.safe_int(item.get("violations", 0), 0, 0),
            "days": round(self.safe_float(item.get("days", 0), 0, 0), 1),
        }

    def backup_save_file(self, reason: str = "backup") -> Optional[Path]:
        """备份当前存档文件，用于重置、迁移或损坏文件保护。"""
        try:
            if not self.save_path.exists():
                return None
            stamp = time.strftime("%Y%m%d_%H%M%S")
            backup_path = self.save_path.with_name(f"{self.save_path.stem}_{reason}_{stamp}{self.save_path.suffix}")
            shutil.copy2(self.save_path, backup_path)
            return backup_path
        except OSError:
            return None

    def migrate_save_payload(self, payload: dict) -> dict:
        """把旧版本存档迁移到当前结构。

        v1/v2：使用 version 字段，只包含 checkpoints；
        v3：使用 save_version + game_version + level_state。
        """
        if not isinstance(payload, dict):
            return {"save_version": SAVE_VERSION, "game_version": GAME_VERSION, "checkpoints": {}, "level_state": {}}
        version = payload.get("save_version", payload.get("version", 1))
        try:
            version = int(version)
        except Exception:
            version = 1
        checkpoints = payload.get("checkpoints", {})
        if not isinstance(checkpoints, dict):
            checkpoints = {}
        clean_checkpoints = {
            str(key): value for key, value in checkpoints.items()
            if str(key).isdigit() and isinstance(value, dict)
        }
        level_state = payload.get("level_state", {})
        if not isinstance(level_state, dict):
            level_state = {}
        # 旧存档没有 level_state，则由最高已存节点推断解锁。
        if version < 3 or not level_state:
            stages = sorted(int(key) for key in clean_checkpoints if str(key).isdigit())
            latest = max(stages) if stages else 0
            level_state = {"current_stage": latest, "unlocked": list(range(latest + 1)), "stars": {}, "badges": {}, "rewards": {}}
        return {
            "save_version": SAVE_VERSION,
            "game_version": GAME_VERSION,
            "checkpoints": clean_checkpoints,
            "level_state": level_state,
        }

    def reset_all_saved_data(self):
        """从菜单或控制台重置节点存档，并先自动备份。"""
        backup = self.backup_save_file("reset")
        self.checkpoints = {}
        if hasattr(self, "level_manager"):
            self.level_manager.reset(keep_records=False)
        try:
            self.save_path.unlink(missing_ok=True)
        except OSError:
            pass
        note = f"已重置节点存档。备份：{backup.name}" if backup else "已重置节点存档。"
        self.set_message(note, WARNING)

    def safe_write_json(self, path: Path, payload: dict):
        """先写临时文件再替换正式文件，避免写入中断破坏已有记录。"""
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(path)

    def read_records(self) -> list:
        """容错读取成绩并规范字段，非法成绩不会影响菜单或结算。"""
        try:
            if not self.record_path.exists():
                return []
            payload = json.loads(self.record_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or not isinstance(payload.get("records", []), list):
                return []
            cleaned = []
            for item in payload.get("records", []):
                normalized = self.normalize_record(item)
                if normalized:
                    cleaned.append(normalized)
            return cleaned[:30]
        except (OSError, ValueError, TypeError, AttributeError):
            return []

    def write_records(self):
        try:
            self.safe_write_json(self.record_path, {"version": 2, "records": self.records[:30]})
        except OSError:
            self.set_message("成绩记录写入失败，请检查文件夹权限。", WARNING)

    def mission_complete(self) -> bool:
        if self.is_starter_mode():
            return self.stage == 4 and not self.scrammed and self.runtime >= 18 and self.safety >= 75
        mission = MISSION_TYPES[self.mission_key]
        unresolved_barrier = self.barrier_repair_required() is not None
        if (self.stage != 4 or self.scrammed or self.runtime < mission["run_time"] or
                self.service_job is not None or unresolved_barrier):
            return False
        if self.mission_key == "guided":
            return self.safety >= 80 and self.protection_score >= 80 and self.defense_score() >= 78
        if self.mission_key == "protection":
            return (self.collective_dose < 12 and self.protection_score >= 92 and
                    self.barriers["environment"] >= 92)
        return self.funds >= 1800 and self.safety >= 78 and self.equipment_average_health() >= 80

    def calculate_total_score(self) -> int:
        mission_bonus = 12 if self.mission_complete() else 0
        dose_score = max(0, 100 - self.collective_dose * 2.0)
        economy_score = clamp((self.funds / 2500) * 100 - self.lost_revenue / 55, 0, 100)
        time_score = clamp(100 - max(0, self.days - 500) / 5 - self.operation_seconds / 8, 0, 100)
        health_score = self.equipment_average_health()
        dispatch_score = clamp(80 + self.completed_dispatch * 8 - self.dispatch_failures * 12, 0, 100)
        total = (self.safety * 0.15 + self.protection_score * 0.15 +
                 self.defense_score() * 0.14 + health_score * 0.10 +
                 dose_score * 0.10 + economy_score * 0.09 +
                 time_score * 0.06 + dispatch_score * 0.05 +
                 mission_bonus + self.side_goal_bonus())
        return int(clamp(total, 0, 100))

    def record_result(self):
        if self.result_recorded:
            return
        self.result_recorded = True
        self.unlock_endgame_rewards()
        entry = {
            "mission": self.mission_key,
            "mission_name": MISSION_TYPES[self.mission_key]["name"],
            "site": self.site["name"],
            "score": self.calculate_total_score(),
            "stars": self.current_stars() if hasattr(self, "current_stars") else 0,
            "commissioning_quality": round(getattr(self, "commissioning_quality", 100.0), 1),
            "safety": self.safety,
            "protection": self.protection_score,
            "defense": self.defense_score(),
            "health": self.equipment_average_health(),
            "mode": self.play_mode,
            "dose": round(self.collective_dose, 2),
            "operation_seconds": self.operation_seconds,
            "lost_revenue": round(self.lost_revenue, 1),
            "service_count": self.service_count,
            "violations": self.work_plan_violations,
            "dispatch_done": self.completed_dispatch,
            "dispatch_fail": self.dispatch_failures,
            "side_goals": [{"key": g["key"], "name": g["name"], "done": self.goal_completed(g["key"])} for g in self.side_goals],
            "achievements": list(self.achievements_unlocked),
            "gallery": list(self.gallery_unlocked),
            "strategy_style": self.strategy_style() if hasattr(self, "strategy_style") else "平衡型",
            "strategy_history": list(getattr(self, "strategy_history", [])),
            "decision_review": list(getattr(self, "decision_review", []))[-8:],
            "days": round(self.days, 1),
        }
        valid_records = [item for item in self.records if isinstance(item, dict)]
        valid_records.append(entry)
        grouped = {}
        for item in valid_records:
            mission = item.get("mission", "guided")
            mode = item.get("mode", "guided")
            if mission not in MISSION_TYPES:
                continue
            if mode not in PLAY_MODES:
                mode = "guided"
            grouped.setdefault((mode, mission), []).append(item)
        retained = []
        for items in grouped.values():
            retained.extend(sorted(items, key=lambda row: row.get("score", 0), reverse=True)[:5])
        self.records = sorted(retained, key=lambda row: row.get("score", 0), reverse=True)[:30]
        self.write_records()

    def finish_challenge(self):
        """手动结束本局：运行中需先完成处置；自动停堆后允许直接进入事故报告。"""
        if self.stage != 4:
            return
        if self.challenge_finished:
            self.report = True
            return
        if self.warning_event or self.fault or self.dose_task:
            self.dashboard_page = "status"
            self.set_message("仍有待处置事件：请先完成当前处置，再结束挑战。", WARNING)
            self.show_banner("无法结束挑战", "请先完成当前预警、故障或作业任务", WARNING, 3.5)
            return
        pending = self.barrier_repair_required()
        if not self.scrammed and (self.service_job or pending):
            title = self.service_job["title"] if self.service_job else pending["name"]
            self.dashboard_page = "maintenance"
            self.set_message("仍有维护/整改任务未完成：" + title + "。", WARNING)
            self.show_banner("存在运行限制", "完成维护与屏障恢复任务后再结束挑战", WARNING, 3.5)
            return
        if self.scrammed:
            self.service_job = None
            self.log_event("review", "停堆状态已冻结，进入事故复盘报告")
        self.challenge_finished = True
        self.slider_drag = False
        self.dragging = None
        self.operation_done = []
        self.record_result()
        self.audio.play("settlement" if not self.scrammed else "alarm")
        self.report = True
        self.set_message("本局挑战已结束，最终成绩与事件状态已锁定并保存。", GOOD)

    def return_to_menu(self):
        """返回任务选择界面，保留节点与成绩；已结束的一局保持冻结。"""
        self.report = False
        self.info_card = None
        self.work_plan_open = False
        self.review_open = False
        self.slider_drag = False
        self.dragging = None
        self.menu = True
        self.challenge_finished = True
        self.message = "可新建任务，或继续读取已保存的阶段节点。"
        self.message_color = BLUE

    def best_score_for_mission(self, key: str, mode: Optional[str] = None) -> Optional[int]:
        """任务分数按玩法模式分别统计，旧记录默认视为引导模式。"""
        target_mode = mode or self.play_mode
        scores = [
            item.get("score", 0) for item in self.records
            if item.get("mission") == key and item.get("mode", "guided") == target_mode
        ]
        return max(scores) if scores else None

    def start_project(self, mission_key: str):
        selected_mode = getattr(self, "selected_mode", "guided")
        if not isinstance(selected_mode, str) or selected_mode not in PLAY_MODES:
            selected_mode = "guided"
        if not isinstance(mission_key, str) or mission_key not in MISSION_TYPES:
            mission_key = "guided"
        if selected_mode in ("starter", "demo"):
            mission_key = "guided"
        self.reset(clear_save=True)
        self.selected_mode = selected_mode
        self.play_mode = selected_mode
        self.tutorial = PLAY_MODES[self.play_mode]["tutorial"]
        self.focus_ui = self.play_mode != "challenge"
        self.show_blueprint_labels = False
        self.mission_key = mission_key
        self.site = deepcopy(SITE_TYPES[0])
        self.site_selection_open = not self.is_starter_mode()
        starter_support = 500 if self.is_starter_mode() else 0
        # 非极简模式先进入“选址小地图”，场址的资金/冷源效果在玩家选择后生效。
        self.funds = float(MISSION_TYPES[mission_key]["funds"] + (self.site["fund_delta"] if self.is_starter_mode() else 0) + starter_support)
        self.side_goals = self.generate_side_goals()
        self.next_dispatch = float("inf") if self.is_starter_mode() else 22.0
        self.menu = False
        # 新手总览弹窗已删除，进入任务后直接操作。
        if hasattr(self, "level_manager"):
            self.level_manager.set_current(self.stage)
        self.save_checkpoint()
        self.level_started_at = pygame.time.get_ticks()
        if self.is_starter_mode():
            self.set_message("极简教学开始：按左侧当前目标拖拽设备，先熟悉基本流程。", BLUE)
        else:
            self.set_message("请先在小地图中选择厂址；不同厂址会改变资金、冷却水条件和运行预警倾向。", BLUE)

    def read_save_file(self) -> dict:
        """容错读取节点存档；自动迁移旧结构，损坏文件会备份后忽略。"""
        self.save_meta = {"save_version": SAVE_VERSION, "game_version": GAME_VERSION}
        try:
            if not self.save_path.exists():
                return {}
            payload = json.loads(self.save_path.read_text(encoding="utf-8"))
            migrated = self.migrate_save_payload(payload)
            self.save_meta = {"save_version": migrated.get("save_version", SAVE_VERSION),
                              "game_version": migrated.get("game_version", GAME_VERSION)}
            if hasattr(self, "level_manager"):
                self.level_manager.load_save(migrated.get("level_state", {}))
            # 如果是旧版本，立即写回当前结构，避免下次继续迁移。
            if payload.get("save_version") != SAVE_VERSION:
                self.checkpoints = migrated["checkpoints"]
                self.write_save_file()
            return migrated["checkpoints"]
        except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
            self.backup_save_file("corrupt")
            return {}

    def write_save_file(self):
        try:
            payload = {"save_version": SAVE_VERSION, "game_version": GAME_VERSION,
                       "checkpoints": self.checkpoints,
                       "level_state": self.level_manager.to_save() if hasattr(self, "level_manager") else {}}
            self.safe_write_json(self.save_path, payload)
        except OSError:
            self.set_message("节点存档写入失败，请检查文件夹权限。", WARNING)

    def snapshot(self) -> dict:
        return {
            "save_version": SAVE_VERSION, "game_version": GAME_VERSION,
            "stage": self.stage, "placed": list(self.placed.keys()), "selected": self.selected,
            "mission_key": self.mission_key, "play_mode": self.play_mode, "site": deepcopy(self.site),
            "side_goals": deepcopy(self.side_goals),
            "equipment_variants": deepcopy(self.equipment_variants),
            "parameter_adjustments": deepcopy(getattr(self, "parameter_adjustments", {})),
            "commissioning_quality": getattr(self, "commissioning_quality", 100.0),
            "last_choice_effect": getattr(self, "last_choice_effect", ""),
            "decision_review": deepcopy(getattr(self, "decision_review", [])),
            "active_tab": self.active_tab, "pump_choice": self.pump_choice,
            "funds": self.funds, "days": self.days, "safety": self.safety,
            "mistakes": self.mistakes, "cooling_flow": self.cooling_flow,
            "protection_score": self.protection_score, "protection_verified": self.protection_verified,
            "collective_dose": self.collective_dose, "max_task_dose": self.max_task_dose,
            "operation_seconds": self.operation_seconds, "lost_revenue": self.lost_revenue,
            "work_plan_violations": self.work_plan_violations, "service_count": self.service_count,
            "equipment_health": deepcopy(self.equipment_health),
            "installed_costs": deepcopy(self.installed_costs),
            "primary_pump_safety_delta": self.primary_pump_safety_delta,
            "starter_fault_handled": self.starter_fault_handled,
            "dispatch_task": deepcopy(self.dispatch_task),
            "dispatch_left": self.dispatch_left,
            "next_dispatch": self.next_dispatch,
            "completed_dispatch": self.completed_dispatch,
            "dispatch_failures": self.dispatch_failures,
            "achievements_unlocked": deepcopy(self.achievements_unlocked),
            "gallery_unlocked": deepcopy(self.gallery_unlocked),
            "quiz": deepcopy(self.quiz), "critical_step": self.critical_step,
            "runtime": self.runtime, "next_fault": self.next_fault, "next_dose_task": self.next_dose_task,
            "history": deepcopy(self.history), "dashboard_page": self.dashboard_page,
            "barriers": deepcopy(self.barriers), "event_log": deepcopy(self.event_log),
            "grace_used": list(self.grace_used), "validation_penalties": list(self.validation_penalties),
            "challenge_finished": False, "scrammed": self.scrammed,
            "show_blueprint_labels": getattr(self, "show_blueprint_labels", False),
            "upgrades": {key: {"level": up.level} for key, up in self.upgrades.items()},
        }

    def save_checkpoint(self) -> bool:
        """每个阶段仅在首次到达时存档一次，不能覆盖已有节点。"""
        key = str(self.stage)
        if key in self.checkpoints:
            return False
        self.checkpoints[key] = self.snapshot()
        self.write_save_file()
        return True

    def latest_saved_stage(self) -> Optional[int]:
        stages = [int(key) for key in self.checkpoints.keys() if str(key).isdigit()]
        return max(stages) if stages else None

    def restore_checkpoint(self, stage: Optional[int] = None) -> bool:
        stage = self.latest_saved_stage() if stage is None else stage
        data = self.checkpoints.get(str(stage)) if stage is not None else None
        if not isinstance(data, dict):
            self.set_message("节点存档不可读取或已损坏。", WARNING)
            return False

        mission_key = data.get("mission_key", "guided")
        play_mode = data.get("play_mode", "guided")
        if not isinstance(mission_key, str) or mission_key not in MISSION_TYPES:
            mission_key = "guided"
        if not isinstance(play_mode, str) or play_mode not in PLAY_MODES:
            play_mode = "guided"

        self.stage = self.safe_int(data.get("stage", 0), 0, 0, len(STAGE_NAMES) - 1)
        if hasattr(self, "level_manager"):
            self.level_manager.set_current(self.stage)
        placed = data.get("placed", [])
        if not isinstance(placed, list):
            placed = []
        self.placed = {key: ALL_MODULES[key].slot.copy()
                       for key in placed if isinstance(key, str) and key in ALL_MODULES}
        selected = data.get("selected")
        self.selected = selected if isinstance(selected, str) and selected in ALL_MODULES else None
        self.mission_key = mission_key
        self.play_mode = play_mode
        self.selected_mode = play_mode
        self.tutorial = PLAY_MODES[play_mode]["tutorial"]
        self.focus_ui = play_mode != "challenge"
        self.show_blueprint_labels = bool(data.get("show_blueprint_labels", False))
        self.site = self.normalize_site(data.get("site", SITE_TYPES[0]))
        self.site_selection_open = False
        saved_goals = data.get("side_goals", [])
        self.side_goals = [dict(g) for g in saved_goals if isinstance(g, dict) and "key" in g] if isinstance(saved_goals, list) else []
        if not self.side_goals and not self.is_starter_mode():
            self.side_goals = self.generate_side_goals()
        saved_variants = data.get("equipment_variants", {})
        self.equipment_variants = {"steam_gen": "standard", "turbine": "standard", "condenser": "standard"}
        if isinstance(saved_variants, dict):
            for key, value in saved_variants.items():
                if key in EQUIPMENT_VARIANTS and value in EQUIPMENT_VARIANTS[key]:
                    self.equipment_variants[key] = value
        saved_adjustments = data.get("parameter_adjustments", {})
        self.parameter_adjustments = {"condenser_pressure": 0.0, "primary_flow": 0.0, "sg_level": 0.0, "temperature": 0.0}
        if isinstance(saved_adjustments, dict):
            for key in self.parameter_adjustments:
                self.parameter_adjustments[key] = self.safe_float(saved_adjustments.get(key), 0.0, -20.0, 20.0)
        self.commissioning_quality = self.safe_float(data.get("commissioning_quality"), 100.0, 50.0, 110.0)
        self.last_choice_effect = data.get("last_choice_effect") if isinstance(data.get("last_choice_effect"), str) else "选址、调试和事故处置会影响关键参数。"
        saved_decisions = data.get("decision_review", [])
        self.decision_review = [item for item in saved_decisions if isinstance(item, dict)][-18:] if isinstance(saved_decisions, list) else []

        active_tab = data.get("active_tab", "反应堆")
        self.active_tab = active_tab if isinstance(active_tab, str) and active_tab in EQUIP_TABS else "反应堆"
        if play_mode == "starter" and self.active_tab == "防护":
            self.active_tab = "反应堆"
        pump_choice = data.get("pump_choice", "监测强化")
        # 兼容旧存档：上一版曾使用“轴封泵/屏蔽泵”，本版统一改为 CPR1000 主泵轴封维护/监测强化方案。
        legacy_pump_map = {"轴封泵": "轴封维护", "屏蔽泵": "监测强化"}
        if isinstance(pump_choice, str):
            pump_choice = legacy_pump_map.get(pump_choice, pump_choice)
        self.pump_choice = pump_choice if isinstance(pump_choice, str) and pump_choice in self.primary_choice_buttons else "监测强化"

        self.funds = self.safe_float(data.get("funds"), MISSION_TYPES[mission_key]["funds"], 0)
        self.days = self.safe_float(data.get("days"), 0, 0)
        self.safety = self.safe_int(data.get("safety"), 100, 0, 100)
        self.mistakes = self.safe_int(data.get("mistakes"), 0, 0)
        self.cooling_flow = self.safe_float(data.get("cooling_flow"), 75, 40, 100)
        self.protection_score = self.safe_int(data.get("protection_score"), 100, 0, 100)
        self.protection_verified = bool(data.get("protection_verified", False))
        self.collective_dose = self.safe_float(data.get("collective_dose"), 0, 0)
        self.max_task_dose = self.safe_float(data.get("max_task_dose"), 0, 0)
        self.operation_seconds = self.safe_int(data.get("operation_seconds", data.get("operation_minutes", 0)), 0, 0)
        self.lost_revenue = self.safe_float(data.get("lost_revenue"), 0, 0)
        self.work_plan_violations = self.safe_int(data.get("work_plan_violations"), 0, 0)
        self.service_count = self.safe_int(data.get("service_count"), 0, 0)

        saved_health = data.get("equipment_health", {})
        self.equipment_health = {key: 100.0 for key in HEALTH_META}
        if isinstance(saved_health, dict):
            for key in self.equipment_health:
                self.equipment_health[key] = self.safe_float(saved_health.get(key), 100, 0, 100)
        self.service_job = None
        self.health_clock = 0.0
        self.power_cap = 1.0
        saved_costs = data.get("installed_costs", {})
        self.installed_costs = {}
        if isinstance(saved_costs, dict):
            for key, value in saved_costs.items():
                if isinstance(key, str) and key in self.placed:
                    self.installed_costs[key] = self.safe_int(value, ALL_MODULES[key].cost, 0)
        self.primary_pump_safety_delta = self.safe_int(data.get("primary_pump_safety_delta"), 0, -4, 3)
        self.starter_fault_handled = bool(data.get("starter_fault_handled", False))

        default_quiz = {"flush": None, "seal": None, "diesel_a_test": False, "diesel_b_test": False}
        saved_quiz = data.get("quiz", default_quiz)
        self.quiz = default_quiz.copy()
        if isinstance(saved_quiz, dict):
            self.quiz["flush"] = True if saved_quiz.get("flush") is True else None
            self.quiz["seal"] = True if saved_quiz.get("seal") is True else None
            self.quiz["diesel_a_test"] = bool(saved_quiz.get("diesel_a_test", False))
            self.quiz["diesel_b_test"] = bool(saved_quiz.get("diesel_b_test", False))
        self.critical_step = self.safe_int(data.get("critical_step"), 0, 0, 4)
        self.runtime = self.safe_float(data.get("runtime"), 0, 0)
        self.next_fault = max(self.runtime, self.safe_float(data.get("next_fault"), self.first_warning_time(), 0))
        self.next_dose_task = max(self.runtime, self.safe_float(data.get("next_dose_task"), self.first_dose_time(), 0))
        saved_dispatch = data.get("dispatch_task")
        self.dispatch_task = deepcopy(saved_dispatch) if isinstance(saved_dispatch, dict) else None
        self.dispatch_left = self.safe_float(data.get("dispatch_left"), 0, 0)
        self.next_dispatch = max(self.runtime, self.safe_float(data.get("next_dispatch"), 24, 0))
        self.completed_dispatch = self.safe_int(data.get("completed_dispatch"), 0, 0)
        self.dispatch_failures = self.safe_int(data.get("dispatch_failures"), 0, 0)
        saved_achievements = data.get("achievements_unlocked", [])
        self.achievements_unlocked = [a for a in saved_achievements if isinstance(a, str) and a in ACHIEVEMENTS] if isinstance(saved_achievements, list) else []
        saved_gallery = data.get("gallery_unlocked", [])
        self.gallery_unlocked = [a for a in saved_gallery if isinstance(a, str) and a in GALLERY_ITEMS] if isinstance(saved_gallery, list) else []

        saved_history = data.get("history", {})
        self.history = {"temp": [], "pressure": [], "power": []}
        if isinstance(saved_history, dict):
            for key in self.history:
                values = saved_history.get(key, [])
                if isinstance(values, list):
                    self.history[key] = [self.safe_float(value, 0) for value in values
                                         if isinstance(value, (int, float))][-BALANCE.history_samples:]
        self.dashboard_page = data.get("dashboard_page", "status")
        if self.dashboard_page not in ("status", "trend", "barrier", "maintenance", "atlas", "log"):
            self.dashboard_page = "status"

        default_barriers = {"fuel": 100.0, "primary": 100.0, "safety": 100.0, "environment": 100.0}
        saved_barriers = data.get("barriers", {})
        self.barriers = default_barriers.copy()
        if isinstance(saved_barriers, dict):
            for key in self.barriers:
                self.barriers[key] = self.safe_float(saved_barriers.get(key), self.barriers[key], 0, 100)
        self.event_log = self.normalize_event_log(data.get("event_log", []))
        self.grace_used = set(item for item in data.get("grace_used", []) if isinstance(item, int)) if isinstance(data.get("grace_used"), list) else set()
        self.validation_penalties = set(str(item) for item in data.get("validation_penalties", [])) if isinstance(data.get("validation_penalties"), list) else set()
        self.challenge_finished = False
        self.result_recorded = False
        self.scrammed = bool(data.get("scrammed", False))

        saved_upgrades = data.get("upgrades", {})
        if not isinstance(saved_upgrades, dict):
            saved_upgrades = {}
        for key, up in self.upgrades.items():
            item = saved_upgrades.get(key, {})
            up.level = self.safe_int(item.get("level", 0), 0, 0, 1) if isinstance(item, dict) else 0
            up.in_progress = False
            up.remaining = 0.0

        self.menu = False
        self.report = False
        self.dragging = None
        self.info_card = None
        self.card_scroll = 0
        self.card_max_scroll = 0
        self.fault = None
        self.fault_left = 0.0
        self.dose_task = None
        self.dose_task_left = 0.0
        self.warning_event = None
        self.warning_left = 0.0
        self.operation_done = []
        self.diagnostic_buttons = {}
        self.diagnosis_resolved = True
        self.diagnosis_attempts = 0
        self.work_plan_open = False
        self.work_plan_selection = {"route": None, "staff": None, "equipment": None}
        self.review_open = False
        self.review_answer = None
        self.review_feedback = ""
        self.review_score = 0
        self.review_buttons = {}
        self.slider_drag = False
        self.selected_quiz = None
        self.tip_index = 0
        self.banner = None
        self.feedback_rings = []
        self.feedback_particles = []
        self.update_parameters(0)
        self.set_message(f"已返回节点：{STAGE_NAMES[self.stage]}。", GOOD)
        if self.tutorial:
            self.open_stage_guide()
        return True


