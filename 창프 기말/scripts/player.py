# scripts/player.py

import pygame, math, sys
sys.path.insert(0, '.')
from scripts import player_base
from scripts.animation import Animation
from scripts.bullet import Bullet, SlashWave

DRAW_SIZE = 70

MELEE_RANGE  = 30
MELEE_SPREAD = math.pi * 0.75


def _scale_frames(frames, size):
    return [
        pygame.transform.scale(f.copy(), (size, size))
        for f in frames
    ]


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

        # 근접+참격 공격 트리거
        self._atk_angle       = 0.0
        self._melee_triggered = False

        # 애니메이션을 __init__ 에서 즉시 로드(지연 로드 제거)
        self._anims_loaded = False
        self._anims = {}
        self._cur_anim = None
        self._ensure_anims()

    # ── 애니메이션 로드 ────────────────────────────────────

    def _ensure_anims(self):
        if self._anims_loaded:
            return

        idle_frames   = _scale_frames(player_base.IDLE_0,   DRAW_SIZE)
        walk_frames   = _scale_frames(player_base.MOVE_0,   DRAW_SIZE)
        attack_frames = _scale_frames(player_base.ATTACK_0, DRAW_SIZE)

        self._anims = {
            "IDLE"  : Animation(idle_frames,   10, loop=True),
            "WALK"  : Animation(walk_frames,    6, loop=True),
            "ATTACK": Animation(attack_frames,  3, loop=False),
            "HIT"   : Animation(idle_frames,    6, loop=False),
        }
        self._cur_anim = self._anims["IDLE"]
        self._anims_loaded = True

    def _apply_attack_state(self):
        """ATTACK 애니메이션 강제 시작."""
        self.state = "ATTACK"
        anim = self._anims["ATTACK"]
        anim.reset()
        self._cur_anim = anim

    # ── 이동 / 입력 ────────────────────────────────────────

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

    # ── 공격 ───────────────────────────────────────────────

    def try_shoot(self, mouse_pos, cam_x, cam_y):
        """공격 시도. 쿨다운 중이면 None 반환."""
        if self.fire_cd > 0:
            return None
        wx = mouse_pos[0] + cam_x
        wy = mouse_pos[1] + cam_y
        self._atk_angle       = math.atan2(wy - self.y, wx - self.x)
        self.fire_cd          = self.fire_rate
        self._melee_triggered = True

        # 애니메이션은 항상 즉시 적용 (__init__ 에서 로드 보장)
        self._apply_attack_state()

        return SlashWave(self.x, self.y, self._atk_angle, damage=self.damage)

    def consume_melee(self):
        if self._melee_triggered:
            self._melee_triggered = False
            return True, self._atk_angle
        return False, 0.0

    def melee_hits(self, ex, ey):
        dx   = ex - self.x
        dy   = ey - self.y
        dist = math.hypot(dx, dy)
        if dist > MELEE_RANGE:
            return False
        angle_to = math.atan2(dy, dx)
        diff     = abs(math.atan2(math.sin(angle_to - self._atk_angle),
                                  math.cos(angle_to - self._atk_angle)))
        return diff < MELEE_SPREAD

    # ── 업데이트 ───────────────────────────────────────────

    def update(self):
        self._ensure_anims()

        if self.fire_cd > 0:
            self.fire_cd -= 1
        if self.hit_timer > 0:
            self.hit_timer -= 1

        if self._cur_anim:
            self._cur_anim.update()

            if self._cur_anim.done and self.state in ("ATTACK", "HIT"):
                self.state = "IDLE"
                self._anims["IDLE"].reset()
                self._cur_anim = self._anims["IDLE"]

    def take_damage(self, amount):
        if self.hit_timer > 0:
            return False
        self.hp -= amount
        self.hit_timer = 60
        self.state = "HIT"
        self._anims["HIT"].reset()
        self._cur_anim = self._anims["HIT"]
        if self.hp < 0:
            self.hp = 0
        return True

    def is_dead(self):
        return self.hp <= 0

    # ── 그리기 ─────────────────────────────────────────────

    def draw(self, screen, cam_x, cam_y):
        self._ensure_anims()
        if not self._cur_anim:
            return

        if self.state == "HIT" and self.hit_timer > 0 and (self.hit_timer // 4) % 2 == 0:
            return

        sx = int(self.x) - cam_x - DRAW_SIZE // 2
        sy = int(self.y) - cam_y - DRAW_SIZE // 2

        # ATTACK 상태: 일부 프레임(26,27)은 검 이펙트 오버레이만 있고
        # 플레이어 몸체가 없어 투명하게 보임.
        # IDLE 기본 스프라이트를 먼저 깔고, 공격 프레임을 위에 덧그려
        # 몸체가 사라지지 않으면서 검 이펙트도 표시된다.
        if self.state == "ATTACK":
            base = self._anims["IDLE"].get_image()
            if self.flip:
                base = pygame.transform.flip(base, True, False)
            screen.blit(base, (sx, sy))

        img = self._cur_anim.get_image()
        if self.flip:
            img = pygame.transform.flip(img, True, False)
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