# -*- coding: utf-8 -*-
"""游戏目录数据。

设备、厂址、事故卡、任务库等静态数据集中放在这里，
engine.py 只负责流程和交互，剧本人员继续主要修改 story_data.py。
"""

from dataclasses import dataclass
from typing import Dict, Tuple

import pygame

from .models import Module
from .theme import (
    BLUE, CYAN, DEEP_BLUE, GREEN, ORANGE, PURPLE, RED, STEEL, YELLOW
)
from .reference_content import (
    SYSTEM_TECHNICAL_NOTES, DATA_SOURCE_NOTE, accident_case_for_event, format_measures
)

# ========================= 模块与位置 =========================
CIVIL: Dict[str, Module] = {
    "foundation": Module("foundation", "核岛地基", "土建", pygame.Rect(300, 550, 360, 38), STEEL, 450, 40,
                         "承载核岛设备和安全壳的基础结构。", "核电土建需要严格控制基础稳定性。"),
    "containment": Module("containment", "安全壳", "土建", pygame.Rect(300, 178, 360, 372), PURPLE, 800, 95,
                          "包容反应堆系统的重要防护边界。", "安全壳用于限制事故条件下的放射性释放。", ("foundation",)),
    "turbine_hall": Module("turbine_hall", "汽机厂房", "土建", pygame.Rect(706, 182, 306, 160), STEEL, 520, 58,
                           "容纳汽轮机、发电机等二回路设备。", "核岛与常规岛承担不同系统功能。", ("foundation",)),
    "cooling_base": Module("cooling_base", "取排水构筑物", "土建", pygame.Rect(920, 456, 182, 104), DEEP_BLUE, 390, 44,
                           "为冷凝器提供低温冷却水。", "冷却环节直接影响循环效率。", ("foundation",)),
}

EQUIPMENT: Dict[str, Module] = {
    "vessel": Module("vessel", "压力容器", "反应堆", pygame.Rect(335, 284, 112, 186), ORANGE, 620, 55,
                     "容纳燃料组件和冷却剂的承压设备。", "压水堆一回路在高压下保持液态。", ("containment",)),
    "core": Module("core", "堆芯", "反应堆", pygame.Rect(350, 342, 82, 96), RED, 520, 36,
                   "核燃料组件所在区域，是热量产生的核心区域。", "游戏中仅展示能量转换，不模拟核物理细节。", ("vessel",)),
    "crdm": Module("crdm", "控制棒驱动机构", "反应堆", pygame.Rect(305, 236, 168, 42), YELLOW, 260, 22,
                   "驱动控制棒改变反应性。", "控制棒是反应堆控制和停堆的重要手段。", ("vessel", "core")),
    "pressurizer": Module("pressurizer", "稳压器", "常规", pygame.Rect(468, 258, 70, 110), YELLOW, 280, 20,
                          "稳定一回路压力。", "压水堆典型一回路压力约为15.5 MPa，仅作科普展示。", ("containment",)),
    "steam_gen": Module("steam_gen", "蒸汽发生器", "常规", pygame.Rect(552, 245, 91, 176), CYAN, 460, 42,
                        "将一回路热量传递给二回路。", "一、二回路介质不直接混合。", ("containment",)),
    "primary_pump": Module("primary_pump", "主泵", "常规", pygame.Rect(475, 474, 82, 52), ORANGE, 280, 24,
                           "驱动一回路冷却剂流动。", "监测强化方案成本更高，但可降低主泵轴封与流量异常的运行风险。", ("containment",)),
    "turbine": Module("turbine", "汽轮机", "常规", pygame.Rect(735, 228, 122, 68), CYAN, 390, 32,
                      "将蒸汽能转化为轴功。", "叶片效率会影响电功率。", ("turbine_hall",)),
    "generator": Module("generator", "发电机", "常规", pygame.Rect(891, 228, 114, 68), YELLOW, 360, 30,
                        "将机械能转化为电能。", "并网后发电量会转化为运营资金。", ("turbine_hall", "turbine")),
    "condenser": Module("condenser", "冷凝器", "常规", pygame.Rect(744, 378, 158, 76), BLUE, 300, 26,
                        "将排汽冷凝成给水，维持低背压。", "冷凝器绝对压力升高（真空变差）会降低输出功率。", ("turbine_hall",)),
    "secondary_pump": Module("secondary_pump", "给水泵", "常规", pygame.Rect(635, 482, 82, 52), BLUE, 180, 16,
                             "将凝结水送回蒸汽发生器。", "给水稳定有助于保持蒸汽发生器水位。", ("steam_gen",)),
    "cooling": Module("cooling", "循环冷却水系统（CRF）", "常规", pygame.Rect(930, 466, 170, 78), DEEP_BLUE, 340, 30,
                      "向冷凝器提供循环冷却水。", "提高冷却流量可改善真空，但会增加辅机负担。", ("cooling_base",)),
    "tertiary_pump": Module("tertiary_pump", "循环水泵", "常规", pygame.Rect(878, 600, 82, 48), DEEP_BLUE, 170, 14,
                            "推动三回路冷却水循环。", "三回路不进入核岛设备。", ("cooling_base",)),
    "diesel_a": Module("diesel_a", "柴油机 A列", "安全", pygame.Rect(306, 614, 124, 54), GREEN, 330, 20,
                       "失去厂外电源时提供应急电力。", "安全系统采用冗余设计提高可靠性。", ("containment",)),
    "diesel_b": Module("diesel_b", "柴油机 B列", "安全", pygame.Rect(442, 614, 124, 54), GREEN, 330, 20,
                       "与A列相互独立的应急供电。", "两列独立应急供电是本关安全验收要求。", ("containment",)),
    "spray": Module("spray", "安全壳喷淋系统", "安全", pygame.Rect(562, 598, 130, 54), GREEN, 290, 18,
                    "异常状态下辅助控制安全壳环境。", "平时不参与发电，但影响安全评分。", ("containment",)),
    "efw": Module("efw", "辅助给水系统（ASG）", "安全", pygame.Rect(704, 596, 142, 54), GREEN, 290, 18,
                  "主给水能力不足时向蒸汽发生器补水，帮助导出堆芯余热。", "水位低低事故中应优先确认 ASG 辅助给水可用。", ("steam_gen",)),
    # 辐射防护系统：不直接提高发电量，但决定装料许可、作业剂量和防护评分
    "bio_shield": Module("bio_shield", "生物屏蔽墙", "防护", pygame.Rect(302, 188, 132, 40), PURPLE, 420, 30,
                         "降低反应堆周围区域剂量率。", "屏蔽是时间、距离、屏蔽三项基本防护方法之一。", ("containment",)),
    "area_monitor": Module("area_monitor", "区域辐射监测（KRT）", "防护", pygame.Rect(500, 185, 150, 40), GREEN, 260, 16,
                           "持续监视作业区域剂量率。", "监测可以在人员进入前发现剂量异常。", ("containment",)),
    "dosimetry": Module("dosimetry", "个人剂量系统", "防护", pygame.Rect(780, 544, 135, 38), GREEN, 300, 18,
                        "记录参与任务人员的累计受照剂量。", "剂量管理应与作业计划同时开展。", ("containment",)),
    "decon": Module("decon", "污染检查与去污站", "防护", pygame.Rect(1000, 578, 125, 39), CYAN, 290, 18,
                    "用于污染检查与简化去污流程。", "污染控制与外照射控制是不同概念。", ("cooling_base",)),
    "effluent_monitor": Module("effluent_monitor", "排放监测仪", "防护", pygame.Rect(1000, 627, 125, 39), GREEN, 280, 17,
                               "监测排放相关环境指标。", "公众与环境防护是核设施评价的重要内容。", ("cooling_base",)),
}

