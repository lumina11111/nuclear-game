# -*- coding: utf-8 -*-
"""由用户提供的 CPR1000 教材与事故表整理出的游戏内容库。\n\n本文件只存放教学文本与事故资料，避免把资料性内容散落到界面代码中。\n游戏仍是科普与课堂展示模型，不能作为真实核电运行规程使用。\n"""
from __future__ import annotations

DATA_SOURCE_NOTE = "资料来源：防城港 CPR1000 机组系统与设备教材（上册）与用户提供的事故表。游戏已做简化处理。"

SYSTEM_TECHNICAL_NOTES = {
    "vessel": {
        "作用定位": "固定和包容堆芯、堆内构件与一回路冷却剂，是一回路压力边界的重要部分。",
        "资料依据": "压力容器与一回路管道共同组成高压冷却剂压力边界，也是防止放射性物质外逸的第二道屏障之一。",
        "游戏转化": "压力容器未安装时无法安装堆芯；压力边界受损会降低安全评分并影响一回路压力。",
        "关键词": "RPV｜压力边界｜第二道屏障",
    },
    "core": {
        "作用定位": "堆芯由燃料组件组成，是核裂变释放热量的位置。",
        "资料依据": "教材中 CPR1000 堆芯由 157 个燃料组件组成，燃料棒按 17×17 栅格排列。",
        "游戏转化": "游戏将复杂核物理简化为堆芯核功率、热功率和温度趋势，避免真实运行参数误用。",
        "关键词": "堆芯｜堆芯核功率｜热源",
    },
    "crdm": {
        "作用定位": "驱动控制棒插入、提出或保持棒位，用于调节反应性和紧急停堆。",
        "资料依据": "控制棒在正常运行中调节反应堆功率，在事故工况下快速引入负反应性，使反应堆紧急停堆。",
        "游戏转化": "装料与零功率试验阶段必须完成棒位确认；事故复盘中会把停堆作为最后保护动作。",
        "关键词": "CRDM｜控制棒｜紧急停堆",
    },
    "pressurizer": {
        "作用定位": "控制一回路压力，避免压力过低产生不利沸腾或压力过高损伤设备。",
        "资料依据": "RCP 系统中的稳压器用于控制冷却剂压力；稳压器水位过高会影响汽腔，过低会使电加热器暴露。",
        "游戏转化": "一回路压力偏离正常区间会产生报警，错误事故处置会使压力波动扩大。",
        "关键词": "PZR｜压力控制｜喷淋/加热器",
    },
    "steam_gen": {
        "作用定位": "把一回路热量传递给二回路给水，产生驱动汽轮机的蒸汽。",
        "资料依据": "一回路高温高压水在蒸汽发生器倒 U 形管内流动，将热量传给二回路水，两回路介质不直接混合。",
        "游戏转化": "蒸汽发生器品质影响传热效率和水位稳定；水位低低事故将优先要求 ASG 辅助给水。",
        "关键词": "SG｜一二回路隔离｜传热管",
    },
    "primary_pump": {
        "作用定位": "推动反应堆冷却剂在三条一回路环路中循环，把堆芯热量送往蒸汽发生器。",
        "资料依据": "RCP 系统由反应堆和三条并联闭合环路组成，每条环路设一台主泵和一台蒸汽发生器。",
        "游戏转化": "主泵健康度影响一回路流量；外电源异常或设备老化会造成流量下降。",
        "关键词": "RCP｜主泵｜一回路流量",
    },
    "turbine": {
        "作用定位": "把二回路蒸汽热能转化为汽轮机转子机械能。",
        "资料依据": "压水堆能量转换包含核能→热能→机械能→电能，其中汽轮机负责热能到机械能。",
        "游戏转化": "汽轮机效率影响最终电功率；冷凝器真空变差会降低汽轮机出力。",
        "关键词": "汽轮机｜机械能｜效率",
    },
    "generator": {
        "作用定位": "由汽轮机带动，将机械能转换为电能并通过电气系统送出。",
        "资料依据": "发电机转子与汽轮机转子刚性相连，汽轮机直接带动发电机发电。",
        "游戏转化": "并网成功后电功率转化为运行收益，外电源异常会触发应急供电演示。",
        "关键词": "发电机｜并网｜电功率",
    },
    "condenser": {
        "作用定位": "把汽轮机排汽冷凝成水，并维持较低背压以提升循环效率。",
        "资料依据": "汽轮机作功后的乏汽进入冷凝器，由循环冷却水冷却后凝结成水，再送回给水系统。",
        "游戏转化": "冷凝器绝对压力升高表示真空变差，会降低电功率并触发冷端事故卡。",
        "关键词": "冷凝器｜真空｜冷端风险",
    },
    "secondary_pump": {
        "作用定位": "把凝结水和给水送回蒸汽发生器，维持二回路水位与传热。",
        "资料依据": "二回路中凝结水由凝结水泵、加热器和给水泵送入蒸汽发生器重复使用。",
        "游戏转化": "给水能力不足会造成蒸汽发生器水位低低预警，要求投入 ASG 辅助给水。",
        "关键词": "给水｜SG 水位｜二回路",
    },
    "cooling": {
        "作用定位": "为冷凝器提供循环冷却水，是常规岛冷端稳定的关键。",
        "资料依据": "循环冷却水系统向冷凝器供给冷却水，确保汽轮机冷凝器有效冷却。",
        "游戏转化": "冷却水流量滑块直接影响冷凝器绝对压力；过高流量会增加辅机负担。",
        "关键词": "CRF｜循环冷却水｜冷源",
    },
    "tertiary_pump": {
        "作用定位": "推动三回路循环冷却水流动，支撑冷凝器排热。",
        "资料依据": "循环水泵和取水设施为汽轮机组冷凝器提供冷却水源。",
        "游戏转化": "它是备用冷却泵处置动作的前置条件，缺失时冷端事故无法完整处置。",
        "关键词": "循环水泵｜三回路｜备用冷却",
    },
    "diesel_a": {
        "作用定位": "厂外电源异常时为安全系统提供 A 列应急电力。",
        "资料依据": "当厂外电源和发电机组不可用时，备用柴油发电机组向厂内应急设备供电。",
        "游戏转化": "外电源事故必须按顺序投入 A/B 两列柴油机，体现冗余和独立性。",
        "关键词": "EDG-A｜应急供电｜冗余",
    },
    "diesel_b": {
        "作用定位": "与 A 列独立配置，为安全设备提供 B 列应急电力。",
        "资料依据": "事故表中失去厂外电源要求应急柴油发电机为电动泵供电，维持堆芯余热导出能力。",
        "游戏转化": "少装一列会导致安全验收失败，也会在外电源事故中造成处置不完整。",
        "关键词": "EDG-B｜独立列｜纵深防御",
    },
    "spray": {
        "作用定位": "安全壳压力升高时喷淋降温降压，并配合安全壳隔离限制释放。",
        "资料依据": "事故表中安全壳压力高达到高阈值时触发安全壳喷淋，EAS 启动后两台喷淋泵投入。",
        "游戏转化": "喷淋系统提高安全验收结果，并在事故复盘中作为专设安全设施知识点。",
        "关键词": "EAS｜安全壳喷淋｜降温降压",
    },
    "efw": {
        "作用定位": "辅助给水系统（ASG）在主给水能力不足时向蒸汽发生器补水，帮助导出堆芯余热。",
        "资料依据": "事故表中主给水丧失、蒸汽发生器水位低低等工况要求 ASG 辅助给水投入。",
        "游戏转化": "水位事故中必须拖入“应急给水接入”，安装缺失会导致处置失败。",
        "关键词": "ASG｜辅助给水｜SG 水位",
    },
    "bio_shield": {
        "作用定位": "通过屏蔽降低作业区域剂量率，属于辐射防护配置。",
        "资料依据": "燃料组件和一回路设备具有放射性风险，屏蔽是降低外照射的重要手段。",
        "游戏转化": "生物屏蔽墙显著降低剂量任务中的人员受照剂量。",
        "关键词": "屏蔽｜外照射｜ALARA",
    },
    "area_monitor": {
        "作用定位": "持续监视作业区域剂量率，支持人员进入前的风险判断。",
        "资料依据": "区域辐射监测（KRT）用于厂内在线辐射监测；安全壳事故监测另由 ETY 大气监测承担。",
        "游戏转化": "区域辐射监测（KRT）未配置会降低防护评分；安全壳事故中仍保留 ETY 大气监测提示。",
        "关键词": "KRT｜区域剂量率｜ETY 大气监测",
    },
    "dosimetry": {
        "作用定位": "记录人员累计剂量，支持作业计划和剂量约束管理。",
        "资料依据": "事故表中燃料包壳破损等事件会导致一回路放射性指标上升，需取样和监测。",
        "游戏转化": "采用分级剂量机制：20 mSv 职业参考线、50 mSv 橙色警戒、100 mSv 事故教学红线。",
        "关键词": "个人剂量｜20/50/100 mSv｜分级剂量",
    },
    "decon": {
        "作用定位": "用于污染检查和简化去污，区别于外照射屏蔽。",
        "资料依据": "三废处理和排放系统承担放射性废物收集、处理与排放监测任务。",
        "游戏转化": "它提高防护评分，并在剂量/污染复盘中给出低剂量改进建议。",
        "关键词": "去污｜污染控制｜三废处理",
    },
    "effluent_monitor": {
        "作用定位": "监测排放相关环境指标，是公众与环境防护的一部分。",
        "资料依据": "教材第 8 章涉及放射性废液、废气、固体废物处理与排放监测。",
        "游戏转化": "排放监测仪影响环境监测防线；缺失会降低防护验收结果。",
        "关键词": "排放监测｜环境监测防线｜三废",
    },
}

