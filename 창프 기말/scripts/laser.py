# scripts/laser.py

import pygame


class Laser:

    def __init__(self,
                 x,
                 y,
                 width,
                 height,
                 interval):

        self.rect = pygame.Rect(
            x,
            y,
            width,
            height
        )

        # 깜빡임 간격
        self.interval = interval

        self.timer = 0

        # 활성 여부
        self.active = True

    def update(self):

        self.timer += 1

        if self.timer >= self.interval:

            self.timer = 0

            self.active = not self.active

    def draw(self, screen):

        if self.active:

            pygame.draw.rect(
                screen,
                (0,150,255),
                self.rect
            )