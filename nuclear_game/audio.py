"""音效与背景音乐管理。

音效仍然使用程序内合成音；若 assets/sounds/background_music.mp3 存在，
则作为背景音乐循环播放。无声卡或音频设备异常时自动静默降级，不影响游戏运行。
"""
import math
import sys
from array import array
from typing import Dict, List, Tuple
import pygame

try:
    from .asset_manager import load_sound, asset_path
except Exception:
    load_sound = None
    asset_path = None


class AudioManager:
    """集中管理按钮音效、警报音效和背景音乐。"""

    def __init__(self):
        self.enabled = True
        self.available = False
        self.music_enabled = False
        self.music_available = False
        self.music_loaded = False
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(44100, -16, 1, 512)
            generated = {
                "place": self._tone([(660, 0.05), (880, 0.07)], 0.18),
                "success": self._tone([(523, 0.06), (659, 0.06), (784, 0.11)], 0.19),
                "warning": self._tone([(460, 0.10), (0, 0.04), (460, 0.10)], 0.17),
                "alarm": self._tone([(270, 0.12), (210, 0.12), (270, 0.12)], 0.23),
                "click": self._tone([(720, 0.035)], 0.12),
                "countdown": self._tone([(620, 0.035), (0, 0.025), (620, 0.035)], 0.12),
                "star": self._tone([(784, 0.045), (988, 0.07)], 0.16),
                "settlement": self._tone([(523, 0.05), (659, 0.05), (784, 0.05), (1046, 0.10)], 0.17),
            }
            self.sounds = {}
            for key, sound in generated.items():
                external = load_sound(f"{key}.wav") if load_sound else None
                self.sounds[key] = external or sound
            self.available = True
            self._load_background_music()
        except pygame.error:
            self.enabled = False
            self.music_enabled = False

    def _load_background_music(self):
        """加载背景音乐；加载失败不会影响普通音效与游戏启动。"""
        if not asset_path:
            return
        filename = "background_music.ogg" if sys.platform == "emscripten" else "background_music.mp3"
        path = asset_path("sounds", filename)
        if not path:
            # 桌面或浏览器资源缺失时允许回退到另一种格式。
            fallback = "background_music.mp3" if filename.endswith(".ogg") else "background_music.ogg"
            path = asset_path("sounds", fallback)
        if not path:
            return
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(0.28)
            self.music_available = True
            self.music_loaded = True
        except Exception:
            self.music_available = False
            self.music_loaded = False

    def _tone(self, segments: List[Tuple[int, float]], volume: float) -> pygame.mixer.Sound:
        rate = 44100
        samples = array("h")
        for frequency, duration in segments:
            count = max(1, int(rate * duration))
            for i in range(count):
                fade = min(1.0, i / max(1, rate * 0.008), (count - i) / max(1, rate * 0.012))
                signal = 0 if frequency == 0 else math.sin(2 * math.pi * frequency * i / rate)
                samples.append(int(32767 * volume * fade * signal))
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def play(self, key: str):
        if self.enabled and self.available and key in self.sounds:
            self.sounds[key].play()

    def set_music_enabled(self, enabled: bool):
        """按设置开关控制背景音乐，不影响按钮音效。"""
        self.music_enabled = bool(enabled)
        if not self.music_available:
            return
        try:
            if self.music_enabled:
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.play(-1)
            else:
                pygame.mixer.music.stop()
        except Exception:
            self.music_available = False
            self.music_enabled = False

    def toggle(self):
        """音效总开关；关闭音效时也暂停背景音乐，避免静音按钮名不副实。"""
        if self.available:
            self.enabled = not self.enabled
            try:
                if not self.enabled:
                    pygame.mixer.music.pause()
                elif self.music_enabled:
                    pygame.mixer.music.unpause()
                    if not pygame.mixer.music.get_busy():
                        pygame.mixer.music.play(-1)
            except Exception:
                pass
