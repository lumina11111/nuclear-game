# -*- coding: utf-8 -*-
"""
核境造物——新手友好模块化版
=================================================
运行方法：
    pip install -r requirements.txt
    python 启动游戏.py

游戏内容（教学娱乐简化模型）：
1. 分阶段建造：土建施工 -> 设备安装 -> 系统调试 -> 装料与临界 -> 并网运行。
2. 反应堆组合安装：压力容器 -> 堆芯 -> 控制棒驱动机构。
3. 安全系统：两列应急柴油发电机、安全壳喷淋系统、辅助给水系统（ASG）和辐射监测防护设备。
4. 参数监视：温度、压力、流量、水位、真空等动态监视和报警。
5. 运行故障：冷凝器绝对压力升高（真空变差）、蒸汽发生器水位波动、外电源异常。
6. 资源决策：资金、工期、主泵保障方案、运行后升级。
7. 热力反馈：冷却水滑块、功率/排热动态变化、能量流条。
8. 知识卡片：右键设备图标或已安装设备查看科普内容。
9. 界面优化：窗口可缩放、中文自动换行/缩字、紧凑设备卡片。
10. 体验优化：程序内合成音效、安装反馈动画、醒目报警横幅与滚动知识卡片。
11. 平衡优化：集中参数配置，降低新手剂量压力并延长教学模式处置时间。
12. 新手友好：保留极简教学、拖拽吸附和清晰目标提示。
13. 模块化：界面工具、音效、数据模型、目录数据与教程内容拆分为独立模块。

注意：
本程序只用于科普和编程练习。参数、操作和事件响应经过大幅简化，
不能作为真实核电工程设计、运行或安全处置依据。
"""

import sys
import asyncio
import random
from typing import Dict, List, Optional, Tuple

# Windows 高 DPI 下若不主动声明，Pygame 窗口可能被系统拉伸，导致文字发虚。
# 这里在初始化 pygame 前启用 DPI 感知，优先保证真实像素渲染清晰。
if sys.platform == "win32":
    try:
        import ctypes
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import pygame

# 音效为程序内合成提示音，不依赖外部资源；无声卡环境会自动静默降级。
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

# ========================= 基本设置 =========================
# 逻辑画布保持固定坐标；真实窗口可自由缩放，渲染时等比适配。
from .theme import *

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("核境造物")
CLOCK = pygame.time.Clock()

from .storage import user_data_dir
from .catalog import CIVIL, EQUIPMENT, MISSION_TYPES, SITE_TYPES, RUN_OPERATION_TOOLS, HEALTH_META, ALL_MODULES, PLAY_MODES
from .story_data import STORY_STAGE_NAMES, validate_story_data
from .ui_helpers import clamp
from .models import FaultEvent, Upgrade, RingEffect, ParticleEffect
from .advanced_features import PROFESSIONAL_SYSTEM_UPGRADES

# 阶段名称和阶段目标由 story_data.py 提供，剧本人员主要改 story_data.py。
STAGE_NAMES = STORY_STAGE_NAMES
validate_story_data()


from .audio import AudioManager
from .level_manager import LevelManager
from .persistence import PersistenceMixin
from .guidance import GuidanceMixin
from .gameplay import GameplayMixin
from .screens import ScreenMixin
from .demo_system import DemoSystemMixin
from .settings_system import SettingsSystemMixin
from .result_system import ResultSystemMixin


