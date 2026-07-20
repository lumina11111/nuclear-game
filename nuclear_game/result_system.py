# -*- coding: utf-8 -*-
"""通关、失败和复盘报告辅助系统。"""
from __future__ import annotations

FAILURE_PROFILES = [
    {
        "match": ("剂量", "20 mSv"),
        "cause": "事故处置或剂量作业暴露时间过长，个人剂量达到教学红线。",
        "advice": ["预警阶段优先完成诊断", "红色故障阶段及时拖拽正确应急工具", "剂量任务中优先选择屏蔽通道、机器人或临时屏蔽"],
    },
    {
        "match": ("资金", "停工"),
        "cause": "建设方案成本过高、错误操作过多或运行收益不足，导致项目资金耗尽。",
        "advice": ["选址时平衡冷却水条件与建设成本", "减少错误安装和错误处置", "并网运行阶段及时安排维护，降低收益损失"],
    },
    {
        "match": ("安全评分", "安全审查"),
        "cause": "预警或故障处置滞后，导致安全评分持续下降。",
        "advice": ["黄色预警阶段尽早诊断", "优先保持主泵、冷源和安全系统可用", "不要让预警升级为红色故障"],
    },
    {
        "match": ("防护评分", "辐射防护"),
        "cause": "个人剂量系统、区域监测或作业方案控制不足，防护评分低于验收要求。",
        "advice": ["完善个人剂量系统和区域监测", "作业前选择合适路线、人员和防护装备", "优先采用 ALARA 原则降低暴露"],
    },
    {
        "match": ("冷凝器绝对压力", "风险"),
        "cause": "冷却水条件不足或冷却水调节不及时，导致冷凝器绝对压力长期偏高。",
        "advice": ["选址阶段关注冷却水条件", "运行阶段提高冷却水流量", "预警阶段优先处理冷凝器绝对压力升高事件"],
    },
]
DEFAULT_FAILURE_REVIEW = {
    "cause": "关键安全、经济或防护指标未达到本局目标。",
    "advice": ["观察核心参数颜色变化", "按阶段提示完成关键操作", "通关后结合知识复盘调整下一局策略"],
}


class ResultSystemMixin:
    def build_failure_detail(self, reason: str, advice: str = "") -> dict:
        text = f"{reason} {advice}"
        for profile in FAILURE_PROFILES:
            if any(word in text for word in profile["match"]):
                return {
                    "reason": reason,
                    "cause": profile["cause"],
                    "advice": profile["advice"],
                }
        return {"reason": reason, "cause": DEFAULT_FAILURE_REVIEW["cause"], "advice": DEFAULT_FAILURE_REVIEW["advice"]}

    def trigger_failure(self, reason: str, advice: str):
        """覆盖 operation.py 中的失败入口，记录更完整的教学复盘。"""
        if getattr(self, "challenge_finished", False):
            return
        self.failure_reason = reason
        self.failure_advice = advice
        self.failure_detail = self.build_failure_detail(reason, advice)
        self.scrammed = True
        self.challenge_finished = True
        self.report = True
        self.log_event("failure", reason, cause="failure")
        if hasattr(self, "record_choice_effect"):
            self.record_choice_effect("任务失败", self.get_failure_review_lines(), duration_ms=9000)
        if hasattr(self, "audio"):
            self.audio.play("alarm")

    def get_failure_review_lines(self):
        detail = getattr(self, "failure_detail", None)
        if not detail:
            detail = self.build_failure_detail(getattr(self, "failure_reason", ""), getattr(self, "failure_advice", ""))
        lines = []
        if detail.get("reason"):
            lines.append("失败原因：" + detail["reason"])
        if detail.get("cause"):
            lines.append("主要诱因：" + detail["cause"])
        for idx, item in enumerate(detail.get("advice", [])[:3], start=1):
            lines.append(f"改进建议{idx}：{item}")
        return lines
