# scripts/stage1.py

import pygame

from scripts.laser import Laser


class Stage1:

    def __init__(self):

        # 벽
        self.walls = [

            # 시작 지역
            pygame.Rect(50, 450, 300, 20),
            pygame.Rect(50, 450, 20, 180),
            pygame.Rect(330, 450, 20, 180),

            # 중앙 통로
            pygame.Rect(180, 250, 40, 200),

            # 상단 외벽
            pygame.Rect(100, 100, 500, 20),
            pygame.Rect(100, 100, 20, 300),
            pygame.Rect(580, 100, 20, 300),
            pygame.Rect(100, 380, 500, 20),

            # 내부 벽
            pygame.Rect(200, 180, 180, 20),
            pygame.Rect(360, 180, 20, 120),
            pygame.Rect(250, 300, 180, 20),
        ]

        # 용암
        self.lavas = [

            pygame.Rect(130, 120, 430, 40),

            pygame.Rect(120, 160, 60, 180),

            pygame.Rect(450, 160, 130, 200),

            pygame.Rect(160, 320, 120, 50),

            pygame.Rect(430, 320, 120, 50),
        ]

        # 레이저
        self.lasers = [

            Laser(
                170,
                390,
                120,
                5,
                60
            ),

            Laser(
                170,
                420,
                120,
                5,
                90
            ),

            Laser(
                170,
                450,
                120,
                5,
                45
            ),

            Laser(
                170,
                480,
                120,
                5,
                75
            )
        ]

    def update(self):

        for laser in self.lasers:

            laser.update()

    def draw(self, screen):

        # 벽
        for wall in self.walls:

            pygame.draw.rect(
                screen,
                (120,120,120),
                wall
            )

        # 용암
        for lava in self.lavas:

            pygame.draw.rect(
                screen,
                (255,80,0),
                lava
            )

        # 레이저
        for laser in self.lasers:

            laser.draw(screen)