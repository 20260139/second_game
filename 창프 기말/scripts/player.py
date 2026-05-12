# player.py

import pygame
import base64

from io import BytesIO

from scripts.animation import Animation

from scripts import player_base


def load_base64_image(base64_string):

    image_data = base64.b64decode(base64_string)

    image = pygame.image.load(
        BytesIO(image_data)
    ).convert_alpha()

    return image


class Player:

    def __init__(self):

        # 위치
        self.x = 100
        self.y = 300

        # 크기
        self.width = 64
        self.height = 64

        # 이동 속도
        self.speed = 5

        # 체력
        self.hp = 100

        # 방향
        self.flip = False

        # 상태
        self.state = "IDLE"

        # 공격 상태
        self.is_attack = False

        # 공격 후딜레이
        self.attack_cooldown = 0

        # 피격 무적 시간
        self.hit_timer = 0

        # 애니메이션
        self.animations = {

            "IDLE": Animation(

                [
                    load_base64_image(
                        player_base.IDLE_0
                    ),

                    load_base64_image(
                        player_base.IDLE_1
                    )
                ],

                10
            ),

            "MOVE": Animation(

                [
                    load_base64_image(
                        player_base.MOVE_0
                    ),

                    load_base64_image(
                        player_base.MOVE_1
                    )
                ],

                6
            ),

            "ATTACK": Animation(

                [
                    load_base64_image(
                        player_base.ATTACK_0
                    ),

                    load_base64_image(
                        player_base.ATTACK_1
                    )
                ],

                4
            ),

            "GUARD": Animation(

                [
                    load_base64_image(
                        player_base.GUARD_0
                    ),

                    load_base64_image(
                        player_base.GUARD_1
                    )
                ],

                8
            )
        }

        self.current_animation = self.animations["IDLE"]

    def input(self, keys):

        moving = False

        if not self.is_attack:

            if keys[pygame.K_LEFT]:

                self.x -= self.speed

                self.flip = True

                moving = True

            if keys[pygame.K_RIGHT]:

                self.x += self.speed

                self.flip = False

                moving = True

            # 공격
            if keys[pygame.K_z]:

                self.attack()

            # 방어
            elif keys[pygame.K_x]:

                self.state = "GUARD"

            elif moving:

                self.state = "MOVE"

            else:

                self.state = "IDLE"

    def attack(self):

        if self.attack_cooldown > 0:
            return

        self.state = "ATTACK"

        self.is_attack = True

        self.attack_cooldown = 30

    def update(self):

        # 공격 후딜 감소
        if self.attack_cooldown > 0:

            self.attack_cooldown -= 1

        # 공격 종료
        if self.attack_cooldown <= 15:

            self.is_attack = False

        # 피격 무적 감소
        if self.hit_timer > 0:

            self.hit_timer -= 1

        # 현재 애니메이션 변경
        self.current_animation = self.animations[self.state]

        # 애니메이션 업데이트
        self.current_animation.update()

    def get_attack_rect(self):

        if not self.is_attack:
            return None

        if self.flip:

            return pygame.Rect(
                self.x - 40,
                self.y + 10,
                40,
                30
            )

        else:

            return pygame.Rect(
                self.x + self.width,
                self.y + 10,
                40,
                30
            )

    def take_damage(self, damage):

        if self.hit_timer > 0:
            return

        self.hp -= damage

        self.hit_timer = 60

    def draw(self, screen):

        image = self.current_animation.get_image()

        if self.flip:

            image = pygame.transform.flip(
                image,
                True,
                False
            )

        screen.blit(image, (self.x, self.y))
        
    def damage(self, amount):

        if self.hit_timer > 0:
            return

        self.hp -= amount

        self.hit_timer = 60

        # 공격 판정 확인용
        attack_rect = self.get_attack_rect()

        if attack_rect:

            pygame.draw.rect(
                screen,
                (255,0,0),
                attack_rect,
                2
            )