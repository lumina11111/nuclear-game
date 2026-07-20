# -*- coding: utf-8 -*-
"""高级玩法扩展：事故图鉴、事故演化树、专业系统升级、术语显示与答辩路线。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ProfessionalSystemUpgrade:
    key: str
    name: str
    cost: int
    build_time: float
    effect: str
    tags: tuple
    note: str


PROFESSIONAL_SYSTEM_UPGRADES: Dict[str, ProfessionalSystemUpgrade] = {
    "asg": ProfessionalSystemUpgrade(
        "asg", "ASG 泵组冗余", 520, 5.0, "SG 水位事故处置时间 +4s", ("water",),
        "提升辅助给水可用性，蒸汽发生器水位异常时拥有更长处置窗口。",
    ),
    "ris": ProfessionalSystemUpgrade(
        "ris", "RIS 安注训练", 560, 5.5, "LOCA 损失降低", ("safety", "water"),
        "强化高压/低压安注接入训练，降低失水事故造成的屏障损伤。",
    ),
    "eas": ProfessionalSystemUpgrade(
        "eas", "EAS 喷淋覆盖率", 500, 5.0, "安全壳压力恢复更快", ("safety",),
        "提升喷淋覆盖率和碘去除提示，安全壳压力高时处置更稳定。",
    ),
    "edg": ProfessionalSystemUpgrade(
        "edg", "EDG 启动可靠性", 540, 5.0, "LOOP 更难演化为 SBO", ("power",),
        "提高两列应急柴油机启动可靠性，减少 LOOP 后进入复合事故的概率。",
    ),
    "krt": ProfessionalSystemUpgrade(
        "krt", "KRT 布点密度", 430, 4.5, "剂量异常更早预警", ("dose",),
        "增加区域辐射监测布点密度，使剂量任务更早预警并降低作业剂量。",
    ),
    "ety": ProfessionalSystemUpgrade(
        "ety", "ETY 取样与氢监测", 460, 4.5, "氢气事故提前发现", ("safety", "dose"),
        "强化安全壳大气取样与氢气监测，氢气浓度异常时更早提示 EUH/氢复合器。",
    ),
}

ACCIDENT_ATLAS_PAGE_SIZE = 1

# 事故演化链。id 对应事故表编号，用于右侧事故卡与图鉴页展示。
ACCIDENT_EVOLUTION_CHAINS: Dict[int, List[str]] = {
    12: ["冷凝器真空恶化", "汽轮机出力下降", "负荷波动", "蒸汽发生器水位异常"],
    16: ["失去厂外电源 LOOP", "EDG 启动失败", "全厂断电 SBO", "若叠加小破口 LOCA，则进入复合事故"],
    1: ["一回路泄漏", "稳压器水位/压力下降", "RIS 安注投入", "ASG/GCT 辅助导出余热"],
    2: ["大破口 LOCA", "安全壳压力升高", "EAS 喷淋启动", "安全壳隔离与再循环"],
    20: ["锆水反应产生氢气", "ETY 大气监测报警", "EUH/氢复合器投入", "安全壳氢风险受控"],
}

# 错误处置或超时后，下一次异常可能按这个关系演化。
DERIVED_ACCIDENT_MAP = {
    12: 11,  # 真空恶化 -> SG 水位异常
    16: 17,  # LOOP -> SBO + 小破口 LOCA
    1: 2,    # 小破口处置失败 -> 更严重失水演示
    8: 15,   # 主蒸汽管破裂 -> 安全壳压力高
    20: 15,  # 氢气风险 -> 安全壳压力/环境监测复盘
}

TERM_MODE_NAMES = {
    "normal": "普通术语",
    "professional": "专业术语",
    "defense": "答辩术语",
}

SYSTEM_TERM_LABELS = {
    "edg": ("应急供电系统", "EDG 应急柴油发电机"),
    "asg": ("应急给水系统", "ASG 辅助给水系统"),
    "ris": ("应急注水系统", "RIS 安全注入系统"),
    "eas": ("安全壳喷淋", "EAS 安全壳喷淋系统"),
    "krt": ("区域辐射监测", "KRT 区域辐射监测"),
    "ety": ("安全壳大气监测", "ETY 安全壳大气监测"),
    "euh": ("氢气复合器", "EUH 安全壳消氢/氢复合器"),
}

LEVEL_THEMES = [
    ("厂址与土建", "取排水构筑物、安全壳、厂房"),
    ("主回路安装", "RCP、主泵、蒸汽发生器、稳压器"),
    ("常规岛并网", "汽轮机、冷凝器、CRF、发电机"),
    ("专设安全设施", "RIS、EAS、ASG、EDG"),
    ("辐射防护与事故复盘", "KRT、ETY、EUH、三道屏障"),
]

DEMO_ROUTES = {
    "route_build": ("基础建设演示", "选址 → 土建 → 主设备安装 → 并网 → 结算"),
    "route_accident": ("事故链演示", "触发 LOOP → EDG 启动 → ASG 投入 → 成功恢复"),
    "route_radiation": ("辐射防护演示", "KRT 报警 → 剂量分级 → 时间/距离/屏蔽处置 → 复盘"),
    "route_atlas": ("20 个事故图鉴演示", "展示事故图鉴、解锁状态和正确处置记录"),
}


def format_term(system_key: str, mode: str) -> str:
    simple, professional = SYSTEM_TERM_LABELS.get(system_key, (system_key, system_key))
    if mode == "professional":
        return professional
    if mode == "defense":
        return f"{simple}（{professional}）"
    return simple


def chain_text(case_id: int) -> str:
    chain = ACCIDENT_EVOLUTION_CHAINS.get(int(case_id), []) if case_id else []
    return " → ".join(chain)
