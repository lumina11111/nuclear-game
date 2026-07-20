# -*- coding: utf-8 -*-
"""关卡脚本数据转换层。

剧本人员只需要改 story_plain.py；本文件把中文填写表转换为程序内部字段。
"""

import sys

from .story_plain import 游戏标题, 游戏副标题, 新手目标, 关卡填写表

EXCEL_STORY_SOURCE = ""
_excel_story = None
if sys.platform != "emscripten":
    try:
        from .excel_story_loader import load_excel_story
        _excel_story = load_excel_story()
    except Exception:
        _excel_story = None

if _excel_story:
    游戏标题 = _excel_story.get("游戏标题") or 游戏标题
    游戏副标题 = _excel_story.get("游戏副标题") or 游戏副标题
    新手目标 = _excel_story.get("新手目标") or 新手目标
    关卡填写表 = _excel_story.get("关卡填写表") or 关卡填写表
    EXCEL_STORY_SOURCE = _excel_story.get("source", "剧本填写表.xlsx")

GAME_TITLE = 游戏标题
GAME_SUBTITLE = 游戏副标题
BEGINNER_OBJECTIVE = 新手目标

_KEY_MAP = {
    "阶段": "stage",
    "章节": "chapter",
    "标题": "title",
    "主线任务": "main_task",
    "说明": "description",
    "特殊规则": "special_rule",
    "影响": "effect",
    "任务": "tasks",
    "奖励": "rewards",
    "解锁": "unlocks",
    "资质章": "license_badge",
    "知识复盘": "knowledge_review",
    "通关语": "success_message",
}


def _convert_objectives(items):
    result = []
    for item in items or []:
        if isinstance(item, dict):
            result.append({"label": item.get("名称", item.get("label", "目标")),
                           "hint": item.get("提示", item.get("hint", ""))})
        else:
            result.append({"label": str(item), "hint": ""})
    return result


def _convert_stage(row: dict) -> dict:
    item = {}
    for cn_key, en_key in _KEY_MAP.items():
        if cn_key in row:
            item[en_key] = row[cn_key]
    item["objectives"] = _convert_objectives(row.get("目标", row.get("objectives", [])))
    return item


STAGE_SCRIPTS = [_convert_stage(row) for row in 关卡填写表]


def validate_story_data() -> None:
    """启动时检查剧本结构，方便剧本人员定位格式错误。"""
    required = {"stage", "chapter", "title", "main_task", "description", "tasks", "success_message"}
    seen = set()
    for item in STAGE_SCRIPTS:
        missing = required - set(item)
        if missing:
            raise ValueError(f"关卡脚本缺少字段：{missing}，问题关卡：{item}")
        stage = item["stage"]
        if stage in seen:
            raise ValueError(f"关卡 stage 重复：{stage}")
        seen.add(stage)
        for key in ("description", "tasks"):
            if not isinstance(item[key], list):
                raise ValueError(f"{key} 必须是列表，问题关卡：{stage}")
        for key in ("objectives", "rewards", "unlocks", "knowledge_review"):
            if key in item and not isinstance(item[key], list):
                raise ValueError(f"{key} 必须是列表，问题关卡：{stage}")
    expected = set(range(5))
    if seen != expected:
        raise ValueError(f"关卡 stage 必须覆盖 0-4，当前为：{sorted(seen)}")


def get_stage_script(stage: int) -> dict:
    validate_story_data()
    for item in STAGE_SCRIPTS:
        if item["stage"] == stage:
            return item
    return STAGE_SCRIPTS[0]


STORY_STAGE_NAMES = [get_stage_script(i)["title"] for i in range(5)]
STORY_STAGE_HELP = [get_stage_script(i)["main_task"] for i in range(5)]
