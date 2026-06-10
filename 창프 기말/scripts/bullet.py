# scripts/bullet.py

import pygame
import math

class Bullet:
    """플레이어가 발사하는 투사체"""

    def __init__(self, x, y, angle, speed=9, damage=20,
                 color=(255, 220, 60), radius=5):
        self.x      = float(x)
        self.y      = float(y)
        self.vx     = math.cos(angle) * speed
        self.vy     = math.sin(angle) * speed
        self.damage = damage
        self.color  = color
        self.radius = radius
        self.alive  = True
        # 최대 비행 거리
        self._dist  = 0
        self._max_dist = 600

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self._dist += math.hypot(self.vx, self.vy)
        if self._dist > self._max_dist:
            self.alive = False

    def get_rect(self):
        r = self.radius
        return pygame.Rect(int(self.x) - r, int(self.y) - r, r*2, r*2)

    def draw(self, screen, cam_x, cam_y):
        if not self.alive:
            return
        sx = int(self.x) - cam_x
        sy = int(self.y) - cam_y
        # 외곽 글로우
        pygame.draw.circle(screen, (255, 255, 200), (sx, sy), self.radius + 2)
        pygame.draw.circle(screen, self.color,       (sx, sy), self.radius)


class EnemyBullet(Bullet):
    """적이 발사하는 투사체"""

    def __init__(self, x, y, angle, speed=4, damage=8):
        super().__init__(x, y, angle, speed, damage,
                         color=(255, 80, 80), radius=4)
        self._max_dist = 500


class SlashWave(Bullet):
    """
    플레이어 참격 파동 — 근거리 공격과 동시에 발사되는 원거리 슬래시.
    - 부채꼴 모양으로 그려지는 빠른 투사체
    - 넓은 히트박스 (radius=18), 짧은 사거리 (240px)
    - 데미지는 일반 총알의 0.7배
    """

    def __init__(self, x, y, angle, damage=14):
        super().__init__(x, y, angle, speed=14, damage=damage,
                         color=(180, 230, 255), radius=18)
        self._max_dist  = 240
        self._angle     = angle
        self._life      = 0      # 생존 프레임 (그리기 페이드용)

    def update(self):
        super().update()
        self._life += 1

    def draw(self, screen, cam_x, cam_y):
        if not self.alive:
            return
        sx = int(self.x) - cam_x
        sy = int(self.y) - cam_y

        # 페이드 아웃 (짧은 수명이므로 진행도로 alpha 계산)
        progress  = self._dist / self._max_dist          # 0→1
        alpha_val = int(220 * (1.0 - progress * 0.6))

        # ── 부채꼴 슬래시 이펙트 ──
        spread = math.pi / 3          # 부채꼴 60°
        arc_r  = self.radius + 4



        surf = pygame.Surface((arc_r*4, arc_r*4), pygame.SRCALPHA)
        pygame.draw.arc(surf, (15, 10, 20, max(0, alpha_val)),
                        (4, 4, arc_r*4-8, arc_r*4-8),
                        -(self._angle + spread/2),
                        -(self._angle - spread/2), 5)
        screen.blit(surf, (sx - arc_r*2, sy - arc_r*2))