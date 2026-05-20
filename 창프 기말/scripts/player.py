# scripts/player.py

import pygame, math, base64, sys
from io import BytesIO
sys.path.insert(0, '.')
from scripts import player_base
from scripts.animation import Animation
from scripts.bullet import Bullet

CELL      = 64
DRAW_SIZE = 52

def _load_frames_from_sheet(b64_data, n_cols, row=0):
    raw   = base64.b64decode(b64_data)
    sheet = pygame.image.load(BytesIO(raw)).convert_alpha()
    frames = []
    for col in range(n_cols):
        rect  = pygame.Rect(col * CELL, row * CELL, CELL, CELL)
        frame = pygame.transform.scale(
            sheet.subsurface(rect).copy(), (DRAW_SIZE, DRAW_SIZE)
        )
        frames.append(frame)
    return frames


class Player:

    def __init__(self):
        self.x = 200.0
        self.y = 300.0
        self.radius = 12

        self.max_hp    = 100
        self.hp        = 100
        self.speed     = 3.2
        self.damage    = 20
        self.fire_rate = 22

        self.flip      = False
        self.state     = "IDLE"
        self.hit_timer = 0
        self.fire_cd   = 0
        self._attack_queued = False

        # 애니메이션은 최초 draw/update 시 로드
        self._anims_loaded = False
        self._anims = {}
        self._cur_anim = None

    def _ensure_anims(self):
        if self._anims_loaded:
            return
        self._anims = {
            "IDLE"  : Animation(_load_frames_from_sheet(player_base.IDLE_0,   8, row=0), 10, loop=True),
            "WALK"  : Animation(_load_frames_from_sheet(player_base.MOVE_0,   8, row=0),  6, loop=True),
            # ATTACK_0 시트는 가로 8프레임, loop=False (1회 재생)
            "ATTACK": Animation(_load_frames_from_sheet(player_base.ATTACK_0, 8, row=0),  3, loop=False),
            "HIT"   : Animation(_load_frames_from_sheet(player_base.IDLE_0,   8, row=0),  6, loop=False),
        }
        self._cur_anim = self._anims["IDLE"]
        self._anims_loaded = True

        # 로드 시점에 큐에 쌓인 공격이 있으면 즉시 적용
        if self._attack_queued:
            self._apply_attack_state()
            self._attack_queued = False

    def _apply_attack_state(self):
        """ATTACK 애니메이션 강제 시작"""
        self.state = "ATTACK"
        anim = self._anims["ATTACK"]
        anim.reset()
        self._cur_anim = anim

    def get_rect(self):
        r = self.radius
        return pygame.Rect(int(self.x)-r, int(self.y)-r, r*2, r*2)

    def handle_input(self, keys, mouse_pos, walls, cam_x=0, cam_y=0):
        dx, dy = 0.0, 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1

        if dx and dy:
            dx *= 0.707
            dy *= 0.707

        self._move(dx * self.speed, 0, walls)
        self._move(0, dy * self.speed, walls)

        player_screen_x = self.x - cam_x
        self.flip = mouse_pos[0] < player_screen_x

        # 이동 상태 (ATTACK/HIT 중에는 덮어쓰지 않음)
        if self.state not in ("ATTACK", "HIT"):
            new_state = "WALK" if (dx or dy) else "IDLE"
            self._set_state(new_state)

    def _move(self, dx, dy, walls):
        self.x += dx
        self.y += dy
        r = self.radius
        rect = pygame.Rect(int(self.x)-r, int(self.y)-r, r*2, r*2)
        for wall in walls:
            if rect.colliderect(wall):
                if dx > 0: self.x = wall.left  - r
                if dx < 0: self.x = wall.right + r
                if dy > 0: self.y = wall.top   - r
                if dy < 0: self.y = wall.bottom + r

    def _set_state(self, new_state):
        if self.state == new_state:
            return
        self.state = new_state
        if self._anims_loaded and new_state in self._anims:
            self._anims[new_state].reset()
            self._cur_anim = self._anims[new_state]

    def try_shoot(self, mouse_pos, cam_x, cam_y):
        if self.fire_cd > 0:
            return None
        wx = mouse_pos[0] + cam_x
        wy = mouse_pos[1] + cam_y
        angle = math.atan2(wy - self.y, wx - self.x)
        self.fire_cd = self.fire_rate
        self._attack_queued = True
        return Bullet(self.x, self.y, angle, damage=self.damage)

    def update(self):
        # 애니메이션 로드 (최초 1회)
        self._ensure_anims()

        if self.fire_cd > 0:
            self.fire_cd -= 1
        if self.hit_timer > 0:
            self.hit_timer -= 1

        # 큐에 쌓인 공격 트리거 (anims가 로드된 이후)
        if self._attack_queued and self._anims_loaded:
            self._apply_attack_state()
            self._attack_queued = False

        # 애니메이션 진행
        if self._cur_anim:
            self._cur_anim.update()
            # 1회 재생 완료 → IDLE로 복귀
            if self._cur_anim.done and self.state in ("ATTACK", "HIT"):
                self.state = "IDLE"
                self._anims["IDLE"].reset()
                self._cur_anim = self._anims["IDLE"]

    def take_damage(self, amount):
        if self.hit_timer > 0:
            return False
        self.hp -= amount
        self.hit_timer = 60
        # HIT 상태 (ATTACK 중이어도 피격 우선)
        if self._anims_loaded:
            self.state = "HIT"
            self._anims["HIT"].reset()
            self._cur_anim = self._anims["HIT"]
        else:
            self.state = "HIT"
        if self.hp < 0:
            self.hp = 0
        return True

    def is_dead(self):
        return self.hp <= 0

    def draw(self, screen, cam_x, cam_y):
        self._ensure_anims()
        if not self._cur_anim:
            return

        # 피격 깜빡임
        if self.hit_timer > 0 and (self.hit_timer // 4) % 2 == 0:
            return

        img = self._cur_anim.get_image()
        if self.flip:
            img = pygame.transform.flip(img, True, False)

        sx = int(self.x) - cam_x - DRAW_SIZE // 2
        sy = int(self.y) - cam_y - DRAW_SIZE // 2
        screen.blit(img, (sx, sy))

    def draw_hud(self, screen, sw, sh):
        bx, by, bw, bh = 20, 20, 180, 16
        pygame.draw.rect(screen, (50, 15, 15), (bx, by, bw, bh), border_radius=4)
        ratio = max(self.hp / self.max_hp, 0)
        bar_color = (
            int(60 + 160*(1-ratio)),
            int(200 - 150*(1-ratio)),
            40
        )
        pygame.draw.rect(screen, bar_color, (bx, by, int(bw*ratio), bh), border_radius=4)
        pygame.draw.rect(screen, (200,200,200), (bx, by, bw, bh), 1, border_radius=4)

        font = pygame.font.SysFont(None, 22)
        t = font.render(f"HP  {self.hp} / {self.max_hp}", True, (230,230,230))
        screen.blit(t, (bx+4, by+1))

        cd_ratio = self.fire_cd / self.fire_rate if self.fire_rate else 0
        cx = sw // 2
        cy = sh - 30
        pygame.draw.arc(screen, (80, 180, 255),
                        (cx-20, cy-20, 40, 40),
                        math.pi/2 - cd_ratio*2*math.pi, math.pi/2, 5)
        pygame.draw.circle(screen, (80, 180, 255), (cx, cy), 6)
