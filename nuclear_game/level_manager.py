# -*- coding: utf-8 -*-
"""关卡状态管理。

本模块只负责“当前关、下一关、解锁、星级、奖励、地图开关”等跨界面状态，
避免这些逻辑分散在 engine / guidance / persistence 里。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LevelManager:
    stage_count: int = 5
    current_stage: int = 0
    unlocked: List[int] = field(default_factory=lambda: [0])
    stars: Dict[int, int] = field(default_factory=dict)
    badges: Dict[int, str] = field(default_factory=dict)
    rewards: Dict[int, List[str]] = field(default_factory=dict)
    map_open: bool = False

    def reset(self, keep_records: bool = False) -> None:
        old_stars = dict(self.stars)
        old_badges = dict(self.badges)
        old_rewards = {k: list(v) for k, v in self.rewards.items()}
        self.current_stage = 0
        self.unlocked = [0]
        self.map_open = False
        self.stars = old_stars if keep_records else {}
        self.badges = old_badges if keep_records else {}
        self.rewards = old_rewards if keep_records else {}

    def set_current(self, stage: int) -> int:
        stage = max(0, min(self.stage_count - 1, int(stage)))
        self.current_stage = stage
        self.unlock_to(stage)
        return stage

    def unlock_to(self, stage: int) -> None:
        stage = max(0, min(self.stage_count - 1, int(stage)))
        for value in range(stage + 1):
            if value not in self.unlocked:
                self.unlocked.append(value)
        self.unlocked.sort()

    def next_stage(self) -> int:
        return min(self.stage_count - 1, self.current_stage + 1)

    def status(self, stage: int) -> str:
        stage = int(stage)
        if stage < self.current_stage:
            return "已完成"
        if stage == self.current_stage:
            return "当前关"
        if stage in self.unlocked:
            return "已解锁"
        return "未解锁"

    def is_unlocked(self, stage: int) -> bool:
        return int(stage) in self.unlocked

    def record_completion(self, stage: int, stars: int = 0, badge: str = "", rewards: Optional[List[str]] = None) -> None:
        stage = max(0, min(self.stage_count - 1, int(stage)))
        self.stars[stage] = max(self.stars.get(stage, 0), max(0, min(3, int(stars))))
        if badge:
            self.badges[stage] = str(badge)
        if rewards:
            self.rewards[stage] = [str(item) for item in rewards]
        self.unlock_to(min(self.stage_count - 1, stage + 1))

    def stars_for(self, stage: int) -> int:
        return int(self.stars.get(int(stage), 0))

    def to_save(self) -> dict:
        return {
            "current_stage": self.current_stage,
            "unlocked": list(self.unlocked),
            "stars": {str(k): int(v) for k, v in self.stars.items()},
            "badges": {str(k): v for k, v in self.badges.items()},
            "rewards": {str(k): list(v) for k, v in self.rewards.items()},
        }

    def load_save(self, data: object) -> None:
        if not isinstance(data, dict):
            return
        self.current_stage = max(0, min(self.stage_count - 1, int(data.get("current_stage", 0) or 0)))
        raw_unlocked = data.get("unlocked", [0])
        if not isinstance(raw_unlocked, list):
            raw_unlocked = [0]
        self.unlocked = sorted({max(0, min(self.stage_count - 1, int(x))) for x in raw_unlocked if str(x).lstrip("-").isdigit()} | {0})
        raw_stars = data.get("stars", {})
        self.stars = {}
        if isinstance(raw_stars, dict):
            for k, v in raw_stars.items():
                if str(k).isdigit():
                    self.stars[int(k)] = max(0, min(3, int(v or 0)))
        raw_badges = data.get("badges", {})
        self.badges = {int(k): str(v) for k, v in raw_badges.items() if str(k).isdigit()} if isinstance(raw_badges, dict) else {}
        raw_rewards = data.get("rewards", {})
        self.rewards = {}
        if isinstance(raw_rewards, dict):
            for k, v in raw_rewards.items():
                if str(k).isdigit() and isinstance(v, list):
                    self.rewards[int(k)] = [str(item) for item in v]
        self.unlock_to(self.current_stage)