EQUIP_TABS = {
    "反应堆": ["vessel", "core", "crdm"],
    "常规": ["pressurizer", "steam_gen", "primary_pump", "turbine", "generator",
             "condenser", "secondary_pump", "cooling", "tertiary_pump"],
    "安全": ["diesel_a", "diesel_b", "spray", "efw"],
    "防护": ["bio_shield", "area_monitor", "dosimetry", "decon", "effluent_monitor"],
}

PROTECTION_KEYS = ("bio_shield", "area_monitor", "dosimetry", "decon", "effluent_monitor")
DOSE_REFERENCE_LINE = 20.0  # mSv：职业照射年平均参考线，用于黄色提示
DOSE_ORANGE_LINE = 50.0  # mSv：应急作业橙色警戒线，用于加强提示
TEACHING_DOSE_REDLINE = 100.0  # mSv：事故工况教学红线，仅用于游戏失败判定

MISSION_TYPES = {
    "guided": {
        "name": "教学并网",
        "brief": "推荐新手｜熟悉完整流程",
        "goal": "稳定运行25秒，核安全与防护评分均不低于80",
        "funds": 10400,
        "run_time": 25,
    },
    "protection": {
        "name": "防护示范",
        "brief": "关注剂量｜优先采用低剂量方案",
        "goal": "稳定运行30秒，累计剂量低于12mSv且防护评分不低于92",
        "funds": 11100,
        "run_time": 30,
    },
    "economy": {
        "name": "经济保供",
        "brief": "经营挑战｜控制预算并稳定发电",
        "goal": "稳定运行32秒，最终资金不少于1800币且安全评分不低于78",
        "funds": 10000,
        "run_time": 32,
    },
}


GAME_OUTCOME_RULES = {
    "role": "核电项目负责人",
    "core_goal": "完成选址、土建、设备安装、系统调试和并网运行，形成可复盘的安全评价报告。",
    "victory": [
        "完成五个阶段并进入并网运行。",
        "安全评分 ≥ 80，防护评分 ≥ 80。",
        "个人剂量处于分级剂量机制内：20 mSv 为职业参考线，50 mSv 为橙色警戒，100 mSv 为事故教学红线。",
        "达到当前任务目标并查看报告。",
    ],
    "failure": [
        "关键系统资金不足或漏装。",
        "红色故障超时导致停堆。",
        "个人剂量达到 100 mSv 事故教学红线。",
        "安全、防护或屏障评分过低。",
    ],
}

