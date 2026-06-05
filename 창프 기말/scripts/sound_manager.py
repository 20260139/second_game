# scripts/sound_manager.py
"""
BGM / SFX 관리 모듈.
- BGM: pygame.mixer.music  (스트리밍 재생, OGG 권장)
- SFX: pygame.mixer.Sound  (짧은 효과음)

사용법:
    from scripts.sound_manager import SoundManager
    sm = SoundManager()
    sm.play_bgm("asset/Sound/bgm_main.wav")
    sm.set_bgm_volume(0.7)
"""

import pygame
import os
import sys

sys.path.insert(0, '.')
try:
    from scripts.resource_path import resource_path
except Exception:
    def resource_path(p): return p


class SoundManager:
    def __init__(self):
        # mixer 초기화 (main.py 에서 pygame.init() 이후 호출됨)
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=44100, size=-16,
                                  channels=2, buffer=512)
            except Exception as e:
                print(f"[SoundManager] mixer 초기화 실패: {e}")

        self._bgm_volume = 0.7
        self._sfx_volume = 0.8
        self._bgm_path   = None
        self._sfx_cache  = {}    # path → pygame.Sound

    # ── BGM ──────────────────────────────────────────────

    def play_bgm(self, rel_path, loops=-1, fade_ms=1500):
        """BGM 재생. loops=-1 이면 무한 반복."""
        path = resource_path(rel_path)
        if not os.path.exists(path):
            print(f"[SoundManager] BGM 파일 없음: {path}")
            return
        try:
            if pygame.mixer.music.get_busy() and self._bgm_path == path:
                return   # 이미 재생 중
            pygame.mixer.music.stop()
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self._bgm_volume)
            pygame.mixer.music.play(loops, fade_ms=fade_ms)
            self._bgm_path = path
        except Exception as e:
            print(f"[SoundManager] BGM 재생 오류: {e}")

    def stop_bgm(self, fade_ms=800):
        try:
            pygame.mixer.music.fadeout(fade_ms)
        except Exception:
            pass

    def pause_bgm(self):
        try: pygame.mixer.music.pause()
        except Exception: pass

    def resume_bgm(self):
        try: pygame.mixer.music.unpause()
        except Exception: pass

    def set_bgm_volume(self, vol: float):
        self._bgm_volume = max(0.0, min(1.0, vol))
        try:
            pygame.mixer.music.set_volume(self._bgm_volume)
        except Exception:
            pass

    # ── SFX ──────────────────────────────────────────────

    def play_sfx(self, rel_path, volume=None):
        """효과음 재생 (캐시 사용)."""
        path = resource_path(rel_path)
        if path not in self._sfx_cache:
            if not os.path.exists(path):
                return
            try:
                self._sfx_cache[path] = pygame.mixer.Sound(path)
            except Exception as e:
                print(f"[SoundManager] SFX 로드 오류: {e}")
                return
        snd = self._sfx_cache[path]
        snd.set_volume(volume if volume is not None else self._sfx_volume)
        snd.play()

    def set_sfx_volume(self, vol: float):
        self._sfx_volume = max(0.0, min(1.0, vol))
        for snd in self._sfx_cache.values():
            snd.set_volume(self._sfx_volume)