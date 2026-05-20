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