SITE_TYPES = [
    {"key": "river", "name": "临河厂址",
     "brief": "冷却水较稳定，但需关注排水温度变化",
     "cooling_bonus": 3.5, "fund_delta": 0, "warning_bias": "vacuum",
     "parameter_effect": {"condenser_pressure": -0.6, "primary_flow": 0.5},
     "teaching_effect": "冷却水条件较稳、成本适中，后续冷凝器绝对压力略低。"},
    {"key": "coast", "name": "临海厂址",
     "brief": "冷却水充足，但海边设备维护成本增加180币",
     "cooling_bonus": 5.5, "fund_delta": -180, "warning_bias": "power",
     "parameter_effect": {"condenser_pressure": -1.2, "primary_flow": 0.8},
     "teaching_effect": "冷却水条件最好，冷凝器绝对压力更稳定，但前期资金减少。"},
    {"key": "inland", "name": "内陆厂址",
     "brief": "冷却水来源偏紧，获得冷端补贴250币",
     "cooling_bonus": -3.5, "fund_delta": 250, "warning_bias": "vacuum",
     "parameter_effect": {"condenser_pressure": 1.5, "primary_flow": -0.5},
     "teaching_effect": "资金压力较小，但冷源受限，冷凝器绝对压力更容易升高。"},
    {"key": "seismic", "name": "地震设防区",
     "brief": "安全要求高，土建与安全支出增加，评分潜力较好",
     "cooling_bonus": 0.0, "fund_delta": -260, "warning_bias": "power",
     "parameter_effect": {"condenser_pressure": 0.0, "primary_flow": 0.0},
     "teaching_effect": "安全要求高，成本上升，安全评分潜力更好。"},
    {"key": "hot", "name": "高温地区",
     "brief": "冷端压力大，真空预警概率较高，但电价收益更好",
     "cooling_bonus": -2.0, "fund_delta": 180, "warning_bias": "vacuum",
     "parameter_effect": {"condenser_pressure": 1.0, "primary_flow": -0.3},
     "teaching_effect": "收益较好，但高温会削弱冷端裕度。"},
]


# 每局随机抽取的支线目标，增强重玩性。
GOAL_POOL = [
    {"key": "low_dose", "name": "低剂量示范", "desc": "累计任务剂量低于 8 mSv", "bonus": 5},
    {"key": "safe_run", "name": "安全运行", "desc": "安全评分不低于 90", "bonus": 5},
    {"key": "rich_finish", "name": "经济保留", "desc": "结束时剩余资金不少于 2500 币", "bonus": 5},
    {"key": "stable_run", "name": "稳定运行", "desc": "本局累计并网运行不少于 45 秒且未自动停堆", "bonus": 6},
    {"key": "maintenance", "name": "计划检修", "desc": "完成至少 1 次计划检修或屏障恢复", "bonus": 4},
    {"key": "dispatch", "name": "调度响应", "desc": "完成至少 1 次电网调度任务", "bonus": 4},
    {"key": "no_red", "name": "零红色故障", "desc": "本局不发生自动停堆", "bonus": 4},
]

# 设备品质选择。主名称仍使用设备名；品质只影响费用和运行参数。
EQUIPMENT_VARIANTS = {
    "steam_gen": {
        "standard": {"name": "标准型", "cost_delta": 0, "heat": 1.00, "stability": 1.00, "desc": "平衡方案"},
        "efficient": {"name": "高效传热型", "cost_delta": 180, "heat": 1.035, "stability": 0.96, "desc": "发电略高"},
        "stable": {"name": "稳定型", "cost_delta": 160, "heat": 0.995, "stability": 1.10, "desc": "水位更稳"},
    },
    "turbine": {
        "standard": {"name": "标准型", "cost_delta": 0, "eff": 1.00, "aging": 1.00, "desc": "平衡方案"},
        "efficient": {"name": "高效型", "cost_delta": 220, "eff": 1.045, "aging": 1.08, "desc": "收益更高"},
        "durable": {"name": "稳定型", "cost_delta": 160, "eff": 0.99, "aging": 0.82, "desc": "老化更慢"},
    },
    "condenser": {
        "standard": {"name": "普通水冷", "cost_delta": 0, "vacuum": 0.0, "aging": 1.00, "desc": "平衡方案"},
        "reinforced": {"name": "强化水冷", "cost_delta": 210, "vacuum": 2.5, "aging": 0.95, "desc": "真空更稳"},
        "air_assist": {"name": "空冷辅助", "cost_delta": 260, "vacuum": 1.6, "aging": 0.88, "desc": "内陆友好"},
    },
}

# 并网运行期间的电网调度任务。
DISPATCH_TASKS = [
    {"key": "peak", "title": "电网高峰保供", "desc": "保持电功率不低于 900 MWe", "duration": 14, "reward": 180},
    {"key": "water_limit", "title": "高温限水调度", "desc": "冷却水流量不超过 80%，且真空保持安全", "duration": 13, "reward": 160},
    {"key": "maintenance_window", "title": "低负荷维护窗口", "desc": "完成一次检修或将冷却水调到 65% 以下", "duration": 16, "reward": 150},
]

