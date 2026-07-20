# -*- coding: utf-8 -*-
"""由 gameplay.py 拆分出的模块。

本文件只存放一类玩法逻辑，避免单个 gameplay.py 过大。
"""

import math
from typing import List, Tuple
from .theme import *
from .catalog import *
from .story_data import STORY_STAGE_NAMES
from .ui_helpers import clamp

STAGE_NAMES = STORY_STAGE_NAMES

class ParameterSystemMixin:
    def ensure_parameter_state(self):
        """确保参数影响字典存在且字段完整。"""
        defaults = {"condenser_pressure": 0.0, "primary_flow": 0.0, "sg_level": 0.0, "temperature": 0.0}
        current = getattr(self, "parameter_adjustments", None)
        if not isinstance(current, dict):
            self.parameter_adjustments = defaults.copy()
            return
        for key, value in defaults.items():
            self.parameter_adjustments.setdefault(key, value)

    def apply_parameter_delta(self, key: str, delta: float, lower: float = -30.0, upper: float = 30.0):
        """统一修改参数影响，避免各处直接改 parameter_adjustments。"""
        self.ensure_parameter_state()
        try:
            value = float(delta)
        except (TypeError, ValueError):
            return
        self.parameter_adjustments[key] = clamp(float(self.parameter_adjustments.get(key, 0.0)) + value, lower, upper)
        label_map = {
            "condenser_pressure": "冷凝器绝对压力",
            "primary_flow": "一回路流量",
            "sg_level": "蒸汽发生器水位",
            "temperature": "一回路平均温度",
        }
        if hasattr(self, "mark_param_change") and key in label_map:
            display_color = GOOD if value < 0 and key == "condenser_pressure" else WARNING if value >= 0 else GOOD
            self.mark_param_change(label_map[key], display_color)
            if hasattr(self, "add_float_text"):
                unit_map = {"condenser_pressure": " kPa", "primary_flow": "%", "sg_level": "%", "temperature": "℃"}
                prefix = "+" if value >= 0 else ""
                self.add_float_text(f"{label_map[key]} {prefix}{value:g}{unit_map.get(key, '')}", RIGHT.centerx, 214, display_color)

    def apply_parameter_effects(self, effect: dict) -> list:
        """应用 Excel/剧本/厂址中的参数影响，返回可展示的反馈文字。"""
        lines = []
        name_map = {
            "condenser_pressure": "冷凝器绝对压力",
            "primary_flow": "一回路流量",
            "sg_level": "蒸汽发生器水位",
            "temperature": "一回路平均温度",
            "funds": "资金",
            "safety": "安全评分",
            "protection_score": "防护评分",
            "cooling_flow": "冷却水流量",
        }
        unit_map = {
            "condenser_pressure": " kPa(a)", "primary_flow": "%", "sg_level": "%",
            "temperature": " ℃", "funds": " 币", "safety": "", "protection_score": "", "cooling_flow": "%",
        }
        for key, raw in (effect or {}).items():
            try:
                value = float(str(raw).replace("+", ""))
            except (TypeError, ValueError):
                continue
            if key in ("funds", "safety", "protection_score", "cooling_flow"):
                old = float(getattr(self, key, 0.0))
                if key in ("safety", "protection_score"):
                    setattr(self, key, clamp(old + value, 0, 100))
                elif key == "cooling_flow":
                    setattr(self, key, clamp(old + value, 40, 100))
                else:
                    setattr(self, key, old + value)
                if hasattr(self, "mark_param_change"):
                    label = name_map.get(key, key)
                    good_positive = key not in ("condenser_pressure",)
                    display_color = GOOD if (value > 0 and good_positive) else DANGER if value < 0 and good_positive else WARNING
                    self.mark_param_change(label, display_color)
                    if hasattr(self, "add_float_text"):
                        prefix = "+" if value >= 0 else ""
                        self.add_float_text(f"{label} {prefix}{value:g}{unit_map.get(key, '')}", RIGHT.centerx, 184, display_color)
            else:
                self.apply_parameter_delta(key, value)
            prefix = "+" if value >= 0 else ""
            lines.append(f"{name_map.get(key, key)} {prefix}{value:g}{unit_map.get(key, '')}")
        return lines

    def apply_site_parameter_effect(self, site: dict) -> list:
        """统一应用厂址对资金、冷源、运行参数的影响。"""
        feedback = []
        money_delta = float(site.get("fund_delta", 0) or 0)
        if money_delta:
            self.funds += money_delta
        parameter_lines = self.apply_parameter_effects(site.get("parameter_effect", {}))
        cooling_bonus = float(site.get("cooling_bonus", 0) or 0)
        if site.get("key") == "coast":
            self.safety = min(100, self.safety + 2)
        elif site.get("key") == "inland":
            self.cooling_flow = max(65, self.cooling_flow - 4)
        feedback.append(f"资金 {'+' if money_delta >= 0 else ''}{int(money_delta)} 币" if money_delta else "资金不变")
        feedback.append(f"冷却水条件 {'+' if cooling_bonus >= 0 else ''}{cooling_bonus:.1f}%")
        feedback.extend(parameter_lines)
        return feedback

    def update_parameters(self, dt: float):
        run = self.stage == 4 and not self.scrammed
        time = self.runtime
        cooling_level = self.cooling_flow / 100.0
        cooling_bonus = 0.11 if self.upgrades["cooling_upgrade"].level else 0
        blade_bonus = 70 if self.upgrades["blade"].level else 0
        condenser_h = self.equipment_health.get("condenser", 100.0)
        pump_h = self.equipment_health.get("primary_pump", 100.0)
        turbine_h = self.equipment_health.get("turbine", 100.0)
        sg_meta = self.variant_meta("steam_gen") or {}
        turbine_meta = self.variant_meta("turbine") or {}
        condenser_meta = self.variant_meta("condenser") or {}
        steam_gen_heat = sg_meta.get("heat", 1.0)
        sg_stability = sg_meta.get("stability", 1.0)
        turbine_eff_variant = turbine_meta.get("eff", 1.0)
        condenser_vacuum_bonus = condenser_meta.get("vacuum", 0.0)
        quality = float(getattr(self, "commissioning_quality", 100.0))
        quality_deficit = max(0.0, 100.0 - quality)
        adjustments = getattr(self, "parameter_adjustments", {})

        if run:
            ramp = min(1.0, time / 7.0)
            thermal = 3050 * ramp
            fault_key = self.fault.key if self.fault else None
            pressure = 15.50 + 0.04 * math.sin(time * 1.5)
            core_temp = 309.5 + min(1.0, thermal / 3050) * 1.8 + 0.4 * math.sin(time) + quality_deficit * 0.012 + adjustments.get("temperature", 0.0)
            primary_flow = (92 + 2 * math.sin(time * 0.9) - max(0, 100 - pump_h) * 0.10
                            - quality_deficit * 0.045 + adjustments.get("primary_flow", 0.0))
            sg_level = 55 + (1.5 / max(0.8, sg_stability)) * math.sin(time * 0.8) - quality_deficit * 0.035 + adjustments.get("sg_level", 0.0)
            steam_pressure = 6.75 * ramp * steam_gen_heat + 0.05 * math.sin(time)
            vacuum = (94 + (cooling_level - 0.75) * 13 + cooling_bonus * 20 +
                      self.site.get("cooling_bonus", 0) + condenser_vacuum_bonus -
                      max(0, 100 - condenser_h) * 0.14)
            if fault_key == "vacuum":
                vacuum -= 18
                core_temp += 2.0
            elif fault_key == "water":
                sg_level -= 16
                steam_pressure -= 0.55
            elif fault_key == "power":
                primary_flow -= 7
                pressure -= 0.18

            if self.warning_event:
                warn_key = self.warning_event["key"]
                warn_progress = clamp(1 - self.warning_left / self.warning_duration(), 0, 1)
                if warn_key == "vacuum":
                    vacuum -= 8 * warn_progress
                    core_temp += 0.8 * warn_progress
                elif warn_key == "water":
                    sg_level -= 9 * warn_progress
                    steam_pressure -= 0.25 * warn_progress
                elif warn_key == "power":
                    primary_flow -= 4 * warn_progress
                    pressure -= 0.08 * warn_progress

            loss_for_cooling = max(0, (0.62 - cooling_level)) * 170
            low_vacuum_loss = max(0, 89 - vacuum) * 9
            auxiliary_use = max(0, cooling_level - 0.75) * 45
            turbine_factor = (0.88 + 0.12 * turbine_h / 100.0) * turbine_eff_variant
            electric = max(0, (thermal * 0.332 * steam_gen_heat - loss_for_cooling - low_vacuum_loss -
                               auxiliary_use + blade_bonus) * turbine_factor)
            self.power_cap = self.current_power_cap()
            electric *= self.power_cap
            transfer = thermal * 0.985
            reject = max(0, thermal - electric)
        else:
            thermal = 0 if self.stage < 3 else 90 + self.critical_step * 110
            pressure = 0 if self.stage < 3 else 15.20 + self.critical_step * 0.07
            core_temp = 25 if self.stage < 3 else 300 + self.critical_step * 2.5
            primary_flow = 0 if self.stage < 3 else (42 if self.critical_step >= 2 else 0)
            sg_level = 0 if self.stage < 3 else 55
            steam_pressure = 0 if self.stage < 3 else self.critical_step * 0.55
            vacuum = 0 if self.stage < 3 else 82
            electric = 0
            transfer = thermal * 0.95
            reject = thermal
            self.power_cap = 1.0

        self.thermal_mw = thermal
        self.output_mw = electric if not self.scrammed else 0
        core_power_percent = clamp(thermal / 3050 * 100, 0, 105)
        # 内部仍保留原有 cooling/vacuum 玩法指标；界面改为更清楚的“绝对压力”。
        # 数值越高表示真空越差。
        condenser_abs_pressure = clamp(13.0 - (vacuum - 88.0) * 0.35 + adjustments.get("condenser_pressure", 0.0) + quality_deficit * 0.025, 4.0, 22.0)
        self.parameters = {
            "堆芯核功率": (core_power_percent, "%FP", 0, 100),
            "一回路平均温度": (core_temp, "℃", 306, 315),
            "一回路压力": (pressure, "MPa", 15.2, 15.85),
            "一回路流量": (primary_flow, "%", 75, 110),
            "蒸汽压力": (steam_pressure, "MPa", 5.7, 7.2),
            "蒸汽发生器水位": (sg_level, "%", 43, 67),
            "冷凝器绝对压力": (condenser_abs_pressure, "kPa(a)", 4.0, 16.0),
            "冷却水流量": (self.cooling_flow, "%", 55, 100),
            "个人剂量": (self.collective_dose, "mSv", 0, TEACHING_DOSE_REDLINE),
            "热功率": (thermal, "MWth", 0, 3200),
            "电功率": (self.output_mw, "MWe", 0, 1200),
            "排热": (reject, "MW", 0, 3300),
            "传热": (transfer, "MW", 0, 3200),
        }

    def alarms(self) -> List[Tuple[str, Tuple[int, int, int]]]:
        if self.stage != 4 or self.scrammed:
            return []
        alarms = []
        t, _, low_t, high = self.parameters["一回路平均温度"]
        condenser_pressure, _, _, high_c = self.parameters["冷凝器绝对压力"]
        water, _, low_w, high_w = self.parameters["蒸汽发生器水位"]
        pressure, _, low_p, high_p = self.parameters["一回路压力"]
        if self.warning_event:
            alarms.append((self.warning_event.get("title", "黄色预警：运行参数异常"), WARNING))
        if t < low_t or t > high:
            alarms.append(("一回路平均温度异常", DANGER))
        if condenser_pressure > high_c:
            alarms.append(("冷凝器绝对压力偏高", WARNING))
        if water < low_w or water > high_w:
            alarms.append(("蒸汽发生器水位异常", DANGER))
        if pressure < low_p or pressure > high_p:
            alarms.append(("一回路压力波动", DANGER))
        if self.fault:
            alarms.append((self.fault.title, DANGER))
        return alarms

