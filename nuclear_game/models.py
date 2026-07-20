"""游戏领域数据结构。"""
from dataclasses import dataclass
from typing import Tuple
import pygame

@dataclass
class Module:
    key: str
    name: str
    category: str
    slot: pygame.Rect
    color: Tuple[int, int, int]
    cost: int
    days: float
    info: str
    fact: str
    needs: Tuple[str, ...] = ()
    essential: bool = True


@dataclass
class FaultEvent:
    title: str
    description: str
    action: str
    duration: float
    penalty: int
    key: str


@dataclass
class Upgrade:
    name: str
    cost: int
    build_time: float
    effect: str
    level: int = 0
    in_progress: bool = False
    remaining: float = 0.0




@dataclass
class RingEffect:
    center: Tuple[int, int]
    color: Tuple[int, int, int]
    radius: float = 8.0
    life: float = 0.65


@dataclass
class ParticleEffect:
    x: float
    y: float
    vx: float
    vy: float
    color: Tuple[int, int, int]
    life: float = 0.65