ACHIEVEMENTS = {
    "first_grid": {"name": "第一次并网", "desc": "首次进入并网运行阶段"},
    "low_dose_master": {"name": "低剂量专家", "desc": "累计剂量低于 5 mSv 完成挑战"},
    "safety_guard": {"name": "安全卫士", "desc": "安全评分不低于 95"},
    "economy_master": {"name": "经济大师", "desc": "剩余资金不少于 3000 币"},
    "steady_operator": {"name": "稳定运行者", "desc": "并网运行 45 秒以上且不停堆"},
    "dispatch_responder": {"name": "调度响应员", "desc": "完成至少 1 次电网调度任务"},
    "perfect_goals": {"name": "目标全清", "desc": "完成本局全部支线目标"},
}

GALLERY_ITEMS = {
    "first_grid": {"name": "图鉴：压水堆三回路", "desc": "成功并网后解锁"},
    "safety_guard": {"name": "图鉴：三道屏障 + 监测防线", "desc": "高安全评分后解锁"},
    "low_dose_master": {"name": "图鉴：ALARA 防护最优化", "desc": "低剂量完成后解锁"},
    "dispatch_responder": {"name": "图鉴：电网调度与负荷跟踪", "desc": "完成调度后解锁"},
}

# 运行异常发生时，左侧只显示当前必须使用的工具，避免新手信息过载。
RUN_OPERATION_TOOLS = {
    "backup_cooling": {
        "name": "备用冷却泵", "color": DEEP_BLUE,
        "target_name": "备用冷却接口",
        "target": pygame.Rect(963, 624, 132, 43), "requires": "tertiary_pump",
    },
    "quick_feed": {
        "name": "应急给水接入", "color": BLUE,
        "target_name": "给水接入口",
        "target": pygame.Rect(704, 624, 128, 43), "requires": "efw",
    },
    "dg_a_action": {
        "name": "柴油机 A列", "color": GREEN,
        "target_name": "母线 A",
        "target": pygame.Rect(833, 624, 113, 43), "requires": "diesel_a",
    },
    "dg_b_action": {
        "name": "柴油机 B列", "color": GREEN,
        "target_name": "母线 B",
        "target": pygame.Rect(957, 624, 113, 43), "requires": "diesel_b",
    },
}

EVENT_RULES = {
    "vacuum": {
        "warning": "黄色预警：冷凝器真空趋势恶化",
        "fault": "红色故障：冷凝器真空丧失",
        "guide": "先恢复冷却水与冷端换热；若未恢复，拖拽备用冷却泵。",
        "tools": ["backup_cooling"], "penalty": 11,
    },
    "water": {
        "warning": "黄色预警：蒸汽发生器水位低低趋势",
        "fault": "红色故障：主给水/辅助给水能力不足",
        "guide": "投入 ASG 辅助给水，将“应急给水接入”拖入发光接口。",
        "tools": ["quick_feed"], "penalty": 14,
    },
    "power": {
        "warning": "黄色预警：厂外电源不稳定",
        "fault": "红色故障：失去厂外电源（LOOP）",
        "guide": "按顺序将柴油机 A列、B列拖入应急母线，保持安全设备供电。",
        "tools": ["dg_a_action", "dg_b_action"], "penalty": 18,
    },
}

ACCIDENT_CARDS = {
    "vacuum": {
        "name": "冷凝器绝对压力升高",
        "phenomenon": "冷凝器绝对压力上升，输出功率下降。",
        "cause": "冷端换热能力不足或冷却水流量偏低。",
        "action": "提高冷却水流量；必要时接入备用冷却泵。",
        "wrong": "延误处置会导致真空变差、效率下降并扣减安全评分。",
    },
    "water": {
        "name": "蒸汽发生器水位异常",
        "phenomenon": "蒸汽发生器水位偏离正常区间，蒸汽压力波动。",
        "cause": "给水能力不足或给水调节不稳定。",
        "action": "接入应急给水，优先稳定水位。",
        "wrong": "水位持续恶化会削弱传热裕度并触发故障处置。",
    },
    "power": {
        "name": "外电源异常",
        "phenomenon": "外部供电不稳定，一回路流量与压力出现扰动。",
        "cause": "厂外电源失去风险升高。",
        "action": "按顺序投入柴油机A列、B列，保证应急供电。",
        "wrong": "应急供电未及时投入会造成安全系统可用性下降。",
    },
    "dose": {
        "name": "个人剂量报警",
        "phenomenon": "作业累计剂量快速上升，接近20 mSv教学红线。",
        "cause": "作业路线、人员配置或屏蔽措施不充分。",
        "action": "重新制定低剂量作业方案，优先采用屏蔽或远程作业。",
        "wrong": "剂量超限会导致本局停止并扣减防护评分。",
    },
}