# ========================= 主游戏类 =========================
class NuclearGame(PersistenceMixin, GuidanceMixin, ResultSystemMixin, DemoSystemMixin, SettingsSystemMixin, GameplayMixin, ScreenMixin):
    def __init__(self):
        self.display = SCREEN
        self.screen = pygame.Surface((WIDTH, HEIGHT))
        self.viewport = pygame.Rect(0, 0, WIDTH, HEIGHT)
        self.render_scale = 1.0
        self.fullscreen = False
        self.stage = 0
        self.placed: Dict[str, pygame.Rect] = {}
        self.dragging: Optional[dict] = None
        self.selected: Optional[str] = None
        self.info_card: Optional[str] = None
        self.tutorial = True
        self.active_tab = "反应堆"
        self.toolbar_rects: Dict[str, pygame.Rect] = {}
        self.tab_rects: Dict[str, pygame.Rect] = {}
        self.menu = True
        self.report = False
        self.pump_choice = "监测强化"
        self.funds = 9400.0
        self.days = 0.0
        self.safety = 100
        self.mistakes = 0
        self.message = "选择“压水堆 PWR”开始建设。"
        self.message_color = BLACK
        self.progress_flags = set()
        self.anim = 0.0
        self.runtime = 0.0
        self.next_fault = 18.0
        self.fault: Optional[FaultEvent] = None
        self.fault_left = 0.0
        self.scrammed = False
        self.cooling_flow = 75.0
        self.slider_drag = False
        self.parameters = {}
        self.output_mw = 0.0
        self.thermal_mw = 0.0
        self.income_clock = 0.0
        self.protection_score = 100
        self.protection_verified = False
        self.collective_dose = 0.0
        self.max_task_dose = 0.0
        self.operation_seconds = 0
        self.dose_task = None
        self.dose_task_left = 0.0
        self.next_dose_task = 11.0
        self.upgrades = {
            "blade": Upgrade("耐热汽轮机叶片", 700, 6.0, "电功率 +70 MW"),
            "cooling_upgrade": Upgrade("高效冷却换热器", 650, 7.0, "冷却效率提升"),
            "monitor": Upgrade("数字安全监测", 520, 5.0, "安全评分 +6"),
        }
        # CPR1000 专业系统升级：让 ASG/RIS/EAS/EDG/KRT/ETY 变成玩家可投资、可拥有的设施能力。
        for _key, _meta in PROFESSIONAL_SYSTEM_UPGRADES.items():
            self.upgrades[_key] = Upgrade(_meta.name, _meta.cost, _meta.build_time, _meta.effect)
        self.upgrade_buttons: Dict[str, pygame.Rect] = {}
        self.fault_action_button = pygame.Rect(1180, 823, 260, 40)
        self.primary_choice_buttons = {
            "轴封维护": pygame.Rect(270, 792, 95, 32),
            "监测强化": pygame.Rect(373, 792, 95, 32)
        }
        self.action_rects = {}
        self.quiz = {
            "flush": None,
            "seal": None,
            "diesel_a_test": False,
            "diesel_b_test": False,
        }
        self.critical_step = 0
        self.critical_buttons: List[pygame.Rect] = []
        self.critical_tool_rects: Dict[str, pygame.Rect] = {}
        self.critical_option_rects: List[Tuple[pygame.Rect, str, bool]] = []
        self.choice_order_cache = {}
        self.stage_button = pygame.Rect(1000, 801, 118, 46)
        self.reset_button = pygame.Rect(867, 801, 118, 46)
        self.guide_button = pygame.Rect(1050, 20, 93, 34)
        self.report_button = pygame.Rect(1002, 801, 118, 46)
        self.tip_next_button = pygame.Rect(1048, 700, 70, 28)
        self.tip_index = 0
        self.save_path = user_data_dir() / "核境造物_节点存档.json"
        self.record_path = user_data_dir() / "核境造物_成绩记录.json"
        self.level_manager = LevelManager(len(STAGE_NAMES))
        self.checkpoints = self.read_save_file()
        self.records = self.read_records()
        self.mission_buttons: Dict[str, pygame.Rect] = {}
        self.dashboard_page = "status"
        self.detail_modal = None
        self.detail_button = pygame.Rect(0, 0, 0, 0)
        self.detail_close_button = pygame.Rect(0, 0, 0, 0)
        self.dashboard_buttons: Dict[str, pygame.Rect] = {}
        self.operation_tool_rects: Dict[str, pygame.Rect] = {}
        self.stage_guide_open = False
        self.stage_guide_page = 0
        self.guide_prev = pygame.Rect(0, 0, 0, 0)
        self.guide_next = pygame.Rect(0, 0, 0, 0)
        self.guide_close = pygame.Rect(0, 0, 0, 0)
        self.guide_toggle_button = pygame.Rect(1196, 14, 113, 34)
        self.result_recorded = False
        self.audio = AudioManager()
        self.sound_button = pygame.Rect(1090, 14, 92, 34)
        self.menu_mode_buttons: Dict[str, pygame.Rect] = {}
        self.failure_reason = ""
        self.failure_advice = ""
        self.failure_detail = {}
        self.reset_save_button = pygame.Rect(0, 0, 0, 0)
        self.init_demo_system()
        self.init_settings_system()
        self.reset()

    def canvas_pos(self, window_pos: Tuple[int, int]) -> Tuple[int, int]:
        """将可缩放窗口中的鼠标坐标换算为固定逻辑画布坐标。"""
        x = int((window_pos[0] - self.viewport.x) / max(self.render_scale, 0.001))
        y = int((window_pos[1] - self.viewport.y) / max(self.render_scale, 0.001))
        return x, y

    def resize_display(self, size: Tuple[int, int], fullscreen: bool = False):
        """调整真实窗口尺寸。

        本版全屏不再使用 1:1 居中小画布，而是按显示器尺寸等比放大，
        尽量铺满屏幕，并保留正确的鼠标坐标换算。
        """
        self.fullscreen = bool(fullscreen)
        if sys.platform == "emscripten":
            # 浏览器画布尺寸由页面和 Pygbag 管理；避免 SDL FULLSCREEN 重建画布。
            self.fullscreen = False
            self.display = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
            return
        if self.fullscreen:
            # FULLSCREEN 会占用真实显示器分辨率；present_scaled 负责等比放大画面。
            self.display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            return
        width = max(MIN_WINDOW_WIDTH, int(size[0]))
        height = max(MIN_WINDOW_HEIGHT, int(size[1]))
        self.display = pygame.display.set_mode((width, height), pygame.RESIZABLE)

    def toggle_fullscreen(self):
        if getattr(self, "fullscreen", False):
            self.resize_display((WIDTH, HEIGHT), fullscreen=False)
            self.set_message("已退出全屏模式。", BLUE)
        else:
            self.resize_display((0, 0), fullscreen=True)
            self.set_message("已进入全屏模式：画面会按比例放大并居中显示。", BLUE)

    def present_scaled(self):
        """将固定设计分辨率画布显示到当前窗口。

        窗口/全屏都会按比例适配显示区域：
        - 大窗口和全屏：等比放大，避免出现小画面悬在中间；
        - 小窗口：等比缩小，避免内容裁切；
        - 始终更新 viewport 和 render_scale，保证鼠标点击位置正确。
        """
        window_width, window_height = self.display.get_size()
        raw_scale = max(0.1, min(window_width / WIDTH, window_height / HEIGHT))
        # 接近 1x 时强制使用原始像素，避免窗口边框造成 0.98x/1.02x 的轻微缩放使中文发虚；
        # 明显放大时仍按比例放大，满足窗口放大需求。
        self.render_scale = 1.0 if 0.94 <= raw_scale <= 1.06 else raw_scale
        render_width = max(1, int(WIDTH * self.render_scale))
        render_height = max(1, int(HEIGHT * self.render_scale))
        self.viewport = pygame.Rect(
            (window_width - render_width) // 2,
            (window_height - render_height) // 2,
            render_width,
            render_height
        )
        self.display.fill((17, 27, 35))
        if render_width == WIDTH and render_height == HEIGHT:
            self.display.blit(self.screen, self.viewport.topleft)
        else:
            # 放大时不用 smoothscale，避免小字被抗锯齿“糊掉”；
            # 缩小时仍用 smoothscale，避免过度锯齿。
            if self.render_scale >= 1.0:
                scaled = pygame.transform.scale(self.screen, (render_width, render_height))
            else:
                scaled = pygame.transform.smoothscale(self.screen, (render_width, render_height))
            self.display.blit(scaled, self.viewport.topleft)
        pygame.display.flip()

    def reset(self, clear_save: bool = False):
        if clear_save:
            self.checkpoints = {}
            try:
                self.backup_save_file("reset")
                self.save_path.unlink(missing_ok=True)
            except OSError:
                pass
        self.stage = 0
        if hasattr(self, "level_manager"):
            self.level_manager.reset(keep_records=not clear_save)
        self.failure_reason = ""
        self.failure_advice = ""
        self.failure_detail = {}
        self.placed = {}
        self.dragging = None
        self.selected = None
        self.info_card = None
        self.active_tab = "反应堆"
        self.menu = True
        self.report = False
        self.pump_choice = "监测强化"
        self.mission_key = "guided"
        previous_mode = getattr(self, "selected_mode", "guided")
        if not isinstance(previous_mode, str) or previous_mode not in PLAY_MODES:
            previous_mode = "guided"
        self.selected_mode = "demo" if getattr(self, "settings", {}).get("demo_mode", False) else previous_mode
        self.play_mode = self.selected_mode
        self.site = SITE_TYPES[0]
        self.funds = float(MISSION_TYPES["guided"]["funds"])
        self.days = 0.0
        self.safety = 100
        self.mistakes = 0
        self.message = "请选择任务目标，系统会随机生成建设场址。"
        self.message_color = BLACK
        self.progress_flags = set()
        self.anim = 0.0
        self.runtime = 0.0
        self.next_fault = 13.0
        self.fault = None
        self.fault_left = 0.0
        self.warning_event = None
        self.warning_left = 0.0
        self.operation_done: List[str] = []
        self.scrammed = False
        self.cooling_flow = 75.0
        self.slider_drag = False
        self.parameters = {}
        self.output_mw = 0.0
        self.thermal_mw = 0.0
        self.income_clock = 0.0
        self.protection_score = 100
        self.protection_verified = False
        self.collective_dose = 0.0
        self.max_task_dose = 0.0
        self.operation_seconds = 0
        self.dose_task = None
        self.dose_task_left = 0.0
        self.next_dose_task = 19.0
        self.history = {"temp": [], "pressure": [], "power": []}
        self.history_clock = 0.0
        self.dashboard_page = "status"
        self.dashboard_buttons = {}
        self.operation_tool_rects = {}
        self.stage_guide_open = False
        self.stage_guide_page = 0
        self.level_popup = None
        self.level_popup_continue = pygame.Rect(0, 0, 0, 0)
        self.level_popup_rect = pygame.Rect(0, 0, 0, 0)
        self.stage_guide_rect = pygame.Rect(0, 0, 0, 0)
        self.level_map_rect = pygame.Rect(0, 0, 0, 0)
        self.work_plan_rect = pygame.Rect(0, 0, 0, 0)
        self.review_rect = pygame.Rect(0, 0, 0, 0)
        self.report_rect = pygame.Rect(0, 0, 0, 0)
        self.report_restart = pygame.Rect(0, 0, 0, 0)
        self.report_close = pygame.Rect(0, 0, 0, 0)
        self.report_menu = pygame.Rect(0, 0, 0, 0)
        self.report_review = pygame.Rect(0, 0, 0, 0)
        self.settings_rect = pygame.Rect(0, 0, 0, 0)
        self.card_rect = pygame.Rect(0, 0, 0, 0)
        self.card_close_button = pygame.Rect(0, 0, 0, 0)
        self.grace_used = set()
        self.validation_penalties = set()
        self.challenge_finished = False
        self.challenge_shuffle_modules = False
        self.challenge_shuffle_button = pygame.Rect(0, 0, 0, 0)
        self.result_recorded = False
        self.card_scroll = 0
        self.card_max_scroll = 0
        self.feedback_rings: List[RingEffect] = []
        self.feedback_particles: List[ParticleEffect] = []
        self.float_texts: List[dict] = []
        self.banner = None
        self.mode_transition = None
        self.barriers = {"fuel": 100.0, "primary": 100.0, "safety": 100.0, "environment": 100.0}
        self.event_log: List[dict] = []
        self.diagnosis_resolved = True
        self.diagnostic_buttons: Dict[str, pygame.Rect] = {}
        self.diagnosis_attempts = 0
        self.work_plan_open = False
        self.work_plan_selection = {"route": None, "staff": None, "equipment": None}
        self.work_plan_buttons: Dict[Tuple[str, str], pygame.Rect] = {}
        self.work_plan_confirm = pygame.Rect(0, 0, 0, 0)
        self.work_plan_cancel = pygame.Rect(0, 0, 0, 0)
        self.review_open = False
        self.review_key = "general"
        self.review_answer = None
        self.review_feedback = ""
        self.review_buttons: Dict[str, pygame.Rect] = {}
        self.review_close = pygame.Rect(0, 0, 0, 0)
        self.review_score = 0
        self.equipment_health = {key: 100.0 for key in HEALTH_META}
        self.health_clock = 0.0
        self.service_job = None
        self.service_count = 0
        self.lost_revenue = 0.0
        self.work_plan_violations = 0
        self.power_cap = 1.0
        self.maintenance_button = pygame.Rect(0, 0, 0, 0)
        self.repair_button = pygame.Rect(0, 0, 0, 0)
        self.installed_costs: Dict[str, int] = {}
        self.primary_pump_safety_delta = 0
        self.recommend_plan_button = pygame.Rect(0, 0, 0, 0)
        self.site_buttons: Dict[str, pygame.Rect] = {}
        self.site_selection_open = False
        self.parameter_adjustments = {"condenser_pressure": 0.0, "primary_flow": 0.0, "sg_level": 0.0, "temperature": 0.0}
        self.commissioning_quality = 100.0
        self.last_choice_effect = "选址、调试和事故处置会实时影响关键参数。"
        self.choice_effect_lines = ["选址、调试和事故处置会在这里显示具体参数变化。"]
        self.choice_effect_until = 0
        self.decision_review: List[dict] = []
        self.accident_choice_buttons: Dict[int, pygame.Rect] = {}
        self.accident_choice_resolved = False
        self.accident_choice_feedback = ""
        self.active_reference_accident = None
        self.last_reference_accident = None
        self.reference_accident_counter = 0
        self.accident_gallery_state = {i: "locked" for i in range(1, 21)}
        self.accident_atlas_page = 0
        self.accident_atlas_prev = pygame.Rect(0, 0, 0, 0)
        self.accident_atlas_next = pygame.Rect(0, 0, 0, 0)
        self.pending_derived_case_id = None
        self.level_map_open = False
        self.level_map_button = pygame.Rect(0, 0, 0, 0)
        self.level_map_close = pygame.Rect(0, 0, 0, 0)
        self.task_detail_mode = "提示"
        self.focus_ui = True
        self.show_blueprint_labels = False
        self.blueprint_label_button = pygame.Rect(0, 0, 0, 0)
        self.challenge_shuffle_button = pygame.Rect(0, 0, 0, 0)
        self.task_panel_buttons: Dict[str, pygame.Rect] = {}
        self.strategy_bias = {"安全": 0, "平衡": 0, "激进": 0}
        self.strategy_history: List[dict] = []
        self.param_flash = {}
        self.countdown_audio_second = None
        self.level_started_at = pygame.time.get_ticks()
        self.snap_target: Optional[pygame.Rect] = None
        self.pending_install: Optional[str] = None
        self.cool_minus_button = pygame.Rect(0, 0, 0, 0)
        self.cool_plus_button = pygame.Rect(0, 0, 0, 0)
        self.tooltip_box: Optional[Tuple[str, str, pygame.Rect]] = None
        self.starter_fault_handled = False
        self.side_goals: List[dict] = []
        self.equipment_variants = {"steam_gen": "standard", "turbine": "standard", "condenser": "standard"}
        self.variant_buttons: Dict[Tuple[str, str], pygame.Rect] = {}
        self.dispatch_task = None
        self.dispatch_left = 0.0
        self.next_dispatch = 24.0
        self.completed_dispatch = 0
        self.dispatch_failures = 0
        self.achievements_unlocked: List[str] = []
        self.gallery_unlocked: List[str] = []
        self.quiz = {"flush": None, "seal": None, "diesel_a_test": False, "diesel_b_test": False}
        self.critical_step = 0
        self.selected_critical = None
        self.critical_tool_ready = {"fuel_load": False, "rod_check": False, "pump_start": False, "zero_power_test": False}
        self.critical_tool_rects = {}
        self.critical_option_rects = []
        self.choice_order_cache = {}
        self.selected_quiz = None
        self.commissioning_tool_ready = {"flush": False, "seal": False, "diesel_a_test": False, "diesel_b_test": False}
        self.commissioning_tool_rects = {}
        self.commissioning_target_hint = None
        self.minor_event = None
        self.minor_event_left = 0.0
        self.minor_event_buttons = {}
        self.minor_events_remaining = random.randint(1, 2)
        self.next_minor_event = random.uniform(6.0, 11.0)
        self.tip_index = 0
        for up in self.upgrades.values():
            up.level = 0
            up.in_progress = False
            up.remaining = 0
        self.update_parameters(0)

    # ------------------------- 成绩记录与任务 -------------------------


    # ------------------------- 阶段引导 -------------------------


    # ------------------------- 平衡、音效与视觉反馈 -------------------------


    # ------------------------- 辐射防护运行任务 -------------------------


    # ------------------------- 故障与升级 -------------------------


    def start_drag(self, key, pos):
        if getattr(self, "site_selection_open", False):
            self.set_message("请先完成厂址选择，再开始拖拽建设。", WARNING)
            return
        if (self.stage == 0 and self.play_mode in ("starter", "guided", "demo")
                and key != self.next_install_key()):
            target = self.next_install_key()
            target_name = ALL_MODULES[target].name if target in ALL_MODULES else "当前目标"
            self.set_message(f"教学关已锁定顺序：请先拖拽“{target_name}”。其他模块会在完成后自动解锁。", WARNING)
            self.audio.play("warning")
            return
        if key in self.placed:
            return
        self.selected = key
        self.pending_install = key if self.can_click_install() else None
        module = ALL_MODULES[key]
        ghost = module.slot.copy()
        ghost.center = pos
        self.dragging = {
            "key": key, "rect": ghost, "offset": (ghost.width // 2, ghost.height // 2),
            "start_pos": pos, "moved": False
        }

    def finish_drag(self):
        if not self.dragging:
            return
        if not self.dragging.get("moved") and not self.dragging.get("operation") and self.can_click_install():
            key = self.dragging["key"]
            self.pending_install = key
            self.dragging = None
            self.snap_target = ALL_MODULES[key].slot.copy()
            self.set_message(f"已选中：{ALL_MODULES[key].name}。现在点击中间对应虚线槽位即可安装，也可重新拖拽。", BLUE)
            return

        snap_margin = 32 if self.is_guided_mode() else 10
        if self.dragging.get("commissioning"):
            task_key = self.dragging["key"]
            target = self.commissioning_target_rect(task_key)
            if target.inflate(snap_margin * 2, snap_margin * 2).collidepoint(self.dragging["rect"].center):
                self.finish_commissioning_drag(task_key)
            else:
                self.set_message("调试工具没有放入目标区域，请重新拖拽。", WARNING)
                self.audio.play("warning")
            self.dragging = None
            self.snap_target = None
            return
        if self.dragging.get("critical"):
            task_key = self.dragging["key"]
            target = self.critical_target_rect(task_key)
            if target.inflate(snap_margin * 2, snap_margin * 2).collidepoint(self.dragging["rect"].center):
                self.finish_critical_drag(task_key)
            else:
                self.set_message("启动工具没有放入目标区域，请重新拖拽。", WARNING)
                self.audio.play("warning")
            self.dragging = None
            self.snap_target = None
            return
        if self.dragging.get("operation"):
            tool_key = self.dragging["key"]
            target = RUN_OPERATION_TOOLS[tool_key]["target"]
            if target.inflate(snap_margin * 2, snap_margin * 2).collidepoint(self.dragging["rect"].center):
                self.activate_operation_tool(tool_key)
            else:
                self.set_message("没有放入目标槽位，请再次拖拽。", WARNING)
            self.dragging = None
            self.snap_target = None
            return

        key = self.dragging["key"]
        module = ALL_MODULES[key]
        center = self.dragging["rect"].center
        if module.slot.inflate(snap_margin * 2, snap_margin * 2).collidepoint(center):
            self.install(key)
            self.pending_install = None
        else:
            candidate_modules = CIVIL if self.stage == 0 else EQUIPMENT
            wrong_slot = next((other for other, other_module in candidate_modules.items()
                               if other != key and other_module.slot.collidepoint(center)), None)
            if wrong_slot:
                self.penalty(4, f"安装位置错误：{module.name}不能安装在{candidate_modules[wrong_slot].name}槽位。")
            else:
                self.set_message("设备未靠近对应虚线区域，已返回设备库。也可以点击对应槽位安装。", WARNING)
        self.dragging = None
        self.snap_target = None


    def clear_pointer_state(self):
        """取消拖拽、滑块和吸附提示。

        这是防“点不动”的兜底：如果弹窗切换、鼠标释放丢失或用户按 Esc，
        不让旧拖拽/旧滑块状态继续占用点击。
        """
        self.dragging = None
        self.slider_drag = False
        self.pending_install = None
        self.snap_target = None
        self.tooltip_box = None
        # 同步清理最容易残留的鼠标热区，避免关闭弹窗后下一次点击仍被旧区域吞掉。
        self.cool_slider_active = False
        self.cool_slider = pygame.Rect(0, 0, 0, 0)
        self.cool_minus_button = pygame.Rect(0, 0, 0, 0)
        self.cool_plus_button = pygame.Rect(0, 0, 0, 0)
        self.detail_button = pygame.Rect(0, 0, 0, 0)
        self.detail_close_button = pygame.Rect(0, 0, 0, 0)
        self.plan_open_button = pygame.Rect(0, 0, 0, 0)

    def recover_input_state(self):
        """每帧修复可能残留的输入状态，避免玩到一半鼠标被旧状态锁住。"""
        try:
            left_pressed = bool(pygame.mouse.get_pressed(3)[0])
        except Exception:
            left_pressed = False
        try:
            mouse_focused = bool(pygame.mouse.get_focused())
        except Exception:
            mouse_focused = True
        if not mouse_focused:
            self.clear_pointer_state()
            return
        if not left_pressed:
            # 无论是否已经发生明显移动，只要鼠标左键已释放，就不允许旧拖拽/旧滑块继续锁住点击。
            # 这能覆盖系统丢失 MOUSEBUTTONUP、窗口失焦、拖到窗口外释放等情况。
            if self.slider_drag or self.dragging:
                self.clear_pointer_state()
        # 运行外不允许隐藏冷却水滑块继续接管点击。
        if self.stage != 4:
            self.slider_drag = False
            self.cool_slider_active = False
        # 若剂量任务已经结束，作业策划弹窗自动关闭，避免空弹窗挡住界面。
        if getattr(self, "work_plan_open", False) and not getattr(self, "dose_task", None):
            self.work_plan_open = False
            self.work_plan_buttons = {}
            self.work_plan_confirm = pygame.Rect(0, 0, 0, 0)
            self.work_plan_cancel = pygame.Rect(0, 0, 0, 0)
            self.recommend_plan_button = pygame.Rect(0, 0, 0, 0)
        # 选址弹窗只允许在建设阶段使用；旧状态残留时自动关闭。
        if getattr(self, "site_selection_open", False) and (self.menu or self.stage != 0):
            self.site_selection_open = False
            self.site_buttons = {}
        if not getattr(self, "site_selection_open", False):
            self.site_buttons = {}
        # 主菜单打开时不应残留游戏内弹窗；残留遮罩会让用户感觉“点不动”。
        if self.menu:
            self.report = False
            self.detail_modal = None
            self.info_card = None
            self.work_plan_open = False
            self.review_open = False
            self.level_map_open = False
            self.stage_guide_open = False
        # 若某个弹窗已经关闭，则它的旧矩形不应继续参与点击判断。
        if not getattr(self, "report", False):
            self.report_rect = pygame.Rect(0, 0, 0, 0)
        if not getattr(self, "work_plan_open", False):
            self.work_plan_rect = pygame.Rect(0, 0, 0, 0)
        if not getattr(self, "review_open", False):
            self.review_rect = pygame.Rect(0, 0, 0, 0)
        if not getattr(self, "level_map_open", False):
            self.level_map_rect = pygame.Rect(0, 0, 0, 0)
        if not getattr(self, "stage_guide_open", False):
            self.stage_guide_rect = pygame.Rect(0, 0, 0, 0)
        if not getattr(self, "info_card", None):
            self.card_rect = pygame.Rect(0, 0, 0, 0)
            self.card_close_button = pygame.Rect(0, 0, 0, 0)
        if not getattr(self, "detail_modal", None):
            self.detail_modal_rect = pygame.Rect(0, 0, 0, 0)
            self.detail_close_button = pygame.Rect(0, 0, 0, 0)
        if not getattr(self, "level_popup", None):
            self.level_popup_rect = pygame.Rect(0, 0, 0, 0)
            self.level_popup_continue = pygame.Rect(0, 0, 0, 0)

    def close_transient_overlays(self, keep: str = ""):
        """关闭非当前弹窗，避免多个半透明层叠在一起造成点击被上层吞掉。"""
        if keep != "settings":
            self.settings_open = False
        if keep != "detail":
            self.detail_modal = None
        if keep != "info":
            self.info_card = None
        if keep != "work_plan":
            self.work_plan_open = False
        if keep != "review":
            self.review_open = False
        if keep != "level_map":
            self.level_map_open = False
        if keep != "stage_guide":
            self.stage_guide_open = False
        if keep != "site":
            self.site_selection_open = False
        if keep != "level_popup":
            self.level_popup = None
        # 关闭状态和旧热区一起清掉，防止透明层消失后仍有隐藏按钮抢点击。
        self.settings_controls = {}
        self.work_plan_buttons = {}
        self.review_buttons = {}
        self.diagnostic_buttons = {}
        self.accident_choice_buttons = {}
        self.clear_pointer_state()

    def mouse_down(self, pos, button):
        if self.menu:
            if button == 1:
                if getattr(self, "settings_open", False):
                    settings_rect = getattr(self, "settings_rect", pygame.Rect(340, 132, 800, 596))
                    if button == 1 and not settings_rect.collidepoint(pos):
                        self.settings_open = False
                        self.write_settings_file()
                        self.clear_pointer_state()
                        self.audio.play("click")
                    else:
                        self.handle_settings_click(pos, button)
                    return
                if getattr(self, "menu_settings", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                    self.toggle_settings()
                    return
                for mode, rect in self.menu_mode_buttons.items():
                    if rect.collidepoint(pos):
                        self.selected_mode = mode
                        if hasattr(self, "settings"):
                            self.settings["demo_mode"] = (mode == "demo")
                            self.write_settings_file()
                        self.audio.play("click")
                        if mode == "demo":
                            # 答辩模式强调“一键自动演示”，点击模式卡后直接进入默认任务。
                            self.start_project("guided")
                        return
                for key, rect in self.mission_buttons.items():
                    if rect.collidepoint(pos):
                        if self.selected_mode == "starter" and key != "guided":
                            self.set_message("极简教学固定使用“教学并网”目标，请点击第一项。", WARNING)
                            return
                        self.start_project(key)
                        return
                if getattr(self, "menu_continue", None) and self.menu_continue.collidepoint(pos):
                    self.restore_checkpoint()
                    return
                if getattr(self, "menu_reset_save", None) and self.menu_reset_save.collidepoint(pos):
                    self.reset_all_saved_data()
                    return
            return

        # 顶层弹窗优先处理，顺序与 draw_frame 的绘制层级保持一致。
        # 任何顶层弹窗都支持“点击外部关闭”或 Esc 关闭，避免用户误以为界面卡住。
        if self.level_popup:
            if button == 1:
                popup_rect = getattr(self, "level_popup_rect", pygame.Rect(392, 150, 696, 520))
                if (self.level_popup_continue.collidepoint(pos)
                        or getattr(self, "level_popup_next_box", pygame.Rect(0, 0, 0, 0)).collidepoint(pos)
                        or not popup_rect.collidepoint(pos)):
                    self.close_level_popup()
                    self.clear_pointer_state()
                    self.audio.play("click")
                else:
                    self.set_message("点击右下角“进入下一关”，或点击弹窗外关闭。", TEXT_MUTED)
            return

        if getattr(self, "settings_open", False):
            if button == 1:
                settings_rect = getattr(self, "settings_rect", pygame.Rect(340, 132, 800, 596))
                if not settings_rect.collidepoint(pos):
                    self.settings_open = False
                    self.write_settings_file()
                    self.clear_pointer_state()
                    self.audio.play("click")
                    return
            self.handle_settings_click(pos, button)
            return

        if getattr(self, "detail_modal", None):
            if button == 1:
                modal_rect = getattr(self, "detail_modal_rect", pygame.Rect(282, 82, 936, 716))
                if getattr(self, "detail_close_button", pygame.Rect(0, 0, 0, 0)).collidepoint(pos) or not modal_rect.collidepoint(pos):
                    self.detail_modal = None
                    self.clear_pointer_state()
                    self.audio.play("click")
                else:
                    self.set_message("点击“关闭”或弹窗外可返回操作。", TEXT_MUTED)
                return
            return

        # 弹窗/教程层必须优先响应点击。
        # 之前这里先判断 site_selection_open，导致“选址小地图”虽然被教程遮住，
        # 但仍然抢走鼠标事件，玩家点击“下一页 / 跳过总览”没有反应。
        if self.stage_guide_open:
            if button == 1 and self.guide_prev.collidepoint(pos):
                self.stage_guide_page = max(0, self.stage_guide_page - 1)
                self.audio.play("click")
            elif button == 1 and self.guide_next.collidepoint(pos):
                self.advance_stage_guide()
            elif button == 1 and (self.guide_close.collidepoint(pos) or not getattr(self, "stage_guide_rect", pygame.Rect(414, 178, 662, 535)).collidepoint(pos)):
                self.stage_guide_open = False
                self.clear_pointer_state()
                self.audio.play("click")
            return

        if getattr(self, "play_mode", "") == "demo" and self.handle_demo_click(pos, button):
            return

        if getattr(self, "level_map_open", False):
            if button == 1:
                map_rect = getattr(self, "level_map_rect", pygame.Rect(212, 96, 1058, 706))
                if self.level_map_close.collidepoint(pos) or not map_rect.collidepoint(pos):
                    self.level_map_open = False
                    self.clear_pointer_state()
                    self.audio.play("click")
                else:
                    self.set_message("关卡地图已打开，按 Esc / M 或点击外部关闭。", TEXT_MUTED)
            return

        if self.site_selection_open:
            if button == 1:
                for key, rect in self.site_buttons.items():
                    if rect.collidepoint(pos):
                        self.choose_site(key)
                        return
                # 点击选址窗口外直接关闭，避免玩家误以为界面卡住。
                self.site_selection_open = False
                self.site_buttons = {}
                self.clear_pointer_state()
                self.set_message("已关闭选址窗口；需要时可重新打开关卡地图查看厂址。", TEXT_MUTED)
            return

        if self.work_plan_open:
            if button == 1:
                work_rect = getattr(self, "work_plan_rect", pygame.Rect(304, 72, 884, 764))
                if not work_rect.collidepoint(pos):
                    self.work_plan_open = False
                    self.clear_pointer_state()
                    self.audio.play("click")
                    return
                for (group, key), rect in self.work_plan_buttons.items():
                    if rect.collidepoint(pos):
                        self.work_plan_selection[group] = key
                        self.audio.play("click")
                        return
                if self.recommend_plan_button.collidepoint(pos):
                    self.apply_recommended_plan()
                    return
                if self.work_plan_confirm.collidepoint(pos):
                    self.execute_work_plan()
                    return
                if self.work_plan_cancel.collidepoint(pos):
                    self.work_plan_open = False
                    self.clear_pointer_state()
                    return
                self.set_message("请在作业策划弹窗内选择方案，或点击外部返回。", TEXT_MUTED)
            return

        if self.review_open:
            if button == 1:
                review_rect = getattr(self, "review_rect", pygame.Rect(371, 130, 750, 635))
                if not review_rect.collidepoint(pos):
                    self.review_open = False
                    self.clear_pointer_state()
                    self.audio.play("click")
                    return
                for option, rect in self.review_buttons.items():
                    if rect.collidepoint(pos):
                        self.answer_review(option)
                        return
                if self.review_close.collidepoint(pos):
                    self.review_open = False
                    self.clear_pointer_state()
                    return
            return

        if self.report:
            if button == 1 and self.report_restart.collidepoint(pos):
                self.restore_checkpoint()
            elif button == 1 and self.report_close.collidepoint(pos):
                self.report = False
                self.clear_pointer_state()
            elif button == 1 and hasattr(self, "report_menu") and self.report_menu.collidepoint(pos):
                self.return_to_menu()
            elif button == 1 and hasattr(self, "report_review") and self.report_review.collidepoint(pos):
                self.open_review()
            elif button == 1 and not getattr(self, "report_rect", pygame.Rect(360, 118, 780, 650)).collidepoint(pos):
                self.report = False
                self.clear_pointer_state()
                self.audio.play("click")
            return

        if self.info_card:
            if button == 1 and hasattr(self, "card_close_button") and self.card_close_button.collidepoint(pos):
                self.info_card = None
                self.clear_pointer_state()
            elif button == 1:
                # 防御性处理：若知识卡刚打开而本帧还没绘制出 card_rect，
                # 第二次点击不应触发 AttributeError 或造成卡死。
                card_rect = getattr(self, "card_rect", pygame.Rect(0, 0, 0, 0))
                if not card_rect.collidepoint(pos):
                    self.info_card = None
                    self.clear_pointer_state()
            return

        if button == 1 and self.click_install_at(pos):
            return

        slider_blocked = bool(self.dose_task or self.fault or (self.warning_event and self.warning_event.get("key") != "vacuum"))
        if self.stage == 4 and button == 1 and getattr(self, "cool_slider_active", False) and not slider_blocked:
            if getattr(self, "cool_minus_button", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                self.cooling_flow = clamp(self.cooling_flow - 5, 40, 100)
                self.mark_param_change("冷却水流量", WARNING)
                self.add_float_text(f"冷却水 {self.cooling_flow:.0f}%", RIGHT.centerx, 184, WARNING)
                self.set_message(f"冷却水流量调整为 {self.cooling_flow:.0f}%。", BLUE)
                return
            if getattr(self, "cool_plus_button", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                self.cooling_flow = clamp(self.cooling_flow + 5, 40, 100)
                self.mark_param_change("冷却水流量", GOOD)
                self.add_float_text(f"冷却水 {self.cooling_flow:.0f}%", RIGHT.centerx, 184, GOOD)
                self.set_message(f"冷却水流量调整为 {self.cooling_flow:.0f}%。", BLUE)
                return

        if button == 1:
            term_regions = [
                ("冷凝器绝对压力", pygame.Rect(1175, 320, 268, 28)),
                ("冷却水流量", pygame.Rect(1175, 345, 268, 32)),
                ("ALARA", pygame.Rect(1180, 430, 260, 28)),
            ]
            for term, rect in term_regions:
                if rect.collidepoint(pos):
                    self.show_term_tip(term, rect)
                    if self.tooltip_box:
                        return

        if self.sound_button.collidepoint(pos) and button == 1:
            self.audio.toggle()
            if hasattr(self, "settings"):
                self.settings["sound"] = self.audio.enabled
                self.write_settings_file()
            self.set_message("音效已开启。" if self.audio.enabled else "音效已关闭。", BLUE)
            return
        if getattr(self, "settings_button", pygame.Rect(0,0,0,0)).collidepoint(pos) and button == 1:
            self.toggle_settings()
            return
        if getattr(self, "blueprint_label_button", pygame.Rect(0, 0, 0, 0)).collidepoint(pos) and button == 1:
            self.show_blueprint_labels = not getattr(self, "show_blueprint_labels", False)
            if getattr(self, "play_mode", "") == "challenge":
                self.set_message("中央槽位标识已显示。" if self.show_blueprint_labels else "中央槽位标识已隐藏。", BLUE)
            else:
                self.set_message("中央背景文字已显示。" if self.show_blueprint_labels else "中央背景文字已隐藏。", BLUE)
            self.audio.play("click")
            return
        if self.guide_toggle_button.collidepoint(pos) and button == 1:
            if self.play_mode == "challenge":
                self.tutorial = False
                self.set_message("挑战模式已锁定实时答案提示：请使用参数症状、趋势与屏障面板完成诊断。", WARNING)
                return
            self.tutorial = not self.tutorial
            if not self.tutorial:
                self.stage_guide_open = False
                self.set_message("实时指引已关闭；可通过关卡地图查看整体流程。", TEXT_MUTED)
            else:
                self.set_message("实时指引已开启，将提示下一步操作。", BLUE)
            return
        if self.level_map_button.collidepoint(pos) and button == 1:
            self.toggle_level_map()
            return
        # 阶段教程已取消：关卡地图和实时指引承担引导功能。
        if button == 1:
            for mode, rect in getattr(self, "task_panel_buttons", {}).items():
                if rect.collidepoint(pos):
                    self.task_detail_mode = mode
                    self.audio.play("click")
                    return
        if button == 1 and getattr(self, "play_mode", "") == "challenge" and getattr(self, "challenge_shuffle_button", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            self.challenge_shuffle_modules = not getattr(self, "challenge_shuffle_modules", False)
            self.set_message("挑战模式：已启用随机顺序。" if self.challenge_shuffle_modules else "挑战模式：已恢复固定顺序。", BLUE)
            self.audio.play("click")
            return
        if self.stage == 2 and button == 1:
            for rect, key, correct in getattr(self, "quiz_option_rects", []):
                if rect.collidepoint(pos):
                    self.answer_quiz(key, correct)
                    return
        if self.stage == 3 and button == 1:
            for rect, key, correct in getattr(self, "critical_option_rects", []):
                if rect.collidepoint(pos):
                    self.answer_critical_option(key, correct)
                    return
        if self.reset_button.collidepoint(pos) and button == 1:
            self.restore_checkpoint(self.stage)
            return
        if getattr(self, "reset_save_button", None) and self.reset_save_button.collidepoint(pos) and button == 1:
            self.reset_all_saved_data()
            return
        if self.stage == 1 and button == 1:
            for (device_key, variant_key), rect in self.variant_buttons.items():
                if rect.collidepoint(pos):
                    self.set_variant(device_key, variant_key)
                    return

        if self.stage < 4 and self.stage_button.collidepoint(pos) and button == 1:
            self.proceed_stage()
            return
        if self.stage == 4 and self.report_button.collidepoint(pos) and button == 1:
            self.finish_challenge()
            return
        if self.stage == 4 and self.challenge_finished:
            self.set_message("本局成绩已锁定，请点击“结束挑战”重新查看报告，或返回主菜单。", TEXT_MUTED)
            return

        if self.stage == 1 and button == 1:
            for tab, rect in self.tab_rects.items():
                if rect.collidepoint(pos):
                    self.active_tab = tab
                    return
            if "primary_pump" not in self.placed:
                for choice, rect in self.primary_choice_buttons.items():
                    if rect.collidepoint(pos):
                        self.pump_choice = choice
                        self.set_message(f"设计选择：采用{choice}方案。", BLUE)
                        return

        if self.stage in (0, 1):
            self.rebuild_toolbar_rects()
            for key, rect in self.toolbar_rects.items():
                if rect.collidepoint(pos):
                    if button == 1:
                        self.start_drag(key, pos)
                    elif button == 3:
                        self.open_info_card(key)
                    return
            for key, rect in self.placed.items():
                if rect.collidepoint(pos):
                    if button == 1:
                        self.selected = key
                        self.open_info_card(key)
                    elif button == 3:
                        self.open_info_card(key)
                    return

        elif self.stage == 2 and button == 1:
            for key, rect in self.action_rects.items():
                if rect.collidepoint(pos):
                    self.select_commissioning_task(key)
                    return
            for key, rect in getattr(self, "commissioning_tool_rects", {}).items():
                if rect.collidepoint(pos):
                    self.start_commissioning_drag(key, pos)
                    return
            for rect, key, correct in getattr(self, "quiz_option_rects", []):
                if rect.collidepoint(pos):
                    self.answer_quiz(key, correct)
                    return

        elif self.stage == 3 and button == 1:
            for i, rect in enumerate(self.critical_buttons):
                if rect.collidepoint(pos):
                    self.critical_action(i)
                    return
            for key, rect in getattr(self, "critical_tool_rects", {}).items():
                if rect.collidepoint(pos):
                    self.start_critical_drag(key, pos)
                    return
            for rect, key, correct in getattr(self, "critical_option_rects", []):
                if rect.collidepoint(pos):
                    self.answer_critical_option(key, correct)
                    return

        elif self.stage == 4:
            if button == 1:
                # 左侧“制定作业方案”是当前任务主按钮，优先响应，避免被右侧事件/页签逻辑抢掉。
                plan_rect = getattr(self, "plan_open_button", pygame.Rect(0, 0, 0, 0))
                fallback_plan_rect = pygame.Rect(12, self.left_content_top() + 158, 214, 42)
                if self.dose_task and (plan_rect.collidepoint(pos) or fallback_plan_rect.collidepoint(pos)):
                    self.open_work_plan()
                    return
                slider_blocked = bool(self.dose_task or self.fault or (self.warning_event and self.warning_event.get("key") != "vacuum"))
                # 冷凝器真空事件中，滑块需要优先响应；否则会被“查看事故详情”按钮误拦截。
                if (getattr(self, "cool_slider_active", False)
                        and not slider_blocked
                        and hasattr(self, "cool_slider")
                        and self.cool_slider.inflate(18, 30).collidepoint(pos)):
                    self.slider_drag = True
                    self.move_slider(pos[0])
                    return
                if getattr(self, "detail_button", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                    if hasattr(self, "close_transient_overlays"):
                        self.close_transient_overlays(keep="detail")
                    self.detail_modal = "accident"
                    self.audio.play("click")
                    return
                for page, rect in self.dashboard_buttons.items():
                    if rect.collidepoint(pos):
                        hard_event = self.fault or self.dose_task or (self.warning_event and self.diagnosis_resolved)
                        if page != "status" and hard_event:
                            self.dashboard_page = "status"
                            self.set_message("当前需立即处置，已保持“状态”页显示操作指引。", WARNING)
                        else:
                            self.dashboard_page = page
                            self.audio.play("click")
                        return
                if self.dashboard_page == "atlas":
                    if getattr(self, "accident_atlas_prev", pygame.Rect(0,0,0,0)).collidepoint(pos):
                        self.accident_atlas_page = max(0, self.accident_atlas_page - 1)
                        self.audio.play("click")
                        return
                    if getattr(self, "accident_atlas_next", pygame.Rect(0,0,0,0)).collidepoint(pos):
                        self.accident_atlas_page = min(19, self.accident_atlas_page + 1)
                        self.audio.play("click")
                        return
                if self.dashboard_page == "log":
                    # 日志页仅展示，不拦截其他操作。
                    pass
                for idx, rect in getattr(self, "minor_event_buttons", {}).items():
                    if rect.collidepoint(pos):
                        self.answer_minor_event(idx)
                        return
                for choice, rect in self.diagnostic_buttons.items():
                    if rect.collidepoint(pos):
                        self.diagnose_warning(choice)
                        return
                for option_index, rect in getattr(self, "accident_choice_buttons", {}).items():
                    if rect.collidepoint(pos):
                        self.answer_accident_choice(option_index)
                        return
                if self.dose_task and hasattr(self, "plan_open_button") and self.plan_open_button.collidepoint(pos):
                    self.open_work_plan()
                    return
                for tool_key, rect in self.operation_tool_rects.items():
                    if rect.collidepoint(pos) and tool_key not in self.operation_done:
                        self.start_operation_drag(tool_key, pos)
                        return
                if hasattr(self, "repair_button") and self.repair_button.collidepoint(pos):
                    self.start_barrier_repair()
                    return
                if hasattr(self, "maintenance_button") and self.maintenance_button.collidepoint(pos):
                    self.start_maintenance()
                    return
                for key, rect in self.upgrade_buttons.items():
                    if rect.collidepoint(pos):
                        self.start_upgrade(key)
                        return
            for key, rect in self.placed.items():
                if rect.collidepoint(pos):
                    if button == 1:
                        self.selected = key
                        self.open_info_card(key)
                    elif button == 3:
                        self.open_info_card(key)
                    return

    def mouse_up(self, pos, button):
        if button == 1:
            if self.dragging:
                self.finish_drag()
            self.slider_drag = False
            self.snap_target = None

    def mouse_motion(self, pos):
        self.snap_target = None
        self.tooltip_box = None
        if self.dragging:
            ox, oy = self.dragging["offset"]
            start = self.dragging.get("start_pos", pos)
            if abs(pos[0] - start[0]) + abs(pos[1] - start[1]) > 6:
                self.dragging["moved"] = True
            self.dragging["rect"].topleft = (pos[0] - ox, pos[1] - oy)
            margin = 32 if self.is_guided_mode() else 10
            if self.dragging.get("commissioning"):
                target = self.commissioning_target_rect(self.dragging["key"])
            elif self.dragging.get("critical"):
                target = self.critical_target_rect(self.dragging["key"])
            else:
                target = (RUN_OPERATION_TOOLS[self.dragging["key"]]["target"]
                          if self.dragging.get("operation") else ALL_MODULES[self.dragging["key"]].slot)
            if target.inflate(margin * 2, margin * 2).collidepoint(self.dragging["rect"].center):
                self.snap_target = target.copy()
        if self.slider_drag:
            slider_blocked = bool(self.dose_task or self.fault or (self.warning_event and self.warning_event.get("key") != "vacuum"))
            if getattr(self, "cool_slider_active", False) and not slider_blocked:
                self.move_slider(pos[0])
            else:
                self.slider_drag = False

    def move_slider(self, x):
        if not hasattr(self, "cool_slider"):
            return
        old_value = float(getattr(self, "cooling_flow", 75.0))
        ratio = clamp((x - self.cool_slider.x) / self.cool_slider.width, 0, 1)
        self.cooling_flow = 40 + ratio * 60
        if abs(self.cooling_flow - old_value) >= 3:
            self.mark_param_change("冷却水流量", GOOD if self.cooling_flow >= old_value else WARNING)
            now = pygame.time.get_ticks()
            if now - getattr(self, "last_cooling_float_at", 0) > 450:
                self.add_float_text(f"冷却水 {self.cooling_flow:.0f}%", RIGHT.centerx, 184,
                                    GOOD if self.cooling_flow >= old_value else WARNING)
                self.last_cooling_float_at = now

    def prepare_frame_hitboxes(self):
        """每帧绘制前清空只属于当前画面的点击热区。

        这样能避免页面切换后，上一页留下的隐藏按钮、隐藏滑块或旧弹窗按钮继续抢鼠标，
        这是防止“看得见按钮却点不动”的重要兜底。真正显示的按钮会在本帧绘制时重新写入。
        """
        self.detail_button = pygame.Rect(0, 0, 0, 0)
        self.detail_close_button = pygame.Rect(0, 0, 0, 0)
        self.cool_slider_active = False
        self.cool_slider = pygame.Rect(0, 0, 0, 0)
        self.cool_minus_button = pygame.Rect(0, 0, 0, 0)
        self.cool_plus_button = pygame.Rect(0, 0, 0, 0)
        self.plan_open_button = pygame.Rect(0, 0, 0, 0)
        self.commissioning_tool_rects = {}
        self.critical_tool_rects = {}
        self.critical_option_rects = []
        self.minor_event_buttons = {}
        self.card_close_button = pygame.Rect(0, 0, 0, 0)
        self.level_map_close = pygame.Rect(0, 0, 0, 0)
        self.level_popup_continue = pygame.Rect(0, 0, 0, 0)
        self.level_popup_next_box = pygame.Rect(0, 0, 0, 0)
        self.blueprint_label_button = pygame.Rect(0, 0, 0, 0)
        # 页面切换时重建这些按钮；不让上一页的页签/维护按钮/升级按钮留在点击判断里。
        self.dashboard_buttons = {}
        self.task_panel_buttons = {}
        self.maintenance_button = pygame.Rect(0, 0, 0, 0)
        self.repair_button = pygame.Rect(0, 0, 0, 0)
        self.upgrade_buttons = {}
        if not getattr(self, "work_plan_open", False):
            self.work_plan_buttons = {}
            self.work_plan_confirm = pygame.Rect(0, 0, 0, 0)
            self.work_plan_cancel = pygame.Rect(0, 0, 0, 0)
            self.recommend_plan_button = pygame.Rect(0, 0, 0, 0)
        if not getattr(self, "review_open", False):
            self.review_buttons = {}
            self.review_close = pygame.Rect(0, 0, 0, 0)
        if self.stage != 4:
            self.operation_tool_rects = {}
            self.diagnostic_buttons = {}
            self.accident_choice_buttons = {}
        elif self.dashboard_page != "atlas":
            self.accident_atlas_prev = pygame.Rect(0, 0, 0, 0)
            self.accident_atlas_next = pygame.Rect(0, 0, 0, 0)

    # ------------------------- 单帧绘制 -------------------------
    def draw_frame(self):
        """绘制当前帧。

        把主循环中的绘制顺序收束到一个方法里，便于 smoke test 逐页检查，
        也避免后续修改界面时在多处重复维护同一串 draw 调用。
        """
        self.prepare_frame_hitboxes()
        self.draw_top()
        self.draw_left()
        self.draw_center()
        self.draw_bottom()
        self.draw_right()
        if self.site_selection_open and not self.menu:
            self.draw_site_selection_overlay()
        # draw_guide_highlights() 内部已经兜底判断挑战模式；这里不再重复分支。
        self.draw_guide_highlights()
        if hasattr(self, "draw_demo_highlight"):
            self.draw_demo_highlight()
        if getattr(self, "level_map_open", False):
            self.draw_level_map_overlay()
        if self.menu:
            self.draw_menu()
        if self.stage_guide_open and not self.menu:
            self.draw_stage_guide()
        if self.info_card:
            self.draw_info_card()
        if self.report:
            self.draw_report()
        if self.work_plan_open:
            self.draw_work_plan()
        if self.review_open:
            self.draw_incident_review()
        if getattr(self, "detail_modal", None):
            self.draw_detail_modal()
        if hasattr(self, "draw_demo_narration"):
            self.draw_demo_narration()
        if getattr(self, "settings_open", False):
            self.draw_settings_overlay()
        if self.level_popup:
            self.draw_level_popup()
        self.draw_tooltip()

    # ------------------------- 主循环 -------------------------
    def _finger_window_pos(self, event) -> Tuple[int, int]:
        """把 SDL 触摸事件的 0-1 坐标转换为当前窗口像素坐标。"""
        width, height = self.display.get_size()
        return int(float(event.x) * width), int(float(event.y) * height)

    async def run(self, max_frames: Optional[int] = None):
        """运行游戏。

        浏览器版必须在每帧末尾 ``await asyncio.sleep(0)``，把控制权交还给
        WebAssembly/浏览器事件循环；桌面版也可直接使用同一入口。
        ``max_frames`` 仅供自动化冒烟测试使用。
        """
        active = True
        frame_count = 0
        while active:
            dt = CLOCK.tick(FPS) / 1000
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    active = False
                elif event.type == pygame.VIDEORESIZE:
                    if not getattr(self, "fullscreen", False):
                        self.resize_display((event.w, event.h))
                    self.clear_pointer_state()
                elif event.type in (
                    getattr(pygame, "WINDOWFOCUSLOST", -10001),
                    getattr(pygame, "WINDOWLEAVE", -10002),
                    getattr(pygame, "WINDOWMINIMIZED", -10003),
                ):
                    # 窗口失焦/鼠标离开/最小化时，系统可能不会再发 MOUSEBUTTONUP。
                    self.clear_pointer_state()
                elif event.type == getattr(pygame, "FINGERDOWN", -20001):
                    self.mouse_down(self.canvas_pos(self._finger_window_pos(event)), 1)
                elif event.type == getattr(pygame, "FINGERUP", -20002):
                    self.mouse_up(self.canvas_pos(self._finger_window_pos(event)), 1)
                elif event.type == getattr(pygame, "FINGERMOTION", -20003):
                    self.mouse_motion(self.canvas_pos(self._finger_window_pos(event)))
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # SDL 可能同时派发触摸事件和带 touch=True 的鼠标事件，避免重复点击。
                    if not getattr(event, "touch", False):
                        self.mouse_down(self.canvas_pos(event.pos), event.button)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if not getattr(event, "touch", False):
                        self.mouse_up(self.canvas_pos(event.pos), event.button)
                elif event.type == pygame.MOUSEMOTION:
                    if not getattr(event, "touch", False):
                        self.mouse_motion(self.canvas_pos(event.pos))
                elif event.type == pygame.MOUSEWHEEL and self.info_card:
                    self.card_scroll = int(clamp(self.card_scroll - event.y, 0, self.card_max_scroll))
                elif event.type == pygame.KEYDOWN:
                    if self.level_popup:
                        if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                            self.close_level_popup()
                    elif self.stage_guide_open:
                        if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT):
                            self.advance_stage_guide()
                        elif event.key == pygame.K_LEFT:
                            self.stage_guide_page = max(0, self.stage_guide_page - 1)
                        elif event.key == pygame.K_ESCAPE:
                            self.stage_guide_open = False
                    elif getattr(self, "settings_open", False):
                        if event.key in (pygame.K_ESCAPE, pygame.K_s):
                            self.settings_open = False
                            self.write_settings_file()
                            self.clear_pointer_state()
                    elif getattr(self, "level_map_open", False):
                        if event.key in (pygame.K_ESCAPE, pygame.K_m):
                            self.level_map_open = False
                    elif getattr(self, "detail_modal", None) and event.key == pygame.K_ESCAPE:
                        self.detail_modal = None
                        self.clear_pointer_state()
                    elif getattr(self, "play_mode", "") == "demo" and self.handle_demo_key(event.key):
                        pass
                    elif self.site_selection_open:
                        if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                            choices = self.site_choices()
                            index = event.key - pygame.K_1
                            if 0 <= index < len(choices):
                                self.choose_site(choices[index]["key"])
                        elif event.key == pygame.K_ESCAPE:
                            self.site_selection_open = False
                            self.clear_pointer_state()
                            self.set_message("已关闭选址窗口。", TEXT_MUTED)
                    elif event.key == pygame.K_ESCAPE:
                        # 通用退出/解卡：关闭普通弹窗，取消拖拽和滑块状态。
                        self.info_card = None
                        self.detail_modal = None
                        self.work_plan_open = False
                        self.review_open = False
                        self.level_map_open = False
                        self.stage_guide_open = False
                        self.clear_pointer_state()
                    elif event.key == pygame.K_s:
                        self.toggle_settings()
                    elif event.key == pygame.K_m and not self.menu:
                        self.toggle_level_map()
                    elif event.key == pygame.K_F11:
                        # F11：切换全屏放大模式。画面按比例放大并居中显示。
                        self.toggle_fullscreen()
                    elif event.key == pygame.K_RETURN and self.stage == 4 and not self.menu and not self.report:
                        self.finish_challenge()
                    elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE) and self.stage in (0, 1) and self.selected:
                        self.remove(self.selected)
                        self.selected = None

            self.recover_input_state()
            paused_for_learning = self.simulation_paused()
            sim_dt = 0 if paused_for_learning else dt
            self.update_feedback(sim_dt)
            self.update_parameters(sim_dt)
            self.update_running(sim_dt)
            if self.play_mode == "demo":
                # 演示模式需要能越过选址覆盖层和通关弹窗；这些界面会让普通仿真暂停，
                # 但不能阻止答辩自动播放继续推进。
                self.update_demo_mode(dt)

            self.draw_frame()
            self.present_scaled()

            frame_count += 1
            if max_frames is not None and frame_count >= max_frames:
                active = False

            # Pygbag/浏览器版的关键让步点；桌面版同样安全。
            await asyncio.sleep(0)

        if sys.platform != "emscripten":
            pygame.quit()
        return frame_count