ACCIDENT_CASE_LIBRARY = [
    {"id": 1, "category": "一回路系统事故", "name": "一回路小破口失水事故", "phenomenon": "RCP 系统冷却剂泄漏，稳压器水位和压力下降。", "measures": ["增加 RCV 上充流量补偿泄漏", "投入安注系统 RIS", "投入 ASG 辅助给水导出堆芯余热", "蒸汽经 GCT 排入凝汽器或大气"], "event_key": "water"},
    {"id": 2, "category": "一回路系统事故", "name": "一回路大破口失水事故", "phenomenon": "主管道脆性断裂，大量冷却剂喷放。", "measures": ["高/中/低压安注向堆芯注水", "安全壳隔离 EIE", "安全壳喷淋 EAS 降温降压", "启动应急柴油发电机"], "event_key": "safety"},
    {"id": 3, "category": "一回路系统事故", "name": "蒸汽发生器传热管破裂 SGTR", "phenomenon": "一次侧放射性水进入二次侧，稳压器水位下降，二回路放射性升高。", "measures": ["确认紧急停堆", "隔离故障蒸汽发生器", "一回路快速降温降压", "平衡一二次侧压力终止泄漏", "启动辅助给水"], "event_key": "water"},
    {"id": 4, "category": "一回路系统事故", "name": "稳压器压力高", "phenomenon": "一回路压力超过保护限值。", "measures": ["触发紧急停堆", "稳压器安全阀自动开启排放蒸汽", "主喷淋投入降压"], "event_key": "power"},
    {"id": 5, "category": "一回路系统事故", "name": "稳压器压力低", "phenomenon": "一回路压力降至低压保护区间。", "measures": ["P7 信号下触发紧急停堆", "稳压器电加热器投入", "必要时启动安注"], "event_key": "water"},
    {"id": 6, "category": "一回路系统事故", "name": "反应堆冷却剂泵卡转子", "phenomenon": "单环路流量低于额定值，冷却能力下降。", "measures": ["高功率下单环路流量低触发紧急停堆", "低功率下双环路流量低触发紧急停堆"], "event_key": "power"},
    {"id": 7, "category": "一回路系统事故", "name": "控制棒弹棒 / 掉棒事故", "phenomenon": "中子通量变化率异常，功率快速扰动。", "measures": ["中子通量变化率高信号触发紧急停堆", "限制弹棒 / 掉棒事故后果"], "event_key": "power"},
    {"id": 8, "category": "二回路系统事故", "name": "主蒸汽管道破裂", "phenomenon": "蒸汽大量失控排放，安全壳压力上升，一回路过冷引入正反应性。", "measures": ["主蒸汽隔离阀自动关闭", "安注系统注入浓硼", "启动 ASG 辅助给水", "启动安全壳喷淋"], "event_key": "safety"},
    {"id": 9, "category": "二回路系统事故", "name": "主给水管道破裂", "phenomenon": "蒸汽发生器给水丧失，堆芯余热无法有效导出。", "measures": ["ASG 辅助给水投入", "蒸汽发生器低低水位触发紧急停堆"], "event_key": "water"},
    {"id": 10, "category": "二回路系统事故", "name": "蒸汽发生器水位高高", "phenomenon": "给水控制系统故障或蒸汽流量突增造成假水位。", "measures": ["P14 信号使汽机脱扣和主给水隔离", "存在 P7 信号时触发紧急停堆"], "event_key": "water"},
    {"id": 11, "category": "二回路系统事故", "name": "蒸汽发生器水位低低", "phenomenon": "给水流量降低或丧失，二回路吸热能力下降。", "measures": ["任意 SG 水位低于低低保护阈值触发紧急停堆", "水位低且汽水失配超阈值触发紧急停堆", "优先投入 ASG 辅助给水"], "event_key": "water"},
    {"id": 12, "category": "二回路系统事故", "name": "冷凝器真空丧失", "phenomenon": "二回路排热能力下降，一回路温度压力上升。", "measures": ["汽机脱扣", "若 GCT 不可用且核功率较高，汽机跳闸触发反应堆停堆", "恢复冷却水与冷端真空"], "event_key": "vacuum"},
    {"id": 13, "category": "专设安全设施相关事故", "name": "安全注入系统 RIS 误启动", "phenomenon": "安注信号误触发。", "measures": ["安注信号 5 分钟后联锁解除", "操纵员手动复位安注信号", "停运 RIS 相关设备"], "event_key": "safety"},
    {"id": 14, "category": "专设安全设施相关事故", "name": "安全壳喷淋系统 EAS 启动", "phenomenon": "安全壳压力达到喷淋启动阈值。", "measures": ["两台喷淋泵启动", "化学添加剂延迟注入", "20 分钟后切换至地坑再循环"], "event_key": "safety"},
    {"id": 15, "category": "专设安全设施相关事故", "name": "安全壳压力高", "phenomenon": "安全壳压力分级上升并触发不同保护动作。", "measures": ["低阈值触发隔离或停堆", "高阈值触发主蒸汽隔离、安全壳隔离和柴油机启动", "最高阈值触发安全壳喷淋"], "event_key": "safety"},
    {"id": 16, "category": "失电与全厂断电事故", "name": "失去厂外电源（LOOP）", "phenomenon": "厂外电源丧失，主泵转速降低，堆芯余热导出能力受挑战。", "measures": ["汽动辅助给水泵自动启动", "应急柴油发电机（EDG）为必要电动设备供电", "通过 ASG 辅助给水与 GCT 蒸汽排放导出余热", "条件满足后投入 RRA 余热排出系统"], "event_key": "power"},
    {"id": 17, "category": "失电与全厂断电事故", "name": "全厂断电叠加小破口 LOCA", "phenomenon": "复合型超设计基准事故，冷却剂泄漏与电源丧失叠加。", "measures": ["一回路卸压", "一回路外部注水", "优化注水时间和流量策略"], "event_key": "power"},
    {"id": 18, "category": "未能紧急停堆的预期瞬态", "name": "丧失正常给水 ATWS", "phenomenon": "二回路吸热能力下降，一回路温度压力上升。", "measures": ["汽机脱扣降低堆功率", "启动辅助给水防止 SG 烧干", "闭锁部分 GCT 排放阀", "通过 CRDM 电源柜断电实现停堆"], "event_key": "water"},
    {"id": 19, "category": "放射性释放与三废处理事故", "name": "燃料元件包壳破损", "phenomenon": "裂变产物逸入一回路，放射性指标上升。", "measures": ["化容系统净化回路除盐过滤", "一回路冷却剂取样监测", "必要时停堆维修"], "event_key": "dose"},
    {"id": 20, "category": "放射性释放与三废处理事故", "name": "安全壳氢气浓度超标", "phenomenon": "锆水反应产生氢气，氢浓度升高。", "measures": ["EUH 安全壳消氢系统 / 氢复合器自动工作", "ETY 系统混合取样监测氢浓度", "LOCA 后确认氢气复合器可用"], "event_key": "safety"},
]