ACCIDENT_DECISION_OPTIONS = {
    "vacuum": [
        {
            "text": "恢复冷却水流量并接入备用冷却",
            "correct": True,
            "feedback": "判断正确：冷凝器真空恶化时应优先恢复冷端换热能力。",
            "effects": ["冷凝器绝对压力 -0.6 kPa(a)", "安全评分 +1", "解锁备用冷却接入"],
            "parameter": "condenser_pressure",
            "delta": -0.6,
        },
        {
            "text": "提高反应堆功率维持出力",
            "correct": False,
            "feedback": "判断错误：提高功率会增加热负荷，使真空继续变差。",
            "effects": ["安全评分 -5", "资金 -80", "倒计时 -4s", "冷凝器绝对压力 +0.8 kPa(a)"],
            "parameter": "condenser_pressure",
            "delta": 0.8,
        },
        {
            "text": "暂停冷却水系统检查",
            "correct": False,
            "feedback": "判断错误：此时暂停冷却水检查会延误恢复，事故链更快升级。",
            "effects": ["安全评分 -4", "资金 -60", "倒计时 -3s"],
            "parameter": "condenser_pressure",
            "delta": 0.5,
        },
    ],
    "water": [
        {
            "text": "投入 ASG 辅助给水并稳定 SG 水位",
            "correct": True,
            "feedback": "判断正确：SG 水位低低趋势应优先投入辅助给水。",
            "effects": ["蒸汽发生器水位 +2.5%", "安全评分 +1", "解锁给水接入口"],
            "parameter": "sg_level",
            "delta": 2.5,
        },
        {
            "text": "降低冷却水流量",
            "correct": False,
            "feedback": "判断错误：冷却水调节不能直接解决给水能力不足。",
            "effects": ["安全评分 -5", "资金 -80", "倒计时 -4s", "蒸汽发生器水位 -1.8%"],
            "parameter": "sg_level",
            "delta": -1.8,
        },
        {
            "text": "只等待自动调节恢复",
            "correct": False,
            "feedback": "判断错误：水位趋势已异常，等待会缩短事故处置窗口。",
            "effects": ["安全评分 -4", "资金 -60", "倒计时 -3s"],
            "parameter": "sg_level",
            "delta": -1.2,
        },
    ],
    "power": [
        {
            "text": "按顺序投入两列应急柴油机供电",
            "correct": True,
            "feedback": "判断正确：失去厂外电源时，应优先保证两列冗余应急供电。",
            "effects": ["一回路流量 +1.2%", "安全评分 +1", "解锁柴油机 A/B 母线接入"],
            "parameter": "primary_flow",
            "delta": 1.2,
        },
        {
            "text": "关闭一列安全系统降低负荷",
            "correct": False,
            "feedback": "判断错误：关闭安全系统会削弱纵深防御。",
            "effects": ["安全评分 -6", "资金 -100", "倒计时 -4s", "一回路流量 -1.0%"],
            "parameter": "primary_flow",
            "delta": -1.0,
        },
        {
            "text": "继续提高汽轮机负荷",
            "correct": False,
            "feedback": "判断错误：外电源不稳定时提高负荷会放大扰动。",
            "effects": ["安全评分 -5", "资金 -80", "倒计时 -3s"],
            "parameter": "primary_flow",
            "delta": -0.7,
        },
    ],
}


@dataclass(frozen=True)
class BalanceConfig:
    """集中维护难度与节奏参数，后续调平衡不再到多处改硬编码。"""
    guided_warning_seconds: float = 18.0
    normal_warning_seconds: float = 13.0
    guided_fault_seconds: float = 16.0
    normal_fault_seconds: float = 12.0
    guided_first_warning: float = 34.0
    normal_first_warning: float = 18.0
    guided_warning_interval: Tuple[float, float] = (46.0, 62.0)
    normal_warning_interval: Tuple[float, float] = (26.0, 37.0)
    guided_dose_seconds: float = 36.0
    normal_dose_seconds: float = 21.0
    guided_first_dose: float = 48.0
    normal_first_dose: float = 25.0
    guided_dose_interval: Tuple[float, float] = (58.0, 75.0)
    normal_dose_interval: Tuple[float, float] = (30.0, 43.0)
    history_samples: int = 100
    banner_seconds: float = 3.8
    install_fx_seconds: float = 0.65


BALANCE = BalanceConfig()

# 剂量任务的基数经过教学平衡调整：直接进入仍是风险选择，但不再几次任务就必然触线。
DOSE_TASK_LIBRARY = [
    {"title": "主泵振动快速核查", "description": "需快速确认设备状态，延误会影响运行收益。",
     "base_dose": 9.0, "deadline": 14, "budget_limit": 190, "power_loss_per_second": 8, "priority": "speed"},
    {"title": "区域剂量复测", "description": "需以剂量控制为优先完成巡测。",
     "base_dose": 13.0, "deadline": 24, "budget_limit": 360, "power_loss_per_second": 3, "priority": "dose"},
    {"title": "蒸汽发生器仪表确认", "description": "专项资金受限，需要兼顾成本与剂量。",
     "base_dose": 11.0, "deadline": 20, "budget_limit": 175, "power_loss_per_second": 5, "priority": "economy"},
    {"title": "故障后应急巡检", "description": "降功率等待作业完成，时间成本明显。",
     "base_dose": 15.0, "deadline": 16, "budget_limit": 290, "power_loss_per_second": 11, "priority": "speed"},
]

PLAY_MODES = {
    "starter": {
        "name": "极简教学",
        "brief": "只保留基本建设、调试与一次基础预警",
        "tutorial": True,
        "diagnosis_hint": True,
    },
    "guided": {
        "name": "普通模式",
        "brief": "显示原因与推荐操作，逐步体验全部系统",
        "tutorial": True,
        "diagnosis_hint": True,
    },
    "demo": {
        "name": "演示模式",
        "brief": "自动推进演示流程，适合答辩展示",
        "tutorial": True,
        "diagnosis_hint": True,
    },
    "challenge": {
        "name": "挑战模式",
        "brief": "隐藏异常原因，需要根据趋势先完成诊断",
        "tutorial": False,
        "diagnosis_hint": False,
    },
}