ACCIDENT_SCENARIOS_BY_EVENT = {
    "vacuum": [12],
    "water": [11, 9, 3, 18, 1],
    "power": [16, 6, 7, 4],
    "dose": [19, 20],
    "safety": [2, 8, 14, 15, 20],
}


def accident_case_by_id(case_id: int) -> dict:
    for item in ACCIDENT_CASE_LIBRARY:
        if item["id"] == case_id:
            return item
    return ACCIDENT_CASE_LIBRARY[0]


def accident_case_for_event(event_key: str, index: int = 0) -> dict:
    ids = ACCIDENT_SCENARIOS_BY_EVENT.get(event_key) or [1]
    return accident_case_by_id(ids[index % len(ids)])


def accident_cases_for_event(event_key: str):
    return [accident_case_by_id(case_id) for case_id in ACCIDENT_SCENARIOS_BY_EVENT.get(event_key, [])]


def format_measures(case: dict, limit: int = 3) -> str:
    items = case.get("measures", [])[:limit]
    return "；".join(items)


# ========================= 全事故卡覆盖增强（由 事故.xlsx 校对） =========================
# 本段覆盖前面的简化映射，确保事故表 20 个事故全部进入游戏事故库、触发轮换与判断选项。
ACCIDENT_CASE_LIBRARY = [
    {"id": 1, "category": "一回路系统事故", "name": "一回路小破口失水事故（破口当量直径 9.5~25mm）", "phenomenon": "RCP 系统冷却剂泄漏，稳压器水位和压力下降。", "measures": ["增加 RCV 上充流量补偿泄漏", "投入安注系统（RIS）", "投入 ASG 辅助给水系统导出堆芯余热", "蒸汽通过 GCT 排入凝汽器或大气"], "event_key": "water", "game_focus": "一回路泄漏导致水位/压力下降，玩家需要先稳住补水与余热导出。"},
    {"id": 2, "category": "一回路系统事故", "name": "一回路大破口失水事故（破口当量直径 345mm，设计基准事故）", "phenomenon": "主管道脆性断裂，大量冷却剂喷放。", "measures": ["投入高压 / 中压 / 低压安注向堆芯注水", "安全壳隔离（EIE）", "启动安全壳喷淋（EAS）降温降压", "启动应急柴油发电机"], "event_key": "safety", "game_focus": "大型 LOCA 会同时考验安注、喷淋、隔离和应急电源。"},
    {"id": 3, "category": "一回路系统事故", "name": "蒸汽发生器传热管破裂（SGTR）", "phenomenon": "一次侧放射性水进入二次侧，稳压器水位下降，二回路放射性升高。", "measures": ["确认紧急停堆生效", "隔离故障蒸汽发生器", "一回路快速降温降压", "平衡一二次侧压力终止泄漏", "启动辅助给水"], "event_key": "water", "game_focus": "SGTR 用水位/放射性联动表现，处置重点是隔离故障 SG 并稳定给水。"},
    {"id": 4, "category": "一回路系统事故", "name": "稳压器压力高", "phenomenon": "一回路压力超限。", "measures": ["触发紧急停堆", "稳压器安全阀自动开启排放蒸汽", "主喷淋投入降压"], "event_key": "power", "game_focus": "压力高会造成一回路压力边界负担，玩家需要抑制功率和降压。"},
    {"id": 5, "category": "一回路系统事故", "name": "稳压器压力低", "phenomenon": "一回路压力降至 13.0MPa.g 以下。", "measures": ["P7 信号下触发紧急停堆", "稳压器电加热器投入", "必要时启动安注"], "event_key": "water", "game_focus": "压力低与水位下降相互关联，游戏中表现为一回路水位/压力持续恶化。"},
    {"id": 6, "category": "一回路系统事故", "name": "反应堆冷却剂泵卡转子", "phenomenon": "单环路流量低于 88.8% 额定值。", "measures": ["堆功率 > 30% Pn 时单环路流量低触发紧急停堆", "堆功率 > 10% Pn 时双环路流量低触发紧急停堆"], "event_key": "power", "game_focus": "主泵卡转子用一回路流量下降表现，要求尽快进入保守停堆/供电保障。"},
    {"id": 7, "category": "一回路系统事故", "name": "控制棒弹棒 / 掉棒事故", "phenomenon": "中子通量变化率超过 ±5% Pn/2s。", "measures": ["中子通量变化率高信号触发紧急停堆", "限制弹棒 / 掉棒事故后果"], "event_key": "power", "game_focus": "控制棒异常会造成功率快速扰动，玩家不能继续追求出力。"},
    {"id": 8, "category": "二回路系统事故", "name": "主蒸汽管道破裂", "phenomenon": "蒸汽大量失控排放，安全壳压力上升，一回路过冷引入正反应性。", "measures": ["主蒸汽隔离阀自动关闭", "安注系统启动注入浓硼", "启动 ASG 辅助给水", "启动安全壳喷淋"], "event_key": "safety", "game_focus": "主蒸汽破裂把二回路事故与反应性、安全壳压力联系起来。"},
    {"id": 9, "category": "二回路系统事故", "name": "主给水管道破裂", "phenomenon": "蒸汽发生器给水丧失，堆芯余热无法导出。", "measures": ["ASG 辅助给水系统投入", "蒸汽发生器低低水位（2/4）触发紧急停堆"], "event_key": "water", "game_focus": "主给水破裂直接对应 ASG 辅助给水接入玩法。"},
    {"id": 10, "category": "二回路系统事故", "name": "蒸汽发生器水位高高", "phenomenon": "给水控制系统故障或蒸汽流量突增造成假水位。", "measures": ["触发 P14 信号使汽机脱扣和主给水隔离", "存在 P7 信号时触发紧急停堆"], "event_key": "water", "game_focus": "水位高高不是继续补水，而是要隔离给水并防止汽轮机带水风险。"},
    {"id": 11, "category": "二回路系统事故", "name": "蒸汽发生器水位低低", "phenomenon": "给水流量降低或丧失，二回路吸收热量能力下降。", "measures": ["任意 SG 水位低于低低保护阈值（15%）触发紧急停堆", "水位低（25%）且汽水失配超阈值触发紧急停堆", "投入 ASG 辅助给水"], "event_key": "water", "game_focus": "SG 水位低低是给水事故主线，正确选择会解锁应急给水接入口。"},
    {"id": 12, "category": "二回路系统事故", "name": "冷凝器真空丧失", "phenomenon": "二回路排热能力下降，一回路温度压力上升。", "measures": ["汽机脱扣", "若 GCT 不可用且核功率 > 40% Pn，汽机跳闸触发反应堆停堆", "恢复冷却水与冷端真空"], "event_key": "vacuum", "game_focus": "冷端事故以冷凝器绝对压力上升和发电功率下降表现。"},
    {"id": 13, "category": "专设安全设施相关事故", "name": "安全注入系统（RIS）误启动", "phenomenon": "安注信号误触发。", "measures": ["安注信号 5 分钟后联锁解除", "操纵员手动复位安注信号", "停运 RIS 相关设备"], "event_key": "safety", "game_focus": "安全系统误启动要求确认信号、复位并避免错误停运关键系统。"},
    {"id": 14, "category": "专设安全设施相关事故", "name": "安全壳喷淋系统（EAS）启动", "phenomenon": "触发条件：安全壳压力达 0.24MPa.a（MAX4）。", "measures": ["两台喷淋泵启动", "化学添加剂（NaOH）延迟 5 分钟注入", "20 分钟后从换料水箱切换至地坑再循环"], "event_key": "safety", "game_focus": "EAS 启动在游戏中表现为安全壳压力高和绿色喷淋脉冲。"},
    {"id": 15, "category": "专设安全设施相关事故", "name": "安全壳压力高（各阈值响应）", "phenomenon": "安全壳压力上升至不同阈值，触发分级保护动作。", "measures": ["0.12MPa.a（MAX1）：ETY 隔离", "0.13MPa.a（MAX2）：反应堆紧急停堆、汽机脱扣", "0.19MPa.a（MAX3）：主蒸汽隔离、安全壳隔离 B 阶段、柴油机启动", "0.24MPa.a（MAX4）：安全壳喷淋启动、安全壳隔离 A 阶段"], "event_key": "safety", "game_focus": "安全壳压力高做成分级阈值倒计时，越晚处理损失越大。"},
    {"id": 16, "category": "失电与全厂断电事故", "name": "失去厂外电源（LOOP）", "phenomenon": "厂外电源丧失，主泵转速降低，堆芯余热导出能力受挑战。", "measures": ["汽动辅助给水泵自动启动", "应急柴油发电机（EDG）为必要电动设备供电", "通过 ASG 辅助给水与 GCT 蒸汽排放导出余热", "条件满足后投入 RRA 余热排出系统"], "event_key": "power", "game_focus": "LOOP 强调厂外电源丧失后 EDG、ASG、GCT、RRA 的配合；SBO 仅用于厂外电源与应急交流电源均不可用的复合场景。"},
    {"id": 17, "category": "失电与全厂断电事故", "name": "全厂断电叠加小破口 LOCA", "phenomenon": "复合型超设计基准事故。", "measures": ["一回路卸压", "一回路外部注水", "优化注水时间和流量策略"], "event_key": "power", "game_focus": "复合事故会同时惩罚电源与一回路水位，要求先保电源再保冷却。"},
    {"id": 18, "category": "未能紧急停堆的预期瞬态（ATWS）", "name": "丧失正常给水 ATWS", "phenomenon": "二回路吸收热量能力下降，一回路温度压力上升。", "measures": ["汽机脱扣降低堆功率", "启动辅助给水防止 SG 烧干", "闭锁第 3 组 GCT 排放阀", "通过 CRDM 电源柜断开供电实现紧急停堆（独立于停堆断路器）"], "event_key": "water", "game_focus": "ATWS 强调停堆失败下仍要先恢复给水与独立停堆路径。"},
    {"id": 19, "category": "放射性释放与三废处理事故", "name": "燃料元件包壳破损", "phenomenon": "裂变产物逸入一回路，放射性指标上升。", "measures": ["化容系统净化回路除盐过滤", "一回路冷却剂取样监测", "必要时停堆维修"], "event_key": "dose", "game_focus": "包壳破损转化为剂量/放射性指标异常和取样监测任务。"},
    {"id": 20, "category": "放射性释放与三废处理事故", "name": "安全壳氢气浓度超标", "phenomenon": "锆水反应产生氢气，浓度达 1%~3% 时需消氢。", "measures": ["非能动氢复合器自动工作", "ETY 系统混合取样监测氢浓度", "LOCA 后约 1 天启动氢气复合器"], "event_key": "safety", "game_focus": "氢气风险通过安全壳状态灯、红色扫描线和消氢知识卡体现。"},
]