WORK_PLAN_OPTIONS = {
    "route": {
        "near": {"name": "缩短进入时间", "desc": "停留更短，但暴露较高", "cost": 0, "time": 6, "dose": 1.00},
        "shield_corridor": {"name": "增加临时屏蔽", "desc": "绕行屏蔽区域", "cost": 35, "time": 9, "dose": 0.58},
        "remote_point": {"name": "提高作业距离", "desc": "远离辐射源", "cost": 65, "time": 12, "dose": 0.34},
    },
    "staff": {
        "maintainer": {"name": "检修员", "desc": "执行速度较快", "cost": 0, "time": 0, "dose": 1.00},
        "rp_team": {"name": "检修员+防护员", "desc": "先巡测再作业", "cost": 55, "time": 3, "dose": 0.72},
        "robot_operator": {"name": "机器人操作员", "desc": "远程执行任务", "cost": 150, "time": 5, "dose": 0.23},
    },
    "equipment": {
        "dosimeter": {"name": "穿戴防护装备", "desc": "剂量计与巡测配置", "cost": 20, "time": 0, "dose": 0.90},
        "temp_shield": {"name": "临时屏蔽板", "desc": "屏蔽衰减外照射", "cost": 80, "time": 3, "dose": 0.46},
        "robot_kit": {"name": "区域封锁", "desc": "封锁区域并远程检修", "cost": 170, "time": 5, "dose": 0.22},
    },
}

DIAGNOSTIC_CASES = {
    "vacuum": {
        "symptoms": ["冷凝器绝对压力持续升高", "电功率同步下滑", "蒸汽压力基本稳定"],
        "cause": "冷端换热能力不足",
        "choices": ["冷端换热能力不足", "给水不足", "外电源失去"],
        "teaching": "冷却能力不足会使冷凝器绝对压力升高，降低汽轮机输出。",
    },
    "water": {
        "symptoms": ["蒸汽发生器水位下滑", "蒸汽压力轻微波动", "冷凝器绝对压力基本稳定"],
        "cause": "给水能力不足",
        "choices": ["冷端换热能力不足", "给水能力不足", "外电源失去"],
        "teaching": "水位异常应优先关注给水路径与应急给水能力。",
    },
    "power": {
        "symptoms": ["一回路流量轻微下降", "压力出现波动", "外部供电状态不稳定"],
        "cause": "外电源失去风险",
        "choices": ["冷端换热能力不足", "给水能力不足", "外电源失去风险"],
        "teaching": "厂外电源异常时，需要保证两列独立应急供电可投入。",
    },
}

BARRIER_META = {
    "fuel": ("第一道屏障：燃料包壳", RED),
    "primary": ("第二道屏障：一回路压力边界", ORANGE),
    "safety": ("第三道屏障：安全壳/安全系统", GREEN),
    "environment": ("监测防线：KRT/ETY", BLUE),
}

REVIEW_LIBRARY = {
    "vacuum": {
        "question": "本次真空异常的最可能直接原因是什么？",
        "choices": ["控制棒棒位异常", "冷端换热能力不足", "应急电源未启动"],
        "answer": "冷端换热能力不足",
        "improvement": "提前关注真空趋势，并在黄色预警阶段提高冷却流量或接入备用冷却。",
    },
    "water": {
        "question": "蒸汽发生器水位异常时，优先应核查哪一系统？",
        "choices": ["给水与应急给水系统", "城市电网", "安全壳屏蔽墙"],
        "answer": "给水与应急给水系统",
        "improvement": "维护应急给水可用性，并在水位趋势偏离时提前介入。",
    },
    "power": {
        "question": "厂外电源异常时，维持纵深防御的关键是什么？",
        "choices": ["提升汽轮机叶片效率", "两列独立应急供电及时投入", "关闭排放监测"],
        "answer": "两列独立应急供电及时投入",
        "improvement": "建设阶段保证冗余电源齐全，并在预警出现后按顺序接入。",
    },
    "dose": {
        "question": "作业剂量偏高时，最符合防护最优化的改进方向是？",
        "choices": ["延长现场停留时间", "增加屏蔽或采用远程作业", "取消剂量监测"],
        "answer": "增加屏蔽或采用远程作业",
        "improvement": "在满足任务要求的同时，优先选择屏蔽通道、临时屏蔽或远程工具。",
    },
    "general": {
        "question": "运行中发现异常征兆时，较好的安全文化做法是？",
        "choices": ["忽略轻微异常", "先确认趋势并及时处置", "关闭监测面板"],
        "answer": "先确认趋势并及时处置",
        "improvement": "重视预兆、保守决策、完成复盘，能降低重复事件概率。",
    },
}


HEALTH_META = {
    "primary_pump": {"name": "主泵", "color": ORANGE, "wear": 0.08, "cost": 250, "seconds": 6.0, "restore": 30},
    "condenser": {"name": "冷凝器", "color": BLUE, "wear": 0.11, "cost": 230, "seconds": 6.0, "restore": 34},
    "turbine": {"name": "汽轮机", "color": CYAN, "wear": 0.07, "cost": 270, "seconds": 7.0, "restore": 30},
    "diesel_a": {"name": "柴油机 A列", "color": GREEN, "wear": 0.045, "cost": 190, "seconds": 5.0, "restore": 32},
    "diesel_b": {"name": "柴油机 B列", "color": GREEN, "wear": 0.045, "cost": 190, "seconds": 5.0, "restore": 32},
    "effluent_monitor": {"name": "排放监测仪", "color": PURPLE, "wear": 0.07, "cost": 160, "seconds": 5.0, "restore": 38},
}

BARRIER_RECOVERY = {
    "fuel": {
        "threshold": 92, "name": "热工状态专项检查", "cost": 260, "seconds": 6.0,
        "restore": 18, "power_cap": 0.76, "why": "燃料包壳屏障受关注，需限制功率并核查热工状态。"
    },
    "primary": {
        "threshold": 92, "name": "一回路密封复测", "cost": 240, "seconds": 5.0,
        "restore": 20, "power_cap": 0.78, "why": "压力边界受损，需通过复测恢复运行许可。"
    },
    "safety": {
        "threshold": 90, "name": "安全系统功能复测", "cost": 280, "seconds": 6.0,
        "restore": 23, "power_cap": 0.82, "why": "冗余安全能力下降，需确认备用系统可用。"
    },
    "environment": {
        "threshold": 90, "name": "监测校准与去污核查", "cost": 180, "seconds": 5.0,
        "restore": 20, "power_cap": 0.86, "why": "环境监测防线下降，需恢复 KRT/ETY 监测可信度。"
    },
}




ALL_MODULES = {**CIVIL, **EQUIPMENT}

# 用资料库中的 CPR1000 系统说明统一覆盖设备知识卡，不改变安装逻辑。
for _key, _note in SYSTEM_TECHNICAL_NOTES.items():
    _module = ALL_MODULES.get(_key)
    if _module:
        _module.info = _note.get("作用定位", _module.info)
        _module.fact = _note.get("资料依据", _module.fact)

# 事故卡从用户事故表中抽取真实事故名称、现象和处置要点，再映射到现有三类游戏机制。
def _apply_reference_accident_cards():
    for _event_key in ("vacuum", "water", "power", "dose"):
        _case = accident_case_for_event(_event_key)
        if _event_key in ACCIDENT_CARDS:
            ACCIDENT_CARDS[_event_key].update({
                "name": _case["name"],
                "phenomenon": _case["phenomenon"],
                "action": format_measures(_case, 2),
                "source": _case["category"],
            })


_apply_reference_accident_cards()
ACCIDENT_REFERENCE_SOURCE = DATA_SOURCE_NOTE

PIPES = [
    (("core", "steam_gen", "primary_pump"), RED,
     [(447, 330), (522, 330), (522, 288), (552, 288)], "一回路热段", "water"),
    (("steam_gen", "primary_pump", "vessel"), ORANGE,
     [(552, 395), (526, 395), (526, 500), (475, 500), (405, 500), (405, 470)], "一回路冷段", "water"),
    (("steam_gen", "turbine"), (211, 226, 236),
     [(598, 245), (598, 188), (795, 188), (795, 228)], "蒸汽管道", "steam"),
    (("turbine", "generator"), STEEL, [(857, 262), (891, 262)], "转轴", "shaft"),
    (("turbine", "condenser"), BLUE,
     [(797, 296), (797, 346), (822, 346), (822, 378)], "排汽管道", "steam"),
    (("condenser", "secondary_pump", "steam_gen"), BLUE,
     [(744, 426), (687, 426), (687, 482), (676, 508), (598, 508), (598, 421)], "二回路给水", "water"),
    (("condenser", "cooling", "tertiary_pump"), DEEP_BLUE,
     [(902, 401), (1030, 401), (1030, 466)], "冷却水进水", "water"),
    (("cooling", "tertiary_pump", "condenser"), DEEP_BLUE,
     [(953, 531), (966, 531), (966, 608), (924, 608), (866, 608), (866, 454)], "冷却水回水", "water"),
    (("generator",), YELLOW, [(1005, 261), (1040, 261), (1118, 181)], "电力输出", "electric"),
]