ACCIDENT_SCENARIOS_BY_EVENT = {
    "vacuum": [12],
    "water": [1, 3, 5, 9, 10, 11, 18],
    "power": [4, 6, 7, 16, 17],
    "safety": [2, 8, 13, 14, 15, 20],
    "dose": [19],
}

ACCIDENT_DECISION_OPTIONS_BY_CASE = {
    1: [
        {"text": "增加 RCV 上充并准备 RIS 安注", "correct": True, "feedback": "判断正确：小破口失水先补偿泄漏并准备安注。", "effects": ["稳压器水位 +2%", "一回路压力趋稳", "解锁应急给水/安注处置"], "parameter": "sg_level", "delta": 1.8},
        {"text": "继续升功率维持发电收益", "correct": False, "feedback": "判断错误：失水工况下升功率会加重堆芯冷却压力。", "effects": ["安全评分 -5", "资金 -80", "倒计时 -4s", "一回路压力继续下降"], "parameter": "sg_level", "delta": -1.5},
        {"text": "只观察水位，不投入补水", "correct": False, "feedback": "判断错误：小破口泄漏需要及时补偿，等待会扩大损失。", "effects": ["安全评分 -4", "倒计时 -3s", "屏障完整性下降"], "parameter": "sg_level", "delta": -1.0},
    ],
    2: [
        {"text": "投入 RIS 安注、EAS 喷淋并启动柴油机", "correct": True, "feedback": "判断正确：大破口 LOCA 需要安注、隔离、喷淋和应急电源联动。", "effects": ["安全壳压力下降", "安全系统可用性 +1", "解锁安全壳喷淋接入"], "parameter": "primary_flow", "delta": 1.0},
        {"text": "只启动主给水泵补水", "correct": False, "feedback": "判断错误：大破口 LOCA 不是普通给水不足，必须启动专设安全设施。", "effects": ["安全评分 -6", "资金 -100", "倒计时 -4s"], "parameter": "primary_flow", "delta": -1.0},
        {"text": "关闭安全壳喷淋避免耗水", "correct": False, "feedback": "判断错误：喷淋用于安全壳降温降压，关闭会放大安全壳风险。", "effects": ["安全评分 -6", "安全壳压力继续上升"], "parameter": "primary_flow", "delta": -0.8},
    ],
    3: [
        {"text": "隔离故障 SG，降温降压并启动辅助给水", "correct": True, "feedback": "判断正确：SGTR 要终止一二次侧泄漏并保持余热导出。", "effects": ["二回路放射性增长受控", "SG 水位 +2%", "解锁给水接入"], "parameter": "sg_level", "delta": 2.0},
        {"text": "继续使用故障蒸汽发生器排汽", "correct": False, "feedback": "判断错误：故障 SG 未隔离会扩大二回路放射性污染。", "effects": ["安全评分 -5", "剂量 +0.4mSv", "倒计时 -4s"], "parameter": "dose", "delta": 0.4},
        {"text": "只提升冷却水流量", "correct": False, "feedback": "判断错误：冷端换热不能终止 SGTR 的一二次侧泄漏。", "effects": ["资金 -80", "稳压器水位继续下降"], "parameter": "sg_level", "delta": -1.0},
    ],
    4: [
        {"text": "触发停堆并投入稳压器喷淋降压", "correct": True, "feedback": "判断正确：压力高应优先抑制功率并通过喷淋/安全阀降压。", "effects": ["一回路压力下降", "安全评分 +1", "解锁应急电源保障"], "parameter": "primary_flow", "delta": 0.8},
        {"text": "关闭喷淋保持压力", "correct": False, "feedback": "判断错误：压力已高，继续维持压力会加重压力边界负担。", "effects": ["安全评分 -5", "倒计时 -4s", "一回路压力继续升高"], "parameter": "primary_flow", "delta": -0.8},
        {"text": "提高汽轮机负荷消耗蒸汽", "correct": False, "feedback": "判断错误：压力高处置应以反应堆保护和一回路降压为先。", "effects": ["安全评分 -4", "资金 -80"], "parameter": "primary_flow", "delta": -0.5},
    ],
    5: [
        {"text": "投入稳压器电加热器，必要时准备安注", "correct": True, "feedback": "判断正确：压力低要恢复压力并准备安注补水。", "effects": ["一回路压力趋稳", "安全评分 +1", "解锁给水/安注处置"], "parameter": "sg_level", "delta": 1.6},
        {"text": "开启更多喷淋继续降压", "correct": False, "feedback": "判断错误：压力已经偏低，继续喷淋会扩大低压风险。", "effects": ["安全评分 -5", "倒计时 -4s", "水位继续下降"], "parameter": "sg_level", "delta": -1.4},
        {"text": "忽略低压报警继续并网", "correct": False, "feedback": "判断错误：低压保护区间不能继续按正常并网处理。", "effects": ["安全评分 -4", "资金 -80"], "parameter": "sg_level", "delta": -1.0},
    ],
    6: [
        {"text": "确认流量低保护并转入停堆冷却", "correct": True, "feedback": "判断正确：主泵卡转子会快速削弱一回路流量，应保守停堆。", "effects": ["一回路流量 +1.2%", "安全评分 +1", "解锁柴油机供电保障"], "parameter": "primary_flow", "delta": 1.2},
        {"text": "继续提升功率冲过流量波动", "correct": False, "feedback": "判断错误：主泵卡转子时升功率会加剧堆芯冷却风险。", "effects": ["安全评分 -6", "倒计时 -4s", "一回路流量 -1%"], "parameter": "primary_flow", "delta": -1.0},
        {"text": "关闭一列应急电源减少负荷", "correct": False, "feedback": "判断错误：电源冗余应保持可用，不能削弱安全系统。", "effects": ["安全评分 -5", "安全系统可用性下降"], "parameter": "primary_flow", "delta": -0.7},
    ],
    7: [
        {"text": "确认中子通量变化率高并触发停堆", "correct": True, "feedback": "判断正确：弹棒/掉棒导致功率扰动，应优先停堆保护。", "effects": ["堆芯功率波动受控", "安全评分 +1", "解锁应急电源保障"], "parameter": "primary_flow", "delta": 0.8},
        {"text": "继续抽棒提高反应性", "correct": False, "feedback": "判断错误：反应性扰动时继续抽棒会放大功率尖峰。", "effects": ["安全评分 -6", "倒计时 -4s"], "parameter": "primary_flow", "delta": -0.8},
        {"text": "只调整冷凝器真空", "correct": False, "feedback": "判断错误：冷端调节不能处理反应性快速扰动。", "effects": ["资金 -80", "安全评分 -4"], "parameter": "primary_flow", "delta": -0.5},
    ],
    8: [
        {"text": "隔离主蒸汽，注入浓硼并启动 ASG/EAS", "correct": True, "feedback": "判断正确：主蒸汽管破裂需要隔离、安注、辅助给水和喷淋配合。", "effects": ["安全壳压力下降", "反应性风险受控", "解锁喷淋接入"], "parameter": "primary_flow", "delta": 1.0},
        {"text": "打开更多蒸汽排放阀泄压", "correct": False, "feedback": "判断错误：破裂工况下扩大排放会加剧蒸汽失控。", "effects": ["安全评分 -6", "倒计时 -4s", "安全壳压力上升"], "parameter": "primary_flow", "delta": -0.8},
        {"text": "只提高给水流量", "correct": False, "feedback": "判断错误：给水不能替代主蒸汽隔离和安注浓硼。", "effects": ["资金 -80", "安全评分 -4"], "parameter": "sg_level", "delta": -0.8},
    ],
    9: [
        {"text": "投入 ASG 辅助给水，维持 SG 余热导出", "correct": True, "feedback": "判断正确：主给水管道破裂时 ASG 是关键缓解路径。", "effects": ["蒸汽发生器水位 +2.5%", "安全评分 +1", "解锁给水接入口"], "parameter": "sg_level", "delta": 2.5},
        {"text": "等待主给水自动恢复", "correct": False, "feedback": "判断错误：主给水管道破裂不能依赖自动恢复。", "effects": ["安全评分 -5", "倒计时 -4s", "蒸汽发生器水位 -1.8%"], "parameter": "sg_level", "delta": -1.8},
        {"text": "切断 ASG 防止过量给水", "correct": False, "feedback": "判断错误：此时缺的是给水，切断 ASG 会导致 SG 水位继续下降。", "effects": ["安全评分 -5", "资金 -80"], "parameter": "sg_level", "delta": -1.2},
    ],
    10: [
        {"text": "汽机脱扣并隔离主给水，防止水位继续高高", "correct": True, "feedback": "判断正确：水位高高应限制给水和汽机风险，而不是继续补水。", "effects": ["SG 水位回落", "安全评分 +1", "解锁给水隔离处置"], "parameter": "sg_level", "delta": -1.5},
        {"text": "继续投入 ASG 辅助给水", "correct": False, "feedback": "判断错误：水位高高时继续补水会放大汽轮机带水风险。", "effects": ["安全评分 -5", "倒计时 -4s", "蒸汽发生器水位 +2%"], "parameter": "sg_level", "delta": 2.0},
        {"text": "提高反应堆功率蒸干水位", "correct": False, "feedback": "判断错误：用升功率处理水位高高会造成更大热工风险。", "effects": ["安全评分 -6", "资金 -80"], "parameter": "sg_level", "delta": 1.0},
    ],
    11: [
        {"text": "投入 ASG 辅助给水并稳定 SG 水位", "correct": True, "feedback": "判断正确：SG 水位低低趋势应优先投入辅助给水。", "effects": ["蒸汽发生器水位 +2.5%", "安全评分 +1", "解锁给水接入口"], "parameter": "sg_level", "delta": 2.5},
        {"text": "降低冷却水流量", "correct": False, "feedback": "判断错误：冷却水调节不能直接解决给水能力不足。", "effects": ["安全评分 -5", "资金 -80", "倒计时 -4s", "蒸汽发生器水位 -1.8%"], "parameter": "sg_level", "delta": -1.8},
        {"text": "只等待自动调节恢复", "correct": False, "feedback": "判断错误：水位趋势已异常，等待会缩短事故处置窗口。", "effects": ["安全评分 -4", "资金 -60", "倒计时 -3s"], "parameter": "sg_level", "delta": -1.2},
    ],
    12: [
        {"text": "恢复冷却水流量并接入备用冷却", "correct": True, "feedback": "判断正确：冷凝器真空恶化时应优先恢复冷端换热能力。", "effects": ["冷凝器绝对压力 -0.6 kPa(a)", "安全评分 +1", "解锁备用冷却接入"], "parameter": "condenser_pressure", "delta": -0.6},
        {"text": "提高反应堆功率维持出力", "correct": False, "feedback": "判断错误：提高功率会增加热负荷，使真空继续变差。", "effects": ["安全评分 -5", "资金 -80", "倒计时 -4s", "冷凝器绝对压力 +0.8 kPa(a)"], "parameter": "condenser_pressure", "delta": 0.8},
        {"text": "暂停冷却水系统检查", "correct": False, "feedback": "判断错误：此时暂停冷却水检查会延误恢复，事故链更快升级。", "effects": ["安全评分 -4", "资金 -60", "倒计时 -3s"], "parameter": "condenser_pressure", "delta": 0.5},
    ],
    13: [
        {"text": "确认误启动，等待联锁解除后手动复位", "correct": True, "feedback": "判断正确：RIS 误启动要先确认信号，再按程序复位停运相关设备。", "effects": ["误动作风险受控", "安全评分 +1", "解锁安全系统复位"], "parameter": "primary_flow", "delta": 0.6},
        {"text": "立即切除所有安注设备", "correct": False, "feedback": "判断错误：未确认信号就切除全部安注会削弱事故缓解能力。", "effects": ["安全评分 -6", "倒计时 -4s"], "parameter": "primary_flow", "delta": -0.8},
        {"text": "继续升功率抵消误注入", "correct": False, "feedback": "判断错误：误启动应复位信号，不应通过升功率抵消。", "effects": ["安全评分 -5", "资金 -80"], "parameter": "primary_flow", "delta": -0.5},
    ],
    14: [
        {"text": "确认 EAS 启动并维持喷淋泵运行", "correct": True, "feedback": "判断正确：安全壳压力达到阈值后应保证喷淋泵投入。", "effects": ["安全壳压力下降", "安全评分 +1", "解锁喷淋接入"], "parameter": "primary_flow", "delta": 0.8},
        {"text": "停运两台喷淋泵节省水源", "correct": False, "feedback": "判断错误：喷淋用于安全壳降温降压，不能在压力高时停运。", "effects": ["安全评分 -6", "安全壳压力继续上升"], "parameter": "primary_flow", "delta": -0.8},
        {"text": "只打开冷凝器冷却水", "correct": False, "feedback": "判断错误：冷端换热不能替代安全壳喷淋降压。", "effects": ["资金 -80", "倒计时 -3s"], "parameter": "condenser_pressure", "delta": 0.4},
    ],
    15: [
        {"text": "按压力阈值执行隔离、柴油机和喷淋联动", "correct": True, "feedback": "判断正确：安全壳压力高需要分级保护动作联动。", "effects": ["安全壳压力下降", "安全系统可用性 +1", "解锁喷淋接入"], "parameter": "primary_flow", "delta": 1.0},
        {"text": "只复位报警，不执行隔离", "correct": False, "feedback": "判断错误：压力高不是单纯误报警，复位会延误隔离和喷淋。", "effects": ["安全评分 -6", "倒计时 -4s"], "parameter": "primary_flow", "delta": -0.8},
        {"text": "关闭柴油机避免误启动", "correct": False, "feedback": "判断错误：高阈值响应需要柴油机保证安全设备供电。", "effects": ["安全评分 -5", "安全系统可用性下降"], "parameter": "primary_flow", "delta": -0.7},
    ],
    16: [
        {"text": "按顺序投入两列应急柴油机供电", "correct": True, "feedback": "判断正确：失去厂外电源时，应优先保证两列冗余应急供电。", "effects": ["一回路流量 +1.2%", "安全评分 +1", "解锁柴油机 A/B 母线接入"], "parameter": "primary_flow", "delta": 1.2},
        {"text": "关闭一列安全系统降低负荷", "correct": False, "feedback": "判断错误：关闭安全系统会削弱纵深防御。", "effects": ["安全评分 -6", "资金 -100", "倒计时 -4s", "一回路流量 -1.0%"], "parameter": "primary_flow", "delta": -1.0},
        {"text": "继续提高汽轮机负荷", "correct": False, "feedback": "判断错误：外电源不稳定时提高负荷会放大扰动。", "effects": ["安全评分 -5", "资金 -80", "倒计时 -3s"], "parameter": "primary_flow", "delta": -0.7},
    ],
    17: [
        {"text": "先保障应急电源，再卸压并组织外部注水", "correct": True, "feedback": "判断正确：SBO 叠加小破口需要电源、卸压和补水联动；普通失去厂外电源应先按 LOOP 处置。", "effects": ["一回路流量 +1.0%", "稳压器水位趋稳", "解锁柴油机接入"], "parameter": "primary_flow", "delta": 1.0},
        {"text": "只等待蓄电池维持全部安全功能", "correct": False, "feedback": "判断错误：复合事故不能只依赖蓄电池等待。", "effects": ["安全评分 -6", "倒计时 -4s", "一回路流量 -1.0%"], "parameter": "primary_flow", "delta": -1.0},
        {"text": "优先恢复发电收益", "correct": False, "feedback": "判断错误：复合事故下收益优先会导致屏障损伤加速。", "effects": ["安全评分 -6", "资金 -100"], "parameter": "primary_flow", "delta": -0.8},
    ],
    18: [
        {"text": "汽机脱扣，启动辅助给水，并切断 CRDM 供电停堆", "correct": True, "feedback": "判断正确：ATWS 要使用独立于停堆断路器的停堆路径。", "effects": ["SG 水位 +2%", "功率扰动受控", "解锁给水接入"], "parameter": "sg_level", "delta": 2.0},
        {"text": "继续等待停堆断路器自行恢复", "correct": False, "feedback": "判断错误：ATWS 的关键就是未能按预期停堆，不能只等待。", "effects": ["安全评分 -6", "倒计时 -4s", "SG 水位 -1.5%"], "parameter": "sg_level", "delta": -1.5},
        {"text": "打开全部 GCT 排放阀快速泄压", "correct": False, "feedback": "判断错误：ATWS 处置中需要闭锁部分 GCT 排放阀，避免不利影响。", "effects": ["安全评分 -5", "资金 -80"], "parameter": "sg_level", "delta": -1.0},
    ],
    19: [
        {"text": "启动取样监测和化容净化，必要时停堆维修", "correct": True, "feedback": "判断正确：包壳破损要通过取样监测与净化控制放射性。", "effects": ["个人剂量 +0.1mSv 后趋稳", "环境监测防线 +1", "解锁 KRT/ETY 监测"], "parameter": "dose", "delta": 0.1},
        {"text": "关闭区域辐射监测（KRT）避免报警", "correct": False, "feedback": "判断错误：关闭监测会失去放射性趋势判断。", "effects": ["安全评分 -6", "剂量 +0.6mSv", "倒计时 -4s"], "parameter": "dose", "delta": 0.6},
        {"text": "继续安排人员长时间近距离作业", "correct": False, "feedback": "判断错误：放射性升高时应减少暴露时间并优化路径。", "effects": ["剂量 +0.8mSv", "防护评分下降"], "parameter": "dose", "delta": 0.8},
    ],
    20: [
        {"text": "确认 ETY 大气监测，保持安全壳消氢系统（EUH）/氢复合器可用", "correct": True, "feedback": "判断正确：氢气风险应依靠 ETY 大气监测和 EUH/氢复合器降低浓度。", "effects": ["安全壳氢气风险下降", "安全评分 +1", "解锁喷淋/监测接入"], "parameter": "dose", "delta": 0.1},
        {"text": "关闭安全壳通风与氢气监测", "correct": False, "feedback": "判断错误：关闭监测会让氢气风险失去判断依据。", "effects": ["安全评分 -6", "倒计时 -4s"], "parameter": "dose", "delta": 0.4},
        {"text": "安排人员进入安全壳现场确认", "correct": False, "feedback": "判断错误：氢气浓度异常时不应增加人员暴露与进入风险。", "effects": ["剂量 +0.6mSv", "防护评分下降"], "parameter": "dose", "delta": 0.6},
    ],
}

def accident_decision_options(event_key: str, case: dict | None = None):
    """优先返回事故表中具体事故的三选一处置，确保 20 个事故在玩法上有差异。"""
    if case and case.get("id") in ACCIDENT_DECISION_OPTIONS_BY_CASE:
        return ACCIDENT_DECISION_OPTIONS_BY_CASE[case["id"]]
    case = accident_case_for_event(event_key)
    return ACCIDENT_DECISION_OPTIONS_BY_CASE.get(case.get("id"), [])

def accident_coverage_rows():
    """供自检脚本/答辩说明使用：列出 20 个事故的游戏映射。"""
    return [(c["id"], c["category"], c["name"], c["event_key"], c.get("game_focus", "")) for c in ACCIDENT_CASE_LIBRARY]