KNOWLEDGE = {
    "vessel": ("压力容器", "压力容器包围燃料组件并承受一回路高压。\n压水堆运行时一回路水在高压下不沸腾。"),
    "core": ("堆芯", "燃料组件在压力容器内释放热量。\n本游戏将核反应简化为安全的热功率数值。"),
    "crdm": ("控制棒驱动机构", "控制棒通过吸收中子来调节反应性。\n启动和停堆都离不开可靠的控制棒驱动机构。"),
    "pressurizer": ("稳压器", "稳压器用于控制一回路压力。\n科普常用参考值：压水堆约15.5 MPa。"),
    "steam_gen": ("蒸汽发生器", "一回路把热量传给二回路，产生蒸汽。\n两套水系统在结构上隔离。"),
    "turbine": ("汽轮机", "高温蒸汽推动叶片，形成轴功。\n更高效的叶片有助于提高发电输出。"),
    "generator": ("发电机", "汽轮机带动发电机转动，\n将机械能转化为可输送的电力。"),
    "condenser": ("冷凝器", "汽轮机排汽在冷凝器中重新凝结。\n真空良好时，机组循环效率更高。"),
    "cooling": ("循环冷却水系统（CRF）", "三回路带走冷凝器中的排热。\n冷却能力不足会降低功率并触发报警。"),
    "primary_pump": ("主泵", "CPR1000 主泵为带轴封反应堆冷却剂泵。\n本关把选择简化为轴封维护与监测强化两种保障方案。"),
    "diesel_a": ("应急柴油发电机", "厂外电源异常时为安全设备供电。\n本关要求A、B两列独立配置。"),
    "diesel_b": ("应急柴油发电机", "与A列构成冗余应急供电。\n冗余并不是浪费，而是纵深防御思想之一。"),
    "spray": ("安全壳喷淋系统", "用于异常情况下辅助控制安全壳内环境。\n正常发电时通常不参与能量转换。"),
    "efw": ("辅助给水系统（ASG）", "主给水丧失或蒸汽发生器水位低低时，ASG 用于向蒸汽发生器补水。\n本游戏以“应急给水接入”表现其事故缓解作用。"),
    "bio_shield": ("生物屏蔽墙", "屏蔽材料用于降低作业区域的辐射场强度。\n在本关中可显著降低运行剂量任务的受照量。"),
    "area_monitor": ("区域辐射监测（KRT）", "用于持续观察区域剂量率变化。\n安全壳事故监测另由 ETY 大气监测承担。"),
    "dosimetry": ("个人剂量系统", "用于记录工作人员接受的任务剂量。\n本游戏以累计剂量模拟剂量管理过程。"),
    "decon": ("污染检查与去污站", "污染表示放射性物质附着或进入不应到达的位置。\n去污与减少外照射并不是同一件事。"),
    "effluent_monitor": ("排放监测仪", "用于体现对公众和环境的防护监测。\n正常运行也需要持续关注环境指标。"),
}


# 知识卡标题和正文也统一使用资料增强文本。
for _key, _note in SYSTEM_TECHNICAL_NOTES.items():
    _module = ALL_MODULES.get(_key)
    if _module:
        KNOWLEDGE[_key] = (_module.name, _note.get("资料依据", _module.fact))




# ========================= 全事故卡体验强化：新增安全/剂量事故链工具 =========================
RUN_OPERATION_TOOLS.update({
    "spray_action": {
        "name": "EAS 喷淋接入", "color": GREEN,
        "target_name": "喷淋接口",
        "target": pygame.Rect(566, 624, 126, 43), "requires": "spray",
    },
    "radiation_sample": {
        "name": "取样监测", "color": PURPLE,
        "target_name": "监测接口",
        "target": pygame.Rect(566, 624, 126, 43), "requires": "area_monitor",
    },
})

EVENT_RULES.update({
    "safety": {
        "warning": "黄色预警：安全壳/专设安全设施异常",
        "fault": "红色故障：安全壳压力或专设安全设施异常",
        "guide": "确认专设安全设施响应，将 EAS 喷淋接入拖入喷淋接口。",
        "tools": ["spray_action"], "penalty": 17,
    },
    "dose": {
        "warning": "黄色预警：放射性指标异常",
        "fault": "红色故障：包壳/放射性释放风险升高",
        "guide": "启动取样监测，将“取样监测”拖入监测接口，控制剂量和环境监测防线。",
        "tools": ["radiation_sample"], "penalty": 15,
    },
})

ACCIDENT_CARDS.update({
    "safety": {
        "name": "安全壳与专设安全设施异常",
        "phenomenon": "安全壳压力或专设安全设施状态异常。",
        "cause": "LOCA、主蒸汽破裂或保护系统动作导致安全壳风险上升。",
        "action": "确认隔离、喷淋、应急电源和专设安全设施状态。",
        "wrong": "误停喷淋、误复位或延误隔离会使安全壳屏障损伤扩大。",
    },
})

DIAGNOSTIC_CASES.update({
    "safety": {
        "symptoms": ["安全壳压力趋势上升", "专设安全设施状态灯闪烁", "喷淋/隔离联锁出现提示"],
        "cause": "安全壳或专设安全设施异常",
        "choices": ["冷端换热能力不足", "安全壳或专设安全设施异常", "单纯经营资金不足"],
        "teaching": "安全壳压力与专设安全设施相关事故，应优先确认隔离、喷淋和应急电源。",
    },
    "dose": {
        "symptoms": ["放射性指标上升", "个人剂量增长加快", "环境监测防线评分下降"],
        "cause": "放射性释放或包壳屏障异常",
        "choices": ["放射性释放或包壳屏障异常", "汽轮机叶片效率偏低", "冷却水经济性偏低"],
        "teaching": "放射性释放类事故应优先取样监测、净化和降低人员暴露。",
    },
})

REVIEW_LIBRARY.update({
    "safety": {
        "question": "安全壳压力升高或 EAS 启动时，最关键的处置思路是什么？",
        "choices": ["关闭喷淋节省水源", "确认隔离、喷淋和应急电源联动", "提高发电功率"],
        "answer": "确认隔离、喷淋和应急电源联动",
        "improvement": "安全壳相关事故应优先维护第三道屏障完整性，避免误复位或误停运。",
    },
})
